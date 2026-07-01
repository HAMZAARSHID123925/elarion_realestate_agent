import asyncio
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.orchestrator.schemas import UnifiedRequest
from app.orchestrator.graph import orchestrator_graph

# Mute standard logging for cleaner test output
import logging
logging.getLogger().setLevel(logging.CRITICAL)

whatsapp_emergency = UnifiedRequest(
    channel="whatsapp",
    user_id="+923001234567",
    raw_text="The main pipe burst and my kitchen is flooding right now! Please send someone immediately!"
)

async def test_a_latency():
    print("--- Test A: Per-request latency ---")
    payloads = [
        whatsapp_emergency,
        UnifiedRequest(channel="email", user_id="tenant@example.com", raw_text="Hello, I would like to know the process for renewing my lease next month. Thanks."),
        UnifiedRequest(channel="vapi", user_id="unknown_caller", raw_text="I am looking for a 3 bedroom apartment in Lahore under 200 lakhs.")
    ]
    
    times = []
    for i, p in enumerate(payloads, 1):
        start = time.perf_counter()
        await orchestrator_graph.ainvoke({"request": p})
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        flag = " [FLAG > 2s]" if elapsed > 2.0 else ""
        print(f"Request {i} elapsed: {elapsed:.2f}s{flag}")
        
    return times

async def test_b_concurrency(single_avg_time):
    print("\n--- Test B: Concurrency test ---")
    start = time.perf_counter()
    tasks = [orchestrator_graph.ainvoke({"request": whatsapp_emergency}) for _ in range(5)]
    await asyncio.gather(*tasks)
    total_elapsed = time.perf_counter() - start
    
    sequential_time = single_avg_time * 5
    print(f"Total time for 5 concurrent requests: {total_elapsed:.2f}s")
    print(f"Time if run sequentially (5x single): {sequential_time:.2f}s")
    
async def test_c_fallback():
    print("\n--- Test C: Forced failure / fallback test ---")
    real_api_key = os.environ.get("GROQ_API_KEY", "")
    os.environ["GROQ_API_KEY"] = "gsk_invalid_key_for_testing"
    
    try:
        result = await orchestrator_graph.ainvoke({"request": whatsapp_emergency})
        response = result.get("response")
        print(f"Urgency: {response.urgency}")
        print(f"Action Taken: {response.action_taken}")
    finally:
        os.environ["GROQ_API_KEY"] = real_api_key

async def test_d_consistency():
    print("\n--- Test D: Entity key consistency ---")
    keys_list = []
    for i in range(5):
        result = await orchestrator_graph.ainvoke({"request": whatsapp_emergency})
        keys = list(result.get("response").extracted_entities.keys())
        keys.sort()
        keys_list.append(keys)
        print(f"Run {i+1} keys: {keys}")
    
    all_identical = all(k == keys_list[0] for k in keys_list)
    print(f"Keys are identical across 5 runs: {all_identical}")

async def main():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    times = await test_a_latency()
    avg_time = sum(times) / len(times)
    
    await test_b_concurrency(avg_time)
    await test_c_fallback()
    await test_d_consistency()

if __name__ == "__main__":
    asyncio.run(main())
