"""
auditor_scraper.py — Clark County Auditor 'Landmark Web' Forensic Miner

Uses Playwright to navigate the session-protected Auditor portal.
Mines recorded document history (Deeds, Mortgages, Liens) for active deals.
"""

import asyncio
from playwright.async_api import async_playwright
from src.utils.logger import get_logger
from src.utils.parser import extract_json
import config

log = get_logger("integration.auditor_scraper")

# Reuse the persistent browser session to maintain speed
USER_DATA_DIR = config.DATA_DIR / "browser_session"

async def mine_recorded_docs(prop_id: str) -> dict:
    """
    Searches the Clark County Auditor system by Parcel ID.
    Returns a list of high-value recorded documents.
    """
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    log.info("starting_auditor_mining", prop_id=prop_id)
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=True,
            slow_mo=1000 # Be very respectful to the Auditor's server
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # 1. Navigate to Parcel Search
        url = "https://recording.clark.wa.gov/landmarkweb/search/index?searchType=parcelid"
        
        try:
            await page.goto(url, wait_until="networkidle")
            
            # 2. Fill the Parcel ID
            # Clark County pan is often 9 digits. We pad if needed.
            search_val = prop_id.zfill(9)
            await page.fill("input#ParcelId", search_val)
            await page.click("button#submit-search")
            
            # 3. Wait for Results Table
            # Landmark Web usually renders a grid with ID 'resultsTable'
            await page.wait_for_selector(".results-row, #resultsTable", timeout=15000)
            
            # 4. Extract Document Metadata
            documents = []
            rows = await page.query_selector_all(".results-row")
            
            for row in rows[:10]: # Mine the 10 most recent records
                cols = await row.query_selector_all("td")
                if len(cols) >= 5:
                    doc_type = await cols[3].inner_text()
                    rec_date = await cols[1].inner_text()
                    doc_num = await cols[2].inner_text()
                    grantor = await cols[4].inner_text()
                    
                    documents.append({
                        "type": doc_type.strip(),
                        "date": rec_date.strip(),
                        "number": doc_num.strip(),
                        "grantor": grantor.strip()
                    })
            
            log.info("auditor_mining_success", prop_id=prop_id, count=len(documents))
            await context.close()
            return {
                "status": "SUCCESS",
                "prop_id": prop_id,
                "document_history": documents
            }

        except Exception as e:
            log.error("auditor_mining_failed", prop_id=prop_id, error=str(e))
            await context.close()
            return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    # Quick Test for 716 E McLoughlin (41550000)
    res = asyncio.run(mine_recorded_docs("41550000"))
    print(json.dumps(res, indent=2))
