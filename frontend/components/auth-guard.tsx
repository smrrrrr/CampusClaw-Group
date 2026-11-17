"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/store";
import { clearRoleCookies, refreshAccessToken } from "@/lib/api";
import { isRoleAllowed } from "@/lib/route-access";

/**
 * 客户端路由守卫：
 * - 未登录 → /login
 * - must_change_password=true → /change-password
 * - 本页会话角色不匹配路径 → /403，检查通过前不挂载业务内容
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  const accessToken = useAuthStore((s) => s.accessToken);
  const userRole = useAuthStore((s) => s.userRole);
  const mustChangePassword = useAuthStore((s) => s.mustChangePassword);
  const roleAllowed = isRoleAllowed(pathname, userRole);

  useEffect(() => {
    let cancelled = false;
    if (!accessToken || !userRole) {
      setReady(false);
      refreshAccessToken().then((ok) => {
        if (cancelled || ok) return;
        useAuthStore.getState().reset();
        clearRoleCookies();
        router.replace("/login");
      });
      return () => { cancelled = true; };
    }
    if (mustChangePassword && pathname !== "/change-password") {
      setReady(false);
      router.replace("/change-password");
      return;
    }
    if (pathname === "/change-password" && !mustChangePassword) {
      setReady(false);
      router.replace("/");
      return;
    }
    if (!roleAllowed) {
      setReady(false);
      router.replace("/403");
      return;
    }
    setReady(true);
  }, [accessToken, userRole, mustChangePassword, pathname, roleAllowed, router]);

  if (!ready || !accessToken || !userRole || !roleAllowed || (mustChangePassword && pathname !== "/change-password")) {
    return <div className="centered">加载中…</div>;
  }

  return <>{children}</>;
}
