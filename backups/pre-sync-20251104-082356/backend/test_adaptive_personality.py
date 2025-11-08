"""
Test script for Adaptive Personality System
Tests mood detection and style mirroring with various user inputs
"""

from typing import Dict

import requests

API_URL = "http://127.0.0.1:8001/api/v1/route"


def test_chat(prompt: str, description: str = "") -> Dict:
    """Send a chat request to the API"""
    payload = {"task_type": "chat", "prompt": prompt, "context": ""}

    print(f"\n{'='*80}")
    print(f"TEST: {description}")
    print(f"{'='*80}")
    print(f"User Input: '{prompt}'")
    print(f"Length: {len(prompt.split())} words")
    print(f"{'-'*80}")

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        print(f"AI Response: {result.get('text', 'No response')}")
        print(f"Verified: {result.get('verified', False)}")
        print(f"{'='*80}\n")

        return result
    except Exception as e:
        print(f"ERROR: {e}")
        print(f"{'='*80}\n")
        return {"error": str(e)}


def main():
    print("\n🎭 ADAPTIVE PERSONALITY SYSTEM - TEST SUITE")
    print("=" * 80)

    # Test 1: Short & Casual (expect 1-2 sentences, friendly)
    test_chat("hi", "Short & Casual Input")

    # Test 2: Frustrated User (expect supportive, patient response)
    test_chat(
        "This is broken! I've been stuck on this error for hours damn it",
        "Frustrated User - Expects Empathy",
    )

    # Test 3: Stressed User (expect calm, efficient, direct)
    test_chat(
        "Need this fixed ASAP, critical deadline tomorrow",
        "Stressed User - Expects Quick Solution",
    )

    # Test 4: Happy User (expect enthusiastic, positive)
    test_chat("Thanks so much! This works great!", "Happy User - Match Positive Energy")

    # Test 5: Excited User (expect energetic, build momentum)
    test_chat(
        "This is amazing! I can't wait to implement this feature!",
        "Excited User - Match Enthusiasm",
    )

    # Test 6: Long Formal Request (expect 3-5 sentences, professional)
    test_chat(
        "Could you please explain the difference between async and await in Python? "
        "I would like to understand when to use each one and what the performance "
        "implications are for my application.",
        "Long Formal Request - Expects Detailed Professional Response",
    )

    # Test 7: Technical Question (expect technical, minimal fluff)
    test_chat(
        "what's the time complexity of dict lookup in python",
        "Technical Question - Expects Concise Technical Answer",
    )

    # Test 8: Medium Prompt (expect 2-4 sentences, balanced)
    test_chat(
        "How do I handle exceptions in async functions?",
        "Medium Prompt - Expects Balanced Response",
    )

    print("\n✅ Test suite completed!")


if __name__ == "__main__":
    main()
