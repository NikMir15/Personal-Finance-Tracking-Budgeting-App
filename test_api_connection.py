"""
Quick test to verify API connectivity and identify the issue.
"""

import requests
import json

def test_api_connection():
    """Test API endpoints on different ports."""
    
    ports = [8000, 8001]
    endpoints = ['/auth/me', '/expenses/', '/budgets/', '/analytics/dashboard']
    
    print("🔍 Testing API Connection")
    print("=" * 50)
    
    for port in ports:
        print(f"\n📡 Testing port {port}:")
        base_url = f"http://localhost:{port}"
        
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                status = "✅" if response.status_code in [200, 401] else "❌"
                print(f"  {status} {endpoint}: {response.status_code}")
                
                if response.status_code == 401:
                    print(f"    ℹ️  Expected 401 (authentication required)")
                elif response.status_code == 200:
                    print(f"    ✅ Endpoint working!")
                    
            except requests.exceptions.ConnectTimeout:
                print(f"  ⏱️  {endpoint}: Connection timeout")
            except requests.exceptions.ConnectionError:
                print(f"  🔌 {endpoint}: Connection refused")
            except Exception as e:
                print(f"  ❌ {endpoint}: {str(e)}")
    
    print(f"\n🎯 Recommendations:")
    print(f"1. Use the port where endpoints return 200/401 status")
    print(f"2. If using port 8001, access: http://localhost:8001")
    print(f"3. Check browser console for detailed error messages")
    print(f"4. Ensure you're logged in to test authenticated endpoints")

if __name__ == "__main__":
    test_api_connection()
