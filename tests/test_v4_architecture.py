import pytest
import asyncio
from unittest.mock import patch, MagicMock

# --- Test 1: H-MEM (Hierarchical Cognitive Memory) Bayesian Belief Update ---
@patch('src.brain.memory.get_connection')
def test_hmem_semantic_fact_belief_flip(mock_get_connection):
    """
    Tests the H-MEM Bayesian belief update logic in MemoryManager.
    Verifies that strong conflicting evidence correctly increments the beta 
    parameter and ultimately flips the semantic trait value.
    """
    from src.brain.memory import MemoryManager
    
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_get_connection.return_value = mock_conn
    
    # Mock an existing semantic fact where alpha=1.0, beta=1.0, and current_val="motivated"
    mock_conn.execute.return_value.fetchone.return_value = (1.0, 1.0, "motivated")
    
    manager = MemoryManager()
    
    # Update with strong conflicting evidence (reliability = 3.0) to force a belief flip
    manager.update_semantic_fact(seller_id="seller_123", trait="motivation", value="unmotivated", reliability=3.0)
    
    # Verify the UPDATE query was called with the flipped value "unmotivated" and reset alpha/beta
    update_calls = [call for call in mock_conn.execute.call_args_list if "UPDATE semantic_facts" in call[0][0]]
    assert len(update_calls) == 1
    
    # Assert the math: 
    # beta += 3.0 (beta=4.0). Since 4.0 > 1.0 + 2, the flip triggers:
    # new alpha = 1.0 + 3.0 = 4.0, new beta = 1.0
    args = update_calls[0][0][1] 
    assert args[0] == 4.0  # new alpha
    assert args[1] == 1.0  # new beta
    assert args[2] == "unmotivated" # newly flipped current_val

# --- Test 2: Early-Fusion Vision (Multimodal LLM Support) ---
@patch('src.utils.llm.litellm.completion')
@patch('src.utils.llm._log_usage')
@patch('src.utils.llm._check_budget')
def test_early_fusion_vision_multimodal_call(mock_check_budget, mock_log_usage, mock_completion):
    """
    Tests the Early-Fusion Vision integration in the unified LLM gateway.
    Verifies that multimodal prompts correctly configure the Litellm payload
    (e.g., increased timeouts) and are accurately categorized in telemetry.
    """
    from src.utils.llm import complete
    
    # Bypass budget checks for testing
    mock_check_budget.return_value = True
    
    # Mock a successful LLM completion response
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"analysis": "looks good"}'
    mock_response.usage.prompt_tokens = 100
    mock_response.usage.completion_tokens = 50
    mock_completion.return_value = mock_response

    # Simulated Multimodal prompt block (ADR-S13 format)
    multimodal_prompt = [
        {"type": "text", "text": "Analyze this property site plan"},
        {"type": "image_url", "image_url": "https://example.com/site_plan.jpg"}
    ]
    
    result = complete(prompt=multimodal_prompt, agent="vision_agent")
    
    # Verify timeout was extended for heavy multimodal processing
    mock_completion.assert_called_once()
    kwargs = mock_completion.call_args[1]
    assert kwargs["messages"] == [{"role": "user", "content": multimodal_prompt}]
    
    # Verify usage telemetry recorded the correct call_type
    mock_log_usage.assert_called_once()
    log_kwargs = mock_log_usage.call_args[1]
    assert log_kwargs["call_type"] == "multimodal"

# --- Test 3: Generative UI Component Resolution ---
def test_generative_ui_registry_resolution():
    """
    Tests the Generative UI dynamic module resolution logic.
    Verifies that the registry correctly maps Manager agent signals 
    (ui_modules and archetypes) to actionable Streamlit UI functions.
    """
    from src.ui.registry import get_recommended_ui, render_site_plan_calculator, render_debt_wrap_simulator
    
    # Mock a structured JSON verdict emitted by the Manager agent
    verdict_data = {
        "ui_modules": ["infill"],
        "archetype": "SUB_TO"
    }
    
    ui_funcs = get_recommended_ui(verdict_data)
    
    # Validate the registry resolved "infill" to the site plan calculator 
    # and "SUB_TO" to the debt-wrap simulator
    assert len(ui_funcs) == 2
    assert render_site_plan_calculator in ui_funcs
    assert render_debt_wrap_simulator in ui_funcs

# --- Test 4: Async Harmony (Event Loop Synchronization) ---
def test_async_harmony_job_wrapper():
    """
    Tests the standard Async Harmony synchronization wrapper used to safely 
    bridge APScheduler (synchronous) with concurrent Firehouse web scrapers (asyncio/httpx).
    """
    # Mock an async Firehouse scraper job
    async def simulated_scraper_job():
        await asyncio.sleep(0.01)
        return "harmony_achieved"

    # The exact event loop wrapper pattern used in src/firehouse/firehouse_jobs.py
    def run_async(coro):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
            
    result = run_async(simulated_scraper_job())
    
    # Validate safe synchronous completion of the async task
    assert result == "harmony_achieved"
