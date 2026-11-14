import os
import json
import re
import requests

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Project directory
ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
CORS(app)

# IBM watsonx.ai configuration
IBM_API_KEY = os.getenv("IBM_API_KEY", "")
IBM_PROJECT_ID = os.getenv("IBM_PROJECT_ID", "")
IBM_URL = os.getenv(
    "IBM_URL",
    "https://eu-de.ml.cloud.ibm.com"
).rstrip("/")

MODEL_ID = os.getenv(
    "IBM_MODEL_ID",
    "ibm/granite-3-8b-instruct"
)


# Homepage
@app.route("/", methods=["GET"])
def home():
    index_path = os.path.join(ROOT, "index.html")

    if os.path.isfile(index_path):
        return send_from_directory(ROOT, "index.html")

    return jsonify({
        "error": "index.html not found",
        "project_directory": ROOT,
        "available_files": os.listdir(ROOT)
    }), 404


# Health check
@app.route("/api/health", methods=["GET"])
def health():
    configured = bool(
        IBM_API_KEY and IBM_PROJECT_ID and IBM_URL
    )

    return jsonify({
        "status": "ok",
        "mode": "live" if configured else "setup_required",
        "provider": "IBM watsonx.ai",
        "model": MODEL_ID
    })


# File diagnostic
@app.route("/api/check-files", methods=["GET"])
def check_files():
    return jsonify({
        "root": ROOT,
        "files": os.listdir(ROOT),
        "index_exists": os.path.isfile(
            os.path.join(ROOT, "index.html")
        )
    })


# IBM Granite connection
def granite(prompt, max_new_tokens=900):

    if not all([
        IBM_API_KEY,
        IBM_PROJECT_ID,
        IBM_URL
    ]):
        raise RuntimeError(
            "IBM setup incomplete. Check environment variables."
        )

    token_response = requests.post(
        "https://iam.cloud.ibm.com/identity/token",
        data={
            "grant_type":
            "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": IBM_API_KEY
        },
        headers={
            "Content-Type":
            "application/x-www-form-urlencoded"
        },
        timeout=30
    )

    token_response.raise_for_status()

    token = token_response.json()["access_token"]

    url = (
        f"{IBM_URL}/ml/v1/text/generation"
        "?version=2023-05-29"
    )

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "model_id": MODEL_ID,
            "project_id": IBM_PROJECT_ID,
            "input": prompt,
            "parameters": {
                "decoding_method": "greedy",
                "max_new_tokens": max_new_tokens,
                "min_new_tokens": 30
            }
        },
        timeout=120
    )

    response.raise_for_status()

    result = response.json()

    return result["results"][0]["generated_text"].strip()


# JSON response parser
def parse_json(text):

    text = re.sub(
        r"^```(?:json)?|```$",
        "",
        text.strip(),
        flags=re.I | re.M
    ).strip()

    match = re.search(r"\{.*\}", text, re.S)

    if not match:
        raise ValueError(
            "IBM returned an unexpected response."
        )

    return json.loads(match.group(0))


# Lesson adaptation
@app.route("/api/adapt", methods=["POST"])
def adapt():

    data = request.get_json(force=True)

    content = data.get("content", "").strip()
    level = data.get("proficiency", "beginner")
    subject = data.get("subject", "")

    if not content:
        return jsonify(
            error="Please provide lesson content."
        ), 400

    prompt = f"""
You are EduAdapt, an educational tutor.
Adapt this lesson for a {level} learner.
Subject: {subject}.

Return ONLY valid JSON with:
adapted_explanation (string),
key_concepts (array),
analogies (array),
follow_up_questions (array).

Keep facts accurate.

Lesson:
{content}
"""

    try:
        return jsonify(parse_json(granite(prompt)))

    except Exception as error:
        app.logger.exception("Adaptation failed")
        return jsonify(error=str(error)), 502


# Learner assessment pipeline
@app.route("/api/pipeline", methods=["POST"])
def pipeline():

    data = request.get_json(force=True)

    content = data.get("content", "").strip()
    subject = data.get("subject", "")
    description = data.get("user_description", "")

    if not content:
        return jsonify(
            error="Please provide lesson content."
        ), 400

    prompt = f"""
Assess the learner and adapt this lesson.
Learner description: {description}.
Subject: {subject}.

Return ONLY valid JSON with:
proficiency_detected (beginner, intermediate, advanced, expert),
proficiency_confidence (low, medium, high),
adapted_explanation,
key_concepts,
analogies,
follow_up_questions.

Lesson:
{content}
"""

    try:
        return jsonify(parse_json(granite(prompt)))

    except Exception as error:
        app.logger.exception("Pipeline failed")
        return jsonify(error=str(error)), 502


# Quiz generation
@app.route("/api/quiz", methods=["POST"])
def quiz():

    data = request.get_json(force=True)

    content = data.get("content", "").strip()
    level = data.get("proficiency", "beginner")

    if not content:
        return jsonify(
            error="Please provide lesson content."
        ), 400

    prompt = f"""
Create exactly 4 multiple-choice questions
for a {level} learner based only on this lesson.

Return ONLY valid JSON:
{{
  "quiz": [
    {{
      "question": "...",
      "options": ["A...", "B...", "C...", "D..."],
      "correct": 0,
      "explanation": "..."
    }}
  ]
}}

The correct answer must be an option index from 0 to 3.

Lesson:
{content}
"""

    try:
        return jsonify(parse_json(granite(prompt)))

    except Exception as error:
        app.logger.exception("Quiz generation failed")
        return jsonify(error=str(error)), 502


# Run application
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port
    )
