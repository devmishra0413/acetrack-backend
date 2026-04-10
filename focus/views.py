from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta

from .models import FocusSession
from .serializers import FocusSessionSerializer
from tasks.models import Task
from django.contrib.auth import get_user_model

User = get_user_model()


class FocusSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FocusSessionSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def compute_weekly_score(user, week_start, week_end):
    # Tasks score (50% weightage)
    tasks = Task.objects.filter(user=user, date__range=[week_start, week_end])
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    task_score = (completed_tasks / total_tasks * 50) if total_tasks > 0 else 0

    # Focus score (50% weightage)
    focus_result = FocusSession.objects.filter(
        user=user,
        started_at__date__range=[week_start, week_end]
    ).aggregate(total=Sum('duration_minutes'))
    total_focus = focus_result['total'] or 0
    focus_score = min(total_focus / 10, 50)  # cap at 50

    return round(task_score + focus_score, 1), completed_tasks, total_tasks, total_focus


class LeaderboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = today

        users = User.objects.all()
        leaderboard = []

        for user in users:
            score, completed, total, focus_mins = compute_weekly_score(user, week_start, week_end)
            leaderboard.append({
                'username': user.username,
                'score': score,
                'completed_tasks': completed,
                'total_tasks': total,
                'focus_minutes': focus_mins,
            })

        leaderboard.sort(key=lambda x: x['score'], reverse=True)
        top10 = leaderboard[:10]

        # Current user ki rank
        all_sorted = sorted(leaderboard, key=lambda x: x['score'], reverse=True)
        my_rank = next((i+1 for i, u in enumerate(all_sorted)
                        if u['username'] == request.user.username), None)

        return Response({
            'week_start': week_start,
            'week_end': week_end,
            'my_rank': my_rank,
            'leaderboard': top10,
        })


class UserStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        week_start = today - timedelta(days=today.weekday())

        # All time stats
        all_tasks = Task.objects.filter(user=user)
        all_focus = FocusSession.objects.filter(user=user)
        total_focus_mins = all_focus.aggregate(t=Sum('duration_minutes'))['t'] or 0

        # Weekly stats
        weekly_score, completed_w, total_w, focus_w = compute_weekly_score(
            user, week_start, today)

        # Achievements
        achievements = []
        if all_tasks.filter(is_completed=True).count() >= 10:
            achievements.append({'badge': '🎯', 'title': 'Task Crusher', 'desc': '10 tasks complete kiye'})
        if total_focus_mins >= 120:
            achievements.append({'badge': '🔥', 'title': 'Focus Beast', 'desc': '2+ ghante focus kiya'})
        if total_focus_mins >= 600:
            achievements.append({'badge': '💎', 'title': 'Deep Worker', 'desc': '10+ ghante focus total'})
        if all_tasks.filter(is_completed=True).count() >= 50:
            achievements.append({'badge': '🏆', 'title': 'Legend', 'desc': '50 tasks complete kiye'})

        return Response({
            'username': user.username,
            'email': user.email,
            'all_time': {
                'total_tasks': all_tasks.count(),
                'completed_tasks': all_tasks.filter(is_completed=True).count(),
                'total_focus_minutes': total_focus_mins,
                'total_sessions': all_focus.count(),
            },
            'this_week': {
                'score': weekly_score,
                'completed_tasks': completed_w,
                'total_tasks': total_w,
                'focus_minutes': focus_w,
            },
            'achievements': achievements,
        })