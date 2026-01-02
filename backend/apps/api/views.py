# apps/api/views.py

import os
import zipfile
import uuid
import threading
import traceback
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .services.tender_parser import extract_tender_from_pdf_with_gemini
from .services.excel_export import export_tender_excel
from .services.company_parser import extract_company_bidder_and_payments
from .services.tender_db import create_tender_job, update_tender_job, get_tender_job, list_tender_jobs

from .services.zip_utils import safe_extract_zip, ZipSecurityError

from django.http import FileResponse
from urllib.parse import quote


# -------------------------
# Helpers
# -------------------------
def _is_company_folder(name: str) -> bool:
    if not name:
        return False
    if name.startswith("."):
        return False
    if name.lower() == "__macosx":
        return False
    return True


def tender_list_view(request):
    """
    GET /api/tender/list/
    Returns all tenders (latest first).
    """
    db = list_tender_jobs() or {}
    tenders = list((db.get("tenders") or {}).values())

    # sort newest first (createdAt desc)
    tenders.sort(key=lambda x: (x.get("createdAt") or ""), reverse=True)

    return JsonResponse({"tenders": tenders})


def tender_download_excel_view(request):
    """
    GET /api/tender/download-excel/?job_id=TENDER_01
    Downloads the Excel file for a completed tender job.
    """
    job_id = (request.GET.get("job_id") or "").strip()
    if not job_id:
        return JsonResponse({"error": "job_id is required"}, status=400)

    rec = get_tender_job(job_id)
    if not rec:
        return JsonResponse({"error": "job_id not found", "job_id": job_id}, status=404)

    if (rec.get("status") or "") != "completed":
        return JsonResponse(
            {"error": "Tender is not completed yet", "status": rec.get("status", "")},
            status=400,
        )

    excel_path = (rec.get("excelPath") or "").strip()
    if not excel_path:
        return JsonResponse({"error": "excelPath not available for this job"}, status=404)

    # ✅ Security: Only allow files from BASE_DIR/excels/
    base_excels_dir = os.path.abspath(os.path.join(str(settings.BASE_DIR), "excels"))
    abs_excel_path = os.path.abspath(excel_path)

    if not abs_excel_path.startswith(base_excels_dir + os.sep):
        return JsonResponse({"error": "Invalid excel path (blocked)"}, status=403)

    if not os.path.exists(abs_excel_path):
        return JsonResponse({"error": "Excel file not found on server"}, status=404)

    filename = os.path.basename(abs_excel_path) or f"{job_id}.xlsx"
    response = FileResponse(
        open(abs_excel_path, "rb"),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return response


def _normalize_extract_root(extract_dir: str) -> str:
    """
    Many ZIPs contain one wrapper folder.
    If extract_dir has only 1 folder and no tender.pdf at root, step into it.
    """
    try:
        entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
        full_paths = [os.path.join(extract_dir, e) for e in entries]

        if len(entries) == 1 and os.path.isdir(full_paths[0]):
            return full_paths[0]
    except Exception:
        pass
    return extract_dir


def _collect_company_jobs(extract_dir: str):
    """
    Structure expected:
      extract_dir/
        tender.pdf
        CompanyA/ (pdfs...)
        CompanyB/ (pdfs...)
    """
    jobs = []

    for name in os.listdir(extract_dir):
        if not _is_company_folder(name):
            continue

        company_dir = os.path.join(extract_dir, name)
        if not os.path.isdir(company_dir):
            continue

        company_name = name.strip()

        pdf_paths = []
        for root, _, files in os.walk(company_dir):
            for fn in files:
                if not fn.lower().endswith(".pdf"):
                    continue
                if fn.lower() == "tender.pdf":
                    continue
                pdf_paths.append(os.path.join(root, fn))

        if not pdf_paths:
            continue

        jobs.append({"company_name": company_name, "pdf_paths": pdf_paths})

    return jobs


def _merge_tokens_total(total: dict, tokens: dict) -> dict:
    """
    total: {"promptTokens": int, "outputTokens": int, "totalTokens": int}
    tokens: same keys
    """
    if not isinstance(total, dict):
        total = {"promptTokens": 0, "outputTokens": 0, "totalTokens": 0}
    if not isinstance(tokens, dict):
        return total

    def _to_int(v):
        try:
            return int(v)
        except Exception:
            return 0

    total["promptTokens"] = _to_int(total.get("promptTokens")) + _to_int(tokens.get("promptTokens"))
    total["outputTokens"] = _to_int(total.get("outputTokens")) + _to_int(tokens.get("outputTokens"))
    total["totalTokens"] = _to_int(total.get("totalTokens")) + _to_int(tokens.get("totalTokens"))
    return total


def _process_one_company(job: dict, model: str, pdf_workers: int) -> dict:
    company_name = job["company_name"]
    pdf_paths = job["pdf_paths"]

    extracted = extract_company_bidder_and_payments(
        company_name=company_name,
        pdf_paths=pdf_paths,
        model=model,
        max_workers=pdf_workers,
    )

    return {
        "companyName": company_name,
        "bidder": extracted.get("bidder") or {},
        "payments": extracted.get("payments") or [],
        "work_experience": extracted.get("work_experience") or [],
        "analytics": extracted.get("analytics") or {},
    }


# -------------------------
# Background worker
# -------------------------
def _background_run(job_id: str, zip_path: str, extract_dir: str):
    """
    Runs the heavy tender pipeline in background
    and updates tenders_db.json.
    """
    overall_t0 = time.time()

    try:
        # ===============================
        # Safe ZIP extract
        # ===============================
        try:
            safe_extract_zip(zip_path, extract_dir)
        except ZipSecurityError as e:
            update_tender_job(job_id, {
                "status": "failed",
                "error": f"Unsafe ZIP: {str(e)}",
            })
            return

        extract_dir = _normalize_extract_root(extract_dir)
        update_tender_job(job_id, {"extractDir": extract_dir})

        if not os.path.isdir(extract_dir):
            update_tender_job(job_id, {
                "status": "failed",
                "error": "Extract directory was not created",
            })
            return

        # ===============================
        # Locate tender.pdf
        # ===============================
        tender_pdf_path = None
        for root, _, files in os.walk(extract_dir):
            for fn in files:
                if fn.lower() == "tender.pdf":
                    tender_pdf_path = os.path.join(root, fn)
                    break
            if tender_pdf_path:
                break

        if not tender_pdf_path:
            update_tender_job(job_id, {
                "status": "failed",
                "error": "tender.pdf not found inside zip",
            })
            return

        # ===============================
        # 1️⃣ Tender extraction
        # ===============================
        tender_data = extract_tender_from_pdf_with_gemini(
            tender_pdf_path,
            model=os.getenv("GEMINI_TENDER_MODEL", "gemini-3-flash-preview"),
        ) or {}

        update_tender_job(job_id, {
            "tenderId": tender_data.get("tenderId", "") or "",
            "tenderReference": tender_data.get("refNo", "") or "",
            "tenderDescription": tender_data.get("description", "") or "",
            "eligibilityCriteria": tender_data.get("bidderEligibilityCriteria") or [],
            "tenderAnalytics": tender_data.get("tenderAnalytics") or {},
        })

        # ===============================
        # 2️⃣ Company parsing
        # ===============================
        jobs = _collect_company_jobs(extract_dir)
        update_tender_job(job_id, {"companiesDetected": len(jobs)})

        company_workers = int(os.getenv("COMPANY_WORKERS", "4"))
        pdf_workers = int(os.getenv("PDF_WORKERS_PER_COMPANY", "5"))
        model = os.getenv("GEMINI_COMPANY_MODEL", "gemini-3-flash-preview")

        bidders = []
        payments_by_company = []
        work_experience_by_company = []

        # ✅ Tender-level analytics aggregation
        total_pdfs_received = 0
        total_valid_pdfs = 0
        total_gemini_calls = 0
        total_tokens = {"promptTokens": 0, "outputTokens": 0, "totalTokens": 0}
        per_company_analytics = []

        # include tender tokens/calls first
        tender_analytics = tender_data.get("tenderAnalytics") or {}
        tender_tokens = (tender_analytics.get("tokens") or {}) if isinstance(tender_analytics, dict) else {}
        total_tokens = _merge_tokens_total(total_tokens, tender_tokens)
        total_gemini_calls += 1

        if jobs:
            for j in jobs:
                total_pdfs_received += len(j.get("pdf_paths") or [])

            with ThreadPoolExecutor(max_workers=company_workers) as ex:
                futures = [
                    ex.submit(_process_one_company, job, model, pdf_workers)
                    for job in jobs
                ]

                for fut in as_completed(futures):
                    try:
                        result = fut.result() or {}

                        bidders.append(result.get("bidder") or {})

                        payments_by_company.append({
                            "companyName": result.get("companyName") or "",
                            "payments": result.get("payments") or [],
                        })

                        work_experience_by_company.append({
                            "companyName": result.get("companyName") or "",
                            "workExperience": result.get("work_experience") or [],
                        })

                        c_an = result.get("analytics") or {}
                        if isinstance(c_an, dict):
                            per_company_analytics.append(c_an)
                            total_valid_pdfs += int(c_an.get("validPdfCount") or 0)
                            total_gemini_calls += int(c_an.get("geminiCalls") or 0)

                            c_tokens = c_an.get("tokens") or {}
                            if isinstance(c_tokens, dict):
                                total_tokens = _merge_tokens_total(total_tokens, c_tokens)

                    except Exception:
                        continue

        # ===============================
        # ✅ Final analytics object
        # ===============================
        overall_t1 = time.time()
        analytics = {
            "jobId": job_id,
            "durationMs": int((overall_t1 - overall_t0) * 1000),
            "durationSeconds": round(overall_t1 - overall_t0, 3),

            "companiesDetected": len(jobs),
            "totalPdfReceived": total_pdfs_received,
            "totalValidPdfProcessed": total_valid_pdfs,

            "geminiCallsTotal": total_gemini_calls,
            "tokensTotal": total_tokens,
            "perCompany": per_company_analytics,
        }

        # ===============================
        # 3️⃣ Excel export (✅ PASS analytics now)
        # ===============================
        excel_path = export_tender_excel(
            tender_data,
            bidders=bidders,
            payments_by_company=payments_by_company,
            work_experience_by_company=work_experience_by_company,
            analytics=analytics,  # ✅ THIS IS THE CHANGE
        )

        # ===============================
        # ✅ Completed
        # ===============================
        update_tender_job(job_id, {
            "status": "completed",
            "excelPath": excel_path,
            "error": "",
            "analytics": analytics,
        })

    except Exception as e:
        update_tender_job(job_id, {
            "status": "failed",
            "error": f"{str(e)}\n{traceback.format_exc()[:4000]}",
        })


# -------------------------
# API: Submit ZIP
# -------------------------
@csrf_exempt
def parse_tender_zip_view(request):
    """
    POST multipart/form-data
    key: zip_file

    Returns immediately with job_id.
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    if "zip_file" not in request.FILES:
        return JsonResponse(
            {"error": "zip_file is required (multipart/form-data)"},
            status=400
        )

    uploaded_zip = request.FILES["zip_file"]

    # Create job immediately
    job_id = create_tender_job()

    base_tmp = getattr(settings, "MEDIA_ROOT", None) or os.path.join(
        str(settings.BASE_DIR), "tmp_uploads"
    )
    tmp_dir = os.path.join(base_tmp, "tmp_uploads") if base_tmp == getattr(settings, "MEDIA_ROOT", None) else base_tmp

    run_id = uuid.uuid4().hex[:10]
    extract_dir = os.path.join(tmp_dir, f"extracted_{run_id}")

    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(extract_dir, exist_ok=True)

    zip_path = os.path.join(tmp_dir, f"{run_id}_{uploaded_zip.name}")

    with open(zip_path, "wb") as f:
        for chunk in uploaded_zip.chunks():
            f.write(chunk)

    if not zipfile.is_zipfile(zip_path):
        update_tender_job(job_id, {
            "status": "failed",
            "error": "Uploaded file is not a valid ZIP",
        })
        return JsonResponse(
            {"error": "Invalid ZIP file", "job_id": job_id},
            status=400
        )

    update_tender_job(job_id, {
        "zipPath": zip_path,
        "extractDir": extract_dir,
        "status": "processing",
    })

    t = threading.Thread(
        target=_background_run,
        args=(job_id, zip_path, extract_dir),
        daemon=True,
    )
    t.start()

    return JsonResponse({
        "message": "Tender accepted ✅. Processing started. Please check after some minutes.",
        "job_id": job_id,
        "status": "processing",
        "status_check": f"/api/tender/status/?job_id={job_id}",
    })


# -------------------------
# API: Check Status
# -------------------------
def tender_status_view(request):
    """
    GET /api/tender/status/?job_id=TENDER_01
    """
    job_id = (request.GET.get("job_id") or "").strip()
    if not job_id:
        return JsonResponse({"error": "job_id is required"}, status=400)

    rec = get_tender_job(job_id)
    if not rec:
        return JsonResponse(
            {"error": "job_id not found", "job_id": job_id},
            status=404
        )

    return JsonResponse({"job": rec})
