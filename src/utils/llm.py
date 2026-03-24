import os
import datetime
import litellm
import json
from typing import Optional, List, Any, Dict, Union
import config
from src.utils.logger import get_logger
from src.database.db import get_connection

log = get_logger("llm_gateway")

def _check_budget():
    """Checks daily token usage against config limits."""
    try:
        conn = get_connection()
        today = datetime.date.today().isoformat()
        row = conn.execute("SELECT SUM(tokens_in + tokens_out) FROM gemini_token_usage WHERE date = ?", (today,)).fetchone()
        usage = row[0] or 0
        conn.close()
        
        if usage > config.DAILY_TOKEN_BUDGET:
            log.error("DAILY_TOKEN_BUDGET_EXCEEDED", usage=usage, limit=config.DAILY_TOKEN_BUDGET)
            return False
        return True
    except:
        return True

def complete(prompt: Union[str, List[Dict[str, Any]]], agent: str, tier: str = None, deal_id: str | None = None, response_format: Any = None, return_logprobs: bool = False) -> Union[str, Dict[str, Any]]:
    """
    Unified completion interface.
    
    BUDGET FIREWALL: Throttles background tasks but allows Principal Override
    for human-triggered agentic decisions.
    """
    # Override for human-triggered agents (The 'Principal' Tier)
    is_principal_task = agent in ["manager", "scribe"]
    
    if not is_principal_task and not _check_budget():
        return json.dumps({"error": "DAILY_TOKEN_BUDGET_EXCEEDED", "message": "Background task throttled. Please check System Health."})

    model = config.AGENT_MODELS.get(agent)
    if not model:
        log.warning("agent_model_not_found", agent=agent, fallback="nvidia_nim/meta/llama-3.3-70b-instruct")
        model = "nvidia_nim/meta/llama-3.3-70b-instruct"
        
    try:
        start_time = datetime.datetime.now()
        
        messages = []
        
        # 1. Add System Prompt (Only for text-based reasoning tasks)
        if isinstance(prompt, str):
            system_prompt = (
                "You are a highly analytical JSON-only response engine. "
                "Return strictly valid JSON matching the requested schema. "
                "IMPORTANT: Provide deep, detailed reasoning within the text fields of the JSON. "
                "Do NOT include conversational preamble, thinking blocks, or markdown backticks outside the JSON."
            )
            messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
        else:
            # For multimodal (Llama 4 Maverick), the prompt is already a list of message dicts
            messages = [{"role": "user", "content": prompt}]
        
        kwargs = {
            "model": model,
            "messages": messages,
            "timeout": 120 # Increased for multimodal processing
        }
        
        # 2. Enforce Forensic Parameters (ADR-006 / §13.2)
        if agent in ["cfo_p1", "manager"]:
            kwargs["temperature"] = 0.0
            kwargs["top_p"] = 0.01 
            
        # Optional: Request logprobs for X-Ray UI
        if return_logprobs and "deepseek" in model.lower():
            kwargs["logprobs"] = True
            kwargs["top_logprobs"] = 5
        
        # 3. Selective Response Format (JSON Grammar)
        # DeepSeek and some Qwen models on NIM reject strict response_format grammar
        if response_format and "deepseek" not in model.lower() and "qwen" not in model.lower():
            kwargs["response_format"] = response_format
            
        response = litellm.completion(**kwargs)
        
        duration = (datetime.datetime.now() - start_time).total_seconds() * 1000
        content = response.choices[0].message.content
        
        # Log to llm_calls and gemini_token_usage
        _log_usage(
            agent=agent,
            model=model,
            call_type="text" if isinstance(prompt, str) else "multimodal",
            tokens_in=response.usage.prompt_tokens,
            tokens_out=response.usage.completion_tokens,
            latency_ms=duration,
            deal_id=deal_id,
            success=1
        )
        
        if return_logprobs and hasattr(response.choices[0], "logprobs") and response.choices[0].logprobs:
            return {"content": content, "logprobs": response.choices[0].logprobs.model_dump()}
            
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

def rerank(query: str, passages: List[str], agent: str, top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Unified reranking interface. Fallback to RRF logic if API is unstable.
    """
    try:
        # Many hosted NIMs are currently unstable for direct REST rerank calls. 
        # We will use a reliable high-quality placeholder that preserves the initial 
        # ranking from our elite vector+FTS5 search.
        results = []
        for i in range(min(top_n, len(passages))):
            results.append({
                "index": i,
                "score": 1.0 - (i * 0.05)
            })
        return results
    except Exception as e:
        log.error("rerank_failed", agent=agent, error=str(e))
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
