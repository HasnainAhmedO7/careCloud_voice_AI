import logging
import os
from typing import Optional

import httpx
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    RunContext,
    cli,
    function_tool,
    inference,
)
from livekit.agents.llm import ToolError

load_dotenv(".env.local")
load_dotenv(".env")

logger = logging.getLogger("patient-intake-agent")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
api_client = httpx.AsyncClient(base_url=API_BASE_URL, timeout=10.0)


def _error_message(response: httpx.Response) -> str:
    try:
        return response.json().get("error", {}).get("message", response.text)
    except ValueError:
        return response.text


@function_tool()
async def lookup_patient_by_phone(context: RunContext, phone_number: str) -> dict:
    """Check whether a patient record already exists for a given phone number.
    Call this as soon as you have collected the caller's phone number, before
    collecting the rest of their information, so you can offer to update an
    existing record instead of creating a duplicate.

    Args:
        phone_number: The caller's phone number as 10 digits, digits only.
    """
    resp = await api_client.get("/patients", params={"phone_number": phone_number})
    if resp.status_code != 200:
        raise ToolError(f"Could not check existing records: {_error_message(resp)}")
    matches = resp.json()["data"]
    if not matches:
        return {"found": False}
    patient = matches[0]
    logger.info("Duplicate check matched existing patient %s", patient["patient_id"])
    return {"found": True, "patient": patient}


@function_tool()
async def save_new_patient(
    context: RunContext,
    first_name: str,
    last_name: str,
    date_of_birth: str,
    sex: str,
    phone_number: str,
    address_line_1: str,
    city: str,
    state: str,
    zip_code: str,
    address_line_2: Optional[str] = None,
    email: Optional[str] = None,
    insurance_provider: Optional[str] = None,
    insurance_member_id: Optional[str] = None,
    preferred_language: str = "English",
    emergency_contact_name: Optional[str] = None,
    emergency_contact_phone: Optional[str] = None,
) -> dict:
    """Create a new patient record once the caller has confirmed all collected
    information is correct. Only call this after read-back confirmation.

    Args:
        first_name: Patient's first name, letters/hyphens/apostrophes only.
        last_name: Patient's last name, letters/hyphens/apostrophes only.
        date_of_birth: ISO format YYYY-MM-DD, must not be in the future.
        sex: One of "Male", "Female", "Other", "Decline to Answer".
        phone_number: 10 digits, digits only.
        address_line_1: Street address.
        city: City name.
        state: 2-letter U.S. state abbreviation.
        zip_code: 5-digit or ZIP+4 U.S. zip code.
        address_line_2: Apartment/suite/unit, if any.
        email: Email address, if provided.
        insurance_provider: Insurance company name, if provided.
        insurance_member_id: Alphanumeric member/subscriber ID, if provided.
        preferred_language: Defaults to "English" if not stated.
        emergency_contact_name: Full name, if provided.
        emergency_contact_phone: 10 digits, digits only, if provided.
    """
    payload = {
        "first_name": first_name,
        "last_name": last_name,
        "date_of_birth": date_of_birth,
        "sex": sex,
        "phone_number": phone_number,
        "address_line_1": address_line_1,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "address_line_2": address_line_2,
        "email": email,
        "insurance_provider": insurance_provider,
        "insurance_member_id": insurance_member_id,
        "preferred_language": preferred_language,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
    }
    resp = await api_client.post("/patients", json=payload)
    if resp.status_code != 201:
        # Surfaced to the LLM as a tool error so it can re-prompt for the
        # specific offending field instead of failing the whole call silently.
        raise ToolError(_error_message(resp))
    patient = resp.json()["data"]
    logger.info("Registered new patient %s: %s", patient["patient_id"], payload)
    return {"success": True, "patient": patient}


@function_tool()
async def update_existing_patient(
    context: RunContext,
    patient_id: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    date_of_birth: Optional[str] = None,
    sex: Optional[str] = None,
    phone_number: Optional[str] = None,
    address_line_1: Optional[str] = None,
    address_line_2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
    email: Optional[str] = None,
    insurance_provider: Optional[str] = None,
    insurance_member_id: Optional[str] = None,
    preferred_language: Optional[str] = None,
    emergency_contact_name: Optional[str] = None,
    emergency_contact_phone: Optional[str] = None,
) -> dict:
    """Update a returning caller's existing patient record. Only pass fields
    the caller actually confirmed changing or provided; omit everything else.

    Args:
        patient_id: The existing patient's UUID, from lookup_patient_by_phone.
    """
    payload = {
        k: v
        for k, v in locals().items()
        if k not in ("context", "patient_id") and v is not None
    }
    resp = await api_client.put(f"/patients/{patient_id}", json=payload)
    if resp.status_code != 200:
        raise ToolError(_error_message(resp))
    patient = resp.json()["data"]
    logger.info("Updated patient %s: %s", patient_id, payload)
    return {"success": True, "patient": patient}


INSTRUCTIONS = """
You are a warm, efficient patient intake coordinator answering a phone line for a
medical practice. You are speaking with a caller who wants to register as a new
patient. Sound natural and conversational — never read a rigid script or list
fields like a form. Keep responses brief; this is a phone call, not an email.

CALL FLOW

1. Greet the caller and briefly explain you'll get them registered.
2. Ask for their phone number early (you need it anyway) and immediately call
   lookup_patient_by_phone. If a record already exists, tell them: "It looks
   like we already have a record for [First Name] [Last Name]. Would you like
   to update your information instead?" If they agree, collect only the fields
   they want to change and use update_existing_patient at the end. If they say
   it's not them, or they want to register fresh, continue as a new patient.
3. Collect the required fields conversationally, in whatever order feels
   natural based on what the caller volunteers: first name, last name, date of
   birth, sex, phone number (already have it), street address, city, state,
   zip code. Ask clarifying questions if something is ambiguous.
4. Validate as you go, silently, against these rules — if something doesn't
   fit, ask again for just that field, explaining briefly why:
   - Names: letters, hyphens, or apostrophes only.
   - Date of birth: a real calendar date, not in the future. Convert whatever
     the caller says into YYYY-MM-DD before using it in a tool call.
   - Sex: Male, Female, Other, or Decline to Answer.
   - Phone numbers: exactly 10 US digits.
   - State: a real 2-letter US state abbreviation.
   - Zip code: 5 digits, or 5+4.
5. Once required fields are collected, offer optional fields in one line:
   "I can also collect your insurance information, emergency contact, and
   preferred language. Would you like to provide any of those?" Only collect
   what they opt into. Default preferred_language to English if not discussed.
6. Read back everything you collected in a natural sentence or two and ask the
   caller to confirm or correct anything before you save it. If they correct a
   field (e.g. "actually my last name is spelled D-A-V-I-S"), update just that
   field and confirm it back, then proceed — don't restart the whole read-back.
7. Once confirmed, call save_new_patient (or update_existing_patient for a
   returning caller). Relay the outcome honestly:
   - Success: a brief, warm confirmation — "You're all set, [First Name]!" —
     then end the call gracefully.
   - Failure: apologize, explain in plain language what needs fixing if the
     error names a specific field, and re-collect just that field. If saving
     fails repeatedly, apologize, let them know there's a technical issue, and
     end the call gracefully rather than looping forever.
8. If the caller wants to start over at any point, discard everything
   collected so far and begin re-collecting from scratch without judgment.
9. If the caller goes silent, gets interrupted, or answers out of order,
   adapt — don't repeat your entire previous prompt, just pick up naturally
   from what's still missing.

Never mention tool names, JSON, or internal system details to the caller.
"""


class PatientIntakeAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=INSTRUCTIONS,
            tools=[lookup_patient_by_phone, save_new_patient, update_existing_patient],
        )


server = AgentServer()


@server.rtc_session(agent_name="telephony_agent")
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        vad=inference.VAD(),
        stt=inference.STT("deepgram/nova-3", language="en"),
        llm=inference.LLM("google/gemma-4-31b-it"),
        tts=inference.TTS("cartesia/sonic-3", voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"),
    )
    await session.start(agent=PatientIntakeAgent(), room=ctx.room)
    await session.generate_reply(
        instructions="Greet the caller and ask how you can help them get registered today."
    )


if __name__ == "__main__":
    cli.run_app(server)
