"""server.py - API + halaman web. Jalankan: uvicorn server:app --reload"""
import base64
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from modules import capsule as cap, crypto_core as cc, timelock as tl

app = FastAPI(title="Surat untuk Masa Depan")


class SealReq(BaseModel):
    text: str | None = None
    file_b64: str | None = None
    filename: str | None = None
    password: str = ""
    unlock_iso: str                     # waktu buka, ISO 8601 (browser mengirim UTC)
    algorithm: str = "AES-256-GCM"
    public_key_pem: str | None = None


class OpenReq(BaseModel):
    capsule: dict
    password: str = ""
    private_key_pem: str | None = None


@app.post("/api/seal")
def seal(r: SealReq):
    try:
        data = base64.b64decode(r.file_b64) if r.file_b64 else (r.text or "").encode()
        if not data:
            raise HTTPException(400, "Isi kapsul kosong.")
        pub = cc.load_public_key(r.public_key_pem.encode()) if r.public_key_pem else None
        if pub is None and not r.password:
            raise HTTPException(400, "Kata sandi wajib diisi.")
        when = datetime.fromisoformat(r.unlock_iso.replace("Z", "+00:00"))
        return cap.create_capsule(data, r.password, when, r.algorithm, bool(r.file_b64), r.filename, pub)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Gagal menyegel: {e}")


@app.post("/api/open")
def open_(r: OpenReq):
    try:
        priv = cc.load_private_key(r.private_key_pem.encode()) if r.private_key_pem else None
        data = cap.open_capsule(r.capsule, r.password, priv)
    except tl.TimeLockedError:
        raise HTTPException(423, str(r.capsule.get("unlock_timestamp")))
    except cc.DecryptionError as e:
        raise HTTPException(401, str(e))            # password salah / kapsul diubah
    except Exception as e:
        raise HTTPException(400, f"Kapsul tidak valid: {e}")
    c = r.capsule
    return {"is_file": c.get("is_file"), "filename": c.get("filename"),
            "text": None if c.get("is_file") else data.decode("utf-8", "replace"),
            "file_b64": base64.b64encode(data).decode() if c.get("is_file") else None}


@app.get("/")
def index():
    return FileResponse("static/index.html")
