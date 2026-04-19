# HL7 Integration Engine — Message Parser, Validator & REST API

> A Python-based HL7 v2 integration engine built to understand healthcare
> interoperability hands-on — the same workflow pattern that Rhapsody,
> Cloverleaf, InterSystems Ensemble/IRIS, and Mirth Connect run in every
> hospital and health service in the world.

**What it does in one sentence:** receives raw HL7 v2 messages over an HTTP API, parses them into structured data, validates the required segments and fields, routes them to configured downstream destinations, generates a standards-compliant ACK response, stores the full transaction in a SQLite log, and exposes all of it through a REST API backed by a 22-test pytest suite running in GitHub Actions.

---

## Quick Run

```bash
git clone https://github.com/SaiTejaReddyYeldandi/-HL7-Integration-Engine---Message-Parser-Validator-REST.git
cd -HL7-Integration-Engine---Message-Parser-Validator-REST
py -m pip install -r requirements.txt
py run.py
```

In a second terminal:

```bash
# Health check
curl http://127.0.0.1:5000/health

# Send a sample ADT^A01 message through the full pipeline
curl -X POST http://127.0.0.1:5000/api/hl7/parse \
  -H "Content-Type: application/json" -d @payload.json

# Inspect the transaction log
curl http://127.0.0.1:5000/api/hl7/messages
```

Run the test suite:

```bash
py -m pytest tests/ -v
# 22 passed
```

---

## Skills Demonstrated

- **HL7 v2 messaging** — parsing MSH, PID, PV1, OBR, OBX, ORC, EVN segments; handling field, component, and sub-component delimiters
- **Healthcare interoperability workflow** — receive → parse → validate → route → acknowledge → log
- **Validation and error handling** — required segments, required fields, format checks, HL7 datetime regex, structured error reporting
- **ACK protocol** — generating AA / AE / AR acknowledgements with correct sender/receiver swap and MSA.2 echo
- **Message routing** — per-message-type destinations with filter rules (test-message suppression, empty-result drop)
- **Backend API development** — Flask REST API with six endpoints, structured JSON responses, correct HTTP status codes
- **Database design** — SQLite transaction log with indexes on `message_control_id` and `message_type` for audit queries
- **Testing** — 22 pytest tests covering parser, validator, ACK generation, and API contract
- **CI/CD** — GitHub Actions running the full test suite on every push
- **Logging and observability** — runtime trace through parser, validator, router for production troubleshooting

---

## Why I built this

I had worked on REST API integrations and healthcare application development for 2.5 years at Optum India on the SmartDCOM platform — ServiceNow integration, field mapping, end-to-end testing, production support, CI/CD with Jenkins. But I had not worked directly with HL7 v2 messages in production, and I wanted to move beyond reading specs and watching videos into actually parsing real messages, hitting real edge cases, and generating real ACKs.

Writing the parser from first principles — rather than relying on a library — forced me to understand *why* MSH.1 is the field separator character itself, *why* PID.3 is the patient identifier (and what PID.3.5 means), *how* components separate inside a field with `^`, *what* a receiving system actually does when it gets an `ADT^A01`, and *what an AE acknowledgement contains*. Those are the questions that come up in integration engineer interviews.

The project is deliberately scoped to mirror the pipeline of a commercial integration engine — receive, parse, validate, route, acknowledge, store — so the concepts transfer directly.

---

## Table of Contents

1. [Tech Stack](#tech-stack)
2. [Project Structure](#project-structure)
3. [The HL7 v2 Refresher](#the-hl7-v2-refresher--read-this-first)
4. [How the Engine Works — End-to-End Flow](#how-the-engine-works--end-to-end-flow)
5. [Components in Detail](#components-in-detail)
6. [Supported Message Types](#supported-message-types)
7. [Validation Rules](#validation-rules)
8. [ACK Generation](#ack-generation)
9. [Routing Logic](#routing-logic)
10. [Storage Schema](#storage-schema)
11. [REST API Reference](#rest-api-reference)
12. [Running Locally](#running-locally)
13. [Testing](#testing)
14. [CI/CD](#cicd)
15. [Worked Examples](#worked-examples)
16. [How This Maps to Rhapsody / Cloverleaf / Mirth](#how-this-maps-to-rhapsody--cloverleaf--mirth)
17. [Interview Scenario Walk-throughs](#interview-scenario-walk-throughs)
18. [What I Would Do Next](#what-i-would-do-next)
19. [Notes](#notes)

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.13 | Readable, standard for healthcare integration scripting |
| Parser | Custom, pure Python (no library) | Forces understanding of HL7 structure |
| Secondary parser | `hl7apy` (installed but used for cross-checking) | Library-based sanity check option |
| Web framework | Flask | Minimal, explicit, easy to reason about |
| Storage | SQLite | Zero-install, file-backed, built into Python |
| Tests | `pytest` + `pytest-flask` | Standard Python test tooling |
| CI/CD | GitHub Actions | Runs full test suite on every push |

---

## Project Structure

```
hl7-integration-engine/
├── .github/
│   └── workflows/
│       └── ci.yml                  # GitHub Actions — runs all tests on push
├── app/
│   ├── __init__.py                 # Flask app factory, initialises SQLite
│   ├── routes.py                   # All REST endpoints
│   └── core/
│       ├── __init__.py
│       ├── parser.py               # Splits raw HL7 into segments, fields, components
│       ├── validator.py            # Required-segment and required-field checks
│       ├── ack.py                  # AA / AE / AR ACK generator
│       ├── router.py               # Per-message-type routing rules + filters
│       └── storage.py              # SQLite transaction log
├── tests/
│   ├── __init__.py
│   ├── test_parser.py              # 7 parser tests
│   ├── test_validator.py           # 4 validator tests
│   ├── test_ack.py                 # 5 ACK tests
│   └── test_api.py                 # 6 API integration tests
├── sample_messages/
│   ├── adt_a01.hl7                 # Patient admission — valid
│   ├── adt_a01_invalid.hl7         # Patient admission — missing PV1 + empty PID.3
│   ├── oru_r01.hl7                 # Lab result (CBC)
│   └── orm_o01.hl7                 # Pharmacy order
├── payload.json                    # Ready-to-curl valid message payload
├── payload_invalid.json            # Ready-to-curl invalid message payload
├── run.py                          # Entry point — `py run.py`
├── requirements.txt
├── .gitignore
└── README.md                       # This file
```

---

## The HL7 v2 Refresher — Read This First

HL7 v2 is a pipe-delimited text format for exchanging clinical data between hospital systems. It has been in production since the late 1980s and is still the dominant standard in most hospitals worldwide, even as FHIR grows.

### The structure

A **message** is made of **segments**. Each segment is one line. Segments are separated by carriage return `\r` (some systems use `\r\n` or `\n` — good parsers handle all three).

Each **segment** is made of **fields**. Fields are separated by pipe `|`. The first 3 characters of a segment are always the segment name (e.g. `MSH`, `PID`, `PV1`).

Each **field** can be made of **components**. Components are separated by caret `^`. So `Doyle^Sean^Michael` is a single PID.5 field (Patient Name) with three components: family name, given name, middle name.

Components can have **sub-components** separated by ampersand `&`. These are rarer but the parser handles them by leaving the raw value intact and splitting only when asked.

### The key segments

| Segment | Name | Purpose |
|---|---|---|
| **MSH** | Message Header | *Always first.* Says who sent what, when, and what kind of message it is |
| **EVN** | Event Type | Used in ADT messages — confirms the triggering event |
| **PID** | Patient Identification | Patient ID, name, DOB, gender, address, phone |
| **PV1** | Patient Visit | Ward, room, bed, admission type, attending doctor |
| **OBR** | Observation Request | The test or procedure that was ordered |
| **OBX** | Observation Result | The actual result value, units, reference range |
| **ORC** | Order Common | Order control info used with OBR for orders |
| **MSA** | Message Acknowledgement | Used in ACK messages to confirm receipt |

### The MSH segment broken down

```
MSH|^~\&|ADMIT_SYS|CITY_HOSPITAL|HIS|OPTUM|20260418120000||ADT^A01|MSG00001|P|2.5
```

| Field | Value | Meaning |
|---|---|---|
| MSH.1 | `|` | Field separator character (itself a field, the HL7 quirk) |
| MSH.2 | `^~\&` | Encoding characters: component `^`, repetition `~`, escape `\`, sub-component `&` |
| MSH.3 | `ADMIT_SYS` | Sending application |
| MSH.4 | `CITY_HOSPITAL` | Sending facility |
| MSH.5 | `HIS` | Receiving application |
| MSH.6 | `OPTUM` | Receiving facility |
| MSH.7 | `20260418120000` | Message datetime (YYYYMMDDHHMMSS) |
| MSH.9 | `ADT^A01` | Message type + trigger event |
| MSH.10 | `MSG00001` | Message control ID (used to match ACK to original) |
| MSH.11 | `P` | Processing ID (`P`=production, `T`=test, `D`=debug) |
| MSH.12 | `2.5` | HL7 version |

### The PID segment broken down

```
PID|1||PAT123456^^^CITY_HOSP^MR||Doyle^Sean^Michael||19850315|M|||15 Grafton St^^Dublin^^D02||0871234567
```

| Field | Value | Meaning |
|---|---|---|
| PID.1 | `1` | Set ID (sequence number) |
| PID.3 | `PAT123456^^^CITY_HOSP^MR` | Internal Patient ID — `PAT123456` with assigning authority `CITY_HOSP` and ID type `MR` (Medical Record) |
| PID.5 | `Doyle^Sean^Michael` | Family name ^ Given name ^ Middle name |
| PID.7 | `19850315` | Date of birth (YYYYMMDD) |
| PID.8 | `M` | Administrative gender (M/F/O/U/A/N) |
| PID.11 | `15 Grafton St^^Dublin^^D02` | Address: street ^^ city ^^ postcode |
| PID.13 | `0871234567` | Home phone |

**Know PID.3, PID.5, PID.7, and PID.8 cold.** Every healthcare integration interview asks about them.

---

## How the Engine Works — End-to-End Flow

```
      ┌─────────────────────────┐
   1  │ Raw HL7 message arrives │
      │  (HTTP POST /parse)     │
      └────────────┬────────────┘
                   │
                   v
      ┌─────────────────────────┐
   2  │ parser.py               │
      │  - split on \r\n|\r|\n  │
      │  - split segments on |  │
      │  - split fields on ^    │
      │  - extract MSH, PID     │
      └────────────┬────────────┘
                   │
                   v
      ┌─────────────────────────┐
   3  │ validator.py            │
      │  - required segments?   │
      │  - required fields?     │
      │  - format checks?       │
      └────────────┬────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
      valid              invalid
         │                   │
         v                   v
   ┌──────────┐      ┌──────────────┐
 4 │router.py │    5 │ ack.py       │
   │ -> dests │      │ build AE ACK │
   └────┬─────┘      │ with errors  │
        │            └──────┬───────┘
        v                   │
   ┌──────────┐             │
 5 │ack.py    │             │
   │build AA  │             │
   │  ACK     │             │
   └────┬─────┘             │
        │                   │
        └────────┬──────────┘
                 │
                 v
      ┌─────────────────────────┐
   6  │ storage.py              │
      │  INSERT INTO messages   │
      │  (full transaction log) │
      └────────────┬────────────┘
                   │
                   v
      ┌─────────────────────────┐
   7  │ JSON response with ACK  │
      │ returned to caller      │
      └─────────────────────────┘
```

Every step is logged with Python's `logging` module so you get a runtime trace like:

```
2026-04-18 18:30:24,186 INFO app.core.parser - Parsed ADT^A01 message | control_id=MSG00001 | patient=PAT123456
2026-04-18 18:30:24,187 INFO app.core.validator - Validated ADT^A01 | valid=True | errors=0 | warnings=0
2026-04-18 18:30:24,187 INFO app.core.router - Routed ADT^A01 -> ['EHR_MAIN', 'BILLING_SYS', 'PHARMACY', 'LAB'] (filtered=False)
```

This log output *is* the "transaction log" that integration engineers monitor to troubleshoot production issues.

---

## Components in Detail

### `app/core/parser.py` — the parser

The parser's job is to take a raw HL7 string and turn it into a structured Python dict.

Key functions:

- **`_split_segments(raw)`** — normalises line endings (`\r\n` → `\n`, `\r` → `\n`) and splits into segment lines. Raises `ValueError` if the message is empty or the first segment is not MSH.
- **`_parse_segment(segment_line)`** — splits a segment on `|` and returns a dict `{segment, fields, raw}` where `fields` is a map of field number to raw value.
- **`_get_field(segment, n)`** — safe field getter, returns `""` if the field doesn't exist instead of crashing.
- **`_get_component(field_value, n)`** — splits a field on `^` and returns the *n*th component (1-based to match HL7 convention).
- **`parse_message(raw)`** — the public entry point. Calls the helpers, extracts MSH metadata (sending app, receiving app, timestamp, control ID, message type, trigger event), then walks the segments looking for PID and pulls out patient demographics.

Returns a dict like:

```python
{
  "message_type": "ADT^A01",
  "trigger_event": "A01",
  "sending_app": "ADMIT_SYS",
  "sending_facility": "CITY_HOSPITAL",
  "receiving_app": "HIS",
  "receiving_facility": "OPTUM",
  "timestamp": "20260418120000",
  "message_control_id": "MSG00001",
  "processing_id": "P",
  "version": "2.5",
  "segment_names": ["MSH", "EVN", "PID", "PV1"],
  "patient": {
    "patient_id": "PAT123456",
    "assigning_authority": "CITY_HOSP",
    "id_type": "MR",
    "family_name": "Doyle",
    "given_name": "Sean",
    "middle_name": "Michael",
    "date_of_birth": "19850315",
    "gender": "M",
    "street": "15 Grafton St",
    "city": "Dublin",
    "postcode": "D02",
    "phone": "0871234567"
  },
  "segments": [ ... full list of parsed segments ... ]
}
```

**Why I didn't just use `hl7apy`:** two reasons. First, I wanted to *understand* HL7 structure by implementing it. Second, in an interview if someone asks "how does your parser handle a field with a `^` in it?" — I can answer from my own code, not from a library abstraction.

`hl7apy` is installed in `requirements.txt` and was used during development to cross-check my parser's output on edge cases.

### `app/core/validator.py` — the validator

Runs a set of rules against the parsed message and returns `{valid, errors, warnings, message_type}`.

Rule categories:

1. **Message type recognition** — is this a message type I know how to route? Unknown types get a warning, not an error.
2. **Required segments** — each message type has a list of segments it must contain (defined in `REQUIRED_SEGMENTS` dict). Missing ones are errors.
3. **MSH required fields** — sending app, sending facility, receiving app, receiving facility, timestamp, message type, message control ID, version ID. Missing any of these is an error.
4. **Timestamp format** — MSH.7 must match HL7 datetime regex `^\d{8}(\d{4}(\d{2})?)?$` (i.e. YYYYMMDD, YYYYMMDDHHMM, or YYYYMMDDHHMMSS).
5. **PID required fields** — PID.3 (patient ID) and PID.5 (patient name) must not be empty.
6. **PID.8 gender sanity** — should be one of `M/F/O/U/A/N`. Anything else gets a warning.
7. **ORU-specific** — if the message is `ORU^R01`, there must be at least one OBX segment, and each OBX must have a value in OBX.5.

The distinction between **errors** (triggers an AE ACK, message rejected) and **warnings** (logged but message still accepted) matters. Integration engineers use this exact distinction in Rhapsody filters.

### `app/core/ack.py` — the acknowledgement generator

Two functions:

**`determine_ack_code(validation_result)`** — looks at the validation result and picks an ACK code:
- `AA` if valid
- `AE` if there are errors (with the first 3 joined into an error summary)

**`build_ack(original, ack_code, error_text)`** — builds the ACK message string. The ACK is itself a mini HL7 message:

```
MSH|^~\&|<ack_sending_app>|<ack_sending_fac>|<ack_receiving_app>|<ack_receiving_fac>|<now>||ACK|ACK<now>|P|2.5
MSA|<ack_code>|<original_control_id>|<error_text>
```

**The swap rule:** the ACK's sending application becomes the original message's receiving application, and vice versa. This is because we're responding to the sender — from our perspective, we're the sender now and they're the receiver.

**MSA.2** carries the original message's control ID. This is how the sending system matches ACKs back to messages it sent — it remembers "I sent MSG00001, and now an ACK came back with MSA.2=MSG00001, so this is the ACK for that message."

### `app/core/router.py` — the router

Maintains a `ROUTING_TABLE` — a dict mapping message type to a list of downstream destinations:

```python
ROUTING_TABLE = {
    "ADT^A01": ["EHR_MAIN", "BILLING_SYS", "PHARMACY", "LAB"],
    "ADT^A03": ["EHR_MAIN", "BILLING_SYS"],
    "ADT^A08": ["EHR_MAIN", "BILLING_SYS", "PHARMACY"],
    "ORU^R01": ["EHR_MAIN", "CLINICAL_PORTAL"],
    "ORM^O01": ["LAB", "PHARMACY"],
}
```

Also applies two filter rules:

1. **Test message filter** — if `MSH.11 = T` (test message), suppress all downstream forwarding. This mirrors how Rhapsody is usually configured in staging environments.
2. **Empty result filter** — if the message is `ORU^R01` but has no OBX segments, drop the message (there's nothing to report).

Returns `{message_type, destinations, filtered, filter_reason}`.

### `app/core/storage.py` — the transaction log

SQLite database with one `messages` table:

| Column | Purpose |
|---|---|
| id | Auto-increment primary key |
| received_at | ISO timestamp when we processed it |
| message_control_id | From MSH.10 — used for searching |
| message_type | From MSH.9 |
| sending_app, sending_facility | Routing source |
| patient_id | Extracted from PID.3 — used for searching by patient |
| is_valid | 1 or 0 |
| errors | JSON array of error strings |
| warnings | JSON array of warning strings |
| destinations | JSON array of downstream systems we routed to |
| ack_code | AA / AE / AR |
| raw_message | Full original HL7 text, for replay |
| parsed_json | Parsed structure (excluding segments list) for quick read |

Two indexes are created on first init: one on `message_control_id` and one on `message_type`, so searches by either are O(log n) instead of table scans.

This is the database an integration engineer would query when a clinician says "my lab result didn't come through" — you search by patient ID or timestamp range and see exactly what happened to every related message.

### `app/routes.py` — the Flask REST API

Six endpoints — see [REST API Reference](#rest-api-reference) below.

---

## Supported Message Types

| Type | Trigger | Real-world meaning | Required segments |
|---|---|---|---|
| **ADT^A01** | Admit | Patient arrives at hospital — notify all downstream systems | MSH, EVN, PID, PV1 |
| **ADT^A03** | Discharge | Patient is discharged — close active orders | MSH, EVN, PID, PV1 |
| **ADT^A08** | Update | Patient details changed — sync demographics across systems | MSH, EVN, PID, PV1 |
| **ORU^R01** | Observation Result | Lab returns a test result to the ordering system | MSH, PID, OBR, OBX |
| **ORM^O01** | Order Message | Doctor places an order (lab test, pharmacy, radiology) | MSH, PID, ORC, OBR |

Unknown message types are accepted with a warning and forwarded with no destinations (no-op route).

---

## Validation Rules

Summary of what triggers an ERROR (AE ACK) vs. a WARNING (AA ACK but logged):

### Errors (reject the message with AE)

- First segment is not MSH
- Empty message
- Missing required segment for the declared message type
- MSH.3, MSH.4, MSH.5, MSH.6, MSH.7, MSH.9, MSH.10, or MSH.12 is empty
- MSH.7 does not match HL7 datetime format
- PID.3 (patient ID) is empty
- PID.5 (patient name) is empty
- ORU^R01 message with no OBX segments

### Warnings (accept with AA but log)

- Message type not in routing table
- PID.7 (DOB) is not in HL7 date format
- PID.8 (gender) not in M/F/O/U/A/N
- OBX.5 (observation value) is empty
- MSH.12 (version) doesn't start with "2."

---

## ACK Generation

HL7 ACK codes per the v2 spec:

| Code | Meaning | When this engine sends it |
|---|---|---|
| **AA** | Application Accept | Message parsed and all validation rules passed |
| **AE** | Application Error | Message parsed but validation rules failed — sender should fix and resend |
| **AR** | Application Reject | Message could not be parsed at all (malformed MSH, empty message, etc.) |

**Example valid ACK:**
```
MSH|^~\&|HIS|OPTUM|ADMIT_SYS|CITY_HOSPITAL|20260418173024||ACK|ACK20260418173024|P|2.5
MSA|AA|MSG00001|
```

**Example error ACK (from the invalid test message):**
```
MSH|^~\&|HIS|OPTUM|ADMIT_SYS|CITY_HOSPITAL|20260418173055||ACK|ACK20260418173055|P|2.5
MSA|AE|MSG00004|Missing required segment: PV1; PID.3 (Patient ID (PID.3)) is empty
```

Note how the sender/receiver are swapped (the ACK's MSH.3/4 is the original's MSH.5/6 and vice versa) and the original message control ID is echoed in MSA.2.

---

## Routing Logic

| Message type | Destinations |
|---|---|
| ADT^A01 (Admit) | EHR_MAIN, BILLING_SYS, PHARMACY, LAB |
| ADT^A03 (Discharge) | EHR_MAIN, BILLING_SYS |
| ADT^A08 (Update) | EHR_MAIN, BILLING_SYS, PHARMACY |
| ORU^R01 (Result) | EHR_MAIN, CLINICAL_PORTAL |
| ORM^O01 (Order) | LAB, PHARMACY |

Two filters short-circuit the routing:

1. **`processing_id == "T"`** → filtered, no destinations, reason = "Message has processing_id=T (test), suppressed from downstream"
2. **ORU^R01 with zero OBX segments** → filtered, reason = "ORU message has no OBX result segments — dropped"

---

## Storage Schema

```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    received_at TEXT NOT NULL,
    message_control_id TEXT,
    message_type TEXT,
    sending_app TEXT,
    sending_facility TEXT,
    patient_id TEXT,
    is_valid INTEGER,
    errors TEXT,           -- JSON array
    warnings TEXT,         -- JSON array
    destinations TEXT,     -- JSON array
    ack_code TEXT,
    raw_message TEXT,
    parsed_json TEXT       -- JSON dict
);

CREATE INDEX idx_control_id ON messages(message_control_id);
CREATE INDEX idx_type ON messages(message_type);
```

---

## REST API Reference

### `GET /health`

Service health check.

**Request:**
```bash
curl http://127.0.0.1:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "HL7 Integration Engine",
  "version": "1.0.0"
}
```

---

### `POST /api/hl7/parse`

Full pipeline — parse, validate, route, store, and return ACK.

**Request body:**
```json
{ "message": "MSH|^~\\&|ADMIT_SYS|CITY_HOSPITAL|HIS|OPTUM|20260418120000||ADT^A01|MSG00001|P|2.5\rEVN|A01|20260418120000\rPID|1||PAT123456^^^CITY_HOSP^MR||Doyle^Sean^Michael||19850315|M\rPV1|1|I|WARD4" }
```

**Response (valid message):**
```json
{
  "success": true,
  "message_id": 1,
  "message_type": "ADT^A01",
  "message_control_id": "MSG00001",
  "patient": {
    "patient_id": "PAT123456",
    "family_name": "Doyle",
    "given_name": "Sean",
    "date_of_birth": "19850315",
    "gender": "M",
    "city": "Dublin",
    "...": "..."
  },
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "message_type": "ADT^A01"
  },
  "routing": {
    "destinations": ["EHR_MAIN", "BILLING_SYS", "PHARMACY", "LAB"],
    "filtered": false,
    "filter_reason": "",
    "message_type": "ADT^A01"
  },
  "ack_code": "AA",
  "ack_message": "MSH|^~\\&|HIS|OPTUM|ADMIT_SYS|CITY_HOSPITAL|20260418173024||ACK|ACK20260418173024|P|2.5\rMSA|AA|MSG00001|"
}
```

**Response (invalid message):**
```json
{
  "success": true,
  "message_id": 2,
  "message_type": "ADT^A01",
  "validation": {
    "valid": false,
    "errors": [
      "Missing required segment: PV1",
      "PID.3 (Patient ID (PID.3)) is empty"
    ],
    "warnings": []
  },
  "ack_code": "AE",
  "ack_message": "MSH|^~\\&|HIS|OPTUM|ADMIT_SYS|CITY_HOSPITAL|20260418173055||ACK|ACK20260418173055|P|2.5\rMSA|AE|MSG00004|Missing required segment: PV1; PID.3 (Patient ID (PID.3)) is empty"
}
```

---

### `POST /api/hl7/validate`

Validate only — does not store or route.

Returns `{valid, errors, warnings, message_type}` directly.

---

### `GET /api/hl7/messages?limit=50`

List recent processed messages.

```json
{
  "count": 2,
  "messages": [
    {
      "id": 2,
      "received_at": "2026-04-18T17:30:55.957366",
      "message_control_id": "MSG00004",
      "message_type": "ADT^A01",
      "sending_app": "ADMIT_SYS",
      "patient_id": "",
      "is_valid": 0,
      "ack_code": "AE",
      "errors": ["Missing required segment: PV1", "PID.3 (Patient ID (PID.3)) is empty"],
      "destinations": ["EHR_MAIN", "BILLING_SYS", "PHARMACY", "LAB"]
    },
    { "id": 1, "ack_code": "AA", "...": "..." }
  ]
}
```

---

### `GET /api/hl7/messages/<id>`

Full detail for one message including the raw HL7 text and the parsed JSON structure. This is what you'd use to replay or debug a specific transaction.

---

### `GET /api/hl7/stats`

Summary counters:

```json
{
  "total": 2,
  "valid": 1,
  "invalid": 1,
  "by_type": { "ADT^A01": 2 }
}
```

---

## Running Locally

```bash
# Clone
git clone https://github.com/SaiTejaReddyYeldandi/-HL7-Integration-Engine---Message-Parser-Validator-REST.git
cd -HL7-Integration-Engine---Message-Parser-Validator-REST

# Install
py -m pip install -r requirements.txt

# Run
py run.py
# Flask starts on http://127.0.0.1:5000
```

In a second terminal, test:

```bash
# Health check
curl http://127.0.0.1:5000/health

# Build a payload from the sample message
py -c "import json; msg=open('sample_messages/adt_a01.hl7', encoding='utf-8').read(); print(json.dumps({'message': msg}))" > payload.json

# Send it
curl -X POST http://127.0.0.1:5000/api/hl7/parse -H "Content-Type: application/json" -d @payload.json

# See it in the log
curl http://127.0.0.1:5000/api/hl7/messages

# Stats
curl http://127.0.0.1:5000/api/hl7/stats
```

---

## Testing

```bash
py -m pytest tests/ -v
```

Current result: **22 passed**.

```
tests/test_ack.py::test_ack_aa_format PASSED
tests/test_ack.py::test_ack_sender_receiver_swapped PASSED
tests/test_ack.py::test_ack_ae_carries_error PASSED
tests/test_ack.py::test_determine_ack_valid PASSED
tests/test_ack.py::test_determine_ack_invalid PASSED
tests/test_api.py::test_health PASSED
tests/test_api.py::test_parse_valid_message PASSED
tests/test_api.py::test_parse_missing_body PASSED
tests/test_api.py::test_validate_only PASSED
tests/test_api.py::test_list_messages PASSED
tests/test_api.py::test_stats PASSED
tests/test_parser.py::test_parse_returns_message_type PASSED
tests/test_parser.py::test_parse_extracts_msh_fields PASSED
tests/test_parser.py::test_parse_extracts_patient PASSED
tests/test_parser.py::test_parse_segment_names PASSED
tests/test_parser.py::test_parse_empty_raises PASSED
tests/test_parser.py::test_parse_no_msh_raises PASSED
tests/test_parser.py::test_parse_handles_crlf PASSED
tests/test_validator.py::test_valid_message_passes PASSED
tests/test_validator.py::test_missing_required_segment_fails PASSED
tests/test_validator.py::test_empty_patient_id_fails PASSED
tests/test_validator.py::test_bad_timestamp_fails PASSED

22 passed in 0.64s
```

### Test coverage by concern

- **Parser (7 tests)** — valid parse, MSH extraction, patient extraction, segment names, empty input, missing MSH, CRLF line endings
- **Validator (4 tests)** — valid passes, missing required segment fails, empty PID.3 fails, bad timestamp format fails
- **ACK (5 tests)** — AA format correct, sender/receiver swapped, AE carries error text, valid→AA code, invalid→AE code
- **API (6 tests)** — health, parse valid, parse missing body, validate-only, list messages, stats

---

## CI/CD

`.github/workflows/ci.yml` runs on every push to `main`:

```yaml
name: HL7 Engine CI
on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/ -v
```

Green checkmark on every commit confirms the full 22-test suite passes in a clean Ubuntu environment.

---

## Worked Examples

### Example 1 — Valid ADT^A01 admission

**Input (`sample_messages/adt_a01.hl7`):**
```
MSH|^~\&|ADMIT_SYS|CITY_HOSPITAL|HIS|OPTUM|20260418120000||ADT^A01|MSG00001|P|2.5
EVN|A01|20260418120000
PID|1||PAT123456^^^CITY_HOSP^MR||Doyle^Sean^Michael||19850315|M|||15 Grafton St^^Dublin^^D02||0871234567
PV1|1|I|WARD4^ROOM2^BED1|E||||DOC001^Murphy^Patrick|||CAR|||||ADM|||INS001
```

**What happens:**
1. Parser splits into 4 segments, extracts MSH routing, extracts patient Doyle/Sean/Michael.
2. Validator: all 4 required segments present (MSH, EVN, PID, PV1), all MSH fields populated, PID.3 and PID.5 populated, timestamps valid. **valid=true, errors=[]**.
3. Router: ADT^A01 → `[EHR_MAIN, BILLING_SYS, PHARMACY, LAB]`, processing_id=P so not filtered.
4. ACK builder: valid → AA. Builds MSH with swapped sender/receiver and MSA|AA|MSG00001|.
5. Storage: insert row with is_valid=1, ack_code=AA, destinations JSON, raw message, parsed JSON.
6. JSON response returned to client with message_id=1.

### Example 2 — Invalid ADT^A01 (missing PV1 + empty PID.3)

**Input (`sample_messages/adt_a01_invalid.hl7`):**
```
MSH|^~\&|ADMIT_SYS|CITY_HOSPITAL|HIS|OPTUM|20260418120000||ADT^A01|MSG00004|P|2.5
EVN|A01|20260418120000
PID|1||||Doyle^Sean^Michael||19850315|M
```

**What happens:**
1. Parser splits into 3 segments successfully — parser doesn't reject missing segments, that's the validator's job.
2. Validator: PV1 missing (ADT^A01 requires it), PID.3 empty. **valid=false, errors=[2]**.
3. Router still runs (it doesn't check validity — in a real engine you might short-circuit here, but the separation is cleaner this way).
4. ACK builder: invalid → AE, error text = "Missing required segment: PV1; PID.3 (Patient ID (PID.3)) is empty".
5. Storage: row with is_valid=0, errors JSON populated, ack_code=AE.
6. JSON response shows `validation.valid=false`, errors array, and the AE ACK string.

---

## How This Maps to Rhapsody / Cloverleaf / Mirth

The concepts in this project map one-to-one to commercial integration engines:

| This project | Rhapsody | Cloverleaf | Mirth Connect |
|---|---|---|---|
| `parser.py` | Built-in HL7 v2 parser | Built-in HL7 v2 parser | Built-in HL7 parser |
| `validator.py` | Filter → required-field rules on a route | TCL-scripted precondition filter | Source filter / destination filter |
| `router.py` | Route with conditional destinations | "Xlate" / route-to logic | Destinations with filters |
| `ack.py` | Auto-generated ACK reply | Auto-generated ACK | Auto-respond with ACK |
| `storage.py` | Message Tracker / message viewer | Audit DB / Transaction log | Message log / Dashboard |
| Flask `/parse` endpoint | **MLLP listener** on TCP port 2575 | **MLLP communication point** | **MLLP listener channel** |

**The one missing piece: MLLP.** Real integration engines do not use HTTP/JSON to receive HL7 messages — they use **Minimal Lower Layer Protocol** over TCP. MLLP wraps each HL7 message with a start block `\x0b` (vertical tab) and an end block `\x1c\r` (file separator + CR). Senders connect to a TCP port (typically 2575) and send MLLP-framed messages.

I used HTTP/JSON here because it's trivial to test with `curl`, trivial to show in a REST API demo, and the parsing/validation/routing logic is identical regardless of transport. **If I were turning this into a production engine**, I'd add a TCP socket server listening on 2575 that reads MLLP frames, feeds them into the same pipeline (parser → validator → router → storage), and writes the ACK back MLLP-framed. The core logic would not change.

---

## Interview Scenario Walk-throughs

These are the five scenario types that come up in every healthcare integration interview. For each, I've written how I would answer using this project as evidence of hands-on understanding.

### Scenario 1 — "Walk me through your HL7 project"

> I built a Python-based HL7 v2 integration engine from first principles to understand how healthcare interoperability actually works at the message level. When a raw HL7 message comes in — for example an `ADT^A01` patient admission — the engine splits it into segments on carriage returns, then each segment into fields on pipes, then extracts the MSH header to work out routing, and the PID segment to pull patient demographics. Then the validator runs — it checks the required segments for that message type, checks the required fields are populated, and validates formats like the HL7 datetime. If validation passes the router looks up the message type in a routing table and returns the list of downstream destinations — for ADT^A01 that's EHR, billing, pharmacy, and lab. The ACK generator builds an AA acknowledgement with the sender and receiver swapped and the original control ID in MSA.2 so the sending system can match it back. The whole transaction is logged to SQLite. If validation fails, the same pipeline runs but the ACK code is AE and the error text goes into MSA.3. Everything is wrapped in a Flask REST API with six endpoints and covered by 22 pytest tests running in GitHub Actions. The same workflow pattern is what Rhapsody, Cloverleaf, and Mirth provide in production — I used HTTP instead of MLLP because it's easier to demonstrate, but the parsing, validation, routing, and ACK logic is identical.

### Scenario 2 — "A hospital says they sent us an ADT message an hour ago but we don't have the patient in our system. How do you troubleshoot?"

> First I'd check our transaction log — in my project that's `GET /api/hl7/messages`, in Rhapsody it's the Message Tracker. I'd search by the time window and sending facility to see whether the message arrived at all. Three possibilities:
>
> **(a) Message never arrived.** Then it's a network or connectivity issue — check whether the MLLP listener port is open, whether firewall rules changed, whether the sender's configuration still points at our endpoint. I'd coordinate with the sender to check their outbound logs.
>
> **(b) Message arrived but we sent an AE ACK back.** In the transaction log the `is_valid=0` and the `errors` column tells us exactly which validation rule failed. Most common: empty PID.3, missing required segment, malformed timestamp. I'd send the specific error back to the sender so they can fix the source data.
>
> **(c) Message arrived, we sent AA, but the patient isn't in the downstream EHR.** That means the message was accepted and routed but the downstream system rejected it — I'd check the outbound message log for the EHR destination and look at the EHR's own ingestion log. Common causes: the EHR's patient ID format doesn't match, mapping rules dropped a required field, or the EHR system was down during the forwarding window and didn't retry.

### Scenario 3 — "The sending system is getting AE back on every message. What's happening?"

> An AE means the messages are being parsed successfully but failing validation. In my project the error text in MSA.3 tells them exactly which rule failed. If I'm the one receiving the complaint, I'd ask for one specific failing MSH.10 control ID and look it up in the transaction log — `GET /api/hl7/messages/<id>` in my project — and read the `errors` field. Common root causes:
>
> - **Schema change on the sender side** — they upgraded their EHR and PID.3 is now an empty field instead of a patient ID because of a mapping bug in their upgrade.
> - **Data entry issue** — clinicians leaving required fields blank and the sender isn't validating before sending.
> - **Our validation is too strict** — rare, but possible if we added a new required-field rule that the sender's HL7 spec doesn't actually require.
>
> In Rhapsody I'd use the filter's error log to see which rule rejected it. In my project the equivalent is `is_valid=0` with the `errors` JSON column.

### Scenario 4 — "The interface worked yesterday and is failing today — nothing in our code changed. How do you troubleshoot?"

> Something *outside* our code changed. My checklist:
>
> **1. Was there a deployment on either side?** Check change logs on our side and the sender's side in the last 24 hours.
>
> **2. Did a certificate expire?** TLS certificates for VPN tunnels or SFTP often expire quietly and kill production integrations. Check expiry dates.
>
> **3. Did the sending system change their message format?** Hospitals occasionally upgrade their EHR without telling integration partners. Diff a failing message against a successful message from two days ago — look at every MSH, PID, and message-type-specific segment field by field.
>
> **4. Did network rules change?** Firewall updates, IP whitelist changes, or VPN reconfiguration can silently block traffic.
>
> **5. Did the message volume spike?** Queue depth on the listener can cause messages to back up and time out.
>
> In my project I'd compare today's failing transaction to yesterday's successful one using `GET /api/hl7/messages/<id>` for each. Walk through MSH field by field, PID field by field, and every other segment. The difference is the cause. In Rhapsody the equivalent is comparing the raw message bytes in the Message Tracker.

### Scenario 5 — "Explain the difference between HL7 v2 and FHIR — which should we use for a new integration?"

> HL7 v2 is the older pipe-delimited text standard that's been in production in hospitals since the late 1980s. It's still dominant in existing hospital systems — every EHR, lab system, pharmacy system in production today either speaks HL7 v2 natively or has an HL7 v2 adapter. The strengths are: universal support, extremely efficient for TCP/MLLP transport, mature tooling in every integration engine.
>
> FHIR is the modern REST+JSON standard. Resources like Patient, Observation, Encounter, and MedicationRequest map directly to v2 segments like PID, OBX, PV1, and RXE. FHIR is better for web applications, mobile apps, and patient-facing portals because it uses HTTPS and JSON that web developers already understand. It's easier to onboard new integration partners because there's no MLLP to set up — just a REST endpoint.
>
> For a new integration in 2026, my answer depends on the counterparty:
>
> - **Integrating with an existing EHR** (Epic, Cerner, Meditech) → HL7 v2 if their interface is already there, FHIR if you're building a new one from scratch and the EHR vendor supports FHIR (which Epic does extensively through Epic Bridges and Care Everywhere).
> - **Integrating with a patient portal, mobile app, or modern SaaS** → FHIR, no question.
> - **Integrating with a legacy hospital system** → HL7 v2, because that's what it speaks.
>
> Most real production environments support both in parallel — HL7 v2 for the established integrations and FHIR for anything new.

---

## What I Would Do Next

Things I deliberately scoped out of version 1 that would be next on the list if this went further:

- **MLLP TCP listener** — the transport layer that real integration engines use. Wrap the same parser/validator/router/storage pipeline behind a TCP socket server listening on 2575 with MLLP framing (`\x0b` start block, `\x1c\r` end block).
- **Transformation engine** — mapping from one message format to another. E.g. take an incoming ADT^A01 with PID.7 as YYYYMMDD and transform PID.7 to DD/MM/YYYY for a downstream system that expects that format.
- **Retry queue and dead letter queue** — if a downstream destination is unreachable, queue the message for retry; if all retries fail, move to DLQ for manual review.
- **FHIR bridge** — take an incoming HL7 v2 ADT and post an equivalent FHIR Patient resource to a downstream FHIR server. This is an extremely common real-world requirement as hospitals modernise.
- **Web dashboard** — small Streamlit or HTMX dashboard showing queue depth, message volume by type, ACK code breakdown, and recent errors — what an integration engineer actually watches during on-call.

---

## Notes

- Timestamps use timezone-aware UTC (`datetime.now(timezone.utc)`) rather than the deprecated `datetime.utcnow()`.
- Development scratch test scripts have been removed from the repo root; all tests now live under `tests/`.

---

## Context

Built as a personal learning project to move from conceptual understanding of HL7 and healthcare integration into hands-on experience — parsing real messages, generating real ACKs, and handling real validation edge cases. Complements 2.5 years of Optum India experience in REST API integration, SmartDCOM application development, end-to-end testing, and production support.

**Author:** Sai Teja Reddy Yeldandi
**GitHub:** [github.com/SaiTejaReddyYeldandi](https://github.com/SaiTejaReddyYeldandi)
**Location:** Dublin, Ireland