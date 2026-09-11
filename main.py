import os
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI

app = FastAPI(title="AppleSupport AI Agent API")

# Explicit CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize OpenAI Client using Environment Variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

INTENT_TAXONOMY = [
    "account_access",
    "device_hardware",
    "software_update",
    "billing_subscription",
    "connectivity_sync",
    "general_query"
]

SYSTEM_PROMPT = f"""You are an AI Support Agent for @AppleSupport on Twitter.
Analyze the customer's tweet and generate a structured JSON response.

Allowed Intent Categories:
{', '.join(INTENT_TAXONOMY)}

Rules for Escalation:
- Set 'escalate' to true IF the query involves unauthorized billing, financial refund requests, severe user frustration/abuse, or personal security breaches (hacked Apple ID/locked account).
- Otherwise, set 'escalate' to false.

Response Guidelines:
- Draft a polite, helpful, empathetic, and concise reply (< 280 characters).
- Maintain Apple's brand voice.

You MUST respond strictly with a valid JSON object with the following schema:
{{
  "intent": "<one of the allowed intent categories>",
  "escalate": <true or false>,
  "message": "<your drafted reply or escalation instructions>"
}}
"""

class TweetRequest(BaseModel):
    tweet: str

@app.get("/")
def home():
    return {"status": "AppleSupport AI Agent API is running!"}

# Combined Route Handler supporting both JSON payload and direct Request parsing
@app.api_route("/api/chat", methods=["POST", "GET", "OPTIONS"])
@app.api_route("/api/chat/", methods=["POST", "GET", "OPTIONS"])
@app.api_route("/", methods=["POST"])
async def chat_handler(request: Request):
    if request.method == "OPTIONS":
        return {"status": "ok"}

    tweet_text = ""
    try:
        body = await request.json()
        tweet_text = body.get("tweet", "")
    except Exception:
        pass

    if not tweet_text.strip():
        return {
            "intent": "general_query",
            "escalate": False,
            "message": "Please enter a valid tweet text to process."
        }

    try:
        user_payload = f'Customer Tweet: "{tweet_text}"'
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_payload}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        content = json.loads(response.choices[0].message.content)
        return {
            "intent": content.get("intent", "general_query"),
            "escalate": bool(content.get("escalate", False)),
            "message": content.get("message", "Thank you for reaching out to @AppleSupport. Please check support.apple.com for assistance.")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
