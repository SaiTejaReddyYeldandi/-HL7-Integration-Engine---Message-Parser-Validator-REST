"""
HL7 v2 Validator — checks required segments and fields per message type.

This is where most real-world integration errors surface. Interview scenarios
usually come down to "message X arrived but is missing field Y — what does
your engine do?" The answer: validate, log a descriptive error, and return
an AE (Application Error) ACK so the sender knows to fix it.

Validation levels:
  - ERROR: violates a must-have rule — message is rejected
  - WARNING: unusual but not rejectable — logged for review
"""

import re
import logging

log = logging.getLogger(__name__)


REQUIRED_SEGMENTS = {
    "ADT^A01": ["MSH", "EVN", "PID", "PV1"],
    "ADT^A03": ["MSH", "EVN", "PID", "PV1"],
    "ADT^A08": ["MSH", "EVN", "PID", "PV1"],
    "ORU^R01": ["MSH", "PID", "OBR", "OBX"],
    "ORM^O01": ["MSH", "PID", "ORC", "OBR"],
}

# Important:
# These indexes match YOUR parsed MSH fields after split("|")
# not raw HL7 spec numbering.
REQUIRED_MSH_FIELDS = {
    2: "Sending Application",
    3: "Sending Facility",
    4: "Receiving Application",
    5: "Receiving Facility",
    6: "Message Timestamp",
    8: "Message Type",
    9: "Message Control ID",
    11: "Version ID",
}

REQUIRED_PID_FIELDS = {
    3: "Patient ID (PID.3)",
    5: "Patient Name (PID.5)",
}


def _is_valid_hl7_datetime(value: str) -> bool:
    """HL7 datetime format: YYYYMMDD or YYYYMMDDHHMM or YYYYMMDDHHMMSS."""
    if not value:
        return False
    return bool(re.match(r"^\d{8}(\d{4}(\d{2})?)?$", value))


def _get(segment: dict, field_num: int) -> str:
    return segment["fields"].get(field_num, "")


def validate_message(parsed: dict) -> dict:
    """
    Run all validation checks on a parsed message.

    Returns:
      {
        "valid": bool,
        "errors": list of str,
        "warnings": list of str,
        "message_type": str,
      }
    """
    errors = []
    warnings = []

    message_type = parsed.get("message_type", "")
    segment_names = parsed.get("segment_names", [])
    segments = parsed.get("segments", [])

    if not message_type:
        errors.append("MSH Message Type is missing")
    elif message_type not in REQUIRED_SEGMENTS:
        warnings.append(
            f"Message type '{message_type}' is not in the configured routing table"
        )

    required_segs = REQUIRED_SEGMENTS.get(message_type, ["MSH", "PID"])
    for req_seg in required_segs:
        if req_seg not in segment_names:
            errors.append(f"Missing required segment: {req_seg}")

    msh = segments[0] if segments else None
    if msh:
        for field_num, field_desc in REQUIRED_MSH_FIELDS.items():
            value = _get(msh, field_num)
            if not value:
                errors.append(f"MSH field {field_num} ({field_desc}) is empty")

        ts = _get(msh, 6)
        if ts and not _is_valid_hl7_datetime(ts):
            errors.append(
                f"MSH timestamp '{ts}' is not a valid HL7 datetime"
            )

        version = _get(msh, 11)
        if version and not version.startswith("2."):
            warnings.append(f"MSH version '{version}' is unusual")

    pid = next((s for s in segments if s["segment"] == "PID"), None)
    if pid:
        for field_num, field_desc in REQUIRED_PID_FIELDS.items():
            value = _get(pid, field_num)
            if not value:
                errors.append(f"PID.{field_num} ({field_desc}) is empty")

        dob = _get(pid, 7)
        if dob and not _is_valid_hl7_datetime(dob):
            warnings.append(
                f"PID.7 Date of Birth '{dob}' is not in HL7 format YYYYMMDD"
            )

        gender = _get(pid, 8)
        if gender and gender.upper() not in ("M", "F", "O", "U", "A", "N"):
            warnings.append(
                f"PID.8 Gender '{gender}' is not a recognised HL7 code"
            )

    if message_type == "ORU^R01":
        obx_segs = [s for s in segments if s["segment"] == "OBX"]
        if not obx_segs:
            errors.append("ORU^R01 message has no OBX (result) segments")
        for i, obx in enumerate(obx_segs, 1):
            if not _get(obx, 5):
                warnings.append(f"OBX #{i} has no observation value (OBX.5 empty)")

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "message_type": message_type,
    }

    log.info(
        "Validated %s | valid=%s | errors=%d | warnings=%d",
        message_type, result["valid"], len(errors), len(warnings),
    )
    return result