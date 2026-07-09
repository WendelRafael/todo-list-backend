import django_filters

from .models import Task


class TaskFilter(django_filters.FilterSet):
    """Filtros de GET /api/tasks/ conforme a seção 6 do PLANEJAMENTO.md.

    ?due_date=2026-07-10      → tarefas que vencem NESSE dia (compara só a data)
    ?due_date__lte=2026-07-10 → tarefas que vencem até essa data
    ?due_date__gte=2026-07-10 → tarefas que vencem a partir dessa data
    ?priority=alta            → filtra por prioridade
    ?completed=false          → filtra por status
    """

    due_date = django_filters.DateFilter(field_name="due_date", lookup_expr="date")
    due_date__lte = django_filters.DateFilter(
        field_name="due_date", lookup_expr="date__lte"
    )
    due_date__gte = django_filters.DateFilter(
        field_name="due_date", lookup_expr="date__gte"
    )

    class Meta:
        model = Task
        fields = ["priority", "completed"]
