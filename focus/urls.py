from django.urls import path
from .views import FocusSessionView, LeaderboardView, UserStatsView

urlpatterns = [
    path('focus/',          FocusSessionView.as_view()),
    path('leaderboard/',    LeaderboardView.as_view()),
    path('profile/stats/',  UserStatsView.as_view()),
]