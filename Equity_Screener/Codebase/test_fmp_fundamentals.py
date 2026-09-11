import requests

API_KEY = "tW3H8UXqZxm87wyt4YeJ1jJI4XPnNf4y"  # Replace with your actual key
ticker = "AAPL"

# Test profile endpoint
print("Testing Profile endpoint:")
url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={API_KEY}"
response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}\n")

# Test key metrics endpoint
print("Testing Key Metrics endpoint:")
url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}?apikey={API_KEY}"
response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}\n")

# Test ratios endpoint
print("Testing Ratios endpoint:")
url = f"https://financialmodelingprep.com/api/v3/ratios-ttm/{ticker}?apikey={API_KEY}"
response = requests.get(url)
print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")
