import json
from pathlib import Path
from typing import Optional, Union, Dict, Any
from pydantic import BaseModel, Field
import pandas as pd
from google import genai
from src.graph.state import DealState
from src.utils.logger import get_logger
from src.database.db import get_connection
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
    """
    ext = file_path.suffix.lower()
    
    if ext == '.csv':
        df = pd.read_csv(file_path)
        return f"File: {file_path.name}\n\n{df.to_markdown()}"
        
    elif ext == '.xlsx':
        df = pd.read_excel(file_path)
        return f"File: {file_path.name}\n\n{df.to_markdown()}"
        
    elif ext in ['.pdf', '.jpg', '.jpeg', '.png']:
        log.info("uploading_to_gemini_file_api", file=file_path.name)
        # Using the new google-genai SDK
        client = genai.Client()
        uploaded_file = client.files.upload(file=str(file_path))
        return uploaded_file
        
    else:
        raise ValueError(f"Unsupported financial document type: {ext}")

# ── Nodes ─────────────────────────────────────────────────────────────────────

def cfo_extract_node(state: DealState) -> dict:
    """
    Phase 1: Extracts raw financial data from documents.
    """
    log.info("executing_cfo_extract", deal_id=state.get("deal_id"))
    return {"financials": {"extracted": True}}

def cfo_calculate_node(state: DealState) -> dict:
    """
    Phase 3: Performs definitive calculations (DSCR, Cap Rate) on verified data.
    """
    log.info("executing_cfo_calculate", deal_id=state.get("deal_id"))
    return {"financials": {"calculated": True, "dscr": 1.2}}
