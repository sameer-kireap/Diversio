import base64
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View

from .tasks import process_hris_csv_task

class UploadView(View):
    def get(self, request):
        return render(request, "preview/upload.html")

class SubmitTaskView(View):
    def post(self, request):
        if "csv_file" not in request.FILES:
            return JsonResponse({"success": False, "error": "No file uploaded. Please select an HRIS CSV file."}, status=400)

        uploaded_file = request.FILES["csv_file"]
        if not uploaded_file.name.endswith(".csv"):
            return JsonResponse({"success": False, "error": "Invalid file format. Please upload a .csv file."}, status=400)

        try:
            file_bytes = uploaded_file.read()
            file_b64 = base64.b64encode(file_bytes).decode("utf-8")
        except Exception as exc:
            return JsonResponse({"success": False, "error": f"Failed to read file: {str(exc)}"}, status=400)

        # Dispatch task to Celery with fallback to in-memory eager execution
        try:
            async_result = process_hris_csv_task.delay(file_b64)
            task_id = async_result.id

            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", True):
                return JsonResponse({
                    "success": True,
                    "task_id": task_id,
                    "redirect_url": f"/results/{task_id}/",
                    "state": "SUCCESS",
                })

            return JsonResponse({
                "success": True,
                "task_id": task_id,
                "redirect_url": f"/processing/{task_id}/",
                "state": "PENDING",
            })
        except Exception:
            # Fall back to synchronous eager task execution if Redis server is unavailable
            eager_result = process_hris_csv_task.apply(args=[file_b64])
            task_id = eager_result.id
            return JsonResponse({
                "success": True,
                "task_id": task_id,
                "redirect_url": f"/results/{task_id}/",
                "state": "SUCCESS",
            })

class ProcessingView(View):
    def get(self, request, task_id):
        return render(request, "preview/processing.html", {"task_id": task_id})

class TaskStatusView(View):
    def get(self, request, task_id):
        cached_result = cache.get(f"hris_result_{task_id}")
        if cached_result is not None:
            return JsonResponse({"state": "SUCCESS", "result": cached_result})

        from celery.result import AsyncResult
        res = AsyncResult(task_id)
        if res.ready():
            val = res.get()
            return JsonResponse({"state": "SUCCESS", "result": val})

        return JsonResponse({"state": res.state})

class ResultsView(View):
    def get(self, request, task_id):
        cached_result = cache.get(f"hris_result_{task_id}")

        if cached_result is None:
            from celery.result import AsyncResult
            res = AsyncResult(task_id)
            if res.ready():
                cached_result = res.get()

        if cached_result is None:
            return render(
                request,
                "preview/processing.html",
                {"task_id": task_id, "error": "Task results are still processing or expired. Please refresh."},
            )

        if not cached_result.get("success", False):
            return render(request, "preview/upload.html", {"error": cached_result.get("error_message")})

        return render(request, "preview/results.html", {"data": cached_result, "task_id": task_id})
