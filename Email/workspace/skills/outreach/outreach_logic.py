import os
import json
import urllib.request
import urllib.error
import time

# The User-Provided System Prompt for the Outreach Agent
PRIMARY_DILIGENCE_SYSTEM_PROMPT = """
SYSTEM PROMPT: Primary Diligence Email Outreach Agent

You are a professional email writing assistant. Your task is to generate precisely crafted inquiries for expert outreach. The sender is Mayank Hinduja, a student researcher at NYU Stern.

CORE MANDATE: THE "ACKNOWLEDGE + PIVOT" STRATEGY
1. **Acknowledge**: Open by briefly acknowledging the expert's impressive background at their CURRENT firm (e.g., "I saw your work at [Company]...").
2. **Pivot**: Immediately pivot to your research project on the DILIGENCE TARGET ({target}). **CRITICAL**: Acknowledge that they were a former technical lead or employee at {target}. This establishes institutional authority and explains why you are reaching out to them specifically for {target} research.
3. **Focus**: ALL questions must be directed at the technology, strategy, or market position of {target}.
4. **Prohibition**: DO NOT ask for internal information, data, or opinions about the expert's own company. This is a technical diligence project for {target} ONLY.

STEP 1 — RECIPIENT PROFILE
- Identify the anchor role.
- Align the the 'Diligence Objective' with their specific career expertise.

STEP 2 — SUBJECT LINE
- Maximum 8 words. Use: {target} Diligence: [Technical/Strategic Topic]
- Example: "Firefly Aerospace Diligence: Propulsion Scalability"

STEP 3 — EMAIL BODY
- Opening Hook: Professional acknowledgement of their role at their current firm.
- Identity: NYU Stern research on {target}.
- Rationale & Objective: Explicitly state that our analysis has identified a key catalyst: {topic}. 
- The Questions: 2-3 hyper-specific technical questions derived from {topic}.
- The Ask: 10-15 minute call for expert insight.

PROHIBITED: No "I hope you are well", no calendar links. Use "Mayank Hinduja" in signature.

FORMATTING: Ensure there are clear line gaps (double newlines) between paragraphs and before the list of questions for readability.
"""

def generate_advanced_email(name, company, target="Firefly Aerospace", topic=None, role=None, warmth="cold", seniority="manager", linkedin_url=None):
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY not found in environment.")

    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    
    # Precise framing: Target = What we research. Company = Where they work.
    user_context = f"""
    RESEARCH MANDATE:
    - Diligence Target: {target} (This is the company we are analyzing)
    - Primary Research Topic: {topic if topic else "General technical/strategic outlook"}
    
    EXPERT BACKGROUND (Context only):
    - Name: {name}
    - Current/Past Role: {role if role else "Specialist"}
    - Current/Past Firm: {company}
    
    SENDER INFO:
    - Name: Mayank Hinduja (NYU Stern student)
    - LinkedIn: {linkedin_url if linkedin_url else "Not provided"}
    
    INSTRUCTION: Write an email to {name} acknowledging their current role at {company}. 
    State explicitly that you are conducting a research project focused on {target} (the "Target"). 
    The logic should be: "I see you are at {company}, and given your expertise in {role}, I wanted to reach out regarding my research on {target}."
    
    Then, direct 2-3 specific technical/strategic questions ONLY at {target}. 
    DO NOT ask about {company} internals.
    
    Format your response as a JSON object:
    {{
      "subject": "[Target] Research Request: [Keyword]",
      "body": "the full email body"
    }}
    """

    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [
            {"role": "system", "content": PRIMARY_DILIGENCE_SYSTEM_PROMPT},
            {"role": "user", "content": user_context}
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
        "response_format": { "type": "json_object" }
    }

    for attempt in range(4):
        try:
            req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            })
            with urllib.request.urlopen(req, timeout=25) as response:
                result = json.loads(response.read().decode())
                content = result['choices'][0]['message'].get('content')
                return json.loads(content)
        except Exception as e:
            if "429" in str(e):
                wait_time = (2 ** attempt) * 5 + 2
                print(f"   [Rate Limit] Outreach LLM hit 429. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                continue
            print(f"Error generating sophisticated email: {e}")
            return None
    return None
