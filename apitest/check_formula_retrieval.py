"""Synthetic formula/heading retrieval and precise citation provenance."""
import hashlib
import json
import os
from pathlib import Path
import tempfile


with tempfile.TemporaryDirectory(prefix='formula-retrieval-', ignore_cleanup_errors=True) as temp:
    os.environ['DATABASE_URL'] = f'sqlite:///{temp}/test.db'
    os.environ['UPLOAD_DIR'] = temp+'/uploads'
    from database import Base, engine, SessionLocal
    from models import Class, User, Role, Material, MaterialChunk
    from embedding_service import embed_text
    from rag_search_service import retrieve_top_k, serialize_vector
    from routers.student import _retrieve_context
    from citation_service import validate_references
    from material_service import resolve_abs_path

    Base.metadata.create_all(engine)
    formula = r'$$\cos\theta=\frac{\vec a\cdot\vec b}{|\vec a||\vec b|}$$'
    heading = '### 两个非零向量夹角的余弦公式'
    pieces = [heading, formula, '### 平面法向量练习', 'A=(1,2,-2), B=(2,-1,2)。求平面法向量。']
    content = '\n\n'.join(pieces)
    checks = []
    def check(name, value):
        checks.append({'name':name,'passed':bool(value)})
        if not value: raise AssertionError(name)
    with SessionLocal() as db:
        db.add_all([Class(id=101,name='Synthetic A'),Class(id=102,name='Synthetic B')])
        db.add_all([User(id=1,identifier='T1',name='Synthetic teacher',role=Role.teacher,subject='math',password_hash='unused'),
                    User(id=2,identifier='T2',name='Synthetic physics',role=Role.teacher,subject='physics',password_hash='unused')])
        db.flush()
        for mid,cid,teacher in [(1,101,1),(2,102,1),(3,101,2)]:
            path=f'{cid}/formula-{mid}.md'; physical=resolve_abs_path(path);physical.parent.mkdir(parents=True,exist_ok=True);physical.write_bytes(content.encode('utf8'))
            db.add(Material(id=mid,class_id=cid,uploader_id=teacher,filename='空间向量.md',file_path=path,file_type='text/markdown',file_size=len(content.encode()),is_indexed=True,source_sha256=hashlib.sha256(content.encode()).hexdigest()))
            for index,piece in enumerate(pieces,1):
                db.add(MaterialChunk(material_id=mid,class_id=cid,chunk_index=index,content=piece,embedding=serialize_vector(embed_text(piece))))
        db.commit()
        question='已知空间向量 a=(1,2,-2), b=(2,-1,2)，求两向量夹角的余弦值'
        for mode in ['keyword','hybrid']:
            hits=retrieve_top_k(db,[101],question,subject='math',mode=mode)
            check(mode+' formula recalled despite coordinate distractor',any(h['content']==formula for h in hits))
            check(mode+' class and subject retained',all(h['material_id']==1 for h in hits))
            check(mode+' raw excerpts unchanged',all(h['content'] in pieces for h in hits))
        _,candidates=_retrieve_context(db,101,question,'math')
        match=next(c for c in candidates if c.excerpt==formula)
        answer,used=validate_references(f'根据讲义的夹角余弦公式[{match.reference_id}]，先计算数量积。',candidates)
        check('real formula reference retained',len(used)==1 and used[0].excerpt==formula)
        check('source fingerprint exact',used[0].file_sha256==hashlib.sha256(content.encode()).hexdigest())
        _,used=validate_references('这是自行计算，不标注来源。',candidates)
        check('no invented auto reference',not used)
        check('irrelevant question not forced into chapter',not retrieve_top_k(db,[101],'食堂营业时间几点钟',subject='math'))
        resolve_abs_path('101/formula-1.md').write_text('tampered',encoding='utf8')
        _,candidates=_retrieve_context(db,101,question,'math')
        check('tampered source excluded',not candidates)
    engine.dispose()
    print(json.dumps({'total':len(checks),'passed':sum(c['passed'] for c in checks),'checks':checks},ensure_ascii=False))
