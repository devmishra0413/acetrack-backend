from rest_framework import serializers
from .models import FocusSession

class FocusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FocusSession
        fields = ['id', 'task', 'duration_seconds', 'date', 'created_at']
        read_only_fields = ['id', 'created_at']