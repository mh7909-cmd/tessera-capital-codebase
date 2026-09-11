import sys
import os

# Add the voiceagent directory to path to import phone.py
sys.path.append(os.path.join(os.path.dirname(__file__), 'voiceagent'))

from phone import trigger_outbound_call

def manual_test():
    phone_number = "+16462625452"
    name = "Shubhanker"
    context = "Testing the voice agent connection manually."
    
    print(f"🚀 Manually triggering call to {phone_number}...")
    result = trigger_outbound_call(phone_number, name, context)
    print(f"Result: {result}")

if __name__ == "__main__":
    manual_test()
