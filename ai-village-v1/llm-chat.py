import requests

URL = "http://localhost:11434/api/generate"

conversation = []

def chat(user_input):
    conversation.append(f"User: {user_input}")

    prompt = "\n".join(conversation) + "\nAssistant:"

    payload = {
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(URL, json=payload).json()["response"]

    conversation.append(f"Assistant: {response}")

    return response


# --- Interactive loop ---
print("AI Village Chat (type 'exit' to quit)\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        break

    reply = chat(user_input)
    print("AI:", reply)
