import os

import psycopg2
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

SRC_HOST = os.environ.get("SRC_PG_HOST", "localhost")
SRC_PORT = int(os.environ.get("SRC_PG_PORT", "5432"))
SRC_DB = os.environ.get("SRC_PG_DB", "ticketdb")
SRC_USER = os.environ.get("SRC_PG_USER", "postgres")
SRC_PASS = os.environ.get("SRC_PG_PASS", "postgres")

TGT_HOST = os.environ.get("TGT_PG_HOST", "localhost")
TGT_PORT = int(os.environ.get("TGT_PG_PORT", "5433"))
TGT_DB = os.environ.get("TGT_PG_DB", "ticketdb")
TGT_USER = os.environ.get("TGT_PG_USER", "postgres")
TGT_PASS = os.environ.get("TGT_PG_PASS", "postgres")

TABLES = [
    "venues",
    "artists",
    "customers",
    "events",
    "sections",
    "event_artists",
    "orders",
    "order_items",
]

KEY_COLS = {"event_artists": ["event_id", "artist_id"]}
SKIP_COLS = {"event_artists": ["id"]}


def key_cols_for(table):
    return KEY_COLS.get(table, ["id"])


def order_cols_for(table):
    keys = key_cols_for(table)
    return ", ".join(keys)


def where_for(table):
    keys = key_cols_for(table)
    return " AND ".join(f"a.{k} = b.{k}" for k in keys)


def fetch_all(cur, table):
    cur.execute(f"SELECT * FROM {table} ORDER BY {order_cols_for(table)}")
    cols = [desc[0] for desc in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return cols, rows


def rows_by_key(rows, table):
    keys = key_cols_for(table)
    return {tuple(r[k] for k in keys): r for r in rows}


def compare_rows(src_row, tgt_row, table):
    diffs = {}
    skip = set(SKIP_COLS.get(table, []))
    all_keys = set(src_row.keys()) | set(tgt_row.keys())
    for k in all_keys:
        if k in skip:
            continue
        sv = src_row.get(k)
        tv = tgt_row.get(k)
        if sv != tv:
            diffs[k] = (sv, tv)
    return diffs


def col_type(val):
    if isinstance(val, int):
        return "int"
    if isinstance(val, float):
        return "float"
    return "str"


def main():
    console = Console()

    src = psycopg2.connect(host=SRC_HOST, port=SRC_PORT, dbname=SRC_DB, user=SRC_USER, password=SRC_PASS)
    tgt = psycopg2.connect(host=TGT_HOST, port=TGT_PORT, dbname=TGT_DB, user=TGT_USER, password=TGT_PASS)
    src_cur = src.cursor()
    tgt_cur = tgt.cursor()

    for table in TABLES:
        src_cols, src_rows = fetch_all(src_cur, table)
        tgt_cols, tgt_rows = fetch_all(tgt_cur, table)

        src_by_key = rows_by_key(src_rows, table)
        tgt_by_key = rows_by_key(tgt_rows, table)
        src_keys = set(src_by_key.keys())
        tgt_keys = set(tgt_by_key.keys())

        only_src = src_keys - tgt_keys
        only_tgt = tgt_keys - src_keys
        common = src_keys & tgt_keys

        diff_count = 0
        for key in sorted(common):
            diffs = compare_rows(src_by_key[key], tgt_by_key[key], table)
            if diffs:
                diff_count += 1

        status = "[green]OK[/green]"
        if only_src or only_tgt or diff_count:
            parts = []
            if only_src:
                parts.append(f"[red]{len(only_src)} missing in target[/red]")
            if only_tgt:
                parts.append(f"[yellow]{len(only_tgt)} extra in target[/yellow]")
            if diff_count:
                parts.append(f"[red]{diff_count} rows differ[/red]")
            status = " | ".join(parts)

        panel = Panel(
            f"Source: [cyan]{len(src_rows)}[/cyan] rows  |  Target: [cyan]{len(tgt_rows)}[/cyan] rows\n{status}",
            title=f"[bold]{table}[/bold]",
        )
        console.print(panel)

        if only_src:
            t = Table("Key", "Columns")
            for key in sorted(only_src)[:10]:
                r = src_by_key[key]
                preview = ", ".join(f"{k}={v}" for k, v in list(r.items())[:4])
                t.add_row(str(key), preview)
            console.print(t)

        if diff_count:
            t = Table("Key", "Column", "Source", "Target")
            shown = 0
            for key in sorted(common):
                diffs = compare_rows(src_by_key[key], tgt_by_key[key], table)
                for col, (sv, tv) in diffs.items():
                    if shown >= 15:
                        break
                    t.add_row(str(key), col, str(sv), str(tv))
                    shown += 1
                if shown >= 15:
                    break
            if shown:
                console.print(t)

    src_cur.close()
    src.close()
    tgt_cur.close()
    tgt.close()


if __name__ == "__main__":
    main()
