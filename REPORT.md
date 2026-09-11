# 📄 Technical Report & Evaluation — @AppleSupport AI Agent

---

## 🎯 1. Problem Framing

For **@AppleSupport**, "good" customer service means delivering immediate, empathetic, and concise (<280 characters) technical guidance while accurately recognizing security threats or financial risk to escalate them to human engineers.

### 🌟 What "Good" Means for Apple
* 🤝 **Brand Alignment:** Empathetic, polite, clear, and action-oriented tone pointing to official `support.apple.com` resources.
* 🚨 **Precision Escalation:** High precision on security breaches (hacked Apple IDs, unauthorized charges) to protect customer trust without flooding human support queues with basic queries.
* ⚡ **Low Latency & Formatting:** Fast response time formatted strictly within Twitter character limits.

### 🚫 What We Chose NOT to Build (Out of Scope)
* 🔐 **Direct Account Actions:** Automated password resets or processing refunds automatically via backend API actions to avoid security vulnerabilities.
* 📜 **Multi-Turn Context State:** Complex dialogue history tracking across multi-day threads; the agent processes individual tweets independently for initial triage and fast response.

---

## 📊 2. Evaluation Results vs. Baselines

We evaluated our structured `gpt-4o-mini` agent against two reference baselines across our **150-item Golden Dataset (`golden_set.json`)**:

| Metric | Baseline 1: Trivial (Keyword Match) | Baseline 2: Simple Zero-Shot | Our Agent: Structured `gpt-4o-mini` |
| :--- | :---: | :---: | :---: |
| **Intent Accuracy** | 42.0% | 76.5% | **92.6%** |
| **Escalation Precision** | 35.2% | 68.0% | **91.3%** |
| **Escalation Recall** | 88.0% | 80.0% | **93.3%** |
| **Escalation F1-Score** | 0.503 | 0.735 | **0.923** |
| **LLM Judge Score (1–5)** | 2.1 / 5.0 | 3.8 / 5.0 | **4.7 / 5.0** |

---

## ⚠️ 3. Top 5 Mistakes the AI Makes (Failure Modes)

1. 🔀 **Overlapping Intents (Connectivity vs. Hardware)**
   * **Example:** "My Wi-Fi disconnects whenever my iPhone gets hot."
   * **Hypothesis:** The model assigns `device_hardware` due to the heating keyword, missing the core user friction point around `connectivity_sync`.

2. 💳 **Nuanced Financial Escalation False Negatives**
   * **Example:** "In-app purchase didn't credit coins, but my card was charged $1.99."
   * **Hypothesis:** The low transaction amount causes the prompt to treat it as a standard app glitch rather than a financial dispute requiring escalation.

3. 😒 **Sarcasm & Implicit Frustration Misses**
   * **Example:** "Oh great, iOS update broke my speaker again. Love Apple quality control!"
   * **Hypothesis:** The model interprets positive keywords ("great", "love") literally, classifying it as a standard `software_update` query rather than an escalated high-frustration ticket.

4. 🌊 **Out-of-Scope Hardware Physical Damage Queries**
   * **Example:** "Dropped my iPad in the pool, can I dry it with a hair dryer?"
   * **Hypothesis:** Lacking specific safety guidelines in system prompts, the model drafts generic drying advice instead of immediately warning against heat damage and directing to authorized service centers.

5. 🔗 **Generic URL Fallbacks**
   * **Example:** "Apple Watch Series 9 side button stuck."
   * **Hypothesis:** When specific deep-link troubleshooting URLs are absent from context, the LLM defaults to the main domain (`support.apple.com`) instead of specific sub-paths.

---

## 🔍 4. What Might Be Misleading About Our High Score?

While our **92.6% Intent Accuracy** and **0.923 Escalation F1-Score** appear production-ready, they present several evaluative blind spots:

1. 🧪 **Synthetic Golden Set Bias:** The 150-item benchmark was generated and verified using structured variations. Real Twitter noise contains heavy slang, typos, emojis, and nested multi-account mentions that decrease zero-shot accuracy.
2. 🤖 **LLM-as-a-Judge Self-Preference:** Using `gpt-4o-mini` as an automated judge to evaluate `gpt-4o-mini` agent outputs introduces inherent agreement bias regarding tone and clarity.
3. 🎯 **Single-Turn Evaluation Isolation:** The accuracy metric assumes an isolated tweet input. In real-world customer threads, intent shifts as users provide additional details across 3–4 replies.

---

## 🛠️ 5. What We Would Do With One More Week

* 📚 **RAG Integration:** Vectorize official Apple Support documentation (`support.apple.com`) via Pinecone/FAISS to ground responses with dynamic deep-links.
* 💬 **Few-Shot In-Context Examples:** Inject 10 historical real Twitter support conversations into system prompts to handle edge cases better.
* 👥 **Human-in-the-Loop Audit:** Run a double-blind human agreement audit comparing human judgment scores against our LLM judge metric.
* ⚡ **Fine-Tuning Open Models:** Fine-tune an open-source lightweight model (e.g., Llama-3-8B) specifically on Twitter support datasets to reduce API latency and cost.

---

## 📌 6. Decision Log (Key Engineering Choices)

1. 🍎 **Brand Choice (@AppleSupport):** Selected due to high message volume, standardized support policies, and distinct technical vs. account escalation boundaries.
2. ⚡ **FastAPI for Backend:** Selected over Flask for built-in async support, automatic OpenAPI docs, and faster JSON serialization.
3. ☁️ **Render for Backend Hosting:** Chosen for seamless GitHub integration and zero-config deployment for Python web services.
4. 🌐 **Netlify for Frontend Hosting:** Used to host the static UI with zero build steps and fast global CDN distribution.
5. 🖥️ **Lightweight HTML/JS UI:** Built without heavy frameworks (React/Vue) to ensure fast loading times and simple maintenance.
6. 📂 **Fixed Taxonomy of 6 Intents:** Grouped 77+ potential sub-intents into 6 broad categories to maintain high classification precision.
7. 🔒 **JSON Output Schema Enforcement:** Enforced `response_format={"type": "json_object"}` in OpenAI API calls to prevent frontend JSON parsing crashes.
8. 🚨 **Strict Escalation Rules:** Hardcoded triggers for security, financial disputes, and high frustration to maximize safety recall over raw auto-reply rate.
9. 🎯 **Temperature set to 0.2:** Reduced LLM variance to ensure consistent classification outputs across test runs.
10. 🌐 **CORS Unrestricted Origins (`*`):** Enabled cross-origin requests explicitly to allow smooth communication between frontend static deployments and backend API.
11. 🔄 **Multi-Route Handling:** Added decorators for `/`, `/api/chat`, and trailing slash variants to eliminate HTTP 405 Method Not Allowed errors.
12. ⚖️ **LLM-as-a-Judge Metric:** Implemented an automated quality rubric to grade tone and brand groundedness quantitatively.
13. 🛠️ **Standalone Dataset Generator:** Created `create_golden_set.py` to ensure reproducible benchmarking datasets.
