"""
FastAPI route definitions for GlucoSense Clinical Support API.

Endpoints: POST /predict, POST /explain, POST /recommend, GET /model-info, etc.
Input validation and structured JSON responses with clinical metadata.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..config.schema import DashboardConfig, GLUCOSE_ZONES, get_glucose_zone
from ..safety.audit import log_prediction
from ..monitoring import get_monitor
from ..storage import (
    init_db,
    insert_record,
    insert_smart_sensor_prediction,
    insert_clinician_feedback,
    get_clinician_feedback,
    get_records,
    get_notifications,
    insert_notification,
    delete_notifications_by_type,
    mark_notifications_read,
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
    list_patients,
    get_patient,
    create_patient,
    update_patient,
    patient_exists,
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["GlucoSense"])


@router.get("/health/live", tags=["health"])
def api_health_live():
    """Liveness only — no DB or model (Vite proxy + UI wait-on use this)."""
    return JSONResponse(content={"status": "ok", "live": True})


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
            detail=f"Model not loaded. Run: python scripts/run_smart_sensor_ml.py. Error: {e}"
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
    """Readiness: DB + seed. Always returns HTTP 200 JSON (use /api/health/live for liveness only)."""
    try:
        init_db()
    except BaseException as e:
        logger.exception("GET /api/health: init_db failed")
        return JSONResponse(
            status_code=200,
            content={"status": "degraded", "database": str(e)},
        )
    try:
        run_seed_if_needed()
    except BaseException as e:
        logger.exception("GET /api/health: run_seed_if_needed failed")
        return JSONResponse(
            status_code=200,
            content={"status": "ok", "database": f"ready (seed: {e})"},
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "database": "ready"},
    )


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
def api_list_patients():
    """List all registered patients."""
    try:
        run_seed_if_needed()
        items = list_patients()
        return {"patients": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}")
def api_get_patient(patient_id: int):
    """Get a single patient by id."""
    try:
        p = get_patient(patient_id)
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        return p
    except HTTPException:
        raise
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
