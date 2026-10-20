import { apiRequest, authenticatedFetch } from './api';

export interface LessonReference {
  ref: string; research_material_id: number; filename: string; file_sha256: string;
  start_line: number; end_line: number; heading: string; excerpt: string;
}
export interface LessonResources { references: LessonReference[]; assets: { name: string; source_id: number; source_name: string; sha256: string }[]; source_ids: number[]; source_hashes: Record<string, string> }
export interface LessonForm {
  class_id: number; topic: string; duration: number; scope: string;
  curriculum_standards: string; class_profile: string; requirements: string; research_material_ids: number[];
}
export interface LessonSummary {
  id: number; title: string; class_id: number; class_name: string; subject: string; duration: number;
  status: 'draft' | 'reviewed' | 'final'; current_version: number; revision: number; updated_at: string; created_at: string;
}
export interface LessonPlan extends LessonSummary {
  content: string; resources: LessonResources; requirements: LessonForm;
  student_lesson: string; student_handout: string; student_from_version: number | null;
  versions: { version: number; content: string; resources: LessonResources; created_at: string }[];
  publications: { id: number; version: number; kind: 'lesson' | 'handout'; class_id: number; class_name: string; material_id: number; created_at: string }[];
  group_publications: { version: number; research_material_id: number; created_at: string }[];
}
const prefix = '/api/teacher/lesson-plans';
export const lessonApi = {
  list: () => apiRequest<{ items: LessonSummary[] }>(prefix),
  get: (id: number) => apiRequest<LessonPlan>(`${prefix}/${id}`),
  save: (p: LessonPlan, content: string) => apiRequest<LessonPlan>(`${prefix}/${p.id}`, { method: 'PUT', body: { revision: p.revision, content } }),
  review: (p: LessonPlan) => apiRequest<LessonPlan>(`${prefix}/${p.id}/review`, { method: 'POST', body: { revision: p.revision, reviewed: true } }),
  finalize: (p: LessonPlan) => apiRequest<LessonPlan>(`${prefix}/${p.id}/finalize`, { method: 'POST', body: { revision: p.revision } }),
  share: (p: LessonPlan) => apiRequest<{ plan: LessonPlan; research_material_id: number; message: string }>(`${prefix}/${p.id}/share-to-group`, { method: 'POST', body: { revision: p.revision } }),
  revise: (p: LessonPlan) => apiRequest<LessonPlan>(`${prefix}/${p.id}/revise`, { method: 'POST', body: { revision: p.revision } }),
  saveStudents: (p: LessonPlan, student_lesson: string, student_handout: string) => apiRequest<LessonPlan>(`${prefix}/${p.id}/student-drafts`, { method: 'PUT', body: { revision: p.revision, student_lesson, student_handout } }),
  publish: (p: LessonPlan, kind: 'lesson' | 'handout', class_ids: number[]) => apiRequest<{ plan: LessonPlan; message: string; indexed: boolean[] }>(`${prefix}/${p.id}/publish`, { method: 'POST', body: { revision: p.revision, kind, class_ids, reviewed: true } }),
  delete: (p: LessonPlan) => apiRequest<{ message: string }>(`${prefix}/${p.id}`, { method: 'DELETE', body: { revision: p.revision } }),
  imageUrl: (id: number, src: string) => `${prefix}/${id}/assets?name=${encodeURIComponent(decodeURIComponent(src))}`,
};

/** 网络中断、无 done 帧、失败帧都不能把半篇生成结果当成已保存教案。 */
export async function streamLesson(path: string, body: unknown, options: {
  signal: AbortSignal; onDelta?: (delta: string) => void; onProgress?: (message: string) => void;
}): Promise<LessonPlan> {
  const response = await authenticatedFetch(`${prefix}${path}`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body), signal: options.signal,
  });
  if (!response.body) throw new Error('生成服务未返回内容，请重试');
  const reader = response.body.getReader(); const decoder = new TextDecoder();
  let buffer = ''; let done: LessonPlan | null = null;
  const dispatch = (line: string) => {
    if (!line.startsWith('data:')) return;
    const data = JSON.parse(line.slice(5));
    if (data.type === 'error') throw new Error(data.message);
    if (data.type === 'delta') options.onDelta?.(data.text);
    if (data.type === 'progress') options.onProgress?.(data.message);
    if (data.type === 'done') done = data.plan;
  };
  try {
    while (true) {
      const result = await reader.read();
      buffer += decoder.decode(result.value, { stream: !result.done });
      const lines = buffer.split('\n'); buffer = lines.pop() ?? '';
      for (const line of lines) dispatch(line);
      if (result.done) { if (buffer.trim()) dispatch(buffer); break; }
    }
    if (!done) throw new Error('生成连接中断，请查看教案列表确认是否已保存后再重试');
    return done;
  } finally { await reader.cancel().catch(() => {}); reader.releaseLock(); }
}
