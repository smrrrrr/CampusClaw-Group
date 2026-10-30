## Why

作业批改（`add-homework-grading`）和错题本（`add-mistake-notebook`）已落地，学生端「学情分析」页与教师端「本班学情」入口仍全部为演示/占位数据。学生无法看到真实的作业正确率、错题分布和学科掌握度，教师也无法按班级或学科查看学情汇总。本变更将学情诊断接入真实数据，补齐从数据采集到 AI 画像的闭环。

## What Changes

- 新增后端学情诊断服务与接口：
  - 学生本人学情概览（累计提问、作业提交数、作业正确率、错题累计）
  - 学生各学科掌握度（基于作业 `teacher_score` 与错题未掌握率计算）、近期成绩趋势、综合掌握度
  - AI 学习画像（基于提问、作业、错题生成学习风格、优势学科、待提升学科与建议）
  - 教师班级学情汇总（班主任全科 / 任课单科）：班级平均分、各分数段分布、提交率、错题率、学生掌握度排行
- 学生端学情分析页由演示数据改为调用真实接口，保留原有图表结构（统计卡、雷达图、环图、趋势、热力、AI 画像）
- 教师端「本班学情（全科）」与「学情分析（单科）」由占位改为真实数据展示
- 所有数据严格按身份、班级、学科、本人归属隔离；AI 画像只读取本人/本班数据

## Capabilities

### New Capabilities
- `learning-diagnostics`: 学情诊断后端能力——学生本人学情统计、学科掌握度计算、AI 学习画像生成、教师班级/学科学情汇总。

### Modified Capabilities
- `student-workspace`: 「学情分析演示界面」需求由静态演示数据改为调用真实学情接口；统计卡、雷达图、环图、趋势、热力、AI 画像均展示本人真实数据。
- `teacher-workspace`: 班主任「本班学情（全科）」与任课「学情分析（单科）」由占位改为真实班级学情数据。

## Impact

- 后端新增 `analytics_service.py` 与 `routers/analytics.py`，在 `main.py` 注册
- 复用 `Homework`、`HomeworkSubmission`、`MistakeNote`、`Conversation`、`Message` 表，不改表结构
- AI 画像复用 `llm_service.generate_answer`，未配置 Key 时降级
- 前端 `lib/api.ts` 新增学情接口；`app/student/page.tsx` 与教师端页面接入真实数据
- 需在 `scripts/check_layering.py` 登记 `analytics_service: BUSINESS`
