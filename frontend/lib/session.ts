"use client";

import { TokenDTO, setRoleCookies } from "./api";
import { useAuthStore } from "./store";

/** 将 TokenDTO 应用到全局会话（登录 / 改密后共用）。 */
export function applyTokenSession(
  data: TokenDTO,
  setSession: ReturnType<typeof useAuthStore.getState>["setSession"],
) {
  setSession({
    accessToken: data.access_token,
    userRole: data.role,
    mustChangePassword: data.must_change_password,
    currentStudent:
      data.role === "student"
        ? {
            id: data.user.id,
            name: data.user.name,
            class_id: data.user.class_id,
          }
        : null,
    teachingClasses: data.user.teaching_classes ?? null,
    subject: data.user.subject ?? null,
    homeroomClassId: data.user.homeroom_class_id ?? null,
  });
  setRoleCookies(data.role);
}
