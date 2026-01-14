import json
import logging
from google import genai
from google.genai import types
from .config import settings
from .client import MCPClientManager

logger = logging.getLogger(__name__)

class GeminiAgent:
    def __init__(self, mcp_client: MCPClientManager):
        self.mcp_client = mcp_client
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model_id = 'gemini-2.5-flash'  # Utiliser un modèle récent et rapide

    async def run(self, user_prompt: str) -> str:
        """Exécute la boucle principale de l'agent : Réflexion -> Outil -> Réponse."""
        
        # 1. Récupérer les outils disponibles
        tools = await self.mcp_client.get_available_tools()
        tools_desc = json.dumps(tools, indent=2, ensure_ascii=False)

        # 2. Construire le prompt système
        system_instruction = (
            "Tu es un expert en sécurité informatique.\n"
            "Ton objectif est d'analyser la sécurité des dépôts GitHub.\n"
            "Tu as accès à des outils externes via MCP (Model Context Protocol).\n"
            "Prends bien en compte la branche ou la version spécifiée par l'utilisateur si elle est présente (paramètre 'branch' ou 'ref' dans les outils GitHub).\n"
            "Si tu ne trouves pas avec 'branch' ou 'ref', regarde dans les releases"
            "Voici les éléments à analyser :\n"
            " - popularité : nombre d'étoiles et de forks\n"
            " - maintenance : nombre de `contributors` actifs et réguliers\n"
            " - dernière version : `latest release`\n"
            " - présence de CVE : recherche les CVE sur le dépôt et sa version si elle est spécifiée avec les outils `vul_vendor_products` et `vul_vendor_product_cve`\n"
            f"Outils disponibles :\n{tools_desc}\n\n"
            "Si tu dois utiliser un outil, réponds UNIQUEMENT avec un JSON au format suivant :\n"
            '{"server": "nom_serveur", "tool": "nom_outil", "arguments": {"arg1": "valeur"}}\n'
            'Si un outil retourne une erreur, essaie un autre outil ou passe à la suite.\n'
            "Sinon, uniquement si tu ne prévois plus d'utiliser d'outils, fournis ta réponse finale en texte clair en faisant une synthèse en moins de 10 lignes de ton analyse."
        )
        
        # 3. Boucle principale de conversation (Multi-step)
        messages = [f"{system_instruction}\n\nQuestion: {user_prompt}"]
        
        while True:
            try:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=messages
                )
    
                if not response.text:
                    return "Erreur: Réponse vide de Gemini."

                # Vérifier si c'est un appel d'outil
                if '{"server":' in response.text:
                    tool_result_msg = await self._execute_tool(response.text)
                    messages.append(response.text)
                    messages.append(tool_result_msg)
                # Sinon, c'est la réponse finale
                else:
                    return response.text
                    
            except Exception as e:
                return f"Erreur dans la boucle de réflexion : {e}"

    async def _execute_tool(self, response_text: str) -> str:
        """Parse et exécute l'outil, retourne le message de résultat formaté."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if not json_match:
                return "System: Erreur - JSON d'outil non trouvé."

            call_data = json.loads(json_match.group())
            
            tool_name = call_data.get('tool')
            server_name = call_data.get('server')
            args = call_data.get('arguments', {})

            logger.info(f"Appel outil: {tool_name} sur {server_name} avec {args}")
            
            result = await self.mcp_client.call_tool(server_name, tool_name, args)
            return f"System: Résultat de l'outil ({tool_name}): {result}"

        except Exception as e:
            logger.error(f"Erreur exécution outil: {e}")
            return f"System: Erreur lors de l'exécution de l'outil: {e}"

