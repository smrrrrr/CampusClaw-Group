/** 修复 AI 把图片路径中的 %20 写回空格的情况；不改代码示例或有效的图片标题。 */
export function normalizeMarkdownImagePaths(text: string): string {
  return text.replace(/```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`|!\[([^\]\n]*)\]\(([^)\n]+)\)/g,
    (whole: string, alt?: string, raw?: string) => {
      if (alt === undefined || raw === undefined) return whole;
      let destination = raw.trim();
      // 尖括号本身就是 Markdown 对带空格地址的合法写法。
      if (destination.startsWith('<') && destination.endsWith('>')) return whole;
      const titled = destination.match(/^(.*?)\s+("[^"\n]*"|'[^'\n]*')$/);
      const title = titled ? ' ' + titled[2] : '';
      if (titled) destination = titled[1];
      if (!/[ \t]/.test(destination)) return whole;
      return `![${alt}](${destination.replace(/[ \t]/g, c => encodeURIComponent(c))}${title})`;
    });
}
