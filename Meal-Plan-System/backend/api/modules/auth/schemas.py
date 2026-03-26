"""Auth request/response schemas."""
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal


class ProfilePatchInput(BaseModel):
    """Partial profile update (all fields optional)."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activity_level: Optional[str] = None
    has_diabetes: Optional[bool] = None
    diabetes_type: Optional[str] = None
    target_blood_glucose_min: Optional[float] = None
    target_blood_glucose_max: Optional[float] = None
    profile_completed: Optional[bool] = None


class RegisterInput(BaseModel):
    username: str
    email: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    has_diabetes: bool = False
    diabetes_type: Optional[str] = None


class LoginInput(BaseModel):
    username: str
    password: str


class GlucosenseEmbedInput(BaseModel):
    """Trusted hand-off from GlucoSense portal (requires X-Glucosense-Embed-Key)."""

    email: EmailStr
    display_name: Optional[str] = None
    role: Literal["clinician", "patient"] = "patient"
