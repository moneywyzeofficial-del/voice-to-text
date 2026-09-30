import os
import shutil
import socket
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import database
import ai_service

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Inicializar Base de Dados
database.init_db()

app = FastAPI(title="Voice to Text - Gestor Diário")

# Permitir CORS para testes locais
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir ficheiros estáticos e uploads de áudio
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

def get_local_ip() -> str:
    """Obtém o IP local da máquina na rede Wi-Fi."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

class SettingsPayload(BaseModel):
    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None

class SummaryPayload(BaseModel):
    date_str: str

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Voice to Text</h1><p>A carregar ficheiros estáticos...</p>")

@app.get("/api/info")
async def get_app_info():
    api_key = ai_service.get_api_key()
    model = ai_service.get_model_name()
    return {
        "has_api_key": bool(api_key),
        "current_model": model,
        "local_ip": get_local_ip(),
        "server_time": datetime.now().strftime("%H:%M"),
        "server_date": datetime.now().strftime("%Y-%m-%d")
    }

@app.post("/api/settings")
async def update_settings(payload: SettingsPayload):
    if not payload.gemini_api_key and not payload.gemini_model:
        raise HTTPException(status_code=400, detail="Nenhum parâmetro para atualizar.")
    success = ai_service.save_settings(api_key=payload.gemini_api_key, model_name=payload.gemini_model)
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao guardar configuração.")
    return {"status": "ok", "message": "Definições guardadas com sucesso!"}

@app.get("/api/notes")
async def list_notes(date: Optional[str] = None):
    available_dates = database.get_available_dates()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    target_date = date if date else (today_str if today_str in available_dates else (available_dates[0] if available_dates else today_str))
    notes = database.get_all_notes(target_date)
    return {
        "selected_date": target_date,
        "available_dates": available_dates,
        "notes": notes
    }

@app.post("/api/record")
async def create_voice_note(
    audio_file: UploadFile = File(...),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    client_time: Optional[str] = Form(None),
    client_date: Optional[str] = Form(None),
    duration_sec: Optional[float] = Form(0.0)
):
    # Definir data e hora da nota
    now = datetime.now()
    date_str = client_date if client_date else now.strftime("%Y-%m-%d")
    time_str = client_time if client_time else now.strftime("%H:%M")

    # Guardar áudio
    filename = f"rec_{now.strftime('%Y%m%d_%H%M%S')}_{audio_file.filename}"
    file_path = os.path.join(UPLOADS_DIR, filename)
    relative_audio_path = f"/uploads/{filename}"

    audio_bytes = await audio_file.read()
    with open(file_path, "wb") as f:
        f.write(audio_bytes)

    # Processar localização inversa
    location_name = None
    if latitude is not None and longitude is not None:
        location_name = ai_service.reverse_geocode(latitude, longitude)

    # Analisar com Gemini
    mime_type = audio_file.content_type or "audio/mp4"
    try:
        analysis = ai_service.analyze_audio_with_gemini(audio_bytes, mime_type)
    except ValueError as ve:
        # Chave não configurada
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento da IA: {str(e)}")

    # Guardar na BD
    note = database.insert_note(
        date_str=date_str,
        time_str=time_str,
        transcription=analysis.get("transcription", ""),
        summary=analysis.get("summary", ""),
        theme=analysis.get("theme", "Geral"),
        tasks=analysis.get("tasks", []),
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        audio_path=relative_audio_path,
        duration_sec=duration_sec or 0.0
    )

    return {"status": "ok", "note": note}

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int):
    success = database.delete_note_by_id(note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Nota não encontrada.")
    return {"status": "ok", "message": "Nota eliminada com sucesso."}

@app.post("/api/daily-summary")
async def get_summary_for_day(payload: SummaryPayload):
    notes = database.get_all_notes(payload.date_str)
    if not notes:
        return {"summary": "Não existem notas gravadas para esta data."}
    
    summary_text = ai_service.generate_daily_summary(notes)
    return {"summary": summary_text}
