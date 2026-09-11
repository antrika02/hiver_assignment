import os
import json
from openai import OpenAI

# OpenAI Client setup kar rahe hain (API key environment variable se uthayega)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# 1. Categories jisme AI customer ki problem ko baant sakega
INTENT_TAXONOMY = [
    "account_access",
    "device_hardware",
    "software_update",
    "billing_subscription",
    "connectivity_sync",
    "general_query"
]

# 2. System Instructions (AI ko rules sikha rahe hain)
SYSTEM_PROMPT = f"""You are an AI Support Agent for @AppleSupport on Twitter.
Analyze the customer's tweet and generate a structured JSON response.

Intents allowed: {', '.join(INTENT_TAXONOMY)}

Rules for Escalation:
- Set 'escalate' to true IF the query involves unauthorized billing, financial refund requests, severe user frustration/abuse, or personal security breaches (hacked Apple ID).
- Otherwise, set 'escalate' to false.

Response Guidelines:
- Draft a polite, concise reply (< 280 characters).
- Suggest official help links (e.g., support.apple.com) or standard troubleshooting.
"""

# 3. Main Function jo Tweet lekar OpenAI ko bhejta hai
def process_tweet(customer_tweet: str):
    user_payload = f'Customer Tweet: "{customer_tweet}"'
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_payload}
        ],
        response_format={"type": "json_object"}, # Structured JSON format output
        temperature=0.2
    )
    return json.loads(response.choices[0].message.content)

# 4. Testing Block (Script chalane par ye 3 fake test cases run honge)
if __name__ == "__main__":
    print("\n==========================================")
    print("      HIVER AI AGENT TESTING RUNNER       ")
    print("==========================================\n")
    
    test_tweets = [
        "@AppleSupport My iPhone battery dropped from 80% to 10% in 20 minutes after iOS update! Fix this!",
        "@AppleSupport I was charged $49.99 twice for my iCloud storage this morning! Refund me now!",
        "@AppleSupport How do I pair my AirPods Pro with my MacBook Air?"
    ]
    
    for idx, tweet in enumerate(test_tweets, 1):
        print(f"[Test Case {idx}]")
        print(f"Customer Tweet : {tweet}")
        try:
            result = process_tweet(tweet)
            print("Agent Result   :")
            print(json.dumps(result, indent=2))
        except Exception as e:
            print(f"\nError: {e}")
            print("Note: Make sure your OPENAI_API_KEY is set correctly using: set OPENAI_API_KEY=your_key")
        print("-" * 50)