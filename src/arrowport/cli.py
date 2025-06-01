import click
import uvicorn
from rich.console import Console
from rich.table import Table

from .config.settings import settings
from .config.streams import stream_config_manager
from .constants import HTTP_200_OK
from .core.storage import get_storage_backend

console = Console()


@click.group()
def cli():
    """Arrowport CLI - Your friendly data landing controller 🛬"""
    pass


@cli.command()
@click.option("--host", default=settings.api_host, help="Host to bind to")
@click.option("--port", default=settings.api_port, help="Port to bind to")
@click.option("--reload/--no-reload", default=True, help="Enable auto-reload")
def serve(host, port, reload):
    """Start the Arrowport server 🚀"""
    console.print(f"[green]Starting Arrowport server on {host}:{port}[/green]")
    uvicorn.run(
        "arrowport.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )


@cli.command()
def streams():
    """List configured streams 📋"""
    try:
        config = stream_config_manager._configs
        if not config:
            console.print("[yellow]No streams configured[/yellow]")
            return

        table = Table(title="Configured Streams")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Path", style="blue")
        table.add_column("Compression", style="magenta")

        for name, stream in config.items():
            table.add_row(
                name,
                stream.get("type", "unknown"),
                stream.get("path", "N/A"),
                stream.get("compression", "none"),
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error listing streams: {str(e)}[/red]")
        raise click.Abort()


@cli.group()
def delta():
    """Delta Lake operations 🏔️"""
    pass


@delta.command()
def list():
    """List Delta Lake tables 📊"""
    try:
        from pathlib import Path

        delta_path = Path(settings.delta_config.table_path)
        if not delta_path.exists():
            console.print("[yellow]No Delta tables found[/yellow]")
            return

        table = Table(title="Delta Lake Tables")
        table.add_column("Table", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Files", style="blue")
        table.add_column("Size", style="magenta")
        table.add_column("Rows", style="yellow")

        storage = get_storage_backend("delta")

        for item in delta_path.iterdir():
            if item.is_dir() and (item / "_delta_log").exists():
                try:
                    info = storage.get_table_info(item.name)
                    size_mb = info["total_size_bytes"] / (1024 * 1024)
                    table.add_row(
                        item.name,
                        str(info["version"]),
                        str(info["file_count"]),
                        f"{size_mb:.2f} MB",
                        f"{info['row_count']:,}",
                    )
                except Exception as e:
                    table.add_row(item.name, "Error", str(e), "-", "-")

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error listing Delta tables: {str(e)}[/red]")
        raise click.Abort()


@delta.command()
@click.argument("table_name")
@click.option("--limit", default=10, help="Number of history entries to show")
def history(table_name, limit):
    """Show Delta table history 📜"""
    try:
        from deltalake import DeltaTable

        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            console.print(f"[red]Delta table '{table_name}' not found[/red]")
            return

        table_path = storage._get_table_path(table_name)
        dt = DeltaTable(table_path)
        history_entries = dt.history(limit=limit)

        table = Table(title=f"History for {table_name}")
        table.add_column("Version", style="cyan")
        table.add_column("Timestamp", style="green")
        table.add_column("Operation", style="blue")
        table.add_column("User", style="magenta")
        table.add_column("Parameters", style="yellow")

        for entry in history_entries:
            table.add_row(
                str(entry.get("version", "")),
                str(entry.get("timestamp", "")),
                entry.get("operation", ""),
                entry.get("userName", "unknown"),
                str(entry.get("operationParameters", {}))[:50] + "...",
            )

        console.print(table)
    except Exception as e:
        console.print(f"[red]Error getting table history: {str(e)}[/red]")
        raise click.Abort()


@delta.command()
@click.argument("table_name")
@click.option(
    "--retention-hours", default=168, help="Hours to retain old files (default: 7 days)"
)
@click.option("--dry-run/--no-dry-run", default=True, help="Perform a dry run")
def vacuum(table_name, retention_hours, dry_run):
    """Clean up old Delta table files 🧹"""
    try:
        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            console.print(f"[red]Delta table '{table_name}' not found[/red]")
            return

        if dry_run:
            console.print(
                f"[yellow]Performing dry run for vacuum on '{table_name}'...[/yellow]"
            )
        else:
            console.print(f"[yellow]Running vacuum on '{table_name}'...[/yellow]")

        if not dry_run:
            result = storage.vacuum(table_name, retention_hours)
            console.print("[green]Vacuum complete![/green]")
            console.print(f"Files removed: {result['files_removed']}")
            console.print(f"Files remaining: {result['files_remaining']}")
        else:
            # For dry run, just show what would be done
            info = storage.get_table_info(table_name)
            console.print(f"Current file count: {info['file_count']}")
            console.print(f"Retention period: {retention_hours} hours")
            console.print(
                "[yellow]Run with --no-dry-run to actually remove files[/yellow]"
            )

    except Exception as e:
        console.print(f"[red]Error running vacuum: {str(e)}[/red]")
        raise click.Abort()


@delta.command()
@click.argument("table_name")
@click.argument("version", type=int)
def restore(table_name, version):
    """Restore Delta table to a specific version ⏪"""
    try:
        storage = get_storage_backend("delta")

        if not storage.table_exists(table_name):
            console.print(f"[red]Delta table '{table_name}' not found[/red]")
            return

        info = storage.get_table_info(table_name)
        current_version = info["version"]

        if version == current_version:
            console.print(f"[yellow]Table is already at version {version}[/yellow]")
            return

        console.print(
            f"[yellow]Restoring '{table_name}' from version {current_version} to version {version}...[/yellow]"
        )

        result = storage.restore(table_name, version)

        console.print("[green]Restore complete![/green]")
        console.print(
            f"Restored from version {result['restored_from']} to version {result['restored_to']}"
        )

    except Exception as e:
        console.print(f"[red]Error restoring table: {str(e)}[/red]")
        raise click.Abort()


@cli.command()
@click.argument("stream_name")
@click.argument("arrow_file", type=click.Path(exists=True))
@click.option(
    "--backend", type=click.Choice(["duckdb", "delta"]), help="Storage backend to use"
)
@click.option(
    "--partition-by", multiple=True, help="Columns to partition by (Delta Lake only)"
)
def ingest(stream_name, arrow_file, backend, partition_by):
    """Ingest an Arrow IPC file into a stream 📥"""
    import pyarrow as pa
    import requests

    # Read the Arrow file
    with pa.memory_map(arrow_file, "rb") as source:
        reader = pa.ipc.open_stream(source)
        table = reader.read_all()

    # Get stream config
    config = stream_config_manager.get_stream_config(stream_name)
    if not config:
        console.print(
            f"[red]Error: Stream '{stream_name}' not found in configuration[/red]"
        )
        return

    # Override backend if specified
    if backend:
        config.storage_backend = backend

    # Add partition_by for Delta Lake
    if partition_by and backend == "delta":
        if not config.delta_options:
            from .models.arrow import DeltaOptions

            config.delta_options = DeltaOptions(partition_by=list(partition_by))
        else:
            config.delta_options.partition_by = list(partition_by)

    # Send to Arrowport
    sink = pa.BufferOutputStream()
    writer = pa.ipc.new_stream(sink, table.schema)
    writer.write_table(table)
    writer.close()

    response = requests.post(
        f"http://{settings.api_host}:{settings.api_port}/stream/{stream_name}",
        json={
            "config": config.model_dump(),
            "batch": {
                "schema": table.schema.to_dict(),
                "data": sink.getvalue().to_pybytes(),
            },
        },
    )

    if response.status_code == HTTP_200_OK:
        result = response.json()
        console.print(f"Successfully processed stream: {result['rows_processed']} rows")
        console.print(f"Storage backend: {result.get('storage_backend', 'unknown')}")
    else:
        console.print(f"Error: {response.text}", style="red")


if __name__ == "__main__":
    cli()
