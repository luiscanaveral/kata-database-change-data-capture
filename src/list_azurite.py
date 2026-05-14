import os
from azure.storage.blob import BlobServiceClient
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich import print as rprint

CONN_STR = os.environ.get(
    "AZURITE_CONNECTION_STRING",
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;",
)
CONTAINER = os.environ.get("BLOB_CONTAINER", "cdc-events")


def main():
    console = Console()

    svc = BlobServiceClient.from_connection_string(CONN_STR)
    container = svc.get_container_client(CONTAINER)

    try:
        container.get_container_properties()
    except Exception:
        rprint(f"[red]Container '{CONTAINER}' not found[/red]")
        return

    blobs = list(container.list_blobs())

    if not blobs:
        rprint(f"[yellow]No blobs in '{CONTAINER}'[/yellow]")
        return

    tree = Tree(f":cloud: [bold]{CONTAINER}[/bold] ({len(blobs)} blobs)")
    tables = {}

    for b in blobs:
        parts = b.name.split("/")
        table_name = parts[0]
        op = parts[1] if len(parts) > 1 else "?"
        if table_name not in tables:
            branch = tree.add(f"[bold cyan]{table_name}[/bold cyan]")
            tables[table_name] = branch
        tables[table_name].add(f"[dim]{b.name}[/dim]")

    console.print(tree)

    table = Table(title=f"Blobs in {CONTAINER}")
    table.add_column("Table", style="cyan")
    table.add_column("Operation", style="magenta")
    table.add_column("Path", style="dim")
    table.add_column("Size", justify="right")

    for b in sorted(blobs, key=lambda x: x.name):
        parts = b.name.split("/")
        table_name = parts[0]
        op = parts[1] if len(parts) > 1 else "?"
        size = f"{b.size / 1024:.1f} KB" if b.size else "-"
        table.add_row(table_name, op, b.name, size)

    console.print(table)


if __name__ == "__main__":
    main()
