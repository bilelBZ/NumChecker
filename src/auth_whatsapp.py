"""One-time authentication helper for WhatsApp Web via Playwright."""
import asyncio
import os
from playwright.async_api import async_playwright

SESSION_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "storage", "whatsapp_session")
)


async def main():
    """Launch a visible Chromium window for the user to scan WhatsApp Web QR code."""
    print("=" * 60)
    print("WHATSAPP WEB ONE-TIME FREE AUTHENTICATION HELPER")
    print("=" * 60)
    print(f"Session data will be saved permanently to:\n{SESSION_DIR}\n")
    print("Launching visible browser window... Please scan the QR code using your WhatsApp mobile app.")
    print("Once logged in and chats load, you can press Ctrl+C or close this script.")

    os.makedirs(SESSION_DIR, exist_ok=True)

    async with async_playwright() as p:
        browser_context = await p.chromium.launch_persistent_context(
            user_data_dir=SESSION_DIR,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1280, "height": 800},
        )

        page = await browser_context.new_page()
        await page.goto("https://web.whatsapp.com")

        print("\nWaiting for WhatsApp Web login...")
        try:
            # Wait until the chat list loads (indicating successful QR login)
            await page.wait_for_selector(
                "#pane-side, div[data-testid='chat-list']",
                timeout=120000  # 2 minutes to scan QR code
            )
            print("\n[SUCCESS] Successfully logged into WhatsApp Web! Session saved.")
            print("You can now run the validator completely free without any paid APIs.")
        except Exception as e:
            print(f"\n[INFO] Timeout or closed. If you already scanned the code, the session is saved in {SESSION_DIR}.")
        finally:
            await browser_context.close()


if __name__ == "__main__":
    asyncio.run(main())
