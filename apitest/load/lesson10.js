// 第10课三接口压测（k6）。
// 用法：
//   k6 run -e BASE_URL=http://127.0.0.1:8080 -e SCENARIO=submit \
//     -e TEACHER_TOKEN=... -e HOMEWORK_ID=7 -e CONCURRENCY=10 -e DURATION=60s apitest/load/lesson10.js
// SCENARIO: submit（教师触发初批，202）| query（教师查任务）| retrieve（学生检索问答）
// 令牌只从环境变量读取，脚本不打印、不写报告。429 如实计为业务拒绝，不关闭生产限流。

import http from 'k6/http';
import { check } from 'k6';
import { Counter, Trend } from 'k6/metrics';

const scenario = __ENV.SCENARIO || 'query';
const base = __ENV.BASE_URL || 'http://127.0.0.1:8080';
const teacherToken = __ENV.TEACHER_TOKEN || '';
const studentToken = __ENV.STUDENT_TOKEN || '';
const homeworkId = __ENV.HOMEWORK_ID || '1';
const gradeTaskId = __ENV.GRADE_TASK_ID || '1';
const question = __ENV.QUESTION || '请提示这道题的思路';

const rejected = new Counter('business_rejected_total');
const okDuration = new Trend('accepted_request_duration');

export const options = {
  scenarios: {
    load: {
      executor: 'constant-vus',
      vus: Number(__ENV.CONCURRENCY || 1),
      duration: __ENV.DURATION || '60s',
      gracefulStop: '10s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<1'],
  },
};

function target() {
  if (scenario === 'submit') {
    return { url: `${base}/api/teacher/homeworks/${homeworkId}/ai-grade`, method: 'POST', token: teacherToken, body: null, expect: 202 };
  }
  if (scenario === 'retrieve') {
    return { url: `${base}/api/student/ai-question`, method: 'POST', token: studentToken, body: JSON.stringify({ question, subject: __ENV.SUBJECT || 'math' }), expect: 200 };
  }
  return { url: `${base}/api/teacher/grade-tasks/${gradeTaskId}`, method: 'GET', token: teacherToken, body: null, expect: 200 };
}

export default function () {
  const t = target();
  const params = {
    headers: { Authorization: `Bearer ${t.token}`, 'Content-Type': 'application/json' },
    tags: { scenario },
  };
  const response = t.method === 'POST' ? http.post(t.url, t.body, params) : http.get(t.url, params);
  if (response.status === 429) {
    rejected.add(1);
    return;
  }
  okDuration.add(response.timings.duration);
  check(response, { [`${scenario} 返回 ${t.expect}`]: (r) => r.status === t.expect });
}
