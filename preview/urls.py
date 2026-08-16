from django.urls import path
from .views import UploadView, SubmitTaskView, ProcessingView, TaskStatusView, ResultsView

urlpatterns = [
    path("", UploadView.as_view(), name="upload"),
    path("submit/", SubmitTaskView.as_view(), name="submit_task"),
    path("processing/<str:task_id>/", ProcessingView.as_view(), name="processing"),
    path("task-status/<str:task_id>/", TaskStatusView.as_view(), name="task_status"),
    path("results/<str:task_id>/", ResultsView.as_view(), name="results"),
]
