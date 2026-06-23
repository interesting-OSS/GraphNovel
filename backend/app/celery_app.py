"""Celery application — async task queue backed by Redis broker.

Used for: batch generation, batch analysis, batch polish, book import,
and other long-running operations that should not block the HTTP request.
"""
from celery import Celery  
"""
它是用来处理耗时任务或定时任务的后台工具。它的核心思想是：把耗时的、
不急着立刻返回结果的工作拿到后台去异步执行，
让主程序（比如你的网页、API）能够秒回响应。
"""
from app.config import settings

app = Celery(
    "langnovel",
    broker=settings.redis_url,
    broker_connection_retry_on_startup=True,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    worker_send_task_events=True,
    task_send_sent_event=True,
    result_expires=86400,  # 24h
    task_default_queue="langnovel",
    task_routes={
        "app.celery_tasks.*": {"queue": "langnovel"},
    },
)

app.autodiscover_tasks(["app.celery_tasks"])
