import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from .config import settings
from .client import MCPClientManager
from .agent import GeminiAgent

async def serve():
    app = Server("ai-agent-server")

    @app.list_tools()
    async def list_tools():
        return [
            Tool(
                name="ask_security_agent",
                description="Pose une question à l'agent expert en sécurité capable d'utiliser GitHub et d'autres outils pour analyser la sécurité d'un dépôt.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "question": {"type": "string", "description": "La question à poser à l'agent"}
                    },
                    "required": ["question"]
                }
            )
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        if name != "ask_security_agent":
            raise ValueError(f"Outil inconnu: {name}")

        question = arguments.get("question")
        
        mcp_client = MCPClientManager(settings.mcp_servers_config)
        agent = GeminiAgent(mcp_client)
        
        try:
            await mcp_client.connect()
            response = await agent.run(question)
            return [TextContent(type="text", text=response)]
        finally:
            await mcp_client.cleanup()

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )
