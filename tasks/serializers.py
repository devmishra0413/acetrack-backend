from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'is_completed', 'priority', 'date', 'start_time', 'end_time', 'created_at']
        read_only_fields = ['id', 'created_at']