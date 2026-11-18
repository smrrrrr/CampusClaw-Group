/** 页面角色只取已恢复的本页会话；班级、学科与资源权限由后端判定。 */
export function getRouteRole(pathname: string): "teacher" | "student" | undefined {
  if (/^\/teacher(\/|$)/.test(pathname)) return "teacher";
  if (/^\/student(\/|$)/.test(pathname)) return "student";
}

export function isRoleAllowed(pathname: string, role: "teacher" | "student" | null): boolean {
  if (role !== "teacher" && role !== "student") return false;
  const required = getRouteRole(pathname);
  return required === undefined || required === role;
}
