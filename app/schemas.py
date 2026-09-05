import re
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL", "IN",
    "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV",
    "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC", "SD", "TN",
    "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC",
}

NAME_RE = re.compile(r"^[A-Za-z'-]{1,50}$")
ZIP_RE = re.compile(r"^\d{5}(-\d{4})?$")
ALNUM_RE = re.compile(r"^[A-Za-z0-9]+$")

Sex = Literal["Male", "Female", "Other", "Decline to Answer"]


def _validate_name(v: str) -> str:
    if not NAME_RE.match(v):
        raise ValueError("must be 1-50 alphabetic characters, hyphens, or apostrophes")
    return v


def _validate_phone(v: str) -> str:
    digits = re.sub(r"\D", "", v)
    if len(digits) != 10:
        raise ValueError("must be a valid U.S. 10-digit phone number")
    return digits


def _validate_dob(v: date) -> date:
    if v > date.today():
        raise ValueError("date of birth cannot be in the future")
    return v


def _validate_state(v: str) -> str:
    v = v.upper()
    if v not in US_STATES:
        raise ValueError("must be a valid 2-letter U.S. state abbreviation")
    return v


def _validate_zip(v: str) -> str:
    if not ZIP_RE.match(v):
        raise ValueError("must be a 5-digit or ZIP+4 U.S. zip code")
    return v


def _validate_member_id(v: str) -> str:
    if not ALNUM_RE.match(v):
        raise ValueError("must be alphanumeric")
    return v


class PatientBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    date_of_birth: date
    sex: Sex
    phone_number: str
    email: Optional[EmailStr] = None
    address_line_1: str = Field(..., min_length=1)
    address_line_2: Optional[str] = None
    city: str = Field(..., min_length=1, max_length=100)
    state: str
    zip_code: str
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: str = "English"
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    _v_first_name = field_validator("first_name")(_validate_name)
    _v_last_name = field_validator("last_name")(_validate_name)
    _v_dob = field_validator("date_of_birth")(_validate_dob)
    _v_phone = field_validator("phone_number")(_validate_phone)
    _v_state = field_validator("state")(_validate_state)
    _v_zip = field_validator("zip_code")(_validate_zip)

    @field_validator("insurance_member_id")
    @classmethod
    def _v_member_id(cls, v: Optional[str]) -> Optional[str]:
        return _validate_member_id(v) if v else v

    @field_validator("emergency_contact_phone")
    @classmethod
    def _v_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v else v


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=50)
    last_name: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[date] = None
    sex: Optional[Sex] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address_line_1: Optional[str] = None
    address_line_2: Optional[str] = None
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = None
    zip_code: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_member_id: Optional[str] = None
    preferred_language: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None

    _v_first_name = field_validator("first_name")(lambda cls, v: _validate_name(v) if v else v)
    _v_last_name = field_validator("last_name")(lambda cls, v: _validate_name(v) if v else v)

    @field_validator("date_of_birth")
    @classmethod
    def _v_dob(cls, v: Optional[date]) -> Optional[date]:
        return _validate_dob(v) if v else v

    @field_validator("phone_number")
    @classmethod
    def _v_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v else v

    @field_validator("state")
    @classmethod
    def _v_state(cls, v: Optional[str]) -> Optional[str]:
        return _validate_state(v) if v else v

    @field_validator("zip_code")
    @classmethod
    def _v_zip(cls, v: Optional[str]) -> Optional[str]:
        return _validate_zip(v) if v else v

    @field_validator("insurance_member_id")
    @classmethod
    def _v_member_id(cls, v: Optional[str]) -> Optional[str]:
        return _validate_member_id(v) if v else v

    @field_validator("emergency_contact_phone")
    @classmethod
    def _v_emergency_phone(cls, v: Optional[str]) -> Optional[str]:
        return _validate_phone(v) if v else v


class PatientOut(PatientBase):
    patient_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
