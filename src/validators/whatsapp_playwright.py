"""Free WhatsApp Web headless session verification via Playwright."""
import asyncio
import logging
import os
import sys
from typing import Dict, List, Optional
from playwright.async_api import BrowserContext, Page, async_playwright

from src.auth_whatsapp import get_whatsapp_session_dir
from src.models import WhatsAppResult
from src.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class PlaywrightWhatsAppValidator:
    """Free WhatsApp verification using a headless Chromium browser session."""

    def __init__(
        self,
        session_dir: Optional[str] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        headless: bool = True,
        simulation_mode: bool = False,
    ):
        self.session_dir = session_dir or get_whatsapp_session_dir()
        self.rate_limiter = rate_limiter or AsyncRateLimiter(requests_per_second=1.0, max_concurrency=1)
        self.headless = headless
        self.simulation_mode = simulation_mode
        self._playwright = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()
        self._is_authenticated = False

    async def _ensure_browser(self) -> Page:
        """Initialize persistent browser context with saved WhatsApp Web session."""
        if self._page is not None and not self._page.is_closed():
            return self._page

        async with self._lock:
            if self._page is None or self._page.is_closed():
                os.makedirs(self.session_dir, exist_ok=True)
                self._playwright = await async_playwright().start()

                browser_channel = None
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
                    "user_data_dir": self.session_dir,
                    "headless": self.headless,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                    "viewport": {"width": 1280, "height": 800},
                }
                if browser_channel:
                    launch_kwargs["channel"] = browser_channel

                try:
                    self._context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
                except Exception:
                    if "channel" in launch_kwargs:
                        launch_kwargs.pop("channel")
                        self._context = await self._playwright.chromium.launch_persistent_context(**launch_kwargs)
                    else:
                        raise

                self._page = await self._context.new_page()

                # Test if already authenticated
                await self._page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=30000)
                try:
                    # Look for chat panel indicating active session
                    await self._page.wait_for_selector(
                        "#pane-side, div[data-testid='chat-list'], div[aria-label='Chat list']",
                        timeout=25000
                    )
                    self._is_authenticated = True
                    logger.info("Playwright WhatsApp Web session is authenticated and ready.")
                except Exception:
                    # Capture QR code screenshot for Apify cloud users
                    try:
                        from apify import Actor
                        qr_elem = await self._page.query_selector("canvas, div[data-ref]")
                        if qr_elem:
                            qr_bytes = await qr_elem.screenshot()
                            await Actor.set_value("WHATSAPP_QR.png", qr_bytes, content_type="image/png")
                            logger.info("Saved WhatsApp login QR code to Apify Key-Value Store: WHATSAPP_QR.png")
                    except Exception:
                        pass

                    logger.warning(
                        "WhatsApp Web is not authenticated. To link your free account locally, "
                        "run: python -m src.auth_whatsapp. In Apify Cloud, scan the QR code saved in Key-Value Store."
                    )
                    self._is_authenticated = False

            return self._page

    async def verify_number(self, e164_number: str) -> WhatsAppResult:
        """Verify if a single E.164 number is registered on WhatsApp using headless browser."""
        if self.simulation_mode:
            return self._simulate(e164_number)

        async with self.rate_limiter:
            try:
                page = await self._ensure_browser()

                if not self._is_authenticated:
                    logger.warning("Unauthenticated WhatsApp session.")
                    return WhatsAppResult(
                        isRegistered=False,
                        error="WhatsApp not linked. Click 'Link WhatsApp (Scan QR)' first."
                    )

                cleaned_num = e164_number.lstrip("+").replace(" ", "").replace("-", "")
                url = f"https://web.whatsapp.com/send?phone={cleaned_num}"
                await page.goto(url, wait_until="domcontentloaded", timeout=35000)

                # Poll for up to 20 seconds for resolution:
                # - If "Starting chat" dialog appears, wait for it to finish.
                # - If error dialog ("isn't on WhatsApp") appears, return isRegistered=False.
                # - If conversation panel (#main, input box) loads, return isRegistered=True.
                for _ in range(20):
                    await asyncio.sleep(1)

                    # 1. Check for modal dialogs
                    dialog = await page.query_selector("div[data-animate-modal-popup='true'], div[role='dialog']")
                    if dialog:
                        txt = (await dialog.inner_text()).lower()
                        # If transient spinner is present, keep waiting
                        if "starting chat" in txt or "démarrage" in txt or "chargement" in txt:
                            continue
                        # If error dialog appeared
                        if "whatsapp" in txt or "invalid" in txt or "ok" in txt:
                            ok_btn = await dialog.query_selector("button")
                            if ok_btn:
                                await ok_btn.click()
                            return WhatsAppResult(
                                isRegistered=False,
                                accountType=None,
                                error="Account not registered on WhatsApp"
                            )

                    # 2. Check for conversation panel
                    main_chat = await page.query_selector("#main, div[data-testid='conversation-panel-wrapper'], footer div[contenteditable='true']")
                    if main_chat:
                        # Check header for business indicators
                        is_business = False
                        header = await page.query_selector("#main header, header")
                        if header:
                            header_text = (await header.inner_text()).lower()
                            if "business" in header_text or "professionnel" in header_text or "compte pro" in header_text:
                                is_business = True

                        return WhatsAppResult(
                            isRegistered=True,
                            accountType="business" if is_business else "regular",
                            error=None
                        )

                return WhatsAppResult(isRegistered=False, error="Could not determine registration status (Timeout)")

            except Exception as e:
                logger.error(f"Playwright WhatsApp verification error for {e164_number}: {e}")
                return WhatsAppResult(isRegistered=False, error=str(e))

    async def close(self) -> None:
        """Close browser resources cleanly."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self._page = None

    def _simulate(self, num: str) -> WhatsAppResult:
        """Simulation fallback when browser session is not linked."""
        last_digit = int(num[-1]) if num[-1].isdigit() else 0
        is_reg = (last_digit % 2 == 0)
        acc_type = "business" if last_digit in (2, 8) else "regular"
        return WhatsAppResult(
            isRegistered=is_reg,
            accountType=acc_type if is_reg else None,
            error=None if is_reg else "Account not registered (Simulated)"
        )
