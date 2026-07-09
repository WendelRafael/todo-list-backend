from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .filters import TaskFilter
from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(viewsets.ModelViewSet):
    """CRUD de tarefas do usuário autenticado, com busca, filtros e lixeira.

    Isolamento de dados: o queryset parte sempre de request.user, então
    acessar tarefa de outro usuário resulta em 404 — nem revela que existe.
    """

    serializer_class = TaskSerializer
    filterset_class = TaskFilter
    search_fields = ["title"]
    ordering_fields = ["due_date", "priority", "created_at", "title"]

    def get_queryset(self):
        base = Task.objects.filter(user=self.request.user)
        # Rotas da lixeira enxergam SÓ o que foi excluído; as demais, só o
        # que está ativo — restaurar/excluir de vez exige item já na lixeira.
        if self.action in ("trash", "restore", "permanent"):
            return base.filter(deleted_at__isnull=False)
        return base.filter(deleted_at__isnull=True)

    def perform_create(self, serializer):
        # O dono nunca vem do cliente — é sempre o usuário autenticado
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        # Soft delete: DELETE move para a lixeira em vez de apagar
        instance.deleted_at = timezone.now()
        instance.save(update_fields=["deleted_at", "updated_at"])

    @action(detail=False, methods=["get"])
    def trash(self, request):
        """GET /api/tasks/trash/ — lista as tarefas na lixeira do usuário."""
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """POST /api/tasks/{id}/restore/ — restaura uma tarefa da lixeira."""
        task = self.get_object()
        task.deleted_at = None
        task.save(update_fields=["deleted_at", "updated_at"])
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=["delete"])
    def permanent(self, request, pk=None):
        """DELETE /api/tasks/{id}/permanent/ — exclui definitivamente
        (404 se a tarefa não estiver na lixeira)."""
        task = self.get_object()
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
