\# HL7 Integration Engine — Message Parser, Validator \& REST API



A Python-based HL7 v2 integration engine built to understand healthcare interoperability workflows hands-on. The project parses inbound HL7 messages, validates required segments and fields, generates HL7 acknowledgements, routes messages to downstream systems, stores transactions in SQLite, and exposes everything through a Flask REST API.



\## Features



\- Parse HL7 v2 messages such as `ADT^A01`, `ORU^R01`, and `ORM^O01`

\- Extract MSH metadata and PID patient details

\- Validate required segments and required fields

\- Generate HL7 ACK responses: `AA`, `AE`, `AR`

\- Route messages based on message type

\- Store processed transactions in SQLite

\- Expose REST endpoints for parsing, validation, listing, and stats

\- Run automated tests with `pytest`

\- Run CI on GitHub Actions



\## Supported Message Types



\- `ADT^A01` — Admit patient

\- `ADT^A03` — Discharge patient

\- `ADT^A08` — Update patient details

\- `ORU^R01` — Observation result

\- `ORM^O01` — Order message



\## API Endpoints



\- `GET /health`

\- `POST /api/hl7/parse`

\- `POST /api/hl7/validate`

\- `GET /api/hl7/messages`

\- `GET /api/hl7/messages/<id>`

\- `GET /api/hl7/stats`



\## Run locally



```bash

py -m pip install -r requirements.txt

py run.py

