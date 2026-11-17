// 题目内容显示：代码中的下划线原样保留（frontend/lib/markdown-blanks.ts）。
// 用真实 TS 模块验证，不依赖浏览器；不调用接口与模型。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');

function check(name, value) {
  if (!value) throw new Error(name);
  console.log('PASS ' + name);
}

function load(file) {
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', compiled)(require, module, module.exports);
  return module.exports;
}

const { protectFillBlanks } = load('frontend/lib/markdown-blanks.ts');
const escaped = '\\_\\_\\_\\_';

check('代码中的下划线：正文填空空位转义为字面下划线',
  protectFillBlanks('答案是____。') === '答案是' + escaped + '。');
check('代码中的下划线：行内代码中的 ____ 原样显示，不出现多余反斜杠',
  protectFillBlanks('写作 `a____b` 结束') === '写作 `a____b` 结束');
check('代码中的下划线：围栏代码块中的 ____ 原样显示',
  protectFillBlanks('```\nx____y\n```') === '```\nx____y\n```');
check('代码中的下划线：公式与自动链接内的下划线不动',
  protectFillBlanks('$____$ 与 $$____$$ 与 <https://example.com/____>')
    === '$____$ 与 $$____$$ 与 <https://example.com/____>');
check('代码中的下划线：已转义下划线不重复转义',
  protectFillBlanks('已转义 ' + escaped) === '已转义 ' + escaped);
check('代码中的下划线：整行仅下划线按分隔线保留',
  protectFillBlanks('____') === '____');
check('代码中的下划线：不足四个下划线不处理',
  protectFillBlanks('a__b 与 a___b') === 'a__b 与 a___b');
check('代码中的下划线：同一行多个空位逐个转义且其余字符不变',
  protectFillBlanks('前____中______后') === '前' + '\\_'.repeat(4) + '中' + '\\_'.repeat(6) + '后');
check('代码中的下划线：未闭合行内代码仍按正文转义',
  protectFillBlanks('未闭合 ` 后空位____') === '未闭合 ` 后空位' + escaped);
assert.equal(protectFillBlanks(''), '');
