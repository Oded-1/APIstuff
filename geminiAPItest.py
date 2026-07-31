import requests
import os
from google import genai


#
# os.environ.get("GEMINI_API_KEY")

# url = "https://generativelanguage.googleapis.com/v1beta/interactions"
# h = {"x-goog-api-key": os.getenv("GEMINI_API_KEY"), 
#         "Content-Type": "application/json"}
# d = {"model": "gemini-3.5-flash-lite",
#         "input": "fun and intresting quantum mechanics fact with explaination"}

# answer = requests.post(url, headers=h, json=d)
# print(answer.json()) 
question = input("Ask something: ")

client = genai.Client()  # automatically reads GEMINI_API_KEY from your environment
interaction = client.interactions.create(
    model="gemini-3.5-flash-lite",
    input=question #"fun and intresting quantum mechanics fact with explaination"
)
print(interaction.output_text)