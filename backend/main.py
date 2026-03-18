from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from huggingface_hub import InferenceClient
import json
import ai_service
import os

app = FastAPI(title="Creator AI API")

# Configure HuggingFace client
# Using Mistral Nemo which is consistently available on the free API
client = InferenceClient(
    model="mistralai/Mistral-Nemo-Instruct-2407",
    token=ai_service.HUGGINGFACE_API_KEY
)

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
        # Convert custom Message format to standard LLM format
        messages = [
            {"role": "system", "content": ai_service.INTERVIEW_PROMPT.format(
                title=request.title,
                context=request.context
            )}
        ]
        for msg in request.history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        # HuggingFace chat completion
        response = client.chat_completion(
            messages=messages,
            max_tokens=500
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        print(f"Chat API Error: {str(e)}")
        import traceback
        return {"reply": f"API Error Encountered: {str(e)}\n\nTraceback: {traceback.format_exc()}"}

@app.post("/api/generate_structure")
async def generate_structure(request: StructureRequest):
    try:
        messages = [
            {"role": "system", "content": ai_service.STRUCTURE_PROMPT}
        ]
        for msg in request.history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        response = client.chat_completion(
            messages=messages,
            max_tokens=1000
        )
        structure_text = response.choices[0].message.content
        
        # HuggingFace returns JSON string but might wrap it in markdown block. Clean it.
        if "```json" in structure_text:
            structure_text = structure_text.split("```json")[1].split("```")[0]
        elif "```" in structure_text:
             structure_text = structure_text.split("```")[1].split("```")[0]
        structure_text = structure_text.strip()
            
        structure = json.loads(structure_text)
        return {"structure": structure}
        
    except Exception as e:
        print(f"Structure API Error: {str(e)}")
        import traceback
        return {"structure": [
            {"title": f"API Error: {str(e)}", "content": traceback.format_exc()}
        ]}

@app.post("/api/generate_script")
async def generate_script(request: ScriptRequest):
    try:
        structure_text = ""
        for sec in request.structure:
            structure_text += f"Section: {sec['title']}\nContent: {sec['content']}\n\n"

        response = client.chat_completion(
            messages=[
                {"role": "system", "content": ai_service.SCRIPT_PROMPT},
                {"role": "user", "content": structure_text}
            ],
            max_tokens=2500
        )
        return {"script": response.choices[0].message.content}
        
    except Exception as e:
        print(f"Script API Error: {str(e)}")
        import traceback
        return {"script": f"API Error: {str(e)}\n\nTraceback: {traceback.format_exc()}"}

@app.post("/api/generate_visuals")
async def generate_visuals(request: VisualsRequest):
    try:
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": ai_service.VISUALS_PROMPT},
                {"role": "user", "content": request.script}
            ],
            max_tokens=3000
        )
        return {"script_with_visuals": response.choices[0].message.content}
        
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
