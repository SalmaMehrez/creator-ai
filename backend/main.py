from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from anthropic import Anthropic
import json
import ai_service
import os

app = FastAPI(title="Creator AI API")

# Configure Anthropic client
client = Anthropic(api_key=ai_service.ANTHROPIC_API_KEY)
# Claude 3.5 Haiku is the best balance of speed and cost
MODEL = "claude-3-haiku-20240307"

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
        # Build system prompt from ai_service template
        system_prompt = ai_service.INTERVIEW_PROMPT.format(
            title=request.title,
            context=request.context
        )
        
        # Convert custom Message format to Anthropic format
        messages = []
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=messages
        )
        return {"reply": response.content[0].text}
    except Exception as e:
        print(f"Chat API Error: {e}")
        last_msg = request.history[-1].content if request.history else ""
        return {"reply": f"Noted! You said: '{last_msg}'. Any more details to add? (API Error)"}

@app.post("/api/generate_structure")
async def generate_structure(request: StructureRequest):
    try:
        # Convert custom Message format to Anthropic format
        messages = []
        for msg in request.history:
            messages.append({"role": msg.role, "content": msg.content})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1000,
            system=ai_service.STRUCTURE_PROMPT,
            messages=messages
        )
        structure_text = response.content[0].text
        
        # Anthropic might wrap the JSON in markdown blocks, so clean it
        if structure_text.startswith("```json"):
            structure_text = structure_text.split("```json")[1]
        if structure_text.endswith("```"):
            structure_text = structure_text.rsplit("```", 1)[0]
        structure_text = structure_text.strip()
            
        structure = json.loads(structure_text)
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

        response = client.messages.create(
            model=MODEL,
            max_tokens=2500,
            system=ai_service.SCRIPT_PROMPT,
            messages=[
                {"role": "user", "content": structure_text}
            ]
        )
        return {"script": response.content[0].text}
        
    except Exception as e:
        print(f"Script API Error: {e}")
        script_text = ""
        for sec in request.structure:
            script_text += f"[{sec['title']}]\nGenerated text for {sec['content']}...\n\n"
        return {"script": script_text}

@app.post("/api/generate_visuals")
async def generate_visuals(request: VisualsRequest):
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=3000,
            system=ai_service.VISUALS_PROMPT,
            messages=[
                {"role": "user", "content": request.script}
            ]
        )
        return {"script_with_visuals": response.content[0].text}
        
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
