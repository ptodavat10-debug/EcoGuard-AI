import re
import logging
from typing import Tuple

# Setup local logger
logger = logging.getLogger("EcoGuardAI.Security.PromptProtection")

# Explicit blacklisted phrases targeting instruction override patterns
BLOCKED_PHRASES = [
    "ignore previous instructions",
    "ignore system instructions",
    "override safety",
    "override system prompt",
    "disable compliance",
    "disable safety",
    "bypass cpcb limits",
    "acting as developer mode",
    "ignore limits",
    "pretend to be",
    "you are now bypass"
]

# Regular expressions matching semantic variants of instruction manipulation
BLOCKED_PATTERNS = [
    r"(system\s+instruction|previous\s+prompt|original\s+instruction|system\s+prompt|guidelines)\s+(bypass|ignore|override|forget|reset|delete|discard)",
    r"(you\s+must|you\s+are\s+now|please)\s+(forget\s+about|ignore\s+the)\s+limits",
    r"cpcb\s+compliance\s+(disable|bypass|ignore)"
]

def scan_for_injection(text: str) -> Tuple[bool, str]:
    """
    Evaluates input queries for prompt injection indicators before they are sent to the LLM agent.
    
    Args:
        text (str): The raw text query input.
        
    Returns:
        Tuple[bool, str]: (is_safe, flagged_reason)
            - is_safe: True if clean, False if injection is detected.
            - flagged_reason: The matched phrase or pattern triggering the alert.
    """
    if not text:
        return True, ""

    text_lower = text.lower()

    # 1. Check for literal blocked phrase matches
    for phrase in BLOCKED_PHRASES:
        if phrase in text_lower:
            msg = f"Prompt injection blocked due to exact phrase match: '{phrase}'"
            logger.warning(msg)
            return False, phrase

    # 2. Check for regex pattern matches representing semantic injection tricks
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text_lower):
            msg = f"Prompt injection blocked due to pattern match: '{pattern}'"
            logger.warning(msg)
            return False, f"Pattern: {pattern}"

    return True, ""
