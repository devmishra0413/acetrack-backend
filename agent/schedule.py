from groq import Groq
from datetime import datetime, timedelta
import os
import json
import re

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------

def _parse_time(time_str: str) -> datetime:
    """
    '6:00 AM', '06:00', '6:30 AM' — sab formats handle karo.
    Returns a datetime on a fixed base date (date doesn't matter, only time).
    """
    time_str = time_str.strip().upper()
    for fmt in ("%I:%M %p", "%I %p", "%H:%M", "%I:%M%p"):
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Time format samajh nahi aaya: '{time_str}'")


def _fmt(dt: datetime) -> str:
    """datetime → '6:00 AM'"""
    return dt.strftime("%-I:%M %p")


def _build_slots(activities_json: list, wake_dt: datetime, sleep_dt: datetime) -> list:
    """
    Model se aaye activities (duration only) ko le kar
    Python side pe exact start/end times assign karo.
    Overnight sleep handle hota hai (e.g. wake 6 AM, sleep 11 PM).
    """
    # Total available minutes
    if sleep_dt <= wake_dt:
        sleep_dt += timedelta(days=1)  # overnight

    total_minutes = int((sleep_dt - wake_dt).total_seconds() / 60)

    # Scale durations agar sum > total available time
    raw_total = sum(a.get("duration_minutes", 30) for a in activities_json)
    scale = total_minutes / raw_total if raw_total > total_minutes else 1.0

    slots = []
    cursor = wake_dt
    for item in activities_json:
        duration = max(5, round(item.get("duration_minutes", 30) * scale / 5) * 5)  # round to 5 min
        end = cursor + timedelta(minutes=duration)
        slots.append({
            "time": f"{_fmt(cursor)} – {_fmt(end)}",
            "activity": item.get("activity", ""),
            "duration": f"{duration} min",
            "priority": item.get("priority", "Medium"),
            "emoji": item.get("emoji", "📌"),
        })
        cursor = end

    return slots


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_schedule(activities: str, goal: str, wake_time: str, sleep_time: str) -> str:

    wake_dt = _parse_time(wake_time)
    sleep_dt = _parse_time(sleep_time)
    if sleep_dt <= wake_dt:
        sleep_dt += timedelta(days=1)
    available_minutes = int((sleep_dt - wake_dt).total_seconds() / 60)

    # Step 1 — Model se sirf activities + durations lo (no time calculation)
    system_prompt = """
Tu ek expert student life coach hai.
Tera kaam hai: user ki activities aur goal dekhkar ek optimized daily routine plan karna.

IMPORTANT — Tu SIRF valid JSON return karega, kuch aur nahi.
Koi explanation nahi, koi markdown nahi, sirf raw JSON.

JSON format:
{
  "activities": [
    {
      "activity": "Morning walk",
      "duration_minutes": 30,
      "priority": "High",
      "emoji": "🏃"
    }
  ],
  "tips": ["tip 1", "tip 2", "tip 3"],
  "analysis": "2-3 lines mein kya galat ho raha hai aur kya improve karna chahiye"
}

Rules:
- Activities wake time se sleep time tak cover karni hain
- Total duration_minutes ka sum exactly {available_minutes} hona chahiye
- Meals (breakfast, lunch, dinner), breaks, aur sleep transition include karo
- Goal ke hisaab se study/work time properly allocate karo
- Priority: High / Medium / Low
- Realistic emojis use karo
- Tips 3-4 short, actionable Hinglish mein
"""

    user_prompt = f"""
User ki details:
- Wake time: {wake_time}
- Sleep time: {sleep_time}
- Available time: {available_minutes} minutes
- Goal: {goal}
- Current activities: {activities}

Optimized schedule banao. Total duration_minutes = {available_minutes} exactly.
Sirf JSON return karo.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt.format(available_minutes=available_minutes)},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2000,
        temperature=0.4,   # low temp — structured output chahiye
    )

    raw = response.choices[0].message.content.strip()

    # Step 2 — JSON parse karo (markdown fences strip karo agar ho)
    raw = re.sub(r"```(?:json)?", "", raw).strip("`").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: raw response return karo agar JSON toot gaya
        return raw

    activities_json = data.get("activities", [])
    tips = data.get("tips", [])
    analysis = data.get("analysis", "")

    # Step 3 — Python side pe time slots calculate karo
    slots = _build_slots(activities_json, wake_dt, sleep_dt)

    # Step 4 — Human-readable output format karo
    return _format_output(slots, tips, analysis, goal, wake_time, sleep_time)


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------

def _format_output(slots: list, tips: list, analysis: str, goal: str, wake: str, sleep: str) -> str:
    lines = []

    lines.append(f"🗓️ **Tera Optimized Daily Schedule**")
    lines.append(f"🎯 Goal: {goal}")
    lines.append(f"⏰ {wake} se {sleep} tak\n")

    lines.append("─" * 52)
    lines.append(f"{'TIME':<22} {'ACTIVITY':<22} {'DUR':<10} {'PRIORITY'}")
    lines.append("─" * 52)

    for s in slots:
        lines.append(
            f"{s['emoji']} {s['time']:<20} {s['activity']:<22} {s['duration']:<10} {s['priority']}"
        )

    lines.append("─" * 52)

    if analysis:
        lines.append(f"\n📊 **Analysis**")
        lines.append(analysis)

    if tips:
        lines.append(f"\n💡 **Tips**")
        for i, tip in enumerate(tips, 1):
            lines.append(f"{i}. {tip}")

    return "\n".join(lines)