from django.contrib.auth.models import AbstractUser
from django.db import models

class Student(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='student_set',   # ← clash fix
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='student_set',   # ← clash fix
        blank=True
    )