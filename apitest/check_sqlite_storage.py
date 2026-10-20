"""Isolated SQLite journal modes, concurrent commits and database readiness."""
import json
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


with tempfile.TemporaryDirectory(prefix='sqlite-storage-test-') as tmp:
    os.environ['DATABASE_URL'] = f'sqlite:///{Path(tmp)/"probe.db"}'
    os.environ['UPLOAD_DIR'] = str(Path(tmp)/'uploads')
    os.environ['SQLITE_JOURNAL_MODE'] = 'DELETE'
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from config import Settings, settings
    from database import engine, Base
    import main

    checks = []
    def check(name, passed):
        checks.append({'name': name, 'passed': bool(passed)})
        if not passed:
            raise AssertionError(name)

    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE storage_probe(id INTEGER PRIMARY KEY)'))
    for offset, mode in [(0, 'DELETE'), (20, 'WAL')]:
        engine.dispose()
        settings.sqlite_journal_mode = mode
        with engine.connect() as connection:
            check(mode+' journal active', connection.exec_driver_sql('PRAGMA journal_mode').scalar().upper() == mode)
            check(mode+' synchronous safe', connection.exec_driver_sql('PRAGMA synchronous').scalar() == (2 if mode == 'DELETE' else 1))
            check(mode+' busy timeout', connection.exec_driver_sql('PRAGMA busy_timeout').scalar() == 15000)
        def commit_value(index):
            with engine.begin() as connection:
                connection.execute(text('INSERT INTO storage_probe(id) VALUES (:id)'), {'id': index+offset})
                return connection.execute(text('SELECT count(*) FROM storage_probe')).scalar() > 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            check(mode+' parallel commits', all(pool.map(commit_value, range(20))))
        with engine.connect() as connection:
            check(mode+' rows persisted', connection.exec_driver_sql('SELECT count(*) FROM storage_probe').scalar() == offset+20)
            check(mode+' integrity', connection.exec_driver_sql('PRAGMA integrity_check').scalar() == 'ok')
    with TestClient(main.app) as client:
        check('healthy database HTTP 200', client.get('/api/health').status_code == 200)
        original = main.engine
        class BrokenEngine:
            def connect(self):
                raise OperationalError('hidden SQL', {}, Exception('private database error'))
        try:
            main.engine = BrokenEngine()
            response = client.get('/api/health')
            check('unavailable database HTTP 503', response.status_code == 503)
            check('readiness error sanitized', response.json()['detail'] == '数据库暂不可用，请稍后重试')
        finally:
            main.engine = original
    try:
        Settings(sqlite_journal_mode='OFF')
        check('unsafe journal rejected', False)
    except ValueError:
        check('unsafe journal rejected', True)
    engine.dispose()
    print(json.dumps({'total': len(checks), 'passed': sum(c['passed'] for c in checks), 'checks': checks}, ensure_ascii=False))
