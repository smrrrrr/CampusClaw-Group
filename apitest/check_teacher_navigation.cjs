// Run the actual shared navigation hook with isolated Next/session adapters.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');
let passed = 0;
function check(name, fn) { fn(); passed++; console.log('PASS ' + name); }
function navigation(route, overrides = {}) {
  const url = new URL(route, 'http://check.invalid');
  const state = { teachingClasses: [101, 102], homeroomClassId: 101, subject: 'math', ...overrides };
  const pushed = [];
  const code = ts.transpileModule(fs.readFileSync('frontend/components/teacher-navigation.tsx', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX },
  }).outputText;
  const jsx = (type, props) => ({ type, props });
  const adapters = {
    'next/navigation': { useRouter: () => ({ push: to => pushed.push(to) }), usePathname: () => url.pathname, useSearchParams: () => url.searchParams },
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'fragment' },
    './class-selector': { ClassSelector: 'ClassSelector' },
    '@/lib/store': { useAuthStore: selector => selector(state) },
  };
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)(name => {
    assert(name in adapters, 'Unexpected runtime dependency: ' + name);
    return adapters[name];
  }, module, module.exports);
  return { ...module.exports.useTeacherNavigation(), pushed };
}
const expected = [
  ['research-materials', '教研组资料', '/teacher/library'],
  ['lesson-prep', '智能备课', '/teacher/lesson-prep'],
  ['lesson-quiz', '智能命题', '/teacher/quiz'],
];
for (const route of ['/teacher', '/teacher/library', '/teacher/lesson-prep', '/teacher/quiz', '/teacher/upload', '/materials']) {
  for (const homeroomClassId of [101, null]) {
    check(`R1 正常：${route} / 带班${homeroomClassId}教研菜单恰好三项`, () => {
      const nav = navigation(route, { homeroomClassId });
      assert.deepEqual(nav.navItems.filter(item => item.section === '教研中心').map(({ key, label, to }) => [key, label, to]), expected);
      const all = JSON.stringify(nav.navItems);
      for (const removed of ['research-qa', 'case-analysis', '教研问答', '课例分析']) assert(!all.includes(removed));
    });
  }
}
check('R1 边界：没有任教班级仍只有三项教研入口', () => {
  const nav = navigation('/teacher?workspace=teaching', { teachingClasses: [], homeroomClassId: null });
  assert.equal(nav.classId, null);
  assert.deepEqual(nav.navItems.filter(item => item.section === '教研中心').map(({ key, label, to }) => [key, label, to]), expected);
});
for (const old of ['research-qa', 'case-analysis']) {
  for (const workspace of ['teaching', 'homeroom']) {
    for (const classId of [101, 102]) {
      check(`R2 失败路径：旧${old} / ${workspace} / ${classId}归一到既有备课跳转`, () => {
        const nav = navigation(`/teacher?view=${old}&workspace=${workspace}&class_id=${classId}`);
        assert.equal(nav.requestedView, 'lesson-prep');
        assert.equal(nav.classId, workspace === 'homeroom' ? 101 : classId);
      });
    }
  }
}
for (const view of ['tools', 'students', 'agent', 'subject-analysis', 'lesson-prep', 'lesson-quiz', 'unknown', '', null]) {
  check(`R3 边界：其他view保持原值 ${JSON.stringify(view)}`, () => {
    const query = new URLSearchParams({ workspace: 'teaching', class_id: '102' });
    if (view !== null) query.set('view', view);
    const nav = navigation('/teacher?' + query);
    assert.equal(nav.requestedView, view);
    assert.equal(nav.classId, 102);
  });
}
check('R3 正常：资料、备课、命题点击仍到原路径，移除项不再可导航', () => {
  const nav = navigation('/teacher?workspace=teaching&class_id=102');
  for (const [key, , to] of expected) { nav.onNavigate(key); assert.equal(nav.pushed.at(-1), to); }
  const before = nav.pushed.length;
  nav.onNavigate('research-qa'); nav.onNavigate('case-analysis');
  assert.equal(nav.pushed.length, before);
});
for (const [route, expectedPath, expectedView] of [
  ['/teacher?workspace=teaching&view=tools&class_id=101', '/teacher', 'tools'],
  ['/teacher?workspace=teaching&view=agent&class_id=101', '/teacher', 'agent'],
  ['/materials?workspace=teaching&class_id=101', '/materials', null],
  ['/teacher?workspace=homeroom&view=home&class_id=101', '/teacher', 'students'],
]) {
  check('R3 正常：切班保留现有页面行为 ' + route, () => {
    const nav = navigation(route); nav.selectTeachingClass(102);
    const target = new URL(nav.pushed.at(-1), 'http://check.invalid');
    assert.equal(target.pathname, expectedPath); assert.equal(target.searchParams.get('view'), expectedView);
    assert.equal(target.searchParams.get('class_id'), '102'); assert.equal(target.searchParams.get('workspace'), 'teaching');
  });
}
console.log(JSON.stringify({ passed, scenarios: ['R1', 'R2', 'R3'], model_calls: 0, database_writes: 0 }));
