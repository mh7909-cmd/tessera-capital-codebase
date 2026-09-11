import urllib.request
import json
import os

api_key = os.getenv("NVIDIA_API_KEY", "")
url = "https://integrate.api.nvidia.com/v1/chat/completions"
payload = {
    "model": "moonshotai/kimi-k2.5",
    "messages": [
        {"role": "user", "content": "Hello"}
    ],
    "max_tokens": 1024
}

req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers={
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}'
})

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print(result['choices'][0]['message']['content'])
except Exception as e:
    print(f"Error calling NVIDIA API: {e}")
    if hasattr(e, 'read'):
        print(e.read().decode())
