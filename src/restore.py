import os
import json
import logging
from datetime import datetime

import psycopg2
from azure.storage.blob import BlobServiceClient
from rich.console import Console
from rich.table import Table
from rich.progress import Progress

logging.basicConfig(level=logging.WARNING)

TARGET_HOST = os.environ["TGT_PG_HOST"]
TARGET_PORT = int(os.environ["TGT_PG_PORT"])
TARGET_DB = os.environ["TGT_PG_DB"]
TARGET_USER = os.environ["TGT_PG_USER"]
TARGET_PASS = os.environ["TGT_PG_PASS"]

AZURITE_CONN_STR = os.environ["AZURITE_CONNECTION_STRING"]
CONTAINER_NAME = os.environ.get("BLOB_CONTAINER", "cdc-events")

TABLE_ORDER = [
    "venues",
    "artists",
    "customers",
    "events",
    "sections",
    "event_artists",
    "orders",
    "order_items",
]

OP_MAP = {"c": "create", "r": "snapshot", "u": "update", "d": "delete"}


def to_pg_value(val):
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return val
    return str(val)


def apply_event(cur, table, op, after, before):
    if op in ("c", "r") and after:
        keys = [k for k in after if k != "_rows"]
        cols = ", ".join(keys)
        placeholders = ", ".join("%s" for _ in keys)
        values = [to_pg_value(after[k]) for k in keys]
        cur.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING",
            values,
        )
    elif op == "u" and after:
        keys = [k for k in after if k not in ("_rows", "id")]
        if not keys:
            return
        sets = ", ".join(f"{k} = %s" for k in keys)
        values = [to_pg_value(after[k]) for k in keys]
        values.append(to_pg_value(after["id"]))
        cur.execute(f"UPDATE {table} SET {sets} WHERE id = %s", values)
    elif op == "d" and before:
        cur.execute(f"DELETE FROM {table} WHERE id = %s", (to_pg_value(before["id"]),))


def main():
    console = Console()

    blob_svc = BlobServiceClient.from_connection_string(AZURITE_CONN_STR)
    container = blob_svc.get_container_client(CONTAINER_NAME)

    try:
        container.get_container_properties()
    except Exception:
        console.print(f"[red]Container '{CONTAINER_NAME}' not found[/red]")
        return

    conn = psycopg2.connect(
        host=TARGET_HOST,
        port=TARGET_PORT,
        dbname=TARGET_DB,
        user=TARGET_USER,
        password=TARGET_PASS,
    )
    conn.autocommit = False
    cur = conn.cursor()

    blobs = sorted(container.list_blobs(), key=lambda b: b.creation_time or b.name)

    by_table: dict[str, list] = {t: [] for t in TABLE_ORDER}
    for b in blobs:
        parts = b.name.split("/")
        table = parts[0]
        if table in by_table:
            by_table[table].append(b)

    total = sum(len(v) for v in by_table.values())
    counts = {t: 0 for t in TABLE_ORDER}
    errors = []

    with Progress() as progress:
        task = progress.add_task("Restoring...", total=total)

        for table in TABLE_ORDER:
            table_blobs = by_table.get(table, [])
            for b in table_blobs:
                try:
                    blob_data = json.loads(container.get_blob_client(b.name).download_blob().readall())
                    payload = blob_data.get("payload", {})
                    op = payload.get("op", "r")
                    after = payload.get("after")
                    before = payload.get("before")
                    apply_event(cur, table, op, after, before)
                    counts[table] += 1
                except Exception as e:
                    errors.append((table, b.name, str(e)))
                progress.update(task, advance=1)

    conn.commit()

    summary = Table(title="Restore Summary")
    summary.add_column("Table", style="cyan")
    summary.add_column("Events Applied", justify="right")
    for t in TABLE_ORDER:
        summary.add_row(t, str(counts[t]))
    console.print(summary)

    if errors:
        err_table = Table(title="Errors", style="red")
        err_table.add_column("Table")
        err_table.add_column("Blob")
        err_table.add_column("Error")
        for tbl, blob_name, err in errors[:20]:
            err_table.add_row(tbl, blob_name, err)
        console.print(err_table)

    cur.close()
    conn.close()

    console.print(f"\n[green]Restore complete: {total} events processed[/green]")


if __name__ == "__main__":
    main()
