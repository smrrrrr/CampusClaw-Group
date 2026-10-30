"""Isolated lesson workflow acceptance. All AI outputs mocked; no real accounts/files touched."""
import asyncio
import base64
import io
import json
import logging
import os
import tempfile
import zipfile
from urllib.parse import quote

import httpx


async def main():
    with tempfile.TemporaryDirectory(prefix='lesson-prep-test-', ignore_cleanup_errors=True) as temp:
        os.environ['DATABASE_URL'] = f'sqlite:///{temp}/test.db'
        os.environ['UPLOAD_DIR'] = f'{temp}/uploads'
        from database import Base, SessionLocal, engine
        from main import app
        from models import (Class, User, Role, LessonPlan, LessonPlanVersion, LessonPublication,
                            Material, MaterialChunk, ResearchMaterial, ResearchChunk, LessonGroupPublication, AuditLog)
        from security import hash_password
        from material_service import resolve_abs_path
        from lesson_service import validate_student, parse_student_output, build_resources, normalize_image_links, context_text
        from types import SimpleNamespace
        from llm_service import LLMGenerationError
        from routers import lesson_plans as lp
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            db.add_all([Class(id=101, name='Class A'), Class(id=102, name='Class B'), Class(id=103, name='Other')])
            for name, role, subject, classes, cid in [
                ('TM', Role.teacher, 'math', '[101,102]', None), ('TP', Role.teacher, 'physics', '[101,102]', None),
                ('TC', Role.teacher, 'math', '[101]', None), ('S1', Role.student, None, None, 101), ('S2', Role.student, None, None, 102)]:
                db.add(User(identifier=name, role=role, subject=subject, teaching_classes=classes, class_id=cid,
                            name=name, password_hash=hash_password('Test@2026'), must_change_password=False))
            db.commit()
        checks = []
        def check(name, passed):
            checks.append((name, bool(passed)))
            assert passed, name
        def events(response):
            assert response.status_code == 200, (response.status_code, response.text)
            return [json.loads(line[5:]) for line in response.text.splitlines() if line.startswith('data:')]
        def done(response):
            frames = events(response)
            assert frames[-1]['type'] == 'done', frames[-1]
            return frames[-1]['plan']
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jV3sAAAAASUVORK5CYII=')
        original = '# 空间向量与立体几何\n\n教师备课资料。\n\n## 二、核心知识点\n\n线面角用法向量与方向向量计算。\n\n## 三、代表例题\n\n### 例题 EX01 线面角\n\n**题干**：求直线与平面所成角。\n\n![原图](第一章 空间立体几何.assets/figure.png)\n\n**答案**：SECRET_TEACHER_ANSWER\n\n**解答**：PRIVATE_SOLUTION\n'
        package = io.BytesIO()
        with zipfile.ZipFile(package, 'w') as z:
            z.writestr('geometry.md', original); z.writestr('第一章 空间立体几何.assets/figure.png', image)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            headers = {}
            for who in ['TM', 'TP', 'TC', 'S1', 'S2']:
                r = await client.post('/api/auth/login', json={'identifier': who, 'password': 'Test@2026'})
                headers[who] = {'Authorization': 'Bearer ' + r.json()['access_token']}
            async def req(method, suffix='', who='TM', **kwargs):
                return await client.request(method, '/api/teacher/lesson-plans' + suffix, headers=headers[who], **kwargs)
            r = await client.post('/api/teacher/research-materials', headers=headers['TM'], files={'file': ('geometry.zip', package.getvalue(), 'application/zip')})
            check('teacher source imported', r.status_code == 200)
            sid = r.json()['id']; asset_name = f'sources/{sid}/第一章 空间立体几何.assets/figure.png'
            teacher = ('# 线面角教师教案\n\n## 教学目标\n理解方向向量与法向量的关系。[S1]\n\n## 教学重难点\n'
                       '掌握正弦值与余弦值的区别。\n\n## 教学过程\n导入5分钟、探究15分钟、例题15分钟、练习8分钟、总结2分钟。\n'
                       '教师应依据班级基础安排提问，这是教学设计补充。\n\n## 例题及教师解答\n### EX01\n'
                       f'求直线与平面所成角。\n![题图]({asset_name})\n**答案**：SECRET_TEACHER_ANSWER\n'
                       '**解答**：PRIVATE_SOLUTION\n\n## 课堂练习\n学生尝试解题。\n\n## 课后任务\n复习公式。\n\n## 板书设计\n公式与步骤。\n')
            student_lesson = f'# 线面角学生教案\n\n## 学习目标\n掌握线面角。\n\n## 课堂活动\n观察原图，先建立空间直角坐标系。\n![题图]({asset_name})\n'
            handout = f'# 线面角学生讲义\n\n### EX01\n求直线与平面所成角。\n![题图]({asset_name})\n\n**作答区**：\n\n________________\n'
            output = teacher
            prompts = []
            async def fake_stream(messages, **kwargs):
                prompts.append(messages)
                for i in range(0, len(output), 80):
                    yield output[i:i + 80]
            async def fail_stream(messages, **kwargs):
                yield 'partial'
                raise LLMGenerationError('fake provider failure')
            lp.stream_chat = fake_stream
            body = dict(class_id=101, topic='线面角', duration=45, scope='仅线面角，原题 EX01', class_profile='基础一般', research_material_ids=[sid])
            check('unauthenticated rejected', (await client.get('/api/teacher/lesson-plans')).status_code == 401)
            check('student list rejected', (await req('GET', who='S1')).status_code == 403)
            check('student generation rejected', (await req('POST', '/generate', who='S1', json=body)).status_code == 403)
            check('nonteaching class rejected', (await req('POST', '/generate', json={**body, 'class_id': 103})).status_code == 403)
            check('cross subject source rejected', (await req('POST', '/generate', who='TP', json=body)).status_code == 403)
            check('empty sources rejected', (await req('POST', '/generate', json={**body, 'research_material_ids': []})).status_code == 422)
            check('invalid duration rejected', (await req('POST', '/generate', json={**body, 'duration': 0})).status_code == 422)
            lp.settings.deepseek_api_key = ''
            check('unconfigured AI is explicit 503', (await req('POST', '/generate', json=body)).status_code == 503)
            lp.settings.deepseek_api_key = 'test-key'
            lp.stream_chat = fail_stream
            r = await req('POST', '/generate', json=body)
            check('AI error produces error event', events(r)[-1]['type'] == 'error')
            with SessionLocal() as db: check('partial AI not saved', db.query(LessonPlan).count() == 0)
            lp.stream_chat = fake_stream
            output = teacher + '[S999]'
            check('invented citation rejected', events(await req('POST', '/generate', json=body))[-1]['type'] == 'error')
            output = teacher
            r = await req('POST', '/generate', json=body); p = done(r); pid = p['id']; path = f'/{pid}'
            check('teacher draft saved with actual stream', p['status'] == 'draft' and any(e['type'] == 'delta' for e in events(r)))
            check('selected class context and manual profile passed', '基础一般' in prompts[-1][1]['content'] and 'Class A' in prompts[-1][1]['content'])
            refs = p['resources']['references']
            check('reference excerpts exact and lines traceable', all('\n'.join(original.splitlines()[r['start_line'] - 1:r['end_line']]).rstrip() == r['excerpt'] for r in refs))
            check('teacher generation fixes raw spaced image destinations', quote(asset_name, safe='/') in p['content'] and asset_name not in p['content'])
            check('version fingerprint retained', all(len(r['file_sha256']) == 64 for r in refs))
            check('same subject colleague private plan denied', (await req('GET', path, who='TC')).status_code == 403)
            check('cross subject plan denied', (await req('GET', path, who='TP')).status_code == 403)
            check('student plan denied', (await req('GET', path, who='S1')).status_code == 403)
            check('other teacher list empty', (await req('GET', who='TC')).json()['items'] == [])
            check('list class filter access checked', (await req('GET', '?class_id=103')).status_code == 403)
            rev = lambda: {'revision': p['revision']}
            check('cannot finalize unreviewed draft', (await req('POST', path + '/finalize', json=rev())).status_code == 400)
            check('draft cannot share to group', (await req('POST', path + '/share-to-group', json=rev())).status_code == 409)
            check('default private plan has no group publication', p['group_publications'] == [])
            check('review requires explicit check', (await req('POST', path + '/review', json=rev())).status_code == 400)
            check('cannot generate students before final', (await req('POST', path + '/student-drafts', json=rev())).status_code == 409)
            check('unknown rewrite section rejected', (await req('POST', path + '/regenerate-section', json={**rev(), 'heading': '## Missing'})).status_code == 400)
            output = '## 教学目标\n不应替换另一个章节。'
            check('wrong AI section boundaries rejected', events(await req('POST', path + '/regenerate-section', json={**rev(), 'heading': '## 教学重难点'}))[-1]['type'] == 'error')
            original_before = p['content']
            check('failed section rewrite keeps original', (await req('GET', path)).json()['content'] == original_before)
            output = '## 教学重难点\n\n教学设计补充：增加学生讨论，区分线面角与向量夹角。'
            p = done(await req('POST', path + '/regenerate-section', json={**rev(), 'heading': '## 教学重难点', 'instructions': '增加学生讨论'}))
            check('section rewrite changes only selected block', '增加学生讨论' in p['content'] and p['content'].split('## 教学过程')[1] == original_before.split('## 教学过程')[1] and p['content'].split('## 教学重难点')[0] == original_before.split('## 教学重难点')[0])
            output = teacher
            old = p['revision']
            p = (await req('PUT', path, json={**rev(), 'content': teacher + '\n教学设计补充：注意学生基础。'})).json()
            check('edit saved and remains draft', p['revision'] == old + 1 and p['status'] == 'draft')
            check('stale window cannot overwrite', (await req('PUT', path, json={'revision': old, 'content': teacher})).status_code == 409)
            check('private URLs rejected', (await req('PUT', path, json={**rev(), 'content': teacher + '\n[secret](/api/teacher/research-materials/1)'})).status_code == 400)
            p = (await req('POST', path + '/review', json={**rev(), 'reviewed': True})).json()
            check('review state persisted', p['status'] == 'reviewed')
            p = (await req('PUT', path, json={**rev(), 'content': teacher + '\n教学设计补充：修改。'})).json()
            check('editing reviewed invalidates review', p['status'] == 'draft')
            p = (await req('POST', path + '/review', json={**rev(), 'reviewed': True})).json()
            p = (await req('POST', path + '/finalize', json=rev())).json()
            check('final snapshot v1', p['status'] == 'final' and p['current_version'] == 1 and len(p['versions']) == 1)
            first_final = p['content']
            check('final is not automatically shared', p['group_publications'] == [])
            check('student cannot share teacher plan', (await req('POST', path + '/share-to-group', who='S1', json=rev())).status_code == 403)
            check('colleague cannot share private original', (await req('POST', path + '/share-to-group', who='TC', json=rev())).status_code == 403)
            check('stale revision cannot share', (await req('POST', path + '/share-to-group', json={'revision':p['revision'] - 1})).status_code == 409)
            r = await req('POST', path + '/share-to-group', json=rev())
            check('explicitly share current final', r.status_code == 200)
            shared_id = r.json()['research_material_id']; p = r.json()['plan']
            check('share state records version and group material', p['group_publications'][0]['version'] == 1 and p['group_publications'][0]['research_material_id'] == shared_id)
            r = await req('POST', path + '/share-to-group', json=rev())
            check('same final share is idempotent', r.status_code == 200 and r.json()['research_material_id'] == shared_id)
            p = r.json()['plan']
            group_url = f'/api/teacher/research-materials/{shared_id}'
            async def group_req(method, tail='', who='TC', **kwargs):
                return await client.request(method, group_url + tail, headers=headers[who], **kwargs)
            r = await group_req('GET')
            check('same subject colleague sees full teacher snapshot', r.status_code == 200 and r.json()['content'] == first_final and 'PRIVATE_SOLUTION' in r.json()['content'])
            check('shared type and source provenance retained', r.json()['kind'] == 'lesson-plan' and r.json()['lesson_version'] == 1 and r.json()['lesson_sources'] == p['resources']['references'])
            r = await client.get('/api/teacher/research-materials', headers=headers['TC'])
            check('shared plan appears in subject library', any(x['id'] == shared_id and x['kind'] == 'lesson-plan' for x in r.json()['items']))
            check('other subject cannot read shared full answer', (await group_req('GET', who='TP')).status_code == 403)
            check('student cannot read shared full answer', (await group_req('GET', who='S1')).status_code == 403)
            r = await group_req('GET', '/assets', params={'name':asset_name})
            check('group figure copied exactly', r.status_code == 200 and r.content == image)
            check('student cannot read group figure', (await group_req('GET', '/assets', who='S1', params={'name':asset_name})).status_code == 403)
            check('other subject cannot download group bundle', (await group_req('GET', '/bundle', who='TP')).status_code == 403)
            check('student cannot download group bundle', (await group_req('GET', '/bundle', who='S1')).status_code == 403)
            r = await group_req('GET', '/bundle')
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                check('shared teacher bundle includes snapshot and used original figure', len(z.namelist()) == 2 and z.read(asset_name) == image and any(z.read(n) == first_final.encode() for n in z.namelist()))
            check('shared teacher plan cannot use simple student stripping', (await group_req('POST', '/student-preview')).status_code == 422)
            check('shared teacher plan cannot bypass student workflow', (await group_req('POST', '/publish', json={'class_ids':[101],'content':handout,'reviewed':True})).status_code == 400)
            with SessionLocal() as db:
                check('sharing never publishes into student class', db.query(Material).count() == 0 and db.query(MaterialChunk).count() == 0)
                check('sharing indexes only subject research chunks', db.query(ResearchChunk).filter_by(research_material_id=shared_id).count() > 0)
                shared = db.get(ResearchMaterial, shared_id)
                new_context = context_text(build_resources([shared], '线面角', ''))
                check('reusing shared plan strips old source number scope', new_context.count('[S1]') == 1)
                colleague = db.query(User).filter_by(identifier='TC').one(); colleague.teaching_classes = '[102]'; db.commit()
            check('group share does not require authors class relation', (await group_req('GET')).status_code == 200)
            check('original private plan remains inaccessible after sharing', (await req('GET', path, who='TC')).status_code == 403)
            check('final cannot edit without revise', (await req('PUT', path, json={**rev(), 'content': teacher})).status_code == 409)
            check('final section rewrite requires new revision', (await req('POST', path + '/regenerate-section', json={**rev(), 'heading': '## 教学目标'})).status_code == 409)
            pair = {'student_lesson': student_lesson, 'student_handout': handout}
            encoded_lesson = normalize_image_links(student_lesson)
            encoded_handout = normalize_image_links(handout)
            check('image path encoding is idempotent', normalize_image_links(encoded_handout) == encoded_handout)
            check('source paths encoded before sending to AI', quote(asset_name, safe='/') in context_text(p['resources']))
            check('code examples are preserved', normalize_image_links('`'+handout.splitlines()[4]+'`') == '`'+handout.splitlines()[4]+'`')
            normalized = parse_student_output(json.dumps({**pair, 'student_handout': handout + '\n\\vspace{3cm}'}), p['resources'])
            check('AI layout command converted to Markdown answer lines', '\\vspace' not in normalized['student_handout'] and normalized['student_handout'].count('______________________________') == 3)
            many_sections = '\n'.join(f'## 线面角 {i}\n线面角知识点。' for i in range(25))
            two_sources = [SimpleNamespace(id=1, filename='a.md', content=many_sections, assets_json='[]', source_sha256='a'*64), SimpleNamespace(id=2, filename='b.md', content='# 辅助资料\n基础知识。', assets_json='[]', source_sha256='b'*64)]
            selection = build_resources(two_sources, '线面角', '')
            check('all selected sources contribute complete sections', {r['research_material_id'] for r in selection['references']} == {1, 2})
            output = json.dumps(pair, ensure_ascii=False)
            p = done(await req('POST', path + '/student-drafts', json=rev()))
            check('both student drafts tied to final', p['student_from_version'] == 1 and p['student_handout'] == encoded_handout and p['student_lesson'] == encoded_lesson)
            check('student generation uses actual final', first_final in prompts[-1][1]['content'])
            output = '{broken json'
            check('broken student response gives error', events(await req('POST', path + '/student-drafts', json=rev()))[-1]['type'] == 'error')
            check('failed regeneration preserves existing students', (await req('GET', path)).json()['student_handout'] == encoded_handout)
            # harden-model-json-escapes 4.3：学生稿用同一修补规则，单反斜杠公式仍能保存
            BS, DBS = '\\', '\\\\'
            latex_lesson = (f'# 线面角学生教案\n\n## 学习目标\n理解 ${DBS}vec{{a}}$ 与 ${BS}overrightarrow{{AB}}$ 的关系。\n\n'
                            f'## 课堂活动\n计算 ${BS}frac{{1}}{{2}}$，并比较 ${BS}cos{BS}theta$ 与已知 ${BS}sqrt{{2}}$。\n')
            latex_handout = (f'# 线面角学生讲义\n\n### EX01\n求 ${BS}vec{{a}}{BS}cdot{DBS}vec{{b}}$ 的夹角。\n\n'
                             f'由题意得 ${BS}tan{DBS}alpha=1$\\n第二步用 ${BS}neq$ 判断。\n\n________________\n')
            # 模型真实输出的形态：手写 JSON 原文，单反斜杠不转义
            output = ('{"student_lesson": "' + latex_lesson.replace('\n', DBS + 'n') + '", '
                      '"student_handout": "' + latex_handout.replace('\n', DBS + 'n') + '"}')
            # 修补次数要真正写进服务端日志（design §6），且不带学生稿正文
            lesson_logger = logging.getLogger('lesson_service')
            repair_records = []
            capture = logging.Handler()
            capture.emit = repair_records.append
            lesson_logger.addHandler(capture)
            try:
                check('单反斜杠学生稿：重新生成成功并保存', events(await req('POST', path + '/student-drafts', json=rev()))[-1]['type'] == 'done')
            finally:
                lesson_logger.removeHandler(capture)
            repair_messages = [r.getMessage() for r in repair_records if '修补' in r.getMessage()]
            # 日志由根 logger 统一输出为 JSON（engineering-baseline），这里判断“确实有处理器会写出”，不再要求模块自挂处理器
            output_handlers = list(lesson_logger.handlers) + (logging.getLogger().handlers if lesson_logger.propagate else [])
            check('单反斜杠学生稿：修补次数写入服务端日志且不含正文',
                  lesson_logger.isEnabledFor(logging.INFO)
                  and any(h is not capture for h in output_handlers)
                  and len(repair_messages) == 1
                  and isinstance(repair_records[0].args[0], int) and repair_records[0].args[0] > 0
                  and '线面角' not in repair_messages[0] and 'vec' not in repair_messages[0])
            saved_pair = (await req('GET', path)).json()
            # 学生稿每次保存都会推进教案修订号，后续请求用最新修订号
            current_rev = saved_pair['revision']
            check('单反斜杠学生稿：公式还原为 LaTeX 命令',
                  all(cmd in saved_pair.get('student_handout', '') for cmd in
                      (BS + 'vec{a}', BS + 'cdot', BS + 'tan', BS + 'alpha', BS + 'neq'))
                  and BS + 'overrightarrow{AB}' in saved_pair.get('student_lesson', '')
                  and BS + 'frac{1}{2}' in saved_pair.get('student_lesson', ''))
            check('单反斜杠学生稿：合法换行保留、不含控制字符',
                  '第二步用' in saved_pair.get('student_handout', '')
                  and '\f' not in saved_pair.get('student_handout', '')
                  and '\b' not in saved_pair.get('student_lesson', ''))
            good_lesson, good_handout = saved_pair['student_lesson'], saved_pair['student_handout']
            # 漏网控制字符：学生稿含换页（U+000C）时拒绝保存，旧稿保持不变
            control_lesson = '# 线面角\n\n含换页' + chr(12) + '残留公式\n'
            output = json.dumps({**pair, 'student_lesson': control_lesson}, ensure_ascii=False)
            check('学生稿含 U+000C：返回 error',
                  events(await req('POST', path + '/student-drafts', json={'revision': current_rev}))[-1]['type'] == 'error')
            after_control = (await req('GET', path)).json()
            check('学生稿含 U+000C：旧稿保持不变',
                  after_control['student_lesson'] == good_lesson and after_control['student_handout'] == good_handout)
            check('学生稿含 U+000C：手工编辑同样拒绝保存',
                  (await req('PUT', path + '/student-drafts',
                             json={'revision': after_control['revision'], **pair,
                                   'student_lesson': control_lesson})).status_code == 400)
            # 学生稿保存推进了修订号：刷新 p，后续用例继续用最新修订号
            p = (await req('GET', path)).json()
            output = json.dumps(pair, ensure_ascii=False)
            output = json.dumps({**pair, 'student_lesson': '**答案**：PRIVATE_SOLUTION'})
            check('AI answer marker rejected before saving', events(await req('POST', path + '/student-drafts', json=rev()))[-1]['type'] == 'error')
            check('manual teacher solution rejected', (await req('PUT', path + '/student-drafts', json={**rev(), **pair, 'student_handout': teacher})).status_code == 400)
            check('unmanaged student figure rejected', (await req('PUT', path + '/student-drafts', json={**rev(), **pair, 'student_handout': handout + '![bad](other.png)'})).status_code == 400)
            validate_student('# 学习\n\n当 $x<0$，当 $x>1$。', p['resources'])
            check('math inequality is not mistaken for HTML', True)
            try:
                validate_student('<script>alert(1)</script>', p['resources'])
                check('HTML blocked', False)
            except ValueError:
                check('HTML blocked', True)
            p = (await req('PUT', path + '/student-drafts', json={**rev(), **pair})).json()
            publish = lambda kind, classes, checked=True: {**rev(), 'kind': kind, 'class_ids': classes, 'reviewed': checked}
            check('publication review required', (await req('POST', path + '/publish', json=publish('lesson', [101], False))).status_code == 400)
            check('mixed unauthorized publication denied', (await req('POST', path + '/publish', json=publish('handout', [101, 103]))).status_code == 403)
            with SessionLocal() as db: check('bad batch publishes nothing', db.query(Material).count() == 0)
            r = await req('POST', path + '/publish', json=publish('lesson', [101])); check('student lesson publishes', r.status_code == 200)
            result = r.json(); p = result['plan']; lesson_mid = result['material_ids'][0]
            r = await req('POST', path + '/publish', json=publish('lesson', [101])); p = r.json()['plan']
            check('repeat publication reuses class copy', r.json()['material_ids'] == [lesson_mid])
            r = await req('POST', path + '/publish', json=publish('handout', [101, 102])); result = r.json(); p = result['plan']
            check('handout publishes both classes with index', r.status_code == 200 and result['indexed'] == [True, True])
            mids = result['material_ids']; own_mid = mids[0]
            with SessionLocal() as db:
                check('only safe student documents indexed', db.query(Material).count() == 3 and all('SECRET_TEACHER' not in c.content and 'PRIVATE_SOLUTION' not in c.content for c in db.query(MaterialChunk).all()))
                check('all publications trace final version', db.query(LessonPublication).count() == 3 and all(x.version == 1 for x in db.query(LessonPublication).all()))
                check('teacher original intact', db.get(ResearchMaterial, sid).content == original)
            r = await client.get(f'/api/materials/{own_mid}/preview', headers=headers['S1'])
            check('student sees only public handout', r.status_code == 200 and r.text == encoded_handout)
            r = await client.get(f'/api/materials/{lesson_mid}/preview', headers=headers['S2'])
            check('other class cannot read student lesson', r.status_code == 403)
            r = await client.get(f'/api/materials/{own_mid}/assets', params={'name': asset_name}, headers=headers['S1'])
            check('public figure exact original', r.status_code == 200 and r.content == image)
            check('private plan figure student denied', (await req('GET', path + '/assets?name=' + asset_name, who='S1')).status_code == 403)
            r = await client.get(f'/api/materials/{own_mid}/bundle', headers=headers['S1'])
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                check('bundle has student text and only used image', len(z.namelist()) == 2 and z.read(asset_name) == image and any(z.read(n) == encoded_handout.encode() for n in z.namelist()))
            with SessionLocal() as db:
                owner = db.query(User).filter_by(identifier='TM').one(); owner.teaching_classes = '[102]'; db.commit()
            check('revoked class relation defeats stale JWT', (await req('GET', path)).status_code == 403)
            check('revoked class not listed', (await req('GET')).json()['items'] == [])
            with SessionLocal() as db:
                owner = db.query(User).filter_by(identifier='TM').one(); owner.teaching_classes = '[101,102]'; db.commit()
            p = (await req('POST', path + '/revise', json=rev())).json()
            check('revision clears student drafts but keeps snapshot', p['status'] == 'draft' and not p['student_handout'] and p['student_from_version'] is None and p['versions'][0]['content'] == first_final)
            check('new private revision does not mutate group snapshot', (await group_req('GET')).json()['content'] == first_final)
            p = (await req('PUT', path, json={**rev(), 'content': teacher + '\n教学设计补充：第二版。'})).json()
            p = (await req('POST', path + '/review', json={**rev(), 'reviewed': True})).json()
            p = (await req('POST', path + '/finalize', json=rev())).json()
            check('new final retains v1 and v2', p['current_version'] == 2 and len(p['versions']) == 2 and p['versions'][1]['content'] == first_final)
            check('new final not automatically shared', [x['version'] for x in p['group_publications']] == [1])
            r = await req('POST', path + '/share-to-group', json=rev()); p = r.json()['plan']
            check('new final shared only by new explicit action', r.status_code == 200 and r.json()['research_material_id'] != shared_id and len(p['group_publications']) == 2)
            check('old shared version stays immutable', (await group_req('GET')).json()['content'] == first_final)
            check('new final cannot publish old student drafts', (await req('POST', path + '/publish', json=publish('handout', [101]))).status_code == 409)
            with SessionLocal() as db:
                file_path = db.get(ResearchMaterial, sid).file_path
            resolve_abs_path(file_path).write_text('# tampered', encoding='utf-8')
            check('tampered source blocked for new generation', (await req('POST', '/generate', json=body)).status_code == 409)
            check('tampered source blocks student generation', (await req('POST', path + '/student-drafts', json=rev())).status_code == 409)
            r = await group_req('GET', '/assets', params={'name':asset_name})
            check('shared image independent of original source file', r.status_code == 200 and r.content == image)
            check('other teacher cannot delete', (await req('DELETE', path, who='TC', json=rev())).status_code == 403)
            r = await req('DELETE', path, json=rev()); check('delete owned plan', r.status_code == 200)
            check('deleted plan returns 404', (await req('GET', path)).status_code == 404)
            with SessionLocal() as db:
                check('versions and plan links cleaned', db.query(LessonPlanVersion).count() == 0 and db.query(LessonPublication).count() == 0)
                check('published materials retained on delete', db.query(Material).count() == 3)
                check('shared copies retained after private plan deletion', db.query(LessonGroupPublication).count() == 2 and all(x.lesson_plan_id is None for x in db.query(LessonGroupPublication).all()))
                check('writes and denials audited', db.query(AuditLog).filter(AuditLog.request_path.like('%lesson-plans%')).count() > 10)
            r = await client.delete(f'/api/teacher/materials/{own_mid}', headers=headers['TM'])
            check('published lesson material deletable via normal class route', r.status_code == 200)
            check('shared final remains readable after deleting private original', (await group_req('GET')).status_code == 200)
        print(json.dumps({'passed': sum(x[1] for x in checks), 'failed': sum(not x[1] for x in checks), 'checks': checks}, ensure_ascii=True))


asyncio.run(main())
