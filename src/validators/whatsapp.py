"""WhatsApp verification service via official WhatsApp Cloud / Meta Graph API."""
import asyncio
import logging
import os
from typing import Dict, List, Optional
import httpx

from src.models import WhatsAppResult
from src.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class WhatsAppValidator:
    """Production WhatsApp validator interfacing with WhatsApp Business / Cloud API."""

    def __init__(
        self,
        api_token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        simulation_mode: bool = False,
        proxy_url: Optional[str] = None,
        use_playwright: Optional[bool] = None,
    ):
        self.api_token = api_token or os.getenv("WHATSAPP_API_TOKEN")
        self.phone_number_id = phone_number_id or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.rate_limiter = rate_limiter or AsyncRateLimiter(requests_per_second=5.0, max_concurrency=5)
        self.proxy_url = proxy_url
        self.base_url = "https://graph.facebook.com/v20.0"
        self.use_playwright = use_playwright if use_playwright is not None else not bool(self.api_token)
        # When using Playwright, simulation_mode is purely controlled by the user/caller
        if self.use_playwright:
            self.simulation_mode = simulation_mode
        else:
            self.simulation_mode = simulation_mode or not (self.api_token and self.phone_number_id)

        self._playwright_validator = None
        if self.use_playwright:
            try:
                from src.validators.whatsapp_playwright import PlaywrightWhatsAppValidator
                self._playwright_validator = PlaywrightWhatsAppValidator(
                    rate_limiter=self.rate_limiter,
                    simulation_mode=self.simulation_mode
                )
            except ImportError:
                self._playwright_validator = None

    async def verify_number(self, e164_number: str) -> WhatsAppResult:
        """Verify if a single E.164 phone number is registered on WhatsApp."""
        if self.use_playwright and self._playwright_validator:
            return await self._playwright_validator.verify_number(e164_number)
        results = await self.verify_batch([e164_number])
        return results.get(e164_number, WhatsAppResult(isRegistered=False, error="Lookup failed"))

    async def close(self) -> None:
        """Clean up resources."""
        if self._playwright_validator:
            await self._playwright_validator.close()

    async def verify_batch(self, e164_numbers: List[str]) -> Dict[str, WhatsAppResult]:
        """Verify a batch of E.164 phone numbers respecting rate limits."""
        if not e164_numbers:
            return {}

        if self.use_playwright and self._playwright_validator:
            res = {}
            for num in e164_numbers:
                res[num] = await self._playwright_validator.verify_number(num)
            return res

        # If in simulation or missing credentials, return mock verified data
        if self.simulation_mode or not self.api_token:
            return self._simulate_verification(e164_numbers)

        async with self.rate_limiter:
            return await self._call_whatsapp_api(e164_numbers)

    async def _call_whatsapp_api(self, e164_numbers: List[str]) -> Dict[str, WhatsAppResult]:
        """Call Meta Graph API contacts verification endpoint with exponential backoff."""
        endpoint = f"{self.base_url}/{self.phone_number_id}/contacts"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        # WhatsApp Cloud API expects numbers without '+' prefix in the contacts array
        cleaned_numbers = [num.lstrip("+") for num in e164_numbers]
        payload = {
            "blocking": "wait",
            "contacts": cleaned_numbers,
            "force_check": True,
        }

        transport = httpx.AsyncHTTPTransport(proxy=self.proxy_url) if self.proxy_url else None
        async with httpx.AsyncClient(transport=transport, timeout=15.0) as client:
            max_retries = 3
            backoff = 2.0

            for attempt in range(max_retries):
                try:
                    response = await client.post(endpoint, json=payload, headers=headers)

                    if response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", backoff))
                        logger.warning(f"WhatsApp Cloud API 429 Rate Limit. Backing off for {retry_after}s")
                        self.rate_limiter.apply_cooldown(retry_after)
                        await asyncio.sleep(retry_after)
                        backoff *= 2
                        continue

                    response.raise_for_status()
                    data = response.json()
                    return self._parse_api_response(e164_numbers, data)

                except httpx.HTTPStatusError as exc:
                    logger.error(f"WhatsApp API HTTP error {exc.response.status_code}: {exc.response.text}")
                    if attempt == max_retries - 1:
                        return {
                            num: WhatsAppResult(isRegistered=False, error=f"HTTP {exc.response.status_code}")
                            for num in e164_numbers
                        }
                    await asyncio.sleep(backoff)
                    backoff *= 2

                except Exception as exc:
                    logger.error(f"WhatsApp API request failed: {exc}")
                    if attempt == max_retries - 1:
                        return {
                            num: WhatsAppResult(isRegistered=False, error=str(exc))
                            for num in e164_numbers
                        }
                    await asyncio.sleep(backoff)
                    backoff *= 2

        return {
            num: WhatsAppResult(isRegistered=False, error="Exhausted retry attempts")
            for num in e164_numbers
        }

    def _parse_api_response(self, original_numbers: List[str], data: dict) -> Dict[str, WhatsAppResult]:
        """Parse Meta contacts verification response payload."""
        results: Dict[str, WhatsAppResult] = {}
        contacts_list = data.get("contacts", [])
        contacts_map = {c.get("input", ""): c for c in contacts_list}

        for num in original_numbers:
            lookup_key = num.lstrip("+")
            contact_info = contacts_map.get(lookup_key)

            if contact_info:
                status = contact_info.get("status")
                is_registered = (status == "valid")
                # When valid, determine if standard account or business
                account_type = "business" if contact_info.get("type") == "business" else "regular"
                results[num] = WhatsAppResult(
                    isRegistered=is_registered,
                    accountType=account_type if is_registered else None,
                    error=None if is_registered else "Account not registered"
                )
            else:
                results[num] = WhatsAppResult(
                    isRegistered=False,
                    accountType=None,
                    error="Number not found in response"
                )

        return results

    def _simulate_verification(self, e164_numbers: List[str]) -> Dict[str, WhatsAppResult]:
        """Simulation logic for local testing and credential-less verification runs."""
        results: Dict[str, WhatsAppResult] = {}
        for num in e164_numbers:
            # Deterministic simulation based on number digits
            last_digit = int(num[-1]) if num[-1].isdigit() else 0
            is_reg = (last_digit % 2 == 0)  # Even numbers registered
            acc_type = "business" if last_digit in (2, 8) else "regular"

            results[num] = WhatsAppResult(
                isRegistered=is_reg,
                accountType=acc_type if is_reg else None,
                error=None if is_reg else "Account not registered (Simulated)"
            )
        return results
