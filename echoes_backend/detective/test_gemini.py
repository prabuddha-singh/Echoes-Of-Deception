
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-3.6-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.7,
    timeout=60,
    max_retries=1,
)

response = llm.invoke("Reply with exactly: Gemini connection successful")

if isinstance(response.content, str):
    print(response.content)
else:
    for block in response.content:
        if isinstance(block, dict) and block.get("type") == "text":
            print(block.get("text", ""), end="")
    print()
