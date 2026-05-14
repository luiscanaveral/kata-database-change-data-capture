# CDC PoC — Ticket Platform

Change Data Capture proof-of-concept using Debezium, Kafka, PostgreSQL, and Azure Blob Storage (Azurite). Every row insert/update/delete in a ticket-platform schema is captured and persisted as JSON blobs.

## Architecture

```
PostgreSQL ──(WAL)──> Debezium Connect ──(CDC events)──> Kafka ──(sink)──> Azurite (Blob Storage)
     ▲
     │ simulator (inserts/updates every 15s)
```

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/)
- `jq` (optional, for connector registration fallback)

## Quick Start

```bash
./scripts/start.sh
```

This single command:
1. Builds and starts all containers
2. Waits for Kafka Connect to be healthy
3. Registers the Debezium PostgreSQL connector

Alternatively, step-by-step:

```bash
# Start infrastructure
docker compose up -d --build

# Wait for Kafka Connect then register the connector
./scripts/register-postgres-connector.sh
```

## What's Running

| Service     | Container      | Port(s)                  |
|-------------|----------------|--------------------------|
| PostgreSQL  | `cdc-postgres`  | `5432`                   |
| Kafka       | `cdc-kafka`     | `9092` (internal), `29092` (host) |
| Zookeeper   | `cdc-zookeeper`  | `2181`                   |
| Debezium    | `cdc-connect`   | `8083`                   |
| Azurite     | `cdc-azurite`   | `10000` (blobs)          |
| Kafka UI    | `cdc-kafka-ui`  | `8080`                   |
| Sink        | `cdc-sink`      | —                        |
| Simulator   | `cdc-simulator` | —                        |

## Database Schema

Tables: `venues`, `artists`, `events`, `event_artists`, `sections`, `customers`, `orders`, `order_items`

All tables with `updated_at` have an automatic `BEFORE UPDATE` trigger.

## CDC Flow

1. **Simulator** inserts/updates a row in PostgreSQL every 15 seconds (random actions: new venue, artist, event, customer, order, status changes)
2. **Debezium** captures the change from the WAL and publishes to a Kafka topic named `ticketdb.public.<table>`
3. **Sink** (`sink/consumer.py`) consumes all `ticketdb.public.*` topics and uploads each event as a JSON file to Azurite
4. **Blob path** format: `cdc-events/{table_name}/{operation}/{YYYY}/{MM}/{DD}/{id}_{timestamp_ms}.json`

## Viewing CDC Events

**Kafka UI** — browse topics and messages: http://localhost:8080

**Azurite** — browse stored CDC blobs via the Azurite REST API or a tool like [Azure Storage Explorer](https://azure.microsoft.com/products/storage/storage-explorer/):
- Account: `devstoreaccount1`
- Key: `Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==`
- Blob endpoint: `http://localhost:10000/devstoreaccount1`

Or view directly via curl:
```bash
# List blobs
curl "http://localhost:10000/devstoreaccount1/cdc-events?restype=container&comp=list&prefix=venues/"

# Download a specific blob
curl "http://localhost:10000/devstoreaccount1/cdc-events/venues/create/2026/05/13/1_1712345678000.json"
```

**PostgreSQL** — connect directly to see live data:
```bash
psql -h localhost -U postgres -d ticketdb
```

## Stopping & Resetting

```bash
# Stop all containers
docker compose down

# Stop and delete all data (volumes)
docker compose down -v
```

## File Layout

```
.
├── docker-compose.yml              # Service definitions
├── postgres/
│   └── init.sql                    # Schema + seed data
├── sink/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── consumer.py                 # Kafka -> Azurite bridge
├── simulator/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── simulate.py                 # Data generator (15s interval)
└── scripts/
    ├── start.sh                    # One-command setup
    └── register-postgres-connector.sh  # Debezium connector registration
```
