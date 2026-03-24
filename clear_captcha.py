import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

async def run():
    user_data_dir = Path("data/browser_session")
    user_data_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch NON-HEADLESS so you can see and click
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=['--start-maximized']
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        url = "https://gis.clark.wa.gov/gishome/property/index.cfm?fuseaction=factsheet&account=41550000"
        print(f"\nOpening {url}")
        print("ACTION REQUIRED: Please click the reCAPTCHA box in the browser window.")
        print("Once you see the Fact Sheet, you can close the browser or press Ctrl+C here.\n")
        
        await page.goto(url)
        
        # Keep open until manual close or timeout
        try:
            await asyncio.sleep(300) # Open for 5 minutes
        except:
            pass
        await context.close()

if __name__ == "__main__":
    asyncio.run(run())
