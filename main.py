from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
import mysql.connector
import ollama
import os
import re

load_dotenv()

app = FastAPI(title="Student Scholarship SQL Generator")
templates = Jinja2Templates(directory="templates")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "scholarship_db")
}

MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")

ollama_client = ollama.Client(host=OLLAMA_URL)


class QuestionRequest(BaseModel):
    question: str


SCHEMA = """
DATABASE: scholarship_db

TABLE students:
student_id, name, course, marks, family_income,
scholarship_amount, scholarship_status

TABLE scholarships:
scholarship_id, student_id, scholarship_name,
provider, scholarship_amount

RELATIONSHIP:
students.student_id = scholarships.student_id
"""


def generate_sql(question):
    prompt = f"""
You are an expert MySQL SQL generator.

SCHEMA:
{SCHEMA}

RULES:
1. Generate only one valid MySQL SELECT query.
2. Use only tables and columns in the schema.
3. Never use a column from the wrong table.
4. Never generate INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, GRANT or REVOKE.
5. Use WHERE, GROUP BY, HAVING, ORDER BY and LIMIT when required.
6. Allowed functions: COUNT(), AVG(), SUM(), MAX(), MIN().
7. Use JOIN when information from both tables is needed.
8. Join using students.student_id = scholarships.student_id.
9. Use INNER JOIN for matching records.
10. Use LEFT JOIN when all students are required.
11. scholarship_status exists only in students.
12. Never use scholarships.scholarship_status.
13. If requested information does not exist, return:
ERROR: Information not available in the database.
14. If question is unrelated, return:
ERROR: Question does not match the database.
15. Return only SQL or ERROR.

EXAMPLES:

Show all students:
SELECT * FROM students;

Show all scholarships:
SELECT * FROM scholarships;

Show students with marks above 80:
SELECT * FROM students WHERE marks > 80;

Show approved students:
SELECT * FROM students
WHERE scholarship_status = 'Approved';

Show students by course:
SELECT course, COUNT(*) AS total_students
FROM students
GROUP BY course;

Show courses having more than one student:
SELECT course, COUNT(*) AS total_students
FROM students
GROUP BY course
HAVING COUNT(*) > 1;

Show students ordered by marks:
SELECT * FROM students
ORDER BY marks DESC;

Show top 3 students:
SELECT * FROM students
ORDER BY marks DESC
LIMIT 3;

Show average marks:
SELECT AVG(marks) AS average_marks
FROM students;

Show highest scholarship:
SELECT MAX(scholarship_amount) AS highest_scholarship
FROM students;

Show students and scholarships:
SELECT students.name, students.course,
scholarships.scholarship_name,
scholarships.provider,
scholarships.scholarship_amount
FROM students
INNER JOIN scholarships
ON students.student_id = scholarships.student_id;

Show all students with scholarship details:
SELECT students.name, students.course,
scholarships.scholarship_name,
scholarships.provider
FROM students
LEFT JOIN scholarships
ON students.student_id = scholarships.student_id;

Show students without scholarships:
SELECT students.name, students.course
FROM students
LEFT JOIN scholarships
ON students.student_id = scholarships.student_id
WHERE scholarships.student_id IS NULL;

Show students with approved scholarships:
SELECT students.name, students.course,
scholarships.scholarship_name,
scholarships.provider,
scholarships.scholarship_amount
FROM students
INNER JOIN scholarships
ON students.student_id = scholarships.student_id
WHERE students.scholarship_status = 'Approved';

USER QUESTION:
{question}

SQL:
"""

    response = ollama_client.generate(
        model=MODEL,
        prompt=prompt
    )

    sql = response["response"].strip()
    sql = sql.replace("```sql", "").replace("```", "").strip()

    return sql


def validate_sql(sql):
    if sql.upper().startswith("ERROR:"):
        return False, sql

    if not sql.upper().startswith("SELECT"):
        return False, "ERROR: Only SELECT queries are allowed."

    dangerous = [
        "INSERT", "UPDATE", "DELETE", "DROP",
        "ALTER", "CREATE", "TRUNCATE",
        "GRANT", "REVOKE"
    ]

    for word in dangerous:
        if re.search(r"\b" + word + r"\b", sql.upper()):
            return False, f"ERROR: {word} queries are not allowed."

    return True, ""


def execute_sql(sql):
    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def explain_results(question, results):
    if not results:
        return "Summary:\n• No matching records were found."

    prompt = f"""
You are an AI result explanation assistant.

USER QUESTION:
{question}

ACTUAL RESULTS:
{results}

Explain ONLY the actual results.

RULES:
1. Do not explain the SQL query.
2. Do not mention SQL, SELECT, JOIN, WHERE or database.
3. Do not add information that is not in the results.
4. Do not guess or invent information.
5. Give a short summary.
6. Give important findings in bullet points.
7. Use simple English.
8. Make sure the explanation matches the actual results.

FORMAT:

Summary:
• Short summary.

Key Findings:
• Important finding
• Important finding
• Important finding

Return only the explanation.
"""

    response = ollama_client.generate(
        model=MODEL,
        prompt=prompt
    )

    return response["response"].strip()


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.post("/ask")
def ask_question(request: QuestionRequest):
    try:
        question = request.question.strip()

        if not question:
            raise HTTPException(
                status_code=400,
                detail="Please enter a question."
            )

        sql = generate_sql(question)
        valid, message = validate_sql(sql)

        if not valid:
            raise HTTPException(
                status_code=400,
                detail=message
            )

        results = execute_sql(sql)
        explanation = explain_results(question, results)

        return {
            "success": True,
            "question": question,
            "generated_sql": sql,
            "results": results,
            "explanation": explanation
        }

    except HTTPException:
        raise

    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=400,
            detail=f"Database Error: {str(e)}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Server Error: {str(e)}"
        )