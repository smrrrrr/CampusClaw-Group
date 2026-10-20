"use client";
import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/api";

export function AuthenticatedImage({ url, alt }: { url: string; alt: string }) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setSrc(null); setError("");
    authenticatedFetch(url).then(r => r.blob()).then(blob => {
      if (cancelled) return;
      objectUrl = URL.createObjectURL(blob);
      setSrc(objectUrl);
    }).catch(e => { if (!cancelled) setError(e.message); });
    return () => { cancelled = true; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [url]);
  if (error) return <span className="error" data-print-resource="error">配图加载失败：{error}</span>;
  return src ? <img src={src} alt={alt} onError={() => setError("图片无法解码")} style={{ maxWidth: "100%", maxHeight: 520, objectFit: "contain" }} /> : <span className="hint" data-print-resource="loading">配图加载中…</span>;
}
