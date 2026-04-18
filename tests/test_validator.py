"""Unit tests for the validator."""

from app.core.parser import parse_message
from app.core.validator import validate_message


ADT_VALID = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|20260418120000||ADT^A01|"
    "MSG001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PID|1||PAT123^^^CITY_HOSP^MR||Doyle^Sean^Michael||19850315|M\r"
    "PV1|1|I|WARD4^ROOM2^BED1"
)

ADT_MISSING_PID = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|20260418120000||ADT^A01|"
    "MSG001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PV1|1|I|WARD4"
)

ADT_EMPTY_PATIENT_ID = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|20260418120000||ADT^A01|"
    "MSG001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PID|1||||Doyle^Sean||19850315|M\r"
    "PV1|1|I|WARD4"
)

ADT_BAD_TIMESTAMP = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|18-04-2026||ADT^A01|"
    "MSG001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PID|1||PAT123||Doyle^Sean||19850315|M\r"
    "PV1|1|I|WARD4"
)


def test_valid_message_passes():
    parsed = parse_message(ADT_VALID)
    result = validate_message(parsed)
    assert result["valid"] is True
    assert result["errors"] == []


def test_missing_required_segment_fails():
    parsed = parse_message(ADT_MISSING_PID)
    result = validate_message(parsed)
    assert result["valid"] is False
    assert any("PID" in e for e in result["errors"])


def test_empty_patient_id_fails():
    parsed = parse_message(ADT_EMPTY_PATIENT_ID)
    result = validate_message(parsed)
    assert result["valid"] is False
    assert any("PID.3" in e for e in result["errors"])


def test_bad_timestamp_fails():
    parsed = parse_message(ADT_BAD_TIMESTAMP)
    result = validate_message(parsed)
    assert result["valid"] is False
    assert any("timestamp" in e.lower() for e in result["errors"])