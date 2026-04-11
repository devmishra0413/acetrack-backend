from django.db import models
from django.conf import settings

class Task(models.Model):
    PRIORITY_CHOICES = [(1, 'Low'), (2, 'Medium'), (3, 'High')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2)  # ✅ add this
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(blank=True, null=True)
    end_time = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.title}"