from typing_extensions import Annotated, Sequence, TypedDict

import operator
from langchain_core.messages import BaseMessage


import json


def merge_dicts(a: dict[str, any], b: dict[str, any]) -> dict[str, any]:
    """Recursively merges two dictionaries for state updates."""
    res = a.copy()
    for k, v in b.items():
        if k in res and isinstance(res[k], dict) and isinstance(v, dict):
            res[k] = merge_dicts(res[k], v)
        else:
            res[k] = v
    return res


# Define agent state
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    data: Annotated[dict[str, any], merge_dicts]
    metadata: Annotated[dict[str, any], merge_dicts]


def show_agent_reasoning(output, agent_name):
    import time
    from colorama import Fore, Style
    # Kinetic pacing for narration
    print(f"   🧠 {Fore.CYAN}{agent_name}{Style.RESET_ALL} is synthesizing intelligence...")
    time.sleep(0.8) 
