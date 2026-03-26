# chat_server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq

client = Groq(api_key="")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# To start chat_server, open up a separate terminal, open venv and run: uvicorn chat_server:app --port 8000

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(req: ChatRequest):
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a helpful assistant embedded in an AI Deepfake Detector app. Help users understand deepfake detection and interpret results. Keep answers concise and friendly."
            },
            {
                "role": "user",
                "content": req.message
            }
        ]
    )
    return {"reply": response.choices[0].message.content}