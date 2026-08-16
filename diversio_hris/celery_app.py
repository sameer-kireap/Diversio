import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "diversio_hris.settings")

app = Celery("diversio_hris")
app.config_from_object("django.conf:settings", namespace="CELERY")

# Enforce Redis broker and backend settings explicitly
app.conf.broker_url = os.getenv("CELERY_BROKER_URL", "redis://127.0.0.1:6379/0")
app.conf.result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://127.0.0.1:6379/0")

app.autodiscover_tasks()
