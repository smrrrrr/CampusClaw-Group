"use client";

import { useEffect, useRef, useState, type RefObject } from "react";

const PRINT_CSS = `
@page { size: A4; margin: 16mm; }
html, body { margin: 0 !important; padding: 0 !important; background: white !important; color: #111 !important; }
body { font-family: Arial, "Microsoft YaHei", "PingFang SC", sans-serif; }
.handout-print { width: auto; max-width: none; overflow-wrap: anywhere; }
.handout-print .markdown-body { font-size: 11pt !important; line-height: 1.7 !important; }
.handout-print h1 { font-size: 20pt; }
.handout-print h2 { font-size: 16pt; }
.handout-print h3 { font-size: 13pt; }
.handout-print h1, .handout-print h2, .handout-print h3, .handout-print h4 { break-after: avoid; page-break-after: avoid; }
.handout-print p, .handout-print li { orphans: 3; widows: 3; }
.handout-print img { display: block; max-width: 100% !important; max-height: 230mm !important; width: auto; height: auto; object-fit: contain; break-inside: avoid; page-break-inside: avoid; margin: 10pt auto; }
.handout-print table { width: 100%; border-collapse: collapse; }
.handout-print th, .handout-print td { border: 1px solid #bbb; padding: 5pt; }
.handout-print thead { display: table-header-group; }
.handout-print tr, .handout-print .katex-display { break-inside: avoid; page-break-inside: avoid; }
.handout-print .katex-display { overflow: visible !important; }
.handout-print pre { white-space: pre-wrap; }
.handout-print a { color: inherit; text-decoration: none; }
`;

function withTimeout<T>(promise: Promise<T>, message: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(message)), 20000);
    promise.then(value => { clearTimeout(timer); resolve(value); }, error => { clearTimeout(timer); reject(error); });
  });
}

// 等待鉴权图片完成请求，避免只把“配图加载中”复制进打印稿。
async function waitForContent(root: HTMLElement) {
  const deadline = Date.now() + 20000;
  while (root.querySelector('[data-print-resource="loading"]')) {
    if (!root.isConnected) throw new Error("讲义已关闭，请重新打开后打印。");
    if (Date.now() > deadline) throw new Error("配图仍在加载，请稍后重试。");
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  if (root.querySelector('[data-print-resource="error"]')) throw new Error("有配图加载失败，请重新打开讲义后再打印。");
}

export function PrintHandoutButton({ contentRef, title, disabled = false }: {
  contentRef: RefObject<HTMLDivElement>;
  title: string;
  disabled?: boolean;
}) {
  const [preparing, setPreparing] = useState(false);
  const [error, setError] = useState("");
  const frameRef = useRef<HTMLIFrameElement | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; frameRef.current?.remove(); };
  }, []);

  const print = async () => {
    const root = contentRef.current;
    if (!root || preparing) return;
    setPreparing(true); setError("");
    try {
      await waitForContent(root);
      if (!mounted.current || !root.isConnected) return;
      frameRef.current?.remove();
      const frame = document.createElement("iframe");
      frame.title = "讲义打印稿";
      frame.setAttribute("aria-hidden", "true");
      frame.style.cssText = "position:fixed;left:-10000px;top:0;width:794px;height:1123px;border:0;";
      document.body.appendChild(frame);
      frameRef.current = frame;
      const doc = frame.contentDocument;
      const win = frame.contentWindow;
      if (!doc || !win) throw new Error("浏览器无法打开打印稿。");
      // 仅复制当前讲义的渲染结果；不复制导航、发布表单或隐藏的教师原稿。
      doc.open(); doc.write('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head><body></body></html>'); doc.close();
      doc.title = title.replace(/\.(md|txt)$/i, "");
      const styles = Array.from(document.querySelectorAll('link[rel="stylesheet"], style')).map(node => {
        const copy = node.cloneNode(true) as HTMLElement;
        if (copy instanceof HTMLLinkElement) {
          return new Promise<void>((resolve, reject) => {
            copy.onload = () => resolve();
            copy.onerror = () => reject(new Error("打印样式加载失败，请重试。"));
            doc.head.appendChild(copy);
          });
        }
        doc.head.appendChild(copy);
        return Promise.resolve();
      });
      const style = doc.createElement("style"); style.textContent = PRINT_CSS; doc.head.appendChild(style);
      const article = doc.createElement("article"); article.className = "handout-print";
      for (const child of Array.from(root.childNodes)) article.appendChild(child.cloneNode(true));
      doc.body.appendChild(article);
      await withTimeout(Promise.all(styles), "打印样式加载超时，请重试。");
      await withTimeout(Promise.all(Array.from(doc.images).map(img => img.decode())), "打印配图加载超时，请重试。");
      await withTimeout(doc.fonts.ready, "公式字体加载超时，请重试。");
      await new Promise(resolve => win.requestAnimationFrame(() => win.requestAnimationFrame(resolve)));
      if (!mounted.current || !root.isConnected) return;
      win.focus(); win.print();
      // 保留打印框架到下一次打印或组件关闭，避免浏览器异步打印时图片被提前移除。
    } catch (e) {
      frameRef.current?.remove(); frameRef.current = null;
      if (mounted.current) setError((e as Error).message || "打印准备失败，请重试。");
    } finally {
      if (mounted.current) setPreparing(false);
    }
  };

  return <div className="handout-print-control">
    <button className="btn-pill ghost sm" disabled={disabled || preparing} onClick={print}>{preparing ? "准备打印…" : "打印／另存为 PDF"}</button>
    {error && <span className="error" role="alert">{error}</span>}
  </div>;
}
