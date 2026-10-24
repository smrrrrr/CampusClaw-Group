"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { LogoutButton } from "@/components/logout-button";
import MarkdownAnswer from "@/components/markdown-answer";
import { useTeacherNavigation } from "@/components/teacher-navigation";
import {
  api, ApiError, authenticatedFetch, streamGeneration,
  type QuizItemDTO, type QuizItemDetailDTO, type QuizPaperDTO, type QuizEventDTO,
  type ResearchMaterialDTO, type QuizGenerationDone,
} from "@/lib/api";

const TYPES: { key: string; label: string }[] = [
  { key: "single_choice", label: "单选题" },
  { key: "multiple_choice", label: "多选题" },
  { key: "true_false", label: "判断题" },
  { key: "fill_blank", label: "填空题" },
  { key: "short_answer", label: "解答题" },
];
const DIFFS: { key: string; label: string }[] = [
  { key: "easy", label: "易" }, { key: "medium", label: "中" }, { key: "hard", label: "难" },
];
const TYPE_NAME: Record<string, string> = Object.fromEntries(TYPES.map(t => [t.key, t.label]));
const DIFF_NAME: Record<string, string> = Object.fromEntries(DIFFS.map(d => [d.key, d.label]));
const STATUS_NAME: Record<string, string> = { pending: "待复核", approved: "已入库", rejected: "已驳回" };

type Tab = "generate" | "review" | "bank" | "papers";

function QuizWorkspace() {
  const nav = useTeacherNavigation();
  const [tab, setTab] = useState<Tab>("generate");
  const [kps, setKps] = useState<string[]>([]);
  const [materials, setMaterials] = useState<ResearchMaterialDTO[]>([]);
  const [classes, setClasses] = useState<{ id: number; name: string }[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api.quizKnowledgePoints().then(r => setKps(r.knowledge_points)).catch(e => setError(e instanceof ApiError ? e.message : "加载知识点失败"));
    api.listResearchMaterials().then(r => setMaterials(r.items)).catch(() => {});
    api.listClasses().then(setClasses).catch(() => {});
  }, []);

  return (
    <AppShell brandMark="T" subtitle="智能教学平台 · 教师端" navItems={nav.navItems} navHeader={nav.navHeader}
      active="lesson-quiz" onNavigate={nav.onNavigate} navFoot="CampusClaw · 教师工作空间" headerRight={<LogoutButton />}>
      <div className="page-title">
        <h2>智能命题</h2>
        <p>{nav.subjectName}教研组 · 生成 → 逐题复核 → 学科题库 → 组卷与发布</p>
      </div>
      <div className="tabs quiz-tabs">
        {([["generate", "生成命题"], ["review", "待复核"], ["bank", "学科题库"], ["papers", "组卷与发布"]] as [Tab, string][]).map(([k, label]) =>
          <button key={k} className={tab === k ? "active" : ""} onClick={() => { setTab(k); setError(""); setMessage(""); }}>{label}</button>)}
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      {message && <div className="success" role="status">{message}</div>}
      {tab === "generate" && <GenerateTab kps={kps} materials={materials} onDone={() => { setMessage("生成完成，请到「待复核」逐题核对。"); }} setError={setError} />}
      {tab === "review" && <ItemsTab mode="review" setError={setError} setMessage={setMessage} />}
      {tab === "bank" && <ItemsTab mode="bank" setError={setError} setMessage={setMessage} />}
      {tab === "papers" && <PapersTab classes={classes} setError={setError} setMessage={setMessage} />}
    </AppShell>
  );
}

// ---------------- 生成命题 ----------------
function GenerateTab({ kps, materials, onDone, setError }: { kps: string[]; materials: ResearchMaterialDTO[]; onDone: () => void; setError: (s: string) => void }) {
  const [selectedMaterials, setSelectedMaterials] = useState<number[]>([]);
  const [selectedKps, setSelectedKps] = useState<string[]>([]);
  const [typeCounts, setTypeCounts] = useState<Record<string, number>>(Object.fromEntries(TYPES.map(t => [t.key, 0])));
  const [diffCounts, setDiffCounts] = useState<Record<string, number>>(Object.fromEntries(DIFFS.map(d => [d.key, 0])));
  const [requirements, setRequirements] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<QuizGenerationDone | null>(null);
  const [interrupted, setInterrupted] = useState(false);

  const typeTotal = Object.values(typeCounts).reduce((a, b) => a + b, 0);
  const diffTotal = Object.values(diffCounts).reduce((a, b) => a + b, 0);

  const toggle = <T,>(arr: T[], v: T) => arr.includes(v) ? arr.filter(x => x !== v) : [...arr, v];

  const generate = async () => {
    setError(""); setResult(null); setInterrupted(false);
    if (selectedMaterials.length < 1 || selectedMaterials.length > 5) { setError("请选择 1–5 份本学科资料"); return; }
    if (selectedKps.length < 1 || selectedKps.length > 5) { setError("请选择 1–5 个考查知识点"); return; }
    if (typeTotal !== diffTotal || typeTotal < 1 || typeTotal > 20) { setError("题型合计须等于难度合计，且为 1–20"); return; }
    setBusy(true); setProgress(0);
    await streamGeneration({
      research_material_ids: selectedMaterials, knowledge_points: selectedKps,
      type_counts: typeCounts, difficulty_counts: diffCounts, requirements,
    }, {
      onProgress: (c) => setProgress(c),
      onDone: (d) => { setResult(d); setBusy(false); onDone(); },
      onError: (m) => { setError(m); setBusy(false); setInterrupted(true); },
    });
    setBusy(false);
  };

  return (
    <div className="quiz-grid">
      <section className="panel">
        <h3>1. 选择本学科资料（1–5 份）</h3>
        <div className="quiz-checks">{materials.map(m => <label key={m.id}><input type="checkbox" checked={selectedMaterials.includes(m.id)} onChange={() => setSelectedMaterials(a => toggle(a, m.id))} />{m.filename}</label>)}</div>
        <h3>2. 考查知识点（1–5 个）</h3>
        <div className="quiz-checks">{kps.map(k => <label key={k}><input type="checkbox" checked={selectedKps.includes(k)} onChange={() => setSelectedKps(a => toggle(a, k))} />{k}</label>)}</div>
      </section>
      <section className="panel">
        <h3>3. 题型与难度</h3>
        <table className="quiz-table"><thead><tr><th>题型</th><th>题数</th></tr></thead><tbody>
          {TYPES.map(t => <tr key={t.key}><td>{t.label}</td><td><input type="number" min={0} max={10} value={typeCounts[t.key]} onChange={e => setTypeCounts({ ...typeCounts, [t.key]: Number(e.target.value) || 0 })} /></td></tr>)}
          <tr className="quiz-sum"><td>合计</td><td>{typeTotal}</td></tr>
        </tbody></table>
        <table className="quiz-table"><thead><tr><th>难度</th><th>题数</th></tr></thead><tbody>
          {DIFFS.map(d => <tr key={d.key}><td>{d.label}</td><td><input type="number" min={0} max={20} value={diffCounts[d.key]} onChange={e => setDiffCounts({ ...diffCounts, [d.key]: Number(e.target.value) || 0 })} /></td></tr>)}
          <tr className="quiz-sum"><td>合计</td><td className={typeTotal !== diffTotal ? "wrong" : ""}>{diffTotal}</td></tr>
        </tbody></table>
        <label className="quiz-label">补充要求（可选）</label>
        <textarea className="input" rows={3} value={requirements} onChange={e => setRequirements(e.target.value)} placeholder="例如：侧重计算题，难度中等偏上" />
        <p className="hint">点击生成会把所选资料片段与命题要求发送给已配置的 DeepSeek；配图只发送路径，不发送图片本体。</p>
        <button className="btn-pill" disabled={busy} onClick={generate}>{busy ? `生成中…（${progress} 字）` : "生成命题"}</button>
      </section>
      {(result || interrupted) && <section className="panel quiz-result">
        <h3>生成结果</h3>
        {interrupted && <p className="hint wrong">生成中断或失败，表单已保留，可直接重试。</p>}
        {result && <>
          <p>通过 <strong>{result.accepted_ids.length}</strong> 题，未通过 <strong>{result.rejected.length}</strong> 题，待补充 <strong>{result.gaps.length}</strong> 项。</p>
          {result.rejected.length > 0 && <div className="quiz-rejected"><h4>未通过</h4>{result.rejected.map(r => <p key={r.index}>第 {r.index + 1} 题：{r.reasons.join("；")}</p>)}</div>}
          {result.gaps.length > 0 && <div className="quiz-gaps"><h4>待补充</h4>{result.gaps.map((g, i) => <p key={i}>{TYPE_NAME[g.type ?? ""] ?? g.type} · {DIFF_NAME[g.difficulty ?? ""] ?? g.difficulty} · {g.knowledge_point ?? ""}：{g.reason ?? ""}</p>)}</div>}
        </>}
      </section>}
    </div>
  );
}

// ---------------- 待复核 / 学科题库 ----------------
function ItemsTab({ mode, setError, setMessage }: { mode: "review" | "bank"; setError: (s: string) => void; setMessage: (s: string) => void }) {
  const [items, setItems] = useState<QuizItemDTO[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ type: "", difficulty: "", knowledge_point: "", q: "", archived: "" });
  const [detail, setDetail] = useState<QuizItemDetailDTO | null>(null);
  const [edit, setEdit] = useState<{ stem: string; explanation: string; options: { label: string; text: string }[]; answer: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const load = async () => {
    setError("");
    try {
      const params: Record<string, string | number | undefined> = { page, type: filters.type, difficulty: filters.difficulty, knowledge_point: filters.knowledge_point, q: filters.q };
      if (mode === "review") params.status = "pending";
      if (mode === "bank") { params.status = "approved"; if (filters.archived) params.archived = filters.archived; }
      const r = await api.listQuizItems(params);
      setItems(r.items); setTotal(r.total);
    } catch (e) { setError(e instanceof ApiError ? e.message : "加载失败"); }
  };
  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [page, filters, mode]);

  const open = async (id: number) => {
    try { setDetail(await api.getQuizItem(id)); setEdit(null); setRejectReason(""); } catch (e) { setError(e instanceof ApiError ? e.message : "加载详情失败"); }
  };

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setError("");
    try { await fn(); setMessage(ok); setDetail(null); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "操作失败"); }
    finally { setBusy(false); }
  };

  const beginEdit = (d: QuizItemDetailDTO) => setEdit({
    stem: d.stem, explanation: d.explanation,
    options: d.options.map(o => ({ ...o })), answer: answerToText(d.type, d.answer),
  });

  return (
    <div className="quiz-grid">
      <section className="panel">
        <div className="quiz-filters">
          <select value={filters.type} onChange={e => setFilters({ ...filters, type: e.target.value })}><option value="">全部题型</option>{TYPES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
          <select value={filters.difficulty} onChange={e => setFilters({ ...filters, difficulty: e.target.value })}><option value="">全部难度</option>{DIFFS.map(d => <option key={d.key} value={d.key}>{d.label}</option>)}</select>
          <input className="input" placeholder="知识点" value={filters.knowledge_point} onChange={e => setFilters({ ...filters, knowledge_point: e.target.value })} />
          <input className="input" placeholder="关键字" value={filters.q} onChange={e => setFilters({ ...filters, q: e.target.value })} />
          {mode === "bank" && <select value={filters.archived} onChange={e => setFilters({ ...filters, archived: e.target.value })}><option value="">未下架</option><option value="true">仅看已下架</option></select>}
        </div>
        <p className="hint">共 {total} 题，第 {page} 页（每页最多 50）</p>
        {items.length === 0 ? <p className="hint">{mode === "review" ? "没有待复核题目。" : "题库暂无题目。"}</p> :
          <div className="quiz-items">{items.map(it => <article key={it.id} className="quiz-item-card">
            <div className="quiz-item-top"><strong># {it.id} · {TYPE_NAME[it.type]} · {DIFF_NAME[it.difficulty]}</strong>
              <span className={`quiz-status ${it.status}`}>{STATUS_NAME[it.status]}{it.archived ? " · 已下架" : ""}</span></div>
            <div className="quiz-item-stem"><MarkdownAnswer text={it.stem} imageUrl={quizImageUrl} /></div>
            <button className="btn-pill ghost sm" onClick={() => open(it.id)}>查看详情 / 操作</button>
          </article>)}</div>}
        <div className="quiz-pager">
          <button className="btn-pill ghost sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>上一页</button>
          <button className="btn-pill ghost sm" disabled={page * 50 >= total} onClick={() => setPage(p => p + 1)}>下一页</button>
        </div>
      </section>

      {detail && <section className="panel quiz-detail">
        <div className="quiz-item-top"><h3>题目 #{detail.id}</h3><button className="btn-pill ghost sm" onClick={() => setDetail(null)}>关闭</button></div>
        <p className="hint">{TYPE_NAME[detail.type]} · {DIFF_NAME[detail.difficulty]} · {detail.status === "approved" ? "已入库" : STATUS_NAME[detail.status]} · 出处状态：{detail.source_status === "consistent" ? "一致" : detail.source_status === "changed" ? "原稿已变化" : detail.source_status === "deleted" ? "原稿已删除" : "无"}</p>
        {edit ? <>
          <label className="quiz-label">题干</label>
          <textarea className="input" rows={4} value={edit.stem} onChange={e => setEdit({ ...edit, stem: e.target.value })} />
          {detail.type === "single_choice" || detail.type === "multiple_choice" ? <>
            <label className="quiz-label">选项</label>
            {edit.options.map((o, i) => <div key={i}><input className="input" value={o.text} onChange={e => { const os = [...edit.options]; os[i] = { ...os[i], text: e.target.value }; setEdit({ ...edit, options: os }); }} /></div>)}
          </> : null}
          <label className="quiz-label">答案{ANSWER_HINT[detail.type] ? `（${ANSWER_HINT[detail.type]}）` : ""}</label>
          {detail.type === "true_false"
            ? <select value={edit.answer} onChange={e => setEdit({ ...edit, answer: e.target.value })}><option value="true">正确</option><option value="false">错误</option></select>
            : detail.type === "fill_blank" || detail.type === "short_answer"
              ? <textarea className="input" rows={detail.type === "fill_blank" ? 3 : 4} value={edit.answer} onChange={e => setEdit({ ...edit, answer: e.target.value })} />
              : <input className="input" value={edit.answer} onChange={e => setEdit({ ...edit, answer: e.target.value })} />}
          <label className="quiz-label">解析</label>
          <textarea className="input" rows={3} value={edit.explanation} onChange={e => setEdit({ ...edit, explanation: e.target.value })} />
          <button className="btn-pill" disabled={busy} onClick={() => run(() => api.updateQuizItem(detail.id, {
            revision: detail.revision, stem: edit.stem, explanation: edit.explanation,
            options: edit.options, answer: textToAnswer(detail.type, edit.answer),
            knowledge_points: detail.knowledge_points, source_refs: detail.sources.map(s => s.ref),
          }), "已保存，仍为待复核。")}>保存修改</button>
        </> : <>
          <div className="quiz-item-stem"><MarkdownAnswer text={detail.stem} imageUrl={quizImageUrl} /></div>
          {detail.options.length > 0 && <ul className="quiz-options">{detail.options.map(o => <li key={o.label}><b>{o.label}.</b> <MarkdownAnswer text={o.text} imageUrl={quizImageUrl} /></li>)}</ul>}
          {detail.type === "fill_blank" || detail.type === "short_answer"
            ? <div className="quiz-answer"><b>答案：</b><MarkdownAnswer text={formatAnswer(detail.answer)} imageUrl={quizImageUrl} /></div>
            : <p><b>答案：</b>{formatAnswer(detail.answer)}</p>}
          <div><b>解析：</b><MarkdownAnswer text={detail.explanation} /></div>
          <details className="quiz-sources"><summary>出处快照（{detail.sources.length}）</summary>
            {detail.sources.map(s => <article key={s.ref}><strong>[{s.ref}] {s.filename} 第 {s.start_line}–{s.end_line} 行</strong><pre>{s.excerpt}</pre></article>)}
          </details>
          {detail.events && detail.events.length > 0 && <details className="quiz-events"><summary>复核历史</summary><ul>{detail.events.map((e, i) => <li key={i}>{e.action} · {e.created_at ? new Date(e.created_at).toLocaleString("zh-CN") : ""}</li>)}</ul></details>}
          <div className="quiz-actions">
            {detail.status === "pending" && <>
              <button className="btn-pill" disabled={busy} onClick={() => run(() => api.approveQuizItem(detail.id, detail.revision), "已通过并入库。")}>确认已核对，通过</button>
              <button className="btn-pill ghost sm" disabled={busy} onClick={() => beginEdit(detail)}>修改</button>
              <input className="input" placeholder="驳回原因（可选）" value={rejectReason} onChange={e => setRejectReason(e.target.value)} />
              <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.rejectQuizItem(detail.id, detail.revision, rejectReason), "已驳回。")}>驳回</button>
              <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.deleteQuizItem(detail.id), "已删除。")}>删除</button>
            </>}
            {detail.status === "approved" && <>
              <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.copyQuizItem(detail.id), "已复制为新候选（待复核）。")}>复制为新候选</button>
              {!detail.can_archive
                ? <span className="hint">仅原作者可下架 / 恢复</span>
                : detail.archived
                ? <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.restoreQuizItem(detail.id, detail.revision), "已恢复。")}>恢复</button>
                : <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.archiveQuizItem(detail.id, detail.revision), "已下架。")}>下架</button>}
            </>}
            {detail.status === "rejected" && <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.deleteQuizItem(detail.id), "已删除。")}>删除</button>}
          </div>
        </>}
      </section>}
    </div>
  );
}

// 编辑框里的答案文本与接口答案类型互转：多选用逗号分隔，填空每行一空，判断用 true / false
const ANSWER_HINT: Record<string, string> = {
  single_choice: "填写一个选项字母", multiple_choice: "填写 2–4 个选项字母，用逗号分隔", fill_blank: "每行一个空，按空位顺序",
};
function answerToText(type: string, a: unknown): string {
  if (type === "true_false") return a === true ? "true" : "false";
  if (Array.isArray(a)) return a.join(type === "fill_blank" ? "\n" : ",");
  return String(a ?? "");
}
function textToAnswer(type: string, text: string): unknown {
  if (type === "true_false") return text === "true";
  if (type === "multiple_choice") return text.split(/[,，、\s]+/).map(s => s.trim().toUpperCase()).filter(Boolean);
  if (type === "fill_blank") return text.split("\n").map(s => s.trim()).filter(Boolean);
  if (type === "single_choice") return text.trim().toUpperCase();
  return text;
}
// 题目与学生卷中的配图写作 sources/<资料编号>/<原图名>，教师端按原资料取图
function quizImageUrl(src: string): string {
  const m = /^sources\/(\d+)\/(.+)$/.exec(src);
  return m ? api.researchAssetUrl(Number(m[1]), m[2]) : src;
}
function formatAnswer(a: unknown): string {
  if (typeof a === "boolean") return a ? "正确" : "错误";
  if (Array.isArray(a)) return a.join("、");
  return String(a);
}

// ---------------- 组卷与发布 ----------------
function PapersTab({ classes, setError, setMessage }: { classes: { id: number; name: string }[]; setError: (s: string) => void; setMessage: (s: string) => void }) {
  const [papers, setPapers] = useState<QuizPaperDTO[]>([]);
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState(90);
  const [groups, setGroups] = useState<{ type: string; count: number; score: number }[]>([{ type: "single_choice", count: 10, score: 5 }]);
  const [pct, setPct] = useState({ easy: 30, medium: 50, hard: 20 });
  const [kps, setKps] = useState<string[]>([]);
  const [selKps, setSelKps] = useState<string[]>([]);
  const [gaps, setGaps] = useState<{ type: string; difficulty: string; needed: number; available: number }[]>([]);
  const [detail, setDetail] = useState<QuizPaperDTO | null>(null);
  const [preview, setPreview] = useState("");
  const [targets, setTargets] = useState<number[]>([]);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [draftDirty, setDraftDirty] = useState(false);

  useEffect(() => { api.quizKnowledgePoints().then(r => setKps(r.knowledge_points)).catch(() => {}); load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);
  const load = () => api.listQuizPapers().then(r => setPapers(r.items)).catch(e => setError(e instanceof ApiError ? e.message : "加载试卷失败"));

  const totalItems = groups.reduce((a, g) => a + g.count, 0);
  const totalScore = groups.reduce((a, g) => a + g.count * g.score, 0);

  const compose = async () => {
    setError(""); setGaps([]);
    if (pct.easy + pct.medium + pct.hard !== 100) { setError("易/中/难百分比合计必须为 100"); return; }
    if (selKps.length < 1) { setError("请至少选择一个知识点"); return; }
    setBusy(true);
    try {
      const p = await api.createQuizPaper({ title, duration, knowledge_points: selKps, groups, difficulty_pct: pct });
      setMessage(`已生成试卷「${p.title}」：${p.item_count} 题，总分 ${p.total_score}。`); setTitle(""); await load();
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        try { const d = JSON.parse(e.message); setGaps(d.gaps ?? (typeof d === "object" ? d.gaps : [])); } catch { setError(e.message); }
        if (!gaps.length) setError("题库不足，无法组卷");
      } else setError(e instanceof ApiError ? e.message : "组卷失败");
    } finally { setBusy(false); }
  };

  const openPaper = async (id: number) => {
    try { const p = await api.getQuizPaper(id); setDetail(p); setPreview(""); setReviewed(false); setTargets([]); }
    catch (e) { setError(e instanceof ApiError ? e.message : "加载试卷失败"); }
  };

  const loadPreview = async (id: number) => {
    try {
      const res = await authenticatedFetch(api.quizPaperPreviewUrl(id));
      setPreview(await res.text());
    } catch (e) { setError(e instanceof ApiError ? e.message : "预览失败"); }
  };

  // 答案卷必须带 Bearer 下载：裸 <a href> 不会带 Authorization，后端只会返回 401。
  const downloadAnswerKey = async (id: number, title: string) => {
    try {
      const res = await authenticatedFetch(api.quizPaperAnswerKeyUrl(id));
      const url = URL.createObjectURL(await res.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `${title}（答案卷）.md`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) { setError(e instanceof ApiError ? e.message : "下载答案卷失败"); }
  };

  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true); setError("");
    try { await fn(); setMessage(ok); if (detail) setDetail(await api.getQuizPaper(detail.id)); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "操作失败"); }
    finally { setBusy(false); }
  };

  return (
    <div className="quiz-grid">
      <section className="panel">
        <h3>新建试卷蓝图</h3>
        <label className="quiz-label">标题</label>
        <input className="input" value={title} onChange={e => setTitle(e.target.value)} placeholder="例如：立体几何单元测验" />
        <label className="quiz-label">时长（分钟）</label>
        <input type="number" className="input" min={10} max={180} value={duration} onChange={e => setDuration(Number(e.target.value) || 90)} />
        <label className="quiz-label">知识点范围（1–5）</label>
        <div className="quiz-checks">{kps.map(k => <label key={k}><input type="checkbox" checked={selKps.includes(k)} onChange={() => setSelKps(a => a.includes(k) ? a.filter(x => x !== k) : [...a, k])} />{k}</label>)}</div>
        <label className="quiz-label">题型分组</label>
        {groups.map((g, i) => <div key={i} className="quiz-group-row">
          <select value={g.type} onChange={e => { const gs = [...groups]; gs[i] = { ...gs[i], type: e.target.value }; setGroups(gs); }}>{TYPES.map(t => <option key={t.key} value={t.key}>{t.label}</option>)}</select>
          <input type="number" min={1} max={20} value={g.count} onChange={e => { const gs = [...groups]; gs[i] = { ...gs[i], count: Number(e.target.value) || 1 }; setGroups(gs); }} />
          <input type="number" min={0.5} max={100} step={0.5} value={g.score} onChange={e => { const gs = [...groups]; gs[i] = { ...gs[i], score: Number(e.target.value) || 0.5 }; setGroups(gs); }} />
          <button className="btn-pill ghost sm" onClick={() => setGroups(groups.filter((_, j) => j !== i))}>删除</button>
        </div>)}
        <button className="btn-pill ghost sm" onClick={() => setGroups([...groups, { type: "single_choice", count: 5, score: 5 }])}>＋ 增加分组</button>
        <label className="quiz-label">易 / 中 / 难 百分比</label>
        <div className="quiz-pct">
          {DIFFS.map(d => <span key={d.key}>{d.label} <input type="number" min={0} max={100} value={pct[d.key as keyof typeof pct]} onChange={e => setPct({ ...pct, [d.key]: Number(e.target.value) || 0 })} /></span>)}
          <span className={pct.easy + pct.medium + pct.hard !== 100 ? "wrong" : ""}>合计 {pct.easy + pct.medium + pct.hard}%</span>
        </div>
        <p className="hint">全卷 {totalItems} 题，总分 {totalScore}（上限 50 题）</p>
        <button className="btn-pill" disabled={busy || !title.trim()} onClick={compose}>{busy ? "组卷中…" : "按蓝图组卷"}</button>
        {gaps.length > 0 && <div className="quiz-gaps"><h4>题库不足，缺口如下（未创建试卷）</h4>
          <table className="quiz-table"><thead><tr><th>题型</th><th>难度</th><th>需要</th><th>可用</th></tr></thead><tbody>
            {gaps.map((g, i) => <tr key={i}><td>{TYPE_NAME[g.type] ?? g.type}</td><td>{DIFF_NAME[g.difficulty] ?? g.difficulty}</td><td>{g.needed}</td><td>{g.available}</td></tr>)}
          </tbody></table></div>}
        <h3>我的试卷</h3>
        {papers.length === 0 ? <p className="hint">暂无试卷。</p> : <ul className="quiz-papers">{papers.map(p => <li key={p.id}>
          <button className="linklike" onClick={() => openPaper(p.id)}>{p.title}</button>
          <span>{p.status === "final" ? "已定稿" : "草稿"} · {p.item_count} 题 · {p.total_score} 分</span>
        </li>)}</ul>}
      </section>

      {detail && <section className="panel quiz-detail">
        <div className="quiz-item-top"><h3>{detail.title}</h3><button className="btn-pill ghost sm" onClick={() => setDetail(null)}>关闭</button></div>
        <p className="hint">{detail.status === "final" ? "已定稿（只读）" : "草稿"} · {detail.item_count} 题 · 总分 {detail.total_score} · 时长 {detail.duration} 分钟</p>
        {detail.status === "draft"
          ? <DraftEditor paper={detail} busy={busy} onDirty={setDraftDirty} onSave={items => run(() => api.updateQuizPaper(detail.id, { revision: detail.revision, items }), "草稿已保存。")} setError={setError} />
          : <ol className="quiz-paper-items">{(detail.items ?? []).map(it => <li key={it.question_item_id}><span className="hint">[{TYPE_NAME[it.snapshot.type]}] {it.score} 分</span><MarkdownAnswer text={it.snapshot.stem} imageUrl={quizImageUrl} /></li>)}</ol>}
        <div className="quiz-actions">
          {detail.status === "draft" && <button className="btn-pill" disabled={busy || draftDirty} title={draftDirty ? "请先保存或放弃草稿修改" : undefined} onClick={() => run(() => api.finalizeQuizPaper(detail.id, detail.revision), "已定稿，试卷只读。")}>定稿</button>}
          <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.copyQuizPaper(detail.id), "已复制为新草稿。")}>复制为新草稿</button>
          <button className="btn-pill ghost sm" onClick={() => loadPreview(detail.id)}>预览学生卷</button>
          <button className="btn-pill ghost sm" onClick={() => downloadAnswerKey(detail.id, detail.title)}>下载答案卷</button>
          {detail.status === "draft" && <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(() => api.deleteQuizPaper(detail.id), "已删除草稿。")}>删除</button>}
        </div>
        {preview && <div className="quiz-preview"><h4>学生卷预览</h4><MarkdownAnswer text={preview} imageUrl={quizImageUrl} /></div>}
        {detail.status === "final" && <div className="research-publish">
          <h4>发布到任教班级</h4>
          <div className="research-class-options">{classes.map(c => <label key={c.id}><input type="checkbox" checked={targets.includes(c.id)} onChange={e => setTargets(t => e.target.checked ? [...t, c.id] : t.filter(x => x !== c.id))} />{c.name}</label>)}</div>
          <label className="research-review"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />我已核对当前学生卷不含答案、解析与出处</label>
          <button className="btn-pill" disabled={busy || !reviewed || targets.length === 0} onClick={() => run(() => api.publishQuizPaper(detail.id, detail.revision, targets), "试卷已发布到所选班级。")}>发布试卷</button>
        </div>}
      </section>}
    </div>
  );
}

// 草稿编辑：替换、删除、上下移动、改分值，保存时整卷提交并携带 revision
type DraftItem = { question_item_id: number; score: number; type: string; stem: string };

function DraftEditor({ paper, busy, onSave, onDirty, setError }: {
  paper: QuizPaperDTO; busy: boolean; setError: (s: string) => void; onDirty: (dirty: boolean) => void;
  onSave: (items: { question_item_id: number; score: number }[]) => void;
}) {
  const initial = (): DraftItem[] => (paper.items ?? []).map(it => ({
    question_item_id: it.question_item_id, score: it.score, type: it.snapshot.type, stem: it.snapshot.stem,
  }));
  const [items, setItems] = useState<DraftItem[]>(initial);
  const [replacing, setReplacing] = useState<number | null>(null);
  const [candidates, setCandidates] = useState<QuizItemDTO[]>([]);
  // 服务端保存后 revision 变化，重新以服务端内容为准
  useEffect(() => { setItems(initial()); setReplacing(null); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [paper.id, paper.revision]);

  const dirty = JSON.stringify(items.map(i => [i.question_item_id, i.score])) !== JSON.stringify(initial().map(i => [i.question_item_id, i.score]));
  useEffect(() => { onDirty(dirty); return () => onDirty(false); }, [dirty, onDirty]);
  const total = items.reduce((a, i) => a + i.score, 0);
  const scoreOk = (s: number) => s >= 0.5 && s <= 100 && Math.round(s * 2) === s * 2;

  const move = (i: number, d: number) => setItems(xs => { const ys = [...xs]; [ys[i], ys[i + d]] = [ys[i + d], ys[i]]; return ys; });
  const startReplace = async (i: number) => {
    setError(""); setReplacing(i); setCandidates([]);
    try {
      const r = await api.listQuizItems({ status: "approved", type: items[i].type });
      const used = new Set(items.map(x => x.question_item_id));
      setCandidates(r.items.filter(c => !c.archived && !used.has(c.id)));
    } catch (e) { setError(e instanceof ApiError ? e.message : "加载可替换题目失败"); }
  };
  const replace = (i: number, c: QuizItemDTO) => {
    setItems(xs => xs.map((x, j) => j === i ? { ...x, question_item_id: c.id, type: c.type, stem: c.stem } : x));
    setReplacing(null);
  };

  return <>
    <ol className="quiz-paper-items">{items.map((it, i) => <li key={it.question_item_id}>
      <div className="quiz-draft-row">
        <span className="hint">[{TYPE_NAME[it.type]}] #{it.question_item_id}</span>
        <input type="number" min={0.5} max={100} step={0.5} value={it.score} className={scoreOk(it.score) ? "" : "wrong"}
          onChange={e => { const v = Number(e.target.value); setItems(xs => xs.map((x, j) => j === i ? { ...x, score: v } : x)); }} /> 分
        <button className="btn-pill ghost sm" disabled={i === 0} onClick={() => move(i, -1)}>上移</button>
        <button className="btn-pill ghost sm" disabled={i === items.length - 1} onClick={() => move(i, 1)}>下移</button>
        <button className="btn-pill ghost sm" onClick={() => startReplace(i)}>替换</button>
        <button className="btn-pill ghost sm" disabled={items.length <= 1} onClick={() => setItems(xs => xs.filter((_, j) => j !== i))}>删除</button>
      </div>
      <MarkdownAnswer text={it.stem} imageUrl={quizImageUrl} />
      {replacing === i && <div className="quiz-replace">
        <p className="hint">从本学科已入库、未下架的同题型题目中选择（已在卷中的题目不列出）：</p>
        {candidates.length === 0 ? <p className="hint">没有可替换的题目。</p> :
          candidates.map(c => <div key={c.id} className="quiz-replace-option">
            <button className="btn-pill ghost sm" onClick={() => replace(i, c)}>选用 #{c.id} · {DIFF_NAME[c.difficulty]}</button>
            <MarkdownAnswer text={c.stem} imageUrl={quizImageUrl} />
          </div>)}
        <button className="btn-pill ghost sm" onClick={() => setReplacing(null)}>取消</button>
      </div>}
    </li>)}</ol>
    <p className="hint">编辑后 {items.length} 题 · 总分 {total}{dirty ? " · 有未保存的修改" : ""}</p>
    <div className="quiz-actions">
      <button className="btn-pill ghost sm" disabled={busy || !dirty || !items.every(i => scoreOk(i.score))}
        onClick={() => onSave(items.map(i => ({ question_item_id: i.question_item_id, score: i.score })))}>保存草稿修改</button>
      <button className="btn-pill ghost sm" disabled={busy || !dirty} onClick={() => setItems(initial())}>放弃修改</button>
    </div>
  </>;
}

export default function QuizPage() {
  return <AuthGate><Suspense fallback={<p>加载中…</p>}><QuizWorkspace /></Suspense></AuthGate>;
}
