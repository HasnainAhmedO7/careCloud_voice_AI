import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.database import Base, SessionLocal, engine
from app.envelope import fail
from app.models import Patient
from app.routers import patients
from app.schemas import PatientCreate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("app")

app = FastAPI(title="Patient Registration API")
app.include_router(patients.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content=fail(str(exc.detail)))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = "; ".join(f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors())
    return JSONResponse(status_code=422, content=fail(messages))


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content=fail("Internal server error"))


@app.get("/health")
def health():
    return {"status": "ok"}


SEED_PATIENTS = [
    PatientCreate(
        first_name="Jane",
        last_name="Doe",
        date_of_birth="1985-06-15",
        sex="Female",
        phone_number="5551234567",
        email="jane.doe@example.com",
        address_line_1="123 Main St",
        city="Springfield",
        state="IL",
        zip_code="62704",
    ),
    PatientCreate(
        first_name="John",
        last_name="Smith",
        date_of_birth="1978-11-02",
        sex="Male",
        phone_number="5559876543",
        address_line_1="456 Oak Ave",
        city="Austin",
        state="TX",
        zip_code="73301",
    ),
]


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Patient).count() == 0:
            for seed in SEED_PATIENTS:
                data = seed.model_dump()
                data["date_of_birth"] = data["date_of_birth"].isoformat()
                db.add(Patient(**data))
            db.commit()
            logger.info("Seeded %d demo patients", len(SEED_PATIENTS))
    finally:
        db.close()
