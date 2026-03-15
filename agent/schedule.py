from groq import Groq
import os

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

def generate_schedule(activities, goal, wake_time, sleep_time):
    """Daily schedule generate karo"""

    system_prompt = """
Tu ek expert life coach aur time management specialist hai.
Tu students ke liye optimized daily schedule banata hai.
Tu Hinglish mein likhta hai — friendly aur practical.
"""

    user_prompt = f"""
Meri daily activities:
{activities}

Mera main goal: {goal}

Main sota hun: {sleep_time} baje
Main uthta hun: {wake_time} baje

Mujhe ek optimized daily schedule do jisme:
1. ⏰ Har activity ka exact time slot ho (e.g. 6:00 AM - 6:30 AM)
2. 📚 Study time properly allocated ho goal ke according
3. 🏃 Exercise/breaks bhi include ho
4. 😴 Proper sleep schedule ho
5. 📵 Phone/social media ka limited time ho
6. 🍽️ Meals ka time bhi include karo
7. 💡 End mein 3-4 important tips do

Table format mein likho:
Time | Activity | Duration | Priority

Aur end mein analysis do ki abhi kya galat ho raha hai aur kya improve karna chahiye.
Simple Hinglish mein likho.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=2000,
        temperature=0.6,
    )

    return response.choices[0].message.content