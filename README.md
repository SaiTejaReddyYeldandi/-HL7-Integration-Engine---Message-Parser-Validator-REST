\# HL7 Integration Engine — Message Parser, Validator \& REST API



> Python-based HL7 v2 integration engine — built to demonstrate healthcare interoperability skills directly aligned with Solution Integration Engineer roles at Dedalus and Optum.



This project simulates the core workflow of a production healthcare integration engine: receive an inbound HL7 message, parse it, validate required segments and fields, generate an acknowledgement, route it to the correct downstream system, store the transaction, and expose everything through a REST API — the same pattern used by tools like Mirth Connect, Rhapsody, and Cloverleaf in real hospital environments.



\---



\## What This Project Does



In a real hospital, systems talk to each other using HL7 messages. When a patient is admitted, the hospital reception system sends an `ADT^A01` message to the lab, pharmacy, and ward systems. Each downstream system needs to:



1\. \*\*Receive\*\* the message

2\. \*\*Parse\*\* it — extract patient data, order details, results

3\. \*\*Validate\*\* it — check all required fields are present

4\. \*\*Acknowledge\*\* it — send back an `AA` (Accept), `AE` (Error), or `AR` (Reject)

5\. \*\*Route\*\* it — forward to the correct destination based on message type

6\. \*\*Store\*\* it — log the transaction for audit and reporting



This engine does all of that.



\---



\## Project Structure



```

HL7-Integration-Engine/

├── .github/

│   └── workflows/

│       └── hl7-ci.yml          # GitHub Actions — runs tests on every push

├── app/

│   ├── \_\_init\_\_.py             # Flask app factory

│   ├── parser.py               # HL7 message parser — extracts MSH, PID, OBR, OBX

│   ├── validator.py            # Validates required segments and fields

│   ├── ack\_generator.py        # Generates HL7 ACK responses (AA, AE, AR)

│   ├── router.py               # Routes messages to correct downstream handler

│   ├── storage.py              # SQLite — stores all processed transactions

│   └── routes.py               # Flask REST API endpoints

├── sample\_messages/

│   ├── adt\_a01.hl7             # Sample ADT^A01 — Patient Admission

│   ├── adt\_a03.hl7             # Sample ADT^A03 — Patient Discharge

│   ├── adt\_a08.hl7             # Sample ADT^A08 — Patient Update

│   ├── oru\_r01.hl7             # Sample ORU^R01 — Lab Result

│   └── orm\_o01.hl7             # Sample ORM^O01 — Lab Order

├── tests/

│   ├── test\_parser.py          # Parser unit tests

│   ├── test\_validator.py       # Validator unit tests

│   ├── test\_ack.py             # ACK generation tests

│   └── test\_routes.py          # API endpoint integration tests

├── payload.json                # Valid HL7 message payload for API testing

├── payload\_invalid.json        # Invalid payload — triggers AE/AR response

├── run.py                      # App entry point

├── requirements.txt            # Python dependencies

└── README.md                   # This file

```



\---



\## Supported HL7 Message Types



| Message Type | Trigger Event | Real-World Use |

|---|---|---|

| `ADT^A01` | Admit patient | Patient arrives at hospital — notify all systems |

| `ADT^A03` | Discharge patient | Patient leaves — close active orders |

| `ADT^A08` | Update patient info | Patient details changed — sync across systems |

| `ORU^R01` | Observation result | Lab sends test result back to ordering system |

| `ORM^O01` | Order message | Doctor orders a lab test or procedure |



\---



\## HL7 Message Structure — What the Parser Reads



A real HL7 v2 ADT^A01 message looks like this:



```

MSH|^\~\\\&|HospitalADT|CorkUniversityHospital|LabSystem|CUH|20260418120000||ADT^A01|MSG00001|P|2.3

PID|1||PAT123456^^^CUH^MR||O'Brien^Seamus||19750315|M|||14 Patrick Street^^Cork^^T12 AB34^IRL

PV1|1|I|EmergencyWard^Room3^Bed7^^^CUH||||DR12345^Murphy^Siobhan|||SUR||||ADM|A0123456^^^CUH^VN

```



| Segment | Full Name | Key Fields Extracted |

|---|---|---|

| `MSH` | Message Header | Sending app, receiving app, timestamp, message type, message ID |

| `PID` | Patient Identification | Patient ID, name, DOB, gender, address |

| `PV1` | Patient Visit | Ward, room, bed, attending doctor, visit type |

| `OBR` | Observation Request | Order number, test code, ordering doctor, collection time |

| `OBX` | Observation Result | Result value, units, reference range, result status |



The `|` character separates fields. The `^` character separates components within a field. The parser handles both.



\---



\## ACK Response Types



After receiving and processing an HL7 message, the engine sends back an acknowledgement:



| ACK Code | Meaning | When Used |

|---|---|---|

| `AA` | Application Accept | Message received, parsed, and stored successfully |

| `AE` | Application Error | Message received but failed validation — missing required field |

| `AR` | Application Reject | Message rejected — malformed structure, cannot process |



Example `AA` response generated by this engine:



```

MSH|^\~\\\&|HL7Engine|Integration|HospitalADT|CorkUniversityHospital|20260418120001||ACK|ACK00001|P|2.3

MSA|AA|MSG00001|Message accepted and processed successfully

```



\---



\## Message Routing Logic



The router reads the message type from `MSH-9` and forwards to the correct handler:



```

ADT^A01  →  Admission Handler    →  Notify ward, pharmacy, lab

ADT^A03  →  Discharge Handler    →  Close active orders, notify billing

ADT^A08  →  Update Handler       →  Sync patient demographics

ORU^R01  →  Result Handler       →  Send result to ordering clinician

ORM^O01  →  Order Handler        →  Create order in lab system

```



Unknown message types return `AR` with a routing error logged.



\---



\## REST API Endpoints



\### GET /health



Returns engine status and message processing statistics.



\*\*Request:\*\*

```bash

curl http://localhost:5000/health

```



\*\*Response:\*\*

```json

{

&#x20; "status": "healthy",

&#x20; "engine": "HL7 Integration Engine v1.0",

&#x20; "messages\_processed": 142,

&#x20; "uptime": "running"

}

```



\---



\### POST /api/hl7/parse



Parses a raw HL7 message and returns structured JSON.



\*\*Request:\*\*

```bash

curl -X POST http://localhost:5000/api/hl7/parse \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d @payload.json

```



\*\*payload.json:\*\*

```json

{

&#x20; "message": "MSH|^\~\\\\\&|HospitalADT|CUH|LabSystem|CUH|20260418120000||ADT^A01|MSG00001|P|2.3\\rPID|1||PAT123456^^^CUH^MR||OBrien^Seamus||19750315|M"

}

```



\*\*Response:\*\*

```json

{

&#x20; "message\_type": "ADT^A01",

&#x20; "message\_id": "MSG00001",

&#x20; "sending\_application": "HospitalADT",

&#x20; "sending\_facility": "CUH",

&#x20; "timestamp": "20260418120000",

&#x20; "patient": {

&#x20;   "id": "PAT123456",

&#x20;   "name": "OBrien Seamus",

&#x20;   "dob": "19750315",

&#x20;   "gender": "M"

&#x20; },

&#x20; "ack": "AA",

&#x20; "stored": true

}

```



\---



\### POST /api/hl7/validate



Validates a message without storing it. Returns field-level errors.



\*\*Response (valid):\*\*

```json

{

&#x20; "valid": true,

&#x20; "message\_type": "ADT^A01",

&#x20; "checks\_passed": \["MSH present", "PID present", "MSH-9 populated", "PID-3 populated"]

}

```



\*\*Response (invalid — from payload\_invalid.json):\*\*

```json

{

&#x20; "valid": false,

&#x20; "ack": "AE",

&#x20; "errors": \["MSH-9 message type is missing", "PID-3 patient ID is empty"]

}

```



\---



\### GET /api/hl7/messages



Returns all processed messages from SQLite storage.



\*\*Response:\*\*

```json

{

&#x20; "total": 142,

&#x20; "messages": \[

&#x20;   {

&#x20;     "id": 1,

&#x20;     "message\_type": "ADT^A01",

&#x20;     "message\_id": "MSG00001",

&#x20;     "patient\_id": "PAT123456",

&#x20;     "ack\_code": "AA",

&#x20;     "processed\_at": "2026-04-18T12:00:01"

&#x20;   }

&#x20; ]

}

```



\---



\### GET /api/hl7/messages/\\<id\\>



Returns a single transaction by ID including full parsed content.



```bash

curl http://localhost:5000/api/hl7/messages/1

```



\---



\### GET /api/hl7/stats



Returns message volume breakdown by type and ACK code.



\*\*Response:\*\*

```json

{

&#x20; "total\_messages": 142,

&#x20; "by\_type": {

&#x20;   "ADT^A01": 58,

&#x20;   "ORU^R01": 41,

&#x20;   "ORM^O01": 28,

&#x20;   "ADT^A03": 10,

&#x20;   "ADT^A08": 5

&#x20; },

&#x20; "by\_ack": {

&#x20;   "AA": 135,

&#x20;   "AE": 5,

&#x20;   "AR": 2

&#x20; }

}

```



\---



\## Tech Stack



| Layer | Technology |

|---|---|

| Language | Python 3.13 |

| API Framework | Flask |

| HL7 Parsing | Custom parser (no external HL7 library) |

| Storage | SQLite via Python sqlite3 |

| Testing | pytest |

| CI/CD | GitHub Actions |

| Version Control | Git, GitHub |



\---



\## Setup and Run



```bash

\# 1. Clone the repo

git clone https://github.com/SaiTejaReddyYeldandi/-HL7-Integration-Engine---Message-Parser-Validator-REST.git

cd -HL7-Integration-Engine---Message-Parser-Validator-REST



\# 2. Install dependencies

pip install -r requirements.txt



\# 3. Run the engine

py run.py

\# API running at http://localhost:5000



\# 4. Test a valid message

curl -X POST http://localhost:5000/api/hl7/parse \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d @payload.json



\# 5. Test an invalid message

curl -X POST http://localhost:5000/api/hl7/validate \\

&#x20; -H "Content-Type: application/json" \\

&#x20; -d @payload\_invalid.json



\# 6. Run all tests

python -m pytest tests/ -v

```



\---



\## GitHub Actions CI/CD



Every push to `main` triggers the workflow:



1\. Spins up Ubuntu environment

2\. Installs Python dependencies

3\. Runs all pytest tests

4\. Reports pass/fail per test



If any test fails, the commit is marked failed. This mirrors how production integration engines are tested before deployment.



\---



\## Sample HL7 Messages



The `sample\_messages/` folder contains real-format HL7 files you can use with the API.



\*\*ADT^A01 — Patient Admission:\*\*

```

MSH|^\~\\\&|HospitalADT|CorkUniversityHospital|LabSystem|CUH|20260418120000||ADT^A01|MSG00001|P|2.3

PID|1||PAT123456^^^CUH^MR||OBrien^Seamus||19750315|M|||14 Patrick Street^^Cork^^T12AB34^IRL

PV1|1|I|EmergencyWard^Room3^Bed7^^^CUH||||DR12345^Murphy^Siobhan

```



\*\*ORU^R01 — Lab Result:\*\*

```

MSH|^\~\\\&|LabSystem|CUH|EHR|CUH|20260418140000||ORU^R01|MSG00002|P|2.3

PID|1||PAT123456^^^CUH^MR||OBrien^Seamus||19750315|M

OBR|1|ORD001|LAB001|88304^Haemoglobin|||20260418130000

OBX|1|NM|718-7^Haemoglobin|1|14.5|g/dL|13.5-17.5|N|||F

```



\*\*ORM^O01 — Lab Order:\*\*

```

MSH|^\~\\\&|EHR|CUH|LabSystem|CUH|20260418110000||ORM^O01|MSG00003|P|2.3

PID|1||PAT123456^^^CUH^MR||OBrien^Seamus||19750315|M

ORC|NW|ORD001|||||||20260418110000

OBR|1|ORD001||FBC^Full Blood Count|||20260418110000

```



\---



\## Validation Rules



The validator checks the following for every message:



| Check | Rule |

|---|---|

| MSH segment present | Every HL7 message must start with MSH |

| MSH-9 populated | Message type must be present (e.g. ADT^A01) |

| MSH-10 populated | Message control ID must be present for ACK matching |

| PID segment present | Patient identification required for ADT and ORU |

| PID-3 populated | Patient ID must not be empty |

| OBR present for ORU | Results must have an observation request segment |

| OBX present for ORU | Results must have at least one observation value |



\---



\## Interview Talking Points



\*\*"Tell me about your HL7 project"\*\*



> "I built a Python-based HL7 v2 integration engine from scratch — it parses inbound messages like ADT^A01 admissions and ORU^R01 lab results, validates required segments and fields, generates AA/AE/AR acknowledgements, routes messages based on type, and stores every transaction in SQLite. The whole thing is exposed as a Flask REST API and tested with pytest on GitHub Actions. It's the same workflow pattern that Mirth Connect and Rhapsody use in production — receive, parse, validate, acknowledge, route, store."



\*\*"What is an ADT^A01 message?"\*\*



> "ADT stands for Admission, Discharge, Transfer. A01 is the admit event. When a patient is admitted to a hospital, the registration system sends an ADT^A01 to all downstream systems — lab, pharmacy, ward management — so they're all aware of the new patient. The MSH segment identifies where it came from and where it's going. The PID segment carries the patient demographics. The PV1 segment carries the visit details — ward, room, bed, attending doctor."



\*\*"What is an ACK and why does it matter?"\*\*



> "An ACK is an acknowledgement — the receiving system sends it back to confirm what happened. AA means accepted and processed. AE means there was a validation error — maybe a required field was missing. AR means the message was rejected entirely — maybe it was malformed. In a real integration, if the sending system doesn't receive an AA within a timeout window, it resends the message. The ACK is what makes HL7 integration reliable."



\*\*"What's the difference between HL7 v2 and FHIR?"\*\*



> "HL7 v2 is pipe-delimited text — it's been in production in hospitals since the 1980s and is still the dominant standard in most existing systems. FHIR is the modern standard — it uses REST APIs and JSON, which makes it much easier to integrate with web applications and mobile systems. FHIR resources like Patient, Observation, and Encounter map directly to HL7 v2 segments like PID, OBX, and PV1. This project handles HL7 v2. FHIR is where the industry is moving."



\---



\## Connection to Real Integration Engines



This project mirrors the core logic of production tools:



| This Project | Mirth Connect / Rhapsody |

|---|---|

| Flask REST endpoint receives message | TCP/MLLP listener receives message |

| Custom Python parser | Built-in HL7 parser |

| Validator checks required fields | Channel filter rules |

| Router sends to correct handler | Channel routing by message type |

| SQLite transaction log | Built-in message log / dashboard |

| pytest tests | Manual channel testing |

| GitHub Actions CI | Deployment pipeline |



The concepts are identical. The tooling is different.



\---



\## All Projects — Portfolio Summary



| Project | Repo | Key Skills Demonstrated |

|---|---|---|

| HL7 Integration Engine | This repo | HL7 parsing, ACK generation, message routing, REST API, healthcare interoperability |

| Healthcare Pricing DB | optum-pricing-db | SQL Server, stored procedures, ETL pipeline, Streamlit dashboard |

| Azure ETL Pipeline | optum-azure-pipeline | Azure Data Factory, Databricks, PySpark, GitHub Actions |

| Churn Prediction API | optum-churn-api | XGBoost, Flask, SMOTE, pytest, Docker, Azure App Service |



\---



\*Built as part of targeted interview preparation for Solution Integration Engineer roles at Dedalus and Optum Ireland\*

\*Author: Sai Teja Reddy Yeldandi | github.com/SaiTejaReddyYeldandi\*

