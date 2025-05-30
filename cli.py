import click
import uvicorn
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table

from .config.settings import settings
from .config.streams import stream_config_manager


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
    table = Table(title="Configured Streams")
    table.add_column("Stream Name", style="cyan")
    table.add_column("Target Table", style="green")
    table.add_column("Chunk Size", justify="right", style="yellow")
    table.add_column("Compression", style="magenta")

    config = stream_config_manager._config
    for name, stream in config.streams.items():
        compression = (
            f"{stream.compression['algorithm']} (level {stream.compression['level']})"
        )
        table.add_row(name, stream.target_table, str(stream.chunk_size), compression)

    console.print(table)


@cli.command()
@click.argument("stream_name")
@click.argument("arrow_file", type=click.Path(exists=True))
def ingest(stream_name, arrow_file):
    """Ingest an Arrow IPC file into a stream 📥"""
    import requests
    import pyarrow as pa

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

    if response.status_code == 200:
        result = response.json()
        console.print(
            f"[green]Successfully ingested {result['rows_processed']} rows[/green]"
        )
    else:
        console.print(f"[red]Error: {response.text}[/red]")


if __name__ == "__main__":
    cli()
