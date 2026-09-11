import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI
import sys

# Add the EC_Analyzer directory to path
sys.path.append(os.path.join(os.getcwd(), 'EC_Analyzer', 'EC_Analyzer'))
from earnings_call_analyzer import fetch_api_transcripts, backoff_request

load_dotenv()

async def test_ec_speed(ticker):
    print(f"🚀 Testing EC analysis speed for {ticker}...")
    
    # 1. Fetch transcripts
    start_fetch = asyncio.get_event_loop().time()
    transcripts = await fetch_api_transcripts(ticker)
    end_fetch = asyncio.get_event_loop().time()
    print(f"   [FETCH] Found {len(transcripts)} transcripts in {end_fetch - start_fetch:.2f}s")
    
    if not transcripts:
        print("   ❌ No transcripts found.")
        return

    # 2. Test LLM speed
    client = AsyncOpenAI(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url="https://integrate.api.nvidia.com/v1"
    )
    
    LLM_MODEL = "meta/llama-3.1-8b-instruct"
    
    async def process_one(i, text):
        t0 = asyncio.get_event_loop().time()
        print(f"   [LLM] Starting analysis for EC {i+1}...")
        
        prompt = f"Provide a brief summary of this transcript for {ticker}.\n\nTranscript:\n{text[:5000]}"
        
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        
        t1 = asyncio.get_event_loop().time()
        print(f"   [LLM] Finished EC {i+1} in {t1 - t0:.2f}s")
        return response.choices[0].message.content

    start_llm = asyncio.get_event_loop().time()
    tasks = [process_one(i, text) for i, text in enumerate(transcripts[:4])]
    results = await asyncio.gather(*tasks)
    end_llm = asyncio.get_event_loop().time()
    
    print(f"🚀 Total LLM time for {len(results)} calls: {end_llm - start_llm:.2f}s")

if __name__ == "__main__":
    asyncio.run(test_ec_speed("FLY"))
