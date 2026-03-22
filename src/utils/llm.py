import os
import datetime
import litellm
from typing import Optional, List, Any
import config
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("llm_gateway")

def complete(prompt: str, tier: str, agent: str, deal_id: str | None = None, response_format: Any = None) -> str:
    """
    Unified completion interface. Routes to FAST or QUALITY model
    and logs token usage to SQLite.
    """
    model = config.FAST_MODEL if tier == "fast" else config.QUALITY_MODEL
    
    try:
        start_time = datetime.datetime.now()
        
        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        if response_format:
            # Tell LiteLLM to enforce the Pydantic schema
            kwargs["response_format"] = response_format
            
        response = litellm.completion(**kwargs)
        
        duration = (datetime.datetime.now() - start_time).total_seconds() * 1000
        content = response.choices[0].message.content
        
        # Log to llm_calls and gemini_token_usage
        _log_usage(
            agent=agent,
            model=model,
            call_type="text",
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            latency_ms=duration,
            deal_id=deal_id,
            success=1
        )
        
        return content
        
    except Exception as e:
        log.error("llm_call_failed", agent=agent, model=model, error=str(e))
        _log_usage(agent=agent, model=model, call_type="text", success=0, error=str(e), deal_id=deal_id)
        raise

def embed(text: str, agent: str, input_type: str = "passage") -> List[float]:
    """
    Unified embedding interface. Always uses config.EMBEDDING_MODEL.
    """
    try:
        kwargs = {
            "model": config.EMBEDDING_MODEL,
            "input": [text],
        }
        
        # NVIDIA NIM models require input_type and encoding_format
        if "nvidia" in config.EMBEDDING_MODEL:
            kwargs["input_type"] = input_type
            kwargs["encoding_format"] = "float"
        else:
            # For Gemini, we might need the API key explicitly if not picked up by LiteLLM
            kwargs["api_key"] = os.environ.get("GEMINI_API_KEY")
            
        response = litellm.embedding(**kwargs)
        
        vector = response.data[0]['embedding']
        
        _log_usage(
            agent=agent,
            model=config.EMBEDDING_MODEL,
            call_type="embedding",
            tokens_in=response.usage.prompt_tokens,
            tokens_out=0,
            success=1
        )
        
        return vector
        
    except Exception as e:
        log.error("embedding_failed", agent=agent, error=str(e))
        raise

def _log_usage(agent: str, model: str, call_type: str, 
               tokens_in: int = 0, tokens_out: int = 0, 
               latency_ms: float = 0, success: int = 1, 
               error: str | None = None, deal_id: str | None = None):
    """
    Internal helper to log usage to SQLite tables.
    """
    ts = datetime.datetime.now(datetime.UTC).isoformat()
    date = datetime.date.today().isoformat()
    
    conn = get_connection()
    try:
        # Log to llm_calls
        conn.execute("""
            INSERT INTO llm_calls (ts, deal_id, agent, model, prompt_len, response_len, tokens_in, tokens_out, latency_ms, success, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, deal_id, agent, model, 0, 0, tokens_in, tokens_out, latency_ms, success, error))
        
        # Log to gemini_token_usage
        conn.execute("""
            INSERT INTO gemini_token_usage (ts, date, agent, model, call_type, tokens_in, tokens_out, deal_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ts, date, agent, model, call_type, tokens_in, tokens_out, deal_id))
        
        conn.commit()
    except Exception as e:
        log.error("logging_failed", error=str(e))
    finally:
        conn.close()
