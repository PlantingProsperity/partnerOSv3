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
import json

log = get_logger("integration.auditor_scraper")

# Reuse the persistent browser session to maintain speed and bypass CAPTCHA
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
        
        # 1. Start at Home to ensure session
        url = "https://e-docs.clark.wa.gov/LandmarkWeb"
        
        try:
            await page.goto(url, wait_until="networkidle")
            
            # Handle disclaimer
            accept = page.get_by_text("Accept", exact=False).first
            if await accept.is_visible():
                await accept.click()
                await page.wait_for_load_state("networkidle")
            
            # 2. Click through to Parcel ID search
            await page.get_by_text("Official Records Search", exact=False).first.click()
            await page.wait_for_load_state("networkidle")
            
            await page.get_by_text("parcel id", exact=False).first.click()
            await page.wait_for_load_state("networkidle")
            
            # 3. Human Mimicry: Tab to the first input and fill
            # This bypasses visibility and role issues in complex Landmark DOMs
            search_val = prop_id.zfill(9)
            await page.keyboard.press("Tab")
            await page.keyboard.type(search_val, delay=100)
            await page.keyboard.press("Enter")
            
            # 4. Wait for Results Table
            # Landmark grids often use '.results-row'
            try:
                await page.wait_for_selector(".results-row", timeout=20000)
            except:
                # If selector fails, check if the table rendered anyway
                rows = await page.query_selector_all("tr")
                if len(rows) < 5:
                    log.error("auditor_no_results_table", prop_id=prop_id)
                    await page.screenshot(path=f"data/logs/auditor_fail_{prop_id}.png")
                    raise Exception("Results table did not render.")
            
            # 5. Extract Document Metadata
            documents = []
            rows = await page.query_selector_all("tr")
            
            for row in rows:
                cols = await row.query_selector_all("td")
                if len(cols) >= 5:
                    # Typical Landmark structure: Date | Number | Type | Grantor | Grantee
                    rec_date = await cols[1].inner_text()
                    doc_num = await cols[2].inner_text()
                    doc_type = await cols[3].inner_text()
                    grantor = await cols[4].inner_text()
                    
                    if doc_type.strip():
                        documents.append({
                            "date": rec_date.strip(),
                            "number": doc_num.strip(),
                            "type": doc_type.strip(),
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
    # Local Test
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "41550000"
    res = asyncio.run(mine_recorded_docs(pid))
    print(json.dumps(res, indent=2))
