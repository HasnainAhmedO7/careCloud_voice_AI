import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.envelope import ok
from app.schemas import PatientCreate, PatientOut, PatientUpdate

logger = logging.getLogger("patients")
router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
def list_patients(
    last_name: Optional[str] = Query(None),
    date_of_birth: Optional[date] = Query(None),
    phone_number: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    patients = crud.list_patients(db, last_name=last_name, date_of_birth=date_of_birth, phone_number=phone_number)
    return ok([PatientOut.model_validate(p).model_dump() for p in patients])


@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return ok(PatientOut.model_validate(patient).model_dump())


@router.post("", status_code=201)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)):
    patient = crud.create_patient(db, payload)
    logger.info("Created patient %s: %s", patient.patient_id, payload.model_dump())
    return ok(PatientOut.model_validate(patient).model_dump())


@router.put("/{patient_id}")
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    patient = crud.update_patient(db, patient, payload)
    logger.info("Updated patient %s: %s", patient_id, payload.model_dump(exclude_unset=True))
    return ok(PatientOut.model_validate(patient).model_dump())


@router.delete("/{patient_id}")
def delete_patient(patient_id: str, db: Session = Depends(get_db)):
    patient = crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    crud.soft_delete_patient(db, patient)
    logger.info("Soft-deleted patient %s", patient_id)
    return ok({"patient_id": patient_id, "deleted": True})
