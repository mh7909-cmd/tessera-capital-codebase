import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

try:
    # Attempt to list models or check a common one
    print("Checking available models...")
    # Anthropic doesn't have a direct 'list models' in the same way OpenAI does in old SDKs, 
    # but we can try a simple message with a known legacy model to see if it works.
    message = client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=10,
        messages=[{"role": "user", "content": "hi"}]
    )
    print(f"Success with Haiku: {message.content[0].text}")
except Exception as e:
    print(f"Error: {e}")
