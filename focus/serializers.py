from rest_framework import serializers
from .models import FocusSession

class FocusSessionSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = FocusSession
        fields = ['id', 'task', 'task_id', 'duration_seconds', 'date', 'created_at']
        read_only_fields = ['id', 'created_at', 'task']