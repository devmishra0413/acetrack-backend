from rest_framework import serializers
from .models import FocusSession

class FocusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusSession
        fields = ['id', 'task', 'duration_minutes', 'focus_type',
                  'started_at', 'ended_at', 'created_at']
        read_only_fields = ['id', 'created_at']