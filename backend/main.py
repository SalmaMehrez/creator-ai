from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from google import genai
from google.genai import types
import json
import ai_service
import os

app = FastAPI(title="Creator AI API")

# Configure Gemini with new SDK
client = genai.Client(api_key=ai_service.GEMINI_API_KEY)
MODEL = "models/gemini-2.0-flash"

# CORS middleware for local testing
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    title: str
    context: str
    history: List[Message]
    
class StructureRequest(BaseModel):
    history: List[Message]
    
class ScriptRequest(BaseModel):
    structure: List[dict]

class VisualsRequest(BaseModel):
    script: str

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest):
    try:
        # Build full prompt as a single string
        prompt = ai_service.INTERVIEW_PROMPT.format(
            title=request.title,
            context=request.context
        )
        for msg in request.history:
            role_prefix = "Creator:" if msg.role == "user" else "AI:"
            prompt += f"\n{role_prefix} {msg.content}"
        prompt += "\nAI:"

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return {"reply": response.text}
    except Exception as e:
        print(f"Chat API Error: {e}")
        last_msg = request.history[-1].content if request.history else ""
        return {"reply": f"Noted! You said: '{last_msg}'. Any more details to add? (API Error)"}

@app.post("/api/generate_structure")
async def generate_structure(request: StructureRequest):
    try:
        prompt = ai_service.STRUCTURE_PROMPT + "\n\nConversation:\n"
        for msg in request.history:
            role_prefix = "Creator:" if msg.role == "user" else "AI:"
            prompt += f"{role_prefix} {msg.content}\n"

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        structure = json.loads(response.text)
        return {"structure": structure}
        
    except Exception as e:
        print(f"Structure API Error: {e}")
        return {
            "structure": [
                {"title": "🎬 Hook (0:00 - 0:15)", "content": "Strong hook based on discussion."},
                {"title": "👋 Introduction (0:15 - 0:45)", "content": "Quick intro and video promise."},
                {"title": "📖 Body - Part 1", "content": "First main point with example."},
                {"title": "🧠 Body - Part 2", "content": "Second point and deep dive."},
                {"title": "🎯 Conclusion & CTA", "content": "Final call to action."}
            ]
        }

@app.post("/api/generate_script")
async def generate_script(request: ScriptRequest):
    try:
        structure_text = ""
        for sec in request.structure:
            structure_text += f"Section: {sec['title']}\nContent: {sec['content']}\n\n"

        prompt = ai_service.SCRIPT_PROMPT + "\n\n" + structure_text

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return {"script": response.text}
        
    except Exception as e:
        print(f"Script API Error: {e}")
        script_text = ""
        for sec in request.structure:
            script_text += f"[{sec['title']}]\nGenerated text for {sec['content']}...\n\n"
        return {"script": script_text}

@app.post("/api/generate_visuals")
async def generate_visuals(request: VisualsRequest):
    try:
        prompt = ai_service.VISUALS_PROMPT + "\n\nHere is the script:\n\n" + request.script

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )
        return {"script_with_visuals": response.text}
        
    except Exception as e:
        print(f"Visuals API Error: {e}")
        return {"script_with_visuals": "[B-Roll: Example visual idea]\n" + request.script}

# Serve frontend static files
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
print(f"Serving frontend from: {frontend_dir}")


from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
