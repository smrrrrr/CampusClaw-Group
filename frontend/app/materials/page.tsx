"use client";

import { useRouter } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { useTeacherNavigation } from "@/components/teacher-navigation";
import { LogoutButton } from "@/components/logout-button";
import { MaterialPreview } from "@/components/material-preview";
import { api, ApiError, MaterialItemDTO } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { STUDENT_NAV_ITEMS } from "@/components/student-navigation";
import { RecentHistory } from "@/components/recent-history";
import { historyKey } from "@/lib/recent-history";
import { useRecentHistory } from "@/lib/use-recent-history";

function MaterialsHome() {
  const userRole = useAuthStore((s) => s.userRole);
  const teacherNav = useTeacherNavigation();
  const currentStudent = useAuthStore((s) => s.currentStudent);
  const classFilter = teacherNav.classId;
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<MaterialItemDTO[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [previewItem, setPreviewItem] = useState<MaterialItemDTO | null>(null);
  const [subjectFilter, setSubjectFilter] = useState("全部");

  const isTeacher = userRole === "teacher";
  const searchHistory = useRecentHistory(isTeacher ? null : historyKey(currentStudent?.id, currentStudent?.class_id, "materials", subjectFilter));
  const subjectOnly = isTeacher && !teacherNav.isHomeroom;
  const requestSequence = useRef(0);
  const studentName = currentStudent?.name ?? "同学";
  const studentClassName = currentStudent?.class_id === 101 ? "高二（1）班" : currentStudent?.class_id === 102 ? "高二（2）班" : `班级 ${currentStudent?.class_id ?? "—"}`;
  const hasClasses = isTeacher
    ? classFilter !== null
    : currentStudent?.class_id != null;

  const fetchMaterials = async (cid: number | null, searchStr: string) => {
    if (cid === null) return;
    const sequence = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const data = await api.listMaterials({ class_id: cid || undefined, search: searchStr || undefined, subject_only: subjectOnly });
      if (sequence !== requestSequence.current) return;
      setItems(data.items);
    } catch (err) {
      if (sequence !== requestSequence.current) return;
      setError(err instanceof ApiError ? err.message : "加载材料列表失败");
      setItems([]);
    } finally {
      if (sequence === requestSequence.current) setLoading(false);
    }
  };

  useEffect(() => {
    setItems([]);
    setPreviewItem(null);
    const cid = isTeacher ? classFilter : currentStudent?.class_id ?? null;
    if (cid !== null) fetchMaterials(cid, search);
    return () => { requestSequence.current += 1; };
  }, [isTeacher, classFilter, currentStudent?.class_id, subjectOnly]);

  const runSearch = (value: string) => {
    const cid = isTeacher ? classFilter : currentStudent?.class_id ?? null;
    const term = value.trim();
    setSearch(term);
    if (!isTeacher && cid !== null) searchHistory.add(term);
    fetchMaterials(cid, term);
  };
  const handleSearch = () => runSearch(search);

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes}B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
    return `${(bytes / 1024 / 1024).toFixed(2)}MB`;
  };

  const visibleItems = !isTeacher && subjectFilter !== "全部"
    ? items.filter((item) => `${item.filename} ${item.description ?? ""} ${item.tags.join(" ")}`.includes(subjectFilter))
    : items;

  const handleDelete = async (item: MaterialItemDTO) => {
    if (!window.confirm(`确定删除「${item.filename}」吗？删除后将无法恢复。`)) return;
    setDeletingId(item.id);
    setError("");
    try {
      await api.deleteMaterial(item.id);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
      if (previewItem?.id === item.id) setPreviewItem(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "删除失败");
    } finally {
      setDeletingId(null);
    }
  };

  const router = useRouter();

  const nav = isTeacher ? teacherNav.navItems : STUDENT_NAV_ITEMS;
  const handleNav = (key: string) => {
    const found =
      nav.find((n) => n.key === key) ||
      nav.flatMap((n) => n.children ?? []).find((c) => c.key === key);
    if (found?.to) router.push(found.to);
  };

  return (
    <AppShell
      brandMark={isTeacher ? "T" : "S"}
      subtitle={isTeacher ? "智能教学平台 · 教师端" : "学习平台 · 学生端"}
      navItems={nav}
      active={isTeacher ? teacherNav.isHomeroom ? "class-materials" : "subject-materials" : "materials"}
      navHeader={isTeacher ? teacherNav.navHeader : undefined}
      navFoot={isTeacher ? "CampusClaw · 教师工作空间" : "学习空间 · 学习数据仅本人可见"}
      headerLeft={isTeacher ? undefined : <><span className="status-dot" /><span className="class-pill">{studentClassName}</span></>}
      onNavigate={handleNav}
      headerRight={
        <>
          {isTeacher ? (
            <>
              <button className="hdr-btn" onClick={() => router.push(teacherNav.href(teacherNav.isHomeroom ? "home" : "students"))}>工作台</button>
              {!teacherNav.isHomeroom && <button className="hdr-btn" onClick={() => router.push(teacherNav.uploadHref)}>单科资料发布</button>}
            </>
          ) : (
            <span className="user-chip"><span className="avatar">生</span>{studentName}</span>
          )}
          <LogoutButton />
        </>
      }
    >
      <div className={`content${isTeacher ? "" : " student-materials-page"}`} style={{ padding: 0, maxWidth: "none" }}>
        <div className="page-title"><h2>{isTeacher ? teacherNav.isHomeroom ? "本班资料（全科）" : "本班资料（单科）" : "讲义与检索"}</h2><p>{isTeacher ? teacherNav.isHomeroom ? "查看带班班级各科讲义，此总览为只读视图。" : `${teacherNav.subjectName} · 查看当前任教班级已发布的资料，可预览或下载。` : `在 ${studentClassName} 的知识库中检索，结果会标注来源（讲义名与位置）。`}</p></div>

        {!hasClasses ? (
          <div className="card" style={{ textAlign: "center", padding: 32 }}>
            <p className="hint" style={{ fontSize: 16 }}>
              {isTeacher ? "暂无任教班级" : "暂无班级"}
            </p>
            <p className="hint" style={{ marginTop: 8 }}>
              {isTeacher ? "您尚未被分配任教班级，请联系管理员处理。" : "您尚未被分配到任何班级，请联系教师或管理员处理。"}
            </p>
          </div>
        ) : (
          <>
            {!isTeacher && <div className="student-subject-tabs">{["全部", "数学", "语文", "英语", "物理", "化学"].map((subject) => <button className={subjectFilter === subject ? "active" : ""} key={subject} onClick={() => setSubjectFilter(subject)}>{subject}</button>)}</div>}
            <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center" }}>
              {isTeacher && (
                <>
                  <span className="class-pill">{teacherNav.isHomeroom ? "我的带班" : "任教班级"} · 班级 {classFilter}</span>
                </>
              )}
              <input
                className="input"
                style={{ flex: 1, minWidth: 0 }}
                placeholder={isTeacher ? "搜索描述或标签…" : "输入关键词，搜索本班讲义的描述或标签…"}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.nativeEvent.isComposing && !loading && handleSearch()}
              />
              <button className="btn" style={{ width: "auto", padding: "8px 16px" }} onClick={handleSearch} disabled={loading}>
                搜索
              </button>
            </div>

            {!isTeacher && <RecentHistory label="搜索历史" entries={searchHistory.entries}
              onSelect={runSearch} onClear={searchHistory.clear} disabled={loading} />}

            {error && <div className="error" style={{ marginBottom: 8 }}>{error}</div>}

            {!isTeacher && <div className="student-section-title"><span />{subjectFilter === "全部" ? "本班讲义" : `${subjectFilter}讲义`}</div>}
            <div className={isTeacher ? undefined : "student-material-results"} aria-busy={loading}>
            {loading ? (
              <p className="hint">加载中…</p>
            ) : visibleItems.length === 0 ? (
              <p className="hint">{!isTeacher && subjectFilter !== "全部" ? `暂无${subjectFilter}资料` : "暂无资料"}</p>
            ) : !isTeacher ? (
              <>
                <div className="student-material-grid">
                  {visibleItems.map((item) => <article className="student-material-card" key={item.id}>
                    <span className="student-material-icon">📘</span>
                    <div className="student-material-main"><strong>{item.filename}</strong><span>{item.description || `${item.tags.join(" · ") || "本班学习资料"}`}</span><small>{item.tags.join(" · ") || "本班讲义"} · {formatSize(item.file_size)}</small><small>{new Date(item.created_at).toLocaleString("zh-CN", { dateStyle: "short", timeStyle: "short" })}</small></div>
                    <div className="student-material-actions"><button className="btn-pill ghost sm" onClick={() => setPreviewItem(item)}>预览与下载</button></div>
                  </article>)}
                </div>
              </>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
                <thead>
                  <tr style={{ textAlign: "left", borderBottom: "2px solid #e5e7eb" }}>
                    <th style={{ padding: "8px 4px" }}>文件名</th>
                    <th style={{ padding: "8px 4px" }}>班级</th>
                    <th style={{ padding: "8px 4px" }}>大小</th>
                    <th style={{ padding: "8px 4px" }}>描述</th>
                    <th style={{ padding: "8px 4px" }}>标签</th>
                    <th style={{ padding: "8px 4px" }}>索引</th>
                    <th style={{ padding: "8px 4px" }}>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={{ padding: "8px 4px" }}>{item.filename}</td>
                      <td style={{ padding: "8px 4px" }}>{item.class_name ?? item.class_id}</td>
                      <td style={{ padding: "8px 4px" }}>{formatSize(item.file_size)}</td>
                      <td style={{ padding: "8px 4px" }}>{item.description ?? "—"}</td>
                      <td style={{ padding: "8px 4px" }}>
                        {item.tags.length > 0 ? item.tags.join(", ") : "—"}
                      </td>
                      <td style={{ padding: "8px 4px" }}>
                        {item.is_indexed ? (
                          <span style={{ color: "#059669" }}>已索引</span>
                        ) : (
                          <span style={{ color: "#9ca3af" }}>未索引</span>
                        )}
                      </td>
                      <td style={{ padding: "8px 4px", whiteSpace: "nowrap" }}>
                          <button
                            className="btn"
                            style={{ width: "auto", padding: "4px 10px", fontSize: 13, marginRight: 4 }}
                            onClick={() => setPreviewItem(item)}
                          >
                            预览与下载
                          </button>
                        {isTeacher && !teacherNav.isHomeroom && (
                          <button
                            className="btn"
                            style={{
                              width: "auto",
                              padding: "4px 10px",
                              fontSize: 13,
                              marginLeft: 4,
                              color: "#dc2626",
                              borderColor: "#fecaca",
                            }}
                            onClick={() => handleDelete(item)}
                            disabled={deletingId === item.id}
                          >
                            {deletingId === item.id ? "删除中…" : "删除"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            </div>
          </>
        )}
      </div>

      {previewItem && (
        <MaterialPreview
          item={previewItem}
          onClose={() => setPreviewItem(null)}
        />
      )}
    </AppShell>
  );
}

export default function MaterialsPage() {
  return (
    <AuthGate>
      <Suspense fallback={<div className="centered">加载中…</div>}><MaterialsHome /></Suspense>
    </AuthGate>
  );
}
