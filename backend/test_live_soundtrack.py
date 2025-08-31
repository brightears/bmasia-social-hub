#!/usr/bin/env python3
"""
Test live Soundtrack API integration on deployed service
This script can be run as an endpoint to test the API
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_soundtrack_api_live() -> Dict[str, Any]:
    """Test Soundtrack API integration on live service"""
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0
        }
    }
    
    def add_test(name: str, success: bool, details: str, error: str = None):
        results["tests"].append({
            "name": name,
            "success": success,
            "details": details,
            "error": error
        })
        results["summary"]["total"] += 1
        if success:
            results["summary"]["passed"] += 1
        else:
            results["summary"]["failed"] += 1
    
    # Test 1: Check environment variables
    try:
        base_url = os.getenv('SOUNDTRACK_BASE_URL', 'https://api.soundtrackyourbrand.com/v2')
        api_credentials = os.getenv('SOUNDTRACK_API_CREDENTIALS')
        client_id = os.getenv('SOUNDTRACK_CLIENT_ID')
        client_secret = os.getenv('SOUNDTRACK_CLIENT_SECRET')
        
        has_credentials = bool(api_credentials or (client_id and client_secret))
        
        add_test(
            "Environment Variables",
            has_credentials,
            f"Base URL: {base_url}, Credentials configured: {has_credentials}",
            None if has_credentials else "No API credentials found"
        )
        
    except Exception as e:
        add_test("Environment Variables", False, "Failed to check environment", str(e))
        return results
    
    # Test 2: Import Soundtrack API
    try:
        from soundtrack_api import soundtrack_api
        add_test("Import Soundtrack API", True, "Successfully imported soundtrack_api module", None)
    except Exception as e:
        add_test("Import Soundtrack API", False, "Failed to import", str(e))
        return results
    
    # Test 3: Test API connection (if credentials available)
    if has_credentials:
        try:
            # Test getting accounts
            accounts = soundtrack_api.get_accounts()
            
            if isinstance(accounts, list):
                account_count = len(accounts)
                add_test(
                    "API Connection", 
                    True, 
                    f"Successfully retrieved {account_count} accounts"
                )
                
                # Test 4: Test venue search
                if account_count > 0:
                    try:
                        matches = soundtrack_api.find_matching_accounts("Hilton")
                        match_count = len(matches) if isinstance(matches, list) else 0
                        add_test(
                            "Venue Search",
                            True,
                            f"Found {match_count} matches for 'Hilton'"
                        )
                    except Exception as e:
                        add_test("Venue Search", False, "Search failed", str(e))
            else:
                add_test(
                    "API Connection", 
                    False, 
                    f"API returned non-list: {type(accounts)}", 
                    str(accounts) if isinstance(accounts, dict) and 'error' in accounts else None
                )
                
        except Exception as e:
            add_test("API Connection", False, "Connection failed", str(e))
    else:
        add_test("API Connection", False, "Skipped - no credentials", "API credentials not configured")
    
    # Test 5: Test bot integration
    try:
        from bot_soundtrack import soundtrack_bot
        
        # Test basic message processing
        test_response = soundtrack_bot.process_message(
            "I am from Millennium Hilton Bangkok, can you check our zones?",
            "+6012345678",
            "Test User"
        )
        
        response_ok = isinstance(test_response, str) and len(test_response) > 0
        add_test(
            "Bot Integration",
            response_ok,
            f"Bot response generated (length: {len(test_response) if response_ok else 0})",
            None if response_ok else "No response generated"
        )
        
    except Exception as e:
        add_test("Bot Integration", False, "Bot test failed", str(e))
    
    # Test 6: Test webhook system
    try:
        from webhooks_simple import BOT_ENABLED, bot
        webhook_ok = BOT_ENABLED and bot is not None
        add_test(
            "Webhook Integration",
            webhook_ok,
            f"Webhook system enabled: {BOT_ENABLED}, Bot loaded: {bot is not None}",
            None if webhook_ok else "Bot not properly loaded in webhook system"
        )
    except Exception as e:
        add_test("Webhook Integration", False, "Webhook test failed", str(e))
    
    return results

def generate_test_report(results: Dict[str, Any]) -> str:
    """Generate a formatted test report"""
    
    report = ["=== SOUNDTRACK API INTEGRATION TEST REPORT ===\n"]
    report.append(f"Timestamp: {results['timestamp']}")
    report.append(f"Total Tests: {results['summary']['total']}")
    report.append(f"Passed: {results['summary']['passed']} ✅")
    report.append(f"Failed: {results['summary']['failed']} ❌")
    report.append(f"Success Rate: {(results['summary']['passed'] / max(results['summary']['total'], 1) * 100):.1f}%")
    report.append("\n" + "="*50 + "\n")
    
    for test in results["tests"]:
        status = "✅ PASS" if test["success"] else "❌ FAIL"
        report.append(f"{status} | {test['name']}")
        report.append(f"         {test['details']}")
        if test["error"]:
            report.append(f"         ERROR: {test['error']}")
        report.append("")
    
    report.append("="*50)
    report.append("RECOMMENDATIONS:")
    report.append("")
    
    # Add recommendations based on results
    failed_tests = [t for t in results["tests"] if not t["success"]]
    
    if any("Environment Variables" in t["name"] for t in failed_tests):
        report.append("🔧 Configure Soundtrack API credentials in Render environment variables:")
        report.append("   - SOUNDTRACK_API_CREDENTIALS (base64 encoded)")
        report.append("   - OR SOUNDTRACK_CLIENT_ID and SOUNDTRACK_CLIENT_SECRET")
        report.append("")
    
    if any("API Connection" in t["name"] for t in failed_tests):
        report.append("🔧 Check API connectivity:")
        report.append("   - Verify credentials are correct")
        report.append("   - Check if Soundtrack API is accessible")
        report.append("   - Review API endpoint URL")
        report.append("")
    
    if results["summary"]["passed"] == results["summary"]["total"]:
        report.append("🎉 All tests passed! The Soundtrack integration is working correctly.")
    
    return "\n".join(report)

if __name__ == "__main__":
    # Run tests
    results = test_soundtrack_api_live()
    
    # Generate and print report
    report = generate_test_report(results)
    print(report)
    
    # Also save results as JSON for potential API use
    with open('/tmp/soundtrack_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)