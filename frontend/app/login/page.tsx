"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError, TokenDTO } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { applyTokenSession } from "@/lib/session";

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuthStore((s) => s.setSession);
  const accessToken = useAuthStore((s) => s.accessToken);

  const [error, setError] = useState("");
  const [forgotHint, setForgotHint] = useState(false);
  const [loading, setLoading] = useState(false);

  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  // 已登录用户访问登录页 → 按角色跳走
  useEffect(() => {
    if (accessToken) {
      const role = useAuthStore.getState().userRole;
      router.replace(role === "teacher" ? "/teacher" : "/student");
    }
  }, [accessToken, router]);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setForgotHint(false);
    setLoading(true);
    try {
      const data: TokenDTO = await api.login(identifier.trim(), password);
      applyTokenSession(data, setSession);
      if (data.must_change_password) {
        router.replace("/change-password");
      } else {
        router.replace(data.role === "teacher" ? "/teacher" : "/student");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "登录失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="centered">
      <div className="card">
        <h1 style={{ color: "var(--brand)" }}>CampusClaw 校园助手</h1>

        {error && <div className="error">{error}</div>}

        <form onSubmit={handlePasswordLogin}>
          <div className="field">
            <label>学号 / 工号</label>
            <input
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="请输入学号或工号"
              required
            />
          </div>
          <div className="field">
            <label>密码</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
            />
          </div>
          <button className="btn" type="submit" disabled={loading}>
            {loading ? "登录中…" : "登 录"}
          </button>
          <div style={{ marginTop: 12, textAlign: "center" }}>
            <button
              type="button"
              className="link-like"
              onClick={() => setForgotHint((v) => !v)}
            >
              忘记密码？
            </button>
            {forgotHint && (
              <div className="hint" style={{ marginTop: 6 }}>
                请联系班主任重置
              </div>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
