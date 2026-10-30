"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { findTeacherNavItem, useTeacherNavigation, SUBJECT_NAMES } from "@/components/teacher-navigation";
import { ClassSelector } from "@/components/class-selector";
import { LogoutButton } from "@/components/logout-button";
import { api, ApiError, type AgentConfigDTO, type McpServerDTO, type McpToolDTO, type McpToolCallDTO, type SkillDTO, type ClassAnalyticsDTO } from "@/lib/api";

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
  const { navItems, classId, isHomeroom, subjectName, subject } = nav;
  const requestedView = nav.requestedView ?? (isHomeroom ? "home" : "lesson-prep");
  useEffect(() => {
    if (requestedView === "lesson-prep") router.replace("/teacher/lesson-prep");
    if (requestedView === "lesson-quiz") router.replace("/teacher/quiz");
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

  // 作业批改
  const [hwList, setHwList] = useState<Awaited<ReturnType<typeof api.listTeacherHomeworks>>>([]);
  const [hwLoading, setHwLoading] = useState(false);
  const [hwError, setHwError] = useState("");
  const [hwForm, setHwForm] = useState({ title: "", stem: "", dueAt: "" });
  const [hwSubmitting, setHwSubmitting] = useState(false);
  const [hwSubmissions, setHwSubmissions] = useState<Awaited<ReturnType<typeof api.listHomeworkSubmissions>>>([]);
  const [hwSubLoading, setHwSubLoading] = useState(false);
  const [hwSelectedId, setHwSelectedId] = useState<number | null>(null);
  const [hwAiGrading, setHwAiGrading] = useState<number | null>(null);
  const [hwGradeForm, setHwGradeForm] = useState<Record<number, { score: string; feedback: string }>>({});
  const [hwGradingId, setHwGradingId] = useState<number | null>(null);

  // 班级学情
  const [classAnalytics, setClassAnalytics] = useState<ClassAnalyticsDTO | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [analyticsError, setAnalyticsError] = useState("");

  useEffect(() => {
    if ((view !== "class-analysis" && view !== "subject-analysis" && view !== "class-homework") || classId === null) return;
    let cancelled = false;
    setAnalyticsLoading(true);
    setAnalyticsError("");
    const targetSubject = view === "subject-analysis" ? subject ?? undefined : undefined;
    api.getTeacherClassAnalytics(classId, targetSubject)
      .then((data) => { if (!cancelled) setClassAnalytics(data); })
      .catch((e) => { if (!cancelled) setAnalyticsError(e instanceof ApiError ? e.message : "学情加载失败"); })
      .finally(() => { if (!cancelled) setAnalyticsLoading(false); });
    return () => { cancelled = true; };
  }, [view, classId, subject]);

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

  // 作业列表加载
  const loadHwList = async () => {
    if (classId === null) return;
    setHwLoading(true);
    setHwError("");
    try {
      const list = await api.listTeacherHomeworks(classId);
      setHwList(list);
    } catch (e) {
      setHwError(e instanceof ApiError ? e.message : "加载作业失败");
    } finally {
      setHwLoading(false);
    }
  };
  useEffect(() => {
    if (view !== "tools") return;
    loadHwList();
  }, [view, classId]);

  const handleCreateHomework = async () => {
    if (!hwForm.title.trim() || !hwForm.stem.trim() || !hwForm.dueAt) return;
    setHwSubmitting(true);
    try {
      const dueAt = new Date(hwForm.dueAt).toISOString();
      const content = JSON.stringify({ stem: hwForm.stem });
      await api.createHomework({ class_id: classId!, title: hwForm.title, content, due_at: dueAt });
      setHwForm({ title: "", stem: "", dueAt: "" });
      await loadHwList();
    } catch (e) {
      setHwError(e instanceof ApiError ? e.message : "创建作业失败");
    } finally {
      setHwSubmitting(false);
    }
  };

  const handlePublishHw = async (id: number) => {
    try { await api.publishHomework(id); await loadHwList(); }
    catch (e) { setHwError(e instanceof ApiError ? e.message : "发布失败"); }
  };
  const handleCloseHw = async (id: number) => {
    try { await api.closeHomework(id); await loadHwList(); }
    catch (e) { setHwError(e instanceof ApiError ? e.message : "关闭失败"); }
  };

  const loadSubmissions = async (hwId: number) => {
    setHwSelectedId(hwId);
    setHwSubLoading(true);
    try {
      const subs = await api.listHomeworkSubmissions(hwId);
      setHwSubmissions(subs);
    } catch (e) {
      setHwError(e instanceof ApiError ? e.message : "加载提交失败");
    } finally {
      setHwSubLoading(false);
    }
  };

  const handleAiGrade = async (hwId: number) => {
    setHwAiGrading(hwId);
    try {
      const res = await api.aiGradeHomework(hwId);
      if (hwSelectedId === hwId) await loadSubmissions(hwId);
      await loadHwList();
      setHwError(`AI 已批改 ${res.graded_count} 份`);
    } catch (e) {
      setHwError(e instanceof ApiError ? e.message : "AI 批改失败");
    } finally {
      setHwAiGrading(null);
    }
  };

  const handleGradeSub = async (subId: number) => {
    const form = hwGradeForm[subId];
    if (!form) return;
    const score = parseInt(form.score, 10);
    if (isNaN(score) || score < 0 || score > 100) return;
    setHwGradingId(subId);
    try {
      await api.gradeSubmission(subId, score, form.feedback || null);
      if (hwSelectedId !== null) await loadSubmissions(hwSelectedId);
    } catch (e) {
      setHwError(e instanceof ApiError ? e.message : "改分失败");
    } finally {
      setHwGradingId(null);
    }
  };

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

  // MCP 服务器管理
  const [mcpServers, setMcpServers] = useState<McpServerDTO[]>([]);
  const [mcpBusy, setMcpBusy] = useState(false);
  const [mcpMsg, setMcpMsg] = useState("");
  const [mcpError, setMcpError] = useState("");
  const [mcpForm, setMcpForm] = useState({ name: "", base_url: "", auth_token: "" });
  const [mcpTools, setMcpTools] = useState<Record<number, McpToolDTO[]>>({});
  const [mcpOpenTools, setMcpOpenTools] = useState<number | null>(null);
  const [toolCalls, setToolCalls] = useState<McpToolCallDTO[]>([]);

  // 技能文件
  const [skills, setSkills] = useState<SkillDTO[]>([]);
  const [skillSource, setSkillSource] = useState("");
  const [editingSkillId, setEditingSkillId] = useState<number | null>(null);
  const [skillMsg, setSkillMsg] = useState("");
  const [skillError, setSkillError] = useState("");

  const loadMcp = async (cid: number) => {
    try {
      const [servers, calls] = await Promise.all([api.listMcpServers(cid), api.listMcpToolCalls(cid)]);
      setMcpServers(servers.items);
      setToolCalls(calls.items);
    } catch (e) {
      setMcpError(e instanceof ApiError ? e.message : "加载 MCP 服务器失败");
    }
  };

  const loadSkills = async (cid: number) => {
    try {
      const data = await api.listSkills(cid);
      setSkills(data.items);
    } catch (e) {
      setSkillError(e instanceof ApiError ? e.message : "加载技能失败");
    }
  };

  useEffect(() => {
    if (classId === null || view !== "agent") return;
    setMcpMsg(""); setMcpError(""); setSkillMsg(""); setSkillError("");
    loadMcp(classId);
    loadSkills(classId);
  }, [classId, view]);

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

  const submitMcpServer = async () => {
    if (classId === null) return;
    setMcpBusy(true); setMcpMsg(""); setMcpError("");
    try {
      await api.createMcpServer({
        class_id: classId,
        name: mcpForm.name.trim(),
        base_url: mcpForm.base_url.trim(),
        auth_token: mcpForm.auth_token,
      });
      // 令牌提交后立即清空，页面不再持有
      setMcpForm({ name: "", base_url: "", auth_token: "" });
      setMcpMsg("服务器已登记，请点击「连接并发现」获取工具。");
      await loadMcp(classId);
    } catch (e) {
      setMcpError(e instanceof ApiError ? e.message : "登记失败");
    } finally {
      setMcpBusy(false);
    }
  };

  const connectMcp = async (id: number) => {
    if (classId === null) return;
    setMcpBusy(true); setMcpMsg(""); setMcpError("");
    try {
      const res = await api.connectMcpServer(id);
      const excluded = res.excluded?.length ? `；已排除不合规工具：${res.excluded.join("、")}` : "";
      setMcpMsg(`已连接，发现 ${res.server.tool_count} 个工具${excluded}`);
      await loadMcp(classId);
    } catch (e) {
      setMcpError(e instanceof ApiError ? e.message : "连接失败");
      await loadMcp(classId);
    } finally {
      setMcpBusy(false);
    }
  };

  const disconnectMcp = async (id: number) => {
    if (classId === null) return;
    setMcpBusy(true); setMcpMsg(""); setMcpError("");
    try {
      await api.disconnectMcpServer(id);
      setMcpMsg("已断开，工具缓存已清空。");
      await loadMcp(classId);
      setMcpTools((prev) => ({ ...prev, [id]: [] }));
    } catch (e) {
      setMcpError(e instanceof ApiError ? e.message : "断开失败");
    } finally {
      setMcpBusy(false);
    }
  };

  const removeMcp = async (id: number) => {
    if (classId === null || !window.confirm("确定删除该 MCP 服务器？已产生的调用记录会保留。")) return;
    setMcpBusy(true); setMcpMsg(""); setMcpError("");
    try {
      await api.deleteMcpServer(id);
      setMcpMsg("服务器已删除。");
      await loadMcp(classId);
    } catch (e) {
      setMcpError(e instanceof ApiError ? e.message : "删除失败");
    } finally {
      setMcpBusy(false);
    }
  };

  const toggleTools = async (id: number) => {
    if (mcpOpenTools === id) { setMcpOpenTools(null); return; }
    setMcpOpenTools(id);
    if (!mcpTools[id]) {
      try {
        const data = await api.listMcpTools(id);
        setMcpTools((prev) => ({ ...prev, [id]: data.items }));
      } catch (e) {
        setMcpError(e instanceof ApiError ? e.message : "加载工具失败");
      }
    }
  };

  const saveSkill = async () => {
    if (classId === null || !skillSource.trim()) return;
    setSkillMsg(""); setSkillError("");
    try {
      if (editingSkillId !== null) {
        await api.updateSkill(editingSkillId, skillSource);
        setSkillMsg("技能已更新。");
      } else {
        await api.createSkill({ class_id: classId, source: skillSource });
        setSkillMsg("技能已保存。");
      }
      setSkillSource(""); setEditingSkillId(null);
      await loadSkills(classId);
    } catch (e) {
      setSkillError(e instanceof ApiError ? e.message : "保存技能失败");
    }
  };

  const startEditSkill = (s: SkillDTO) => {
    setEditingSkillId(s.id);
    setSkillSource(s.source);
    setSkillMsg(""); setSkillError("");
  };

  const removeSkill = async (id: number) => {
    if (classId === null || !window.confirm("确定删除该技能？")) return;
    setSkillMsg(""); setSkillError("");
    try {
      await api.deleteSkill(id);
      setSkillMsg("技能已删除。");
      if (editingSkillId === id) { setEditingSkillId(null); setSkillSource(""); }
      await loadSkills(classId);
    } catch (e) {
      setSkillError(e instanceof ApiError ? e.message : "删除技能失败");
    }
  };

  // 只请求当前班级，后端再次校验任教范围。
  useEffect(() => {
    if (classId === null || !isStudentView) return;
    let cancelled = false;
    setLoadingStudents(true);    setError("");
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
                  {skillError && <div className="error" role="alert">{skillError}</div>}
                  {skillMsg && <div className="success" role="status">{skillMsg}</div>}
                  <div className="agent-skill-list">
                    {skills.length === 0 && <p className="hint">还没有技能文件。可在下方粘贴技能文件新建。</p>}
                    {skills.map((s) => <div className="agent-skill-card" key={s.id}>
                      <div className="agent-skill-top"><strong>{s.name} {s.enabled ? <span className="agent-tool-tag">已启用</span> : <span className="agent-required">已停用</span>}</strong>
                        <span style={{ display: "flex", gap: 8 }}>
                          <button className="btn-pill ghost sm" onClick={() => startEditSkill(s)}>改写</button>
                          <button className="btn-pill ghost sm" onClick={() => removeSkill(s.id)}>删除</button>
                        </span>
                      </div>
                      <p className="hint">适用条件：{s.trigger}</p>
                      <span className="agent-tool-tag">⌁ {s.tools.join(" · ")}</span>
                    </div>)}
                  </div>
                  <div className="field" style={{ marginTop: 12 }}>
                    <label htmlFor="skill-source">{editingSkillId !== null ? "改写技能文件" : "新建技能文件"}</label>
                    <textarea id="skill-source" value={skillSource} onChange={(e) => setSkillSource(e.target.value)} rows={8}
                      placeholder={"名称：公式提示\n适用条件：夹角,公式\n工具：knowledge_search, formula_hint@campus-tools\n启用：是\n\n说明：先给公式与步骤，引导学生自行计算。"} />
                    <p className="hint">头部每行「键：值」，空行以下是技能说明；工具可写 knowledge_search 或 工具名@服务器名。</p>
                  </div>
                  <div className="agent-actions">
                    <button className="btn-pill" onClick={saveSkill} disabled={!skillSource.trim()}>{editingSkillId !== null ? "保存改写" : "保存技能"}</button>
                    {editingSkillId !== null && <button className="btn-pill ghost sm" onClick={() => { setEditingSkillId(null); setSkillSource(""); }}>取消改写</button>}
                  </div>
                  <section className="agent-reference-materials" aria-label="助手参考资料">
                    <h3 className="agent-panel-heading agent-knowledge-heading">助手参考资料（{nav.subjectName}）</h3>
                    <p className="hint">助手会自动检索所选班级已发布且完成索引的{nav.subjectName}资料，无需手动绑定。</p>
                    <p className="hint">仅使用学生可见版本，教研组中的教师原稿不会直接用于学生问答。</p>
                    {nav.teachingClassId !== null ? <Link className="btn-pill ghost sm" href={nav.materialHref(nav.teachingClassId, "teaching")}>查看本班资料</Link> : <p className="hint">请先选择任教班级，再查看参考资料。</p>}
                  </section>
                </section>
                <section className="panel agent-mcp-panel"><div><h3 className="agent-panel-heading">MCP 服务器（Model Context Protocol）</h3><p>登记服务器、连接并发现工具，令牌只保存在服务端。</p></div>
                  {mcpError && <div className="error" role="alert">{mcpError}</div>}
                  {mcpMsg && <div className="success" role="status">{mcpMsg}</div>}
                  <div className="agent-mcp-form">
                    <div className="field"><label htmlFor="mcp-name">服务器名称</label>
                      <input id="mcp-name" value={mcpForm.name} onChange={(e) => setMcpForm({ ...mcpForm, name: e.target.value })} placeholder="campus-tools" /></div>
                    <div className="field"><label htmlFor="mcp-url">Base URL</label>
                      <input id="mcp-url" value={mcpForm.base_url} onChange={(e) => setMcpForm({ ...mcpForm, base_url: e.target.value })} placeholder="http://mcp-tools:8090" /></div>
                    <div className="field"><label htmlFor="mcp-token">访问令牌</label>
                      <input id="mcp-token" type="password" autoComplete="off" value={mcpForm.auth_token} onChange={(e) => setMcpForm({ ...mcpForm, auth_token: e.target.value })} placeholder="只发送到服务端，不保存到浏览器" /></div>
                    <button className="btn-pill" onClick={submitMcpServer} disabled={mcpBusy || !mcpForm.name.trim() || !mcpForm.base_url.trim()}>{mcpBusy ? "处理中…" : "登记服务器"}</button>
                  </div>
                  <div className="agent-mcp-list">
                    {mcpServers.length === 0 && <p className="hint">还没有登记 MCP 服务器。</p>}
                    {mcpServers.map((s) => <div className="agent-mcp-card" key={s.id}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        <span>🔌 {s.name} · {s.connected ? "已连接" : "未连接"} · {s.tool_count} 个工具 · {s.has_auth ? "已配令牌" : "无令牌"}</span>
                        <span style={{ display: "flex", gap: 8 }}>
                          <button className="btn-pill ghost sm" onClick={() => connectMcp(s.id)} disabled={mcpBusy}>{s.connected ? "重新连接" : "连接并发现"}</button>
                          <button className="btn-pill ghost sm" onClick={() => disconnectMcp(s.id)} disabled={mcpBusy || !s.connected}>断开</button>
                          <button className="btn-pill ghost sm" onClick={() => toggleTools(s.id)}>{mcpOpenTools === s.id ? "收起工具" : "查看工具"}</button>
                          <button className="btn-pill ghost sm" onClick={() => removeMcp(s.id)} disabled={mcpBusy}>删除</button>
                        </span>
                      </div>
                      {s.last_error && <p className="hint warn">上次错误：{s.last_error}</p>}
                      {mcpOpenTools === s.id && <div className="agent-mcp-tools">
                        {(mcpTools[s.id] ?? []).length === 0 ? <p className="hint">暂无工具（需先连接）。</p> : (mcpTools[s.id] ?? []).map((t) => <div key={t.name} className="agent-mcp-tool">
                          <strong>{t.name}</strong><p className="hint">{t.description}</p>
                          <pre className="agent-tool-schema">{JSON.stringify(t.input_schema, null, 2)}</pre>
                        </div>)}
                      </div>}
                    </div>)}
                  </div>
                  <div className="agent-mcp-calls">
                    <h4 className="agent-panel-heading">最近调用记录</h4>
                    {toolCalls.length === 0 ? <p className="hint">暂无调用记录。</p> : <table><thead><tr><th>时间</th><th>工具</th><th>状态</th><th>说明</th></tr></thead>
                      <tbody>{toolCalls.slice(0, 10).map((c) => <tr key={c.id}><td>{new Date(c.created_at.endsWith("Z") ? c.created_at : `${c.created_at}Z`).toLocaleString("zh-CN")}</td><td>{c.tool_ref}</td><td>{c.status === "ok" ? "成功" : c.status === "denied" ? "被拒" : "错误"}</td><td>{c.detail ?? "—"}</td></tr>)}</tbody>
                    </table>}
                  </div>
                </section>
                {agentPreviewMsg && <p className="hint agent-preview-message" role="status">{agentPreviewMsg}</p>}
                <p className="hint agent-integration-note">提示词按班级、学科及教师独立保存；解题引导开启时使用固定引导框架。技能与 MCP 服务器为真实配置；作业批改与错题讲解开关仍为界面预览。</p>
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
          ) : view === "tools" ? (
            <>
              <div className="page-title"><h2>作业与改分</h2><p>布置本科目作业、查看提交、AI 初批与教师改分。</p></div>
              {hwError && <div className="error" role="alert" style={{ marginBottom: 12 }}>{hwError}</div>}
              <div className="panel" style={{ marginBottom: 16 }}>
                <h3 style={{ marginBottom: 12 }}>布置新作业</h3>
                <div style={{ display: "grid", gap: 8 }}>
                  <input className="input" placeholder="作业标题" value={hwForm.title} onChange={(e) => setHwForm({ ...hwForm, title: e.target.value })} />
                  <textarea className="input" placeholder="题目内容" style={{ minHeight: 60 }} value={hwForm.stem} onChange={(e) => setHwForm({ ...hwForm, stem: e.target.value })} />
                  <input className="input" type="datetime-local" value={hwForm.dueAt} onChange={(e) => setHwForm({ ...hwForm, dueAt: e.target.value })} />
                  <button className="btn" style={{ width: "auto" }} onClick={handleCreateHomework} disabled={hwSubmitting || !hwForm.title.trim() || !hwForm.stem.trim() || !hwForm.dueAt}>
                    {hwSubmitting ? "创建中…" : "创建草稿"}
                  </button>
                </div>
              </div>
              <div className="panel">
                <h3 style={{ marginBottom: 12 }}>本班本科目作业</h3>
                {hwLoading ? <p className="hint">加载中…</p> : hwList.length === 0 ? (
                  <p className="hint" style={{ padding: 24, textAlign: "center" }}>暂无作业</p>
                ) : (
                  <div style={{ display: "grid", gap: 12 }}>
                    {hwList.map((hw) => (
                      <div key={hw.id} className="panel" style={{ padding: 12, border: "1px solid #f3f4f6" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                          <div>
                            <strong>{hw.title}</strong>
                            <div className="hint">截止：{hw.due_at ?? "无"} · 提交 {hw.submitted_count}/{hw.total_count} · 状态：{hw.status}</div>
                          </div>
                          <div style={{ display: "flex", gap: 6 }}>
                            {hw.status === "draft" && <button className="btn" style={{ width: "auto", padding: "4px 10px" }} onClick={() => handlePublishHw(hw.id)}>发布</button>}
                            {hw.status === "published" && <button className="btn" style={{ width: "auto", padding: "4px 10px" }} onClick={() => handleCloseHw(hw.id)}>关闭</button>}
                            <button className="btn" style={{ width: "auto", padding: "4px 10px" }} onClick={() => loadSubmissions(hw.id)}>查看提交</button>
                            {hw.status === "published" && <button className="btn" style={{ width: "auto", padding: "4px 10px" }} onClick={() => handleAiGrade(hw.id)} disabled={hwAiGrading === hw.id}>{hwAiGrading === hw.id ? "批改中…" : "AI 初批"}</button>}
                          </div>
                        </div>
                        {hwSelectedId === hw.id && (
                          <div style={{ marginTop: 12, borderTop: "1px solid #f3f4f6", paddingTop: 12 }}>
                            {hwSubLoading ? <p className="hint">加载中…</p> : hwSubmissions.length === 0 ? (
                              <p className="hint">暂无学生提交</p>
                            ) : hwSubmissions.map((sub) => (
                              <div key={sub.id} style={{ padding: 10, borderBottom: "1px solid #f3f4f6" }}>
                                <div className="hint">学生 #{sub.student_id} · {sub.status}</div>
                                <div style={{ margin: "6px 0", whiteSpace: "pre-wrap" }}>{sub.answer_text}</div>
                                {sub.ai_score !== null && <div className="hint">AI 评分：{sub.ai_score} · {sub.ai_feedback}</div>}
                                {sub.teacher_score !== null && <div style={{ fontWeight: 700 }}>教师评分：{sub.teacher_score} · {sub.teacher_feedback}</div>}
                                <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                                  <input className="input" type="number" min={0} max={100} placeholder="分数" style={{ width: 80 }}
                                    value={hwGradeForm[sub.id]?.score ?? sub.ai_score ?? ""}
                                    onChange={(e) => setHwGradeForm((p) => ({ ...p, [sub.id]: { score: e.target.value, feedback: p[sub.id]?.feedback ?? sub.ai_feedback ?? "" } }))} />
                                  <input className="input" placeholder="评语" style={{ flex: 1 }}
                                    value={hwGradeForm[sub.id]?.feedback ?? ""}
                                    onChange={(e) => setHwGradeForm((p) => ({ ...p, [sub.id]: { score: p[sub.id]?.score ?? "", feedback: e.target.value } }))} />
                                  <button className="btn" style={{ width: "auto", padding: "4px 12px" }} onClick={() => handleGradeSub(sub.id)} disabled={hwGradingId === sub.id}>
                                    {hwGradingId === sub.id ? "…" : "改分"}
                                  </button>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : view === "class-homework" ? (
            <>
              <div className="page-title"><h2>本班作业（总览）</h2><p>全科作业提交率与平均分统计（只读）。</p></div>
              {analyticsLoading ? (
                <div className="panel" style={{ textAlign: "center", padding: 24 }}>加载中…</div>
              ) : analyticsError ? (
                <div className="panel" style={{ textAlign: "center", padding: 24, color: "#c62828" }}>{analyticsError}</div>
              ) : classAnalytics ? (
                <div className="panel" style={{ padding: 24 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16, marginBottom: 24 }}>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>作业提交率</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.submission_rate}%</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>班级平均分</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.class_average != null ? `${classAnalytics.class_average}分` : "暂无"}</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>错题率</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.mistake_rate}%</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>学生人数</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.total_students}</div></div>
                  </div>
                  {Object.keys(classAnalytics.subject_averages).length > 0 ? (
                    <div>
                      <div className="student-section-title" style={{ marginBottom: 8 }}><span />各学科作业平均分</div>
                      <table style={{ width: "100%", borderCollapse: "collapse" }}>
                        <thead><tr style={{ borderBottom: "1px solid #eee" }}><th style={{ textAlign: "left", padding: "8px 4px" }}>学科</th><th style={{ textAlign: "left", padding: "8px 4px" }}>平均分</th></tr></thead>
                        <tbody>
                          {Object.entries(classAnalytics.subject_averages).map(([subj, avg]) => (
                            <tr key={subj} style={{ borderBottom: "1px solid #f5f5f5" }}>
                              <td style={{ padding: "8px 4px" }}>{SUBJECT_NAMES[subj] ?? subj}</td>
                              <td style={{ padding: "8px 4px" }}><b>{avg}分</b></td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="hint" style={{ padding: 24, textAlign: "center" }}>暂无各科作业成绩数据</p>
                  )}
                </div>
              ) : (
                <div className="panel" style={{ textAlign: "center", padding: 24 }}>暂无作业统计数据</div>
              )}
            </>
          ) : view === "class-analysis" || view === "subject-analysis" ? (
            <>
              <div className="page-title"><h2>{view === "class-analysis" ? "本班学情（全科）" : `学情分析（单科·${subjectName}）`}</h2><p>{view === "class-analysis" ? "本班各学科平均分、分数段分布与学生掌握度排行。" : `当前任教班级${subjectName}掌握度与分数分布。`}</p></div>
              {analyticsLoading ? (
                <div className="panel" style={{ textAlign: "center", padding: 24 }}>加载中…</div>
              ) : analyticsError ? (
                <div className="panel" style={{ textAlign: "center", padding: 24, color: "#c62828" }}>{analyticsError}</div>
              ) : classAnalytics ? (
                <div className="panel" style={{ padding: 24 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 16, marginBottom: 24 }}>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>班级平均分</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.class_average != null ? `${classAnalytics.class_average}分` : "暂无"}</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>提交率</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.submission_rate}%</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>错题率</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.mistake_rate}%</div></div>
                    <div style={{ background: "#fafafa", padding: 16, borderRadius: 8 }}><div style={{ fontSize: 12, color: "#888" }}>学生人数</div><div style={{ fontSize: 24, fontWeight: 700 }}>{classAnalytics.total_students}</div></div>
                  </div>
                  {view === "class-analysis" && Object.keys(classAnalytics.subject_averages).length > 0 && (
                    <div style={{ marginBottom: 24 }}>
                      <div className="student-section-title" style={{ marginBottom: 8 }}><span />各学科平均分</div>
                      <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
                        {Object.entries(classAnalytics.subject_averages).map(([subj, avg]) => (
                          <div key={subj} style={{ background: "#fafafa", padding: "8px 16px", borderRadius: 8 }}>
                            <span style={{ marginRight: 8 }}>{SUBJECT_NAMES[subj] ?? subj}</span>
                            <b>{avg}分</b>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <div style={{ marginBottom: 24 }}>
                    <div className="student-section-title" style={{ marginBottom: 8 }}><span />分数段分布</div>
                    <div style={{ display: "flex", gap: 12 }}>
                      <div style={{ flex: 1, background: "#ffebee", padding: 12, borderRadius: 8, textAlign: "center" }}><div style={{ fontSize: 12, color: "#888" }}>{`< 60`}</div><div style={{ fontSize: 20, fontWeight: 700 }}>{classAnalytics.score_distribution.lt60}</div></div>
                      <div style={{ flex: 1, background: "#fff3e0", padding: 12, borderRadius: 8, textAlign: "center" }}><div style={{ fontSize: 12, color: "#888" }}>60-79</div><div style={{ fontSize: 20, fontWeight: 700 }}>{classAnalytics.score_distribution["60_79"]}</div></div>
                      <div style={{ flex: 1, background: "#e8f5e9", padding: 12, borderRadius: 8, textAlign: "center" }}><div style={{ fontSize: 12, color: "#888" }}>80-100</div><div style={{ fontSize: 20, fontWeight: 700 }}>{classAnalytics.score_distribution["80_100"]}</div></div>
                    </div>
                  </div>
                  <div>
                    <div className="student-section-title" style={{ marginBottom: 8 }}><span />学生掌握度排行</div>
                    <table style={{ width: "100%", borderCollapse: "collapse" }}>
                      <thead><tr style={{ borderBottom: "1px solid #eee" }}><th style={{ textAlign: "left", padding: "8px 4px" }}>姓名</th><th style={{ textAlign: "left", padding: "8px 4px" }}>综合掌握度</th><th style={{ textAlign: "left", padding: "8px 4px" }}>薄弱学科</th></tr></thead>
                      <tbody>
                        {classAnalytics.student_ranking.map((r, i) => (
                          <tr key={i} style={{ borderBottom: "1px solid #f5f5f5" }}>
                            <td style={{ padding: "8px 4px" }}>{r.name}</td>
                            <td style={{ padding: "8px 4px" }}>{r.overall != null ? `${r.overall}分` : "暂无"}</td>
                            <td style={{ padding: "8px 4px" }}>{r.weak_subjects.length > 0 ? r.weak_subjects.join("、") : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div className="panel" style={{ textAlign: "center", padding: 24 }}>暂无学情数据</div>
              )}
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
