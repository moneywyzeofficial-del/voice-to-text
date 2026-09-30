import os
import json
import requests
from typing import Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def get_api_key() -> Optional[str]:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("gemini_api_key"):
                    return data["gemini_api_key"].strip()
        except Exception:
            pass
    return os.getenv("GEMINI_API_KEY")

def get_model_name() -> str:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("gemini_model"):
                    return data["gemini_model"].strip()
        except Exception:
            pass
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

def save_settings(api_key: Optional[str] = None, model_name: Optional[str] = None) -> bool:
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        if api_key is not None:
            data["gemini_api_key"] = api_key.strip()
        if model_name is not None:
            data["gemini_model"] = model_name.strip()
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False

# Pydantic schema for structured output from Gemini
class VoiceNoteAnalysis(BaseModel):
    transcription: str = Field(description="Transcrição literal e fiel do áudio em português europeu.")
    summary: str = Field(description="Resumo claro e direto do que foi dito e feito.")
    theme: str = Field(
        description="Categoria principal da nota. Exemplo: 'Jardinagem', 'Piscinas', 'Compras & Material', 'Contacto / Cliente', 'Orçamento', 'Manutenção Geral', 'Pessoal'."
    )
    tasks: list[str] = Field(
        default_factory=list,
        description="Lista de ações, tarefas pendentes ou materiais a comprar mencionados na gravação."
    )

def analyze_audio_with_gemini(audio_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    api_key = get_api_key()
    if not api_key:
        raise ValueError("Chave de API do Gemini não configurada. Por favor, adiciona a tua API Key nas Definições.")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    prompt = """
Tu és o assistente inteligente de gestão de trabalho diário do Tiago. O Tiago cria e mantém jardins e também faz manutenção de piscinas em Portugal.

Analisa a gravação de áudio fornecida:
1. Transcreve o áudio exatamente como foi dito, corrigindo pontuação para fácil leitura (em Português Europeu).
2. Identifica o tema principal (ex: 'Jardinagem', 'Piscinas', 'Compras & Material', 'Contacto / Cliente', 'Orçamento', 'Geral').
3. Faz um resumo conciso, informal e direto.
4. Extrai quaisquer tarefas, materiais necessários ou alertas práticos mencionados.
"""

    # Normalizar mime types comuns de browsers/iOS
    clean_mime = mime_type.split(";")[0].strip().lower()
    if clean_mime in ["audio/m4a", "audio/x-m4a", "audio/mp4", "audio/aac"]:
        clean_mime = "audio/mp4"
    elif clean_mime in ["audio/webm", "audio/ogg"]:
        clean_mime = "audio/webm"
    elif clean_mime in ["audio/wav", "audio/x-wav"]:
        clean_mime = "audio/wav"

    primary_model = get_model_name()
    fallback_model = "gemini-2.0-flash" if primary_model != "gemini-2.0-flash" else "gemini-1.5-flash"

    try:
        response = client.models.generate_content(
            model=primary_model,
            contents=[
                types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=VoiceNoteAnalysis,
                temperature=0.2,
            )
        )
        
        result_json = json.loads(response.text)
        return result_json
    except Exception as e:
        try:
            response = client.models.generate_content(
                model=fallback_model,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=clean_mime),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=VoiceNoteAnalysis,
                    temperature=0.2,
                )
            )
            return json.loads(response.text)
        except Exception as e2:
            raise RuntimeError(f"Erro ao processar áudio com Gemini ({primary_model}): {str(e2)}")

# Geocoding cache
_geo_cache: Dict[Tuple[float, float], str] = {}

def reverse_geocode(latitude: Optional[float], longitude: Optional[float]) -> Optional[str]:
    if latitude is None or longitude is None:
        return None

    # Arredondar para ~10-20 metros para aproveitar cache
    lat_r = round(latitude, 4)
    lng_r = round(longitude, 4)
    if (lat_r, lng_r) in _geo_cache:
        return _geo_cache[(lat_r, lng_r)]

    try:
        url = "https://nominatim.openstreetmap.org/reverse"
        headers = {"User-Agent": "VoiceToTextApp-Tiago/1.0"}
        params = {
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "zoom": 18,
            "addressdetails": 1
        }
        resp = requests.get(url, params=params, headers=headers, timeout=4)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            road = addr.get("road") or addr.get("pedestrian") or addr.get("suburb") or ""
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
            
            parts = [p for p in [road, city] if p]
            result = ", ".join(parts) if parts else data.get("display_name", "")
            if len(result) > 60:
                result = result[:57] + "..."
            _geo_cache[(lat_r, lng_r)] = result
            return result
    except Exception:
        pass
    return f"{latitude:.4f}, {longitude:.4f}"

def generate_daily_summary(notes: list[dict]) -> str:
    """Gera um resumo executivo de todas as notas do dia com a IA."""
    api_key = get_api_key()
    if not api_key or not notes:
        return "Sem notas suficientes ou chave de API ausente."

    from google import genai

    client = genai.Client(api_key=api_key)
    notes_text = ""
    for n in sorted(notes, key=lambda x: x["time_str"]):
        notes_text += f"- [{n['time_str']}] {n.get('location_name', '')} | {n['theme']}: {n['summary']}\n"
        if n.get("tasks"):
            notes_text += f"  Tarefas: {', '.join(n['tasks'])}\n"

    prompt = f"""
Cria um resumo diário estruturado e conciso (em Markdown, Português Europeu) para o Tiago a partir dos seguintes registos de trabalho do dia:

{notes_text}

Formato pretendido:
# 📅 Resumo do Dia
### 🕒 Cronologia do Trabalho
(breve linha temporal com horas, locais e o que foi feito)

### ✅ Tarefas e Pendentes
(lista das tarefas que ficaram para fazer ou materiais a comprar)

### 📌 Destaques / Notas Importantes
(se houver algo relevante a salientar)
"""
    try:
        model_name = get_model_name()
        resp = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return resp.text
    except Exception as e:
        return f"Erro ao gerar resumo: {e}"
