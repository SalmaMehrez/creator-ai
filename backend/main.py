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
    model="Qwen/Qwen2.5-72B-Instruct",
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
    duration_minutes: Optional[float] = 5.0

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
    messages = [
        {"role": "system", "content": ai_service.STRUCTURE_PROMPT}
    ]
    for msg in request.history:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.content})

    # Retry up to 3 times
    last_error = None
    for attempt in range(3):
        try:
            response = client.chat_completion(
                messages=messages,
                max_tokens=1200
            )
            raw = response.choices[0].message.content or ""
            print(f"Structure attempt {attempt+1}, raw length: {len(raw)}")

            # Clean JSON from markdown code blocks if present
            structure_text = raw.strip()
            if "```json" in structure_text:
                structure_text = structure_text.split("```json")[1].split("```")[0].strip()
            elif "```" in structure_text:
                structure_text = structure_text.split("```")[1].split("```")[0].strip()

            # Find first [ ... ] JSON array in the response
            start = structure_text.find("[")
            end = structure_text.rfind("]")
            if start != -1 and end != -1:
                structure_text = structure_text[start:end+1]

            if not structure_text:
                raise ValueError("Empty response from model")

            structure = json.loads(structure_text)
            return {"structure": structure}

        except Exception as e:
            last_error = e
            print(f"Structure attempt {attempt+1} failed: {str(e)}")

    # Fallback structure if all retries fail
    print(f"All structure attempts failed: {last_error}")
    return {"structure": [
        {"title": "🎬 Hook", "content": "A strong opening statement to grab the viewer's attention immediately."},
        {"title": "👋 Introduction", "content": "Introduce yourself and the video topic. State what the viewer will learn."},
        {"title": "📖 Main Point 1", "content": "First key insight or step. Use a concrete example."},
        {"title": "💡 Main Point 2", "content": "Second key insight. Add a personal story or case study."},
        {"title": "🔄 Counter-intuitive Twist", "content": "Share a surprising or unexpected angle on the topic."},
        {"title": "🎯 Conclusion & CTA", "content": "Summarize the key takeaways and give a clear call to action."}
    ]}

@app.post("/api/generate_script")
async def generate_script(request: ScriptRequest):
    try:
        structure_text = ""
        for sec in request.structure:
            structure_text += f"Section: {sec['title']}\nContent: {sec['content']}\n\n"

        # Calculate required word count: ~140 words/minute average speaking pace
        target_words = int((request.duration_minutes or 5.0) * 150)
        duration_instruction = (
            f"TARGET: {request.duration_minutes}-minute video = {target_words} WORDS MINIMUM.\n"
            f"You MUST write at least {target_words} words. Count your words as you go.\n"
            f"Do NOT stop until you have written {target_words} words of spoken dialogue.\n"
            f"Expand every section with stories, examples, and detailed explanations.\n\n"
            f"HERE IS THE STRUCTURE TO FOLLOW:\n\n"
        )

        response = client.chat_completion(
            messages=[
                {"role": "system", "content": ai_service.SCRIPT_PROMPT},
                {"role": "user", "content": duration_instruction + structure_text}
            ],
            max_tokens=5000
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
