/**
 * 填空空位（连续 4 个及以上下划线，与后端 BLANK_RUN 口径一致）在 Markdown 中会被当作强调分隔符，
 * 两侧都是中文标点时会配成 `<strong>`，空位消失。这里把空位里的每个 `_` 转义为 `\_`，按字面显示。
 *
 * 原样跳过：围栏代码、行内代码、`$$...$$` / `$...$` 公式、尖括号自动链接，
 * 以及整行只有下划线的行（学生卷解答题作答横线，按分隔线渲染）。前面已有 `\` 的下划线也不处理。
 */
export function protectFillBlanks(text: string): string {
  return text.replace(
    /```[\s\S]*?```|~~~[\s\S]*?~~~|`[^`\n]*`|\$\$[^$]+?\$\$|\$[^$]+?\$|<[a-zA-Z][a-zA-Z0-9+.-]{1,31}:[^<>\s]*>|^[ \t]*_+[ \t]*$|(?<![\\_])(_{4,})/gm,
    (whole: string, blank?: string) => blank === undefined ? whole : blank.replace(/_/g, "\\_")
  );
}
