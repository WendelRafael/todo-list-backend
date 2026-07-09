from rest_framework import serializers

from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    """Serializa a tarefa sem expor o campo user como gravável.

    O dono é sempre definido pela view (request.user); o cliente não consegue
    criar ou mover tarefas para outro usuário.
    """

    due_date = serializers.DateTimeField(
        error_messages={
            "required": "A tarefa precisa de uma data de vencimento (due_date).",
            "null": "A tarefa precisa de uma data de vencimento (due_date).",
            "invalid": "Data de vencimento inválida. Use o formato ISO 8601, "
            "ex.: 2026-07-10T18:00:00Z.",
        },
    )

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "completed",
            "due_date",
            "priority",
            "deleted_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["deleted_at", "created_at", "updated_at"]
