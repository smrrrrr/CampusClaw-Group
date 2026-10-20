"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { findTeacherNavItem, useTeacherNavigation } from "@/components/teacher-navigation";
import { ClassSelector } from "@/components/class-selector";
import { LogoutButton } from "@/components/logout-button";
import { api, ApiError, type AgentConfigDTO } from "@/lib/api";

interface StudentRow {
  id: number;
  identifier: string;
  name: string | null;
  class_id: number | null;
  class_name: string | null;
  phone: string | null;
}

function TeacherHome() {
  const router = useRouter();
  const nav = useTeacherNavigation();
  const { navItems, classId, isHomeroom, subjectName } = nav;
  const requestedView = nav.requestedView ?? (isHomeroom ? "home" : "lesson-prep");
  useEffect(() => {
    if (requestedView === "lesson-prep") router.replace("/teacher/lesson-prep");
  }, [requestedView, router]);
  const view = findTeacherNavItem(navItems, requestedView)?.to?.startsWith("/teacher?")
    ? requestedView : "lesson-prep";
  const isStudentView = view === "students" || view === "class-students";
  const [students, setStudents] = useState<StudentRow[]>([]);
  const [loadingStudents, setLoadingStudents] = useState(false);
  const [error, setError] = useState("");
  const [audit, setAudit] = useState<Awaited<ReturnType<typeof api.listAuditLogs>> | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditError, setAuditError] = useState("");

  useEffect(() => {
    if (view !== "audit" || classId === null) return;
    let cancelled = false;
    setAudit(null);
    setAuditLoading(true);
    setAuditError("");
    api.listAuditLogs(classId)
      .then((data) => { if (!cancelled) setAudit(data); })
      .catch((e) => { if (!cancelled) setAuditError(e instanceof ApiError ? e.message : "加载审计日志失败"); })
      .finally(() => { if (!cancelled) setAuditLoading(false); });
    return () => { cancelled = true; };
  }, [view, classId]);

  const hasClasses = classId !== null;

  // 重置密码
  const [resetMsg, setResetMsg] = useState("");
  const [resettingId, setResettingId] = useState<number | null>(null);

  // AI 助手配置
  const [cfgPrompt, setCfgPrompt] = useState("");
  const [cfgTutor, setCfgTutor] = useState(true);
  const [cfgLoading, setCfgLoading] = useState(false);
  const [cfgSaving, setCfgSaving] = useState(false);
  const [cfgMsg, setCfgMsg] = useState("");
  const [cfgError, setCfgError] = useState("");
  const [agentSkills, setAgentSkills] = useState({ tutor: true, homework: true, mistakeExplain: true });
  const [agentPreviewMsg, setAgentPreviewMsg] = useState("");
  const defaultPromptRef = useRef("");

  useEffect(() => {
    api
      .getAgentDefaultPrompt()
      .then((d) => (defaultPromptRef.current = d.system_prompt))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (classId === null || view !== "agent") return;
    let cancelled = false;
    setCfgLoading(true);
    setCfgMsg("");
    setCfgError("");
    api
      .getAgentConfig(classId)
      .then((cfg: AgentConfigDTO) => {
        if (cancelled) return;
        setCfgPrompt(cfg.system_prompt);
        setCfgTutor(cfg.tutor_enabled);
      })
      .catch((e) => { if (!cancelled) setCfgError(e instanceof ApiError ? e.message : "加载配置失败"); })
      .finally(() => { if (!cancelled) setCfgLoading(false); });
    return () => { cancelled = true; };
  }, [classId, view]);

  const saveAgentConfig = async () => {
    if (classId === null) return;
    setCfgSaving(true);
    setCfgMsg("");
    setCfgError("");
    try {
      await api.saveAgentConfig({
        class_id: classId,
        system_prompt: cfgPrompt,
        tutor_enabled: cfgTutor,
      });
      setCfgMsg("已保存。学生端下次提问将使用此提示词与技能设置。");
    } catch (e) {
      setCfgError(e instanceof ApiError ? e.message : "保存失败");
    } finally {
      setCfgSaving(false);
    }
  };

  // 只请求当前班级，后端再次校验任教范围。
  useEffect(() => {
    if (classId === null || !isStudentView) return;
    let cancelled = false;
    setLoadingStudents(true);
    setError("");
    setResetMsg("");
    api
      .listStudents(classId)
      .then((data) => {
        if (cancelled) return;
        setStudents(
          data.items.map((s) => ({
            id: s.id,
            identifier: s.identifier,
            name: s.name,
            class_id: s.class_id,
            class_name: s.class_name,
            phone: s.phone,
          })),
        );
      })
      .catch((e) => { if (!cancelled) setError(e instanceof ApiError ? e.message : "加载学生列表失败"); })
      .finally(() => { if (!cancelled) setLoadingStudents(false); });
    return () => { cancelled = true; };
  }, [classId, isStudentView]);

  const handleResetPassword = async (s: StudentRow) => {
    if (!window.confirm(`确定重置「${s.name ?? s.identifier}」的密码为初始密码吗？`)) return;
    setResettingId(s.id);
    setError("");
    setResetMsg("");
    try {
      const res = await api.resetStudentPassword(s.id);
      setResetMsg(`${res.message}，初始密码：${res.initial_password}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "重置失败");
    } finally {
      setResettingId(null);
    }
  };

  const filteredStudents =
    classId !== null ? students.filter((s) => s.class_id === classId) : students;
  const className = filteredStudents[0]?.class_name ?? (classId ? `班级 ${classId}` : "");

  const activeItem = findTeacherNavItem(navItems, view);
  const needsClass = isStudentView || ["home", "class-analysis", "class-homework", "class-notices", "subject-analysis", "tools", "agent"].includes(view);
  const scopeDescription = view === "audit"
    ? "仅限带班班级的审计与统计。"
    : view.startsWith("class-") || view === "home"
      ? "班主任工作台 · 仅限我的带班。"
      : ["lesson-prep", "lesson-quiz", "research-qa", "case-analysis"].includes(view)
        ? `${subjectName}教研组 · 仅限本学科组资料。`
        : `${subjectName} · 仅限当前任教班级的本科目数据。`;

  return (
    <AppShell
      brandMark="T"
      subtitle="智能教学平台 · 教师端"
      navItems={navItems}
      active={view}
      onNavigate={nav.onNavigate}
      navHeader={nav.navHeader}
      navFoot="CampusClaw · 教师工作空间"
      headerLeft={
        <>
          <span className="status-dot" />
          <span className="class-pill subject">{subjectName}教研组</span>
          {hasClasses && <span className="class-pill">{className || `班级 ${classId}`}</span>}
          {isHomeroom && <span className="class-pill">我的带班 · 全科总览</span>}
        </>
      }
      headerRight={
        <>
          <span className="user-chip">
            <span className="avatar">师</span>
            教师
          </span>
          <LogoutButton />
        </>
      }
    >
      <div style={{ padding: 0 }}>
          {!hasClasses && needsClass ? (
            <div className="panel" style={{ textAlign: "center", padding: "56px 32px" }}>
              <p className="hint" style={{ fontSize: 16 }}>
                暂无任教班级
              </p>
              <p className="hint" style={{ marginTop: 8 }}>
                您尚未被分配任教班级，请联系管理员处理。
              </p>
            </div>
          ) : view === "home" && isHomeroom ? (
            <>
              <div className="page-title"><h2>本班首页</h2><p>班主任工作台 · 管理带班事务，查看本班全科概况。</p></div>
              <div className="teacher-overview-grid">
                {navItems[0]?.children?.map((item) => <button key={item.key} className="panel teacher-overview-card" onClick={() => nav.onNavigate(item.key)}>
                  <strong>{item.label}</strong><p>{item.description}</p><span>进入模块 →</span>
                </button>)}
              </div>
            </>
          ) : isStudentView ? (
            <>
              <div className="page-title" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                <div>
                  <h2>{isHomeroom ? "本班学生" : "班级学生"}</h2>
                  <p>{isHomeroom ? "查看带班班级的学生名单，管理学生账号。" : `查看当前任教班级的学生名单 · ${subjectName}科目视角。`}</p>
                </div>
                {!isHomeroom && <Link href={nav.uploadHref} className="btn-pill">单科资料发布</Link>}
              </div>

              {error && <div className="error" style={{ marginBottom: 8 }}>{error}</div>}
              {resetMsg && <div className="success" style={{ marginBottom: 8 }}>{resetMsg}</div>}

              {loadingStudents ? (
                <div className="panel"><p className="hint">加载中…</p></div>
              ) : filteredStudents.length === 0 ? (
                <div className="panel" style={{ textAlign: "center", padding: "44px 24px" }}>
                  <p className="hint">暂无学生</p>
                </div>
              ) : (
                <div className="table-card">
                  <table>
                    <thead>
                      <tr>
                        <th>学号</th>
                        <th>姓名</th>
                        <th>班级</th>
                        <th>手机号</th>
                        {isHomeroom && <th style={{ width: 140 }}>操作</th>}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredStudents.map((s) => (
                        <tr key={s.id}>
                          <td style={{ fontVariantNumeric: "tabular-nums" }}>{s.identifier}</td>
                          <td>{s.name ?? "—"}</td>
                          <td>{s.class_name ?? "—"}</td>
                          <td>{s.phone ?? "—"}</td>
                          {isHomeroom && <td>
                            <button
                              className="btn-pill ghost sm"
                              onClick={() => handleResetPassword(s)}
                              disabled={resettingId !== null}
                            >
                              {resettingId === s.id ? "重置中…" : "重置密码"}
                            </button>
                          </td>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          ) : view === "agent" ? (
            <>
              <div className="page-title agent-page-title" style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between" }}>
                <div>
                  <h2>助手配置</h2>
                  <p>{nav.subjectName} · 按班级保存自己的助手配置，学生选择该科目时使用。</p>
                </div>
                <div className="agent-class-select"><label>配置班级</label><ClassSelector value={nav.teachingClassId} onChange={(id) => nav.selectTeachingClass(id, "agent")} /></div>
              </div>
              <div className="agent-config-grid">
                <section className="panel agent-config-panel">
                  <h3 className="agent-panel-heading">提示词（总说明）</h3>
                  {cfgError && <div className="error">{cfgError}</div>}
                  {cfgMsg && <div className="success">{cfgMsg}</div>}
                  {cfgLoading ? <p className="hint">加载中…</p> : <>
                    <div className="field">
                      <label htmlFor="agent-prompt">角色提示词（可自定义，留空则使用默认）</label>
                      <textarea id="agent-prompt" value={cfgPrompt} onChange={(e) => { setCfgPrompt(e.target.value); setCfgMsg(""); }} rows={18} placeholder="留空使用默认提示词" />
                      <p className="hint" style={{ marginTop: 6 }}>提示词中应保留 LaTeX 公式定界符（$...$ 行内 / $$...$$ 独立）与[编号]标注规范，避免前端渲染源码。</p>
                    </div>
                    <div className="agent-actions">
                      <button className="btn-pill" onClick={saveAgentConfig} disabled={cfgSaving || classId === null}>{cfgSaving ? "保存中…" : "保存提示词"}</button>
                      <button className="btn-pill ghost sm" onClick={() => { setCfgPrompt(defaultPromptRef.current); setCfgMsg(""); }}>填入默认提示词</button>
                    </div>
                  </>}
                </section>
                <section className="panel agent-config-panel">
                  <h3 className="agent-panel-heading">AI 技能</h3>
                  {([
                    ["tutor", "解题引导", "学生就题目提问后，追问思路、引用知识库，默认不直接给最终答案。", "知识库检索"],
                    ["homework", "作业批改", "学生提交作业以后给出分数、评语与依据，教师可以改分。", "作业读取 · 知识库检索"],
                    ["mistakeExplain", "错题讲解", "学生查看判错的题目时按错因讲解，默认不直接给最终答案。", "作业读取 · 知识库检索"],
                  ] as const).map(([key, title, description, tools]) => <div className="agent-skill-card" key={key}>
                    <div className="agent-skill-top"><strong>{title} <span className="agent-required">必做</span></strong><label className="agent-toggle" aria-label={`切换${title}`}><input type="checkbox" checked={key === "tutor" ? cfgTutor : agentSkills[key]} onChange={(e) => { if (key === "tutor") setCfgTutor(e.target.checked); setAgentSkills({ ...agentSkills, [key]: e.target.checked }); setAgentPreviewMsg("技能开关当前为界面预览；解题引导保存提示词时一并生效。"); }} /><span /></label></div>
                    <p>{description}</p><span className="agent-tool-tag">⌁ {tools}</span>
                  </div>)}
                  <button className="agent-add-button" onClick={() => setAgentPreviewMsg("技能注册接口尚未接入。")}>＋ 上传 / 注册技能</button>
                  <section className="agent-reference-materials" aria-label="助手参考资料">
                    <h3 className="agent-panel-heading agent-knowledge-heading">助手参考资料（{nav.subjectName}）</h3>
                    <p className="hint">助手会自动检索所选班级已发布且完成索引的{nav.subjectName}资料，无需手动绑定。</p>
                    <p className="hint">仅使用学生可见版本，教研组中的教师原稿不会直接用于学生问答。</p>
                    {nav.teachingClassId !== null ? <Link className="btn-pill ghost sm" href={nav.materialHref(nav.teachingClassId, "teaching")}>查看本班资料</Link> : <p className="hint">请先选择任教班级，再查看参考资料。</p>}
                  </section>
                </section>
                <section className="panel agent-mcp-panel"><div><h3 className="agent-panel-heading">MCP 服务器（Model Context Protocol）</h3><p>通过 MCP 为助手接入工具，展示工具连接与执行状态。</p></div><button className="btn-pill" onClick={() => setAgentPreviewMsg("MCP 服务器接口尚未接入。")}>＋ 添加服务器</button>
                  {["知识库检索服务", `${nav.subjectName}计算工具`].map((name) => <div className="agent-mcp-card" key={name}>🔌　{name}<span>预览</span></div>)}
                </section>
                {agentPreviewMsg && <p className="hint agent-preview-message" role="status">{agentPreviewMsg}</p>}
                <p className="hint agent-integration-note">提示词按班级、学科及教师独立保存；解题引导开启时使用固定引导框架。作业批改、错题讲解、技能注册与 MCP 控件仍为界面预览。</p>
              </div>
            </>
          ) : view === "audit" ? (
            <>
              <div className="page-title"><h2>审计与统计</h2><p>仅显示带班班级的审计日志，最近 100 条。</p></div>
              {auditError && <div className="error" role="alert">{auditError}</div>}
              <div className="panel" style={{ overflowX: "auto" }}>
                {auditLoading ? <p className="hint">加载中…</p> : <>
                  <p className="hint" style={{ marginBottom: 16 }}>本班审计记录共 {audit?.total ?? 0} 条</p>
                  <table><thead><tr><th>时间</th><th>用户编号</th><th>角色</th><th>请求</th><th>状态码</th></tr></thead>
                    <tbody>{audit?.items.map((item) => <tr key={item.id}><td>{new Date(item.created_at.endsWith("Z") ? item.created_at : `${item.created_at}Z`).toLocaleString("zh-CN")}</td><td>{item.user_id ?? "—"}</td><td>{item.role === "student" ? "学生" : item.role === "teacher" ? "教师" : "—"}</td><td>{item.method} {item.request_path}</td><td>{item.status_code}</td></tr>)}</tbody>
                  </table>
                  {!audit?.items.length && <p className="hint" style={{ padding: 24, textAlign: "center" }}>暂无本班审计记录</p>}
                </>}
              </div>
            </>
          ) : (
            <div className="panel" style={{ textAlign: "center", padding: "56px 32px" }}>
              <p className="hint" style={{ fontSize: 16 }}>
                {activeItem?.label ?? view}
              </p>
              <p className="hint" style={{ marginTop: 8 }}>{scopeDescription}</p>
              <p className="hint" style={{ marginTop: 8 }}>{activeItem?.description}</p>
              <p className="hint" style={{ marginTop: 16 }}>
                该模块尚未接入，敬请期待。
              </p>
            </div>
          )}
      </div>
    </AppShell>
  );
}

export default function TeacherPage() {
  return (
    <AuthGate>
      <Suspense fallback={<div className="centered">加载中…</div>}><TeacherHome /></Suspense>
    </AuthGate>
  );
}
