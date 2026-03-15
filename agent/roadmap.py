from groq import Groq
import fitz  # pymupdf
import os

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

def extract_syllabus_from_pdf(file):
    """PDF se syllabus extract karo"""
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    pdf.close()
    return text.strip()

def generate_roadmap(syllabus_text, exam_name, exam_date, daily_hours):
    """Groq se roadmap generate karo"""

    system_prompt = """
Tu ek expert study planner hai jo students ke liye roadmap banata hai.
Tu Hinglish mein likhta hai — simple aur clear.
Tera kaam hai ek practical, week-wise study plan banana.
"""

    user_prompt = f"""
Mera exam hai: {exam_name}
Exam date: {exam_date}
Roz study kar sakta hun: {daily_hours} ghante

Syllabus:
{syllabus_text[:6000]}

Mujhe ek detailed roadmap do jisme:
1. 📅 Week-wise plan ho (Week 1, Week 2...)
2. 📚 Har week mein kaunse topics cover karne hain
3. ⏰ Har din ka time breakdown
4. 📝 Revision schedule bhi include karo
5. 💡 Important tips bhi do exam ke liye
6. 🎯 Last week mein sirf revision aur mock tests

Simple Hinglish mein likho — bullet points use karo.
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