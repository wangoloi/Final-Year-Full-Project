"""Auth service - single responsibility: user auth logic."""
import re
import secrets
import time
import jwt

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from api.models import User
from api.core.config import JWT_SECRET
from api.core.exceptions import ValidationError, AuthError
from api.core.logging_config import get_logger

logger = get_logger("api.auth.service")


def create_token(user_id: int) -> str:
    """Generate JWT for user."""
    # Integer exp avoids PyJWT/datetime edge cases across versions
    payload = {"userId": user_id, "exp": int(time.time()) + 7 * 24 * 3600}
    secret = JWT_SECRET if isinstance(JWT_SECRET, str) else str(JWT_SECRET)
    token = jwt.encode(payload, secret, algorithm="HS256")
    # PyJWT 1.x returns bytes; 2.x returns str — JSON response must be str
    if isinstance(token, bytes):
        return token.decode("utf-8")
    return token


def validate_username_available(db: Session, username: str, email: str) -> None:
    """Raise if username or email already in use."""
    try:
        existing = db.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
    except OperationalError as e:
        logger.exception("validate_username_available: database error")
        raise ValidationError(
            "Database error (try again in a few seconds, or restart the API). If this persists, see README for resetting SQLite."
        ) from e
    if existing:
        raise ValidationError("Username or email already exists")


def create_user(db: Session, data: dict) -> User:
    """Create and persist user."""
    user = User(
        username=data["username"],
        email=data["email"],
        first_name=data.get("first_name"),
        last_name=data.get("last_name"),
        has_diabetes=data.get("has_diabetes", False),
        diabetes_type=data.get("diabetes_type"),
    )
    user.set_password(data["password"])
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValidationError("Username or email already exists") from None
    except OperationalError:
        db.rollback()
        logger.exception("Database error during user registration (schema or disk issue)")
        raise ValidationError(
            "Database error. If you recently updated the app, delete the old SQLite file and restart: "
            "Windows: %LocalAppData%\\Glocusense\\glocusense.db"
        ) from None
    except SQLAlchemyError:
        db.rollback()
        logger.exception("SQLAlchemy error during user registration")
        raise ValidationError(
            "Could not save account (database error). Try deleting the old DB file and restart the API — "
            "Windows: %LocalAppData%\\Glocusense\\glocusense.db"
        ) from None
    db.refresh(user)
    logger.info("User registered", extra={"user_id": user.id})
    return user


def find_user_by_username_or_email(db: Session, identifier: str) -> User | None:
    """Find user by username or email."""
    return db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    """Validate credentials and return user."""
    user = find_user_by_username_or_email(db, identifier)
    if not user:
        raise AuthError("Invalid username or password")

    if not user.check_password(password):
        raise AuthError("Invalid username or password")

    logger.info("User logged in", extra={"user_id": user.id})
    return user


def get_or_create_user_for_glucosense_embed(
    db: Session,
    email: str,
    display_name: str | None,
    role: str,
) -> User:
    """
    Return existing user by email, or create one with a random password (never used for login).
    Onboarding is marked complete so the embedded app opens directly to /app.
    """
    normalized_email = (email or "").strip().lower()
    user = db.query(User).filter(User.email == normalized_email).first()
    if user:
        return user

    local = (normalized_email.split("@")[0] if "@" in normalized_email else normalized_email) or "user"
    local = re.sub(r"[^a-zA-Z0-9_]", "_", local)[:24] or "user"
    username = local
    n = 0
    while db.query(User).filter(User.username == username).first():
        n += 1
        username = f"{local[:20]}_{n}"

    first = (display_name or local).strip()[:50] or None
    random_password = secrets.token_urlsafe(32)
    user = User(
        username=username,
        email=normalized_email,
        first_name=first,
        has_diabetes=role == "patient",
        diabetes_type="type1" if role == "patient" else None,
    )
    user.set_password(random_password)
    user.onboarding_completed = True
    user.profile_completed = True
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        user = db.query(User).filter(User.email == normalized_email).first()
        if user:
            return user
        raise
    db.refresh(user)
    logger.info("GlucoSense embed user provisioned", extra={"user_id": user.id, "email": normalized_email})
    return user


def apply_profile_patch(user: User, data: dict) -> User:
    """Apply non-None fields from patch dict to user (mutates in memory; caller commits)."""
    field_map = {
        "first_name",
        "last_name",
        "age",
        "gender",
        "height",
        "weight",
        "activity_level",
        "has_diabetes",
        "diabetes_type",
        "target_blood_glucose_min",
        "target_blood_glucose_max",
        "profile_completed",
    }
    for key in field_map:
        if key in data and data[key] is not None:
            setattr(user, key, data[key])
    return user
