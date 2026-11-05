"""RabbitMQ适配：消息只有任务编号，持久消息、发布确认、手动消费确认。"""
import json
import logging

import pika

from config import settings

logging.getLogger("pika").setLevel(logging.WARNING)


class GradingQueue:
    def __init__(self):
        if not settings.grading_broker_password:
            raise ValueError("批改队列未配置")
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(
            host=settings.grading_broker_host, port=settings.grading_broker_port,
            credentials=pika.PlainCredentials(settings.grading_broker_user, settings.grading_broker_password),
            heartbeat=0, connection_attempts=1, socket_timeout=3, stack_timeout=5,
            blocked_connection_timeout=5,
        ))
        self.channel = self.connection.channel()
        for name in (settings.grading_queue, settings.grading_queue + ".dead"):
            self.channel.queue_declare(queue=name, durable=True)
        self.channel.confirm_delivery()
        self.channel.basic_qos(prefetch_count=1)

    def publish(self, task_id: int, dead: bool = False):
        self.channel.basic_publish(
            exchange="", routing_key=settings.grading_queue + (".dead" if dead else ""),
            body=json.dumps({"task_id": task_id}).encode(), mandatory=True,
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )

    def get(self):
        method, _, body = self.channel.basic_get(settings.grading_queue, auto_ack=False)
        if method is None:
            return None
        try:
            obj = json.loads(body)
            task_id = obj["task_id"]
            if type(task_id) is not int or task_id <= 0 or set(obj) != {"task_id"}:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            # 拒绝任意消息内容，不执行、不回显正文。
            self.channel.basic_reject(method.delivery_tag, requeue=False)
            return None
        return method.delivery_tag, task_id

    def ack(self, delivery_tag):
        self.channel.basic_ack(delivery_tag)

    def counts(self):
        return {key: self.channel.queue_declare(queue=name, passive=True).method.message_count
                for key, name in (("ready", settings.grading_queue), ("dead", settings.grading_queue + ".dead"))}

    def close(self):
        if self.connection.is_open:
            self.connection.close()
