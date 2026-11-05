// Actual middleware/AuthGate behavior with isolated sessions; no browser/API/AI calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const frontend = createRequire(path.resolve('frontend/package.json'));
const ts = frontend('typescript');
let passed = 0;
function check(name, fn) { fn(); passed += 1; console.log(`PASS ${name}`); }
function load(file, overrides = {}) {
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 },
  }).outputText;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', code)(name => name in overrides ? overrides[name] : frontend(name), module, module.exports);
  return module.exports;
}
const { middleware } = load('frontend/middleware.ts', {
  'next/server': { NextResponse: { next: () => ({ action: 'next' }), redirect: url => ({ action: 'redirect', url: String(url) }) } },
});
function bootstrap(route, cookies) {
  return middleware({ nextUrl: new URL(route, 'http://localhost:3009'), url: `http://localhost:3009${route}`,
    cookies: { get: name => cookies[name] === undefined ? undefined : { value: cookies[name] } } });
}
check('双标签提示变化后的单科切班：教师页面不被学生提示拒绝', () => {
  assert.equal(bootstrap('/teacher?workspace=teaching&view=subject-analysis&class_id=102', { cc_role: 'student', cc_has_token: '1' }).action, 'next');
});
for (const route of ['/teacher', '/teacher/quiz', '/student', '/student?view=assignments', '/materials', '/']) {
  check(`辅助提示缺失但会话有效：允许启动并恢复 ${route}`, () => assert.equal(bootstrap(route, {}).action, 'next'));
}
check('伪造角色提示不赋予页面权限：提示仅允许启动校验', () => assert.equal(bootstrap('/student', { cc_role: 'teacher', cc_has_token: '0' }).action, 'next'));

const { isRoleAllowed } = load('frontend/lib/route-access.ts');
for (const [route, role, allowed] of [
  ['/teacher', 'teacher', true], ['/teacher/quiz', 'teacher', true], ['/teacher', 'student', false],
  ['/student', 'student', true], ['/student/child', 'teacher', false], ['/materials', 'teacher', true],
  ['/materials', 'student', true], ['/teacherly', 'student', true], ['/students', 'teacher', true],
  ['/teacher', null, false], ['/teacher', 'admin', false],
]) check(`角色目录按完整路径边界判断：${route} / ${role}`, () => assert.equal(isRoleAllowed(route, role), allowed));

function session(role, overrides = {}) { return { accessToken: 'check-only-in-memory-token', userRole: role, mustChangePassword: false, ...overrides }; }
function harness(state, route, { ready: initialReady = true, refresh = null } = {}) {
  let ready = initialReady;
  let effects = [];
  const redirects = [];
  const calls = { refresh: 0, reset: 0, clear: 0 };
  const store = selector => selector(state);
  store.getState = () => ({ reset: () => { calls.reset += 1; Object.assign(state, { accessToken: null, userRole: null }); } });
  const router = { replace: url => redirects.push(url) };
  const jsx = (type, props) => ({ type, props });
  const { AuthGate } = load('frontend/components/auth-guard.tsx', {
    react: { useState: () => [ready, next => { ready = next; }], useEffect: callback => effects.push(callback) },
    'react/jsx-runtime': { jsx, jsxs: jsx, Fragment: 'fragment' },
    'next/navigation': { usePathname: () => route, useRouter: () => router },
    '@/lib/store': { useAuthStore: store },
    '@/lib/route-access': { isRoleAllowed },
    '@/lib/api': {
      clearRoleCookies: () => { calls.clear += 1; },
      refreshAccessToken: async () => { calls.refresh += 1; if (refresh) Object.assign(state, refresh); return Boolean(refresh); },
    },
  });
  return { redirects, calls,
    render: () => { effects = []; return AuthGate({ children: 'PRIVATE_BUSINESS' }); },
    flush: async () => { for (const effect of effects.splice(0)) effect(); await Promise.resolve(); await Promise.resolve(); },
  };
}
function containsBusiness(node) { return JSON.stringify(node).includes('PRIVATE_BUSINESS'); }
async function main() {
  for (const [role, route, allowed] of [
    ['teacher', '/teacher', true], ['teacher', '/teacher/quiz', true], ['student', '/student', true],
    ['teacher', '/materials', true], ['student', '/materials', true],
    ['student', '/teacher', false], ['teacher', '/student', false],
  ]) {
    const gate = harness(session(role), route);
    const initial = gate.render();
    await gate.flush();
    check(`${allowed ? '本角色页面正常渲染' : '伪造角色提示不赋予页面权限'}：${role} → ${route}`, () => {
      assert.equal(containsBusiness(initial), allowed, 'ready 曾为 true 时也不能闪现对方业务内容');
      assert.deepEqual(gate.redirects, allowed ? [] : ['/403']);
      assert.equal(gate.calls.refresh, 0);
    });
  }
  const changingIdentity = session('teacher');
  const changingGate = harness(changingIdentity, '/teacher');
  assert(containsBusiness(changingGate.render())); await changingGate.flush();
  changingIdentity.userRole = 'student';
  const changed = changingGate.render(); await changingGate.flush();
  check('前端越权跳转 403 页面：已就绪页面角色变化时先隐藏业务', () => {
    assert.equal(containsBusiness(changed), false); assert.deepEqual(changingGate.redirects, ['/403']);
  });
  for (const missing of [{ accessToken: null }, { userRole: null }]) {
    const gate = harness(session('teacher', missing), '/teacher');
    const initial = gate.render(); await gate.flush();
    check('身份恢复前不显示业务内容：缺少' + Object.keys(missing)[0], () => {
      assert.equal(containsBusiness(initial), false); assert.equal(gate.calls.refresh, 1);
      assert.equal(gate.calls.reset, 1); assert.equal(gate.calls.clear, 1); assert.deepEqual(gate.redirects, ['/login']);
    });
  }
  for (const role of ['teacher', 'student']) {
    const gate = harness(session(null, { accessToken: null }), '/teacher', { ready: false, refresh: session(role) });
    assert.equal(containsBusiness(gate.render()), false); await gate.flush();
    const beforeReady = gate.render(); await gate.flush();
    const settled = gate.render();
    check('刷新恢复后的角色仍须匹配：' + role, () => {
      assert.equal(containsBusiness(beforeReady), false);
      assert.equal(containsBusiness(settled), role === 'teacher');
      assert.deepEqual(gate.redirects, role === 'teacher' ? [] : ['/403']);
    });
  }
  const firstLogin = harness(session('student', { mustChangePassword: true }), '/teacher');
  assert.equal(containsBusiness(firstLogin.render()), false); await firstLogin.flush();
  check('身份恢复前不显示业务内容：首次改密优先', () => assert.deepEqual(firstLogin.redirects, ['/change-password']));
  const changePassword = harness(session('student', { mustChangePassword: true }), '/change-password');
  const passwordForm = changePassword.render(); await changePassword.flush();
  check('首次改密页面仍可用', () => { assert(containsBusiness(passwordForm)); assert.deepEqual(changePassword.redirects, []); });
  console.log(`Route guard regression: ${passed} checks passed`);
}
main().catch(error => { console.error(error); process.exitCode = 1; });
