"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { ClassSelector } from "./class-selector";
import type { NavItem } from "./app-layout";
import { useAuthStore } from "@/lib/store";

export const SUBJECT_NAMES: Record<string, string> = {
  math: "数学", english: "英语", chinese: "语文", physics: "物理", chemistry: "化学", biology: "生物",
};

export function findTeacherNavItem(items: NavItem[], key: string): NavItem | undefined {
  return items.find((item) => item.key === key)
    ?? items.flatMap((item) => item.children ?? []).find((item) => item.key === key);
}

/** 三个教师页面共用同一导航，班主任身份由会话中的带班班级判定。 */
export function useTeacherNavigation() {
  const router = useRouter();
  const params = useSearchParams();
  const pathname = usePathname();
  const teachingClasses = useAuthStore((s) => s.teachingClasses);
  const homeroomClassId = useAuthStore((s) => s.homeroomClassId);
  const subject = useAuthStore((s) => s.subject);
  const isHeadTeacher = homeroomClassId !== null;
  const isHomeroom = isHeadTeacher && (
    params.get("workspace") === "homeroom" || (params.get("workspace") === null && pathname === "/teacher")
  );
  const requestedClass = Number(params.get("class_id"));
  const teachingClassId = teachingClasses?.includes(requestedClass)
    ? requestedClass : teachingClasses?.[0] ?? null;
  const classId = isHomeroom ? homeroomClassId : teachingClassId;
  const subjectName = subject ? SUBJECT_NAMES[subject] ?? subject : "未设置学科";
  const workspace = isHomeroom ? "homeroom" : "teaching";

  const href = (view: string, scope = workspace, cid = classId) => {
    const query = new URLSearchParams({ workspace: scope, view });
    if (cid !== null) query.set("class_id", String(cid));
    return `/teacher?${query}`;
  };
  const homeroomHref = (view: string) => href(view, "homeroom", homeroomClassId);
  const teachingHref = (view: string) => href(view, "teaching", teachingClassId);
  const materialHref = (cid: number | null, scope = workspace) => {
    const query = new URLSearchParams({ workspace: scope });
    if (cid !== null) query.set("class_id", String(cid));
    return `/materials?${query}`;
  };
  const uploadHref = `/teacher/upload?${new URLSearchParams({
    workspace: "teaching", ...(teachingClassId !== null ? { class_id: String(teachingClassId) } : {}),
  })}`;
  const selectTeachingClass = (id: number, targetView?: string) => {
    if (pathname === "/materials" && !isHomeroom) {
      router.push(materialHref(id, "teaching"));
      return;
    }
    const query = new URLSearchParams({ workspace: "teaching", class_id: String(id) });
    const view = targetView ?? (pathname === "/teacher" && !isHomeroom ? params.get("view") : null);
    query.set("view", view ?? "students");
    router.push(`${isHomeroom ? "/teacher" : pathname}?${query}`);
  };

  const navItems: NavItem[] = [
    ...(isHeadTeacher ? [{
      key: "home", label: "本班首页", icon: "home", section: "班主任工作台", expanded: true,
      to: homeroomHref("home"),
      children: [
        { key: "class-students", label: "本班学生", icon: "students", to: homeroomHref("class-students"), description: "管理带班班级的学生名单、考勤等" },
        { key: "class-materials", label: "本班资料（全科）", icon: "doc", to: materialHref(homeroomClassId, "homeroom"), description: "查看本班所有学科的讲义，其他学科资料只读" },
        { key: "class-analysis", label: "本班学情（全科）", icon: "log", to: homeroomHref("class-analysis"), description: "本班各科掌握度与总分分布" },
        { key: "class-homework", label: "本班作业（总览）", icon: "tools", to: homeroomHref("class-homework"), description: "查看各科提交率和平均分，只读、不批改" },
        { key: "class-notices", label: "班级通知/公告", icon: "chat", to: homeroomHref("class-notices"), description: "发布班级事务" },
      ],
    }] : []),
    {
      key: "teaching", label: "任课管理", icon: "books", section: "任课教学", expanded: true,
      to: teachingHref("students"),
      accessory: <div className="nav-class-selector"><ClassSelector value={teachingClassId} onChange={selectTeachingClass} /></div>,
      children: [
        { key: "students", label: "班级学生", icon: "students", to: teachingHref("students"), description: "任教班级学生名单，仅限本科目视角" },
        { key: "subject-materials", label: "本班资料（单科）", icon: "doc", to: materialHref(teachingClassId, "teaching"), description: `查看当前任教班级已发布的${subjectName}资料` },
        { key: "subject-analysis", label: "学情分析（单科）", icon: "log", to: teachingHref("subject-analysis"), description: `仅展示${subjectName}掌握度，不包含其他学科` },
        { key: "tools", label: "作业与改分", icon: "tools", to: teachingHref("tools"), description: "布置、批改本学科作业，查看本学科统计" },
        { key: "upload", label: "单科资料发布", icon: "upload", to: uploadHref, description: "发布本学科讲义到对应任教班级" },
      ],
    },
    { key: "research-materials", label: "教研组资料", icon: "books", section: "教研中心", to: "/teacher/library", description: "组内教师版素材、学生版预览与分班发布" },
    { key: "lesson-prep", label: "智能备课", icon: "robot", section: "教研中心", to: "/teacher/lesson-prep", description: "选择组内资料生成教案，定稿后发布学生教案与讲义" },
    { key: "lesson-quiz", label: "智能命题", icon: "edit", section: "教研中心", to: "/teacher/quiz", description: "命题生成、逐题复核、学科题库与组卷发布" },
    { key: "research-qa", label: "教研问答", icon: "chat", section: "教研中心", to: href("research-qa"), description: "仅限本学科组共享问答" },
    { key: "case-analysis", label: "课例分析", icon: "search", section: "教研中心", to: href("case-analysis"), description: "仅限本学科组课例批注" },
    { key: "agent", label: "助手配置", icon: "robot", section: "系统与统计", to: teachingHref("agent"), description: "选择任教班级，配置 AI 提示词与技能" },
    ...(isHeadTeacher ? [{ key: "audit", label: "审计与统计", icon: "audit", section: "系统与统计", to: homeroomHref("audit"), description: "仅查看带班班级的审计与统计" }] : []),
  ];

  const navHeader = <>
    <div className="nav-scope-label">{subjectName}教研组 · {isHomeroom ? "班主任视角" : "任课教师视角"}</div>
  </>;

  return {
    navItems, navHeader, classId, teachingClassId, isHomeroom, isHeadTeacher, homeroomClassId,
    subject, subjectName, href, materialHref, uploadHref, selectTeachingClass,
    onNavigate: (key: string) => {
      const item = findTeacherNavItem(navItems, key);
      if (item?.to) router.push(item.to);
    },
    requestedView: params.get("view"),
  };
}
