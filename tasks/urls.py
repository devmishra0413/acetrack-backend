from django.urls import path
from .views import TaskListCreateView, TaskUpdateDeleteView

urlpatterns = [
    path('', TaskListCreateView.as_view()),          # GET, POST
    path('<int:pk>/', TaskUpdateDeleteView.as_view()), # PATCH, DELETE
]