import asyncio
import json
import logging
from contextlib import AsyncExitStack
from typing import Dict, List, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

class MCPClientManager:
    """Gère les connexions aux multiples serveurs MCP."""
    
    def __init__(self, servers_config_json: str):
        self.servers_config = json.loads(servers_config_json)
        self.exit_stack = AsyncExitStack()
        self.sessions: Dict[str, ClientSession] = {}

    async def connect(self):
        """Connecte l'agent à tous les serveurs MCP configurés."""
        for name, config in self.servers_config.items():
            try:
                server_params = StdioServerParameters(
                    command=config['command'],
                    args=config['args'],
                    env={**config.get('env', {})}
                )

                transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
                session = await self.exit_stack.enter_async_context(ClientSession(transport[0], transport[1]))
                await session.initialize()
                
                self.sessions[name] = session
                logger.info(f"Connecté au serveur MCP: {name}")
                
            except Exception as e:
                logger.error(f"Erreur de connexion au serveur {name}: {e}")

    async def get_available_tools(self) -> List[Dict[str, Any]]:
        """Récupère tous les outils disponibles sur les serveurs connectés."""
        all_tools = []
        for server_name, session in self.sessions.items():
            result = await session.list_tools()
            for tool in result.tools:
                all_tools.append({
                    "server": server_name,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
        return all_tools

    async def call_tool(self, server: str, tool_name: str, arguments: Dict[str, Any]):
        """Exécute un outil sur un serveur spécifique."""
        if server not in self.sessions:
            raise ValueError(f"Serveur {server} inconnu.")
        
        result = await self.sessions[server].call_tool(tool_name, arguments)
        return result.content

    async def cleanup(self):
        """Ferme proprement toutes les connexions."""
        await self.exit_stack.aclose()
