"""独立投递/消费进程：python grading_worker.py --mode dispatch|consume|both。"""
import argparse
import logging
import signal
import time

from config import settings
from database import Base, SessionLocal, engine, run_simple_migrations
from grading_queue import GradingQueue
from grading_service import dispatch, process_task, recover_pending_deliveries
from logging_setup import configure_logging, request_id_var
from models import GradeTask

logger = logging.getLogger(__name__)


def run(mode):
    configure_logging()
    run_simple_migrations()
    Base.metadata.create_all(engine)
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    queue = None
    while not stopping:
        try:
            if queue is None:
                queue = GradingQueue()
            if mode in ("dispatch", "both"):
                dispatch(queue)
            item = queue.get() if mode in ("consume", "both") else None
            if item:
                tag, task_id = item
                with SessionLocal() as db:
                    task = db.get(GradeTask, task_id)
                    request_id = task.request_id if task else None
                token = request_id_var.set(request_id)
                try:
                    state = process_task(task_id)
                    logger.info("批改任务消息处理完成", extra={"task_id": task_id, "status": state})
                    queue.ack(tag)
                finally:
                    request_id_var.reset(token)
            else:
                # 分段等待，SIGTERM可在一次轮询后退出；不接收新的任务。
                time.sleep(settings.grading_poll_seconds)
        except Exception:
            logger.warning("批改队列暂不可用，将自动重连")
            if queue:
                try:
                    queue.close()
                except Exception:
                    pass
            queue = None
            time.sleep(settings.grading_poll_seconds)
    if queue:
        queue.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="作业异步初批后台进程")
    parser.add_argument("--mode", choices=("dispatch", "consume", "both"), default="both")
    parser.add_argument("--recover-pending", action="store_true", help="消费者停止且确认代理消息丢失后，显式恢复待执行投递；执行后退出")
    args = parser.parse_args()
    if args.recover_pending:
        configure_logging()
        with SessionLocal() as db:
            count = recover_pending_deliveries(db)
        logger.warning("管理员显式恢复待执行消息投递", extra={"task_count": count})
    else:
        run(args.mode)
