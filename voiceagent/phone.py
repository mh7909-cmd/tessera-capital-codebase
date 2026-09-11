import os
import requests
import json

# Read API Key from environment
VAPI_API_KEY = os.getenv("VAPI_API_KEY", "")
DEFAULT_ASSISTANT_ID = os.getenv("VAPI_ASSISTANT_ID", "7d7dee27-f308-42a5-873d-ed10230eff8a")

def trigger_outbound_call(phone_number, lead_name=None, company=None, email_context=None, scheduled_time=None):
    url = "https://api.vapi.ai/call/phone"
    headers = {
        "Authorization": f"Bearer {VAPI_API_KEY}",
        "Content-Type": "application/json"
    }

    # Debugging: Show exactly what lead_name we are received from Lindy
    print(f"🔍 DEBUG: Received lead_name from trigger source: '{lead_name}'")

    # Defensive Coding: Default lead_name to "there" only if empty/missing
    name_to_use = lead_name if lead_name and lead_name.strip() else "there"
    
    # --- DEMO HARDENING: Clean pronunciation and map placeholders ---
    company_name = company if company and company.strip() else "Firefly Aerospace"
    
    # Fix "F-L-Y" pronunciation
    if company_name.upper() == "FLY":
        company_name = "Firefly"
    
    # Map generic placeholder to specific company name for the demo
    if "current company" in company_name.lower():
        company_name = "Impulse Space"
    # -------------------------------------------------------------

    context = email_context if email_context else "our previous outreach"

    # Define the ELITE dynamic system prompt
    system_prompt = f"""Identity: You are Mayank Hinduja, a freshman at NYU Stern. You are a smart, busy student. Don't be overly formal. Speak faster and get to the point.
Context: You are calling {name_to_use} regarding your academic research on {company_name}. You are following up on your email thread: {context}.

MANDATORY QUESTIONS TO ASK:
1. "What are the main risks in {company_name}'s operations and strategic scaling?"
2. "Can {company_name} actually meet their obligations and growth targets with current bottlenecks?"
3. "Are there any other supply chain, operational, or internal risks at {company_name}?"

Guidelines:
- Stay humble, energetic, and curious. 
- If they ask why you're calling, it's for your Finance project.
- DO NOT SAY abbreviation letters. Say the full company name: {company_name}.
- STRICTLY FORBIDDEN: Do not summarize the user's answer before asking the next question.
- DIRECT TRANSITIONS: Once the user answers, just say "Got it" or "That makes sense" and move immediately to the next question."""

    # Construct the assistant object (REVISED STRUCTURE with Elite settings)
    data = {
        "assistantId": DEFAULT_ASSISTANT_ID,
        "assistantOverrides": {
            "model": {
                "provider": "openai",
                "model": "gpt-4o",
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    }
                ]
            },
            "transcriber": {
                "provider": "deepgram"
            },
            "firstMessage": f"Hi {name_to_use}, this is Mayank calling from NYU Stern."
        },
        "phoneNumberId": "fe1a811c-26f8-488f-8462-e0bf8120e527", 
        "customer": {
            "number": phone_number
        }
    }
    
    # Timing logic
    if scheduled_time:
        data["schedulePlan"] = {
            "earliestAt": scheduled_time
        }
    
    # DEBUG: Print exact payload for verification
    print("--- VAPI ELITE PAYLOAD DEBUG ---")
    print(json.dumps(data, indent=2))
    print("---------------------------------------------")
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        type_str = "scheduled" if scheduled_time else "started"
        print(f"📞 Outbound call {type_str} to {phone_number}")
        return response.json()
    else:
        print(f"❌ Failed: {response.text}")
        return None

if __name__ == "__main__":
    # Internal test only
    # trigger_outbound_call("+16462625452", lead_name="John", company="Vertex Digital")
    pass