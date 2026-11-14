import os, json, re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=ROOT, static_url_path='')
CORS(app)
IBM_API_KEY = os.getenv('IBM_API_KEY', '')
IBM_PROJECT_ID = os.getenv('IBM_PROJECT_ID', '')
IBM_URL = os.getenv('IBM_URL', '').rstrip('/')
MODEL_ID = os.getenv('IBM_MODEL_ID', 'ibm/granite-3-8b-instruct')

@app.get('/')
def home(): return send_from_directory(ROOT, 'index.html')

@app.get('/api/health')
def health():
    configured = bool(IBM_API_KEY and IBM_PROJECT_ID and IBM_URL)
    return jsonify({'status':'ok','mode':'live' if configured else 'setup_required','provider':'IBM watsonx.ai','model':MODEL_ID})

def granite(prompt, max_new_tokens=900):
    if not (IBM_API_KEY and IBM_PROJECT_ID and IBM_URL):
        raise RuntimeError('IBM setup incomplete. Set IBM_API_KEY, IBM_PROJECT_ID and IBM_URL in the hosting environment.')
    token_res = requests.post('https://iam.cloud.ibm.com/identity/token', data={
        'grant_type':'urn:ibm:params:oauth:grant-type:apikey','apikey':IBM_API_KEY
    }, headers={'Content-Type':'application/x-www-form-urlencoded'}, timeout=30)
    token_res.raise_for_status(); token = token_res.json()['access_token']
    url = f'{IBM_URL}/ml/v1/text/generation?version=2023-05-29'
    res = requests.post(url, headers={'Authorization':f'Bearer {token}','Content-Type':'application/json'}, json={
        'model_id':MODEL_ID,'project_id':IBM_PROJECT_ID,'input':prompt,'parameters':{'decoding_method':'greedy','max_new_tokens':max_new_tokens,'min_new_tokens':30}
    }, timeout=120)
    res.raise_for_status()
    data=res.json(); return data['results'][0]['generated_text'].strip()

def parse_json(text):
    text=re.sub(r'^```(?:json)?|```$', '', text.strip(), flags=re.I|re.M).strip()
    m=re.search(r'\{.*\}', text, re.S)
    if not m: raise ValueError('IBM model returned an unexpected response. Please try again.')
    return json.loads(m.group(0))

@app.post('/api/adapt')
def adapt():
    d=request.get_json(force=True); content=d.get('content','').strip(); level=d.get('proficiency','beginner'); subject=d.get('subject','')
    if not content: return jsonify(error='Please provide lesson content.'),400
    prompt=f'''You are EduAdapt, an educational tutor. Adapt this lesson for a {level} learner. Subject: {subject}. Return ONLY valid JSON with keys adapted_explanation (string), key_concepts (array of short strings), analogies (array of strings), follow_up_questions (array of strings). Keep facts accurate. Lesson:\n{content}'''
    try: return jsonify(parse_json(granite(prompt)))
    except Exception as e: return jsonify(error=str(e)), 502

@app.post('/api/pipeline')
def pipeline():
    d=request.get_json(force=True); content=d.get('content','').strip(); subject=d.get('subject',''); desc=d.get('user_description','')
    if not content: return jsonify(error='Please provide lesson content.'),400
    prompt=f'''Assess the learner and adapt this lesson to a suitable level. Learner description: {desc}. Subject: {subject}. Return ONLY valid JSON with keys proficiency_detected (one of beginner, intermediate, advanced, expert), proficiency_confidence (low, medium, high), adapted_explanation, key_concepts (array), analogies (array), follow_up_questions (array). Lesson:\n{content}'''
    try: return jsonify(parse_json(granite(prompt)))
    except Exception as e: return jsonify(error=str(e)), 502

@app.post('/api/quiz')
def quiz():
    d=request.get_json(force=True); content=d.get('content','').strip(); level=d.get('proficiency','beginner')
    prompt=f'''Create exactly 4 multiple-choice comprehension questions for a {level} learner based only on this lesson. Return ONLY valid JSON as {{"quiz":[{{"question":"...","options":["A...","B...","C...","D..."],"correct":0,"explanation":"..."}}]}}. correct must be option index 0-3. Lesson:\n{content}'''
    try:
        data=parse_json(granite(prompt)); return jsonify(data)
    except Exception as e: return jsonify(error=str(e)), 502

if __name__ == '__main__': app.run(host='0.0.0.0', port=int(os.getenv('PORT',5000)))
