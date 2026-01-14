import typer
import asyncio
import logging
from rich.console import Console
from rich.logging import RichHandler
from .server import serve
from .agent import GeminiAgent
from .client import MCPClientManager
from .config import settings

# Configuration du logging sur stderr pour ne pas polluer stdout (utilisation de stdio)
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True, markup=True)]
)

app = typer.Typer()

@app.command()
def mcp():
    """Lance l'agent en mode Serveur MCP (pour connexion à Cursor)."""
    # Désactivation des logs sur stdout (utilisation de stdio)
    logging.getLogger().setLevel(logging.ERROR)
    asyncio.run(serve())

@app.command()
def ask(question: str):
    """Pose une question directe à l'agent depuis le terminal."""
    async def _run():
        client = MCPClientManager(settings.mcp_servers_config)
        agent = GeminiAgent(client)
        try:
            await client.connect()
            print(f"\n[bold green]Réponse:[/bold green]\n{await agent.run(question)}")
        finally:
            await client.cleanup()
            
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n[bold red]Interruption utilisateur (Ctrl+C).[/bold red]")
    except Exception as e:
        print(f"\n[bold red]Erreur fatale:[/bold red] {e}")

def main():
    app()

if __name__ == "__main__":
    main()
