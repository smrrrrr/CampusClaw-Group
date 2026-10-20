"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/store";
import { AuthGate } from "@/components/auth-guard";

function HomeRedirect() {
  const router = useRouter();

  useEffect(() => {
    const { accessToken, userRole, mustChangePassword } = useAuthStore.getState();
    if (!accessToken) {
      router.replace("/login");
    } else if (mustChangePassword) {
      router.replace("/change-password");
    } else {
      router.replace(userRole === "teacher" ? "/teacher" : "/student");
    }
  }, [router]);

  return <div className="centered">加载中…</div>;
}

export default function HomePage() {
  return <AuthGate><HomeRedirect /></AuthGate>;
}
