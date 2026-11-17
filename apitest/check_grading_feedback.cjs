// E3/E4：受理回执可核对编号、作业卡片内呈现、提交人数同步。
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');
const code = ts.transpileModule(fs.readFileSync('frontend/lib/grading-feedback.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText;
const loaded = { exports: {} };
new Function('exports', code)(loaded.exports);
const { formatGradeReceipt, syncSubmissionCount } = loaded.exports;
let passed = 0;
function check(name, fn) { fn(); passed++; console.log('PASS ' + name); }
const receipt = (created, existing, ids, skipped = 0) => ({ created_count: created, existing_count: existing, task_ids: ids, skipped_count: skipped });
check('E3 正常：新建回执包含任务编号', () => {
  const text = formatGradeReceipt(receipt(1, 0, [7]));
  assert(text.includes('已新建 1 个后台任务：#7'));
  assert(!text.includes('已复用任务'));
});
check('E3 边界：重复点击明确没有新建并复用原编号', () => {
  const text = formatGradeReceipt(receipt(0, 1, [7]));
  assert(text.includes('没有新建任务'));
  assert(text.includes('已复用任务 #7（已有 1 个）'));
});
check('E3 边界：混合批次保留全部编号与两种数量', () => {
  const text = formatGradeReceipt(receipt(1, 1, [7, 8]));
  assert(text.includes('已新建 1 个、复用 1 个'));
  assert(text.includes('#7、#8'));
});
check('E3 边界：没有待批改时不编造任务', () => {
  const text = formatGradeReceipt(receipt(0, 0, [], 2));
  assert(text.includes('没有待初批的提交'));
  assert(text.includes('已跳过 2 份'));
  assert(!text.includes('#'));
});
check('E4 正常：提交数量更新且不污染其他作业或原数组', () => {
  const rows = [{ id: 1, submitted_count: 0, title: 'A' }, { id: 2, submitted_count: 3, title: 'B' }];
  const next = syncSubmissionCount(rows, 1, 1);
  assert.equal(next[0].submitted_count, 1);
  assert.equal(next[0].title, 'A');
  assert.equal(next[1], rows[1]);
  assert.equal(rows[0].submitted_count, 0);
});
check('E4 边界：空列表和未知作业不会新增或修改其他记录', () => {
  assert.deepEqual(syncSubmissionCount([], 1, 1), []);
  assert.deepEqual(syncSubmissionCount([{ id: 2, submitted_count: 3 }], 1, 1), [{ id: 2, submitted_count: 3 }]);
});

const source = ts.createSourceFile('teacher.tsx', fs.readFileSync('frontend/app/teacher/page.tsx', 'utf8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let feedback;
function visit(node) {
  if (ts.isJsxElement(node) && node.openingElement.attributes.properties.some(attr => ts.isJsxAttribute(attr)
      && attr.name.getText(source) === 'data-testid' && attr.initializer?.getText(source).includes('homework-grade-feedback-'))) feedback = node;
  ts.forEachChild(node, visit);
}
visit(source);
check('E3 正常：回执位于具有作业编号的卡片内，不在页面顶部', () => {
  assert(feedback, '缺少可定位的卡片反馈');
  let card = feedback.parent;
  while (card && !(ts.isJsxElement(card) && card.openingElement.attributes.properties.some(attr =>
    ts.isJsxAttribute(attr) && attr.name.getText(source) === 'key' && attr.initializer?.getText(source) === '{hw.id}'))) card = card.parent;
  assert(card, '反馈必须位于当前作业卡片中');
  assert(feedback.getText(source).includes('hwNotices[hw.id].text'));
});
check('E3 失败：错误回执在同一反馈块使用alert', () => {
  const role = feedback.openingElement.attributes.properties.find(attr => ts.isJsxAttribute(attr) && attr.name.getText(source) === 'role');
  assert(role?.initializer.getText(source).includes('hwNotices[hw.id].error ? "alert" : "status"'));
});
console.log(JSON.stringify({ passed, scenarios: ['E3', 'E4'] }));
