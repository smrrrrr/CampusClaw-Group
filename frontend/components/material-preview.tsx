"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, authenticatedFetch } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import type { MaterialItemDTO } from "@/lib/api";
import MarkdownAnswer from "@/components/markdown-answer";
import { PrintHandoutButton } from "@/components/print-handout-button";

/**
 * 在线预览组件：
 * - 图片（JPG/PNG）→ img 渲染 blob URL
 * - PDF → iframe 渲染 blob URL
 * - Markdown / TXT → 按文本拉取，用 MarkdownAnswer（react-markdown + KaTeX）渲染，
 *   使含 LaTeX 公式的讲义也能显示为数学符号
 * - PPTX/DOCX → 提示暂不支持在线预览，请下载查看
 * 鉴权：通过 Authorization 头获取文件流。
 */
export function MaterialPreview({
  item,
  onClose,
}: {
  item: MaterialItemDTO;
  onClose: () => void;
}) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [loading, setLoading] = useState(true);
  const printContent = useRef<HTMLDivElement>(null);

  const isImage = item.file_type.startsWith("image/");
  const isText = item.file_type === "text/markdown" || item.file_type === "text/plain";
  const isPdf = item.file_type === "application/pdf";
  const previewable = isImage || isText || isPdf;
  const imageUrl = useCallback((src: string) => api.materialAssetUrl(item.id, src), [item.id]);
  const downloadFile = async () => {
    setDownloadError("");
    try {
      const bundle = item.file_type === "text/markdown";
      const response = await authenticatedFetch(bundle ? `/api/materials/${item.id}/bundle` : api.materialDownloadUrl(item.id));
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url; link.download = bundle ? item.filename.replace(/\.md$/i, "") + ".zip" : item.filename; link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setDownloadError((e as Error).message); }
  };

  useEffect(() => {
    const token = useAuthStore.getState().accessToken;
    const url = api.materialPreviewUrl(item.id);
    let objectUrl: string | null = null;
    setLoading(true);
    (async () => {
      try {
        const res = await fetch(url, {
          headers: { Authorization: `Bearer ${token}` },
          credentials: "include",
        });
        if (!res.ok) throw new Error(res.status === 403 ? "无权预览该材料" : "预览加载失败");
        if (isText) {
          setTextContent(await res.text());
        } else {
          objectUrl = URL.createObjectURL(await res.blob());
          setBlobUrl(objectUrl);
        }
        setError("");
      } catch (err) {
        setError((err as Error).message || "预览加载失败");
      } finally {
        setLoading(false);
      }
    })();

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      if (blobUrl) URL.revokeObjectURL(blobUrl);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [item.id, isText]);

  return (
    <div
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: "rgba(0,0,0,0.6)",
        display: "flex",
        flexDirection: "column",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: "#fff",
          margin: "40px auto",
          borderRadius: 12,
          width: "90%",
          maxWidth: 1000,
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="material-preview-toolbar"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            borderBottom: "1px solid #e5e7eb",
          }}
        >
          <strong style={{ fontSize: 14 }}>{item.filename}</strong>
          {isText && <PrintHandoutButton key={item.id} contentRef={printContent} title={item.filename} disabled={loading || textContent === null || !!error} />}
          <button className="btn-pill ghost sm" onClick={downloadFile}>{item.file_type === "text/markdown" ? "下载图文包" : "下载原文件"}</button>
          <button className="btn" style={{ width: "auto", padding: "4px 12px", fontSize: 13 }} onClick={onClose}>
            关闭
          </button>
        </div>
        {downloadError && <p className="error" role="alert" style={{ padding: "8px 16px" }}>{downloadError}</p>}
        <div style={{ flex: 1, overflow: "auto", display: "flex", justifyContent: "center", alignItems: "flex-start" }}>
          {loading && <p className="hint" style={{ padding: 24 }}>加载中…</p>}
          {error && <p className="error" style={{ padding: 24 }}>{error}</p>}
          {isText && textContent !== null && !error && (
            <div ref={printContent} style={{ width: "100%", padding: "24px 32px", textAlign: "left" }}>
              <MarkdownAnswer text={textContent} imageUrl={imageUrl} />
            </div>
          )}
          {blobUrl && !error && isImage && (
            <img src={blobUrl} alt={item.filename} style={{ maxWidth: "100%", maxHeight: "80vh" }} />
          )}
          {blobUrl && !error && isPdf && (
            <iframe src={blobUrl} style={{ width: "100%", height: "75vh", border: "none" }} title={item.filename} />
          )}
          {!previewable && !loading && !error && (
            <p className="hint" style={{ padding: 24 }}>该格式暂不支持在线预览，请通过「下载」查看原文。</p>
          )}
        </div>
      </div>
    </div>
  );
}
