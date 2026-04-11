from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),

    # JWT
    path('api/auth/login/', TokenObtainPairView.as_view()),
    path('api/auth/refresh/', TokenRefreshView.as_view()),

    # Apps
    path('api/auth/', include('users.urls')),
    path('api/tasks/', include('tasks.urls')),
    path('api/expenses/', include('expenses.urls')),
    path('api/dashboard/', include('dashboard.urls')), 
    path('api/agent/', include('agent.urls')),
    path('api/', include('focus.urls')),
    path('api/', include('leaderboard.urls')),
]