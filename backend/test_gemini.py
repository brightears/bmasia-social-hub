#!/usr/bin/env python3
"""
Quick test script for Gemini API integration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test Gemini import and configuration
try:
    import google.generativeai as genai
    print("✅ google-generativeai package installed")
except ImportError:
    print("❌ google-generativeai package not installed")
    print("Run: pip install google-generativeai")
    sys.exit(1)

# Get API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(f"API Key found: {'✅ Yes' if GEMINI_API_KEY and GEMINI_API_KEY != 'YOUR_GEMINI_API_KEY_HERE' else '❌ No'}")

if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("❌ No valid Gemini API key found in .env")
    sys.exit(1)

# Configure Gemini
try:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    print("✅ Gemini configured successfully")
except Exception as e:
    print(f"❌ Failed to configure Gemini: {e}")
    sys.exit(1)

# Test with a sample query
print("\n🤖 Testing Gemini AI with a venue support query...")
print("-" * 50)

test_message = "The music stopped playing in our restaurant. What should I check?"

try:
    prompt = """You are BMA Social AI Assistant, helping venue staff with their music systems.
    You support venues using Soundtrack Your Brand music players.
    
    Keep responses concise and helpful. Focus on practical troubleshooting steps.
    
    User message: """ + test_message
    
    response = model.generate_content(prompt)
    
    print(f"User: {test_message}")
    print(f"\nBot Response:\n{response.text}")
    print("-" * 50)
    print("✅ Gemini API test successful!")
    
except Exception as e:
    print(f"❌ Error generating response: {e}")
    sys.exit(1)

print("\n✅ All tests passed! Gemini is ready to use.")