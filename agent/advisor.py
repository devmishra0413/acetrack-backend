from groq import Groq
from django.conf import settings
from tasks.models import Task
from expenses.models import Expense
from django.utils import timezone
from django.db.models import Sum
import os

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

def get_user_context(user):
    today = timezone.localdate()

    # Last 7 days ki tasks fetch karo
    tasks = Task.objects.filter(
        user=user,
        date__gte=today - timezone.timedelta(days=7)
    ).order_by('-date')

    # Last 7 days ke expenses
    expenses = Expense.objects.filter(
        user=user,
        date__gte=today - timezone.timedelta(days=7)
    ).order_by('-date')

    # Productivity score calculate karo
    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    score = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0

    # Total expense
    total_expense = expenses.aggregate(
        total=Sum('amount')
    )['total'] or 0

    # Tasks list banao
    tasks_list = "\n".join([
        f"- {'✅' if t.is_completed else '❌'} {t.title} ({t.date})"
        for t in tasks
    ])

    # Expenses list banao
    expenses_list = "\n".join([
        f"- ₹{e.amount} on {e.label} ({e.date})"
        for e in expenses
    ])

    return {
        'tasks_list': tasks_list or "Koi task nahi",
        'expenses_list': expenses_list or "Koi expense nahi",
        'productivity_score': score,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'total_expense': float(total_expense),
    }


def get_advice(user, user_message, conversation_history):
    # User ka context lo
    context = get_user_context(user)

    # System prompt banao
    system_prompt = f"""
Tu ek helpful student advisor hai jo Hinglish mein baat karta hai.
Seedha aur practical advice deta hai.

Abhi is student ka data hai:

📋 TASKS (Last 7 days):
{context['tasks_list']}

📊 PRODUCTIVITY:
- Total Tasks: {context['total_tasks']}
- Completed: {context['completed_tasks']}
- Score: {context['productivity_score']}%

💸 EXPENSES (Last 7 days):
{context['expenses_list']}
- Total Spend: ₹{context['total_expense']}

Is data ke basis pe student ki help kar.
- Agar productivity low hai toh motivate karo
- Agar expenses zyada hain toh suggest karo
- Practical aur short advice do
- Hinglish mein baat karo (Hindi + English mix)
- Friendly tone rakho
"""

    # Conversation history ke saath message bhejo
    messages = [
        {"role": "system", "content": system_prompt},
        *conversation_history,
        {"role": "user", "content": user_message}
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1000,
        temperature=0.7,
    )

    return response.choices[0].message.content