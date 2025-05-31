import click
import uvicorn
from rich.console import Console
from rich.table import Table

from .config.settings import settings
from .config.streams import stream_config_manager
from .constants import HTTP_200_OK

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


@cli.command()
@click.argument("stream_name")
@click.argument("arrow_file", type=click.Path(exists=True))
def ingest(stream_name, arrow_file):
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
    else:
        console.print(f"Error: {response.text}", style="red")


if __name__ == "__main__":
    cli()
