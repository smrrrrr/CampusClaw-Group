const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');

function load(file, resolve = frontend) {
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', compiled)(resolve, module, module.exports);
  return module.exports;
}

async function main() {
  const page = fs.readFileSync('frontend/app/student/page.tsx', 'utf8');
  assert.match(page, /<MarkdownAnswer text=\{normalizeBackslashMath\(explanations\[m.id\]\)\} allowImages=\{false\}/,
    '错题讲解必须通过数学渲染并禁用图片');
  const packages = new Map(await Promise.all(['react-markdown', 'remark-math', 'rehype-katex'].map(async name =>
    [name, { __esModule: true, ...await import(pathToFileURL(frontend.resolve(name)).href) }])));
  const React = frontend('react');
  const { renderToStaticMarkup } = frontend('react-dom/server');
  const { normalizeBackslashMath } = load('frontend/lib/markdown-math.ts');
  const { default: MarkdownAnswer } = load('frontend/components/markdown-answer.tsx', name => {
    if (packages.has(name)) return packages.get(name);
    if (name.startsWith('@/lib/')) return load(`frontend/lib/${name.slice('@/lib/'.length)}.ts`);
    if (name === './authenticated-image') return { AuthenticatedImage: () => assert.fail('讲解不应请求图片') };
    return frontend(name);
  });
  const render = text => renderToStaticMarkup(React.createElement(MarkdownAnswer, {
    text: normalizeBackslashMath(text), allowImages: false,
  }));

  const explanation = String.raw`1) **解题思路**

- 从点 \(O\) 出发，先画 \(\overrightarrow{OA}=\vec a\)。
- 接着画 $\vec b$。

\[
\overrightarrow{OC}=\overrightarrow{OA}+\overrightarrow{AC}
\]

$$
x^2=1
$$`;
  const rendered = render(explanation);
  assert.match(rendered, /<strong>解题思路<\/strong>/);
  assert.match(rendered, /<ul>/);
  assert.equal((rendered.match(/<math[ >]/g) || []).length, 5);
  assert.equal((rendered.match(/class="katex-display"/g) || []).length, 2);
  console.log('PASS 讲解含向量和解题步骤');

  const code = '`' + String.raw`\(x\)` + '`\n\n```latex\n' + String.raw`\[x\]` + '\n```';
  assert.equal(normalizeBackslashMath(code), code);
  assert.match(render(code), /<code>\\\(x\\\)<\/code>/);
  const invalid = String.raw`未完成 \(x，后面还有 \(y\)。坏公式 \(\notARealCommand{x}\)。`;
  const safe = render(invalid + '\n\n<script>alert(1)</script>\n\n![外图](https://example.com/a.png)');
  assert.match(safe, /未完成/);
  assert.match(safe, /<mtext>\\notARealCommand<\/mtext>/);
  assert.match(safe, /<math[ >]/);
  assert.doesNotMatch(safe, /<script|<img|alert\(1\)/);
  console.log('PASS 讲解含代码、坏公式或外部资源');

  const fallback = 'AI 讲解暂未配置，请联系教师。';
  assert.match(page, new RegExp(fallback));
  assert.match(render(fallback), /<p>AI 讲解暂未配置，请联系教师。<\/p>/);
  console.log('PASS 讲解服务未配置');
}

main().catch(error => { console.error(error.message); process.exitCode = 1; });
