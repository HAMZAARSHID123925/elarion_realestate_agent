import re
import json
import ast
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("elarion.utils.helper")


def robust_json_parse(raw_text: str, expected_keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Indestructible multi-stage JSON parser for LLM responses.
    
    Recovers from:
    - Thinking tags (<think>...</think>) from reasoning models (Qwen, DeepSeek)
    - Markdown code fences (```json ... ```)
    - Python dict syntax (single quotes, True/False/None)
    - Javascript object syntax (unquoted keys: { key: value })
    - Malformed JSON via targeted regex key-value extraction
    """
    if not raw_text:
        return {}

    raw_str = str(raw_text)

    # Stage 1: Strip thinking blocks and markdown code blocks
    cleaned = re.sub(r"<think>.*?</think>", "", raw_str, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = re.sub(r"```[a-zA-Z]*", "", cleaned).strip()

    # Stage 2: Extract JSON substring between the first { and last }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    json_str = cleaned[start:end + 1] if (start != -1 and end != -1) else cleaned

    # Attempt 1: Standard RFC 8259 JSON parsing
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Attempt 2: AST literal eval (handles Python dicts with single quotes & None/True/False)
    try:
        data = ast.literal_eval(json_str)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Attempt 3: Regex syntax repair (unquoted keys, single quotes, Python None/True/False)
    try:
        fixed = json_str
        # Replace single-quoted strings with double-quoted strings
        fixed = re.sub(r"'([^'\\]*(?:\\.[^'\\]*)*)'", r'"\1"', fixed)
        # Quote unquoted property keys: e.g. { tenant_identity: -> { "tenant_identity":
        fixed = re.sub(r'([{\s,])([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed)
        # Replace Python keywords with JSON keywords
        fixed = re.sub(r'\bNone\b', 'null', fixed)
        fixed = re.sub(r'\bTrue\b', 'true', fixed)
        fixed = re.sub(r'\bFalse\b', 'false', fixed)
        data = json.loads(fixed)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    # Attempt 4: Targeted Regex Key-Value Extraction for expected fields
    data = {}
    keys_to_search = expected_keys or [
        "tenant_identity", "property_unit", "issue_category",
        "issue_description", "urgency", "permission_to_enter", "pets_present",
        "intent", "entities"
    ]
    for key in keys_to_search:
        # Matches "key": "value" or 'key': 'value' or key: value
        match = re.search(
            rf'["\']?{re.escape(key)}["\']?\s*:\s*["\']?([^,"\n\}}\]]+)["\']?',
            json_str,
            re.IGNORECASE
        )
        if match:
            val = match.group(1).strip().strip('"').strip("'")
            if val.lower() not in ["null", "none", "n/a", "undefined", ""]:
                data[key] = val

    if data:
        logger.info(f"robust_json_parse: Successfully recovered {len(data)} fields via regex extraction.")
        return data

    logger.warning(f"robust_json_parse: Could not parse any valid JSON or key-value pairs from text: {raw_str[:150]}")
    return {}
