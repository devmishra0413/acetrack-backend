from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from tasks.models import Task
from expenses.models import Expense
from django.db.models import Sum, Count, Case, When, IntegerField


class DashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.localdate()
        last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]

        chart_data = []

        for day in last_7_days:
            # Tasks data
            tasks = Task.objects.filter(user=user, date=day)
            total_tasks = tasks.count()
            completed_tasks = tasks.filter(is_completed=True).count()

            # Productivity score
            if total_tasks > 0:
                score = round((completed_tasks / total_tasks) * 100, 1)
            else:
                score = 0

            # Expenses data
            expense_total = Expense.objects.filter(
                user=user, date=day
            ).aggregate(total=Sum('amount'))['total'] or 0

            chart_data.append({
                'date': day.strftime('%d %b'),   # e.g. "12 Mar"
                'productivity_score': score,
                'total_expense': float(expense_total),
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
            })

        # Today's quick stats
        today_tasks = Task.objects.filter(user=user, date=today)
        today_expenses = Expense.objects.filter(user=user, date=today)

        summary = {
            'chart_data': chart_data,
            'today': {
                'total_tasks': today_tasks.count(),
                'completed_tasks': today_tasks.filter(is_completed=True).count(),
                'productivity_score': round(
                    (today_tasks.filter(is_completed=True).count() /
                     today_tasks.count() * 100), 1
                ) if today_tasks.count() > 0 else 0,
                'total_expense': float(
                    today_expenses.aggregate(
                        total=Sum('amount'))['total'] or 0
                ),
            }
        }

        return Response(summary)