"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { LogoutButton } from "@/components/logout-button";
import MarkdownAnswer from "@/components/markdown-answer";
import { PrintHandoutButton } from "@/components/print-handout-button";
import { useTeacherNavigation } from "@/components/teacher-navigation";
import { api, authenticatedFetch, ResearchMaterialDTO, ResearchMaterialDetailDTO } from "@/lib/api";

function Library() {
  const nav = useTeacherNavigation();
  const requestedSource = Number(useSearchParams().get("material_id"));
  const [items, setItems] = useState<ResearchMaterialDTO[]>([]);
  const [filter, setFilter] = useState<'all' | 'source' | 'lesson-plan'>('all');
  const [detail, setDetail] = useState<ResearchMaterialDetailDTO | null>(null);
  const [classes, setClasses] = useState<{ id: number; name: string }[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [draft, setDraft] = useState("");
  const [classIds, setClassIds] = useState<number[]>([]);
  const [reviewed, setReviewed] = useState(false);
  const [tab, setTab] = useState<"teacher" | "student">("teacher");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const sequence = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const teacherPrintContent = useRef<HTMLDivElement>(null);
  const studentPrintContent = useRef<HTMLDivElement>(null);
  const refresh = useCallback(async () => { setItems((await api.listResearchMaterials()).items); }, []);

  useEffect(() => {
    let cancelled = false;
    api.listResearchMaterials().then(r => { if (!cancelled) setItems(r.items); }).catch(e => { if (!cancelled) setError(e.message); }).finally(() => { if (!cancelled) setLoading(false); });
    api.listClasses().then(r => { if (!cancelled) setClasses(r); }).catch(() => {});
    return () => { cancelled = true; sequence.current++; };
  }, []);

  const select = async (id: number) => {
    const request = ++sequence.current;
    setDetail(null); setDraft(""); setReviewed(false); setClassIds([]); setTab("teacher"); setError("");
    try { const row = await api.getResearchMaterial(id); if (request === sequence.current) setDetail(row); }
    catch (e) { if (request === sequence.current) setError((e as Error).message); }
  };
  const imageUrl = useCallback((src: string) => api.researchAssetUrl(detail!.id, src), [detail?.id]);
  useEffect(() => {
    if (Number.isInteger(requestedSource) && requestedSource > 0) void select(requestedSource);
  }, [requestedSource]);
  const downloadTeacherBundle = async () => {
    if (!detail) return;
    try {
      const response = await authenticatedFetch(`/api/teacher/research-materials/${detail.id}/bundle`);
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement('a'); link.href = url;
      link.download = detail.filename.replace(/\.md$/i, '') + '.zip'; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError((e as Error).message); }
  };
  const visibleItems = filter === 'all' ? items : items.filter(item => item.kind === filter);

  const importFile = async () => {
    if (!file) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api.importResearchMaterial(file);
      await refresh(); await select(result.id);
      setMessage(result.message); setFile(null); if (fileInput.current) fileInput.current.value = "";
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const makeDraft = async () => {
    if (!detail) return;
    setBusy(true); setError(""); setMessage("");
    try { const result = await api.previewStudentMaterial(detail.id); setDraft(result.content); setReviewed(false); setTab("student"); setMessage(result.message); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  const publish = async () => {
    if (!detail) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const result = await api.publishStudentMaterial(detail.id, classIds, draft, reviewed);
      setDetail(await api.getResearchMaterial(detail.id));
      setMessage(result.message + (result.indexed.every(Boolean) ? "，索引已完成。" : "；部分资料索引失败，可在班级资料中重新索引。"));
      setReviewed(false); setClassIds([]);
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };

  return <AppShell brandMark="T" subtitle="智能教学平台 · 教师端" navItems={nav.navItems} navHeader={nav.navHeader} active="research-materials" onNavigate={nav.onNavigate} navFoot="CampusClaw · 教师工作空间" headerRight={<LogoutButton />}>
    <div className="content research-library">
      <div className="page-title"><h2>教研组资料</h2><p>{nav.subjectName}教研组 · 教师版组内共享，学生版按任教班级发布。</p></div>
      <section className="card research-import">
        <div><h3>导入教师版资料</h3><p className="hint">有配图时选择包含 Markdown 与图片的 ZIP 资料包；无配图可直接选择 MD。导入后仅本学科组教师可见。</p></div>
        <div className="research-import-controls"><input aria-label="教师版资料文件" ref={fileInput} type="file" accept=".md,.zip" disabled={busy} onChange={e => setFile(e.target.files?.[0] ?? null)} /><button className="btn-pill" disabled={busy || !file} onClick={importFile}>{busy ? "处理中…" : "导入组内资料"}</button></div>
      </section>
      {error && <p className="error" role="alert">{error}</p>}
      {message && <p className="research-message" role="status">{message}</p>}
      <div className="research-tabs" aria-label="资料类型筛选">{([['all', '全部资料'], ['source', '教师素材'], ['lesson-plan', '共享教案']] as const).map(([key, label]) => <button key={key} className={`btn-pill ${filter === key ? '' : 'ghost'}`} aria-pressed={filter === key} disabled={busy} onClick={() => setFilter(key)}>{label}</button>)}</div>
      <div className="research-columns">
        <aside className="research-source-list">
          <h3>组内教师版 <span className="hint">{visibleItems.length} 份</span></h3>
          {loading && <p className="hint">资料加载中…</p>}
          {!loading && !visibleItems.length && <p className="hint">{filter === 'lesson-plan' ? '暂无共享教案，教师可在智能备课定稿后主动发布。' : '暂无此类资料。'}</p>}
          {visibleItems.map(row => <button key={row.id} className={`card research-source ${detail?.id === row.id ? "selected" : ""}`} disabled={busy} onClick={() => { setMessage(""); void select(row.id); }}>
            <strong>{row.filename}</strong><span>{row.uploader_name ?? "教师"} · {row.asset_count} 张配图 · {row.chunk_count} 个索引片段</span><small>{row.kind === 'lesson-plan' ? `共享教案 · v${row.lesson_version}` : '教师素材'} · 组内可见</small>
          </button>)}
        </aside>
        <section className="card research-document">
          {!detail ? <div className="research-empty"><h3>选择组内资料</h3><p className="hint">查看教师版原稿，提取学生版题干，核对后选择要发布到的班级。</p></div> : <>
            <div className="research-toolbar"><h3>{detail.filename}</h3>{detail.kind === 'lesson-plan' ? <a className="btn-pill" href={`/teacher/lesson-prep?research_material_id=${detail.id}`}>使用此教案备课</a> : <button className="btn-pill" onClick={makeDraft} disabled={busy}>生成无答案学生版预览</button>}</div>
            <p className="hint">{detail.kind === 'lesson-plan' ? '完整教师教案的共享定稿，仅同学科教师可见。可作为新的备课素材，不能直接作为学生讲义发布。' : '此处按明确的题干与答案分区提取内容，发布前需核对正文与配图；未知格式会提示整理，不会直接复制教师版。'}</p>
            <div className="research-tabs"><button className={`btn-pill ${tab === "teacher" ? "" : "ghost"}`} onClick={() => setTab("teacher")}>教师版原稿</button>{detail.kind !== 'lesson-plan' && <button className={`btn-pill ${tab === "student" ? "" : "ghost"}`} disabled={!draft} onClick={() => setTab("student")}>学生版编辑与预览</button>}</div>
            {tab === "teacher" ? <><div className="lesson-actions"><PrintHandoutButton key={detail.id} contentRef={teacherPrintContent} title={detail.filename} disabled={busy} /><button className="btn-pill ghost sm" onClick={downloadTeacherBundle}>下载教师图文包</button></div><div ref={teacherPrintContent}><MarkdownAnswer text={detail.content} imageUrl={imageUrl} /></div>{!!detail.lesson_sources.length && <details className="lesson-sources"><summary>教案原始出处记录</summary>{detail.lesson_sources.map(source => <article key={source.ref}><strong>[{source.ref}] {source.filename} · {source.heading}</strong><p className="hint">原文第 {source.start_line}–{source.end_line} 行 · 指纹 {source.file_sha256.slice(0, 12)}…</p><pre>{source.excerpt}</pre></article>)}</details>}</> : <>
              <label className="hint" htmlFor="student-material-content">学生版内容（可修改，修改后需重新确认）</label>
              <textarea id="student-material-content" className="input research-editor" value={draft} disabled={busy} onChange={e => { setDraft(e.target.value); setReviewed(false); }} />
              <section className="research-publish"><h3>发布到任教班级</h3><div className="research-class-options">{classes.map(c => <label key={c.id}><input type="checkbox" disabled={busy} checked={classIds.includes(c.id)} onChange={e => setClassIds(old => e.target.checked ? [...old, c.id] : old.filter(id => id !== c.id))} />{c.name}</label>)}</div>
                {!classes.length && <p className="hint">暂无可发布的任教班级。</p>}
                <label className="research-review"><input type="checkbox" checked={reviewed} disabled={busy} onChange={e => setReviewed(e.target.checked)} />我已检查正文及配图，确认学生版不含答案和教师解析。</label>
                <button className="btn-pill" disabled={busy || !classIds.length || !reviewed || !draft.trim()} onClick={publish}>{busy ? "处理中…" : "发布学生版"}</button>
              </section>
              <div className="research-toolbar"><h3>学生将看到的讲义</h3><PrintHandoutButton key={`${detail.id}:${draft}`} contentRef={studentPrintContent} title={detail.filename.replace(/\.md$/i, "（学生版）.md")} disabled={busy || !draft.trim()} /></div>
              <p className="hint">在打印窗口选择“另存为 PDF”，即可保留公式和配图；建议使用 A4 纸张并关闭页眉和页脚。</p>
              <div ref={studentPrintContent}><MarkdownAnswer text={draft} imageUrl={imageUrl} /></div>
            </>}
            {!!detail.publications.length && <section className="research-published"><h3>发布记录</h3>{detail.publications.map(p => <p key={p.material_id}><a href={nav.materialHref(p.class_id, "teaching")}>{p.class_name} · 学生版 #{p.material_id}</a><span className="hint">　{new Date(p.created_at).toLocaleString("zh-CN")}</span></p>)}</section>}
          </>}
        </section>
      </div>
    </div>
  </AppShell>;
}

export default function ResearchLibraryPage() {
  return <AuthGate><Suspense fallback={<p>加载中…</p>}><Library /></Suspense></AuthGate>;
}
