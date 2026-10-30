"""Isolated subject library, answer separation, assets and publication acceptance."""
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import tempfile
import zipfile

import httpx


async def main():
    with tempfile.TemporaryDirectory(prefix='research-audit-', ignore_cleanup_errors=True) as temp:
        os.environ['DATABASE_URL'] = f'sqlite:///{temp}/audit.db'
        os.environ['UPLOAD_DIR'] = f'{temp}/uploads'
        from database import Base, SessionLocal, engine
        from main import app
        from models import Class, Material, MaterialAsset, MaterialChunk, MaterialPublication, ResearchMaterial, ResearchChunk, Role, User
        from material_service import resolve_abs_path
        from security import hash_password
        from knowledge_tags import knowledge_tags
        Base.metadata.create_all(engine)
        with SessionLocal() as db:
            db.add_all([Class(id=101, name='Class A'), Class(id=102, name='Class B')])
            for identifier, role, subject, classes, cid in [
                ('TM',Role.teacher,'math','[101,102]',None), ('TP',Role.teacher,'physics','[101,102]',None),
                ('TC',Role.teacher,'math','[102]',None), ('S1',Role.student,None,None,101), ('S2',Role.student,None,None,102)]:
                db.add(User(identifier=identifier, role=role, subject=subject, teaching_classes=classes, class_id=cid, name=identifier,
                            password_hash=hash_password('OnlyTest@2026'), must_change_password=False))
            db.commit()
        checks=[]
        def check(name, passed):
            checks.append((name,bool(passed)))
            assert passed,name
        check('geometry chapter creates knowledge topic',knowledge_tags('第一章 空间立体几何（学生版）.md','# 第一章 空间向量与立体几何','math')==['立体几何'])
        check('chapter title wins over incidental exercise',knowledge_tags('立体几何.md','# 立体几何\n### 一元二次方程练习','math')==['立体几何'])
        check('specific function topic is not duplicated',knowledge_tags('二次函数.md','# 二次函数','math')==['二次函数'])
        check('knowledge headings can provide topics',knowledge_tags('lesson.md','# 复习\n### 空间向量','math')==['空间向量'])
        check('unknown topic does not guess label',knowledge_tags('lesson.md','# 学习讲义\n这是课堂资料。','math')==[])
        check('subject vocabulary isolated',knowledge_tags('立体几何.md','# 立体几何','physics')==[])
        png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jV3sAAAAASUVORK5CYII=')
        teacher='# Math\n\n教师备课资料。\n\n## 二、核心知识点\n\n一元二次方程判别式为 $b^2-4ac$。\n\n## 三、代表例题\n\n### 例题 EX01\n\n**原题位置**：教师资料\n\n**题干**：求解一元二次方程 $x^2-5x+6=0$。\n\n![图](lesson.assets/figure.png)\n\n**答案**：SECRET_TEACHER_ANSWER_2_3\n\n**解答**：PRIVATE_SOLUTION\n\n## 四、备课使用建议\n\nTEACHER_ONLY_NOTES\n'
        def pack(entries):
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w') as z:
                for name,content in entries:z.writestr(name,content)
            return out.getvalue()
        package=pack([('lesson.md',teacher),('lesson.assets/figure.png',png),('provenance.json','{}')])
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            headers={}
            for who in ['TM','TP','TC','S1','S2']:
                r=await client.post('/api/auth/login',json={'identifier':who,'password':'OnlyTest@2026'})
                assert r.status_code==200
                headers[who]={'Authorization':'Bearer '+r.json()['access_token']}
            async def req(method,url,who='TM',**kwargs):
                return await client.request(method,url,headers=headers[who],**kwargs)
            r=await req('POST','/api/teacher/research-materials',files={'file':('lesson.zip',package,'application/zip')})
            check('import teacher package',r.status_code==200)
            source_id=r.json()['id'];prefix=f'/api/teacher/research-materials/{source_id}'
            check('original image and separate chunks',r.json()['asset_count']==1 and r.json()['chunk_count']>0)
            r=await req('POST','/api/teacher/research-materials',files={'file':('lesson.zip',package,'application/zip')})
            check('duplicate package reuses immutable source',r.status_code==200 and r.json()['id']==source_id)
            with SessionLocal() as db:
                check('import does not publish class material',db.query(Material).count()==0)
                check('teacher answer stored only in research content', 'SECRET_TEACHER_ANSWER' in db.get(ResearchMaterial,source_id).content and db.query(ResearchChunk).count()>0)
            r=await req('POST','/api/teacher/upload-material',data={'class_id':'101'},files={'file':('lesson.md',teacher,'text/markdown')})
            check('legacy class upload rejects teacher answer content',r.status_code==400)
            r=await req('POST','/api/teacher/upload-material',data={'class_id':'101'},files={'file':('讲义（教师版）.md','# content','text/markdown')})
            check('legacy class upload rejects teacher edition filename',r.status_code==400)
            r=await req('GET','/api/teacher/research-materials','TC')
            check('same subject colleagues share source',len(r.json()['items'])==1)
            r=await req('GET','/api/teacher/research-materials','TP')
            check('other subject sees no source',r.json()['items']==[])
            check('cross subject read denied',(await req('GET',prefix,'TP')).status_code==403)
            check('student library list denied',(await req('GET','/api/teacher/research-materials','S1')).status_code==403)
            check('student source read denied',(await req('GET',prefix,'S1')).status_code==403)
            check('student source generation denied',(await req('POST',prefix+'/student-preview','S1')).status_code==403)
            check('source image teacher only',(await req('GET',prefix+'/assets?name=lesson.assets/figure.png','S1')).status_code==403)
            check('cross subject source image denied',(await req('GET',prefix+'/assets?name=lesson.assets/figure.png','TP')).status_code==403)
            r=await req('GET',prefix+'/assets?name=lesson.assets/figure.png','TC')
            check('same subject source image exact',r.status_code==200 and r.content==png)
            r=await req('POST',prefix+'/student-preview')
            check('student preview generated',r.status_code==200)
            student=r.json()['content']
            check('preview preserves questions math and figures','x^2-5x+6=0' in student and 'lesson.assets/figure.png' in student)
            check('preview excludes answers solutions and teacher notes',all(x not in student for x in ['SECRET_TEACHER_ANSWER','PRIVATE_SOLUTION','TEACHER_ONLY_NOTES','**答案**','**解答**']))
            body={'class_ids':[101],'content':student,'reviewed':False}
            check('publication requires review',(await req('POST',prefix+'/publish',json=body)).status_code==400)
            body['reviewed']=True;body['class_ids']=[101,103]
            check('mixed unauthorized classes entire request denied',(await req('POST',prefix+'/publish',json=body)).status_code==403)
            with SessionLocal() as db:check('denied batch did not publish partial class',db.query(Material).count()==0)
            body['class_ids']=[101];body['content']=teacher
            check('teacher original cannot be published as student edition',(await req('POST',prefix+'/publish',json=body)).status_code==400)
            body['content']=student+'\n**解答**：do not publish'
            check('edited solution marker rejected',(await req('POST',prefix+'/publish',json=body)).status_code==400)
            body['content']=student+'\n![private](../teacher.png)'
            check('traversal image publication rejected',(await req('POST',prefix+'/publish',json=body)).status_code==400)
            body['content']=student+'\n[teacher](/api/teacher/research-materials/1)'
            check('teacher link publication rejected',(await req('POST',prefix+'/publish',json=body)).status_code==400)
            body['content']=student
            r=await req('POST',prefix+'/publish',json=body)
            check('publish authorized student edition',r.status_code==200 and r.json()['indexed']==[True])
            mid=r.json()['material_ids'][0]
            with SessionLocal() as db:
                check('only student content indexed',all('SECRET_TEACHER_ANSWER' not in c.content and 'PRIVATE_SOLUTION' not in c.content for c in db.query(MaterialChunk).all()))
                check('publication source trace retained',db.query(MaterialPublication).filter_by(material_id=mid,research_material_id=source_id).count()==1)
                check('teacher original unchanged',db.get(ResearchMaterial,source_id).content==teacher)
            r=await req('GET',f'/api/materials/{mid}/preview','S1')
            check('own class student sees student version',r.status_code==200 and r.text==student and 'PRIVATE_SOLUTION' not in r.text)
            r=await req('GET','/api/materials','S1')
            published=next(row for row in r.json()['items'] if row['id']==mid)
            check('published list includes knowledge topic and edition',published['tags']==['数学','一元二次方程','学生版'])
            check('other class cannot see published version',(await req('GET',f'/api/materials/{mid}/preview','S2')).status_code==403)
            r=await req('GET',f'/api/materials/{mid}/assets?name=lesson.assets/figure.png','S1')
            check('published image exact',r.status_code==200 and r.content==png)
            check('cross class image denied',(await req('GET',f'/api/materials/{mid}/assets?name=lesson.assets/figure.png','S2')).status_code==403)
            r=await req('GET',f'/api/materials/{mid}/bundle','S1')
            with zipfile.ZipFile(io.BytesIO(r.content)) as z:
                check('student bundle contains only student md and original figure',len(z.namelist())==2 and any(z.read(n)==student.encode() for n in z.namelist()) and z.read('lesson.assets/figure.png')==png)
            check('cross class bundle denied',(await req('GET',f'/api/materials/{mid}/bundle','S2')).status_code==403)
            for name,content in [('bad.md','![image](missing.png)'),('bad.zip',pack([('../escape.md','# bad')]))]:
                r=await req('POST','/api/teacher/research-materials',files={'file':(name,content,'application/octet-stream')})
                check('invalid import '+name,r.status_code==400)
            r=await req('POST','/api/teacher/research-materials',files={'file':('unknown.md','# unstructured\nAnswers may be mixed','text/markdown')})
            check('unknown format refuses automatic stripping',(await req('POST',f"/api/teacher/research-materials/{r.json()['id']}/student-preview")).status_code==422)
            with SessionLocal() as db:
                asset=db.query(MaterialAsset).filter_by(material_id=mid).one();asset_path=resolve_abs_path(asset.file_path)
                asset_path.write_bytes(b'changed')
            check('changed image rejected',(await req('GET',f'/api/materials/{mid}/assets?name=lesson.assets/figure.png','S1')).status_code==409)
            check('delete student publication',(await req('DELETE',f'/api/teacher/materials/{mid}')).status_code==200)
            with SessionLocal() as db:
                check('delete cleans publication and assets',db.query(MaterialPublication).count()==db.query(MaterialAsset).count()==0)
                check('delete publication preserves teacher original',db.get(ResearchMaterial,source_id) is not None)
            body['class_ids']=[101,102]
            r=await req('POST',prefix+'/publish',json=body)
            check('authorized multi class batch succeeds',r.status_code==200 and r.json()['indexed']==[True,True])
            mids=r.json()['material_ids']
            with SessionLocal() as db:
                check('multi class copies use distinct files',db.get(Material,mids[0]).file_path!=db.get(Material,mids[1]).file_path and db.query(MaterialAsset).count()==2)
            check('second class sees own student copy',(await req('GET',f'/api/materials/{mids[1]}/preview','S2')).status_code==200)
            check('first class cannot read second class copy',(await req('GET',f'/api/materials/{mids[1]}/preview','S1')).status_code==403)
        print(json.dumps({'passed':len(checks),'failed':0,'checks':[name for name,_ in checks]},ensure_ascii=True))


asyncio.run(main())
