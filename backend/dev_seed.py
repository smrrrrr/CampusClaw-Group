"""开发用种子数据：建表 + 插入测试账号（幂等，可反复运行）。

账号体系（一人一号，无家长端）：
- 教师：张老师（TEA001，数学，任教 101+102，101 班班主任）、
        李老师（TEA002，物理，任教 101+102，102 班班主任）
- 学生：李明（20260001，一班）、王芳（20260002，二班）
"""

import json

from database import Base, SessionLocal, engine, run_simple_migrations
from models import Class, Role, User
from security import hash_password

Base.metadata.create_all(bind=engine)
run_simple_migrations()

db = SessionLocal()
try:
    # 班级
    for cid, cname in [(101, "高二（1）班"), (102, "高二（2）班")]:
        obj = db.query(Class).filter_by(id=cid).first()
        if not obj:
            db.add(Class(id=cid, name=cname))
    db.commit()

    # 教师（已改密，可直接登录）
    teachers = [
        # (工号, 姓名, 学科, 任教班级, 班主任班级)
        ("TEA001", "张老师", "math", [101, 102], 101),
        ("TEA002", "李老师", "physics", [101, 102], 102),
    ]
    for tid, tname, subject, classes, homeroom in teachers:
        t = db.query(User).filter_by(identifier=tid).first()
        if not t:
            t = User(
                role=Role.teacher,
                identifier=tid,
                password_hash=hash_password("Teach@2026"),
                name=tname,
                must_change_password=False,
            )
            db.add(t)
        t.name = tname
        t.teaching_classes = json.dumps(classes)
        t.subject = subject
        t.homeroom_class_id = homeroom
    db.commit()

    # 学生（一人一号：每个学生一个独立学号，删除多娃手机号绑定）
    seeds = [
        ("20260001", "李明", 101),
        ("20260002", "王芳", 102),
    ]
    for ident, name, cid in seeds:
        u = db.query(User).filter_by(identifier=ident).first()
        if not u:
            u = User(
                role=Role.student,
                identifier=ident,
                password_hash=hash_password("thu" + ident[-6:]),
                name=name,
                class_id=cid,
                must_change_password=True,
            )
            db.add(u)
        else:
            # 强制重置为初始密码（开发用）
            u.password_hash = hash_password("thu" + ident[-6:])
            u.must_change_password = True
            u.class_id = cid
            u.name = name
    # 清理不在种子清单中的学生（如旧的多娃/单娃账号 20230003）
    seed_identifiers = {ident for ident, _, _ in seeds}
    for u in db.query(User).filter(User.role == Role.student).all():
        if u.identifier not in seed_identifiers:
            db.delete(u)
    db.commit()

    print("=== 种子数据就绪 ===")
    for u in db.query(User).order_by(User.id).all():
        tc = json.loads(u.teaching_classes) if u.teaching_classes else None
        print(
            f"  {u.role.value:8s} | {u.identifier} | {u.name} | subject={u.subject} | "
            f"class={u.class_id} | teaching={tc} | homeroom={u.homeroom_class_id} | mcp={u.must_change_password}"
        )
finally:
    db.close()
