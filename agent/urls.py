from django.urls import path
from .views import AdvisorView, SummarizerView, RoadmapView, ScheduleView

urlpatterns = [
    path('advice/', AdvisorView.as_view()),
    path('summarize/', SummarizerView.as_view()),
    path('roadmap/', RoadmapView.as_view()),
    path('schedule/', ScheduleView.as_view()),
]