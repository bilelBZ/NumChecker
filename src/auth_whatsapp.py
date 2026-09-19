"""One-time authentication helper for WhatsApp Web via Playwright."""
import asyncio
import logging
import os
import shutil
import sys
from typing import Callable, Optional
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


def get_whatsapp_session_dir() -> str:
    """Get absolute path to persistent WhatsApp session storage."""
    if getattr(sys, "frozen", False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return os.path.join(base_dir, "storage", "whatsapp_session")


def is_whatsapp_linked() -> bool:
    """Check if WhatsApp Web session appears to be established."""
    s_dir = get_whatsapp_session_dir()
    if not os.path.exists(s_dir):
        return False
    # Check for Chrome/Chromium user profile markers
    default_dir = os.path.join(s_dir, "Default")
    return os.path.exists(default_dir) and len(os.listdir(default_dir)) > 3


def unlink_whatsapp_session() -> bool:
    """Remove stored WhatsApp session files."""
    s_dir = get_whatsapp_session_dir()
    if os.path.exists(s_dir):
        try:
            shutil.rmtree(s_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to delete WhatsApp session directory: {e}")
            return False
    return True


async def authenticate_whatsapp_interactive(status_callback: Optional[Callable[[str], None]] = None) -> bool:
    """Launch a visible browser window for the user to scan WhatsApp Web QR code."""
    session_dir = get_whatsapp_session_dir()
    os.makedirs(session_dir, exist_ok=True)

    if status_callback:
        status_callback("Launching WhatsApp Web browser...")

    async with async_playwright() as p:
        browser_channel = None
        # On Windows, try system Chrome, then Edge
        if sys.platform == "win32":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            edge_paths = [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            ]
            if any(os.path.exists(p) for p in chrome_paths):
                browser_channel = "chrome"
            elif any(os.path.exists(p) for p in edge_paths):
                browser_channel = "msedge"

        launch_kwargs = {
            "user_data_dir": session_dir,
            "headless": False,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
            "viewport": {"width": 1200, "height": 800},
        }
        if browser_channel:
            launch_kwargs["channel"] = browser_channel

        try:
            browser_context = await p.chromium.launch_persistent_context(**launch_kwargs)
        except Exception as e:
            # Fallback without specific channel
            if "channel" in launch_kwargs:
                launch_kwargs.pop("channel")
                browser_context = await p.chromium.launch_persistent_context(**launch_kwargs)
            else:
                raise e

        try:
            page = await browser_context.new_page()
            if status_callback:
                status_callback("Navigating to web.whatsapp.com... Please scan QR code.")
            await page.goto("https://web.whatsapp.com", wait_until="domcontentloaded")

            if status_callback:
                status_callback("Scan QR code using WhatsApp on your phone (Linked Devices).")

            # Wait until chat list loads (indicating successful login)
            await page.wait_for_selector(
                "#pane-side, div[data-testid='chat-list']",
                timeout=180000  # 3 minutes for QR scan
            )
            if status_callback:
                status_callback("WhatsApp Web successfully authenticated!")
            await asyncio.sleep(2)  # Give browser 2s to flush session state
            return True
        except Exception as e:
            logger.warning(f"Interactive WhatsApp login exception or closed: {e}")
            return is_whatsapp_linked()
        finally:
            await browser_context.close()


async def main():
    """CLI Entry point."""
    print("=" * 60)
    print("WHATSAPP WEB ONE-TIME FREE AUTHENTICATION HELPER")
    print("=" * 60)
    session_dir = get_whatsapp_session_dir()
    print(f"Session data will be saved permanently to:\n{session_dir}\n")
    print("Launching visible browser window... Please scan the QR code using your WhatsApp mobile app.")
    print("Once logged in and chats load, this window will automatically save the session.")

    def log_cb(msg: str):
        print(f"[STATUS] {msg}")

    success = await authenticate_whatsapp_interactive(log_cb)
    if success:
        print("\n[SUCCESS] Successfully logged into WhatsApp Web! Session saved.")
    else:
        print("\n[INFO] Session window closed.")


if __name__ == "__main__":
    asyncio.run(main())

