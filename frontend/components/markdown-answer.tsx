"use client";

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useMemo } from "react";
import { AuthenticatedImage } from "./authenticated-image";
import { normalizeMarkdownImagePaths } from "@/lib/markdown-images";
import { protectFillBlanks } from "@/lib/markdown-blanks";

/**
 * 常用 LaTeX 命令表。部分讲义源文件命令未写反斜杠（如 `$vec{a}$` 而非 `$\vec{a}$`），
 * 导致 KaTeX 无法解析而源码直显。这里在渲染期对公式块内的裸命令补 `\`。
 */
const KNOWN_COMMANDS = [
  // 长命令（覆盖向量、矩阵、求和积分等）
  "overrightarrow", "underrightarrow", "overleftrightarrow",
  "longrightarrow", "longleftarrow", "overset", "underset", "stackrel",
  "overline", "underline", "mathbb", "mathbf", "boldsymbol",
  "dfrac", "tfrac", "lVert", "rVert",
  // 常用
  "vec", "frac", "sqrt", "cdot", "times", "div", "pm", "mp",
  "sum", "prod", "int", "iint", "oint", "lim", "max", "min",
  "left", "right", "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "middle",
  "vert", "lvert", "rvert", "Vert",
  "pi", "alpha", "beta", "gamma", "delta", "epsilon", "varepsilon", "varphi", "theta",
  "lambda", "mu", "nu", "xi", "phi", "omega", "sigma", "rho", "tau", "eta", "zeta", "chi", "psi",
  "Gamma", "Delta", "Theta", "Lambda", "Sigma", "Omega", "Pi",
  "cos", "sin", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
  "log", "ln", "exp",
  "leq", "geq", "leqq", "geqq", "leqslant", "geqslant", "neq", "ne",
  "approx", "equiv", "sim", "cong", "propto", "perp", "parallel", "nmid", "mid",
  "in", "notin", "subset", "subseteq", "supset", "supseteq", "subsetneq",
  "cup", "cap", "setminus", "emptyset", "varnothing",
  "to", "rightarrow", "leftarrow", "Rightarrow", "Leftarrow", "leftrightarrow", "Leftrightarrow", "mapsto",
  "angle", "ell", "ldots", "cdots", "vdots", "ddots", "dots",
  "text", "mathrm", "textbf", "textit",
  "quad", "qquad", "begin", "end",
] as const;

const COMMAND_SET = new Set<string>(KNOWN_COMMANDS);

/**
 * 在 `$$...$$` / `$...$` 内为缺失反斜杠的裸 LaTeX 命令补 `\`。
 *
 * - 定界符：先匹配块级 `$$...$$`，再匹配行内 `$...$`，确保与 remark-math 的切分一致，
 *   避免把相邻 `$`/`$$` 混配造成公式边界错误。
 * - 命令判定：匹配「最长字母串」，仅当该字母串**整体**前面不是 `\` 且确实位于命令表内时补 `\`。
 *   这样已正确转义的 `\overrightarrow` 整词会被跳过，不会被误拆成 `\over\rightarrow`。
 * 仅处理公式块，不影响公式外的普通中文/英文正文。
 */
function normalizeLatex(text: string): string {
  return text.replace(
    /\$\$([^$]+?)\$\$|\$([^$]+?)\$/g,
    (whole, block, inline) => {
      const body = block !== undefined ? block : inline;
      const fixed = body.replace(/(^|[^a-zA-Z\\])([a-zA-Z]+)/g, (m: string, pre: string, cmd: string) =>
        pre !== "\\" && COMMAND_SET.has(cmd) ? pre + "\\" + cmd : m
      );
      if (fixed === body) return whole;
      return block !== undefined ? "$$" + fixed + "$$" : "$" + fixed + "$";
    }
  );
}

/**
 * 渲染 AI 回答 / 资料预览：Markdown（加粗/列表） + KaTeX（LaTeX 数学公式）。
 * 用于学生端 AI 解题助手与讲义预览，让公式以真正的数学符号展示而非源码。
 */
export default function MarkdownAnswer({ text, imageUrl }: { text: string; imageUrl?: (src: string) => string }) {
  const components = useMemo(() => imageUrl ? { img: ({ src, alt }: { src?: string; alt?: string }) => {
    if (!src) return null;
    try { return <AuthenticatedImage url={imageUrl(src)} alt={alt ?? "讲义配图"} />; }
    catch { return <span className="error" data-print-resource="error">配图地址无效</span>; }
  } } : undefined, [imageUrl]);
  return (
    <div className="markdown-body" style={{ lineHeight: 1.8, fontSize: 14 }}>
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]} components={components}>
        {normalizeLatex(protectFillBlanks(imageUrl ? normalizeMarkdownImagePaths(text) : text))}
      </ReactMarkdown>
    </div>
  );
}
