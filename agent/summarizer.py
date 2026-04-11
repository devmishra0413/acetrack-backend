from groq import Groq
import fitz  # pymupdf
import os
import re

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def extract_text_from_pdf(file) -> str:
    """
    PDF se clean text extract karo.
    - Page-wise extract karta hai
    - Extra whitespace / repeated newlines clean karta hai
    - Scanned/image-only PDFs ke liye empty string return karta hai
    """
    chunks = []
    pdf_bytes = file.read()

    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page in pdf:
            # "text" mode better ordering deta hai "blocks" se compared to default
            page_text = page.get_text("text")
            if page_text.strip():
                chunks.append(page_text)

    raw = "\n".join(chunks)
    return _clean_text(raw)


def extract_text_from_txt(file) -> str:
    raw = file.read().decode("utf-8")
    return _clean_text(raw)


def _clean_text(text: str) -> str:
    """
    3+ newlines ko 2 mein compress karo.
    Leading/trailing spaces each line se hatao.
    """
    # Har line ke start/end ke spaces hatao
    lines = [line.strip() for line in text.splitlines()]
    cleaned = "\n".join(lines)
    # 3+ blank lines → 2
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Summarizer
# ---------------------------------------------------------------------------

def summarize_content(text: str) -> str:
    """
    Text ko Hinglish mein summarize karo — natural, human-like tone.
    PDF aur direct text dono ke liye same function.
    """

    # 12000 chars — enough for ~2500-3000 words, Groq token safe
    content_slice = text[:12_000]

    system_prompt = """
Tu ek padha-likha dost hai jo kisi bhi document ya content ko padhke
simple, natural language mein explain karta hai.

Tera kaam hai:
- Content ko genuinely samajhna aur apne words mein likhna
- Aise likhna jaise kisi yaar ko WhatsApp pe properly explain kar rahe ho —
  na zyada formal, na zyada casual
- Andar ki actual information summarize karni hai, 
  yeh nahi batana ki "yeh document kis baare mein hai"
- Bullet points use karo key points ke liye, but har point mein 
  proper context hona chahiye — sirf heading jaisi lines nahi
- 3-4 sections mein divide karo agar content alag topics cover karta hai
- 300-400 words maximum

Yeh BILKUL mat karna:
- "Yeh document/PDF/text ... ke baare mein hai" — yeh avoid karo
- Generic filler lines jaise "Yeh ek bahut important topic hai"
- Over-formal language jaise "Iss lekh mein varnan kiya gaya hai"
- English-only ya pure Hindi — Hinglish natural lagti hai
"""

    user_prompt = f"""Neeche diya content padho aur summarize karo.
Seedha content ki baat karo — document ke baare mein mat batana, 
document ke andar ki cheezein batao.

---
{content_slice}
---
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.6,   # 0.5 se thoda upar — natural lagta hai, hallucinate nahi karta
    )

    return response.choices[0].message.content