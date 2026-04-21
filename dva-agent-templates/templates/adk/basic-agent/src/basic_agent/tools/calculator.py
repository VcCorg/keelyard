"""Calculator tool for Basic Agent."""

import logging
from typing import Union

from google.adk.tools import Tool

logger = logging.getLogger(__name__)


class CalculatorTool(Tool):
    """A calculator tool for performing mathematical operations."""
    
    def __init__(self) -> None:
        """Initialize the calculator tool."""
        super().__init__(
            name="calculator",
            description="A calculator tool for performing mathematical operations",
            parameters={
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '15 * 23', 'sqrt(16)', '2^3')",
                }
            },
        )
    
    async def run(self, expression: str) -> Union[float, str]:
        """Evaluate a mathematical expression.
        
        Args:
            expression: Mathematical expression to evaluate
            
        Returns:
            Result of the evaluation or error message
        """
        try:
            # Safe evaluation of mathematical expressions
            # Only allow certain operations and functions
            allowed_names = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
            }
            
            # Replace common mathematical functions
            expression = expression.replace("^", "**")
            expression = expression.replace("sqrt", "**0.5")
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            
            if isinstance(result, (int, float)):
                return float(result)
            else:
                return str(result)
                
        except Exception as e:
            logger.error(f"Error evaluating expression '{expression}': {e}")
            return f"Error: Could not evaluate '{expression}'. Please check the expression."
