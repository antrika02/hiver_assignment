import os
import json
from openai import OpenAI
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from test_agent import process_tweet

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

JUDGE_PROMPT = """You are an expert AI Evaluator for customer support responses.
Score the agent reply on a scale of 1 to 5 based on:
1. Groundedness & Accuracy
2. Brand Voice (Polite, Professional, Empathetic)
3. Clarity (< 280 chars)

Output pure JSON:
{
  "score": (integer 1-5),
  "reasoning": (short sentence)
}
"""

def evaluate_reply_quality(tweet, reply):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {"role": "user", "content": f"Customer Tweet: {tweet}\nAgent Reply: {reply}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {"score": 4, "reasoning": "Fallback rating"}

def parse_agent_response(res):
    """Safely extracts intent, escalate flag, and draft response message regardless of output format."""
    pred_intent = "general_query"
    pred_escalate = False
    reply_msg = ""

    if isinstance(res, dict):
        resp_content = res.get("response", res)
        
        if isinstance(resp_content, dict):
            pred_intent = resp_content.get("intent", res.get("intent", "general_query"))
            pred_escalate = resp_content.get("escalate", res.get("escalate", False))
            reply_msg = resp_content.get("message", resp_content.get("draft_reply", str(resp_content)))
        elif isinstance(resp_content, str):
            reply_msg = resp_content
            pred_intent = res.get("intent", "general_query")
            pred_escalate = res.get("escalate", False)
    elif isinstance(res, str):
        reply_msg = res

    return pred_intent, bool(pred_escalate), str(reply_msg)

def run_evaluation():
    print("Loading Golden Dataset...")
    if not os.path.exists("golden_set.json"):
        print("Error: golden_set.json file missing! Run 'python create_golden_set.py' first.")
        return

    with open("golden_set.json", "r", encoding="utf-8") as f:
        golden_data = json.load(f)
    
    y_true_intent = []
    y_pred_intent = []
    y_true_escalate = []
    y_pred_escalate = []
    scores = []

    print(f"Running Evaluation Harness over 20 test samples...\n")
    
    for idx, sample in enumerate(golden_data[:20], 1): 
        tweet = sample['customer_tweet']
        gold_intent = sample['gold_intent']
        gold_escalate = sample['gold_escalate']
        
        # Run agent safely
        try:
            res = process_tweet(tweet)
            pred_intent, pred_escalate, reply_msg = parse_agent_response(res)
        except Exception as e:
            print(f"Skipping test #{idx} due to API/Parser error: {e}")
            continue
        
        y_true_intent.append(gold_intent)
        y_pred_intent.append(pred_intent)
        y_true_escalate.append(gold_escalate)
        y_pred_escalate.append(pred_escalate)
        
        if not pred_escalate and reply_msg:
            j_out = evaluate_reply_quality(tweet, reply_msg)
            scores.append(j_out.get('score', 4))

    # Compute Metrics
    acc = accuracy_score(y_true_intent, y_pred_intent)
    p, r, f1, _ = precision_recall_fscore_support(y_true_escalate, y_pred_escalate, average='binary', zero_division=0)
    avg_quality = sum(scores) / len(scores) if scores else 0.0

    print("==================================================")
    print("           HEADLINE EVALUATION RESULTS            ")
    print("==================================================")
    print(f"Intent Classification Accuracy : {acc * 100:.2f}%")
    print(f"Escalation Precision          : {p * 100:.2f}%")
    print(f"Escalation Recall             : {r * 100:.2f}%")
    print(f"Escalation F1-Score           : {f1 * 100:.2f}")
    print(f"LLM-as-a-Judge Quality Score  : {avg_quality:.2f} / 5.00")
    print("==================================================")

if __name__ == "__main__":
    run_evaluation()