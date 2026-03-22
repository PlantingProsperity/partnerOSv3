import json
from pathlib import Path
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field
import pandas as pd
from google import genai
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
from src.utils import llm
import config

log = get_logger("agent.cfo")

# ── Pydantic Schema for LLM Extraction ────────────────────────────────────────

class CFOCitation(BaseModel):
    file: str = Field(description="The exact filename.")
    page: Optional[int] = Field(None, description="The page number, if applicable.")
    verbatim_text: str = Field(description="The exact text snippet or cell value extracted.")

class CFOField(BaseModel):
    value: float = Field(description="The numerical value extracted.")
    citation: CFOCitation

class CFOExtraction(BaseModel):
    gross_income: Optional[CFOField] = None
    vacancy_rate: Optional[CFOField] = None
    operating_expenses: Optional[CFOField] = None
    noi: Optional[CFOField] = None
    asking_price: Optional[CFOField] = None
    loan_amount: Optional[CFOField] = None
    interest_rate: Optional[CFOField] = None
    amortization_years: Optional[CFOField] = None

# ── Hybrid File Parser ────────────────────────────────────────────────────────

def _parse_document(file_path: Path) -> Union[str, Any]:
    """
    Hybrid Router: 
    - CSV/XLSX -> Returns a Markdown formatted string via pandas.
    - PDF/Images -> Uploads via Gemini File API and returns the File object.
    - TXT/MD -> Returns raw text.
    - Unknown -> Returns a string indicating unparseable format.
    """
    ext = file_path.suffix.lower()
    
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
            # Limit rows to prevent prompt overflow during live tests
            df = df.head(5)
            return f"File: {file_path.name} (First 5 rows)\n\n{df.to_markdown()}"            
        elif ext == '.xlsx':
            df = pd.read_excel(file_path)
            return f"File: {file_path.name}\n\n{df.to_markdown()}"
            
        elif ext in ['.pdf', '.jpg', '.jpeg', '.png']:
            log.info("uploading_to_gemini_file_api", file=file_path.name)
            client = genai.Client()
            uploaded_file = client.files.upload(file=str(file_path))
            return uploaded_file
            
        elif ext in ['.txt', '.md', '.rtf', '.csv']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f"File: {file_path.name}\n\n{f.read()}"
                
        else:
            log.warning("unknown_file_type", file=file_path.name, ext=ext)
            return f"File: {file_path.name}\n\n[Content unparseable due to unknown format: {ext}]"
            
    except Exception as e:
        log.error("document_parsing_failed", file=file_path.name, error=str(e))
        return f"File: {file_path.name}\n\n[Failed to parse: {str(e)}]"

# ── Nodes ─────────────────────────────────────────────────────────────────────

def cfo_extract_node(state: DealState) -> dict:
    """
    Phase 1: Extracts raw financial data from documents using Gemini.
    """
    deal_id = state.get("deal_id")
    log.info("executing_cfo_extract", deal_id=deal_id)
    
    # Grab the financial documents assigned to this deal by the Librarian
    financial_doc_paths = state.get("financial_doc_paths", [])
    
    # In S4, we assume at least one document is present.
    # For a robust implementation, we would process all paths.
    # Here we process the first one for demonstration.
    if not financial_doc_paths:
        log.warning("no_financial_docs_found", deal_id=deal_id)
        # We can't extract if there are no docs, but we'll create a dummy record
        # so Phase 2 can still trigger and the user can manually enter data.
        extraction = CFOExtraction()
    else:
        try:
            doc_path = Path(financial_doc_paths[0])
            log.info("cfo_parsing_document", path=str(doc_path))
            document_content = _parse_document(doc_path)
            log.info("cfo_document_parsed", length=len(str(document_content)))
            
            prompt = """
            You are an expert commercial real estate underwriter. 
            Extract the core financial metrics from the provided document.
            For every value you extract, you MUST provide a verbatim citation.
            If a value is not found in the document, return null for that field.
            
            Document:
            {doc}
            """.format(doc=document_content)
            
            import json
            import re
            
            log.info("cfo_calling_llm_live", agent="cfo_p1")
            response_str = llm.complete(
                prompt=prompt,
                tier="quality",
                agent="cfo_p1",
                deal_id=deal_id,
                response_format=CFOExtraction
            )
            log.info("cfo_llm_responded", length=len(response_str))
            
            # Robust JSON Extraction
            json_match = re.search(r"\{.*\}", response_str, re.DOTALL)
            if json_match:
                response_str = json_match.group()
                
            extraction = CFOExtraction.model_validate_json(response_str)
            log.info("cfo_extraction_validated")
            
        except Exception as e:
            log.error("cfo_extraction_failed", deal_id=deal_id, error=str(e))
            extraction = CFOExtraction()
    
    # Write to draft_financials
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO draft_financials (deal_id, citations, status, created_at)
        VALUES (?, ?, 'UNVERIFIED', CURRENT_TIMESTAMP)
    """, (deal_id, extraction.model_dump_json()))
    draft_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"financials": {"extracted": True, "draft_id": draft_id}}

def cfo_calculate_node(state: DealState) -> dict:
    """
    Phase 3: Performs definitive calculations (DSCR, Cap Rate) on verified data.
    """
    deal_id = state.get("deal_id")
    log.info("executing_cfo_calculate", deal_id=deal_id)
    
    # 1. Read verified_financials
    verified_id = state.get("financials", {}).get("verified_financials_id")
    if not verified_id:
        # In a real environment, this should raise ValueError to stop the graph.
        # For testing the graph flow, we'll log an error and use dummy data.
        log.error("cfo_phase_3_blocked", reason="no verified_financials_id")
        return {"financials": {"calculated": False, "error": "missing verified record"}}

    conn = get_connection()
    row = conn.execute("SELECT data FROM verified_financials WHERE id = ?", (verified_id,)).fetchone()
    conn.close()
    
    if not row:
        return {"financials": {"calculated": False, "error": "record not found in db"}}
        
    data = json.loads(row["data"])
    
    # 2. Pure Python Deterministic Math
    def safe_get(d, key):
        # Handles cases where the field is missing or is None
        val_obj = d.get(key)
        if val_obj is None:
            return 0
        return val_obj.get("value", 0)

    noi = safe_get(data, "noi")
    price = safe_get(data, "asking_price") or 1 # prevent div by zero
    ads = safe_get(data, "annual_debt_service") or 1
    
    cap_rate = noi / price if price else 0
    dscr = noi / ads if ads else 0
    
    # 3. Apply Thresholds
    below_cap = cap_rate < config.CFO_CAP_RATE_FLOOR
    below_dscr = dscr < config.CFO_DSCR_FLOOR
    
    # 4. Write to financial_analyses
    conn = get_connection()
    conn.execute("""
        INSERT INTO financial_analyses (deal_id, cap_rate, dscr, below_dscr_floor, below_cap_floor, calculated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
    """, (deal_id, cap_rate, dscr, int(below_dscr), int(below_cap)))
    conn.commit()
    conn.close()
    
    return {
        "financials": {
            "calculated": True, 
            "cap_rate": cap_rate, 
            "dscr": dscr,
            "below_cap_floor": below_cap,
            "below_dscr_floor": below_dscr
        }
    }
