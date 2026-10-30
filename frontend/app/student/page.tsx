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
  type ChatMetaData,
  type StudentHomeworkDTO,
  type MistakeDTO,
  type StudentOverviewDTO,
  type StudentMasteryDTO,
  type StudentPortraitDTO,
} from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { getStudentNavItem, STUDENT_NAV_ITEMS } from "@/components/student-navigation";
import { RecentHistory } from "@/components/recent-history";
import { historyKey } from "@/lib/recent-history";
import { useRecentHistory } from "@/lib/use-recent-history";

type StudentView = "home" | "assistant" | "assignments" | "mistakes" | "analytics";

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
  ongoingHomework,
  pendingSubmit,
  mistakeCount,
}: {
  name: string;
  className: string;
  onNavigate: (view: string) => void;
  ongoingHomework: number;
  pendingSubmit: number;
  mistakeCount: number;
}) {
  const stats = [
    { value: "10", label: "本班讲义", tone: "red" },
    { value: String(ongoingHomework), label: "进行中作业", tone: "blue" },
    { value: String(pendingSubmit), label: "待提交", tone: "gold" },
    { value: String(mistakeCount), label: "我的错题", tone: "red" },
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
  const [homeworks, setHomeworks] = useState<StudentHomeworkDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState<number | null>(null);
  const [selectedSubject, setSelectedSubject] = useState<string>("");

  const loadHomeworks = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const list = await api.listStudentHomeworks();
      setHomeworks(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载作业失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadHomeworks(); }, [loadHomeworks]);

  const subjectTabs = [{ id: "", name: "全部" }, ...ASSISTANT_SUBJECTS];
  const filteredHomeworks = selectedSubject
    ? homeworks.filter((h) => h.subject === selectedSubject)
    : homeworks;

  const handleSubmit = async (hw: StudentHomeworkDTO) => {
    const text = answers[hw.id] ?? "";
    if (!text.trim()) return;
    setSubmitting(hw.id);
    try {
      await api.submitHomework(hw.id, text);
      await loadHomeworks();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(null);
    }
  };

  const isOverdue = (dueAt: string | null) => {
    if (!dueAt) return false;
    return new Date(dueAt).getTime() < Date.now();
  };

  return <div className="student-page">
    <div className="page-title"><h2>交作业</h2><p>提交后作业会进入批改队列；处理完成后可查看分数和评语。</p></div>
    <div className="student-subject-tabs">{subjectTabs.map((s) => <button className={selectedSubject === s.id ? "active" : ""} key={s.id} onClick={() => setSelectedSubject(s.id)}>{s.name}</button>)}</div>
    {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
    {loading ? (
      <p className="hint">加载中…</p>
    ) : filteredHomeworks.length === 0 ? (
      <div className="student-empty panel"><h2>暂无作业</h2><p>本班该学科目前没有待完成的作业。</p></div>
    ) : (
      <div className="student-assignment-list">
        {filteredHomeworks.map((hw) => {
          const submitted = hw.status !== "not_submitted";
          const overdue = isOverdue(hw.due_at);
          const statusLabel = submitted ? (hw.graded ? "已批改" : "待批改") : (overdue ? "已截止" : "未提交");
          return (
            <article className="student-assignment-card" key={hw.id}>
              <div className="student-assignment-top">
                <div>
                  <h3>{hw.title}</h3>
                  <p>{hw.content?.stem ?? hw.title}</p>
                  <span className="hint">截止：{hw.due_at ?? "无"}</span>
                </div>
                <span className={`student-status ${hw.graded && (hw.final_score ?? 0) < 60 ? "wrong" : submitted ? "done" : ""}`}>{statusLabel}</span>
              </div>
              {submitted && hw.submission_id && (
                <>
                  <div className="student-grade-row">
                    <strong className={(hw.final_score ?? 0) < 60 ? "wrong" : ""}>{hw.graded ? hw.final_score : "—"}</strong>
                    <div><b>教师终评</b><span>{hw.graded ? "已批改" : "待教师批改"}</span></div>
                  </div>
                  {hw.feedback && <div className="student-feedback">{hw.feedback}</div>}
                  {hw.graded && (hw.final_score ?? 0) < 60 && (
                    <button className="btn" style={{ width: "auto", marginTop: 12 }} onClick={() => onNavigate("mistakes")}>查看错题讲解</button>
                  )}
                </>
              )}
              {!overdue && (
                <>
                  <div className="student-answer-label">我的作答</div>
                  <textarea
                    className="input"
                    style={{ width: "100%", minHeight: 80, resize: "vertical" }}
                    placeholder={submitted ? "可修改后重新提交" : "请输入你的答案…"}
                    value={answers[hw.id] ?? ""}
                    onChange={(e) => setAnswers((prev) => ({ ...prev, [hw.id]: e.target.value }))}
                  />
                  <button
                    className="btn"
                    style={{ width: "auto", marginTop: 8 }}
                    onClick={() => handleSubmit(hw)}
                    disabled={submitting === hw.id || !(answers[hw.id] ?? "").trim()}
                  >
                    {submitting === hw.id ? "提交中…" : submitted ? "重新提交" : "提交作业"}
                  </button>
                </>
              )}
            </article>
          );
        })}
      </div>
    )}
  </div>;
}

function StudentMistakes({ onNavigate }: { onNavigate: (view: string) => void }) {
  const [mistakes, setMistakes] = useState<MistakeDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [subject, setSubject] = useState<string>("");
  const [onlyUnmastered, setOnlyUnmastered] = useState(false);
  const [explainingId, setExplainingId] = useState<number | null>(null);
  const [explanations, setExplanations] = useState<Record<number, string>>({});

  const loadMistakes = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const list = await api.listStudentMistakes(subject || undefined, onlyUnmastered);
      setMistakes(list);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载错题失败");
    } finally {
      setLoading(false);
    }
  }, [subject, onlyUnmastered]);

  useEffect(() => { loadMistakes(); }, [loadMistakes]);

  const handleToggleMastered = async (m: MistakeDTO) => {
    try {
      const updated = await api.toggleMistakeMastered(m.id, !m.mastered);
      setMistakes((prev) => prev.map((x) => (x.id === m.id ? updated : x)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    }
  };

  const handleExplain = async (m: MistakeDTO) => {
    setExplainingId(m.id);
    try {
      const res = await api.explainMistake(m.id);
      const text = res.available && res.explanation ? res.explanation : "AI 讲解暂未配置，请联系教师。";
      setExplanations((prev) => ({ ...prev, [m.id]: text }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "讲解失败");
    } finally {
      setExplainingId(null);
    }
  };

  const subjectOptions: { value: string; label: string }[] = [
    { value: "", label: "全部学科" },
    { value: "math", label: "数学" },
    { value: "chinese", label: "语文" },
    { value: "english", label: "英语" },
    { value: "physics", label: "物理" },
    { value: "chemistry", label: "化学" },
  ];

  return (
    <div className="student-page">
      <div className="page-title">
        <h2>错题</h2>
        <p>判错的题目会进入这里，可按学科筛选、标记已掌握，或请 AI 分析错因。</p>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 16, flexWrap: "wrap" }}>
        <select className="input" style={{ width: "auto" }} value={subject} onChange={(e) => setSubject(e.target.value)}>
          {subjectOptions.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
        <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }}>
          <input type="checkbox" checked={onlyUnmastered} onChange={(e) => setOnlyUnmastered(e.target.checked)} />
          仅未掌握
        </label>
      </div>
      {error && <div className="student-demo-note" style={{ color: "#dc2626" }}>{error}</div>}
      {loading ? (
        <div className="student-demo-note">加载中…</div>
      ) : mistakes.length === 0 ? (
        <div className="student-demo-note">暂无错题记录。</div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {mistakes.map((m) => (
            <div className="student-mistake-card" key={m.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span className={`student-status ${m.mastered ? "done" : "wrong"}`}>
                  {m.mastered ? "✓ 已掌握" : "❕ 未掌握"} · {m.subject}
                </span>
                {m.homework_title && <span style={{ fontSize: 12, color: "#6b7280" }}>来源：{m.homework_title}</span>}
              </div>
              <div className="student-answer-label">题目</div>
              <p>{m.question_stem}</p>
              {m.student_answer && (
                <>
                  <div className="student-answer-label">我的作答</div>
                  <div className="student-answer-box">{m.student_answer}</div>
                </>
              )}
              {m.reason && (
                <>
                  <div className="student-answer-label">错因</div>
                  <p>{m.reason}</p>
                </>
              )}
              {explanations[m.id] && (
                <>
                  <div className="student-answer-label">AI 讲解</div>
                  <div style={{ whiteSpace: "pre-wrap", background: "#f9fafb", padding: 12, borderRadius: 8, fontSize: 14 }}>
                    {explanations[m.id]}
                  </div>
                </>
              )}
              <div style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}>
                <button className="btn" style={{ width: "auto" }} onClick={() => handleToggleMastered(m)}>
                  {m.mastered ? "取消掌握" : "标记已掌握"}
                </button>
                <button
                  className="btn"
                  style={{ width: "auto" }}
                  onClick={() => handleExplain(m)}
                  disabled={explainingId === m.id}
                >
                  {explainingId === m.id ? "讲解中…" : "AI 讲解"}
                </button>
                <button className="btn" style={{ width: "auto" }} onClick={() => onNavigate("assistant")}>
                  请助手讲解
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const RADAR_SUBJECTS = [
  { id: "math", name: "数学", angle: -Math.PI / 2 },
  { id: "chinese", name: "语文", angle: -Math.PI / 10 },
  { id: "english", name: "英语", angle: (3 * Math.PI) / 10 },
  { id: "physics", name: "物理", angle: (7 * Math.PI) / 10 },
  { id: "chemistry", name: "化学", angle: (11 * Math.PI) / 10 },
];

function StudentAnalytics({ name }: { name: string }) {
  const [overview, setOverview] = useState<StudentOverviewDTO | null>(null);
  const [mastery, setMastery] = useState<StudentMasteryDTO | null>(null);
  const [portrait, setPortrait] = useState<StudentPortraitDTO | null>(null);
  const [portraitAvailable, setPortraitAvailable] = useState(true);

  useEffect(() => {
    api.getStudentAnalyticsOverview().then(setOverview).catch(() => {});
    api.getStudentAnalyticsMastery().then(setMastery).catch(() => {});
    api.getStudentAnalyticsPortrait().then((r) => {
      setPortrait(r.portrait);
      setPortraitAvailable(r.available);
    }).catch(() => setPortraitAvailable(false));
  }, []);

  // 雷达图：5 个学科固定轴，掌握度映射到半径
  const masteryMap = new Map(mastery?.subjects.map((s) => [s.subject, s.mastery]) ?? []);
  const radarPoints = RADAR_SUBJECTS.map((sub) => {
    const m = masteryMap.get(sub.id);
    const r = m != null ? (105 * m) / 100 : 0;
    return { x: 140 + r * Math.cos(sub.angle), y: 128 + r * Math.sin(sub.angle) };
  });
  const radarPoly = radarPoints.map((p) => `${p.x},${p.y}`).join(" ");
  const overallText = mastery?.overall != null ? `${mastery.overall}%` : "—";

  // 趋势折线
  const trend = mastery?.trend ?? [];
  const trendPoints = trend.map((t, i) => {
    const x = trend.length > 1 ? 15 + (i / (trend.length - 1)) * 450 : 240;
    const y = 150 - (t.score / 100) * 120;
    return { x, y, score: t.score, title: t.title };
  });
  const trendPoly = trendPoints.map((p) => `${p.x},${p.y}`).join(" ");
  const trendArea = trend.length > 1 ? `${trendPoly} ${trendPoints[trendPoints.length - 1].x},150 ${trendPoints[0].x},150` : "";

  const stats = [
    { value: String(overview?.questions ?? 0), label: "累计提问", tone: "red" },
    { value: String(overview?.submissions ?? 0), label: "作业提交", tone: "blue" },
    { value: overview?.accuracy != null ? `${overview.accuracy}%` : "暂无", label: "作业正确率", tone: "green" },
    { value: String(overview?.mistakes ?? 0), label: "错题累计", tone: "red" },
  ];

  return <div className="student-page">
    <div className="page-title"><h2>学情分析 · {name}</h2><p>覆盖本班开设的各学科，由 AI 依据提问、作业与错题生成个性化学习画像。</p></div>
    <div className="student-stat-grid">
      {stats.map((stat) => <div className="student-stat-card" key={stat.label}><strong className={stat.tone}>{stat.value}</strong><span>{stat.label}</span></div>)}
    </div>
    <div className="student-analysis-grid">
      <section className="student-panel"><div className="student-section-title"><span />各学科掌握度</div><div className="student-radar-wrap"><svg viewBox="0 0 280 260" role="img" aria-label="各学科掌握度雷达图"><g transform="translate(140 128)" fill="none" stroke="#e4e7ec">{[30,55,80,105].map((r) => <polygon key={r} points={`0,-${r} ${r * .95},-${r * .31} ${r * .59},${r * .81} -${r * .59},${r * .81} -${r * .95},-${r * .31}`} />)}<path d="M0-105V105M-100-32l200 64M-59 85l118-170M59 85L-59-85M100-32l-200 64" /></g>{mastery && mastery.subjects.length > 0 && <polygon points={radarPoly} fill="rgba(139,21,56,.2)" stroke="#a30b0b" strokeWidth="2.5" />}{radarPoints.map((p, i) => masteryMap.get(RADAR_SUBJECTS[i].id) != null && <circle key={i} cx={p.x} cy={p.y} r="3.5" fill="#a30b0b" />)}<text x="140" y="15" textAnchor="middle">数学</text><text x="265" y="112" textAnchor="middle">语文</text><text x="200" y="250" textAnchor="middle">英语</text><text x="80" y="250" textAnchor="middle">物理</text><text x="15" y="112" textAnchor="middle">化学</text></svg><div className="student-score-ring"><strong>{overallText}</strong><span>综合掌握</span></div></div></section>
      <section className="student-panel"><div className="student-section-title"><span />近期成绩趋势</div>{trend.length > 0 ? <svg className="student-trend-chart" viewBox="0 0 500 160" role="img" aria-label="近期成绩趋势">{trendArea && <path d={`M${trendArea}Z`} fill="rgba(163,11,11,.1)" />}<polyline points={trendPoly} fill="none" stroke="#a30b0b" strokeWidth="3" />{trendPoints.map((p, i) => <circle key={i} cx={p.x} cy={p.y} r="4" fill="#fff" stroke="#a30b0b" strokeWidth="2" />)}</svg> : <p style={{ padding: "16px", color: "#888" }}>暂无成绩趋势</p>}<div className="student-section-title"><span />各学科掌握热力</div>{RADAR_SUBJECTS.map((sub) => { const m = masteryMap.get(sub.id); const score = m ?? 0; return <div className="student-progress-row" key={sub.id}><span>{sub.name}</span><div><i style={{ width: `${m != null ? score : 0}%` }} /></div><b>{m != null ? score : "—"}</b></div>; })}</section>
    </div>
    <section className="student-profile-panel"><div className="student-section-title"><span />🧠 AI 学习画像</div>{portraitAvailable && portrait ? <div className="student-profile-body"><div><p>学习风格：<b>{portrait.style || "—"}</b></p><div className="student-tag-row">{portrait.strengths.map((s) => <span key={`s-${s}`}>强科·{s}</span>)}{portrait.weaknesses.map((s) => <span key={`w-${s}`}>待提升·{s}</span>)}</div><article><b>💡 学习建议</b><p>{portrait.suggestion || "暂无"}</p></article></div><div className="student-strength-box"><b>优势知识点</b>{portrait.strengths.length > 0 ? portrait.strengths.map((s) => <p key={`ss-${s}`}>✅ {s}</p>) : <p>暂无</p>}<hr/><b className="warn">待提升知识点</b>{portrait.weaknesses.length > 0 ? portrait.weaknesses.map((s) => <p key={`ws-${s}`}>⚠️ {s}</p>) : <p>暂无</p>}</div></div> : <p style={{ padding: "16px", color: "#888" }}>AI 学习画像暂未配置，请联系教师。</p>}</section>
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

  // 首页作业统计：进行中作业数、待提交数
  const [ongoingHomework, setOngoingHomework] = useState(0);
  const [pendingSubmit, setPendingSubmit] = useState(0);
  const [mistakeCount, setMistakeCount] = useState(0);
  useEffect(() => {
    if (!hasClass) return;
    api.listStudentHomeworks().then((list) => {
      const now = Date.now();
      const ongoing = list.filter((h) => h.due_at ? new Date(h.due_at).getTime() >= now : true).length;
      const pending = list.filter((h) => h.status === "not_submitted" && (h.due_at ? new Date(h.due_at).getTime() >= now : true)).length;
      setOngoingHomework(ongoing);
      setPendingSubmit(pending);
    }).catch(() => { /* 统计加载失败不阻塞 */ });
    api.listStudentMistakes(undefined, true).then((list) => {
      setMistakeCount(list.length);
    }).catch(() => { /* 统计加载失败不阻塞 */ });
  }, [hasClass, currentStudent?.id]);

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
  const [streamMeta, setStreamMeta] = useState<ChatMetaData | null>(null);
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
    setStreamMeta(null);

    // 局部累加，避免回调内读取过期的 state
    let acc = "";
    await streamChat(cid, q, {
      onMeta: (m) => {
        if (version !== subjectVersion.current) return;
        setStreamMeta(m);
      },
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
        setStreamMeta(null);
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
        <StudentDashboard name={studentName} className={className} onNavigate={navigate} ongoingHomework={ongoingHomework} pendingSubmit={pendingSubmit} mistakeCount={mistakeCount} />
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
                        {streamMeta && (
                          <div className="student-tool-bar" data-testid="tool-bar">
                            <span className="student-tool-skill">🧩 {streamMeta.skill?.name}</span>
                            {(streamMeta.tool_calls ?? []).map((tc, i) => (
                              <span key={i} className={`student-tool-chip ${tc.status}`} title={tc.reason ?? ""}>
                                {tc.ref} · {tc.status === "ok" ? "成功" : tc.status === "denied" ? "被拒" : "错误"}
                              </span>
                            ))}
                          </div>
                        )}
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
