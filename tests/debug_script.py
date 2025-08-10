#!/usr/bin/env python3
"""
Debug script to test the FastAPI server
"""

import requests
import sys
import json

BASE_URL = "http://localhost:8000"

def test_endpoint(url, description):
    """Test an endpoint and print results"""
    print(f"\n🔍 Testing {description}: {url}")
    try:
        response = requests.get(url, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            # Try to parse as JSON
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response (HTML): {response.text[:100]}...")
        else:
            print(f"   Error: {response.text[:100]}")
            
    except requests.exceptions.ConnectionError:
        print("   ❌ CONNECTION ERROR - Server is not running!")
        return False
    except requests.exceptions.Timeout:
        print("   ⏰ TIMEOUT - Server is not responding!")
        return False
    except Exception as e:
        print(f"   ❌ ERROR: {str(e)}")
        return False
    
    return True

def main():
    print("🚀 FastAPI Server Debug Tool")
    print("=" * 50)
    
    # Test basic connectivity
    if not test_endpoint(f"{BASE_URL}/health", "Health Check"):
        print("\n❌ Server is not running. Please start it with:")
        print("   python -m uvicorn app.main:app --reload")
        sys.exit(1)
    
    # Test all important endpoints
    endpoints = [
        ("/", "Root Page"),
        ("/docs", "Swagger UI"),
        ("/redoc", "ReDoc"),
        ("/openapi.json", "OpenAPI Spec"),
        ("/test", "Test Endpoint"),
    ]
    
    for path, desc in endpoints:
        test_endpoint(f"{BASE_URL}{path}", desc)
    
    print("\n" + "=" * 50)
    print("✅ Debug complete!")
    print("\n📚 If /docs is working, open this URL in your browser:")
    print(f"   {BASE_URL}/docs")

if __name__ == "__main__":
    main()
    