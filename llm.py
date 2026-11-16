import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from schema import get_schema

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SCHEMA = get_schema()

RULES = """You are a MySQL expert. Convert the business question into ONE MySQL query.
Rules:
- Return ONLY the SQL, no explanation, no markdown.
- SELECT only. Never modify data.
- Use only tables and columns from the schema below.
- Prefer the vw_ views when they already answer the question.
- For "share", "percentage", "rate" or "ratio" questions, divide by the total of the same group (e.g. Enterprise customers in a region / all customers in that region). Never filter in WHERE first and then count.
- Use SUM(condition) or COUNT(CASE WHEN ...) for the numerator, and keep all rows in the denominator.
- Add LIMIT 100 unless the query is an aggregate returning few rows.
- If the question can't be answered from the schema, return: SELECT 'UNANSWERABLE' AS error;
"""

def clean(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.replace("sql\n", "", 1).strip() if text.lower().startswith("sql\n") else text.strip()

def generate_sql(question: str, error: str = None, bad_sql: str = None) -> str:
    prompt = f"{RULES}\nSCHEMA:\n{SCHEMA}\n\nQuestion: {question}"
    if error:
        prompt += f"\n\nYour previous SQL failed.\nSQL: {bad_sql}\nError: {error}\nReturn a corrected query."
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0),
    )
    return clean(resp.text)

if __name__ == "__main__":
    print(generate_sql("How many customers do we have?"))