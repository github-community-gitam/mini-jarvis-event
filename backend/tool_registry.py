import json
from typing import Dict, Any, Callable, List

class ToolRegistry:
    def __init__(self):
        self.tools = {}

    def register(self, name: str, description: str, parameters: Dict[str, Any], func: Callable, requires_confirmation: bool = False, required_permissions: str = ""):
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "func": func,
            "requires_confirmation": requires_confirmation,
            "required_permissions": required_permissions
        }

    def get_tool(self, name: str):
        return self.tools.get(name)

    def get_all_tools_for_llm(self) -> List[Dict[str, Any]]:
        llm_tools = []
        for name, tool in self.tools.items():
            llm_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            })
        return llm_tools

registry = ToolRegistry()
