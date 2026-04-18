"""
HL7 v2 Parser — breaks raw HL7 messages into structured dicts.

HL7 v2 structure recap:
- Messages = segments separated by \\r (carriage return) or \\n (newline)
- Segments = fields separated by | (pipe)
- Fields  = components separated by ^ (caret)

The delimiters themselves are declared in MSH-1 and MSH-2 of every message.
MSH-1 is always the field separator (|). MSH-2 is always the encoding
characters: ^~\\& (component, repetition, escape, sub-component).

We parse these defensively so a broken message gives us a useful error
instead of a crash.
"""

import logging

log = logging.getLogger(__name__)


def _split_segments(raw_message: str) -> list:
    """
    Split a raw HL7 message into individual segments.

    HL7 messages in the wild use \\r as segment separator, but when saved
    to disk on Windows they often become \\r\\n, and sometimes just \\n.
    We normalise all three.
    """
    if not raw_message or not raw_message.strip():
        raise ValueError("Empty message")

    normalised = raw_message.replace("\r\n", "\n").replace("\r", "\n")
    segments = [s for s in normalised.split("\n") if s.strip()]

    if not segments:
        raise ValueError("No segments found in message")

    if not segments[0].startswith("MSH"):
        raise ValueError(f"First segment must be MSH, got: {segments[0][:3]}")

    return segments


def _parse_segment(segment_line: str) -> dict:
    """
    Parse one segment into a dict of field_number -> raw_string.

    Field 0 is always the segment name itself (e.g. 'PID').
    """
    fields = segment_line.split("|")
    segment_name = fields[0]

    parsed = {
        "segment": segment_name,
        "fields": {},
        "raw": segment_line,
    }

    for i, value in enumerate(fields):
        parsed["fields"][i] = value

    return parsed


def _get_field(parsed_segment: dict, field_num: int) -> str:
    """Safe field getter — returns empty string if field doesn't exist."""
    return parsed["fields"].get(field_num, "") if (parsed := parsed_segment) else ""


def _get_component(field_value: str, component_num: int) -> str:
    """
    Split a field by ^ and return a specific component.
    component_num is 1-based to match HL7 documentation convention.

    Example: 'Doyle^Sean^Michael' with component_num=1 returns 'Doyle'
    """
    if not field_value:
        return ""

    components = field_value.split("^")

    if component_num < 1 or component_num > len(components):
        return ""

    return components[component_num - 1]


def parse_message(raw_message: str) -> dict:
    """
    Main parsing entry point.

    Returns a dict with:
      - message_type: e.g. 'ADT^A01'
      - trigger_event: e.g. 'A01'
      - sending_app, sending_facility, receiving_app, receiving_facility
      - message_control_id
      - timestamp
      - segments: list of all parsed segments
      - patient: extracted patient info (if PID present)
    """
    segments = _split_segments(raw_message)
    parsed_segments = [_parse_segment(s) for s in segments]

    msh = parsed_segments[0]

    # Important:
    # After split('|'), Python indexes do NOT exactly match HL7 MSH field numbers.
    # For your message:
    # fields[0] = MSH
    # fields[1] = ^~\&
    # fields[2] = sending_app
    # fields[3] = sending_facility
    # fields[4] = receiving_app
    # fields[5] = receiving_facility
    # fields[6] = timestamp
    # fields[8] = message_type
    # fields[9] = message_control_id
    # fields[10] = processing_id
    # fields[11] = version
    message_type_raw = _get_field(msh, 8)
    trigger_event = _get_component(message_type_raw, 2)

    result = {
        "message_type": message_type_raw,
        "trigger_event": trigger_event,
        "sending_app": _get_field(msh, 2),
        "sending_facility": _get_field(msh, 3),
        "receiving_app": _get_field(msh, 4),
        "receiving_facility": _get_field(msh, 5),
        "timestamp": _get_field(msh, 6),
        "message_control_id": _get_field(msh, 9),
        "processing_id": _get_field(msh, 10),
        "version": _get_field(msh, 11),
        "segments": parsed_segments,
        "segment_names": [s["segment"] for s in parsed_segments],
        "patient": None,
    }

    pid = next((s for s in parsed_segments if s["segment"] == "PID"), None)

    if pid:
        pid3 = _get_field(pid, 3)
        pid5 = _get_field(pid, 5)
        pid11 = _get_field(pid, 11)

        result["patient"] = {
            "patient_id": _get_component(pid3, 1),
            "assigning_authority": _get_component(pid3, 4),
            "id_type": _get_component(pid3, 5),
            "family_name": _get_component(pid5, 1),
            "given_name": _get_component(pid5, 2),
            "middle_name": _get_component(pid5, 3),
            "date_of_birth": _get_field(pid, 7),
            "gender": _get_field(pid, 8),
            "street": _get_component(pid11, 1),
            "city": _get_component(pid11, 3),
            "postcode": _get_component(pid11, 5),
            "phone": _get_field(pid, 13),
        }

    log.info(
        "Parsed %s message | control_id=%s | patient=%s",
        result["message_type"],
        result["message_control_id"],
        result["patient"]["patient_id"] if result["patient"] else "N/A",
    )

    return result