from django.contrib.auth.models import AbstractUser
from django.db import models

class Student(AbstractUser):
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='student_set',
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='student_set',
        blank=True
    )

class UserProfile(models.Model):
    user       = models.OneToOneField('users.Student', on_delete=models.CASCADE, related_name='profile')
    joined_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s profile"