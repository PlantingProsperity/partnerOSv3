"""
scout_scraper.py — Playwright-based Property Information Center scraper

This module uses a PERSISTENT BROWSER CONTEXT. 
To bypass the reCAPTCHA, the user must occasionally clear it manually
in a visible browser window using the same context directory.
"""

import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright
from src.utils.logger import get_logger
import config

log = get_logger("integration.scout_scraper")

# Path to store the browser session (cookies, etc.)
USER_DATA_DIR = config.DATA_DIR / "browser_session"

async def scrape_pic_details(prop_id: str) -> dict:
    """
    Scrapes high-value forensics from the Clark County PIC.
    Uses persistent context to leverage 7-day reCAPTCHA cookies.
    """
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    log.info("starting_pic_forensics", prop_id=prop_id)
    
    async with async_playwright() as p:
        # We use launch_persistent_context to save cookies
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=True, # Run headless for automation
            slow_mo=500    # Be gentle to the server
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        # 1. Navigate to Fact Sheet (most dense data)
        url = f"https://gis.clark.wa.gov/gishome/property/index.cfm?fuseaction=factsheet&account={prop_id}"
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            # 2. Check for CAPTCHA
            body_text = await page.inner_text("body")
            if "NOT A ROBOT" in body_text.upper():
                log.warning("recaptcha_blocked_scout", prop_id=prop_id)
                await context.close()
                return {"status": "BLOCKED_BY_CAPTCHA", "message": "7-day key expired. Manual verification required."}
            
            # 3. Extract Data (Fact Sheet Analysis)
            body_text = await page.inner_text("body")
            
            forensics = {
                "status": "COMPLETE",
                "prop_id": prop_id,
                "has_photos": False,
                "document_links": [],
                "delinquency_notes": None,
                "environmental": []
            }
            
            # --- Forensic Layer 1: Recorded Documents (The 'Secret' History) ---
            # Search for 'Recorded Documents' or 'Excise' links
            doc_links = await page.query_selector_all("a[href*='recorded_documents'], a[href*='excise']")
            for link in doc_links[:5]: # Take top 5 recent docs
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and text:
                    forensics["document_links"].append({"type": text.strip(), "url": href})

            # --- Forensic Layer 2: Building Photos ---
            photos = await page.query_selector_all("a[href*='photo'], img[src*='photo']")
            forensics["has_photos"] = len(photos) > 0

            # --- Forensic Layer 3: Tax/Delinquency Detail ---
            if "DELINQUENT" in body_text.upper() or "PRIOR YEARS DUE" in body_text.upper():
                forensics["delinquency_notes"] = "CRITICAL: Found active delinquency text on Fact Sheet."
            
            # --- Forensic Layer 4: Environmental Constraints ---
            if "WETLAND" in body_text.upper(): forensics["environmental"].append("WETLANDS")
            if "FLOOD" in body_text.upper(): forensics["environmental"].append("FLOOD_ZONE")
            
            log.info("pic_scrape_success", prop_id=prop_id, docs=len(forensics["document_links"]), photos=forensics["has_photos"])
            
            await context.close()
            return forensics

        except Exception as e:
            log.error("pic_scrape_failed", prop_id=prop_id, error=str(e))
            await context.close()
            return {"status": "ERROR", "error": str(e)}

if __name__ == "__main__":
    # Test run
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(scrape_pic_details("41550000"))
    print(res)
