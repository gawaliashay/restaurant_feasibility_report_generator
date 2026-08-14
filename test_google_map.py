import requests

API_KEY = "5c4762cf5efd004813297b196031900eb0a342b7dc959c5b2d586a49dd920592"

# Test 1: Try google_maps engine
params1 = {
    "engine": "google_maps",
    "q": "momo restaurants",
    "location": "Pune",
    "api_key": API_KEY,
}
r1 = requests.get("https://serpapi.com/search", params=params1)
print(f"google_maps: {r1.status_code}")

# Test 2: Try google_local engine
params2 = {
    "engine": "google_local",
    "q": "momo restaurants",
    "location": "Pune",
    "api_key": API_KEY,
}
r2 = requests.get("https://serpapi.com/search", params=params2)
print(f"google_local: {r2.status_code}")

# Test 3: Try with ll instead of location
params3 = {
    "engine": "google_local",
    "q": "momo restaurants",
    "ll": "@18.5204,73.8567,14z",
    "api_key": API_KEY,
}
r3 = requests.get("https://serpapi.com/search", params=params3)
print(f"google_local with ll: {r3.status_code}")

# Test 4: Try google_maps with just query
params4 = {
    "engine": "google_maps",
    "q": "momo restaurants Pune",
    "api_key": API_KEY,
}
r4 = requests.get("https://serpapi.com/search", params=params4)
print(f"google_maps no location: {r4.status_code}")