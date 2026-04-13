from django.urls import path
from .views import RegisterView, ProfileView
from focus.views import UserStatsView

urlpatterns = [
    path('register/',        RegisterView.as_view()),
    path('profile/',         ProfileView.as_view()),
    path('profile/stats/',   UserStatsView.as_view()),
]