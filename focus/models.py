from django.db import models
from django.conf import settings
from tasks.models import Task

class FocusSession(models.Model):
    user             = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task             = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)
    date             = models.DateField(default='2026-01-01')
    created_at       = models.DateTimeField(auto_now_add=True)

    def duration_minutes(self):
        return round(self.duration_seconds / 60, 1)

    def __str__(self):
        return f"{self.user.username} - {self.duration_seconds}s on {self.date}"