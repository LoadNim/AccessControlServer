# main.py — 최종본 v1.4: 데이터 조회 API 분리
# 채널: /qr-events (JSON only), /access-events (metadata + 1 image),
#       /registrations (metadata + N images)

import os
import datetime as dt
import hashlib
import json
import uuid
import boto3

from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

# =========================
# FastAPI 기본 설정
# =========================
app = FastAPI(title="Access Control API (Full Cloud Native)")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

KST = ZoneInfo("Asia/Seoul")

# =========================
# 환경 변수 및 클라이언트 설정
# =========================
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment variables.")
engine = create_engine(DATABASE_URL)

R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL")
R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID")
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY")

if not all([R2_BUCKET_NAME, R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY]):
    raise RuntimeError("R2 storage environment variables are not fully set.")

s3_client = boto3.client(
    's3',
    endpoint_url=R2_ENDPOINT_URL,
    aws_access_key_id=R2_ACCESS_KEY_ID,
    aws_secret_access_key=R2_SECRET_ACCESS_KEY
)

# =========================
# DB 함수 (조회 함수 분리됨)
# =========================

# --- 데이터 삽입(INSERT) 함수들 ---
def insert_access_event(images_dir: str, requested_at: str, device_id: str):
    with engine.connect() as conn:
        statement = text(
            """
            INSERT INTO access_events (images_dir, requested_at, device_id) 
            VALUES (:images_dir, :requested_at, :device_id)
            """
        )
        conn.execute(
            statement,
            {"images_dir": images_dir, "requested_at": requested_at, "device_id": device_id}
        )
        conn.commit()

def insert_registration(images_dir: str, dong: str, ho: str, phone: str, requested_at: str, device_id: str):
    with engine.connect() as conn:
        statement = text(
            """
            INSERT INTO registrations (images_dir, dong, ho, phone, requested_at, device_id) 
            VALUES (:images_dir, :dong, :ho, :phone, :requested_at, :device_id)
            """
        )
        conn.execute(
            statement,
            {
                "images_dir": images_dir,
                "dong": dong,
                "ho": ho,
                "phone": phone,
                "requested_at": requested_at,
                "device_id": device_id
            }
        )
        conn.commit()

def insert_qr_event(phone: str, purpose: str, requested_at: str, device_id: str):
    with engine.connect() as conn:
        statement = text(
            """
            INSERT INTO qr_events (phone, purpose, requested_at, device_id, status) 
            VALUES (:phone, :purpose, :requested_at, :device_id, DEFAULT)
            """
        )
        conn.execute(
            statement,
            {"phone": phone, "purpose": purpose, "requested_at": requested_at, "device_id": device_id}
        )
        conn.commit()

# --- 데이터 조회(SELECT) 함수들 ---
def get_all_registrations(limit: int = 50):
    """registrations 테이블에서 최신 데이터를 조회합니다."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM registrations ORDER BY id DESC LIMIT :limit"), {"limit": limit})
        return [dict(row._mapping) for row in result]

def get_all_access_events(limit: int = 50):
    """access_events 테이블에서 최신 데이터를 조회합니다."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM access_events ORDER BY id DESC LIMIT :limit"), {"limit": limit})
        return [dict(row._mapping) for row in result]

def get_all_qr_events(limit: int = 50):
    """qr_events 테이블에서 최신 데이터를 조회합니다."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM qr_events ORDER BY id DESC LIMIT :limit"), {"limit": limit})
        return [dict(row._mapping) for row in result]

# =========================
# 공용 유틸 (변경 없음)
# =========================
def _safe_name(name: str) -> str:
    keep = [c for c in name if c.isalnum() or c in ("-", "_", ".",)]
    return "".join(keep) or "payload.json"

def _day_dir_str() -> str:
    return dt.datetime.now(KST).strftime("%Y%m%d")

def _iso_kst(d: dt.datetime) -> str:
    return d.astimezone(KST).isoformat(timespec="seconds")

def _parse_iso_any(s: Optional[str]) -> Optional[dt.datetime]:
    if not s: return None
    try:
        return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None

def _augment_timing(meta: Dict[str, Any]) -> Dict[str, Any]:
    server_recv = dt.datetime.now(KST)
    timing = dict(meta.get("timing") or {})
    capture_time = timing.get("capture_time")

    client_dt = _parse_iso_any(capture_time)
    transfer_ms: Optional[int] = None
    if client_dt:
        try:
            transfer_ms = int((server_recv - client_dt.astimezone(KST)).total_seconds() * 1000)
        except Exception:
            transfer_ms = None

    timing["server_received_at"] = _iso_kst(server_recv)
    if transfer_ms is not None:
        timing["transfer_ms"] = transfer_ms
    return timing

def _save_metadata_cloud(meta: Dict[str, Any], session_id: str, event_type: str):
    meta["schema"] = 2
    json_bytes = json.dumps(meta, ensure_ascii=False, indent=2).encode("utf-8")
    object_key = f"{event_type}/{_day_dir_str()}/{session_id}/metadata.json"
    try:
        s3_client.put_object(Bucket=R2_BUCKET_NAME, Key=object_key, Body=json_bytes, ContentType='application/json')
    except Exception as e:
        print(f"Error uploading metadata for {session_id} to R2: {e}")
        raise HTTPException(status_code=500, detail="Metadata upload to cloud storage failed.")

async def _save_images_cloud(files: List[UploadFile], session_id: str, event_type: str) -> str:
    cloud_dir_path = f"{event_type}/{_day_dir_str()}/{session_id}"
    for idx, f in enumerate(files):
        raw = await f.read()
        if not raw: continue
        original_filename = _safe_name(f.filename or f"frame_{idx:03d}.webp")
        object_key = f"{cloud_dir_path}/{original_filename}"
        try:
            s3_client.put_object(Bucket=R2_BUCKET_NAME, Key=object_key, Body=raw, ContentType=f.content_type)
        except Exception as e:
            print(f"Error uploading {object_key} to R2: {e}")
            raise HTTPException(status_code=500, detail="File upload to cloud storage failed.")
    return cloud_dir_path

# =========================
# 헬스/파비콘 (변경 없음)
# =========================
@app.get("/healthz")
def healthz():
    return {"ok": True, "now": _iso_kst(dt.datetime.now(KST))}

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    from fastapi import Response
    return Response(status_code=204)

# =========================
# API 엔드포인트 (조회 엔드포인트 분리됨)
# =========================

# --- 데이터 조회용 GET 엔드포인트들 ---
@app.get("/registrations", summary="모든 등록 이벤트 목록 조회")
def list_registrations():
    """DB에서 모든 '등록' 이벤트를 조회하여 JSON으로 반환합니다."""
    return {"registrations": get_all_registrations()}

@app.get("/access-events", summary="모든 출입 이벤트 목록 조회")
def list_access_events():
    """DB에서 모든 '출입' 이벤트를 조회하여 JSON으로 반환합니다."""
    return {"access_events": get_all_access_events()}

@app.get("/qr-events", summary="모든 QR 이벤트 목록 조회")
def list_qr_events():
    """DB에서 모든 'QR' 이벤트를 조회하여 JSON으로 반환합니다."""
    return {"qr_events": get_all_qr_events()}


# --- 데이터 기록용 POST 엔드포인트들 ---
@app.post("/qr-events")
async def qr_events(payload: Dict[str, Any], request: Request):
    meta = dict(payload)
    timing = _augment_timing(meta)
    meta["timing"] = timing
    session_id = uuid.uuid4().hex[:12]
    _save_metadata_cloud(meta, session_id, event_type="qr-events")
    device_id = meta.get("client", {}).get("device_id", "unknown")
    data = meta.get("data", {})
    phone   = (data.get("phone") or "").strip()
    purpose = (data.get("purpose") or "").strip()
    if not (phone and purpose):
        raise HTTPException(status_code=400, detail="phone and purpose are required")
    requested_at = timing.get("server_received_at") or _iso_kst(dt.datetime.now(KST))
    insert_qr_event(phone, purpose, requested_at, device_id)
    return PlainTextResponse("QR 요청 전송")

@app.post("/access-events")
async def access_events(
    metadata: str = Form(...),
    image: UploadFile = File(...),
):
    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata must be valid JSON")
    session_id = uuid.uuid4().hex[:12]
    cloud_dir_path = await _save_images_cloud([image], session_id, event_type="access-events")
    timing = _augment_timing(meta)
    meta["timing"] = timing
    _save_metadata_cloud(meta, session_id, event_type="access-events")
    device_id = meta.get("client", {}).get("device_id", "unknown")
    requested_at = timing.get("server_received_at") or _iso_kst(dt.datetime.now(KST))
    insert_access_event(cloud_dir_path, requested_at, device_id)
    return PlainTextResponse("출입 요청 전송")

@app.post("/registrations")
async def registrations(
    metadata: str = Form(...),
    images: List[UploadFile] = File(...),
):
    if not images:
        raise HTTPException(status_code=400, detail="no images provided")
    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="metadata must be valid JSON")
    session_id = uuid.uuid4().hex[:12]
    cloud_dir_path = await _save_images_cloud(images, session_id, event_type="registrations")
    timing = _augment_timing(meta)
    meta["timing"] = timing
    _save_metadata_cloud(meta, session_id, event_type="registrations")
    device_id = meta.get("client", {}).get("device_id", "unknown")
    data = meta.get("data", {})
    dong  = (data.get("dong")  or "").strip()
    ho    = (data.get("ho")    or "").strip()
    phone = (data.get("phone") or "").strip()
    if not (dong and ho and phone):
        raise HTTPException(status_code=400, detail="dong, ho, phone are required")
    requested_at = timing.get("server_received_at") or _iso_kst(dt.datetime.now(KST))
    insert_registration(cloud_dir_path, dong, ho, phone, requested_at, device_id)
    return PlainTextResponse("등록 요청 전송")