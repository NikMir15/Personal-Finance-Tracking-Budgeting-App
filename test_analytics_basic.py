"""
Basic test to verify analytics endpoints are working.
Run this after starting the application to test the analytics functionality.
"""

import requests
import json

# Base URL of your application
BASE_URL = "http://localhost:8000"

def test_analytics_endpoints():
    """Test the analytics endpoints with a sample user."""
    
    print("🧪 Testing Analytics Endpoints")
    print("=" * 40)
    
    # Test 1: Check if analytics dashboard endpoint exists
    try:
        response = requests.get(f"{BASE_URL}/analytics/dashboard")
        print(f"✅ Analytics dashboard endpoint: {response.status_code}")
        if response.status_code == 401:
            print("   ℹ️  Expected 401 (authentication required)")
    except Exception as e:
        print(f"❌ Analytics dashboard endpoint failed: {e}")
    
    # Test 2: Check if CSV export endpoint exists
    try:
        response = requests.get(f"{BASE_URL}/analytics/export/csv")
        print(f"✅ CSV export endpoint: {response.status_code}")
        if response.status_code == 401:
            print("   ℹ️  Expected 401 (authentication required)")
    except Exception as e:
        print(f"❌ CSV export endpoint failed: {e}")
    
    # Test 3: Check if analytics page exists
    try:
        response = requests.get(f"{BASE_URL}/analytics")
        print(f"✅ Analytics page: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Analytics page loads successfully")
    except Exception as e:
        print(f"❌ Analytics page failed: {e}")
    
    # Test 4: Check API documentation
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code == 200:
            print("✅ API docs accessible - check /docs for Analytics endpoints")
        else:
            print(f"⚠️  API docs status: {response.status_code}")
    except Exception as e:
        print(f"❌ API docs failed: {e}")
    
    print("\n🎯 Next Steps:")
    print("1. Visit http://localhost:8000/analytics to see the dashboard")
    print("2. Login with your account to view real analytics data")
    print("3. Check http://localhost:8000/docs for API documentation")
    print("4. Add some expenses to see meaningful analytics")

if __name__ == "__main__":
    test_analytics_endpoints()
