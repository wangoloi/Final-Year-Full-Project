"""Demo API for SmartSensor_DiabetesMonitoring.csv (synthetic wearable-style data)."""
from fastapi import APIRouter, Depends, HTTPException, Query

from api.models import User
from api.shared.dependencies import get_current_user
from api.modules.sensor_demo import service

router = APIRouter(prefix="/api/sensor-demo", tags=["sensor-demo"])


@router.get("/meta")
def sensor_meta(user: User = Depends(get_current_user)):
    """Dataset shape and row count (auth required like other app APIs)."""
    return service.dataset_meta()


@router.get("/patients")
def sensor_patients(
    limit: int = Query(80, ge=1, le=200),
    user: User = Depends(get_current_user),
):
    return {"patients": service.distinct_patients(limit=limit)}


@router.get("/series")
def sensor_series(
    patient_id: str = Query(..., min_length=1, max_length=128),
    limit: int = Query(200, ge=1, le=2000),
    user: User = Depends(get_current_user),
):
    rows = service.series_for_patient(patient_id, limit=limit)
    if not rows:
        raise HTTPException(status_code=404, detail="No rows for that patient_id (or CSV empty).")
    return {"patient_id": patient_id, "readings": rows}


@router.get("/summary")
def sensor_summary(
    patient_id: str = Query(..., min_length=1, max_length=128),
    last_n: int = Query(96, ge=1, le=2000),
    user: User = Depends(get_current_user),
):
    return service.summary_for_patient(patient_id, last_n=last_n)
