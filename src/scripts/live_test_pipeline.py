import os
from pathlib import Path
from src.graph.nodes.librarian import Librarian, librarian_node
from src.graph.nodes.cfo import cfo_extract_node
from src.graph.state import DealState
from src.utils.logger import get_logger
import config

log = get_logger("live_test")

def run_live_test():
    log.info("starting_live_pipeline_test")
    
    # 1. Target the real file
    target_file = config.INBOX_DIR / "lists" / "Propwire Export - 34 Properties - Nov 6, 2025.csv"
    
    if not target_file.exists():
        log.error("test_file_not_found", path=str(target_file))
        return

    # 2. Setup Initial State (Simulating a new deal trigger)
    state = DealState(
        deal_id="live_test_deal_001",
        address="716 E MCLOUGHLIN BLVD", # First address in your CSV
        parcel_number="041550-000",
        status="INTAKE",
        cfo_verified=False,
        heuristic_flagged=False,
        heuristic_failures=[],
        financials={},
        financial_doc_paths=[str(target_file)], # Handing the file to the pipeline
        property_data={},
        seller_archetype="",
        profiler_confidence=0,
        profiler_cites=[],
        verdict="",
        reasoning_text="",
        manager_confidence=0,
        scribe_instructions="",
        loi_draft=""
    )

    log.info("running_librarian_node_live")
    # We call the node directly to see the LLM output
    lib_result = librarian_node(state)
    log.info("librarian_node_output", result=lib_result)
    
    # Update state with librarian output
    state.update(lib_result)
    
    log.info("running_cfo_extract_node_live")
    # This will use Llama 3.3 70B to try and extract from the CSV text
    cfo_result = cfo_extract_node(state)
    log.info("cfo_node_output", result=cfo_result)

if __name__ == "__main__":
    run_live_test()
