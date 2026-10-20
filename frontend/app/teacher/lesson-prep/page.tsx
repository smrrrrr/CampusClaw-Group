"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { AuthGate } from '@/components/auth-guard';
import { AppShell } from '@/components/app-layout';
import { LogoutButton } from '@/components/logout-button';
import MarkdownAnswer from '@/components/markdown-answer';
import { PrintHandoutButton } from '@/components/print-handout-button';
import { useTeacherNavigation } from '@/components/teacher-navigation';
import { api, ResearchMaterialDTO } from '@/lib/api';
import { lessonApi, streamLesson, LessonPlan, LessonSummary, LessonForm, LessonResources } from '@/lib/lesson-api';

const STATUS = { draft: '草稿', reviewed: '已审阅', final: '已定稿' };
const EMPTY: LessonForm = { class_id: 0, topic: '', duration: 45, scope: '', curriculum_standards: '', class_profile: '', requirements: '', research_material_ids: [] };

function LessonWorkspace() {
  const nav = useTeacherNavigation();
  const requestedMaterial = Number(useSearchParams().get('research_material_id'));
  const [classes, setClasses] = useState<{ id: number; name: string }[]>([]);
  const [materials, setMaterials] = useState<ResearchMaterialDTO[]>([]);
  const [items, setItems] = useState<LessonSummary[]>([]);
  const [form, setForm] = useState<LessonForm>(EMPTY);
  const [plan, setPlan] = useState<LessonPlan | null>(null);
  const [teacherText, setTeacherText] = useState('');
  const [studentLesson, setStudentLesson] = useState('');
  const [handout, setHandout] = useState('');
  const [tab, setTab] = useState<'teacher' | 'lesson' | 'handout'>('teacher');
  const [version, setVersion] = useState<number | null>(null);
  const [rewriteHeading, setRewriteHeading] = useState('');
  const [rewriteInstructions, setRewriteInstructions] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [studentReviewed, setStudentReviewed] = useState(false);
  const [targets, setTargets] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState('');
  const [streamText, setStreamText] = useState('');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [booted, setBooted] = useState(false);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const contentRef = useRef<HTMLDivElement>(null);

  const adopt = (row: LessonPlan) => {
    setPlan(row); setTeacherText(row.content); setStudentLesson(row.student_lesson); setHandout(row.student_handout);
    setReviewed(false); setStudentReviewed(false); setVersion(null); setTargets([]);
    setRewriteHeading('');
  };
  const refreshList = async () => { setItems((await lessonApi.list()).items); };
  useEffect(() => {
    let cancelled = false;
    Promise.all([api.listClasses(), api.listResearchMaterials(), lessonApi.list()]).then(([c, m, p]) => {
      if (cancelled) return;
      setClasses(c); setMaterials(m.items); setItems(p.items);
      setForm(old => ({ ...old, class_id: c[0]?.id ?? 0, research_material_ids: m.items.some(item => item.id === requestedMaterial) ? [requestedMaterial] : old.research_material_ids })); setBooted(true);
    }).catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; sequence.current++; controller.current?.abort(); };
  }, [requestedMaterial]);
  const teacherDirty = !!plan && teacherText !== plan.content;
  const studentDirty = !!plan && (studentLesson !== plan.student_lesson || handout !== plan.student_handout);
  useEffect(() => {
    if (!teacherDirty && !studentDirty && !busy) return;
    const handler = (e: BeforeUnloadEvent) => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [teacherDirty, studentDirty, busy]);

  const discard = () => !(teacherDirty || studentDirty) || window.confirm('当前修改尚未保存，确定离开当前教案吗？');
  const select = async (id: number) => {
    if (busy || !discard()) return;
    const request = ++sequence.current; setBusy(true); setError(''); setMessage('');
    try { const row = await lessonApi.get(id); if (request === sequence.current) { adopt(row); setTab('teacher'); setStreamText(''); } }
    catch (e) { setError((e as Error).message); }
    finally { if (request === sequence.current) setBusy(false); }
  };
  const run = async (action: () => Promise<void>) => {
    if (busy) return;
    setBusy(true); setError(''); setMessage('');
    try { await action(); await refreshList(); }
    catch (e) { setError((e as Error).message); setStreamText(''); }
    finally { setBusy(false); setProgress(''); }
  };
  const generate = async () => {
    if (!form.topic.trim() || !form.class_id || !form.research_material_ids.length || !discard()) return;
    await run(async () => {
      controller.current = new AbortController(); setProgress('正在依据所选资料生成教师教案…'); setStreamText('');
      const row = await streamLesson('/generate', form, { signal: controller.current.signal, onDelta: delta => setStreamText(old => old + delta) });
      adopt(row); setTab('teacher'); setStreamText(''); setMessage('教师草稿已保存，请核对正文、公式与来源。');
    });
  };
  const mutate = (action: (p: LessonPlan) => Promise<LessonPlan>, text: string) => run(async () => {
    if (!plan) return;
    adopt(await action(plan)); setMessage(text);
  });
  const makeStudents = () => run(async () => {
    if (!plan || !discard()) return;
    if ((plan.student_lesson || plan.student_handout) && !window.confirm('重新生成将替换当前已保存的两份学生稿，已发布资料保留。确定继续吗？')) return;
    controller.current = new AbortController(); setProgress('正在生成学生可见教案与配套讲义…');
    const row = await streamLesson(`/${plan.id}/student-drafts`, { revision: plan.revision }, {
      signal: controller.current.signal, onProgress: setProgress,
    });
    adopt(row); setTab('lesson'); setMessage('两份学生稿已保存。请逐份检查是否有答案或教师提示，确认后再发布。');
  });
  const publish = () => run(async () => {
    if (!plan || !targets.length || !studentReviewed || studentDirty || tab === 'teacher') return;
    const result = await lessonApi.publish(plan, tab, targets);
    adopt(result.plan); setMessage(result.message + (result.indexed.every(Boolean) ? '，资料索引已完成。' : '；部分资料索引失败，可到班级资料重新索引。'));
  });
  const deletePlan = () => run(async () => {
    if (!plan || !window.confirm('确定删除此教案及定稿历史吗？已发布到班级的资料和教研组共享稿会保留。')) return;
    const result = await lessonApi.delete(plan); setPlan(null); setTeacherText(''); setStudentLesson(''); setHandout(''); setMessage(result.message);
  });
  const rewriteSection = () => run(async () => {
    if (!plan || teacherDirty || !rewriteHeading) return;
    controller.current = new AbortController(); setProgress('正在重写所选章节…');
    const row = await streamLesson(`/${plan.id}/regenerate-section`, { revision: plan.revision, heading: rewriteHeading, instructions: rewriteInstructions }, {
      signal: controller.current.signal, onProgress: setProgress,
    });
    adopt(row); setMessage('所选章节已重写并保存，其他章节保持原样，请重新核对与审阅。');
  });
  const shareToGroup = () => run(async () => {
    if (!plan || teacherDirty) return;
    const result = await lessonApi.share(plan);
    setPlan(result.plan); setMessage(result.message);
    setMaterials((await api.listResearchMaterials()).items);
  });

  const snapshot = plan?.versions.find(v => v.version === version);
  const text = snapshot?.content ?? (tab === 'teacher' ? teacherText : tab === 'lesson' ? studentLesson : handout);
  const resources: LessonResources | undefined = snapshot?.resources ?? plan?.resources;
  const imageUrl = useCallback((src: string) => lessonApi.imageUrl(plan!.id, src), [plan?.id]);
  const changeStudent = (value: string) => { if (tab === 'lesson') setStudentLesson(value); else setHandout(value); setStudentReviewed(false); };
  const title = plan ? `${plan.title}（${tab === 'teacher' ? '教师教案' : tab === 'lesson' ? '学生可见教案' : '学生讲义'}）.md` : '';

  return <AppShell brandMark="T" subtitle="智能教学平台 · 教师端" navItems={nav.navItems} navHeader={nav.navHeader} active="lesson-prep" onNavigate={nav.onNavigate} navFoot="CampusClaw · 教师工作空间" headerRight={<LogoutButton />}>
    <div className="content lesson-workspace">
      <div className="page-title"><h2>智能备课</h2><p>{nav.subjectName}教研组 · 生成教师教案 → 修改定稿 → 生成学生稿 → 分班发布</p></div>
      {error && <p className="error lesson-feedback" role="alert">{error} <button className="btn-pill ghost sm" disabled={busy} onClick={() => run(async () => { if (plan && discard()) adopt(await lessonApi.get(plan.id)); })}>重新加载当前教案</button></p>}
      {message && <p className="research-message" role="status">{message}</p>}
      {busy && <p className="lesson-progress" role="status">{progress || '正在保存…'}</p>}
      <section className="card lesson-form">
        <h3>1. 选择资料与教学要求</h3>
        <div className="lesson-fields">
          <label>课题<input className="input" aria-label="备课课题" maxLength={160} disabled={busy} value={form.topic} onChange={e => setForm({ ...form, topic: e.target.value })} placeholder="例如：空间向量法求直线与平面所成角" /></label>
          <label>备课班级<select className="input" disabled={busy} value={form.class_id} onChange={e => setForm({ ...form, class_id: Number(e.target.value) })}>{!classes.length && <option value={0}>暂无任教班级</option>}{classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
          <label>课时（分钟）<input className="input" type="number" min={10} max={180} disabled={busy} value={form.duration} onChange={e => setForm({ ...form, duration: Number(e.target.value) })} /></label>
          <label>教学范围<textarea className="input" maxLength={2000} disabled={busy} value={form.scope} onChange={e => setForm({ ...form, scope: e.target.value })} placeholder="本节讲哪些知识点、例题或章节；不需要哪些内容" /></label>
          <label>班级情况<textarea className="input" maxLength={2000} disabled={busy} value={form.class_profile} onChange={e => setForm({ ...form, class_profile: e.target.value })} placeholder="选填：学生基础、常见困难。留空不会虚构真实学情。" /></label>
          <label>教学目标／课标要求<textarea className="input" maxLength={3000} disabled={busy} value={form.curriculum_standards} onChange={e => setForm({ ...form, curriculum_standards: e.target.value })} placeholder="选填：自行填写，不自动编造课标条目" /></label>
          <label className="lesson-wide">额外要求<textarea className="input" maxLength={3000} disabled={busy} value={form.requirements} onChange={e => setForm({ ...form, requirements: e.target.value })} placeholder="例如：保留原题配图，安排两道课堂练习，突出向量法的建系步骤" /></label>
        </div>
        <fieldset disabled={busy} className="lesson-source-picker"><legend>教研组教师资料（选择 1–5 份）</legend>{materials.map(m => <label key={m.id}><input type="checkbox" checked={form.research_material_ids.includes(m.id)} onChange={e => setForm({ ...form, research_material_ids: e.target.checked ? [...form.research_material_ids, m.id] : form.research_material_ids.filter(id => id !== m.id) })} />{m.filename}<small>{m.asset_count} 张图</small></label>)}{booted && !materials.length && <p className="hint">请先到<a href="/teacher/library">教研组资料</a>导入教师版资料。</p>}</fieldset>
        <button className="btn-pill" disabled={!booted || busy || !form.class_id || !form.topic.trim() || form.duration < 10 || form.duration > 180 || !form.research_material_ids.length || form.research_material_ids.length > 5} onClick={generate}>生成新的教师教案</button>
        <p className="hint">点击生成会将所选教师资料片段及教学要求发送至现有 DeepSeek 服务；配图仅提供路径，不上传图片本体。保存的草稿不会自动发布给学生；生成失败会保留以上填写内容。</p>
      </section>
      <div className="lesson-columns">
        <aside className="lesson-list"><h3>我的教案</h3>{booted && !items.length && <p className="hint">还没有教案，请先生成。</p>}{items.map(row => <button className={`card research-source ${plan?.id === row.id ? 'selected' : ''}`} key={row.id} disabled={busy} onClick={() => select(row.id)}><strong>{row.title}</strong><span>{row.class_name} · {row.duration} 分钟</span><small>{STATUS[row.status]} · {row.current_version ? `定稿 v${row.current_version}` : '尚未定稿'}</small></button>)}</aside>
        <section className="card lesson-document">
          {streamText && <><h3>正在生成教师草稿…</h3><p className="hint">生成尚未完成，来源与内容请在完成后核对。</p><MarkdownAnswer text={streamText.replace(/!\[[^\]]*\]\([^)]+\)/g, '（配图将在生成完成后显示）')} /></>}
          {!streamText && !plan && <p className="hint">选择已保存教案，或填写教学要求生成新教案。</p>}
          {!streamText && plan && <>
            <div className="research-toolbar"><h3>{plan.title}</h3><span className="student-status done">{STATUS[plan.status]}{plan.current_version ? ` · v${plan.current_version}` : ''}</span></div>
            <p className="hint">{plan.class_name} · {plan.duration} 分钟 · 编辑权限仅本人，完整定稿可选择发布到教研组</p>
            <div className="research-tabs"><button className={`btn-pill ${tab === 'teacher' ? '' : 'ghost'}`} disabled={busy} onClick={() => { setTab('teacher'); setVersion(null); setStudentReviewed(false); }}>教师教案</button><button className={`btn-pill ${tab === 'lesson' ? '' : 'ghost'}`} disabled={busy || !plan.student_lesson} onClick={() => { setTab('lesson'); setVersion(null); setStudentReviewed(false); }}>学生可见教案</button><button className={`btn-pill ${tab === 'handout' ? '' : 'ghost'}`} disabled={busy || !plan.student_handout} onClick={() => { setTab('handout'); setVersion(null); setStudentReviewed(false); }}>配套学生讲义</button></div>
            {tab === 'teacher' ? <>
              <h3>2. 修改、审阅与定稿</h3>
              <label className="lesson-editor-label">教师教案正文<textarea className="input lesson-editor" aria-label="教师教案正文" value={teacherText} disabled={busy || plan.status === 'final' || version !== null} onChange={e => { setTeacherText(e.target.value); setReviewed(false); }} /></label>
              <div className="lesson-actions">
                {plan.status !== 'final' && <button className="btn-pill" disabled={busy || !teacherDirty || !teacherText.trim()} onClick={() => mutate(p => lessonApi.save(p, teacherText), '草稿已保存，请重新审阅。')}>保存教师草稿</button>}
                {plan.status === 'draft' && <><label><input type="checkbox" disabled={busy || teacherDirty} checked={reviewed} onChange={e => setReviewed(e.target.checked)} />我已核对内容、公式、例题及来源</label><button className="btn-pill ghost" disabled={busy || teacherDirty || !reviewed} onClick={() => mutate(lessonApi.review, '教案已审阅，可以定稿。')}>审阅通过</button></>}
                {plan.status === 'reviewed' && <button className="btn-pill" disabled={busy || teacherDirty} onClick={() => mutate(lessonApi.finalize, '已保存新的定稿版本，可以生成两份学生稿。')}>确认定稿</button>}
                {plan.status === 'final' && <><button className="btn-pill" disabled={busy || version !== null} onClick={makeStudents}>3. 生成配套学生稿</button><button className="btn-pill ghost" disabled={busy} onClick={() => { if (discard()) mutate(lessonApi.revise, '已开始新修订。历史定稿与已发布资料保留，需重新定稿和生成学生稿。'); }}>开始新修订</button></>}
              </div>
              <section className="lesson-group-share"><h3>教研组共享（可选）</h3><p className="hint">默认仅本人可见。主动发布后，{nav.subjectName}教研组教师可查看、下载完整教案及所用配图；学生不可见。以后修订不会自动更新组内版本。</p>{plan.group_publications.some(p => p.version === plan.current_version) ? <p className="research-message">定稿 v{plan.current_version} 已发布到教研组</p> : <button className="btn-pill ghost" disabled={busy || teacherDirty || plan.status !== 'final' || version !== null} onClick={shareToGroup}>发布当前定稿到教研组</button>}{plan.status !== 'final' && <p className="hint">完成审阅与定稿后，即可选择发布。</p>}{plan.group_publications.map(p => <p key={p.version}><a href={`/teacher/library?material_id=${p.research_material_id}`}>查看组内共享教案 v{p.version}</a></p>)}</section>
              {plan.status !== 'final' && <details className="lesson-versions"><summary>只重写一个章节</summary><p className="hint">先保存手动修改；重写完成后会回到草稿状态，其他章节保留。</p><select className="input" aria-label="重写章节" disabled={busy || teacherDirty} value={rewriteHeading} onChange={e => setRewriteHeading(e.target.value)}><option value="">选择章节</option>{Array.from(plan.content.matchAll(/^##\s+[^\n]+/gm), m => m[0]).map((heading, index) => <option key={`${index}:${heading}`} value={heading}>{heading.replace(/^##\s+/, '')}</option>)}</select><input className="input" aria-label="章节重写要求" maxLength={2000} value={rewriteInstructions} disabled={busy} onChange={e => setRewriteInstructions(e.target.value)} placeholder="例如：增加学生讨论环节，保留原题" /><button className="btn-pill ghost" disabled={busy || teacherDirty || !rewriteHeading} onClick={rewriteSection}>重写所选章节</button></details>}
              <details className="lesson-versions"><summary>定稿历史（{plan.versions.length}）</summary><button className="btn-pill ghost sm" disabled={busy} onClick={() => setVersion(null)}>查看当前稿</button>{plan.versions.map(v => <button key={v.version} className="btn-pill ghost sm" disabled={busy} onClick={() => setVersion(v.version)}>查看 v{v.version} · {new Date(v.created_at).toLocaleString('zh-CN')}</button>)}</details>
            </> : <>
              <h3>3. 核对并编辑{tab === 'lesson' ? '学生可见教案' : '配套学生讲义'}</h3>
              <p className="hint">两份学生稿均应去掉答案、教师解析与提示。自动检查无法替代对正文和图片的人工核对。</p>
              <textarea className="input lesson-editor" aria-label={tab === 'lesson' ? '学生可见教案正文' : '配套学生讲义正文'} disabled={busy} value={text} onChange={e => changeStudent(e.target.value)} />
              <button className="btn-pill" disabled={busy || !studentDirty || !studentLesson.trim() || !handout.trim()} onClick={() => mutate(p => lessonApi.saveStudents(p, studentLesson, handout), '两份学生稿已保存，请重新核对当前要发布的文稿。')}>保存学生稿修改</button>
              <section className="research-publish"><h3>4. 发布当前{tab === 'lesson' ? '学生可见教案' : '学生讲义'}</h3><div className="research-class-options">{classes.map(c => <label key={c.id}><input type="checkbox" disabled={busy} checked={targets.includes(c.id)} onChange={e => setTargets(old => e.target.checked ? [...old, c.id] : old.filter(id => id !== c.id))} />{c.name}</label>)}</div><label className="research-review"><input type="checkbox" disabled={busy || studentDirty} checked={studentReviewed} onChange={e => setStudentReviewed(e.target.checked)} />我已核对当前文稿及配图，确认没有答案、教师解析与提示</label><button className="btn-pill" disabled={busy || studentDirty || !studentReviewed || !targets.length || !text.trim()} onClick={publish}>发布当前文稿到所选班级</button></section>
            </>}
            <div className="research-toolbar"><h3>{snapshot ? `历史定稿 v${snapshot.version}` : '内容预览'}</h3><PrintHandoutButton key={`${plan.id}:${tab}:${version}:${text}`} contentRef={contentRef} title={title} disabled={busy || !text.trim()} /></div>
            <div ref={contentRef}><MarkdownAnswer text={text} imageUrl={imageUrl} /></div>
            {tab === 'teacher' && resources && <details className="lesson-sources"><summary>备课依据与原文核对（{resources.references.length} 个片段）</summary><p className="hint">[S编号] 对应本次提供给 AI 的原文片段，标注原文行号与文件指纹。引用是否支持相邻论断仍需人工核对，不把相关片段当成结论证明。</p>{resources.references.map(r => <article key={r.ref}><strong>[{r.ref}] {r.filename} · {r.heading}</strong><p className="hint">原文第 {r.start_line}–{r.end_line} 行 · 指纹 {r.file_sha256.slice(0, 12)}…</p><pre>{r.excerpt}</pre><a href={`/teacher/library?material_id=${r.research_material_id}`} target="_blank" rel="noreferrer">打开对应教师原稿</a></article>)}</details>}
            {!!plan.publications.length && <section className="research-published"><h3>班级发布记录</h3>{plan.publications.map(p => <p key={p.id}><a href={nav.materialHref(p.class_id, 'teaching')}>{p.class_name} · {p.kind === 'lesson' ? '学生可见教案' : '学生讲义'} · v{p.version}</a><small>　{new Date(p.created_at).toLocaleString('zh-CN')}</small></p>)}</section>}
            <button className="btn-pill ghost lesson-delete" disabled={busy} onClick={deletePlan}>删除私人教案及定稿历史</button>
          </>}
        </section>
      </div>
    </div>
  </AppShell>;
}

export default function LessonPrepPage() {
  return <AuthGate><Suspense fallback={<p>加载中…</p>}><LessonWorkspace /></Suspense></AuthGate>;
}
