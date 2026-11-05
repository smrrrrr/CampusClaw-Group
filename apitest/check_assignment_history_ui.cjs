const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const ts = createRequire(path.resolve('frontend/package.json'))('typescript');
function load(file) {
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;
  const exports = {}; new Function('exports', output)(exports); return exports;
}
const { canSubmitAssignment, isAssignmentHistory } = load('frontend/lib/assignment-history.ts');
const { formatGradingAttempts } = load('frontend/lib/grading-feedback.ts');
const now = Date.parse('2026-11-04T10:00:00Z');
const hw = { homework_status: 'published', submission_id: null, due_at: '2026-11-04T11:00:00Z' };
let passed = 0;
function check(name, fn) { fn(); passed++; console.log('PASS ' + name); }
check('H4 正常：未交未截止属于待完成', () => { assert.equal(isAssignmentHistory(hw, now), false); assert.equal(canSubmitAssignment(hw, now), true); });
check('H1 正常：已交待批改即进入历史', () => assert.equal(isAssignmentHistory({ ...hw, submission_id: 7 }, now), true));
check('H2 正常：关闭有提交属于只读历史', () => { const closed = { ...hw, submission_id: 7, homework_status: 'closed' }; assert.equal(isAssignmentHistory(closed, now), true); assert.equal(canSubmitAssignment(closed, now), false); });
check('H4 边界：刚好截止仍按原合同允许，超过即历史只读', () => { assert.equal(canSubmitAssignment(hw, Date.parse(hw.due_at)), true); assert.equal(canSubmitAssignment(hw, Date.parse(hw.due_at)+1), false); assert.equal(isAssignmentHistory(hw, Date.parse(hw.due_at)+1), true); });
check('H4 边界：无截止未交仍在待完成', () => assert.equal(isAssignmentHistory({ ...hw, due_at: null }, now), false));
check('Q4 正常：消息43只显示本轮批改尝试1', () => { const text = formatGradingAttempts({ attempts: 43, execution_count: 1, max_attempts: 3 }); assert(text.includes('批改尝试 1 次')); assert(text.includes('上限 3 次')); assert(!text.includes('43')); });
console.log(JSON.stringify({ passed, scenarios: ['Q4','H1','H2','H4'] }));
