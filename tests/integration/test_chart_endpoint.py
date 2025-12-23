import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_chart(symbol, period):
    print(f"Testing chart for {symbol} with period {period}...")
    try:
        response = requests.get(f"{BASE_URL}/crypto/{symbol}/chart", params={"period": period})
        if response.status_code == 200:
            data = response.json()
            prices = data.get("prices", [])
            print(f"✅ Success! Received {len(prices)} data points.")
            if len(prices) > 0:
                print(f"   First point: {prices[0]}")
                print(f"   Last point: {prices[-1]}")
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_chart("BTC", "1h")
    test_chart("BTC", "24h")
    test_chart("BTC", "7d")
    test_chart("BTC", "30d")
