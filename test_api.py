#!/usr/bin/env python3
# =====================================================
# CRBOT - API Endpoints Test Script
# Test all endpoints with sample data
# =====================================================

import requests
import json
from typing import Dict, Any
import time

BASE_URL = "http://localhost:8000"

class APITester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
    
    def print_header(self, title: str):
        print(f"\n{'='*60}")
        print(f"🧪 {title}")
        print(f"{'='*60}\n")
    
    def test_endpoint(self, method: str, endpoint: str, expected_status: int = 200, **kwargs) -> bool:
        """Test an API endpoint"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url, **kwargs)
            elif method == "POST":
                response = self.session.post(url, **kwargs)
            elif method == "PUT":
                response = self.session.put(url, **kwargs)
            elif method == "DELETE":
                response = self.session.delete(url, **kwargs)
            else:
                print(f"❌ Unknown method: {method}")
                return False
            
            status_ok = response.status_code == expected_status
            status_symbol = "✅" if status_ok else "❌"
            
            print(f"{status_symbol} {method} {endpoint}")
            print(f"   Status: {response.status_code} (expected {expected_status})")
            
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            except:
                print(f"   Response: {response.text[:200]}...")
            
            self.results.append({
                "endpoint": f"{method} {endpoint}",
                "status": response.status_code,
                "success": status_ok
            })
            
            return status_ok
        
        except Exception as e:
            print(f"❌ {method} {endpoint}")
            print(f"   Error: {str(e)}")
            self.results.append({
                "endpoint": f"{method} {endpoint}",
                "error": str(e),
                "success": False
            })
            return False
    
    def print_summary(self):
        """Print test summary"""
        self.print_header("📊 TEST SUMMARY")
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get("success", False))
        failed = total - successful
        
        print(f"Total Tests:    {total}")
        print(f"✅ Successful:  {successful}")
        print(f"❌ Failed:      {failed}")
        print(f"Success Rate:   {(successful/total*100):.1f}%\n")
        
        if failed > 0:
            print("Failed Endpoints:")
            for result in self.results:
                if not result.get("success", False):
                    print(f"  • {result['endpoint']}")

def wait_for_server(url: str, timeout: int = 30) -> bool:
    """Wait for server to be ready"""
    print(f"⏳ Waiting for server at {url}...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{url}/")
            if response.status_code == 200:
                print(f"✅ Server is ready!\n")
                return True
        except:
            pass
        
        time.sleep(1)
    
    print(f"❌ Server did not respond within {timeout}s")
    return False

def main():
    print("\n" + "="*60)
    print("🚀 CRBOT API TEST SUITE")
    print("="*60)
    
    # Wait for server
    if not wait_for_server(BASE_URL):
        print("Cannot connect to API server. Make sure it's running:")
        print(f"  cd c:\\CRBot\\backend")
        print(f"  python -m uvicorn app.main:app --reload")
        return
    
    tester = APITester(BASE_URL)
    
    # ===================== HEALTH CHECKS =====================
    tester.print_header("🏥 HEALTH CHECKS")
    tester.test_endpoint("GET", "/", expected_status=200)
    tester.test_endpoint("GET", "/health", expected_status=200)
    
    # ===================== PORTFOLIO ENDPOINTS =====================
    tester.print_header("💼 PORTFOLIO ENDPOINTS")
    tester.test_endpoint("GET", "/api/portfolio/summary", expected_status=200)
    tester.test_endpoint("GET", "/api/trades", expected_status=200)
    tester.test_endpoint("GET", "/api/trades?limit=10&status=OPEN", expected_status=200)
    tester.test_endpoint("GET", "/api/portfolio/equity-curve?days=30", expected_status=200)
    
    # ===================== BOTS ENDPOINTS =====================
    tester.print_header("🤖 BOTS ENDPOINTS")
    tester.test_endpoint("GET", "/api/bots/list", expected_status=200)
    
    # Note: We don't have actual bot IDs yet, so we'll skip individual bot tests
    # tester.test_endpoint("GET", "/api/bots/bot_1", expected_status=200)
    # tester.test_endpoint("POST", "/api/bots/bot_1/start", expected_status=200)
    
    # ===================== REPORTS ENDPOINTS =====================
    tester.print_header("📊 REPORTS ENDPOINTS")
    tester.test_endpoint("GET", "/api/reports/dashboard", expected_status=200)
    tester.test_endpoint("GET", "/api/reports/trades", expected_status=200)
    tester.test_endpoint("GET", "/api/reports/trades?limit=10&days=7", expected_status=200)
    tester.test_endpoint("GET", "/api/reports/strategies", expected_status=200)
    tester.test_endpoint("GET", "/api/reports/performance", expected_status=200)
    
    # ===================== CRYPTO ENDPOINTS =====================
    tester.print_header("📈 CRYPTO ENDPOINTS")
    tester.test_endpoint("GET", "/api/crypto/prices", expected_status=200)
    tester.test_endpoint("GET", "/api/crypto/prices?symbol=BTC", expected_status=200)
    
    # ===================== SUMMARY =====================
    tester.print_summary()
    
    print("\n" + "="*60)
    print("✨ API DOCUMENTATION: http://localhost:8000/docs")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
