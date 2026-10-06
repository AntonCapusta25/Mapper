import sys
import os
from dotenv import load_dotenv
load_dotenv() # Load Telegram token and Gemini key from .env file
import asyncio
import uuid
import httpx
import shutil
import re
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scraper_events_fast
import llm_engine
from llm_engine import LLMEngine
import database
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException, Response, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json

# Global state for ML models and active scraper tasks
ml_models = {}
active_tasks: Dict[str, asyncio.Event] = {} # Stores task_id -> cancellation_event
active_task_info = {"id": None, "intent": None} # Stores current running task metadata

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the ML model on startup
    print("Loading LLM Engine...")
    ml_models["llm"] = LLMEngine()
    yield
    # Clean up on shutdown
    ml_models.clear()
    active_tasks.clear()

app = FastAPI(lifespan=lifespan)

# Allow React local dev to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class LaunchRequest(BaseModel):
    intent: str
    queries: List[Dict[str, str]] 
    duration: int 
    platforms: List[str] = ["google-maps"]
    deep_discovery: bool = False

class IntentRequest(BaseModel):
    intent: str
    platforms: List[str] = ["google-maps"]
    count: int = 10

class CampaignSynthesisRequest(BaseModel):
    search_id: Optional[str] = None
    intent: str
    meeting_link: Optional[str] = "https://calendly.com/nederland-homemademeals/events"
    is_referral: bool = False
    city: Optional[str] = ""

@app.post("/api/generate-queries")
async def generate_queries(req: IntentRequest):
    """Generates a list of search queries based on user intent."""
    llm = ml_models.get("llm") or LLMEngine()
    queries = llm.process_intent(req.intent, count=req.count)
    return {"status": "success", "queries": queries}

@app.post("/api/generate-campaign")
async def generate_campaign(req: CampaignSynthesisRequest):
    """Synthesizes a tailored email campaign based on intent and city."""
    llm = ml_models.get("llm") or LLMEngine()
    campaign = llm.generate_branded_campaign(
        intent=req.intent,
        city=req.city,
        meeting_link=req.meeting_link,
        is_referral=req.is_referral
    )
    if req.search_id:
        database.save_campaign(req.search_id, campaign)
    return {"status": "success", "campaign": campaign}

@app.get("/api/campaign/{task_id}")
async def get_campaign(task_id: str):
    """Retrieves the AI-generated campaign draft for a specific task."""
    campaign = database.get_campaign(task_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found for this task.")
    return campaign

@app.get("/api/logs")
async def stream_logs():
    """Streams the scraper log file to the frontend via SSE."""
    log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper_fast.log")
    
    async def log_generator():
        while not os.path.exists(log_file):
            yield "data: Initializing autonomous engine...\n\n"
            await asyncio.sleep(1.0)
        
        with open(log_file, "r") as f:
            f.seek(0, os.SEEK_END)
            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.5)
                    continue
                yield f"data: {line.strip()}\n\n"
    
    return StreamingResponse(log_generator(), media_type="text/event-stream")
    
@app.get("/api/active-task")
async def get_active_task():
    return active_task_info

async def process_and_launch_search(req: LaunchRequest, background_tasks: BackgroundTasks):
    """Unified entry point for launching a search from any interface (Web/Bot)."""
    task_id = str(uuid.uuid4())
    cancel_event = asyncio.Event()
    active_tasks[task_id] = cancel_event
    active_task_info["id"] = task_id
    active_task_info["intent"] = req.intent

    cities = scraper_events_fast.CITIES if req.deep_discovery else ["Amsterdam", "Rotterdam", "Utrecht", "Den Haag", "Eindhoven"]
    scraper_events_fast.CURRENT_SEARCH_ID = task_id
    database.create_search(req.intent.strip(), search_id=task_id)

    async def scraper_task():
        log_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scraper_fast.log")
        with open(log_file, "w") as f:
            f.write(f"🚀 [INIT] Launching search for: {req.intent}\n")
            f.write(f"🔍 Queries: {len(req.queries)} | Deep Discovery: {req.deep_discovery}\n\n")

        try:
            query_strings = [q.get("query", "") for q in req.queries if q.get("query")]
            if cancel_event.is_set():
                database.update_search_status(task_id, "cancelled")
                return

            import contextlib
            original_stdout = sys.stdout
            class TeeLog:
                def __init__(self, filename, original):
                    self.f = open(filename, "a")
                    self.original = original
                def write(self, data):
                    self.f.write(data)
                    self.f.flush()
                    self.original.write(data)
                def flush(self):
                    self.f.flush()
                    self.original.flush()

            with contextlib.redirect_stdout(TeeLog(log_file, original_stdout)):
                print(f"--- Starting Scraper Sequence [{task_id}] ---")
                if "google-maps" in req.platforms:
                    await scraper_events_fast.run_scraper(query_strings, cities)
                print(f"\n✅ Scraper finished. Starting AI Synthesis...")

            database.update_search_status(task_id, "completed")
            
            if not cancel_event.is_set():
                engine = LLMEngine()
                target_city = "Netherlands"
                for c in ["Den Haag", "Enschede", "Amsterdam", "Rotterdam", "Utrecht", "Haarlem", "Delft"]:
                    if c.lower() in req.intent.lower():
                        target_city = c
                        break
                
                campaign_draft = engine.generate_branded_campaign(req.intent, city=target_city)
                database.save_campaign(task_id, campaign_draft)
                with open(log_file, "a") as f:
                    f.write(f"✨ [AI] Campaign synthesis complete for {target_city}.\n")
                    f.write(f"🏁 entire sequence finished.\n")
                    
        except Exception as e:
            print(f"ERROR in scraper_task: {e}")
            database.update_search_status(task_id, "error")
            with open(log_file, "a") as f:
                f.write(f"❌ [ERROR] {str(e)}\n")
        finally:
            active_tasks.pop(task_id, None)
            if active_task_info["id"] == task_id:
                active_task_info["id"] = None
                active_task_info["intent"] = None
            scraper_events_fast.CURRENT_SEARCH_ID = None

    background_tasks.add_task(scraper_task)
    return task_id

@app.post("/api/launch")
async def launch_scraper(req: LaunchRequest, background_tasks: BackgroundTasks):
    task_id = await process_and_launch_search(req, background_tasks)
    return {"status": "success", "task_id": task_id}

@app.post("/api/telegram-webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handles incoming Telegram messages and triggers searches via voice intent."""
    try:
        data = await request.json()
        if "message" not in data: return {"ok": True}
        
        msg = data["message"]
        chat_id = msg["chat"]["id"]
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        
        if not token: 
            print("[TG] No BOT TOKEN set in environment.")
            return {"ok": True}

        async def send_msg(text):
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            async with httpx.AsyncClient() as client:
                await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})

        # Handle Voice Messages
        if "voice" in msg:
            file_id = msg["voice"]["file_id"]
            await send_msg("🧘 **Analyzing your voice command...** (Gemini Multi-Modal)")
            
            async with httpx.AsyncClient() as client:
                # 1. Get file path
                resp = await client.get(f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}")
                file_path = resp.json()["result"]["file_path"]
                # 2. Download bytes
                audio_resp = await client.get(f"https://api.telegram.org/file/bot{token}/{file_path}")
                audio_bytes = audio_resp.content
            
            # 3. Interpret using Gemini
            llm = LLMEngine()
            result = llm.interpret_voice_command(audio_bytes)
            
            if "error" in result:
                await send_msg(f"❌ **Gemini Interpretation Failed:**\n{result['error']}")
                return {"ok": True}
                
            transcription = result.get("transcription", "Unknown")
            intent = result.get("intent", "")
            count = result.get("count", 20)
            
            if not intent:
                await send_msg(f"🤷 **Transcription:**\n_{transcription}_\n\nI couldn't find a clear search intent. Please be more specific (e.g. 'Find car dealers in Haarlem').")
                return {"ok": True}

            await send_msg(
                f"🎙️ **Transcribed:**\n_{transcription}_\n\n"
                f"🚀 **Launching Search**\n"
                f"🔹 **Intent:** {intent}\n"
                f"🔹 **Queries:** {count}\n\n"
                f"Check the [NexusScrape Dashboard](http://178.104.45.251:3000) for live updates."
            )
            
            # 4. Generate Queries and Launch
            queries = llm.process_intent(intent, count)
            launch_req = LaunchRequest(
                intent=intent,
                queries=queries,
                platforms=["google-maps"],
                duration=60,  # Default duration for bot launches
                deep_discovery=False
            )
            await process_and_launch_search(launch_req, background_tasks)

        # Handle Text Commands
        elif "text" in msg:
            text = msg["text"]
            if text == "/start":
                await send_msg("👋 **Welcome to NexusScrape Autonomous Bot.**\n\nSend me a **voice message** describing who you want to find and where (e.g., 'Find dentists in Rotterdam, 20 queries') and I'll handle the rest.")

        return {"ok": True}
    except Exception as e:
        print(f"[TG ERROR] {e}")
        return {"ok": True}

@app.post("/api/cancel/{task_id}")
async def cancel_scraper(task_id: str):
    import subprocess
    subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
    subprocess.run(["pkill", "-f", "playwright"], capture_output=True)
    if task_id in active_tasks:
        active_tasks[task_id].set()
    database.update_search_status(task_id, "cancelled")
    return {"status": "cancelled", "task_id": task_id}

@app.get("/api/history")
async def get_history():
    return database.get_all_searches()

@app.get("/api/history/{search_id}/campaign")
async def get_search_campaign(search_id: str):
    return database.get_campaign(search_id)

@app.get("/api/history/{search_id}/leads")
async def get_leads(search_id: str):
    return database.get_leads_for_search(search_id)

@app.delete("/api/history/{search_id}")
async def delete_history(search_id: str):
    database.delete_search(search_id)
    return {"status": "deleted"}

@app.get("/api/track/{lead_id}")
async def track_open(lead_id: int):
    database.log_lead_open(lead_id)
    pixel_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06'
        b'\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00'
        b'\x01\r\n2\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return Response(content=pixel_data, media_type="image/png")

@app.get("/api/history/{lead_id}/messages")
async def get_lead_messages(lead_id: int):
    return database.get_lead_history(lead_id)

class GasCampaignRequest(BaseModel):
    webhook_url: str
    subject: str
    body: str
    search_id: Optional[str] = None
    leads: Optional[List[Dict[str, Any]]] = None

@app.post("/api/send-gas")
async def send_gas_campaign(req: GasCampaignRequest):
    """Sends a GAS campaign by proxying the request to the GAS webhook."""
    print(f"DEBUG: Received send-gas request. Webhook: {req.webhook_url[:20]}...")
    try:
        if not req.webhook_url:
            raise HTTPException(status_code=400, detail="Missing Webhook URL. Please pull from GAS Settings.")
            
        target_leads = req.leads or []
        if req.search_id and not target_leads:
            target_leads = database.get_leads_for_search(req.search_id)
        
        if not target_leads:
            print("DEBUG: No leads found. Synthesis might have failed or session is empty.")
            raise HTTPException(status_code=400, detail="No leads found for this session.")

        print(f"DEBUG: Dispatching to GAS for {len(target_leads)} leads.")
        # Pre-replace variables for the preview/test lead if it's a single test
        if len(target_leads) == 1:
            lead = target_leads[0]
            co_name = lead.get('name') or "Uw Bedrijf"
            req.subject = (req.subject or "").replace("{companyName}", co_name).replace("{{companyName}}", co_name)
            req.body = (req.body or "").replace("{companyName}", co_name).replace("{{companyName}}", co_name)

        payload = {
            "subject": req.subject or "Partnership Inquiry",
            "body": req.body or "Drafting error - please check synthesis.",
            "leads": target_leads,
            "vps_ip": "178.104.45.251:8443"
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(req.webhook_url, json=payload, follow_redirects=True)
            print(f"DEBUG: GAS Response Code: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    thread_map = data.get("threadMap", {})
                    for lead in target_leads:
                        lead_id = lead.get("id")
                        if lead_id:
                            database.save_message(
                                lead_id=int(lead_id),
                                direction="sent",
                                subject=req.subject,
                                body=req.body,
                                thread_id=thread_map.get(lead.get("email"))
                            )
                return data
            raise HTTPException(status_code=resp.status_code, detail=f"GAS Error: {resp.text}")
    except Exception as e:
        print(f"ERROR: send-gas failure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Proxy Error: {str(e)}")


@app.post("/api/sync-responses")
async def sync_responses(webhook_url: str):
    """Polls GAS for new replies and syncs them to the local database."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(webhook_url, json={"action": "checkReplies"}, follow_redirects=True)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    new_replies = data.get("replies", [])
                    for reply in new_replies:
                        email_match = re.search(r'<(.+?)>', reply.get("from", ""))
                        email = email_match.group(1) if email_match else reply.get("from")
                        lead = database.get_lead_by_email(email)
                        if lead:
                            database.save_message(
                                lead_id=lead['id'],
                                direction="received",
                                subject=reply.get("subject"),
                                body=reply.get("body"),
                                thread_id=reply.get("threadId")
                            )
                return data
            return {"status": "error", "code": response.status_code}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

class GasDeployRequest(BaseModel):
    mode: str = "update"
    deployment_id: Optional[str] = None

PRIMARY_DEPLOYMENT_ID = "AKfycbyw19qTJv3O3qrs-ZUdbfYBuHXEUx4YO5Fg0PfoQlzxBb-5nnPOBGi4DTyQ_k-SF_-2"

@app.post("/api/redeploy-gas")
async def redeploy_gas(req: GasDeployRequest = GasDeployRequest()):
    import subprocess
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gas_dest_dir = os.path.join(root, "gas_deploy")
    shutil.copy2(os.path.join(root, "gas_mailer.gs"), os.path.join(gas_dest_dir, "Code.gs"))
    clasp_path = shutil.which("clasp") or "/usr/local/bin/clasp"
    subprocess.run([clasp_path, "push", "--force"], cwd=gas_dest_dir)
    target_id = req.deployment_id or PRIMARY_DEPLOYMENT_ID
    subprocess.run([clasp_path, "deploy", "--deploymentId", target_id], cwd=gas_dest_dir)
    return {"status": "updated", "webhook_url": f"https://script.google.com/macros/s/{target_id}/exec"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8443, reload=True)
