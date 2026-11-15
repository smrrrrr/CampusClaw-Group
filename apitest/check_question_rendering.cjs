// 题目显示：多空位、公式答案、解答题作答横线（真实组件 + React SSR + KaTeX）。
// 对应 smart-question-generation「多空位填空题显示」「填空与解答题答案含公式」
// 「解答题作答横线不变」「学生端打开已发布试卷」；不依赖浏览器与模型。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const { pathToFileURL } = require('node:url');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');

function check(name, fn) {
  fn();
  console.log('PASS ' + name);
}

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
      if (name === './authenticated-image') return { AuthenticatedImage: () => null };
      return frontend(name);
    };
    new Function('require', 'module', 'exports', compiled)(req, module, module.exports);
    return module.exports;
  }
  const Component = load('frontend/components/markdown-answer.tsx').default;
  const React = frontend('react');
  const { renderToStaticMarkup } = frontend('react-dom/server');
  const render = text => renderToStaticMarkup(React.createElement(Component, { text }));

  const stem = '则 $\\overrightarrow{EF}$ 的坐标为____，____，____。';
  check('多空位填空题显示：三个空位保留且无加粗斜体', () => {
    const html = render(stem);
    assert.equal((html.match(/_/g) || []).length, 12, '三个空位共 12 个下划线');
    assert(!/<strong|<em|font-style:italic|font-weight:bold/i.test(html), '下划线不能被解析成强调');
    assert.match(html, /class="katex"/);
    assert(!html.includes('katex-error'));
  });

  check('填空与解答题答案含公式：答案以 KaTeX 渲染且无 katex-error', () => {
    for (const answer of ['$\\frac{\\sqrt{15}}{5}$', '$\\frac{\\sqrt{3}}{3}$']) {
      const html = render(answer);
      assert.match(html, /class="katex"/, answer);
      assert(!html.includes('katex-error'), answer);
      assert(!html.includes('$'), '不能显示美元源码：' + answer);
    }
  });

  check('解答题作答横线不变：整行下划线渲染为分隔线而非文字', () => {
    const html = render('____');
    assert.match(html, /<hr/);
    assert(!html.includes('____'));
  });

  check('学生端打开已发布试卷：多空位题干渲染后空位与发布时一致', () => {
    const published = '已知 $\\vec{a}=(1,2)$，则坐标____，____。';
    const html = render(published);
    assert.equal((html.match(/_/g) || []).length, 8);
    assert.match(html, /class="katex"/);
    assert(!html.includes('katex-error'));
  });

  console.log(JSON.stringify({ passed: 4, model_calls: 0, database_writes: 0 }));
}

main().catch(error => { console.error(error); process.exitCode = 1; });
