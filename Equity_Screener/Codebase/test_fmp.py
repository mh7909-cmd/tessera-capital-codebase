import requests

API_KEY = "tW3H8UXqZxm87wyt4YeJ1jJI4XPnNf4y"  # Replace with your actual key

# Test S&P 500 endpoint
url = f"https://financialmodelingprep.com/api/v4/sp500_constituent?apikey={API_KEY}"
response = requests.get(url)

print("Status Code:", response.status_code)
print("\nResponse:")
print(response.text[:500])  # First 500 characters

# Parse as JSON
try:
    data = response.json()
    print("\nData type:", type(data))
    if isinstance(data, list) and len(data) > 0:
        print("First item:", data[0])
        print("Keys:", data[0].keys() if isinstance(data[0], dict) else "Not a dict")
except Exception as e:
    print("Error:", e)
