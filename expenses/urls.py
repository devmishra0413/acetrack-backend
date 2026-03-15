from django.urls import path
from .views import ExpenseListCreateView, ExpenseDeleteView

urlpatterns = [
    path('', ExpenseListCreateView.as_view()),        # GET, POST
    path('<int:pk>/', ExpenseDeleteView.as_view()),   # DELETE
]