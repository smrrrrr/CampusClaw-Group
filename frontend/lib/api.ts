"use client";

import { useAuthStore } from "./store";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  // 为 true 时 401 不触发自动刷新（登录/刷新接口本身）
  skipAuthRefresh?: boolean;
}

let refreshingPromise: Promise<boolean> | null = null;

export async function refreshAccessToken(): Promise<boolean> {
  // 并发请求只触发一次刷新
  if (refreshingPromise) return refreshingPromise;

  refreshingPromise = (async () => {
    try {
      const res = await fetch("/api/auth/refresh", {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) return false;
      const data = await res.json();
      const user: UserInfoDTO = data.user;
      useAuthStore.getState().setSession({
        accessToken: data.access_token,
        userRole: user.role,
        mustChangePassword: data.must_change_password,
        currentStudent: user.role === "student" ? { id: user.id, name: user.name, class_id: user.class_id } : null,
        teachingClasses: user.teaching_classes ?? null,
        subject: user.subject ?? null,
        homeroomClassId: user.homeroom_class_id ?? null,
      });
      setRoleCookies(user.role);
      return true;
    } catch {
      return false;
    } finally {
      refreshingPromise = null;
    }
  })();

  return refreshingPromise;
}

export async function apiRequest<T = unknown>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const doFetch = (): Promise<Response> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = {};
    if (options.body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers["Authorization"] = `Bearer ${token}`;

    return fetch(path, {
      method: options.method ?? "GET",
      headers,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
      credentials: "include",
    });
  };

  let res = await doFetch();

  // Access Token 过期：自动刷新后重试一次
  if (res.status === 401 && !options.skipAuthRefresh) {
    const ok = await refreshAccessToken();
    if (ok) {
      res = await doFetch();
    } else {
      useAuthStore.getState().reset();
      if (typeof window !== "undefined" && window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
      throw new ApiError(401, "登录已失效，请重新登录");
    }
  }

  if (!res.ok) {
    let detail = "请求失败";
    try {
      const data = await res.json();
      detail = data.detail ?? detail;
    } catch {
      // 非 JSON 错误体
    }
    throw new ApiError(res.status, detail);
  }

  // 204 / 空响应
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- 类型定义（与后端 schemas 对齐） ---

export interface UserInfoDTO {
  id: number;
  role: "teacher" | "student";
  name: string | null;
  class_id: number | null;
  must_change_password: boolean;
  teaching_classes?: number[] | null;
  subject?: string | null;
  homeroom_class_id?: number | null;
}

export interface TokenDTO {
  access_token: string;
  token_type: string;
  must_change_password: boolean;
  role: "teacher" | "student";
  user: UserInfoDTO;
}

/** 设置/清除用于 middleware 路由守卫的辅助 Cookie（非 HttpOnly，仅前端路由用）。 */
export function setRoleCookies(role: "teacher" | "student") {
  document.cookie = `cc_role=${role}; path=/; max-age=${7 * 24 * 60 * 60}`;
  document.cookie = "cc_has_token=1; path=/; max-age=" + 7 * 24 * 60 * 60;
}

export function clearRoleCookies() {
  document.cookie = "cc_role=; path=/; max-age=0";
  document.cookie = "cc_has_token=; path=/; max-age=0";
}

export const api = {
  listResearchMaterials: () => apiRequest<{ items: ResearchMaterialDTO[] }>("/api/teacher/research-materials"),
  getResearchMaterial: (id: number) => apiRequest<ResearchMaterialDetailDTO>(`/api/teacher/research-materials/${id}`),
  importResearchMaterial: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const response = await authenticatedFetch("/api/teacher/research-materials", { method: "POST", body: form });
    return await response.json() as ResearchMaterialDetailDTO & { message: string };
  },
  previewStudentMaterial: (id: number) => apiRequest<{ content: string; message: string }>(`/api/teacher/research-materials/${id}/student-preview`, { method: "POST" }),
  publishStudentMaterial: (id: number, classIds: number[], content: string, reviewed: boolean) =>
    apiRequest<{ message: string; material_ids: number[]; class_ids: number[]; indexed: boolean[] }>(`/api/teacher/research-materials/${id}/publish`, { method: "POST", body: { class_ids: classIds, content, reviewed } }),
  researchAssetUrl: (id: number, src: string) => `/api/teacher/research-materials/${id}/assets?name=${encodeURIComponent(decodeURIComponent(src))}`,
  materialAssetUrl: (id: number, src: string) => `/api/materials/${id}/assets?name=${encodeURIComponent(decodeURIComponent(src))}`,
  listAuditLogs: (classId: number) =>
    apiRequest<{ items: { id: number; user_id: number | null; role: string | null; request_path: string; method: string; status_code: number; created_at: string }[]; total: number }>(`/api/teacher/audit-logs?class_id=${classId}`),
  login: (identifier: string, password: string) =>
    apiRequest<TokenDTO>("/api/auth/login", {
      method: "POST",
      body: { identifier, password },
      skipAuthRefresh: true,
    }),

  changePassword: (oldPassword: string, newPassword: string) =>
    apiRequest<TokenDTO>("/api/auth/change-password", {
      method: "POST",
      body: { old_password: oldPassword, new_password: newPassword },
    }),

  logout: () =>
    apiRequest<{ message: string }>("/api/auth/logout", { method: "POST" }),

  // --- 学生 AI 提问 ---
  askAI: (question: string) =>
    apiRequest<AIAnswerResponse>(
      "/api/student/ai-question",
      { method: "POST", body: { question } },
    ),
  getAIHistory: () =>
    apiRequest<AIHistoryItem[]>("/api/student/ai-history", { method: "GET" }),
  deleteAIHistory: (id: number) =>
    apiRequest<{ ok: boolean }>(`/api/student/ai-history/${id}`, { method: "DELETE" }),

  // --- 教师班级/学生（后端按 JWT teaching_classes 校验所选班级）---
  listClasses: () =>
    apiRequest<{ id: number; name: string }[]>("/api/teacher/classes"),
  listStudents: (classId?: number) =>
    apiRequest<{ items: { id: number; identifier: string; name: string | null; class_id: number | null; class_name: string | null; phone: string | null }[]; total: number }>(
      classId === undefined ? "/api/teacher/students" : `/api/teacher/students?class_id=${classId}`,
      { method: "GET" },
    ),
  resetStudentPassword: (studentId: number) =>
    apiRequest<{ message: string; initial_password: string }>(
      "/api/teacher/reset-password",
      { method: "POST", body: { student_id: studentId } },
    ),

  // --- AI 助手配置（教师按班级）---
  getAgentConfig: (classId: number) =>
    apiRequest<AgentConfigDTO>(`/api/teacher/agent-config?class_id=${classId}`),
  saveAgentConfig: (payload: { class_id: number; system_prompt: string; tutor_enabled: boolean }) =>
    apiRequest<AgentConfigDTO>("/api/teacher/agent-config", { method: "PUT", body: payload }),
  getAgentDefaultPrompt: () =>
    apiRequest<{ system_prompt: string; tutor_skill_prompt: string }>(
      "/api/teacher/agent-config/default-prompt",
    ),

  // --- AI 助手多轮会话（学生）---
  getStudentAssistantConfig: (subject: AssistantSubject, conversationId?: number) =>
    apiRequest<StudentAssistantConfigDTO>(`/api/student/assistant-config?subject=${subject}${conversationId !== undefined ? `&conversation_id=${conversationId}` : ""}`),
  createConversation: (title?: string, subject: AssistantSubject = "math") =>
    apiRequest<ConversationItemDTO>("/api/student/conversations", {
      method: "POST",
      body: { title: title ?? "新对话", subject },
    }),
  listConversations: (subject: AssistantSubject = "math") =>
    apiRequest<ConversationItemDTO[]>(`/api/student/conversations?subject=${subject}`),
  getConversationMessages: (id: number) =>
    apiRequest<ConversationMessageDTO[]>(`/api/student/conversations/${id}/messages`),
  deleteConversation: (id: number) =>
    apiRequest<{ ok: boolean }>(`/api/student/conversations/${id}`, { method: "DELETE" }),

  // --- 材料 ---
  uploadMaterial: (
    formData: FormData,
    onProgress?: (loaded: number, total: number) => void,
  ) =>
    new Promise<{ id: number; filename: string; file_type: string; file_size: number; class_id: number; is_indexed: boolean; created_at: string; message: string }>(
      (resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/teacher/upload-material");
        const token = useAuthStore.getState().accessToken;
        if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.withCredentials = true;
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) {
            onProgress(e.loaded, e.total);
          }
        };
        xhr.onload = () => {
          if (xhr.status === 401) {
            refreshAccessToken().then((ok) => {
              if (ok) {
                const newToken = useAuthStore.getState().accessToken;
                if (newToken) xhr.setRequestHeader("Authorization", `Bearer ${newToken}`);
                // 重试
                xhr.open("POST", "/api/teacher/upload-material");
                xhr.setRequestHeader("Authorization", `Bearer ${newToken}`);
                xhr.send(formData);
              } else {
                reject(new ApiError(401, "登录已失效，请重新登录"));
              }
            });
            return;
          }
          if (xhr.status >= 400) {
            let detail = "上传失败";
            try {
              detail = JSON.parse(xhr.responseText).detail ?? detail;
            } catch {
              // 非 JSON
            }
            reject(new ApiError(xhr.status, detail));
            return;
          }
          resolve(JSON.parse(xhr.responseText));
        };
        xhr.onerror = () => reject(new ApiError(0, "网络中断，请重试"));
        xhr.send(formData);
      },
    ),

  listMaterials: (params?: { class_id?: number; search?: string; limit?: number; offset?: number; subject_only?: boolean }) => {
    const qs = new URLSearchParams();
    if (params?.class_id !== undefined) qs.set("class_id", String(params.class_id));
    if (params?.search) qs.set("search", params.search);
    if (params?.subject_only) qs.set("subject_only", "true");
    if (params?.limit !== undefined) qs.set("limit", String(params.limit));
    if (params?.offset !== undefined) qs.set("offset", String(params.offset));
    const q = qs.toString();
    return apiRequest<{
      items: MaterialItemDTO[];
      total: number;
    }>(q ? `/api/materials?${q}` : "/api/materials");
  },

  reindexMaterial: (materialId: number) =>
    apiRequest<{ id: number; is_indexed: boolean; message: string }>(
      `/api/teacher/materials/${materialId}/reindex`,
      { method: "POST" },
    ),

  deleteMaterial: (materialId: number) =>
    apiRequest<{ id: number; message: string }>(
      `/api/teacher/materials/${materialId}`,
      { method: "DELETE" },
    ),

  materialDownloadUrl: (materialId: number, expectedSha256?: string | null) => `/api/materials/${materialId}/download${expectedSha256 ? `?expected_sha256=${encodeURIComponent(expectedSha256)}` : ""}`,
  materialPreviewUrl: (materialId: number) => `/api/materials/${materialId}/preview`,
};

export interface ResearchMaterialDTO {
  id: number; filename: string; subject: string; uploader_name: string | null;
  created_at: string; asset_count: number; chunk_count: number;
  kind: 'source' | 'lesson-plan'; lesson_version: number | null;
}
export interface ResearchMaterialDetailDTO extends ResearchMaterialDTO {
  content: string;
  lesson_sources: { ref: string; filename: string; heading: string; start_line: number; end_line: number; file_sha256: string; excerpt: string }[];
  publications: { material_id: number; class_id: number; class_name: string; created_at: string }[];
}

/** 原文件、图文包与配图通过同一鉴权流程，不把令牌拼进图片 URL。 */
export async function authenticatedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  if (!path.startsWith("/api/")) throw new Error("不支持的资料地址");
  const perform = () => fetch(path, { ...init, credentials: "include", headers: { ...init.headers, Authorization: `Bearer ${useAuthStore.getState().accessToken}` } });
  let response = await perform();
  if (response.status === 401 && await refreshAccessToken()) response = await perform();
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new ApiError(response.status, error.detail ?? "资料加载失败");
  }
  return response;
}

export interface MaterialItemDTO {
  id: number;
  class_id: number;
  uploader_id: number;
  filename: string;
  file_type: string;
  file_size: number;
  description: string | null;
  tags: string[];
  is_indexed: boolean;
  created_at: string;
  class_name: string | null;
}

// AI 回答溯源（add-rag-search）
export interface AnswerCitation {
  material_id: number;
  filename: string;
  chunk_index: number;
  excerpt: string;
  score: number;
  reference_id?: number | null;
  file_sha256?: string | null;
}

export interface AIAnswerResponse {
  id: number;
  answer: string;
  remaining: number;
  citations: AnswerCitation[];
}

export interface AIHistoryItem {
  id: number;
  question: string;
  answer: string;
  created_at: string;
}

// --- AI 助手配置与会话（多轮 agent）---

export interface AgentConfigDTO {
  class_id: number;
  subject: string;
  teacher_id: number;
  system_prompt: string;
  tutor_enabled: boolean;
}

export type AssistantSubject = "math" | "chinese" | "english" | "physics" | "chemistry" | "biology";
export interface StudentAssistantConfigDTO {
  class_id: number;
  subject: AssistantSubject;
  teacher_id: number | null;
  teacher_name: string | null;
  configured: boolean;
  tutor_enabled: boolean;
}

export interface ConversationItemDTO {
  id: number;
  title: string;
  updated_at: string;
  subject: AssistantSubject;
}

export interface ConversationMessageDTO {
  id: number;
  role: "user" | "assistant";
  content: string;
  sources: AnswerCitation[];
  created_at: string;
}

export interface ChatDoneData {
  answer: string;
  citations: AnswerCitation[];
  remaining: number;
}

interface ChatStreamCallbacks {
  onDelta?: (text: string) => void;
  onDone?: (data: ChatDoneData) => void;
  onError?: (message: string, citations?: AnswerCitation[]) => void;
}

/** 向某会话发起流式提问；通过 fetch 读取 SSE，按事件分发 delta / done / error。 */
export async function streamChat(
  conversationId: number,
  question: string,
  cb: ChatStreamCallbacks,
): Promise<void> {
  const doFetch = (): Promise<Response> => {
    const token = useAuthStore.getState().accessToken;
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return fetch(`/api/student/conversations/${conversationId}/chat`, {
      method: "POST",
      headers,
      body: JSON.stringify({ question }),
      credentials: "include",
    });
  };

  let res = await doFetch();
  if (res.status === 401) {
    const ok = await refreshAccessToken();
    if (ok) {
      res = await doFetch();
    } else {
      useAuthStore.getState().reset();
      cb.onError?.("登录已失效，请重新登录");
      return;
    }
  }
  if (!res.status) throw new ApiError(0, "网络中断");

  if (!res.ok || !res.body) {
    let detail = "提问失败";
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      // 忽略
    }
    cb.onError?.(detail);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const dispatch = (raw: string) => {
    for (const line of raw.split("\n")) {
      if (!line.startsWith("data:")) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const evt = JSON.parse(payload);
        if (evt.type === "delta") cb.onDelta?.(evt.content ?? "");
        else if (evt.type === "done")
          cb.onDone?.({ answer: evt.answer ?? "", citations: evt.citations ?? [], remaining: evt.remaining ?? 0 });
        else if (evt.type === "error") cb.onError?.(evt.message ?? "AI 响应异常", evt.citations);
      } catch {
        // 忽略非 JSON 的 SSE 行
      }
    }
  };

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      // SSE 事件以空行分隔；按每个完整事件处理以支持跨 chunk 的半行
      let idx;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const chunk = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        dispatch(chunk);
      }
    }
    if (buffer) dispatch(buffer);
  } catch {
    cb.onError?.("网络中断，请重试");
  }
}
