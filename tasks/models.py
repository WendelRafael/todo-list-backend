from django.contrib.auth.models import User
from django.db import models


class Task(models.Model):
    """Tarefa pessoal, sempre vinculada a um usuário (isolamento de dados)."""

    class Priority(models.TextChoices):
        BAIXA = "baixa", "Baixa"
        MEDIA = "media", "Média"
        ALTA = "alta", "Alta"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name="usuário",
    )
    title = models.CharField("título", max_length=200)
    description = models.TextField("descrição", blank=True)
    completed = models.BooleanField("concluída", default=False)
    due_date = models.DateTimeField("vencimento")
    priority = models.CharField(
        "prioridade",
        max_length=5,
        choices=Priority.choices,
        default=Priority.MEDIA,
    )
    # Lixeira (soft delete): quando preenchido, a tarefa está na lixeira e
    # some das listagens normais até ser restaurada ou excluída de vez.
    deleted_at = models.DateTimeField("excluída em", null=True, blank=True)
    created_at = models.DateTimeField("criada em", auto_now_add=True)
    updated_at = models.DateTimeField("atualizada em", auto_now=True)

    class Meta:
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title
