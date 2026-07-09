from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "priority", "due_date", "completed", "deleted_at")
    list_filter = ("completed", "priority", "deleted_at")
    search_fields = ("title", "description")
    ordering = ("-created_at",)
