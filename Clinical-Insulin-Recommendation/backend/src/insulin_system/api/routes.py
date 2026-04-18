"""
FastAPI route definitions for GlucoSense Clinical Support API.

Endpoints: POST /predict, POST /explain, POST /recommend, GET /model-info, etc.
Input validation and structured JSON responses with clinical metadata.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any, Dict, Optional

import requests
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config.schema import DashboardConfig, GLUCOSE_ZONES, get_glucose_zone
from ..safety.audit import log_prediction
from ..monitoring import get_monitor
from ..storage import (
    init_db,
    check_database_integrity,
    insert_record,
    insert_smart_sensor_prediction,
    insert_clinician_feedback,
    get_clinician_feedback,
    get_records,
    get_notifications,
    insert_notification,
    delete_notifications_by_type,
    mark_notifications_read,
    mark_notification_read,
    delete_notification,
    get_glucose_readings,
    insert_glucose_reading,
    insert_dose_event,
    get_dose_events,
    get_alerts,
    resolve_alert,
    resolve_all_alerts,
    get_patient_context,
    get_setting,
    set_setting,
    run_seed_if_needed,
    seed_demo_cohort,
    ensure_patient_demo_monitoring,
    list_patients,
    list_removed_patients,
    get_patient,
    create_patient,
    update_patient,
    patient_exists,
    delete_patient,
    restore_patient,
)
from ..storage.backup import create_backup, list_backups, restore_backup

from .alert_helpers import check_critical_alerts
from .glucose_trends_helpers import build_trend_series
from .patient_context_helpers import update_patient_context_from_body
from .route_data import (
    build_input_summary,
    DEFAULT_ALERTS_LIMIT,
    DEFAULT_GLUCOSE_TRENDS_HOURS,
    DEFAULT_RECORDS_LIMIT,
    DEFAULT_NOTIFICATIONS_LIMIT,
    REPORTS_DOWNLOAD_NOTIFICATION_TYPE,
)
from .schemas import (
    PredictionResponse,
    ExplainResponse,
    RecommendationResponse,
    ModelInfoResponse,
    FeatureImportanceResponse,
)
from .validators import patient_input_to_dataframe, validate_patient_input
from .engine import (
    get_bundle,
    run_predict,
    run_recommend,
    get_model_info,
    get_feature_importance,
)
from .smart_sensor_engine import (
    smart_sensor_bundle_available,
    run_smart_sensor_predict,
    run_smart_sensor_recommend,
    get_smart_sensor_feature_importance,
)
from .smart_sensor_explain import run_smart_sensor_explain
from .shap_background import load_background_if_needed
from .readiness import get_readiness, ready_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["GlucoSense"])


@router.get("/health/live", tags=["health"])
def api_health_live():
    """Liveness only — no DB or model checks."""
    return JSONResponse(content={"status": "ok", "live": True})


@router.get("/health/ready", tags=["health"])
def api_health_ready():
    """Readiness for startup orchestration: DB + runtime artifacts must be ready."""
    return ready_response()


@router.get("/health/db", tags=["health"])
def api_health_db():
    """SQLite integrity check (durability). Safe to poll after backup/restore."""
    try:
        run_seed_if_needed()
        return check_database_integrity()
    except Exception as e:
        return {"ok": False, "detail": str(e)}


class MealPlanSsoRequest(BaseModel):
    """Body forwarded to Meal Plan POST /api/auth/integration/glucosense."""

    email: str
    display_name: Optional[str] = None
    role: str = Field(default="patient")


def _meal_plan_api_base_url() -> str:
    return (
        os.environ.get("MEAL_PLAN_API_URL", "").strip()
        or os.environ.get("VITE_MEAL_PLAN_API_URL", "").strip()
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _glucosense_embed_key() -> str:
    """Must match Meal Plan API GLUCOSENSE_EMBED_KEY."""
    return (
        os.environ.get("GLUCOSENSE_EMBED_KEY", "").strip()
        or os.environ.get("MEAL_PLAN_EMBED_SECRET", "").strip()
        or "dev-embed-local-only"
    )


@router.post("/meal-plan/sso", tags=["meal-plan"])
def meal_plan_sso_proxy(body: MealPlanSsoRequest):
    """
    Proxy iframe SSO from the GlucoSense SPA to the Meal Plan API.
    The browser calls same-origin /api/meal-plan/sso (Vite → :8000); this handler adds the embed key.
    """
    try:
        base = _meal_plan_api_base_url()
        url = f"{base}/api/auth/integration/glucosense"
        role = body.role if body.role in ("clinician", "patient") else "patient"
        payload = {
            "email": body.email.strip().lower(),
            "display_name": body.display_name,
            "role": role,
        }
        try:
            r = requests.post(
                url,
                json=payload,
                headers={"X-Glucosense-Embed-Key": _glucosense_embed_key()},
                timeout=20,
            )
        except requests.RequestException as exc:
            logger.warning("Meal Plan SSO proxy: request failed: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Meal Plan API unreachable at {base}. Start the Meal Plan backend (port 8001). ({exc})",
            ) from exc
        try:
            data = r.json()
        except Exception:
            data = {"detail": (r.text or r.reason or "Meal Plan SSO failed")[:500]}
        return JSONResponse(status_code=int(r.status_code), content=data)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Meal Plan SSO proxy failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


try:
    init_db()
    run_seed_if_needed()
except Exception:
    pass


def _validation_response(errors: list) -> JSONResponse:
    """Return 422 with structured validation errors."""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


def _http_exception_smart_sensor(exc: Exception, *, action: str) -> HTTPException:
    """Map sklearn bundle/schema mismatches to a clear 503; otherwise 500."""
    msg = str(exc)
    if "unseen at fit time" in msg or "Feature names should match" in msg:
        return HTTPException(
            status_code=503,
            detail=(
                "Smart Sensor model bundle does not match the current preprocessing code. "
                "Regenerate it from the repository root: python run_pipeline.py"
            ),
        )
    return HTTPException(status_code=500, detail=f"{action} failed: {msg}")


def _safe_glucose_float(body: Dict[str, Any]) -> Optional[float]:
    """Extract glucose_level from body as float or None."""
    gl = body.get("glucose_level")
    if gl is None or (isinstance(gl, str) and not gl.strip()):
        return None
    try:
        return float(gl)
    except (TypeError, ValueError):
        return None


def _record_glucose_trend(body: Dict[str, Any], patient_id: Optional[int] = None) -> None:
    """Record glucose from body as trend point if present."""
    gl = body.get("glucose_level")
    if gl is None or (isinstance(gl, str) and not gl.strip()):
        return
    try:
        insert_glucose_reading(float(gl), is_predicted=False, patient_id=patient_id)
    except Exception as e:
        logger.warning("Failed to record glucose for trend: %s", e)


@router.post("/predict", response_model=PredictionResponse)
def predict(body: Dict[str, Any]):
    """Get insulin dosage prediction for a single patient."""
    request_id = str(uuid.uuid4())
    if smart_sensor_bundle_available():
        try:
            from smart_sensor_ml.inference import validate_inference_payload

            validate_inference_payload(body)
        except ValueError as e:
            return _validation_response([{"field": "body", "message": str(e)}])
        try:
            resp = run_smart_sensor_predict(body)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Smart Sensor prediction failed: %s", e)
            raise _http_exception_smart_sensor(e, action="Smart Sensor prediction")
        resp.request_id = request_id
        log_prediction("/predict", request_id, resp.predicted_class, resp.confidence, request_summary={"pipeline": "smart_sensor"})
        try:
            insert_record(
                endpoint="predict",
                request_id=request_id,
                predicted_class=resp.predicted_class,
                confidence=resp.confidence,
                input_summary=build_input_summary(body),
                response_summary={"predicted_class": resp.predicted_class, "confidence": resp.confidence, "pipeline": "smart_sensor"},
            )
            insert_smart_sensor_prediction(
                str(body.get("measurement_time", "")),
                resp.predicted_class,
                resp.confidence,
                resp.probability_breakdown,
                patient_id=None,
                meal_context=str(body.get("meal_context", "")),
                activity_context=str(body.get("activity_context", "")),
            )
        except Exception:
            pass
        return resp

    try:
        patient, _, errors = validate_patient_input(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if errors:
        return _validation_response(errors)

    try:
        bundle = get_bundle()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {e}")

    df = patient_input_to_dataframe(patient)
    try:
        resp = run_predict(patient, df, bundle)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")

    resp.request_id = request_id
    log_prediction("/predict", request_id, resp.predicted_class, resp.confidence, request_summary={"n_fields": len(body)})
    try:
        insert_record(
            endpoint="predict",
            request_id=request_id,
            predicted_class=resp.predicted_class,
            confidence=resp.confidence,
            input_summary=build_input_summary(body),
            response_summary={"predicted_class": resp.predicted_class, "confidence": resp.confidence},
        )
    except Exception:
        pass
    return resp


@router.post("/explain", response_model=ExplainResponse)
def explain(body: Dict[str, Any]):
    """Explain prediction using Smart Sensor ProductionBundle (SHAP on transformed features)."""
    request_id = str(uuid.uuid4())
    if not smart_sensor_bundle_available():
        raise HTTPException(
            status_code=503,
            detail=(
                "Smart Sensor model not available. Train the pipeline so "
                "outputs/smart_sensor_ml/model_bundle/bundle.joblib exists."
            ),
        )
    try:
        from smart_sensor_ml.inference import validate_inference_payload

        validate_inference_payload(body)
    except ValueError as e:
        return _validation_response([{"field": "body", "message": str(e)}])
    try:
        resp = run_smart_sensor_explain(body)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Smart Sensor explain failed: %s", e)
        raise _http_exception_smart_sensor(e, action="Explain")

    resp.request_id = request_id
    log_prediction(
        "/explain",
        request_id,
        resp.predicted_class,
        resp.confidence,
        request_summary={"pipeline": "smart_sensor"},
    )
    try:
        insert_record(
            endpoint="explain",
            request_id=request_id,
            predicted_class=resp.predicted_class,
            confidence=resp.confidence,
            input_summary=build_input_summary(body),
            response_summary={
                "predicted_class": resp.predicted_class,
                "confidence": resp.confidence,
                "pipeline": "smart_sensor",
            },
        )
    except Exception:
        pass
    return resp


@router.post("/batch-recommend")
def batch_recommend(body: Dict[str, Any]):
    """Batch recommendation: body = { "patients": [ {...}, {...} ] }."""
    patients = body.get("patients") or body.get("items") or []
    if not isinstance(patients, list):
        raise HTTPException(status_code=400, detail="Body must contain 'patients' array")
    if len(patients) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 patients per batch")

    try:
        bundle = get_bundle()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {e}")

    background = load_background_if_needed()
    results = []
    for i, p in enumerate(patients):
        try:
            patient, _, errors = validate_patient_input(p)
            if errors:
                results.append({"index": i, "error": errors[0].get("message", "Validation failed")})
                continue
            df = patient_input_to_dataframe(patient)
            resp = run_recommend(patient, df, bundle, background)
            results.append({"index": i, "recommendation": resp.model_dump()})
        except Exception as e:
            results.append({"index": i, "error": str(e)})
    return {"recommendations": results, "count": len(results)}


@router.post("/recommend", response_model=RecommendationResponse)
def recommend(body: Dict[str, Any]):
    """Get full recommendation with dosage suggestion, reasoning, and explanation. Requires patient_id (registered patient)."""
    patient_id = body.get("patient_id")
    if patient_id is None:
        raise HTTPException(
            status_code=400,
            detail="patient_id is required. Register a patient first before running an assessment.",
        )
    try:
        pid = int(patient_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="patient_id must be a valid integer.")
    if not patient_exists(pid):
        raise HTTPException(
            status_code=400,
            detail="Patient not found. Register the patient before running an assessment.",
        )

    request_id = str(uuid.uuid4())
    if smart_sensor_bundle_available():
        try:
            from smart_sensor_ml.inference import validate_inference_payload

            validate_inference_payload(body)
        except ValueError as e:
            return _validation_response([{"field": "body", "message": str(e)}])
        try:
            resp = run_smart_sensor_recommend(body)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Smart Sensor recommendation failed: %s", e)
            raise _http_exception_smart_sensor(e, action="Recommendation")
        resp.request_id = request_id
        log_prediction("/recommend", request_id, resp.predicted_class, resp.confidence, resp.is_high_risk)
        try:
            get_monitor().log_prediction(resp.predicted_class, resp.confidence, resp.is_high_risk, "recommend")
        except Exception:
            pass
        try:
            insert_record(
                endpoint="recommend",
                request_id=request_id,
                predicted_class=resp.predicted_class,
                confidence=resp.confidence,
                is_high_risk=resp.is_high_risk,
                input_summary=build_input_summary(body),
                response_summary={
                    "predicted_class": resp.predicted_class,
                    "confidence": resp.confidence,
                    "dosage_action": resp.dosage_action,
                    "is_high_risk": resp.is_high_risk,
                    "recommendation_summary": resp.recommendation_summary,
                    "recommended_action": getattr(resp, "recommended_action", None) or resp.recommendation_summary,
                    "pipeline": "smart_sensor",
                },
                patient_id=pid,
            )
            insert_smart_sensor_prediction(
                str(body.get("measurement_time", "")),
                resp.predicted_class,
                resp.confidence,
                resp.probability_breakdown,
                patient_id=pid,
                meal_context=str(body.get("meal_context", "")),
                activity_context=str(body.get("activity_context", "")),
            )
        except Exception:
            pass
        update_patient_context_from_body(body)
        _record_glucose_trend(body, patient_id=pid)
        try:
            check_critical_alerts(_safe_glucose_float(body), resp.is_high_risk, resp.predicted_class)
        except Exception:
            pass
        return resp

    try:
        patient, _, errors = validate_patient_input(body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if errors:
        return _validation_response(errors)

    try:
        bundle = get_bundle()
    except Exception as e:
        logger.error("Model load failed for /recommend: %s", e)
        raise HTTPException(
            status_code=503,
            detail=(
                "Model not loaded. Generate a local demo bundle from the Clinical-Insulin-Recommendation "
                "folder: python scripts/quick_train_inference_bundle.py. "
                f"Error: {e}"
            )
        )

    df = patient_input_to_dataframe(patient)
    background = load_background_if_needed()
    try:
        resp = run_recommend(patient, df, bundle, background)
    except Exception as e:
        logger.exception("Recommendation failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}. Check logs for details."
        )

    resp.request_id = request_id
    log_prediction("/recommend", request_id, resp.predicted_class, resp.confidence, resp.is_high_risk)
    try:
        get_monitor().log_prediction(resp.predicted_class, resp.confidence, resp.is_high_risk, "recommend")
    except Exception:
        pass
    try:
        insert_record(
            endpoint="recommend",
            request_id=request_id,
            predicted_class=resp.predicted_class,
            confidence=resp.confidence,
            is_high_risk=resp.is_high_risk,
            input_summary=build_input_summary(body),
            response_summary={
                "predicted_class": resp.predicted_class,
                "confidence": resp.confidence,
                "dosage_action": resp.dosage_action,
                "is_high_risk": resp.is_high_risk,
                "recommendation_summary": resp.recommendation_summary,
                "recommended_action": getattr(resp, "recommended_action", None) or resp.recommendation_summary,
            },
            patient_id=pid,
        )
    except Exception:
        pass

    update_patient_context_from_body(body)
    _record_glucose_trend(body, patient_id=pid)
    try:
        check_critical_alerts(_safe_glucose_float(body), resp.is_high_risk, resp.predicted_class)
    except Exception:
        pass
    return resp


@router.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    """Get model performance metrics and metadata."""
    if smart_sensor_bundle_available():
        try:
            from .smart_sensor_engine import load_smart_sensor_bundle

            b = load_smart_sensor_bundle()
            meta = b.metadata or {}
            if meta.get("task") == "regression":
                mname, mval = "r2_test", float(meta.get("r2_test", 0.0))
            else:
                mname = "composite_score"
                mval = float(meta.get("composite_score_test", meta.get("composite_score", 0.0)))
            return ModelInfoResponse(
                model_name=b.model_name,
                metric_name=mname,
                metric_value=mval,
                feature_names=list(b.feature_names),
                classes=list(b.class_names),
                n_features=len(b.feature_names),
            )
        except Exception as e:
            logger.warning("Smart Sensor model-info fallback: %s", e)
    try:
        bundle = get_bundle()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {e}")
    return get_model_info(bundle)


@router.get("/feature-importance", response_model=FeatureImportanceResponse)
def feature_importance():
    """Get global feature importance (built-in from model)."""
    if smart_sensor_bundle_available():
        try:
            out = get_smart_sensor_feature_importance()
            if out is not None:
                return out
        except Exception as e:
            logger.warning("Smart Sensor feature importance unavailable: %s", e)
        raise HTTPException(
            status_code=404,
            detail=(
                "Feature importance is not available for this Smart Sensor model "
                "(no tree importances or linear coefficients). Inspect offline evaluation metrics."
            ),
        )
    try:
        bundle = get_bundle()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Model not loaded: {e}")
    cfg = DashboardConfig()
    out = get_feature_importance(bundle, cfg.evaluation_dir)
    if out is None:
        raise HTTPException(status_code=404, detail="Feature importance not available for this model")
    return out


@router.post("/feedback")
def record_feedback(body: Dict[str, Any]):
    """Record clinician override/feedback for model improvement."""
    try:
        fid = insert_clinician_feedback(
            record_id=body.get("record_id"),
            request_id=body.get("request_id"),
            predicted_class=body.get("predicted_class"),
            clinician_action=body.get("clinician_action"),
            actual_dose_units=body.get("actual_dose_units"),
            override_reason=body.get("override_reason"),
            input_summary=body.get("input_summary"),
        )
        return {"ok": True, "feedback_id": fid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/feedback")
def list_feedback(limit: int = 100):
    """List clinician feedback records for analysis."""
    try:
        records = get_clinician_feedback(limit=limit)
        return {"feedback": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/monitoring/stats")
def monitoring_stats(n: int = 100):
    """Get recent prediction stats for monitoring."""
    try:
        return get_monitor().get_recent_stats(n=n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/records")
def list_records(limit: int = DEFAULT_RECORDS_LIMIT):
    """List recent prediction/recommendation records from the database."""
    try:
        records = get_records(limit=limit)
        return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
def health():
    """Combined health snapshot with DB readiness and runtime warmup details."""
    try:
        init_db()
        run_seed_if_needed()
    except BaseException as e:
        logger.exception("GET /api/health bootstrap check failed")
        state = get_readiness()
        state["status"] = "degraded"
        state["database"] = {"status": "error", "detail": str(e)}
        return JSONResponse(status_code=200, content=state)
    state = get_readiness()
    return JSONResponse(status_code=200, content=state)


@router.get("/notifications")
def list_notifications(limit: int = DEFAULT_NOTIFICATIONS_LIMIT):
    """List notifications (from seed or runtime)."""
    try:
        run_seed_if_needed()
        items = get_notifications(limit=limit)
        return {"notifications": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notifications")
def create_notification(body: Dict[str, Any]):
    """Create a notification. For type=reports_download, replaces any existing one."""
    text = body.get("text") or ""
    notification_type = body.get("type") or body.get("notification_type")
    if not text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        run_seed_if_needed()
        if notification_type == REPORTS_DOWNLOAD_NOTIFICATION_TYPE:
            delete_notifications_by_type(REPORTS_DOWNLOAD_NOTIFICATION_TYPE)
        insert_notification(text.strip(), notification_type=notification_type)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/by-type/{notification_type}")
def delete_notifications_by_type_route(notification_type: str):
    """Delete notifications by type (e.g. reports_download)."""
    try:
        delete_notifications_by_type(notification_type)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/read")
def notifications_mark_read():
    """Mark all notifications as read."""
    try:
        mark_notifications_read()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/{notification_id}/read")
def notification_mark_read(notification_id: int):
    """Mark a single notification as read."""
    try:
        ok = mark_notification_read(notification_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/notifications/{notification_id}")
def notification_delete(notification_id: int):
    """Delete a single notification (used for auto-delete after read)."""
    try:
        ok = delete_notification(notification_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Notification not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/alerts")
def list_alerts(limit: int = DEFAULT_ALERTS_LIMIT, unresolved_only: bool = True):
    """List critical-condition alerts (unresolved by default)."""
    try:
        run_seed_if_needed()
        items = get_alerts(limit=limit, unresolved_only=unresolved_only)
        return {"alerts": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/resolve-all")
def resolve_all_alerts_route():
    """Mark all unresolved alerts as resolved."""
    try:
        count = resolve_all_alerts()
        return {"status": "ok", "resolved": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/resolve")
def resolve_alert_route(body: Dict[str, Any]):
    """Mark a single alert as resolved. Body: { \"id\": 1 }."""
    alert_id = body.get("id")
    if alert_id is None:
        raise HTTPException(status_code=400, detail="id is required")
    try:
        aid = int(alert_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="id must be an integer")
    try:
        ok = resolve_alert(aid)
        if not ok:
            raise HTTPException(status_code=404, detail="Alert not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients")
def api_list_patients(removed_only: int = Query(0, ge=0, le=1, description="Set to 1 to list soft-deleted patients only.")):
    """
    List registered patients (active). Use removed_only=1 to list soft-deleted patients only.
    Integer flag parses reliably everywhere (bool query strings can be mishandled by some proxies/clients).
    """
    try:
        run_seed_if_needed()
        if removed_only == 1:
            items = list_removed_patients()
            return {"patients": items, "count": len(items), "removed_only": True}
        items = list_patients()
        return {"patients": items, "count": len(items), "removed_only": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _removed_patients_response() -> Dict[str, Any]:
    """Shared payload for removed-patient listing (soft-deleted rows)."""
    run_seed_if_needed()
    items = list_removed_patients()
    return {"patients": items, "count": len(items)}


@router.get("/patients/removed")
def api_list_removed_patients():
    """List patients removed from the register (soft-deleted); monitoring data is retained until restored."""
    try:
        return _removed_patients_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/removed-patients")
def api_list_removed_patients_unambiguous():
    """
    Same as GET /patients/removed but uses a path that cannot be mistaken for /patients/{patient_id}
    (some clients or router order treated 'removed' as an id and returned 422, which the UI showed as an empty list).
    """
    try:
        return _removed_patients_response()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}")
def api_get_patient(patient_id: int):
    """Get a single patient by id."""
    try:
        p = get_patient(patient_id)
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        p.pop("deleted_at", None)
        p.pop("mrn_backup", None)
        return p
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patients/{patient_id}/ensure-demo-monitoring")
def api_ensure_patient_demo_monitoring(patient_id: int):
    """If this patient has no monitoring rows yet, insert demo assessments, glucose, and doses (for demos / Records page)."""
    try:
        run_seed_if_needed()
        if not patient_exists(patient_id):
            raise HTTPException(status_code=404, detail="Patient not found")
        result = ensure_patient_demo_monitoring(patient_id)
        if not result.get("ok"):
            raise HTTPException(status_code=500, detail=result.get("error", "ensure failed"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patients/seed-demo")
def api_seed_demo_patients(body: Optional[Dict[str, Any]] = Body(default=None)):
    """Create named demo patients (if missing) and populate monitoring data. Optional body: {\"force\": true} to refresh readings."""
    try:
        run_seed_if_needed()
        force = bool((body or {}).get("force"))
        result = seed_demo_cohort(force=force)
        items = list_patients()
        return {"status": "ok", **result, "patients": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patients")
def api_create_patient(body: Dict[str, Any]):
    """Register a new patient."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    condition = (body.get("condition") or "Type 1 Diabetes").strip()
    date_of_birth = body.get("date_of_birth")
    gender = body.get("gender")
    medical_record_number = body.get("medical_record_number")
    try:
        pid = create_patient(
            name=name,
            condition=condition,
            date_of_birth=str(date_of_birth).strip() if date_of_birth else None,
            gender=str(gender).strip() if gender else None,
            medical_record_number=str(medical_record_number).strip() if medical_record_number else None,
        )
        return {"id": pid, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/patients/{patient_id}")
def api_update_patient(patient_id: int, body: Dict[str, Any]):
    """Update an existing patient."""
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    name = body.get("name")
    condition = body.get("condition")
    date_of_birth = body.get("date_of_birth")
    gender = body.get("gender")
    medical_record_number = body.get("medical_record_number")
    try:
        ok = update_patient(
            patient_id,
            name=str(name).strip() if name else None,
            condition=str(condition) if condition else None,
            date_of_birth=str(date_of_birth).strip() if date_of_birth else None,
            gender=str(gender) if gender else None,
            medical_record_number=str(medical_record_number).strip() if medical_record_number else None,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/patients/{patient_id}")
def api_delete_patient(patient_id: int):
    """Remove patient from the active list (soft delete). Linked monitoring data is kept for retrieval."""
    try:
        run_seed_if_needed()
        ok = delete_patient(patient_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {"status": "ok", "soft_deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/patients/{patient_id}/restore")
def api_restore_patient(patient_id: int):
    """Restore a soft-deleted patient to the active register (retrieves prior monitoring data)."""
    try:
        run_seed_if_needed()
        ok, err = restore_patient(patient_id)
        if err == "not_found":
            raise HTTPException(status_code=404, detail="Patient not found")
        if err == "not_removed":
            raise HTTPException(status_code=400, detail="Patient is not in the removed list")
        if err == "mrn_conflict":
            raise HTTPException(
                status_code=409,
                detail="Medical record number conflicts with another active patient. Change the other patient's MRN or edit this one after restore.",
            )
        if err == "restore_failed":
            raise HTTPException(status_code=500, detail="Could not restore patient (no row updated). Try again.")
        if not ok:
            raise HTTPException(status_code=500, detail="Could not restore patient")
        if err == "mrn_skipped_conflict":
            return {
                "status": "ok",
                "warning": "Restored without medical record number because it matched another active patient. Edit this patient to set a unique MRN (previous value kept in backup until you save).",
            }
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/records")
def api_patient_records(patient_id: int, limit: int = DEFAULT_RECORDS_LIMIT):
    """Get assessment records for a patient."""
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        records = get_records(limit=limit, patient_id=patient_id)
        return {"records": records, "count": len(records)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/glucose-readings")
def api_patient_glucose(patient_id: int, hours: int = DEFAULT_GLUCOSE_TRENDS_HOURS):
    """Get glucose readings for a patient."""
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        rows = get_glucose_readings(hours=hours, patient_id=patient_id)
        return {"readings": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/dose-events")
def api_patient_doses(patient_id: int, limit: int = 50):
    """Get dose events for a patient."""
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        events = get_dose_events(limit=limit, patient_id=patient_id)
        return {"events": events, "count": len(events)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/recent-activity")
def api_patient_recent_activity(patient_id: int):
    """
    Return latest glucose reading and latest insulin dose event for a patient.
    Used by the assessment form to show recent context when a clinician selects a patient.
    """
    if not patient_exists(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        # glucose_readings are sorted ascending by reading_at; last is newest
        readings = get_glucose_readings(hours=365 * 24, patient_id=patient_id)
        last_glucose = readings[-1] if readings else None
        # dose_events are sorted newest first
        doses = get_dose_events(limit=1, patient_id=patient_id)
        last_dose = doses[0] if doses else None
        # records are sorted newest first
        recs = get_records(limit=25, patient_id=patient_id)
        last_rec = next((r for r in recs if r.get("endpoint") == "recommend"), None)
        last_rec_summary = None
        if last_rec and isinstance(last_rec.get("response_summary"), dict):
            last_rec_summary = {
                "created_at": last_rec.get("created_at"),
                **last_rec.get("response_summary"),
            }
        return {
            "patient_id": patient_id,
            "last_glucose": last_glucose,
            "last_dose": last_dose,
            "last_recommendation": last_rec_summary,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup")
def api_create_backup():
    """Create a timestamped database backup."""
    try:
        path = create_backup()
        if path is None:
            raise HTTPException(status_code=500, detail="Backup failed")
        return {"status": "ok", "path": str(path)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backups")
def api_list_backups():
    """List available backups."""
    try:
        items = list_backups()
        return {"backups": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backups/restore")
def api_restore_backup(body: Dict[str, Any]):
    """Restore database from a backup. Body: { \"filename\": \"glucosense_20250101_120000.db\" }."""
    filename = body.get("filename")
    if not filename or not isinstance(filename, str):
        raise HTTPException(status_code=400, detail="filename is required")
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    try:
        ok = restore_backup(filename.strip())
        if not ok:
            raise HTTPException(status_code=404, detail="Backup not found or restore failed")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patient-context")
def patient_context():
    """Current patient context for sidebar (name, condition, recent metrics)."""
    try:
        run_seed_if_needed()
        ctx = get_patient_context()
        if not ctx:
            return {"name": "Current Patient", "condition": "Type 1 Diabetes", "glucose": None, "carbohydrates": None, "activity_minutes": None}
        return ctx
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/glucose-zones")
def glucose_zones():
    """Glucose interpretation & dosage chart (standard reference zones)."""
    return {"zones": GLUCOSE_ZONES}


@router.get("/glucose-zones/interpret")
def interpret_glucose(glucose: Optional[float] = None):
    """Return the zone and action for a given glucose value (mg/dL)."""
    if glucose is None:
        return {"glucose": None, "zone": None, "message": "Please provide a glucose value (e.g. ?glucose=120)."}
    try:
        gl = float(glucose)
    except (TypeError, ValueError):
        return {"glucose": glucose, "zone": None, "message": "Invalid glucose value; must be a number."}
    zone = get_glucose_zone(gl)
    if zone is None:
        return {"glucose": gl, "zone": None, "message": "No zone found for this value."}
    return {"glucose": gl, "zone": zone}


@router.get("/glucose-trends")
def glucose_trends(hours: int = DEFAULT_GLUCOSE_TRENDS_HOURS):
    """Glucose readings for chart. Returns series with time, actual, predicted."""
    try:
        try:
            run_seed_if_needed()
        except Exception:
            pass
        rows = get_glucose_readings(hours=hours)
        series = build_trend_series(rows)
        return {"series": series, "count": len(series)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dose")
def record_dose(body: Dict[str, Any]):
    """Record a dose administration event. patient_id links to the assessed patient."""
    meal_bolus = body.get("meal_bolus") or body.get("mealBolus")
    correction_dose = body.get("correction_dose") or body.get("correctionDose")
    total_dose = body.get("total_dose") or body.get("totalDose") or body.get("summary")
    request_id = body.get("request_id")
    patient_id = body.get("patient_id")
    pid = int(patient_id) if patient_id is not None else None
    try:
        mid = insert_dose_event(
            meal_bolus=str(meal_bolus) if meal_bolus is not None else None,
            correction_dose=str(correction_dose) if correction_dose is not None else None,
            total_dose=str(total_dose) if total_dose is not None else None,
            request_id=str(request_id) if request_id is not None else None,
            patient_id=pid,
        )
        return {"id": mid, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
def get_settings():
    """Get app settings (units, theme, etc.)."""
    try:
        run_seed_if_needed()
        return {
            "units": get_setting("units") or "mg/dL",
            "theme": get_setting("theme") or "light",
            "notifications_enabled": get_setting("notifications_enabled") != "false",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/settings")
def put_settings(body: Dict[str, Any]):
    """Update app settings."""
    try:
        if "units" in body:
            set_setting("units", str(body["units"]))
        if "theme" in body:
            set_setting("theme", str(body["theme"]))
        if "notifications_enabled" in body:
            set_setting("notifications_enabled", "true" if body["notifications_enabled"] else "false")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
