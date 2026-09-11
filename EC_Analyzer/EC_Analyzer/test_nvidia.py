import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_nvidia_api():
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("LLM_MODEL", "google/gemma-4-31b-it")

    print(f"Testing NVIDIA NIM API with model: {model}")
    
    client = OpenAI(
        base_url=base_url,
        api_key=api_key
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Hello, can you hear me? Respond with 'Yes' if you are working."}
            ],
            temperature=0.5,
            top_p=1,
            max_tokens=64
        )
        print(f"Response: {completion.choices[0].message.content}")
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_nvidia_api()
