from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Patient
from app.schemas import PatientCreate, PatientUpdate


def get_patient(db: Session, patient_id: str) -> Optional[Patient]:
    stmt = select(Patient).where(Patient.patient_id == patient_id, Patient.deleted_at.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def find_by_phone(db: Session, phone_number: str) -> Optional[Patient]:
    stmt = select(Patient).where(Patient.phone_number == phone_number, Patient.deleted_at.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def list_patients(
    db: Session,
    last_name: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    phone_number: Optional[str] = None,
) -> list[Patient]:
    stmt = select(Patient).where(Patient.deleted_at.is_(None))
    if last_name:
        stmt = stmt.where(Patient.last_name.ilike(last_name))
    if date_of_birth:
        stmt = stmt.where(Patient.date_of_birth == date_of_birth.isoformat())
    if phone_number:
        stmt = stmt.where(Patient.phone_number == phone_number)
    return list(db.execute(stmt).scalars().all())


def create_patient(db: Session, payload: PatientCreate) -> Patient:
    data = payload.model_dump()
    data["date_of_birth"] = data["date_of_birth"].isoformat()
    patient = Patient(**data)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


def update_patient(db: Session, patient: Patient, payload: PatientUpdate) -> Patient:
    updates = payload.model_dump(exclude_unset=True)
    if "date_of_birth" in updates and updates["date_of_birth"] is not None:
        updates["date_of_birth"] = updates["date_of_birth"].isoformat()
    for field, value in updates.items():
        setattr(patient, field, value)
    patient.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient


def soft_delete_patient(db: Session, patient: Patient) -> Patient:
    patient.deleted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(patient)
    return patient
