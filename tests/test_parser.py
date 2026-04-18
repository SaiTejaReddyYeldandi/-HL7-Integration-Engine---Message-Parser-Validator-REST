"""Unit tests for the HL7 parser."""

import pytest
from app.core.parser import parse_message

ADT_VALID = (
    "MSH|^~\\&|ADMIT_SYS|CITY_HOSP|HIS|OPTUM|20260418120000||ADT^A01|"
    "MSG001|P|2.5\r"
    "EVN|A01|20260418120000\r"
    "PID|1||PAT123^^^CITY_HOSP^MR||Doyle^Sean^Michael||19850315|M|||"
    "15 Grafton St^^Dublin^^D02||0871234567\r"
    "PV1|1|I|WARD4^ROOM2^BED1|E||||DOC001^Murphy^Patrick"
)


def test_parse_returns_message_type():
    result = parse_message(ADT_VALID)
    assert result["message_type"] == "ADT^A01"
    assert result["trigger_event"] == "A01"


def test_parse_extracts_msh_fields():
    result = parse_message(ADT_VALID)
    assert result["sending_app"] == "ADMIT_SYS"
    assert result["sending_facility"] == "CITY_HOSP"
    assert result["receiving_app"] == "HIS"
    assert result["message_control_id"] == "MSG001"


def test_parse_extracts_patient():
    result = parse_message(ADT_VALID)
    patient = result["patient"]
    assert patient is not None
    assert patient["patient_id"] == "PAT123"
    assert patient["family_name"] == "Doyle"
    assert patient["given_name"] == "Sean"
    assert patient["date_of_birth"] == "19850315"
    assert patient["gender"] == "M"
    assert patient["city"] == "Dublin"


def test_parse_segment_names():
    result = parse_message(ADT_VALID)
    assert result["segment_names"] == ["MSH", "EVN", "PID", "PV1"]


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        parse_message("")


def test_parse_no_msh_raises():
    with pytest.raises(ValueError):
        parse_message("PID|1||PAT123")


def test_parse_handles_crlf():
    crlf = ADT_VALID.replace("\r", "\r\n")
    result = parse_message(crlf)
    assert result["message_type"] == "ADT^A01"