from groq import Groq
import fitz  # pymupdf
import os

client = Groq(api_key=os.environ.get('GROQ_API_KEY'))

def extract_text_from_pdf(file):
    """PDF se text extract karo"""
    text = ""
    pdf = fitz.open(stream=file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    pdf.close()
    return text.strip()

def extract_text_from_txt(file):
    """Text file se content nikalo"""
    return file.read().decode('utf-8').strip()

def summarize_content(text, language="hinglish"):
    """Groq se summary banao"""

    system_prompt = """
Tu ek helpful summarizer hai.
Tu content ko simple Hinglish mein summarize karta hai.
- Simple words use kar
- Bullet points mein important points likho
- Maximum 300-400 words mein rakho
- Headings use karo sections ke liye
- Easy language use karo jaise dost baat kar raha ho
"""

    user_prompt = f"""
Neeche diya gaya content summarize karo simple Hinglish mein:

{text[:8000]}  
"""
# 8000 chars tak limit — Groq token limit ke liye

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1000,
        temperature=0.5,
    )

    return response.choices[0].message.content