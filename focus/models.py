from django.db import models
from django.conf import settings
from tasks.models import Task

FOCUS_TYPES = [
    ('pomodoro', 'Pomodoro'),
    ('deep_work', 'Deep Work'),
    ('revision', 'Revision'),
    ('reading', 'Reading'),
    ('other', 'Other'),
]

class FocusSession(models.Model):
    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    task           = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField()
    focus_type     = models.CharField(max_length=20, choices=FOCUS_TYPES, default='other')
    started_at     = models.DateTimeField()
    ended_at       = models.DateTimeField()
    created_at     = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.focus_type} - {self.duration_minutes}min"