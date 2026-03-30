"""Auth routes - thin layer, delegates to service."""
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session

from api.shared.database import get_db
from api.shared.dependencies import get_current_user
from api.models import User
from api.core.config import GLUCOSENSE_EMBED_KEY
from api.modules.auth.schemas import RegisterInput, LoginInput, ProfilePatchInput, GlucosenseEmbedInput
from api.modules.auth.service import (
    create_token,
    validate_username_available,
    create_user,
    authenticate_user,
    apply_profile_patch,
    get_or_create_user_for_glucosense_embed,
)
from api.core.exceptions import AppError, to_http_exception
from api.core.logging_config import get_logger

logger = get_logger("api.auth.router")

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterInput, db: Session = Depends(get_db)):
    """Register new user."""
    try:
        validate_username_available(db, data.username, data.email)
        user = create_user(db, data.model_dump())
        token = create_token(user.id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({"user": user.to_dict(), "token": token}),
        )
    except HTTPException:
        raise
    except AppError as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.exception("Registration failed")
        raise HTTPException(400, str(e)) from e


@router.post("/integration/glucosense")
def glucosense_embed_session(
    data: GlucosenseEmbedInput,
    db: Session = Depends(get_db),
    x_glucosense_embed_key: str | None = Header(default=None, alias="X-Glucosense-Embed-Key"),
):
    """
    Issue a Meal Plan JWT for the GlucoSense user without a second password login.
    Requires a shared embed key (dev default matches GlucoSense VITE_MEAL_PLAN_EMBED_SECRET).
    """
    if not x_glucosense_embed_key or x_glucosense_embed_key != GLUCOSENSE_EMBED_KEY:
        raise HTTPException(403, "Invalid or missing embed key")
    try:
        user = get_or_create_user_for_glucosense_embed(
            db,
            email=str(data.email),
            display_name=data.display_name,
            role=data.role,
        )
        token = create_token(user.id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({"user": user.to_dict(), "token": token}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("GlucoSense embed session failed")
        raise HTTPException(400, str(e)) from e


@router.post("/login")
def login(data: LoginInput, db: Session = Depends(get_db)):
    """Login user."""
    try:
        user = authenticate_user(db, data.username, data.password)
        token = create_token(user.id)
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder({"user": user.to_dict(), "token": token}),
        )
    except HTTPException:
        raise
    except AppError as e:
        raise to_http_exception(e)
    except OperationalError as e:
        logger.exception("Login failed: database error")
        raise HTTPException(
            503,
            "Database error (locked, missing migration, or bad file). "
            "Stop other API instances using the same DB, or reset %LOCALAPPDATA%\\Glocusense\\glocusense.db and restart.",
        ) from e
    except SQLAlchemyError as e:
        logger.exception("Login failed: SQLAlchemy error")
        raise HTTPException(503, "Database error. Try again in a few seconds.") from e
    except Exception as e:
        logger.exception("Login failed")
        raise HTTPException(401, str(e)) from e


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Get current user."""
    return {"user": user.to_dict()}


@router.patch("/profile")
def patch_profile(
    data: ProfilePatchInput,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update profile fields (partial)."""
    try:
        patch = data.model_dump(exclude_unset=True)
        apply_profile_patch(user, patch)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"user": user.to_dict()}
    except Exception as e:
        db.rollback()
        logger.exception("Profile update failed")
        raise HTTPException(400, str(e)) from e


@router.post("/onboarding/complete")
def complete_onboarding(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark onboarding finished (web app first-run flow)."""
    try:
        user.onboarding_completed = True
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"user": user.to_dict()}
    except Exception as e:
        db.rollback()
        logger.exception("Onboarding complete failed")
        raise HTTPException(400, str(e)) from e
