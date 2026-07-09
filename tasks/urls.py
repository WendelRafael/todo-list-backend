"""Rotas de tarefas via router do DRF: /api/tasks/ e /api/tasks/{id}/."""

from rest_framework.routers import DefaultRouter

from .views import TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
