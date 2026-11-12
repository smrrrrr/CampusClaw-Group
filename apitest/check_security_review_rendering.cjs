// P1-4: Render the actual component with React SSR, its parser and KaTeX.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');

async function main() {
  const esm = {};
  for (const name of ['react-markdown', 'remark-math', 'rehype-katex']) {
    esm[name] = { __esModule: true, default: (await import(pathToFileURL(frontend.resolve(name)).href)).default };
  }
  function load(file) {
    const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
    }).outputText;
    const module = { exports: {} };
    const req = name => {
      if (esm[name]) return esm[name];
      if (name.startsWith('@/lib/')) return load('frontend/' + name.slice(2) + '.ts');
      if (name === './authenticated-image') return { AuthenticatedImage: () => { throw Error('Image loading outside this text-rendering check'); } };
      return frontend(name);
    };
    new Function('require', 'module', 'exports', compiled)(req, module, module.exports);
    return module.exports;
  }
  const Component = load('frontend/components/markdown-answer.tsx').default;
  const React = frontend('react');
  const { renderToStaticMarkup } = frontend('react-dom/server');
  const render = text => renderToStaticMarkup(React.createElement(Component, { text }));
  const formula = '$a < b \\quad x > 0$';
  const raw = formula + '\n\n```python\nif a < b and x > 0: print("&")\n```';
  const html = render(raw);
  assert.match(html, /class="katex"/);
  assert(!html.includes('katex-error'), 'original formula renders without parse error');
  assert.match(html, /if a &lt; b and x &gt; 0: print\(&quot;&amp;&quot;\)/);
  const escaped = formula.replace(/</g, '&lt;').replace(/>/g, '&gt;');
  assert(render(escaped).includes('katex-error'), 'reproduces the old whole-message escape defect');
  const attack = render('<script>alert(1)</script>\n\n<img src=x onerror=alert(2)>\n\n[click](javascript:alert(3))');
  assert(!/<script|<img|onerror=|href="javascript:/i.test(attack), 'raw HTML and dangerous URL cannot execute');
  const code = render('```html\n<script>alert(1)</script>\n```');
  assert.match(code, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.equal(render(raw), html, 'live and reloaded original text render identically');
  console.log('P1-4: 7 rendering assertions passed, including the original escape failure.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
