from groq import Groq
from django.utils import timezone
from django.db.models import Sum
from tasks.models import Task
from expenses.models import Expense
import os
import re

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ---------------------------------------------------------------------------
# Keywords when user actually wants advice
# ---------------------------------------------------------------------------
ADVICE_TRIGGERS = [
    # English
    "advice", "suggest", "suggestion", "help me", "what should i", "how should i",
    "tip", "tips", "guide", "improve", "better", "review", "analyse", "analyze",
    "feedback", "recommend", "plan", "should i", "productivity", "expenses",
    # Hindi / Hinglish
    "batao", "bata", "kya karu", "kaise karu", "kya karun", "kya lagta",
    "suggest karo", "help kar", "advice do", "kya sochte", "kya bologe",
    "kya bolega", "theek hai kya", "sahi hai kya", "review karo", "plan bana",
    "improve karna", "kaise improve", "kya problem", "kya issue",
]

# Word-boundary match to avoid false triggers (e.g. "better" inside "butterfly")
def _wants_advice(message: str) -> bool:
    lowered = message.lower()
    for trigger in ADVICE_TRIGGERS:
        pattern = r'(?<!\w)' + re.escape(trigger) + r'(?!\w)'
        if re.search(pattern, lowered):
            return True
    return False


# ---------------------------------------------------------------------------
# Context builder — only called when advice is needed
# ---------------------------------------------------------------------------
def _get_user_context(user) -> dict:
    today = timezone.localdate()
    week_ago = today - timezone.timedelta(days=7)

    tasks = Task.objects.filter(user=user, date__gte=week_ago).order_by("-date")
    expenses = Expense.objects.filter(user=user, date__gte=week_ago).order_by("-date")

    total_tasks = tasks.count()
    completed_tasks = tasks.filter(is_completed=True).count()
    score = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0
    total_expense = expenses.aggregate(total=Sum("amount"))["total"] or 0

    tasks_list = "\n".join(
        f"- {'✅' if t.is_completed else '❌'} {t.title} ({t.date})" for t in tasks
    ) or "Koi task nahi"

    expenses_list = "\n".join(
        f"- ₹{e.amount} on {e.label} ({e.date})" for e in expenses
    ) or "Koi expense nahi"

    return {
        "tasks_list": tasks_list,
        "expenses_list": expenses_list,
        "productivity_score": score,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "total_expense": float(total_expense),
    }


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------
_COMPANION_SYSTEM_PROMPT = """
Tu ek real dost hai — koi bot nahi, koi assistant nahi.

Tere saath baat karne wala tera best friend hai. Usse waise hi reply kar jaise ek
close yaar karta hai — naturally, warmly, thoda funny kabhi kabhi, kabhi serious.

Rules:
- "How can I assist you?" jaisa KABHI mat bolna
- Apne aap ko AI ya assistant KABHI mat kehna
- Agar woh bol raha hai ki uski problem hai — genuinely sun, judge mat kar
- Chhoti cheezein bol — real conversation honi chahiye, lecture nahi
- Hinglish mein baat kar (Hindi + English naturally mixed)
- Kabhi kabhi question puch taaki conversation chale
- Emojis ka thoda use kar — overdone nahi, bas natural lage
- Agar koi sad hai — pehle usse feel kara ki tu samjha, phir advice (agar maange)
"""

def _build_advice_system_prompt(ctx: dict) -> str:
    return f"""
Tu ek real best friend hai jo genuinely help karna chahta hai.

Tere saath baat karne wala tera yaar hai aur usne tujhse advice maangi hai.
Tere paas unka data hai — iske basis pe honest, caring, practical advice de.
Lecture mat de. Dost ki tarah bol.

📋 TASKS (Last 7 days):
{ctx['tasks_list']}

📊 PRODUCTIVITY:
- Total: {ctx['total_tasks']} | Done: {ctx['completed_tasks']} | Score: {ctx['productivity_score']}%

💸 EXPENSES (Last 7 days):
{ctx['expenses_list']}
- Total Spend: ₹{ctx['total_expense']}

Guidance:
- Productivity 70%+ hai toh hype up karo genuinely
- 40-70% hai toh gently push karo
- 40% se neeche hai toh honest raho magar harsh nahi
- Expenses zyada lag rahe hain toh casually flag karo, shame nahi
- Hinglish mein baat karo
- Short rakho — ek dost jaisi baat, essay nahi
"""


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------
# conversation_history: today's chat loaded from AsyncStorage on the frontend
# It should be a list of { "role": "user"/"assistant", "content": "..." } dicts
# Frontend flow:
#   1. App start  → initChatHistory()               (clears if new day)
#   2. Open chat  → getChatHistory()                (pass as conversation_history)
#   3. User sends → appendChatMessage('user', msg)
#   4. Got reply  → appendChatMessage('assistant', reply)

def get_advice(user, user_message: str, conversation_history: list) -> str:
    advice_mode = _wants_advice(user_message)

    if advice_mode:
        ctx = _get_user_context(user)
        system_prompt = _build_advice_system_prompt(ctx)
    else:
        system_prompt = _COMPANION_SYSTEM_PROMPT

    # Filter history to only valid roles (guard against corrupted storage data)
    valid_history = [
        msg for msg in conversation_history
        if isinstance(msg, dict)
        and msg.get("role") in ("user", "assistant")
        and isinstance(msg.get("content"), str)
    ]

    messages = [
        {"role": "system", "content": system_prompt},
        *valid_history,
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300 if not advice_mode else 500,
        temperature=0.85,
    )

    return response.choices[0].message.content