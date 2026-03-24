import re
import json
from src.utils.logger import get_logger

log = get_logger("utils.parser")

def extract_json(text: str) -> dict:
    """
    Surgically extracts JSON from a string that might contain markdown 
    backticks, thinking blocks, or conversational preamble.
    """
    if not text:
        return {}
        
    # 1. Strip markdown backticks if present
    text = text.replace("```json", "").replace("```", "").strip()
    
    # 2. Use regex to find the first '{' and last '}'
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            log.error("json_parse_failed_after_extraction", error=str(e), snippet=json_str[:100])
            # Last ditch effort: try to clean common trailing commas or newlines
            try:
                # Remove trailing commas before closing braces
                cleaned = re.sub(r',\s*([\]}])', r'\1', json_str)
                return json.loads(cleaned)
            except:
                return {}
    
    log.warning("no_json_found_in_text", snippet=text[:100])
    return {}
