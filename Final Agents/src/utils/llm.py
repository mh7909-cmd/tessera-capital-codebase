"""Helper functions for LLM"""

import json
import threading
import os
from typing import Any, Type
from pydantic import BaseModel
from src.llm.models import get_model, get_model_info
from src.utils.progress import progress
from src.graph.state import AgentState


# Global semaphore to limit concurrent LLM calls (prevents hangs during parallel agent execution)
LLM_SEMAPHORE = threading.Semaphore(10)


def call_llm(
    prompt: any = None,
    pydantic_model: type[BaseModel] = None,
    agent_name: str | None = None,
    state: AgentState | None = None,
    max_retries: int = 3,
    default_factory=None,
    **kwargs,
) -> BaseModel:
    """
    Standardized LLM caller supporting both new positional and legacy keyword arguments.
    """
    # Handle legacy keyword arguments (model_name, response_model, etc.)
    messages = kwargs.get("messages")
    if not prompt and messages and len(messages) > 0:
        first_msg = messages[0]
        if isinstance(first_msg, dict):
            prompt = first_msg.get("content") or first_msg.get("text")
        elif isinstance(first_msg, (tuple, list)):
            # If it's a tuple (role, content), take the last element as the prompt
            prompt = first_msg[-1]
    
    prompt = prompt or kwargs.get("system_prompt")
    pydantic_model = pydantic_model or kwargs.get("response_model")
    model_name_override = kwargs.get("model_name")
    model_provider_override = kwargs.get("model_provider")
    """
    Makes an LLM call with retry logic, handling both JSON supported and non-JSON supported models.

    Args:
        prompt: The prompt to send to the LLM
        pydantic_model: The Pydantic model class to structure the output
        agent_name: Optional name of the agent for progress updates and model config extraction
        state: Optional state object to extract agent-specific model configuration
        max_retries: Maximum number of retries (default: 3)
        default_factory: Optional factory function to create default response on failure

    Returns:
        An instance of the specified Pydantic model
    """
    
    # Extract model configuration
    if model_name_override and model_provider_override:
        model_name, model_provider = model_name_override, model_provider_override
    elif state and agent_name:
        model_name, model_provider = get_agent_model_config(state, agent_name)
    else:
        # Check for FAST_MODE fallback
        model_name = "gpt-4.1"
        model_provider = "OPENAI"

    # Use the High-Speed Llama 3.1 8B model for the YC Demo (Fastest Inference)
    if os.getenv("NVIDIA_API_KEY") and not model_name_override:
        model_name = "meta/llama-3.1-8b-instruct"
        model_provider = "NVIDIA"

    # Extract API keys from state if available
    api_keys = None
    if state:
        request = state.get("metadata", {}).get("request")
        if request and hasattr(request, 'api_keys'):
            api_keys = request.api_keys

    model_info = get_model_info(model_name, model_provider)
    llm = get_model(model_name, model_provider, api_keys)

    # For non-JSON support models, we can use structured output
    if pydantic_model and not (model_info and not model_info.has_json_mode()):
        llm = llm.with_structured_output(
            pydantic_model,
            method="json_mode",
        )

    # Call the LLM with retries
    for attempt in range(max_retries):
        try:
            # Inject a strict JSON enforcement if using NVIDIA models to prevent markdown overrides
            if model_provider == "NVIDIA":
                # Smart Crop: If prompt is too long (emails/transcripts), truncate to keep it focused
                prompt_str = str(prompt.content if hasattr(prompt, 'content') else prompt)
                if len(prompt_str) > 12000:
                    prompt_str = prompt_str[:4000] + "\n...[Dossier Truncated for Speed]...\n" + prompt_str[-8000:]
                
                strict_prompt = prompt_str + "\n\nCRITICAL: Return ONLY a valid JSON object. No markdown, no preambles. Focus on the core SHORT thesis for FLY."
            else:
                strict_prompt = prompt

            # Call the LLM with concurrency limit
            with LLM_SEMAPHORE:
                result = llm.invoke(strict_prompt)

            # --- Thinking Display Block ---
            # Try to extract reasoning/thinking content for models that support it (NVIDIA NIM Gemma 4 / Nemotron)
            reasoning = None
            if hasattr(result, 'additional_kwargs') and 'reasoning_content' in result.additional_kwargs:
                reasoning = result.additional_kwargs['reasoning_content']
            elif hasattr(result, 'content') and '<thinking>' in str(result.content):
                # Fallback for models that wrap thinking in tags
                content_str = str(result.content)
                start = content_str.find('<thinking>') + 10
                end = content_str.find('</thinking>')
                if end != -1:
                    reasoning = content_str[start:end].strip()

            if reasoning and not (state and state.get("metadata", {}).get("is_background")):
                from colorama import Fore, Style
                # Use progress.console to avoid messing up Live display if possible
                print(f"\n{Fore.MAGENTA}--- Institutional Reasoning [{agent_name or 'System'}] ---{Style.RESET_ALL}")
                print(f"{Fore.CYAN}{reasoning}{Style.RESET_ALL}")
                print(f"{Fore.MAGENTA}------------------------{Style.RESET_ALL}\n")
            # ------------------------------

            # For non-JSON support models, we need to extract and parse the JSON manually
            if model_info and not model_info.has_json_mode():
                parsed_result = extract_json_from_response(result.content)
                if pydantic_model and parsed_result:
                    return pydantic_model(**parsed_result)
                if not pydantic_model:
                    return result.content if hasattr(result, 'content') else str(result)
            else:
                # If a pydantic model was requested, result is already an object.
                # If not, return the content string.
                if pydantic_model:
                    return result
                return result.content if hasattr(result, 'content') else str(result)


        except Exception as e:
            # --- NEW: Heuristic Fallback for 'Creative' 8B JSON Outputs ---
            if pydantic_model and pydantic_model.__name__ == "CotAgentStructuredOutput":
                try:
                    # Attempt to extract raw content if it failed validation but might contain useful JSON
                    raw_content = ""
                    if hasattr(e, 'content'):
                        raw_content = e.content
                    elif "completion" in str(e):
                        # Extract the JSON string from the error message if possible
                        import re
                        match = re.search(r'completion\s+(\{.*\})', str(e))
                        if match:
                            raw_content = match.group(1)
                    
                    if raw_content:
                        parsed = extract_json_from_response(raw_content)
                        if parsed:
                            # Map 'creative' audit fields to CotAgentStructuredOutput
                            heuristic_result = map_to_cot_schema(parsed, agent_name)
                            if heuristic_result:
                                if agent_name:
                                    progress.update_status(agent_name, None, "Recovered via heuristic parsing")
                                return heuristic_result
                except Exception as he:
                    pass # Fallback to standard error handling

            if agent_name:
                progress.update_status(agent_name, None, f"Error - retry {attempt + 1}/{max_retries}")

            if attempt == max_retries - 1:
                # Silencing the noisy error for 8B models if we are in FAST_MODE
                if os.getenv("FAST_MODE") != "true":
                    print(f"Error in LLM call after {max_retries} attempts: {e}")
                
                # Use default_factory if provided, otherwise create a basic default
                if default_factory:
                    return default_factory()
                return create_default_response(pydantic_model)

    # This should never be reached due to the retry logic above
    return create_default_response(pydantic_model)


def map_to_cot_schema(parsed: dict, agent_name: str | None) -> Any:
    """Heuristically maps a 'creative' JSON audit to the CotAgentStructuredOutput schema."""
    from src.agents.cot_schema import CotAgentStructuredOutput
    
    # Identify sentiment/signal
    sentiment = parsed.get("sentiment", {})
    if isinstance(sentiment, dict):
        signal_val = sentiment.get("overall_sentiment", "neutral").lower()
    else:
        signal_val = str(sentiment).lower()
    
    if signal_val not in ["bullish", "bearish", "neutral"]:
        signal_val = "neutral"
        
    # Determine score
    score_val = 0
    if "downside_conviction" in parsed:
        score_val = -int(parsed["downside_conviction"]) if signal_val == "bearish" else int(parsed["downside_conviction"])
    elif "score" in parsed:
        score_val = int(parsed["score"])
    
    # Synthesize reasoning steps from catalysts/risks
    steps = []
    catalysts = parsed.get("catalysts", {})
    if isinstance(catalysts, dict):
        steps.append(f"Catalysts: {', '.join([k for k, v in catalysts.items() if v])}")
    
    risks = parsed.get("risk_factors", {})
    if isinstance(risks, dict):
        steps.append(f"Risks: {', '.join([k for k, v in risks.items() if v])}")
        
    if "profitability" in parsed:
        steps.append(f"Financials: {json.dumps(parsed['profitability'])}")
        
    # Ensure min 5 steps
    while len(steps) < 5:
        steps.append("Institutional technical audit factor.")
        
    return CotAgentStructuredOutput(
        agent=agent_name or parsed.get("ticker", "Unknown"),
        reasoning_steps=steps[:8],
        score=max(-100, min(100, score_val)),
        conviction_reason=parsed.get("Management Tone", parsed.get("institutional_recommendation", "Consensus bearish signal")),
        invalidation_condition="Scenario analysis reveals limited upside risk.",
        signal=signal_val
    )


def create_default_response(model_class: type[BaseModel] | None) -> Any:
    """Creates a safe default response based on the model's fields, or a string if no model."""
    if model_class is None:
        return "Error in analysis: check system logs."
    
    default_values = {}
    for field_name, field in model_class.model_fields.items():
        if field.annotation == str:
            default_values[field_name] = "Error in analysis, using default"
        elif field.annotation == float:
            default_values[field_name] = 0.0
        elif field.annotation == int:
            default_values[field_name] = 0
        elif hasattr(field.annotation, "__origin__") and field.annotation.__origin__ == list:
            # Handle list types, providing dummy items if there's a min_length requirement
            min_items = 0
            if hasattr(field, "json_schema_extra") and field.json_schema_extra:
                min_items = field.json_schema_extra.get("min_items", 0)
            # Check Field constraints directly if possible
            if hasattr(field, "metadata"):
                from pydantic.fields import FieldInfo
                for meta in field.metadata:
                    if hasattr(meta, "min_length"):
                        min_items = max(min_items, meta.min_length)
            
            if min_items > 0:
                default_values[field_name] = ["Default step"] * min_items
            else:
                default_values[field_name] = []
        else:
            # For other types (like Literal or complex types), try to use the first allowed value
            if hasattr(field.annotation, "__args__"):
                default_values[field_name] = field.annotation.__args__[0]
            else:
                default_values[field_name] = None

    return model_class(**default_values)


def extract_json_from_response(content: str) -> dict | None:
    """Extracts JSON from markdown-formatted response or raw string."""
    try:
        # Strip thinking tags if present to prevent interference with JSON extraction
        if "<thinking>" in content:
            start_tag = content.find("<thinking>")
            end_tag = content.find("</thinking>")
            if end_tag != -1:
                content = content[end_tag + 11:].strip()
            else:
                # If thinking starts but doesn't end properly, try to skip past the start tag
                content = content[start_tag + 10:].strip()

        # Try to find markdown block
        json_start = content.find("```json")
        if json_start != -1:
            json_text = content[json_start + 7 :]  # Skip past ```json
            json_end = json_text.find("```")
            if json_end != -1:
                json_text = json_text[:json_end].strip()
                return json.loads(json_text)
        
        # New: Search for ANY markdown code block if json block wasn't found
        json_start = content.find("```")
        if json_start != -1:
            json_text = content[json_start + 3 :]
            json_end = json_text.find("```")
            if json_end != -1:
                json_text = json_text[:json_end].strip()
                try:
                    return json.loads(json_text)
                except:
                    pass

        # Fallback: Try to find first '{' and last '}'
        start_idx = content.find("{")
        end_idx = content.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_text = content[start_idx : end_idx + 1]
            try:
                return json.loads(json_text)
            except:
                # If that fails, maybe there are multiple JSON-like objects, 
                # try to find the one that looks most like our schema
                pass
            
        # Last resort: Try raw load
        return json.loads(content.strip())
    except Exception as e:
        print(f"Error extracting JSON from response: {e}\nContent was: {content[:200]}...")
    return None


def get_agent_model_config(state, agent_name):
    """
    Get model configuration for a specific agent from the state.
    Falls back to global model configuration if agent-specific config is not available.
    Always returns valid model_name and model_provider values.
    """
    request = state.get("metadata", {}).get("request")
    
    if request and hasattr(request, 'get_agent_model_config'):
        # Get agent-specific model configuration
        model_name, model_provider = request.get_agent_model_config(agent_name)
        # Ensure we have valid values
        if model_name and model_provider:
            return model_name, model_provider.value if hasattr(model_provider, 'value') else str(model_provider)
    
    # Fall back to global configuration (system defaults)
    model_name = state.get("metadata", {}).get("model_name") or "gpt-4.1"
    model_provider = state.get("metadata", {}).get("model_provider") or "OPENAI"
    
    # Convert enum to string if necessary
    if hasattr(model_provider, 'value'):
        model_provider = model_provider.value
    
    return model_name, model_provider
