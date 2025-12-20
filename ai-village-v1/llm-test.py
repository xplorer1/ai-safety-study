import requests
import json

url = "http://localhost:11434/api/generate"

payload = {
    "model": "mistral",
    "prompt": "Explain what an AI Village is in simple terms.",
    "stream": False
}

response = requests.post(url, json=payload)

print(response.json()["response"])