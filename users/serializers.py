from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    joined_date   = serializers.SerializerMethodField()
    total_tasks   = serializers.SerializerMethodField()
    focus_seconds = serializers.SerializerMethodField()
    streak_days   = serializers.SerializerMethodField()
    achievements  = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = ['id', 'username', 'email', 'joined_date',
                  'total_tasks', 'focus_seconds', 'streak_days', 'achievements']

    def get_joined_date(self, obj):
        return obj.date_joined.date()

    def get_total_tasks(self, obj):
        from tasks.models import Task
        return Task.objects.filter(user=obj, is_completed=True).count()

    def get_focus_seconds(self, obj):
        try:
            from focus.models import FocusSession
            from django.db.models import Sum
            result = FocusSession.objects.filter(user=obj).aggregate(total=Sum('duration_seconds'))
            return result['total'] or 0
        except Exception:
            return 0

    def get_streak_days(self, obj):
        from tasks.models import Task
        streak = 0
        day = timezone.localdate()
        while True:
            has_task = Task.objects.filter(user=obj, date=day, is_completed=True).exists()
            if has_task:
                streak += 1
                day -= timedelta(days=1)
            else:
                break
        return streak

    def get_achievements(self, obj):
        from tasks.models import Task
        unlocked = []

        total_tasks   = self.get_total_tasks(obj)
        focus_seconds = self.get_focus_seconds(obj)
        streak_days   = self.get_streak_days(obj)

        # 🔥 7-Day Streak
        if streak_days >= 7:
            unlocked.append('streak_7')

        # ✅ 50 Tasks Done
        if total_tasks >= 50:
            unlocked.append('tasks_50')

        # ⏱️ 10 Hours Focused
        if focus_seconds >= 36000:
            unlocked.append('focus_10h')

        # 🌙 Night Owl — task completed after 10 PM
        if Task.objects.filter(user=obj, is_completed=True, end_time__hour__gte=22).exists():
            unlocked.append('night_owl')

        # 🌅 Early Bird — task completed before 7 AM
        if Task.objects.filter(user=obj, is_completed=True, end_time__hour__lt=7).exists():
            unlocked.append('early_bird')

        return unlocked