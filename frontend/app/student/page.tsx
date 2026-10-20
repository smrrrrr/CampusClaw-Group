"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { useState, useEffect, useCallback, useRef } from "react";
import { AuthGate } from "@/components/auth-guard";
import { AppShell } from "@/components/app-layout";
import { LogoutButton } from "@/components/logout-button";
import MarkdownAnswer from "@/components/markdown-answer";
import {
  api,
  streamChat,
  type AnswerCitation,
  type ConversationItemDTO,
  type ConversationMessageDTO,
  type AssistantSubject,
  type StudentAssistantConfigDTO,
} from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { getStudentNavItem, STUDENT_NAV_ITEMS } from "@/components/student-navigation";
import { RecentHistory } from "@/components/recent-history";
import { historyKey } from "@/lib/recent-history";
import { useRecentHistory } from "@/lib/use-recent-history";

type StudentView = "home" | "assistant" | "assignments" | "mistakes" | "analytics";

const DEMO_ASSIGNMENTS = [
  { title: "一元二次方程练习", detail: "解方程 x²−5x+6=0，并说明所用方法与判别式。", due: "2026-09-10 23:59", status: "已批改", score: 95, feedback: "很好，过程完整，加 3 分鼓励。" },
  { title: "函数单调性判断", detail: "判断 f(x)=x²−4x 在（2，+∞）上的单调性并给出理由。", due: "2026-09-11 23:59", status: "错题", score: 60, feedback: "结论有误。二次函数在对称轴右侧为增函数。" },
];

const DEMO_SUBJECTS = ["数学", "语文", "英语", "物理", "化学"];
const ASSISTANT_SUBJECTS: { id: AssistantSubject; name: string; icon: string }[] = [
  { id: "math", name: "数学", icon: "🔢" }, { id: "chinese", name: "语文", icon: "📖" },
  { id: "english", name: "英语", icon: "🔤" }, { id: "physics", name: "物理", icon: "⚛️" },
  { id: "chemistry", name: "化学", icon: "🧪" },
];

function StudentDashboard({
  name,
  className,
  onNavigate,
}: {
  name: string;
  className: string;
  onNavigate: (view: string) => void;
}) {
  const stats = [
    { value: "10", label: "本班讲义", tone: "red" },
    { value: "10", label: "进行中作业", tone: "blue" },
    { value: "8", label: "待提交", tone: "gold" },
    { value: "1", label: "我的错题", tone: "red" },
  ];
  const shortcuts = [
    { icon: "💬", title: "向助手提问", detail: "解题引导 · 流式回答 · 引用讲义来源", view: "assistant" },
    { icon: "🔎", title: "检索讲义", detail: "在本班知识库中查找带来源的资料", view: "materials" },
    { icon: "📤", title: "提交作业", detail: "查看待完成作业并提交答案", view: "assignments" },
    { icon: "❕", title: "错题讲解", detail: "复习错题并查看分析建议", view: "mistakes" },
    { icon: "📈", title: "学情分析", detail: "查看各学科掌握度与近期趋势", view: "analytics" },
  ];

  return (
    <div className="student-page">
      <div className="page-title student-welcome">
        <h2>你好，{name} 👋</h2>
        <p>这里是 {className} 的学习空间。所有内容仅限本班可见。</p>
      </div>
      <div className="student-stat-grid">
        {stats.map((stat) => <div className="student-stat-card" key={stat.label}>
          <strong className={stat.tone}>{stat.value}</strong><span>{stat.label}</span>
        </div>)}
      </div>
      <div className="student-section-title"><span />快速开始</div>
      <div className="student-shortcut-grid">
        {shortcuts.map((item) => <button className="student-shortcut-card" key={item.title} onClick={() => onNavigate(item.view)}>
          <span className="student-shortcut-icon">{item.icon}</span>
          <strong>{item.title}</strong>
          <span className="student-shortcut-detail">{item.detail}</span>
        </button>)}
      </div>
      <div className="student-demo-note">演示提示：先在「助手对话」体验解题引导，再到「交作业」提交并观察批改结果，最后到「错题」查看错题讲解。</div>
    </div>
  );
}

function StudentAssignments({ onNavigate }: { onNavigate: (view: string) => void }) {
  return <div className="student-page">
    <div className="page-title"><h2>交作业</h2><p>提交后作业会进入批改队列；处理完成后可查看分数和评语。</p></div>
    <div className="student-subject-tabs">{DEMO_SUBJECTS.map((subject, index) => <button className={index === 0 ? "active" : ""} key={subject}>{subject}</button>)}</div>
    <div className="student-demo-note">演示提示：「函数单调性判断」的示例答案故意留有一个常见错误，提交后会判断并进入「错题」。</div>
    <div className="student-assignment-list">
      {DEMO_ASSIGNMENTS.map((item) => <article className="student-assignment-card" key={item.title}>
        <div className="student-assignment-top"><div><h3>{item.title}</h3><p>{item.detail}</p><span className="hint">截止：{item.due}</span></div><span className={`student-status ${item.status === "错题" ? "wrong" : "done"}`}>{item.status}</span></div>
        <div className="student-answer-label">我的作答</div>
        <div className="student-answer-box">{item.title === "一元二次方程练习" ? "x²−5x+6=0，用十字相乘得 (x−2)(x−3)=0，所以 x=2 或 x=3。判别式 Δ=1>0。" : "f(x)=x²−4x 在 (2,+∞) 上是减函数，因为开口向上。"}</div>
        <div className="student-grade-row"><strong className={item.status === "错题" ? "wrong" : ""}>{item.score}</strong><div><b>教师终评</b><span>{item.status === "错题" ? "本题判错，已进入错题" : "本题正确"}</span></div></div>
        <div className="student-feedback">{item.feedback}<small>依据《一元二次方程与求根公式》例题 1、第 2 页。</small></div>
        {item.status === "错题" && <button className="btn" style={{ width: "auto", marginTop: 12 }} onClick={() => onNavigate("mistakes")}>查看错题讲解</button>}
      </article>)}
    </div>
  </div>;
}

function StudentMistakes({ onNavigate }: { onNavigate: (view: string) => void }) {
  return <div className="student-page">
    <div className="page-title"><h2>错题</h2><p>判错的题目会进入这里，可请「错题讲解」技能分析错因。</p></div>
    <div className="student-mistake-card">
      <span className="student-status wrong">❕ 函数单调性判断</span>
      <div className="student-answer-label">题目</div>
      <p>判断 f(x)=x²−4x 在（2，+∞）上的单调性并给出理由。</p>
      <div className="student-answer-label">我的作答</div>
      <div className="student-answer-box">f(x)=x²−4x 在（2,+∞）上是减函数，因为开口向上。</div>
      <div className="student-answer-label">错因</div>
      <p>把对称轴右侧误判为减函数；未用作差法或导数验证。</p>
      <button className="btn" style={{ width: "auto", marginTop: 8 }} onClick={() => onNavigate("assistant")}>请助手讲解</button>
    </div>
  </div>;
}

function StudentAnalytics({ name }: { name: string }) {
  const bars = [{ name: "数学", score: 65 }, { name: "语文", score: 61 }, { name: "英语", score: 59 }, { name: "物理", score: 64 }, { name: "化学", score: 65 }];
  return <div className="student-page">
    <div className="page-title"><h2>学情分析 · {name}</h2><p>覆盖本班开设的各学科，由 AI 依据提问、作业与错题生成个性化学习画像（演示数据）。</p></div>
    <div className="student-stat-grid">
      {[{ value: "0", label: "累计提问", tone: "red" }, { value: "2", label: "作业提交", tone: "blue" }, { value: "50%", label: "作业正确率", tone: "green" }, { value: "1", label: "错题累计", tone: "red" }].map((stat) => <div className="student-stat-card" key={stat.label}><strong className={stat.tone}>{stat.value}</strong><span>{stat.label}</span></div>)}
    </div>
    <div className="student-analysis-grid">
      <section className="student-panel"><div className="student-section-title"><span />各学科掌握度</div><div className="student-radar-wrap"><svg viewBox="0 0 280 260" role="img" aria-label="各学科掌握度雷达图"><g transform="translate(140 128)" fill="none" stroke="#e4e7ec">{[30,55,80,105].map((r) => <polygon key={r} points={`0,-${r} ${r * .95},-${r * .31} ${r * .59},${r * .81} -${r * .59},${r * .81} -${r * .95},-${r * .31}`} />)}<path d="M0-105V105M-100-32l200 64M-59 85l118-170M59 85L-59-85M100-32l-200 64" /></g><polygon points="140,74 202,108 165,176 108,180 83,110" fill="rgba(139,21,56,.2)" stroke="#a30b0b" strokeWidth="2.5" />{[[140,74],[202,108],[165,176],[108,180],[83,110]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r="3.5" fill="#a30b0b" />)}<text x="140" y="15" textAnchor="middle">数学</text><text x="265" y="112" textAnchor="middle">语文</text><text x="200" y="250" textAnchor="middle">英语</text><text x="80" y="250" textAnchor="middle">物理</text><text x="15" y="112" textAnchor="middle">化学</text></svg><div className="student-score-ring"><strong>63%</strong><span>综合掌握</span></div></div></section>
      <section className="student-panel"><div className="student-section-title"><span />近期成绩趋势</div><svg className="student-trend-chart" viewBox="0 0 500 160" role="img" aria-label="近期成绩趋势"><path d="M15 110 L90 100 L165 103 L240 85 L315 89 L390 65 L465 103 L465 150 L15 150Z" fill="rgba(163,11,11,.1)"/><polyline points="15,110 90,100 165,103 240,85 315,89 390,65 465,103" fill="none" stroke="#a30b0b" strokeWidth="3" />{[[15,110],[90,100],[165,103],[240,85],[315,89],[390,65],[465,103]].map(([x,y],i)=><circle key={i} cx={x} cy={y} r="4" fill="#fff" stroke="#a30b0b" strokeWidth="2" />)}</svg><div className="student-section-title"><span />各学科掌握热力</div>{bars.map((bar) => <div className="student-progress-row" key={bar.name}><span>{bar.name}</span><div><i style={{ width: `${bar.score}%` }} /></div><b>{bar.score}</b></div>)}</section>
    </div>
    <section className="student-profile-panel"><div className="student-section-title"><span />🧠 AI 学习画像</div><div className="student-profile-body"><div><p>学习风格：<b>归纳总结型</b></p><div className="student-tag-row"><span>归纳总结型</span><span>强科·数学</span><span>待提升·英语</span></div><article><b>💡 学习建议</b><p>建议优先巩固「英语」，围绕本学科讲义要点多做基础题；同时保持「数学」的学习手感，形成跨学科的正向迁移。</p></article></div><div className="student-strength-box"><b>优势知识点</b><p>✅ 数学</p><p>✅ 化学</p><hr/><b className="warn">待提升知识点</b><p>⚠️ 语文</p><p>⚠️ 英语</p></div></div></section>
  </div>;
}

function StudentHome() {
  const currentStudent = useAuthStore((s) => s.currentStudent);
  const router = useRouter();
  const searchParams = useSearchParams();
  const requestedView = searchParams.get("view");
  const selectedSubject = ASSISTANT_SUBJECTS.find((s) => s.id === searchParams.get("subject")) ?? ASSISTANT_SUBJECTS[0];
  const questionHistory = useRecentHistory(historyKey(currentStudent?.id, currentStudent?.class_id, "assistant", selectedSubject.id));
  const questionInput = useRef<HTMLInputElement>(null);
  const view: StudentView = requestedView === "assistant" || requestedView === "assignments" || requestedView === "mistakes" || requestedView === "analytics"
    ? requestedView
    : "home";
  const studentName = currentStudent?.name ?? "同学";
  const className = currentStudent?.class_id === 101 ? "高二（1）班" : currentStudent?.class_id === 102 ? "高二（2）班" : `班级 ${currentStudent?.class_id ?? "—"}`;
  const navigate = (key: string) => {
    const item = getStudentNavItem(key);
    if (item?.to) router.push(item.to);
  };

  // 班级数据隔离：未分配班级时展示空状态，不发 API 请求
  const hasClass = currentStudent?.class_id != null;

  // 打开/下载命中的原始文件（标注出处，可回溯原文）
  const openOriginal = (c: AnswerCitation) => {
    if (!c.file_sha256) {
      setError("这条历史来源没有文件版本记录，请重新提问核对。");
      return;
    }
    const token = useAuthStore.getState().accessToken;
    fetch(api.materialDownloadUrl(c.material_id, c.file_sha256), {
      headers: { Authorization: `Bearer ${token}` },
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail ?? "原文加载失败");
        }
        return res.blob();
      })
      .then((blob) => {
        const objUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = objUrl;
        a.download = c.filename;
        a.click();
        URL.revokeObjectURL(objUrl);
      }).catch((e) => setError(e instanceof Error ? e.message : "原文加载失败"));
  };

  // 多轮会话状态
  const [conversations, setConversations] = useState<ConversationItemDTO[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ConversationMessageDTO[]>([]);
  const [question, setQuestion] = useState("");
  const [remaining, setRemaining] = useState<number | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [streamText, setStreamText] = useState("");
  const [streamCites, setStreamCites] = useState<AnswerCitation[]>([]);
  const [error, setError] = useState("");
  const [assistantConfig, setAssistantConfig] = useState<StudentAssistantConfigDTO | null>(null);
  const [assistantLoading, setAssistantLoading] = useState(false);
  const subjectVersion = useRef(0);
  const currentConfig = assistantConfig?.subject === selectedSubject.id ? assistantConfig : null;
  const assistantReady = currentConfig !== null && !assistantLoading;
  const visibleMessages = currentConfig ? messages : [];

  const loadConversations = useCallback(async () => {
    const version = subjectVersion.current;
    try {
      const list = await api.listConversations(selectedSubject.id);
      if (version !== subjectVersion.current) return;
      setConversations(list);
    } catch {
      /* 列表加载失败不阻塞 */
    }
  }, [selectedSubject.id]);

  // 每个科目独立加载教师配置和会话，不沿用其他科目的上下文。
  useEffect(() => {
    if (!hasClass || view !== "assistant") return;
    const version = ++subjectVersion.current;
    setActiveId(null);
    setConversations([]);
    setMessages([]);
    setAssistantConfig(null);
    setAssistantLoading(true);
    setQuestion("");
    setRemaining(null);
    setStreamText("");
    setStreamCites([]);
    setStreaming(false);
    setError("");
    Promise.all([api.getStudentAssistantConfig(selectedSubject.id), api.listConversations(selectedSubject.id)])
      .then(([config, list]) => {
        if (version !== subjectVersion.current) return;
        setAssistantConfig(config);
        setConversations(list);
      })
      .catch((e) => { if (version === subjectVersion.current) setError(e instanceof Error ? e.message : "加载学科助手失败"); })
      .finally(() => { if (version === subjectVersion.current) setAssistantLoading(false); });
    return () => { subjectVersion.current += 1; };
  }, [hasClass, currentStudent?.id, currentStudent?.class_id, selectedSubject.id, view]);

  const selectConversation = async (id: number) => {
    if (streaming) return;
    const version = subjectVersion.current;
    setActiveId(id);
    setError("");
    try {
      const [msgs, config] = await Promise.all([api.getConversationMessages(id), api.getStudentAssistantConfig(selectedSubject.id, id)]);
      if (version !== subjectVersion.current) return;
      setMessages(msgs);
      setAssistantConfig(config);
    } catch {
      /* 忽略 */
    }
  };

  const newConversation = async () => {
    if (streaming || !assistantReady) return;
    const version = subjectVersion.current;
    setAssistantLoading(true);
    try {
      const c = await api.createConversation(undefined, selectedSubject.id);
      if (version !== subjectVersion.current) return;
      setConversations((prev) => [c, ...prev]);
      setActiveId(c.id);
      setMessages([]);
      setError("");
    } catch (e) { if (version === subjectVersion.current) setError(e instanceof Error ? e.message : "创建对话失败"); }
    finally { if (version === subjectVersion.current) setAssistantLoading(false); }
  };

  const removeConversation = async (id: number) => {
    if (streaming) return;
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "删除失败");
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || streaming || !assistantReady) return;
    setError("");

    let cid = activeId;
    const version = subjectVersion.current;
    if (cid == null) {
      setStreaming(true);
      let c: ConversationItemDTO;
      try { c = await api.createConversation(undefined, selectedSubject.id); }
      catch (e) { setError(e instanceof Error ? e.message : "创建对话失败"); setStreaming(false); return; }
      if (version !== subjectVersion.current) return;
      setConversations((prev) => [c, ...prev]);
      cid = c.id;
      setActiveId(c.id);
    }

    questionHistory.add(q);
    // 乐观展示用户消息
    setMessages((prev) => [
      ...prev,
      { id: -Date.now(), role: "user", content: q, sources: [], created_at: "" },
    ]);
    setQuestion("");
    setStreaming(true);
    setStreamText("");
    setStreamCites([]);

    // 局部累加，避免回调内读取过期的 state
    let acc = "";
    await streamChat(cid, q, {
      onDelta: (t) => {
        if (version !== subjectVersion.current) return;
        acc += t;
        setStreamText(acc);
      },
      onDone: (d) => {
        if (version !== subjectVersion.current) return;
        setMessages((prev) => [
          ...prev,
          {
            id: -Date.now() - 1,
            role: "assistant",
            content: d.answer,
            sources: d.citations,
            created_at: "",
          },
        ]);
        setRemaining(d.remaining);
        setStreamText("");
        setStreamCites([]);
        setStreaming(false);
        loadConversations();
      },
      onError: (m, citations) => {
        if (version !== subjectVersion.current) return;
        // 已吐出部分内容时保留为答案
        if (acc || citations !== undefined) {
          setMessages((prev) => [
            ...prev,
            {
              id: -Date.now() - 2,
              role: "assistant",
              content: m,
              sources: citations ?? [],
              created_at: "",
            },
          ]);
        }
        setError(citations !== undefined ? "生成未完成，已保留可核对的内容与来源。" : m);
        setStreamText("");
        setStreamCites([]);
        setStreaming(false);
      },
    }).catch((e) => { if (version === subjectVersion.current) { setError(e instanceof Error ? e.message : "网络异常，请重试"); setStreaming(false); } });
  };

  return (
    <AppShell
      brandMark="S"
      subtitle="学习平台 · 学生端"
      navItems={STUDENT_NAV_ITEMS}
      active={view}
      onNavigate={navigate}
      headerLeft={<><span className="status-dot" /><span className="class-pill">{className}</span></>}
      headerRight={
        <>
          <span className="user-chip"><span className="avatar">生</span>{studentName}</span>
          <LogoutButton />
        </>
      }
      navFoot="学习空间 · 学习数据仅本人可见"
    >
      {!hasClass ? (
        <div className="student-page">
          <div className="student-empty panel"><h2>暂无班级</h2><p>你还未被分配到班级，请联系教师或管理员处理。</p></div>
        </div>
      ) : view === "home" ? (
        <StudentDashboard name={studentName} className={className} onNavigate={navigate} />
      ) : view === "assignments" ? (
        <StudentAssignments onNavigate={navigate} />
      ) : view === "mistakes" ? (
        <StudentMistakes onNavigate={navigate} />
      ) : view === "analytics" ? (
        <StudentAnalytics name={studentName} />
      ) : (
        <div className="student-page student-assistant-page">
          <div className="page-title"><h2>助手对话 · {selectedSubject.icon} {selectedSubject.name}学习助手</h2><p>{currentConfig?.teacher_name ? `${currentConfig.teacher_name} · ` : ""}根据本班任课教师配置，检索本学科资料并流式回答。</p></div>
          <div className="student-subject-tabs">{ASSISTANT_SUBJECTS.map((subject) => <button disabled={streaming || assistantLoading} className={subject.id === selectedSubject.id ? "active" : ""} key={subject.id} onClick={() => router.replace(`/student?view=assistant&subject=${subject.id}`)}>{subject.icon} {subject.name}</button>)}</div>
          <div className="student-skill-state">当前技能状态： {!assistantReady ? <span>正在加载教师配置…</span> : <b>{currentConfig?.tutor_enabled ? "● 解题引导已开启" : "○ 解题引导未开启"}</b>}<span>作业批改、错题讲解尚未接入</span></div>
          <div className="student-demo-note">{!assistantReady ? "正在切换学科助手…" : !currentConfig?.configured ? `本班${selectedSubject.name}老师尚未保存助手配置，暂使用默认助手。` : currentConfig.tutor_enabled ? "「解题引导」已开启：使用教师启用的固定引导框架，默认不直接给最终答案。" : "「解题引导」未开启：使用该科老师保存的提示词，留空时使用默认提示词。"}</div>
          <div className="content" style={{ padding: 0, maxWidth: "none" }}>
          <div className="card student-chat-card">
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 12,
              }}
            >
              <h3 style={{ margin: 0 }}>AI 解题助手</h3>
              <button
                className="btn"
                onClick={newConversation}
                disabled={streaming || !assistantReady}
                style={{ width: "auto", padding: "6px 14px" }}
              >
                新对话
              </button>
            </div>
            <p className="hint" style={{ marginBottom: 12 }}>
              支持连续追问，同一会话内记住前文
              {remaining !== null && `，今日剩余 ${remaining} 次`}
            </p>

            <div style={{ display: "flex", gap: 16, minHeight: 420 }}>
              {/* 左侧会话列表 */}
              <aside
                style={{
                  width: 220,
                  flexShrink: 0,
                  border: "1px solid #f3f4f6",
                  borderRadius: 8,
                  overflow: "auto",
                  maxHeight: 480,
                }}
              >
                {conversations.length === 0 ? (
                  <p className="hint" style={{ padding: 12 }}>
                    暂无会话，点击「新对话」开始
                  </p>
                ) : (
                  conversations.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => selectConversation(c.id)}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 4,
                        padding: "8px 10px",
                        cursor: "pointer",
                        fontSize: 13,
                        borderBottom: "1px solid #f3f4f6",
                        background: c.id === activeId ? "#fbeef2" : "transparent",
                        color: c.id === activeId ? "#8b1538" : "#374151",
                      }}
                    >
                      <span
                        style={{
                          flex: 1,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={c.title}
                      >
                        {c.title}
                      </span>
                      <button
                        title="删除会话"
                        onClick={(e) => {
                          e.stopPropagation();
                          removeConversation(c.id);
                        }}
                        style={{
                          border: "none",
                          background: "transparent",
                          color: "#9ca3af",
                          cursor: "pointer",
                          fontSize: 14,
                          lineHeight: 1,
                          padding: "2px 4px",
                        }}
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </aside>

              {/* 右侧消息线程 */}
              <section style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: 12 }}>
                {error && <div className="error" style={{ margin: 0 }}>{error}</div>}
                <div
                  style={{
                    flex: 1,
                    border: "1px solid #f3f4f6",
                    borderRadius: 8,
                    padding: 12,
                    overflow: "auto",
                    maxHeight: 380,
                    background: "#fafafa",
                  }}
                >
                  {visibleMessages.length === 0 && !streaming ? (
                    <p className="hint" style={{ padding: 8 }}>
                      输入问题开始对话，或选择一个历史会话继续追问。
                    </p>
                  ) : (
                    visibleMessages.map((m) => (
                      <div key={m.id} style={{ marginBottom: 12 }}>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "flex-start",
                            gap: 8,
                          }}
                        >
                          <span
                            style={{
                              flexShrink: 0,
                              fontSize: 12,
                              fontWeight: 700,
                              marginTop: 4,
                              color: m.role === "user" ? "#2563eb" : "#8b1538",
                            }}
                          >
                            {m.role === "user" ? "我" : "AI"}
                          </span>
                          <div style={{ flex: 1 }}>
                            {m.role === "user" ? (
                              <div
                                style={{
                                  background: "#fff",
                                  padding: 8,
                                  borderRadius: 8,
                                  fontSize: 14,
                                  whiteSpace: "pre-wrap",
                                }}
                              >
                                {m.content}
                              </div>
                            ) : (
                              <>
                                <div style={{ background: "#fff", padding: 8, borderRadius: 8, fontSize: 14 }}>
                                  <MarkdownAnswer text={m.content} />
                                </div>
                                {m.sources.length > 0 && (
                                  <div
                                    style={{
                                      marginTop: 8,
                                      background: "#fff",
                                      border: "1px solid #e5e7eb",
                                      padding: 10,
                                      borderRadius: 8,
                                    }}
                                  >
                                    <strong style={{ fontSize: 12 }}>参考资料（可核对原文）</strong>
                                    <ul style={{ margin: "8px 0 0", paddingLeft: 16, fontSize: 12, lineHeight: 1.5 }}>
                                      {m.sources.map((c, index) => (
                                        <li key={`${c.material_id}-${c.chunk_index}`} style={{ marginBottom: 6 }}>
                                          <span style={{ color: "#8b1538", fontWeight: 600 }}>[{c.reference_id ?? index + 1}] {c.filename}</span>
                                          <span className="hint"> · 第 {c.chunk_index} 块</span>
                                          {!c.file_sha256 && <span className="hint">（历史来源未记录版本）</span>}
                                          <button
                                            className="btn"
                                            style={{ width: "auto", padding: "1px 8px", fontSize: 11, marginLeft: 6 }}
                                            onClick={() => openOriginal(c)}
                                            disabled={!c.file_sha256}
                                          >
                                            查看原文
                                          </button>
                                          <div className="citation-excerpt">
                                            <MarkdownAnswer text={c.excerpt} />
                                          </div>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                  {streaming && (
                    <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                      <span style={{ flexShrink: 0, fontSize: 12, fontWeight: 700, marginTop: 4, color: "#8b1538" }}>
                        AI
                      </span>
                      <div style={{ flex: 1, background: "#fff", padding: 8, borderRadius: 8, fontSize: 14 }}>
                        <p className="hint">生成中，引用编号将在完成后核对。</p>
                        <MarkdownAnswer text={streamText + "▍"} />
                      </div>
                    </div>
                  )}
                </div>

                <form onSubmit={handleSend} style={{ display: "flex", gap: 8 }}>
                  <input
                    ref={questionInput}
                    className="input"
                    style={{ flex: 1, minWidth: 0 }}
                    placeholder="输入你的问题，回车发送…"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    disabled={streaming || !assistantReady}
                  />
                  <button
                    className="btn"
                    style={{ width: "auto", padding: "8px 18px" }}
                    type="submit"
                    disabled={streaming || !assistantReady || !question.trim()}
                  >
                    {streaming ? "生成中…" : "发送"}
                  </button>
                </form>
                <RecentHistory label="提问历史" entries={questionHistory.entries} onClear={questionHistory.clear}
                  disabled={streaming || !assistantReady} fillOnly onSelect={(value) => {
                    setQuestion(value);
                    questionInput.current?.focus();
                  }} />
              </section>
            </div>

          </div>
          </div>
        </div>
      )}
    </AppShell>
  );
}

export default function StudentPage() {
  return (
    <AuthGate>
      <Suspense fallback={<div className="centered">加载中…</div>}>
        <StudentHome />
      </Suspense>
    </AuthGate>
  );
}
