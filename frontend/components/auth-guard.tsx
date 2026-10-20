"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/store";
import { clearRoleCookies, refreshAccessToken } from "@/lib/api";

/**
 * 客户端路由守卫：
 * - 未登录 → /login
 * - must_change_password=true → /change-password
 */
export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  const accessToken = useAuthStore((s) => s.accessToken);
  const mustChangePassword = useAuthStore((s) => s.mustChangePassword);

  useEffect(() => {
    let cancelled = false;
    if (!accessToken) {
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
      router.replace("/change-password");
      return;
    }
    if (pathname === "/change-password" && !mustChangePassword) {
      router.replace("/");
      return;
    }
    setReady(true);
  }, [accessToken, mustChangePassword, pathname, router]);

  if (!ready || !accessToken || (mustChangePassword && pathname !== "/change-password")) {
    return <div className="centered">加载中…</div>;
  }

  return <>{children}</>;
}
