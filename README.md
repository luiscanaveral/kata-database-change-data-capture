# CDC PoC — Ticket Platform

Change Data Capture proof-of-concept using Debezium, Kafka, PostgreSQL, and Azure Blob Storage (Azurite). Every row insert/update/delete in a ticket-platform schema is captured and persisted as JSON blobs, then replayable into a target database for verification.

## Prerequisites

- [Docker](https://docs.docker.com/engine/install/) + [Docker Compose](https://docs.docker.com/compose/install/)
- [Task](https://taskfile.dev/installation/) (task runner)
- Python 3.11+

## Quick Start

```bash
task up
```

This single command:
1. Builds and starts all Docker containers
2. Waits for Kafka Connect to be healthy
3. Registers the Debezium PostgreSQL connector
4. Installs Python dependencies
5. Launches the sink consumer and simulator

## What's Running

| Service        | Container              | Port(s)                           |
|----------------|------------------------|-----------------------------------|
| PostgreSQL     | `cdc-postgres`         | `5432`                            |
| PostgreSQL     | `cdc-postgres-target`  | `5433`                            |
| Kafka          | `cdc-kafka`            | `9092` (internal), `29092` (host) |
| Zookeeper      | `cdc-zookeeper`        | `2181`                            |
| Debezium       | `cdc-connect`          | `8083`                            |
| Azurite        | `cdc-azurite`          | `10000` (blobs)                   |
| Kafka UI       | `cdc-kafka-ui`         | `8080`                            |
| Sink           | `cdc-sink`             | —                                 |
| Simulator      | `cdc-simulator`        | —                                 |

## CDC Flow

1. **Simulator** inserts/updates a row in PostgreSQL every 15 seconds
2. **Debezium** captures the change from the WAL and publishes to a Kafka topic named `ticketdb.public.<table>`
3. **Sink** consumes all `ticketdb.public.*` topics and uploads each event as a JSON file to Azurite
4. **Blob path**: `cdc-events/{table_name}/{operation}/{YYYY}/{MM}/{DD}/{id}_{timestamp_ms}.json`

## Schema Change Detection with Alembic

[Alembic](https://alembic.sqlalchemy.org/) detects structural changes in the source PostgreSQL database and generates migrations to keep the target database in sync.

The workflow:

```bash
# Detect schema drift and auto-generate a migration
task db-revision

# Apply pending migrations to the target database
task db-upgrade

# Or both in one step
task db-migrate
```

Alembic compares the **source** database (`:5432`) — reflected at migration time — against the **target** database (`:5433`). Any difference (new tables, columns, constraints, etc.) is captured as a migration script in `alembic/versions/`.

Migrations are idempotent and should be committed to version control alongside schema changes.

## Restore & Verify

Replay captured CDC events from Azurite into the target database and compare:

```bash
# Apply schema migrations, then replay all CDC events
task restore

# Compare source vs target row-by-row
task diff

# Full pipeline: migrate → restore → diff
task verify
```

## Viewing CDC Events

**Kafka UI** — browse topics and messages: http://localhost:8080

**Azurite** — list stored blobs:
```bash
task azurite
```

**Azurite (REST)**:
```bash
curl "http://localhost:10000/devstoreaccount1/cdc-events?restype=container&comp=list"
```

## Stopping & Resetting

```bash
task docker-down      # Stop containers
task docker-down-v    # Stop and delete volumes
task docker-reset     # Full reset (down -v + up)
```

## File Layout

```
.
├── docker-compose.yml
├── Taskfile.yml                 # Task runner commands
├── pyproject.toml               # Python project config + deps
├── alembic.ini                  # Alembic configuration
├── alembic/
│   ├── env.py                   # Reflects source DB for autogenerate
│   └── versions/                # Migration scripts
├── .local/
│   └── postgres/
│       └── init.sql             # Source DB schema + seed data
├── src/
│   ├── sink/
│   │   ├── Dockerfile
│   │   └── consumer.py          # Kafka → Azurite bridge
│   ├── simulator/
│   │   ├── Dockerfile
│   │   └── simulate.py          # Data generator (15s interval)
│   ├── restore.py               # Replay CDC events → target DB
│   ├── diff.py                  # Compare source vs target
│   └── list_azurite.py          # Browse CDC blobs
└── scripts/
    ├── start.sh                 # Legacy one-command setup
    └── register-postgres-connector.sh
```
