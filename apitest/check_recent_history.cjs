// Exercises the actual browser-history store and React history component without API/AI calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');
function load(file) {
  const compiled = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', compiled)(frontend, module, module.exports);
  return module.exports;
}
const { createRecentHistory, historyKey } = load('frontend/lib/recent-history.ts');
const data = new Map();
const storage = { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: key => data.delete(key) };
const history = createRecentHistory(() => storage);
const key = historyKey(1, 101, 'materials', '数学');
assert.equal(historyKey(null, 101, 'materials', '数学'), null);
assert.equal(historyKey(1, null, 'materials', '数学'), null);
assert.deepEqual(history.add(null, '不应保存'), []);
assert.deepEqual(history.add(key, '   '), []);
assert.deepEqual(history.add(key, '  空间向量  '), ['空间向量']);
history.add(key, '夹角公式');
assert.deepEqual(history.add(key, '空间向量'), ['空间向量', '夹角公式']);
assert.deepEqual(createRecentHistory(() => storage).read(key), ['空间向量', '夹角公式']);
for (const other of [historyKey(2, 101, 'materials', '数学'), historyKey(1, 102, 'materials', '数学'),
  historyKey(1, 101, 'materials', '物理'), historyKey(1, 101, 'assistant', '数学')]) {
  assert.deepEqual(history.read(other), []);
  history.add(other, '另一范围');
}
assert.deepEqual(history.read(key), ['空间向量', '夹角公式']);
for (let i = 0; i < 15; i++) history.add(key, `关键词${i}`);
assert.equal(history.read(key).length, 10);
assert.equal(history.read(key)[0], '关键词14');
assert.equal(history.read(key)[9], '关键词5');
history.clear(key);
assert.deepEqual(createRecentHistory(() => storage).read(key), []);
assert.deepEqual(history.read(historyKey(1, 101, 'assistant', '数学')), ['另一范围']);
for (const raw of ['invalid JSON', '{}', 'null', '42']) {
  data.set(key, raw); assert.deepEqual(history.read(key), []);
}
data.set(key, JSON.stringify([null, 7, {}, '', ' 向量 ', '向量', 'x'.repeat(4001), '<script>test</script>']));
assert.deepEqual(history.read(key), ['向量', '<script>test</script>']);
const denied = createRecentHistory(() => { throw Error('storage denied'); });
assert.deepEqual(denied.add(key, '仍可使用'), ['仍可使用']);
assert.deepEqual(denied.read(key), ['仍可使用']);
denied.clear(key); assert.deepEqual(denied.read(key), []);
const quota = createRecentHistory(() => ({ ...storage, setItem() { throw Error('quota'); } }));
quota.add(key, '写入失败');
assert.equal(quota.read(key)[0], '写入失败');
quota.clear(key); assert.deepEqual(quota.read(key), []);
const React = frontend('react');
const { renderToStaticMarkup } = frontend('react-dom/server');
const { RecentHistory } = load('frontend/components/recent-history.tsx');
const html = renderToStaticMarkup(React.createElement(RecentHistory, {
  label: '提问历史', entries: ['<script>alert(1)</script>', '如何求夹角'], disabled: true, fillOnly: true,
  onSelect() { throw Error('must not send on render'); }, onClear() {},
}));
assert(!html.includes('<script>'));
assert(html.includes('&lt;script&gt;'));
assert(html.includes('disabled=""'));
assert(html.includes('type="button"'));
assert(html.includes('点击回填，确认后发送'));
assert(html.includes('清空不会删除历史会话'));
console.log('Recent history checks passed: persistence, scope isolation, deduplication/limit, clearing, invalid/blocked storage, safe rendering.');
