# apps/api/services/tender_db.py

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from django.conf import settings

_DB_LOCK = threading.Lock()


def _db_path() -> str:
    # project root
    return os.path.join(str(settings.BASE_DIR), "tenders_db.json")


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _read_db() -> Dict[str, Any]:
    path = _db_path()
    if not os.path.exists(path):
        return {"lastSeq": 0, "tenders": {}}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {"lastSeq": 0, "tenders": {}}

        data.setdefault("lastSeq", 0)
        data.setdefault("tenders", {})
        if not isinstance(data["tenders"], dict):
            data["tenders"] = {}

        return data
    except Exception:
        # if corrupted, start fresh to prevent crashes
        return {"lastSeq": 0, "tenders": {}}


def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def init_db_if_missing() -> str:
    """
    Ensure tenders_db.json exists.
    Returns db path.
    """
    path = _db_path()
    with _DB_LOCK:
        if not os.path.exists(path):
            _atomic_write(path, {"lastSeq": 0, "tenders": {}})
    return path


def create_tender_job(
    tender_id: str = "",
    tender_reference: str = "",
    tender_description: str = "",
) -> str:
    """
    Create a new tender job record with status=processing.
    Returns job_id like TENDER_01.
    """
    init_db_if_missing()
    path = _db_path()

    with _DB_LOCK:
        db = _read_db()
        seq = int(db.get("lastSeq") or 0) + 1
        db["lastSeq"] = seq

        job_id = f"TENDER_{seq:02d}"

        db["tenders"][job_id] = {
            "id": job_id,
            "tenderId": tender_id or "",
            "tenderReference": tender_reference or "",
            "tenderDescription": tender_description or "",

            "status": "processing",  # processing | completed | failed
            "createdAt": _now_iso(),
            "updatedAt": _now_iso(),

            "excelPath": "",
            "error": "",

            # optional debug info
            "zipPath": "",
            "extractDir": "",
            "companiesDetected": 0,

            # ✅ NEW: eligibility criteria extracted from tender.pdf
            "eligibilityCriteria": [],

            # ✅ NEW: tender.pdf extraction analytics
            # e.g. {model, durationMs, tokens:{promptTokens,outputTokens,totalTokens}}
            "tenderAnalytics": {},

            # ✅ NEW: aggregated tender analytics for full tender run
            # e.g. total time, total pdf count, gemini calls, tokens, perCompany breakdown
            "analytics": {},
        }

        _atomic_write(path, db)

    return job_id


def update_tender_job(job_id: str, patch: Dict[str, Any]) -> None:
    """
    Patch existing job record fields and update updatedAt.
    """
    if not job_id:
        return

    init_db_if_missing()
    path = _db_path()

    with _DB_LOCK:
        db = _read_db()
        tenders = db.get("tenders") or {}
        rec = tenders.get(job_id)

        if not isinstance(rec, dict):
            return

        for k, v in (patch or {}).items():
            rec[k] = v

        rec["updatedAt"] = _now_iso()
        tenders[job_id] = rec
        db["tenders"] = tenders

        _atomic_write(path, db)


def get_tender_job(job_id: str) -> Optional[Dict[str, Any]]:
    init_db_if_missing()
    with _DB_LOCK:
        db = _read_db()
        rec = (db.get("tenders") or {}).get(job_id)
        return rec if isinstance(rec, dict) else None


def list_tender_jobs() -> Dict[str, Any]:
    init_db_if_missing()
    with _DB_LOCK:
        return _read_db()
