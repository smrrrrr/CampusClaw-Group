"use client";

import { create } from "zustand";

export interface StudentInfo {
  id: number;
  name: string | null;
  class_id: number | null;
}

interface AuthState {
  // 会话
  accessToken: string | null;
  userRole: "teacher" | "student" | null;
  mustChangePassword: boolean;
  // 当前登录学生本人信息（学生端；教师为 null）
  currentStudent: StudentInfo | null;
  // 教师任教班级 ID 列表
  teachingClasses: number[] | null;
  // 教师学科（如 "math" / "english"；学生为 null）
  subject: string | null;
  // 教师班主任班级（可空；学生为 null）
  homeroomClassId: number | null;

  // 动作
  setSession: (session: {
    accessToken: string;
    userRole: "teacher" | "student";
    mustChangePassword: boolean;
    currentStudent: StudentInfo | null;
    teachingClasses?: number[] | null;
    subject?: string | null;
    homeroomClassId?: number | null;
  }) => void;
  updateAccessToken: (accessToken: string, mustChangePassword: boolean) => void;
  reset: () => void;
}

const EMPTY = {
  accessToken: null as string | null,
  userRole: null as "teacher" | "student" | null,
  mustChangePassword: false,
  currentStudent: null as StudentInfo | null,
  teachingClasses: null as number[] | null,
  subject: null as string | null,
  homeroomClassId: null as number | null,
};

export const useAuthStore = create<AuthState>((set) => ({
  ...EMPTY,

  setSession: ({
    accessToken,
    userRole,
    mustChangePassword,
    currentStudent,
    teachingClasses = null,
    subject = null,
    homeroomClassId = null,
  }) =>
    set({
      accessToken,
      userRole,
      mustChangePassword,
      currentStudent,
      teachingClasses,
      subject,
      homeroomClassId,
    }),

  updateAccessToken: (accessToken, mustChangePassword) =>
    set({ accessToken, mustChangePassword }),

  reset: () => set({ ...EMPTY }),
}));
