import asyncio
from playwright.async_api import async_playwright

DASHBOARD_URL="https://b2b-dashboard-hydt.streamlit.app"


async def main():
    print(f"Visiting {DASHBOARD_URL} with headless browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            response = await page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=60000)
            print(f"Page loaded")
            await page.wait_for_timeout(7000)
            
            wake_selectors = [
                "button:has-text('Yes, get this app back up!')",
                "button:has-text('wake it back up')",
                "button:has-text('Wake up')"
            ]
            
            clicked = False
            for selector in wake_selectors:
                btn = page.locator(selector)
                if await btn.count() > 0 and await btn.first.is_visible():
                    print(f'Detected sleep mode. Clicking wake-up button: {selector}')
                    await btn.first.click()
                    clicked = True
                    await page.wait_for_timeout(10000)
                    print('Wake-up button clicked!')
                    break
                    
            if not clicked:
                print('Dashboard is already active and running.')
                
            await page.wait_for_timeout(5000)
            print('Streamlit session initialized successfully.')
        except Exception as e:
            print(f'Encountered issue: {e}')
        finally:
            await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
