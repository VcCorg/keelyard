"""Agent for Multi-Agent System."""
from typing import Any, Dict
import os

from google import genai

from agents.base import BaseAgent

class OrchestratorAgent(BaseAgent):
    def __init__(self, settings: Any = None):
        super().__init__(settings)
        self.client = None
        self.model_name = "gemini-2.0-flash-001"
    
    async def initialize(self) -> None:
        self.model_name = self.settings.vertex_ai_model if self.settings else "gemini-2.0-flash-001"
        self.client = None
        try:
            if self.settings and self.settings.google_project_id:
                self.client = genai.Client(
                    vertexai=True,
                    project=self.settings.google_project_id,
                    location=self.settings.google_location,
                )
            elif os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
                self.client = genai.Client()
        except Exception:
            # Defer credential/config errors to first use so the agent can still start.
            self.client = None
        self._initialized = True
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            await self.initialize()
        if self.client is None:
            return {
                "response": "Model client not configured. Set GOOGLE_PROJECT_ID (Vertex AI) or GOOGLE_API_KEY (AI Studio).",
                "status": "error",
            }
        message = input_data.get("message", "")
        history = "\n".join(f"{m.role}: {m.content}" for m in self.get_history(10))
        prompt = f"You are a helpful Multi-Agent System.\n\nHistory:\n{history}\n\nUser: {message}\n\nAssistant:"
        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return {"response": response.text, "status": "success"}
        except Exception as e:
            return {"response": f"Error: {str(e)}", "status": "error"}


# --- Evaluation entrypoint --------------------------------------------------
# Module-level callable so this agent is evaluation-ready by default:
#   keel eval run agent <module.path>:answer <eval-config>
_eval_agent = None


async def answer(input_text: str) -> str:
    """Run OrchestratorAgent on a single input and return its response text."""
    global _eval_agent
    if _eval_agent is None:
        try:
            from config import Settings
            _eval_agent = OrchestratorAgent(settings=Settings())
        except Exception:
            _eval_agent = OrchestratorAgent()
    result = await _eval_agent.process({"message": input_text})
    if isinstance(result, dict):
        return str(result.get("response", ""))
    return str(result)
