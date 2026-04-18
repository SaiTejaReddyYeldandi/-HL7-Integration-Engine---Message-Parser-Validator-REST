"""Tests for ACK generation."""

from app.core.ack import build_ack, determine_ack_code


SAMPLE_PARSED = {
    "message_type": "ADT^A01",
    "sending_app": "ADMIT_SYS",
    "sending_facility": "CITY_HOSP",
    "receiving_app": "HIS",
    "receiving_facility": "OPTUM",
    "message_control_id": "MSG001",
}


def test_ack_aa_format():
    ack = build_ack(SAMPLE_PARSED, "AA")
    assert ack.startswith("MSH|")
    assert "|ACK|" in ack
    assert "MSA|AA|MSG001" in ack


def test_ack_sender_receiver_swapped():
    ack = build_ack(SAMPLE_PARSED, "AA")
    assert "|HIS|OPTUM|ADMIT_SYS|CITY_HOSP|" in ack


def test_ack_ae_carries_error():
    ack = build_ack(SAMPLE_PARSED, "AE", "PID.3 is empty")
    assert "MSA|AE|MSG001|PID.3 is empty" in ack


def test_determine_ack_valid():
    code, err = determine_ack_code({"valid": True, "errors": []})
    assert code == "AA"


def test_determine_ack_invalid():
    code, err = determine_ack_code({
        "valid": False,
        "errors": ["PID.3 empty", "MSH.7 bad"],
    })
    assert code == "AE"
    assert "PID.3" in err