/** 页面角色只取已恢复的本页会话；班级、学科与资源权限由后端判定。 */
export function isRoleAllowed(pathname: string, role: "teacher" | "student" | null): boolean {
  if (role !== "teacher" && role !== "student") return false;
  if (/^\/teacher(\/|$)/.test(pathname)) return role === "teacher";
  if (/^\/student(\/|$)/.test(pathname)) return role === "student";
  return true;
}
