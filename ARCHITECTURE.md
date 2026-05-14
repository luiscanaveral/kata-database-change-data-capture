# Architecture

## System Overview

```mermaid
graph TB
    subgraph "Data Sources"
        SIM[Simulator<br/>Python Script]
        PG[(PostgreSQL<br/>ticketdb<br/>:5432)]
    end

    subgraph "CDC Pipeline"
        ZK[Zookeeper]
        K[Kafka Broker]
        DC[Debezium Connect<br/>PostgreSQL Connector]
    end

    subgraph "Storage"
        AZ[Azurite<br/>Blob Storage<br/>cdc-events container]
    end

    subgraph "Verification"
        TGT[(PostgreSQL Target<br/>ticketdb<br/>:5433)]
        AL[Alembic<br/>Schema Sync]
    end

    subgraph "Monitoring"
        UI[Kafka UI]
    end

    SIM -->|writes data| PG
    PG -->|WAL| DC
    DC -->|CDC events| K
    K -->|topics: ticketdb.public.*| SINK[Sink Consumer<br/>Python]
    SINK -->|JSON blobs| AZ
    ZK --> K
    UI --> K

    AZ -->|task restore| RESTORE[Restore Script]
    RESTORE -->|replay events| TGT

    PG -.->|task db-revision| AL
    AL -.->|autogenerate migration| TGT
```

## Data Flow

```mermaid
sequenceDiagram
    participant Sim as Simulator
    participant PG as PostgreSQL
    participant DC as Debezium Connect
    participant K as Kafka
    participant Sink as Sink Consumer
    participant Az as Azurite

    Sim->>PG: INSERT/UPDATE/DELETE
    PG-->>DC: captures via WAL (pgoutput plugin)
    DC->>K: produces to ticketdb.public.<table>
    K->>Sink: consumes from topic
    Sink->>Az: uploads JSON blob<br/>path: <table>/<op>/<date>/<id>.json
```

## Restore & Verification Flow

```mermaid
sequenceDiagram
    participant Az as Azurite
    participant AL as Alembic
    participant TGT as Target DB (:5433)
    participant SRC as Source DB (:5432)
    participant D as Diff Script

    Note over AL: Detect schema drift
    AL->>SRC: reflect schema
    AL->>TGT: compare with current state
    AL->>TGT: apply migration if needed

    Note over Az,TGT: Replay CDC events
    Az->>TGT: sorted by creation time
    TGT-->>TGT: INSERT (c/r), UPDATE (u), DELETE (d)

    Note over D: Verify consistency
    D->>SRC: query all rows
    D->>TGT: query all rows
    D-->>D: compare row-by-row
    D->>D: report diffs (missing, extra, changed)
```

## Restore Logic

The restore script (`src/restore.py`) processes CDC blobs in FK-safe order:

```mermaid
flowchart LR
    A[Read all blobs<br/>from Azurite] --> B[Sort by<br/>creation time]
    B --> C[Group by table]
    C --> D[Process in<br/>dependency order]
    D --> E1[venues]
    D --> E2[artists]
    D --> E3[customers]
    D --> E4[events]
    D --> E5[sections]
    D --> E6[event_artists]
    D --> E7[orders]
    D --> E8[order_items]
    E1 --> F{op type?}
    E2 --> F
    E3 --> F
    E4 --> F
    E5 --> F
    E6 --> F
    E7 --> F
    E8 --> F
    F -->|c / r| G[INSERT]
    F -->|u| H[UPDATE by id]
    F -->|d| I[DELETE by id]
```

## Alembic Schema Sync

```mermaid
flowchart LR
    SRCDB[(Source DB<br/>:5432)] -->|sqlachemy reflect| REF[Reflected Metadata]
    REF --> AUTO{Alembic<br/>autogenerate}
    TGTDB[(Target DB<br/>:5433)] --> AUTO
    AUTO -->|detects differences| MIG[Migration Script<br/>alembic/versions/]
    MIG -->|alembic upgrade head| TGTDB
```

Alembic compares the current schema of the source database (reflected into `target_metadata`) against the target database's actual schema. Any drift — new tables, columns, constraints, or type changes — is captured in an auto-generated migration script.

## Database Schema

```mermaid
erDiagram
    venues ||--o{ events : has
    events ||--o{ sections : has
    events ||--o{ event_artists : has
    artists ||--o{ event_artists : performs
    customers ||--o{ orders : places
    orders ||--o{ order_items : contains
    sections ||--o{ order_items : references

    venues {
        int id PK
        string name
        string city
        string state
        string country
        int capacity
        timestamp created_at
        timestamp updated_at
    }

    artists {
        int id PK
        string name
        string genre
        text bio
        timestamp created_at
        timestamp updated_at
    }

    events {
        int id PK
        string title
        int venue_id FK
        timestamp event_date
        string status
        text description
        timestamp created_at
        timestamp updated_at
    }

    event_artists {
        int id PK
        int event_id FK
        int artist_id FK
        int performance_order
        timestamp created_at
    }

    sections {
        int id PK
        int event_id FK
        string name
        decimal price
        int capacity
        timestamp created_at
        timestamp updated_at
    }

    customers {
        int id PK
        string name
        string email
        string phone
        timestamp created_at
        timestamp updated_at
    }

    orders {
        int id PK
        int customer_id FK
        timestamp order_date
        decimal total_amount
        string status
        timestamp updated_at
    }

    order_items {
        int id PK
        int order_id FK
        int section_id FK
        int quantity
        decimal unit_price
        timestamp created_at
    }
```

## Services

| Service        | Image                                      | Port(s)           | Purpose                                 |
|----------------|--------------------------------------------|-------------------|-----------------------------------------|
| Zookeeper      | confluentinc/cp-zookeeper                  | 2181              | Kafka coordination                      |
| Kafka          | confluentinc/cp-kafka                      | 9092, 29092       | Message broker for CDC events           |
| PostgreSQL     | debezium/postgres                          | 5432              | Source database with WAL-level CDC      |
| PostgreSQL     | postgres                                   | 5433              | Target database for verification        |
| Debezium       | debezium/connect                           | 8083              | CDC connector runtime                   |
| Azurite        | mcr.microsoft.com/azure-storage/azurite    | 10000-10002       | Local Azure Blob Storage emulator       |
| Kafka UI       | provectuslabs/kafka-ui                     | 8080              | Kafka topic browser                     |
| Sink           | custom (Python)                            | —                 | Consumes CDC events, writes to Azurite  |
| Simulator      | custom (Python)                            | —                 | Generates random ticket data            |
