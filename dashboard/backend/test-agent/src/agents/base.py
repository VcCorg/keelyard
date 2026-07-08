"Base agent class."
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class AgentMessage:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseAgent(ABC):
    def __init__(self, settings: Any = None):
        self.settings = settings
        self.history: List[AgentMessage] = []
        self._initialized = False
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        pass
    
    def add_to_history(self, role: str, content: str, **metadata) -> None:
        self.history.append(AgentMessage(role=role, content=content, metadata=metadata))
    
    def get_history(self, limit: Optional[int] = None) -> List[AgentMessage]:
        return self.history[-limit:] if limit else self.history
    
    async def run_interactive(self) -> None:
        from rich.console import Console
        from rich.prompt import Prompt
        console = Console()
        if not self._initialized:
            await self.initialize()
            self._initialized = True
        console.print("[green]Agent ready! Type quit to exit.[/green]")
        while True:
            try:
                user_input = Prompt.ask("[blue]You[/blue]")
                if user_input.lower() in ["quit", "exit", "q"]:
                    break
                if not user_input.strip():
                    continue
                self.add_to_history("user", user_input)
                response = await self.process({"message": user_input})
                assistant_response = response.get("response", "No response.")
                self.add_to_history("assistant", assistant_response)
                console.print(f"[green]Assistant:[/green] {assistant_response}")
            except KeyboardInterrupt:
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")
