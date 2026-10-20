import type { NavItem } from "@/components/app-layout";

export const STUDENT_NAV_ITEMS: NavItem[] = [
  { key: "home", label: "本班首页", icon: "home", section: "学生端", to: "/student" },
  { key: "materials", label: "讲义与检索", icon: "search", section: "学生端", to: "/materials" },
  { key: "assistant", label: "助手对话", icon: "chat", section: "学生端", to: "/student?view=assistant" },
  { key: "assignments", label: "交作业", icon: "assignment", section: "学生端", to: "/student?view=assignments" },
  { key: "mistakes", label: "错题", icon: "mistake", section: "学生端", to: "/student?view=mistakes" },
  { key: "analytics", label: "学情分析", icon: "analysis", section: "学生端", to: "/student?view=analytics" },
];

export function getStudentNavItem(key: string) {
  return STUDENT_NAV_ITEMS.find((item) => item.key === key);
}
