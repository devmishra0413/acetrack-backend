from groq import Groq
import fitz
import os
import re
from datetime import date, timedelta

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ---------------------------------------------------------------------------
# PDF Extractor
# ---------------------------------------------------------------------------

def extract_syllabus_from_pdf(file) -> str:
    chunks = []
    with fitz.open(stream=file.read(), filetype="pdf") as pdf:
        for page in pdf:
            page_text = page.get_text("text")
            if page_text.strip():
                chunks.append(page_text)

    raw = "\n".join(chunks)
    # 3+ newlines compress karo
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def _calculate_plan_structure(exam_date_str: str, daily_hours: int) -> dict:
    """
    Python side pe saara math karo — model ko exact numbers do.
    """
    today = date.today()

    # exam_date parse — YYYY-MM-DD expected (serializer already validates)
    exam_dt = date.fromisoformat(str(exam_date_str))

    days_left = (exam_dt - today).days

    if days_left <= 0:
        raise ValueError("Exam date already past ho gayi hai.")

    # Last 3 days / min(3, 20% of time) revision ke liye reserve
    revision_days = max(2, min(5, days_left // 5))
    study_days = days_left - revision_days
    total_study_hours = study_days * daily_hours

    # Week breakdown
    full_weeks = study_days // 7
    remaining_days = study_days % 7

    weeks = []
    cursor = today
    for w in range(full_weeks):
        start = cursor
        end = cursor + timedelta(days=6)
        weeks.append({
            "week_num": w + 1,
            "start": start.strftime("%d %b"),
            "end": end.strftime("%d %b"),
            "days": 7,
            "hours": 7 * daily_hours,
        })
        cursor = end + timedelta(days=1)

    if remaining_days > 0:
        start = cursor
        end = cursor + timedelta(days=remaining_days - 1)
        weeks.append({
            "week_num": full_weeks + 1,
            "start": start.strftime("%d %b"),
            "end": end.strftime("%d %b"),
            "days": remaining_days,
            "hours": remaining_days * daily_hours,
        })
        cursor = end + timedelta(days=1)

    # Revision block
    rev_start = cursor
    rev_end = exam_dt - timedelta(days=1)

    return {
        "today": today.strftime("%d %b %Y"),
        "exam_date": exam_dt.strftime("%d %b %Y"),
        "days_left": days_left,
        "study_days": study_days,
        "revision_days": revision_days,
        "total_study_hours": total_study_hours,
        "daily_hours": daily_hours,
        "weeks": weeks,
        "revision_start": rev_start.strftime("%d %b"),
        "revision_end": rev_end.strftime("%d %b"),
        "total_weeks": len(weeks),
    }


def _weeks_summary(weeks: list) -> str:
    lines = []
    for w in weeks:
        lines.append(
            f"  Week {w['week_num']} ({w['start']} – {w['end']}): "
            f"{w['days']} days, {w['hours']} hours available"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Roadmap generator
# ---------------------------------------------------------------------------

def generate_roadmap(syllabus_text: str, exam_name: str, exam_date: str, daily_hours: int) -> str:

    plan = _calculate_plan_structure(exam_date, int(daily_hours))
    weeks_info = _weeks_summary(plan["weeks"])

    # Edge case: bahut kam time
    if plan["days_left"] < 3:
        urgency_note = "⚠️ Bahut kam time bacha hai! Sirf most important topics cover karo."
    elif plan["days_left"] < 10:
        urgency_note = "⚡ Time tight hai — focused, high-priority topics pe dhyan do."
    else:
        urgency_note = ""

    system_prompt = """
Tu ek expert study planner hai.
Tera kaam hai: syllabus dekh kar topics ko available weeks mein distribute karna.

STRICT RULES:
- Sirf utne weeks ka plan banana jitne neeche bataye gaye hain — ek bhi zyada nahi
- Har week ka time budget already calculate ho chuka hai — usse follow karo
- Topics ko evenly distribute karo, easy topics pehle, hard topics beech mein
- Last block hamesha revision + mock tests ka hoga
- Hinglish mein likho — simple, clear, bullet points
- Koi extra weeks mat banana, koi assumption mat laga
"""

    user_prompt = f"""
Exam: {exam_name}
Exam Date: {plan['exam_date']}
Aaj ki date: {plan['today']}
Total time: {plan['days_left']} din bache hain
Roz padhta hun: {plan['daily_hours']} ghante
Total study hours available: {plan['total_study_hours']} hours
{urgency_note}

📅 EXACT WEEK STRUCTURE (sirf inhi weeks ka plan banana hai):
{weeks_info}

🔁 Revision Block: {plan['revision_start']} – {plan['revision_end']} ({plan['revision_days']} days)
   Is block mein: full revision + mock tests + weak topics

📚 Syllabus:
{syllabus_text[:6000]}

Ab EXACTLY {plan['total_weeks']} study weeks + 1 revision block ka roadmap do.
Har week mein:
- Kaunse topics cover honge (syllabus se)
- Roz ka rough time breakdown ({plan['daily_hours']} ghante ke andar)
- Week ke end mein ek quick revision

End mein 3-4 exam tips do.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2500,
        temperature=0.4,  # low — structured output chahiye
    )

    output = response.choices[0].message.content

    # Header prepend karo
    header = (
        f"🎯 {exam_name} Roadmap\n"
        f"📅 Exam: {plan['exam_date']} | "
        f"⏳ {plan['days_left']} din bache | "
        f"📖 {plan['daily_hours']} hrs/day\n"
        f"{'─' * 50}\n\n"
    )

    return header + output