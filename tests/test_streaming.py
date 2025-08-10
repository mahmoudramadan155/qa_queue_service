#!/usr/bin/env python3
"""
Test script for streaming functionality
"""

import asyncio
import json
import aiohttp
import sys

API_BASE = "http://localhost:8000"

async def test_streaming():
    """Test the streaming endpoint"""
    
    # First, you need to authenticate and get a token
    print("🔐 Please ensure you have a valid auth token from the web interface")
    token = input("Enter your auth token: ").strip()
    
    if not token:
        print("❌ No token provided. Please get a token from the web interface first.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    question = input("Enter your question: ").strip()
    if not question:
        question = "What is this document about?"
    
    print(f"\n🤖 Asking: {question}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE}/qa/ask/stream",
                headers=headers,
                json={"question": question}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return
                
                print("📡 Streaming response:")
                print("-" * 30)
                
                full_answer = ""
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])  # Remove 'data: ' prefix
                            
                            if data['type'] == 'status':
                                print(f"⏳ Status: {data['message']}")
                            
                            elif data['type'] == 'chunk':
                                content = data['content']
                                print(content, end='', flush=True)
                                full_answer += content
                            
                            elif data['type'] == 'complete':
                                print(f"\n\n✅ Complete! Response time: {data['response_time']}ms")
                            
                            elif data['type'] == 'error':
                                print(f"\n❌ Error: {data['message']}")
                                break
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Failed to parse JSON: {e}")
                            continue
                
                print(f"\n\n📝 Full answer length: {len(full_answer)} characters")
                
        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

async def test_regular_endpoint():
    """Test the regular (non-streaming) endpoint for comparison"""
    
    print("🔐 Please ensure you have a valid auth token from the web interface")
    token = input("Enter your auth token: ").strip()
    
    if not token:
        print("❌ No token provided. Please get a token from the web interface first.")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    question = input("Enter your question: ").strip()
    if not question:
        question = "What is this document about?"
    
    print(f"\n🤖 Asking (regular): {question}")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                f"{API_BASE}/qa/ask",
                headers=headers,
                json={"question": question}
            ) as response:
                
                if response.status != 200:
                    error_text = await response.text()
                    print(f"❌ Error {response.status}: {error_text}")
                    return
                
                data = await response.json()
                print(f"📝 Answer: {data['answer']}")
                print(f"⏱️ Response time: {data['response_time_ms']}ms")
                
        except aiohttp.ClientError as e:
            print(f"❌ Connection error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

def main():
    """Main function"""
    print("🧪 AI QA Service - Streaming Test")
    print("=" * 40)
    
    choice = input("Choose test type:\n1. Streaming response\n2. Regular response\n3. Both\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(test_streaming())
    elif choice == "2":
        asyncio.run(test_regular_endpoint())
    elif choice == "3":
        print("\n--- Testing Regular Endpoint ---")
        asyncio.run(test_regular_endpoint())
        print("\n--- Testing Streaming Endpoint ---")
        asyncio.run(test_streaming())
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
