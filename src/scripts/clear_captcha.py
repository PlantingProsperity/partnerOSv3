import asyncio
from playwright.async_api import async_playwright
from pathlib import Path
import os

# Root of the project
BASE_DIR = Path(__file__).parent.parent.parent.resolve()
USER_DATA_DIR = BASE_DIR / "data" / "browser_session"

async def run():
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch NON-HEADLESS so Roman can see and click
        print(f"Opening browser with profile: {USER_DATA_DIR}")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=False,
            args=['--start-maximized']
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Open the Fact Sheet for a known property to trigger the check
        url = "https://gis.clark.wa.gov/gishome/property/index.cfm?fuseaction=factsheet&account=41550000"
        print(f"Navigating to {url}")
        print("\n--- ACTION REQUIRED ---")
        print("Please solve the reCAPTCHA in the browser window.")
        print("Once you see the 'Property Fact Sheet', the system is unlocked for 7 days.")
        print("You can then close the browser window.\n")
        
        await page.goto(url)
        
        # Keep open until manual close or long timeout
        try:
            # We wait for the window to be closed manually or 10 mins
            await page.wait_for_timeout(600000) 
        except:
            pass
        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
