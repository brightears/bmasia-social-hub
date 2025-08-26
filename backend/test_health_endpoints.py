#!/usr/bin/env python3
"""
Test script to verify health check endpoints are working correctly
"""

import requests
import time
import sys
from typing import Dict, Any

def test_endpoint(url: str, endpoint: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test a single endpoint"""
    full_url = f"{url}{endpoint}"
    try:
        start_time = time.time()
        response = requests.get(full_url, timeout=5)
        duration = time.time() - start_time
        
        result = {
            "endpoint": endpoint,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2),
            "success": response.status_code == expected_status,
            "response": response.json() if response.status_code == 200 else None,
            "error": None
        }
        
        print(f"✓ {endpoint}: {response.status_code} ({duration:.3f}s)")
        if response.status_code == 200:
            print(f"  Response: {response.json()}")
        
    except requests.exceptions.Timeout:
        result = {
            "endpoint": endpoint,
            "status_code": None,
            "duration_ms": 5000,
            "success": False,
            "response": None,
            "error": "Timeout after 5 seconds"
        }
        print(f"✗ {endpoint}: TIMEOUT")
    except Exception as e:
        result = {
            "endpoint": endpoint,
            "status_code": None,
            "duration_ms": None,
            "success": False,
            "response": None,
            "error": str(e)
        }
        print(f"✗ {endpoint}: ERROR - {e}")
    
    return result

def main():
    # Get the base URL from command line or use default
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    print(f"\nTesting health endpoints at {base_url}")
    print("=" * 50)
    
    # Define endpoints to test
    endpoints = [
        ("/health", 200, "Basic health check (Render uses this)"),
        ("/health/live", 200, "Liveness check"),
        ("/ready", 200, "Readiness check"),
        ("/health/detailed", 200, "Detailed health check"),
    ]
    
    results = []
    
    for endpoint, expected_status, description in endpoints:
        print(f"\nTesting: {description}")
        result = test_endpoint(base_url, endpoint, expected_status)
        results.append(result)
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    
    all_passed = all(r["success"] for r in results)
    critical_passed = results[0]["success"]  # /health endpoint is critical for Render
    
    print(f"Total endpoints tested: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['success'])}")
    
    if critical_passed:
        print("\n✓ CRITICAL: /health endpoint is working (required for Render)")
        print("  Response time: {:.2f}ms".format(results[0]["duration_ms"]))
    else:
        print("\n✗ CRITICAL: /health endpoint is NOT working (Render will fail)")
        if results[0]["error"]:
            print(f"  Error: {results[0]['error']}")
    
    # Performance check
    health_duration = results[0]["duration_ms"] if results[0]["duration_ms"] else 0
    if health_duration > 0 and health_duration < 1000:
        print(f"✓ Performance: /health responds in {health_duration}ms (< 1 second)")
    elif health_duration > 0:
        print(f"⚠ Performance: /health took {health_duration}ms (should be < 1 second)")
    
    return 0 if critical_passed else 1

if __name__ == "__main__":
    sys.exit(main())