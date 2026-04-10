from flask import Flask, request, jsonify
import requests
import json
from datetime import datetime, timedelta
import random
import time

app = Flask(__name__)

# ================== CONFIG ==================
COOKIES = {
    "XSRF-TOKEN": "eyJpdiI6IkFhR0QzSEdoRUxEVDRUdGJxQzR2SXc9PSIsInZhbHVlIjoibG4xOGMrcDFKRjl5M1RoRkRjdFVINzQ0L2lEMmxWNHE1ZHRJcDZSY2lGTEduRmRZMml5ZnhXK0I0K1RNenU4VjVmVVR1cVVKMDByZkJiZTNRRktFblRPaFRuTmlzcUNsY2xCZkZQRkVhTjJ1Z09tWGhZT1FpT2xadTR0MWtNV0IiLCJtYWMiOiIzODVkM2YyMzg0ODJmZDFmODY5MTliNDQ5ZWUwMmFmZDkyMWMwMDYyNDM3ODI5NmQ0YWE5ZDQyODI2MmY1YTIzIiwidGFnIjoiIn0%3D",
    "uncensored_chat_session": "eyJpdiI6IlVteFlOUUFPQityTmlQTDVOS2k5R3c9PSIsInZhbHVlIjoiSktMd2t2VHk3Zmw5TE9BRFBIWmF6OGFLSEtVQW5RZmFGNmNBZmlEMWx0c1FEN3U3MUZIdVZNaTdKaGNabGgwRFN1aE1SeXY3N2F1czBqY3RVTlFXQjNmQ093bTBPamVNN3JPNWZIRWl1ZkZkT01ZSzg4VEdTVUxXeEJZT0NxWEEiLCJtYWMiOiJjZjlmNzg1Y2EyZTFmZDY3ZmU2MzgyMTJiMDg0OTkyNTg1MTYwNDUxM2Q1YWQxM2U0ZjUzNzgxNmVkODgyYTQxIiwidGFnIjoiIn0%3D",
}

X_CSRF_TOKEN = "eyJpdiI6IkFhR0QzSEdoRUxEVDRUdGJxQzR2SXc9PSIsInZhbHVlIjoibG4xOGMrcDFKRjl5M1RoRkRjdFVINzQ0L2lEMmxWNHE1ZHRJcDZSY2lGTEduRmRZMml5ZnhXK0I0K1RNenU4VjVmVVR1cVVKMDByZkJiZTNRRktFblRPaFRuTmlzcUNsY2xCZkZQRkVhTjJ1Z09tWGhZT1FpT2xadTR0MWtNV0IiLCJtYWMiOiIzODVkM2YyMzg0ODJmZDFmODY5MTliNDQ5ZWUwMmFmZDkyMWMwMDYyNDM3ODI5NmQ0YWE5ZDQyODI2MmY1YTIzIiwidGFnIjoiIn0="

CHAT_ID = "1bae9d47-75eb-4524-ba87-f0fe56116f83"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
    "Accept": "text/event-stream",
    "Content-Type": "application/json",
    "Origin": "https://uncensored.chat",
    "Referer": f"https://uncensored.chat/chat/{CHAT_ID}",
    "x-csrf-token": X_CSRF_TOKEN,
    "x-requested-with": "XMLHttpRequest",
}

RATE_LIMIT = 60  # Max 60 requests per hour

request_log = []

def is_rate_limited():
    global request_log
    now = datetime.now()
    request_log = [t for t in request_log if now - t < timedelta(hours=1)]
    if len(request_log) >= RATE_LIMIT:
        return True
    request_log.append(now)
    return False

def send_to_uncensored(message):
    url = f"https://uncensored.chat/chats/{CHAT_ID}/stream"
    
    payload = {
        "messages": [{"role": "user", "content": message, "type": "text"}],
        "api_version": "v1"
    }
    
    try:
        time.sleep(random.uniform(0.5, 1.8))
        resp = requests.post(url, headers=HEADERS, cookies=COOKIES, json=payload, stream=True, timeout=90)
        
        if resp.status_code != 200:
            return f"Error {resp.status_code} - Cookies may be expired"
        
        full_reply = ""
        for line in resp.iter_lines():
            if line and line.startswith(b"data: "):
                try:
                    data = json.loads(line[6:])
                    if "content" in data:
                        full_reply += data["content"]
                except:
                    pass
        return full_reply.strip() or "No response"
    except Exception as e:
        return f"Failed: {str(e)}"

@app.route('/api/chat', methods=['POST'])
def chat():
    if is_rate_limited():
        return jsonify({"error": "Rate limit reached (60/hour)"}), 429
    
    data = request.get_json(silent=True)
    message = data.get('message') if data else None
    
    if not message:
        return jsonify({"error": "message field is required"}), 400
    
    reply = send_to_uncensored(message)
    return jsonify({"response": reply})

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "ok", "message": "Uncensored.chat Wrapper Running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
