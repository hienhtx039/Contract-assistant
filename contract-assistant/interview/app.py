"""
FastAPI application for the Interview Assistant.
Serves the web UI, handles assessment requests, and provides Excel downloads.
"""
import io
import json
import logging
import os
import uuid
from datetime import datetime

import requests
import soundfile as sf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from interview.assessment import assess_transcript
from interview.excel_generator import generate_assessment_excel
from interview.question_generator import extract_text_from_file, generate_questions

logging.basicConfig(level=logging.INFO)

# In-memory session store
sessions: dict = {}


class AssessmentRequest(BaseModel):
    session_id: str
    candidate_name: str
    interviewer: str
    position: str
    transcript: str
    jd_text: str = ""
    date: str = None


class SessionInfo(BaseModel):
    candidate_name: str
    interviewer: str
    position: str


def create_app(output_dir: str = None) -> FastAPI:
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

    app = FastAPI(title="GreenNode Interview Assistant")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

    @app.post("/api/extract-info")
    async def extract_document_info(
        file: UploadFile = File(...),
        doc_type: str = Form(default="cv"),
    ):
        """Extract candidate name from CV or position from JD."""
        file_bytes = await file.read()
        filename = file.filename or "file.pdf"

        try:
            text = extract_text_from_file(file_bytes, filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not text.strip():
            return {"text": "", "extracted": ""}

        # Use first ~500 chars for quick extraction
        snippet = text[:500]

        if doc_type == "cv":
            # Extract candidate name: typically first prominent line
            import subprocess, json as _json
            try:
                result = subprocess.run(
                    ["claude", "-p",
                     f"Trích xuất TÊN ứng viên từ đầu CV sau. Chỉ trả về tên, không giải thích.\n\n{snippet}"],
                    capture_output=True, text=True, timeout=30,
                )
                name = result.stdout.strip().strip('"').strip("'")
                # Sanity check: name should be short
                if len(name) > 50:
                    name = ""
                return {"extracted": name, "full_text": text}
            except Exception:
                return {"extracted": "", "full_text": text}

        elif doc_type == "jd":
            import subprocess
            try:
                result = subprocess.run(
                    ["claude", "-p",
                     f"Trích xuất TÊN VỊ TRÍ tuyển dụng từ JD sau. Chỉ trả về tên vị trí, không giải thích.\n\n{snippet}"],
                    capture_output=True, text=True, timeout=30,
                )
                position = result.stdout.strip().strip('"').strip("'")
                if len(position) > 100:
                    position = ""
                return {"extracted": position, "full_text": text}
            except Exception:
                return {"extracted": "", "full_text": text}

        return {"extracted": "", "full_text": text}

    @app.post("/api/extract-jd-text")
    async def extract_from_jd_text(data: dict):
        """Extract position and functional skills from JD text."""
        jd_text = data.get("jd_text", "").strip()
        if not jd_text:
            raise HTTPException(status_code=400, detail="JD text is empty")

        import subprocess
        try:
            result = subprocess.run(
                ["claude", "-p",
                 f"Từ mô tả tuyển dụng sau, trích xuất thông tin. Trả về CHỈ JSON, không giải thích.\n\n"
                 f"Mô tả: {jd_text}\n\n"
                 f'{{"position": "<tên vị trí>", "functional_skills": ["<kỹ năng 1>", "<kỹ năng 2>", "<kỹ năng 3>"]}}'],
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout.strip()
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()
            import json as _json
            return _json.loads(output)
        except Exception as e:
            logging.error(f"Extract JD text error: {e}")
            return {"position": "", "functional_skills": []}

    @app.post("/api/generate-questions")
    async def generate_interview_questions(
        file: UploadFile = File(...),
        position: str = Form(default=""),
        jd_file: UploadFile = File(default=None),
        jd_text: str = Form(default=""),
    ):
        """Upload CV + optional JD and generate tailored interview questions."""
        if not position.strip():
            raise HTTPException(status_code=400, detail="Position is required")

        file_bytes = await file.read()
        filename = file.filename or "cv.pdf"

        try:
            cv_text = extract_text_from_file(file_bytes, filename)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        if not cv_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from CV")

        # Extract JD text: file takes priority, then pasted text
        jd_content = ""
        if jd_file and jd_file.filename:
            jd_bytes = await jd_file.read()
            try:
                jd_content = extract_text_from_file(jd_bytes, jd_file.filename)
            except ValueError:
                pass
        if not jd_content.strip() and jd_text.strip():
            jd_content = jd_text.strip()

        logging.info(f"Generating questions: position={position}, CV={len(cv_text)} chars, JD={len(jd_content)} chars")
        questions = generate_questions(cv_text, position, jd_text=jd_content)

        if "error" in questions:
            raise HTTPException(status_code=500, detail=questions["error"])

        return questions

    @app.post("/api/session")
    async def create_session(info: SessionInfo):
        session_id = str(uuid.uuid4())[:8]
        sessions[session_id] = {
            "candidate_name": info.candidate_name,
            "interviewer": info.interviewer,
            "position": info.position,
            "created_at": datetime.now().isoformat(),
            "transcript": "",
            "assessment": None,
            "excel_path": None,
        }
        return {"session_id": session_id}

    @app.post("/api/assess")
    async def run_assessment(req: AssessmentRequest):
        """Run Claude Code CLI assessment on the transcript and generate Excel."""
        if not req.transcript.strip():
            raise HTTPException(status_code=400, detail="Transcript is empty")

        logging.info(f"Running assessment for session {req.session_id}")
        logging.info(f"Transcript length: {len(req.transcript)} chars")

        # Save transcript to local file BEFORE assessment (safety backup)
        interview_date = req.date or datetime.now().strftime("%Y-%m-%d")
        safe_name = req.candidate_name.replace(" ", "_").replace("/", "-") or "unknown"
        transcript_path = os.path.join(
            output_dir, f"transcript_{safe_name}_{interview_date}_{req.session_id}.txt"
        )
        os.makedirs(output_dir, exist_ok=True)
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(f"Candidate: {req.candidate_name}\n")
            f.write(f"Position: {req.position}\n")
            f.write(f"Interviewer: {req.interviewer}\n")
            f.write(f"Date: {interview_date}\n")
            f.write(f"Session: {req.session_id}\n")
            f.write("=" * 60 + "\n\n")
            f.write(req.transcript)
            if req.jd_text:
                f.write("\n\n" + "=" * 60 + "\n")
                f.write("JD:\n" + req.jd_text)
        logging.info(f"Transcript saved: {transcript_path}")

        # Run Claude Code CLI assessment
        assessment = assess_transcript(req.transcript, jd_text=req.jd_text)

        if "error" in assessment:
            raise HTTPException(
                status_code=500,
                detail=f"{assessment['error']}. Transcript saved at: {transcript_path}"
            )

        # Generate Excel
        excel_path = generate_assessment_excel(
            assessment=assessment,
            candidate_name=req.candidate_name,
            interviewer=req.interviewer,
            position=req.position,
            interview_date=interview_date,
            output_dir=output_dir,
        )

        # Store in session
        sessions[req.session_id] = {
            "candidate_name": req.candidate_name,
            "interviewer": req.interviewer,
            "position": req.position,
            "transcript": req.transcript,
            "assessment": assessment,
            "excel_path": excel_path,
        }

        return {
            "session_id": req.session_id,
            "assessment": assessment,
            "excel_download": f"/api/download/{req.session_id}",
        }

    @app.get("/api/download/{session_id}")
    async def download_excel(session_id: str):
        session = sessions.get(session_id)
        if not session or not session.get("excel_path"):
            raise HTTPException(status_code=404, detail="Assessment not found")

        excel_path = session["excel_path"]
        if not os.path.exists(excel_path):
            raise HTTPException(status_code=404, detail="Excel file not found")

        return FileResponse(
            excel_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=os.path.basename(excel_path),
        )

    @app.post("/api/transcribe")
    async def transcribe_file(
        file: UploadFile = File(...),
        language: str = Form(default="vi"),
        vocab_hints: str = Form(default=""),
    ):
        """Upload an audio file and transcribe via VNGCloud MaaS Whisper API."""
        base_url = os.getenv("WHISPER_BASE_URL", "").rstrip("/")
        api_key = os.getenv("WHISPER_API_KEY", "")
        model = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3")

        if not base_url:
            raise HTTPException(status_code=500, detail="WHISPER_BASE_URL not configured")

        audio_bytes = await file.read()
        filename = file.filename or "audio.wav"

        # Convert to WAV if needed (Whisper API prefers WAV)
        if not filename.lower().endswith(".wav"):
            try:
                audio_data, sample_rate = sf.read(io.BytesIO(audio_bytes))
                wav_buf = io.BytesIO()
                sf.write(wav_buf, audio_data, sample_rate, format="WAV", subtype="PCM_16")
                wav_buf.seek(0)
                audio_bytes = wav_buf.read()
                filename = "audio.wav"
            except Exception:
                pass  # Send as-is and let the API handle it

        try:
            resp = requests.post(
                f"{base_url}/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (filename, audio_bytes, "audio/wav")},
                data={
                    "model": model,
                    "language": language,
                    "response_format": "json",
                    **({"prompt": f"Phỏng vấn về: {vocab_hints}"} if vocab_hints.strip() else {}),
                },
                timeout=60,
            )
            resp.raise_for_status()
            result = resp.json()
            text = result.get("text", "")
            # Filter Whisper hallucinations
            hallucination_words = [
                "subscribe", "la la school", "ghiền mì gõ", "không bỏ lỡ",
                "video hấp dẫn", "cảm ơn các bạn đã theo dõi", "nhớ like",
                "nhấn chuông", "đăng ký kênh", "like share", "kênh youtube",
            ]
            text_lower = text.lower()
            for hw in hallucination_words:
                if hw in text_lower:
                    text = ""
                    break
            return {"text": text}
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"Whisper API error: {str(e)}")

    @app.get("/api/sessions")
    async def list_sessions():
        return {
            sid: {
                "candidate_name": s.get("candidate_name"),
                "position": s.get("position"),
                "has_assessment": s.get("assessment") is not None,
            }
            for sid, s in sessions.items()
        }

    # Serve frontend static files
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    return app
