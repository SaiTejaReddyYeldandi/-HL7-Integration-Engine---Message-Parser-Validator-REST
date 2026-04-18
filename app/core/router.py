"""
HL7 Message Router.

Simple routing logic based on message type.
"""

import logging

log = logging.getLogger(__name__)


ROUTING_TABLE = {
    "ADT^A01": ["EHR_MAIN", "BILLING_SYS", "PHARMACY", "LAB"],
    "ADT^A03": ["EHR_MAIN", "BILLING_SYS"],
    "ADT^A08": ["EHR_MAIN", "BILLING_SYS", "PHARMACY"],
    "ORU^R01": ["EHR_MAIN", "CLINICAL_PORTAL"],
    "ORM^O01": ["LAB", "PHARMACY"],
}


def route_message(parsed: dict) -> dict:
    """
    Determine downstream destinations for this message.
    """
    message_type = parsed.get("message_type", "")
    destinations = ROUTING_TABLE.get(message_type, [])

    filtered = False
    filter_reason = ""

    processing_id = parsed.get("processing_id", "")
    if processing_id == "T":
        filtered = True
        filter_reason = (
            "Message has processing_id=T (test), suppressed from downstream"
        )
        destinations = []

    if message_type == "ORU^R01":
        obx_count = sum(
            1 for s in parsed.get("segments", []) if s["segment"] == "OBX"
        )
        if obx_count == 0:
            filtered = True
            filter_reason = "ORU message has no OBX result segments — dropped"
            destinations = []

    log.info(
        "Routed %s -> %s (filtered=%s)",
        message_type, destinations, filtered,
    )

    return {
        "message_type": message_type,
        "destinations": destinations,
        "filtered": filtered,
        "filter_reason": filter_reason,
    }