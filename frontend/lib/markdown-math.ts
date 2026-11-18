// Match protected Markdown first so delimiters inside code or existing math stay untouched.
const mathOrProtectedText = new RegExp([
  /^ {0,3}(?<fence>`{3,}|~{3,})[^\r\n]*(?:\r?\n[\s\S]*?)?(?:^ {0,3}\k<fence>[`~]*[ \t]*\r?$|(?![\s\S]))/.source,
  /(?<!`)(?<ticks>`+)(?!`)[\s\S]*?(?<!`)\k<ticks>(?!`)/.source,
  /\$\$[^$]+?\$\$|\$[^$\r\n]+?\$/.source,
  /(?<!\\)\\\[(?<display>(?:(?!\\[\[\]])[\s\S])+?)\\\]/.source,
  /(?<!\\)\\\((?<inline>(?:(?!\\[()])[^\r\n])+?)\\\)/.source,
].join("|"), "gm");

export function normalizeBackslashMath(text: string): string {
  return text.replace(
    mathOrProtectedText,
    (match: string, _fence: string, _ticks: string, display?: string, inline?: string) => {
      if (display?.trim()) return `\n\n$$\n${display.trim()}\n$$\n\n`;
      if (inline?.trim()) return `$${inline.trim()}$`;
      return match;
    }
  );
}
