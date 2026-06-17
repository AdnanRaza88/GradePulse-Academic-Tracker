import httpx
import os
from dotenv import load_dotenv
load_dotenv()
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
def api_get(endpoint):
    response = httpx.get(f"{API_BASE}{endpoint}")
    response.raise_for_status()
    return response.json()
def api_post(endpoint, json_data=None, files=None):
    if files:
        response = httpx.post(f"{API_BASE}{endpoint}", files=files)
    else:
        response = httpx.post(f"{API_BASE}{endpoint}", json=json_data)
    response.raise_for_status()
    return response.json()
def api_put(endpoint, json_data):
    response = httpx.put(f"{API_BASE}{endpoint}", json=json_data)
    response.raise_for_status()
    return response.json()
def api_delete(endpoint):
    response = httpx.delete(f"{API_BASE}{endpoint}")
    response.raise_for_status()
    return response.json()