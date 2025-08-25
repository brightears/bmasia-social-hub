"""
Celery configuration for BMA Social background workers.
Handles message processing, monitoring, and campaigns.
"""

import os
from celery import Celery
from kombu import Queue

from app.config import settings

# Create Celery instance
celery_app = Celery(
    "bma_social",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.message_processor",
        "app.workers.tasks.monitoring",
        "app.workers.tasks.campaigns",
    ],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit
    task_acks_late=True,
    
    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,
    
    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("messages", routing_key="messages.#", priority=10),
        Queue("monitoring", routing_key="monitoring.#", priority=5),
        Queue("campaigns", routing_key="campaigns.#", priority=3),
        Queue("default", routing_key="default.#", priority=1),
    ),
    
    # Route tasks to appropriate queues
    task_routes={
        "app.workers.tasks.message_processor.*": {"queue": "messages"},
        "app.workers.tasks.monitoring.*": {"queue": "monitoring"},
        "app.workers.tasks.campaigns.*": {"queue": "campaigns"},
    },
    
    # Beat schedule for periodic tasks
    beat_schedule={
        "monitor-zones": {
            "task": "app.workers.tasks.monitoring.check_all_zones",
            "schedule": 300.0,  # Every 5 minutes
        },
        "process-campaigns": {
            "task": "app.workers.tasks.campaigns.process_scheduled_campaigns",
            "schedule": 60.0,  # Every minute
        },
        "cleanup-old-data": {
            "task": "app.workers.tasks.monitoring.cleanup_old_logs",
            "schedule": 86400.0,  # Daily
        },
    },
)

# Initialize on import
if __name__ == "__main__":
    celery_app.start()