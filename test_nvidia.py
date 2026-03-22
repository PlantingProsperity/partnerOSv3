import os
import asyncio
from src.utils import llm
import config

def test_nvidia_connection():
    print(f"Testing PRIMARY_PROVIDER: {config.PRIMARY_PROVIDER}")
    print(f"FAST_MODEL: {config.FAST_MODEL}")
    print(f"QUALITY_MODEL: {config.QUALITY_MODEL}")
    
    print("\n--- Testing Fast Model ---")
    try:
        response = llm.complete(
            prompt="Reply with the single word 'SUCCESS'.",
            tier="fast",
            agent="test_script"
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Fast Model Failed: {e}")

    print("\n--- Testing Quality Model ---")
    try:
        response = llm.complete(
            prompt="Reply with the single word 'SUCCESS'.",
            tier="quality",
            agent="test_script"
        )
        print(f"Response: {response}")
    except Exception as e:
        print(f"Quality Model Failed: {e}")

if __name__ == "__main__":
    test_nvidia_connection()