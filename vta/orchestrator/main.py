"""
VTA Task Orchestrator - FastAPI WebSocket Server (port 5000).

Main entry point for the orchestrator. Accepts WebSocket connections
from the React frontend, creates Gemini Live sessions, and coordinates
the tutorial execution loop.

Architecture: Gemini Live = voice, Brain (Gemini Flash) = intent classification + Q&A.
"""

import asyncio
import json
import logging
import os
import uuid
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from vta.orchestrator.gemini_live_client import GeminiLiveClient, ARIA_SYSTEM_PROMPT
from vta.orchestrator.brain_client import BrainClient
from vta.orchestrator.agent_s3_client import AgentS3Client
from vta.orchestrator.orchestrator import run_tutorial
from vta.orchestrator.confirmation import ConfirmationManager
from vta.orchestrator.execution_mode import get_execution_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

app = FastAPI(title="VTA Task Orchestrator", version="3.0.0")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state for active sessions
active_sessions: dict[str, dict] = {}


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
    }


@app.get("/api/pdf/proxy")
async def proxy_pdf(url: str):
    """Proxy external PDF URLs to bypass CORS restrictions."""
    from fastapi.responses import StreamingResponse
    import httpx

    logger.info(f"Proxying PDF from: {url}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "pdf" not in content_type.lower() and len(response.content) < 1000:
                from fastapi import HTTPException
                raise HTTPException(status_code=400, detail="URL did not return a valid PDF")

            return StreamingResponse(
                iter([response.content]),
                media_type="application/pdf",
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Cache-Control": "public, max-age=3600",
                    "Content-Length": str(len(response.content)),
                }
            )
    except Exception as e:
        logger.error(f"Failed to proxy PDF from {url}: {e}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Failed to load PDF: {str(e)}")


@app.get("/api/pdf/{pdf_path:path}")
async def serve_pdf(pdf_path: str):
    """Serve PDF files from local storage."""
    from fastapi.responses import FileResponse
    import os

    pdf_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdfs")
    file_path = os.path.join(pdf_dir, pdf_path)

    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/pdf")
    else:
        logger.warning(f"PDF not found: {file_path}")
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"PDF not found: {pdf_path}")


@app.post("/api/upload-tutorial")
async def upload_tutorial(
    pdf: UploadFile = File(None),
    curriculum: UploadFile = File(None),
    title: str = Form("Uploaded Tutorial"),
):
    """Upload a curriculum JSON and optional PDF to create a tutorial.

    If no curriculum JSON is provided, auto-generates theory tasks from PDF pages.
    If no PDF is provided, creates a hands-on only curriculum.
    Files are stored locally on the server.
    """
    import shutil

    vta_dir = os.path.dirname(os.path.dirname(__file__))
    pdfs_dir = os.path.join(vta_dir, "pdfs")
    curriculum_dir = os.path.join(vta_dir, "curriculum")
    os.makedirs(pdfs_dir, exist_ok=True)
    os.makedirs(curriculum_dir, exist_ok=True)

    # Generate unique tutorial ID
    tutorial_id = f"tutorial_{uuid.uuid4().hex[:8]}"

    # Save PDF (if provided)
    pdf_filename = ""
    pdf_path = ""
    if pdf and pdf.filename:
        pdf_filename = f"{tutorial_id}.pdf"
        pdf_path = os.path.join(pdfs_dir, pdf_filename)
        with open(pdf_path, "wb") as f:
            shutil.copyfileobj(pdf.file, f)
        logger.info(f"Saved PDF: {pdf_path}")

    # Save or generate curriculum
    if curriculum and curriculum.filename:
        # User provided curriculum JSON
        curriculum_data = json.loads(await curriculum.read())
        curriculum_data["tutorial_id"] = tutorial_id
        curriculum_data["pdf_s3_key"] = pdf_filename
        curriculum_data["pdf_url"] = ""
    elif pdf_path:
        # Count PDF pages and auto-generate one theory task per slide
        try:
            import fitz
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1

        tasks_list = []
        for i in range(page_count):
            tasks_list.append({
                "task_id": f"T{i + 1}",
                "type": "theory",
                "title": f"Slide {i + 1}",
                "slide_number": i + 1,
                "slide_context": None,
                "sonic_prompt": None,
                "subtasks": [],
            })

        curriculum_data = {
            "tutorial_id": tutorial_id,
            "title": title,
            "description": f"Tutorial: {title}",
            "pdf_s3_key": pdf_filename,
            "pdf_url": "",
            "tasks": tasks_list,
        }
        logger.info(f"Auto-generated {page_count} theory tasks for '{title}'")
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Please provide a curriculum JSON or a PDF file.")

    curriculum_path = os.path.join(curriculum_dir, f"{tutorial_id}.json")
    with open(curriculum_path, "w") as f:
        json.dump(curriculum_data, f, indent=2)
    logger.info(f"Saved curriculum: {curriculum_path}")

    return JSONResponse({
        "tutorial_id": tutorial_id,
        "title": curriculum_data.get("title", title),
        "pdf_filename": pdf_filename,
        "task_count": len(curriculum_data.get("tasks", [])),
    })


@app.get("/api/tutorials")
async def list_tutorials():
    """List all available tutorials with details."""
    vta_dir = os.path.dirname(os.path.dirname(__file__))
    curriculum_dir = os.path.join(vta_dir, "curriculum")
    pdfs_dir = os.path.join(vta_dir, "pdfs")

    tutorials = []
    if os.path.exists(curriculum_dir):
        for fname in os.listdir(curriculum_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(curriculum_dir, fname)) as f:
                        data = json.load(f)
                    tid = data.get("tutorial_id", fname.replace(".json", ""))
                    pdf_key = data.get("pdf_s3_key", "")
                    has_pdf = bool(pdf_key and os.path.exists(os.path.join(pdfs_dir, pdf_key)))
                    tutorials.append({
                        "tutorial_id": tid,
                        "title": data.get("title", fname),
                        "description": data.get("description", ""),
                        "task_count": len(data.get("tasks", [])),
                        "has_pdf": has_pdf,
                    })
                except Exception:
                    pass

    return {"tutorials": tutorials}


@app.delete("/api/tutorials/{tutorial_id}")
async def delete_tutorial(tutorial_id: str):
    """Delete a tutorial and its PDF."""
    vta_dir = os.path.dirname(os.path.dirname(__file__))
    curriculum_dir = os.path.join(vta_dir, "curriculum")
    pdfs_dir = os.path.join(vta_dir, "pdfs")

    # Find and delete curriculum JSON
    deleted = False
    if os.path.exists(curriculum_dir):
        for fname in os.listdir(curriculum_dir):
            if fname.endswith(".json"):
                filepath = os.path.join(curriculum_dir, fname)
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    if data.get("tutorial_id") == tutorial_id:
                        # Delete associated PDF
                        pdf_key = data.get("pdf_s3_key", "")
                        if pdf_key:
                            pdf_path = os.path.join(pdfs_dir, pdf_key)
                            if os.path.exists(pdf_path):
                                os.remove(pdf_path)
                                logger.info(f"Deleted PDF: {pdf_path}")
                        # Delete curriculum JSON
                        os.remove(filepath)
                        logger.info(f"Deleted curriculum: {filepath}")
                        deleted = True
                        break
                except Exception:
                    pass

    if deleted:
        return {"status": "deleted", "tutorial_id": tutorial_id}
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Tutorial not found: {tutorial_id}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket handler for student connections."""
    await websocket.accept()
    session_id = None

    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            event_type = msg.get("event", "")

            if event_type == "start_session":
                session_id = await _handle_start_session(msg, websocket)

            elif event_type == "student_audio":
                await _handle_student_audio(session_id, msg)

            elif event_type == "student_confirmation":
                await _handle_student_confirmation(session_id, msg)

            elif event_type == "audio_playback_done":
                if session_id and session_id in active_sessions:
                    active_sessions[session_id]["sonic"].signal_playback_done()

            elif event_type == "slide_loaded":
                logger.info(f"Slide loaded: page {msg.get('page')}")

            elif event_type == "end_session":
                await _handle_end_session(session_id)
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        if session_id:
            await _cleanup_session(session_id)


async def _handle_start_session(msg: dict, websocket: WebSocket) -> str:
    """Initialize a new tutorial session."""
    session_id = msg.get("session_id", str(uuid.uuid4()))
    tutorial_id = msg.get("tutorial_id", "linux_basics_v1")
    student_id = msg.get("student_id", "anonymous")
    execution_mode = msg.get("execution_mode", None)
    brain_model = msg.get("brain_model", None)
    browser_vision_model = msg.get("browser_vision_model", None)
    desktop_vision_model = msg.get("desktop_vision_model", None)
    api_key = msg.get("api_key", None)

    # Set API key from frontend if provided
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        logger.info("Gemini API key set from frontend")

    # Prevent duplicate session starts
    if session_id in active_sessions:
        logger.warning(f"Session {session_id} already exists - ignoring duplicate start request")
        return session_id

    logger.info(f"Starting session {session_id} for tutorial {tutorial_id}")

    # Resolve execution mode: frontend > environment > default
    exec_config = get_execution_config(execution_mode)
    logger.info(f"Execution mode: {exec_config.mode.value}")

    # Create Agent S3 client
    agent_s3_url = os.environ.get("AGENT_S3_URL", "http://localhost:5001")
    agent_s3 = AgentS3Client(base_url=agent_s3_url)

    # Create ws_send helper
    async def ws_send(data: dict):
        try:
            if websocket.client_state.value == 1:  # CONNECTED state
                await websocket.send_json(data)
            else:
                logger.debug(f"WebSocket closed, skipping send: {data.get('event', 'unknown')}")
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")

    # Create confirmation manager
    confirmation_mgr = ConfirmationManager()

    # Create Brain client (intent classification + Q&A) — Gemini Flash
    brain_model_key = brain_model or os.environ.get("VTA_BRAIN_MODEL", "flash")
    brain = BrainClient(model_key=brain_model_key)

    # Create Gemini Live client (voice, no tools)
    sonic = GeminiLiveClient(
        audio_output_callback=lambda audio: ws_send({
            "event": "audio_chunk",
            "data": audio,
        }),
        transcript_callback=lambda text, role="ASSISTANT": ws_send({
            "event": "transcript_update",
            "text": text,
            "role": "assistant" if role == "ASSISTANT" else "user",
        }),
    )

    # Store session ID so reconnect() works when run_tutorial() starts.
    sonic._session_id = session_id
    sonic._system_prompt = ARIA_SYSTEM_PROMPT

    # Store session state
    active_sessions[session_id] = {
        "sonic": sonic,
        "agent_s3": agent_s3,
        "brain": brain,
        "confirmation_mgr": confirmation_mgr,
        "ws_send": ws_send,
        "websocket": websocket,
        "tutorial_id": tutorial_id,
        "execution_config": exec_config,
    }

    # Notify frontend
    await ws_send({
        "event": "session_started",
        "session_id": session_id,
        "tutorial_id": tutorial_id,
        "execution_mode": exec_config.mode.value,
        "brain_model": brain_model_key,
    })

    # Start tutorial execution in background
    asyncio.create_task(
        _run_tutorial_task(session_id, tutorial_id, sonic, agent_s3,
                           brain, confirmation_mgr, ws_send, exec_config,
                           browser_vision_model=browser_vision_model,
                           desktop_vision_model=desktop_vision_model)
    )

    return session_id


async def _run_tutorial_task(
    session_id: str,
    tutorial_id: str,
    sonic: GeminiLiveClient,
    agent_s3: AgentS3Client,
    brain: BrainClient,
    confirmation_mgr: ConfirmationManager,
    ws_send,
    exec_config,
    browser_vision_model: str = None,
    desktop_vision_model: str = None,
):
    """Run the tutorial in a background task."""
    try:
        await run_tutorial(
            tutorial_id=tutorial_id,
            session_id=session_id,
            sonic=sonic,
            agent=agent_s3,
            brain=brain,
            confirmation_mgr=confirmation_mgr,
            ws_send=ws_send,
            exec_config=exec_config,
            browser_vision_model=browser_vision_model,
            desktop_vision_model=desktop_vision_model,
        )
    except Exception as e:
        logger.error(f"Tutorial execution error: {e}", exc_info=True)
        await ws_send({
            "event": "error",
            "message": f"Tutorial error: {str(e)}",
        })


async def _handle_student_audio(session_id: Optional[str], msg: dict):
    """Forward student audio to Gemini Live."""
    if not session_id or session_id not in active_sessions:
        return

    audio_data = msg.get("data", "")
    if audio_data:
        sonic = active_sessions[session_id]["sonic"]
        sonic.add_audio_chunk(audio_data)


async def _handle_student_confirmation(session_id: Optional[str], msg: dict):
    """Handle student confirmation button click.

    'ready' → inject kickstart text into Gemini stream.
    Other responses → pass to ConfirmationManager as before.
    """
    if not session_id or session_id not in active_sessions:
        return

    response = msg.get("response", "")
    session = active_sessions[session_id]

    if response == "ready":
        sonic = session["sonic"]
        if sonic.is_active:
            await sonic.send_text_kickstart("Please begin.")
            logger.info(f"Ready button: text kickstart sent for session {session_id}")
        else:
            logger.warning(f"Ready button: stream not active for session {session_id}")
    else:
        confirmation_mgr = session["confirmation_mgr"]
        confirmation_mgr.receive_response(response)

    logger.info(f"Student confirmation (button): {response} for session {session_id}")


async def _handle_end_session(session_id: Optional[str]):
    """End an active session."""
    if session_id and session_id in active_sessions:
        await _cleanup_session(session_id)


async def _cleanup_session(session_id: str):
    """Clean up all resources for a session."""
    session = active_sessions.pop(session_id, None)
    if not session:
        return

    try:
        await session["sonic"].close()
    except Exception:
        pass

    try:
        await session["agent_s3"].close()
    except Exception:
        pass

    logger.info(f"Session {session_id} cleaned up")


if __name__ == "__main__":
    import uvicorn

    # Show configuration on startup
    logger.info("=" * 80)
    logger.info("VTA Orchestrator Starting (v3 - Gemini Live + Brain)...")
    logger.info(f"Local Curriculum: {os.environ.get('VTA_LOCAL_CURRICULUM', 'false')}")
    logger.info(f"Agent S3 URL: {os.environ.get('AGENT_S3_URL', 'http://localhost:5001')}")
    logger.info(f"Execution Mode (default): {os.environ.get('VTA_EXECUTION_MODE', 'demo_only')}")
    logger.info(f"Brain Model (default): {os.environ.get('VTA_BRAIN_MODEL', 'flash')}")
    logger.info(f"Gemini API Key: {'set' if os.environ.get('GEMINI_API_KEY') else 'NOT SET'}")
    logger.info("=" * 80)

    port = int(os.environ.get("ORCHESTRATOR_PORT", "5000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
