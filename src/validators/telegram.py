"""Telegram verification service using official MTProto client (Telethon)."""
import asyncio
import logging
import os
from typing import Dict, List, Optional
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.sessions import StringSession
from telethon.tl.functions.contacts import DeleteContactsRequest, ImportContactsRequest
from telethon.tl.types import InputPhoneContact

from src.models import TelegramResult
from src.utils.rate_limiter import AsyncRateLimiter

logger = logging.getLogger(__name__)


class TelegramValidator:
    """Production MTProto validator for checking Telegram account registration status."""

    def __init__(
        self,
        api_id: Optional[int] = None,
        api_hash: Optional[str] = None,
        session_string: Optional[str] = None,
        rate_limiter: Optional[AsyncRateLimiter] = None,
        simulation_mode: bool = False,
        proxy: Optional[dict] = None,
    ):
        raw_id = api_id or os.getenv("TELEGRAM_API_ID")
        self.api_id = int(raw_id) if raw_id else None
        self.api_hash = api_hash or os.getenv("TELEGRAM_API_HASH")
        self.session_string = session_string or os.getenv("TELEGRAM_SESSION_STRING")
        self.rate_limiter = rate_limiter or AsyncRateLimiter(requests_per_second=2.0, max_concurrency=2)
        self.simulation_mode = simulation_mode or not (self.api_id and self.api_hash and self.session_string)
        self.proxy = proxy
        self._client: Optional[TelegramClient] = None
        self._client_lock = asyncio.Lock()

    async def _get_client(self) -> TelegramClient:
        """Initialize and connect the Telethon MTProto client safely."""
        if self._client is not None and self._client.is_connected():
            return self._client

        async with self._client_lock:
            if self._client is None or not self._client.is_connected():
                session = StringSession(self.session_string)
                self._client = TelegramClient(
                    session,
                    self.api_id,
                    self.api_hash,
                    proxy=self.proxy,
                    connection_retries=3,
                    retry_delay=2,
                )
                await self._client.connect()
                if not await self._client.is_user_authorized():
                    raise RuntimeError("Telegram session is not authorized. Please provide a valid StringSession.")
            return self._client

    async def close(self) -> None:
        """Disconnect client cleanly upon pipeline completion."""
        if self._client and self._client.is_connected():
            await self._client.disconnect()
            self._client = None

    async def verify_number(self, e164_number: str) -> TelegramResult:
        """Verify single phone number registration."""
        results = await self.verify_batch([e164_number])
        return results.get(e164_number, TelegramResult(isRegistered=False, error="Lookup failed"))

    async def verify_batch(self, e164_numbers: List[str]) -> Dict[str, TelegramResult]:
        """Verify a batch of phone numbers via MTProto contact resolution."""
        if not e164_numbers:
            return {}

        if not (self.api_id and self.api_hash and self.session_string):
            if not self.simulation_mode:
                return {
                    num: TelegramResult(
                        isRegistered=False,
                        error="Telegram keys not configured (Enter API ID in Settings)"
                    )
                    for num in e164_numbers
                }
            return self._simulate_verification(e164_numbers)

        async with self.rate_limiter:
            return await self._resolve_contacts_mtproto(e164_numbers)

    async def _resolve_contacts_mtproto(self, e164_numbers: List[str]) -> Dict[str, TelegramResult]:
        """Import contacts into MTProto, extract registration/username info, then delete contacts."""
        results: Dict[str, TelegramResult] = {}
        client = await self._get_client()

        # Build contact items for resolution
        contacts_to_import = [
            InputPhoneContact(
                client_id=idx,
                phone=phone,
                first_name="CRM",
                last_name="Audit"
            )
            for idx, phone in enumerate(e164_numbers)
        ]

        imported_user_ids = []
        try:
            res = await client(ImportContactsRequest(contacts=contacts_to_import))

            # Build lookup of registered users by phone
            registered_users_by_phone = {}
            for user in res.users:
                if hasattr(user, "phone") and user.phone:
                    # Normalized phone without +
                    registered_users_by_phone[user.phone] = user
                imported_user_ids.append(user.id)

            for phone in e164_numbers:
                lookup_key = phone.lstrip("+")
                user = registered_users_by_phone.get(lookup_key)

                if user:
                    has_uname = bool(getattr(user, "username", None))
                    is_premium = bool(getattr(user, "premium", False))
                    results[phone] = TelegramResult(
                        isRegistered=True,
                        hasUsername=has_uname,
                        username=getattr(user, "username", None),
                        userId=user.id,
                        isPremium=is_premium,
                        error=None
                    )
                else:
                    results[phone] = TelegramResult(
                        isRegistered=False,
                        hasUsername=False,
                        isPremium=False,
                        error="Account not registered on Telegram"
                    )

        except FloodWaitError as e:
            logger.warning(f"Telegram FloodWaitError: Required to wait {e.seconds}s")
            self.rate_limiter.apply_cooldown(float(e.seconds))
            await asyncio.sleep(float(e.seconds))
            return {
                phone: TelegramResult(isRegistered=False, error=f"Telegram rate limited (FloodWait {e.seconds}s)")
                for phone in e164_numbers
            }
        except RPCError as e:
            logger.error(f"Telegram RPC error during contact import: {e}")
            return {
                phone: TelegramResult(isRegistered=False, error=f"RPCError: {e.message}")
                for phone in e164_numbers
            }
        except Exception as e:
            logger.error(f"Unexpected error resolving Telegram contacts: {e}")
            return {
                phone: TelegramResult(isRegistered=False, error=str(e))
                for phone in e164_numbers
            }
        finally:
            # Address book hygiene: clean up imported test contacts immediately
            if imported_user_ids:
                try:
                    await client(DeleteContactsRequest(id=imported_user_ids))
                    logger.debug(f"Cleaned up {len(imported_user_ids)} temporary contacts from Telegram address book")
                except Exception as del_err:
                    logger.warning(f"Failed to clean up temporary Telegram contacts: {del_err}")

        return results

    def _simulate_verification(self, e164_numbers: List[str]) -> Dict[str, TelegramResult]:
        """Simulate Telegram responses when running in simulation or test mode."""
        results: Dict[str, TelegramResult] = {}
        for num in e164_numbers:
            last_digit = int(num[-1]) if num[-1].isdigit() else 0
            is_reg = (last_digit % 3 != 0)  # ~66% registered in simulation
            has_uname = (last_digit % 2 == 0) and is_reg
            is_prem = (last_digit == 4) and is_reg

            results[num] = TelegramResult(
                isRegistered=is_reg,
                hasUsername=has_uname,
                username=f"user_{num.lstrip('+')[-4:]}" if has_uname else None,
                isPremium=is_prem,
                error=None if is_reg else "Account not registered (Simulated)"
            )
        return results
