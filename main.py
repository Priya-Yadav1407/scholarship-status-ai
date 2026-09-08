from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

import mysql.connector
import ollama
import os
import re

from dotenv import load_dotenv
from pydantic import BaseModel


# Load environment variables
load_dotenv()


app = FastAPI(
    title="Student Scholarship SQL Generator"
)


# Connect HTML templates
templates = Jinja2Templates(
    directory="templates"
)


# Database configuration
DB_HOST = os.getenv("DB_HOST")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

OLLAMA_MODEL = os.getenv(
    "OLLAMA_MODEL",
    "llama3.2"
)


# -------------------------
# API Request Model
# -------------------------

class QuestionRequest(BaseModel):
    question: str


# -------------------------
# DATABASE CONNECTION
# -------------------------

def get_db_connection():

    connection = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

    return connection


# -------------------------
# DATABASE SCHEMA
# -------------------------

def get_schema():

    return """
DATABASE: scholarship_db

TABLE: students

COLUMNS:

student_id - Integer - Student ID
name - Text - Student Name
course - Text - Course Name
marks - Integer - Student Marks
family_income - Decimal - Family Income
scholarship_amount - Decimal - Scholarship Amount
scholarship_status - Text - Approved, Pending, or Rejected
"""


# -------------------------
# OLLAMA SQL GENERATOR
# -------------------------

def generate_sql(question):

    schema = get_schema()

    prompt = f"""
You are an expert MySQL SQL generator.

Your task is to convert a user's English question into a valid MySQL query.

DATABASE SCHEMA:

{schema}

STRICT RULES:

1. Generate ONLY the SQL query.
2. Do not provide an explanation.
3. Do not use Markdown.
4. Only SELECT statements are allowed.
5. Never generate INSERT.
6. Never generate UPDATE.
7. Never generate DELETE.
8. Never generate DROP.
9. Never generate ALTER.
10. Only use the students table.

USER QUESTION:

{question}

SQL:
"""

    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt
    )

    sql_query = response["response"].strip()

    # Remove markdown formatting
    sql_query = sql_query.replace(
        "```sql", ""
    )

    sql_query = sql_query.replace(
        "```", ""
    )

    return sql_query.strip()


# -------------------------
# SQL SECURITY CHECK
# -------------------------

def validate_sql(sql_query):

    sql_query = sql_query.strip()

    # Must start with SELECT
    if not sql_query.upper().startswith(
        "SELECT"
    ):
        return False

    dangerous_words = [
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "ALTER",
        "CREATE",
        "TRUNCATE",
        "GRANT",
        "REVOKE"
    ]

    for word in dangerous_words:

        pattern = r"\b" + word + r"\b"

        if re.search(
            pattern,
            sql_query.upper()
        ):
            return False

    return True


# -------------------------
# EXECUTE SQL
# -------------------------

def execute_sql(sql_query):

    connection = get_db_connection()

    cursor = connection.cursor(
        dictionary=True
    )

    cursor.execute(sql_query)

    results = cursor.fetchall()

    cursor.close()
    connection.close()

    return results


# -------------------------
# FRONTEND PAGE
# -------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )
# -------------------------
# API: ASK QUESTION
# -------------------------

@app.post("/ask")
def ask_question(request: QuestionRequest):

    try:

        # Generate SQL using Ollama
        sql_query = generate_sql(
            request.question
        )

        # Validate SQL
        if not validate_sql(sql_query):

            raise HTTPException(
                status_code=400,
                detail="Unsafe SQL query generated"
            )

        # Execute query
        results = execute_sql(
            sql_query
        )

        return {
            "success": True,
            "question": request.question,
            "generated_sql": sql_query,
            "results": results
        }

    except HTTPException:
        raise

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )