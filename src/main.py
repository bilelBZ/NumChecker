"""Main Apify Actor entrypoint for CRM phone and messaging verification with B2B lead intelligence."""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from apify import Actor

from src.models import (
    ActorInput,
    TelegramResult,
    ValidationRecord,
    WhatsAppResult,
    compute_lead_quality,
)
from src.utils.input_parser import InputPhoneRecord, normalize_input_records
from src.utils.rate_limiter import AsyncRateLimiter
from src.validators.phone import PhoneSanitizationResult, PhoneValidator
from src.validators.telegram import TelegramValidator
from src.validators.whatsapp import WhatsAppValidator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("actor.crm_phone_validator")


async def process_single_number(
    entry: InputPhoneRecord,
    sanitized: PhoneSanitizationResult,
    platforms: List[str],
    wa_validator: Optional[WhatsAppValidator],
    tg_validator: Optional[TelegramValidator],
    semaphore: asyncio.Semaphore,
) -> ValidationRecord:
    """Validate messaging platform registrations and compute lead intelligence metrics."""
    raw_number = entry.raw_number
    custom_fields = entry.custom_fields
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # If phone format is invalid, return immediately with zero score
    if not sanitized.valid_format or not sanitized.e164:
        score, channel, risk = compute_lead_quality(False, "Invalid", None, None)
        return ValidationRecord(
            input=raw_number,
            e164=None,
            country=sanitized.country,
            validFormat=False,
            carrier=sanitized.carrier,
            whatsapp=None,
            telegram=None,
            timezone=sanitized.timezone,
            localTime=sanitized.local_time,
            isBusinessHours=sanitized.is_business_hours,
            leadQualityScore=score,
            recommendedChannel=channel,
            riskLevel=risk,
            customFields=custom_fields,
            verifiedAt=now_iso,
            error=sanitized.error or "Invalid phone number format",
        )

    e164 = sanitized.e164
    wa_result: Optional[WhatsAppResult] = None
    tg_result: Optional[TelegramResult] = None

    async with semaphore:
        tasks = []

        if "whatsapp" in platforms and wa_validator:
            tasks.append(("whatsapp", wa_validator.verify_number(e164)))

        if "telegram" in platforms and tg_validator:
            tasks.append(("telegram", tg_validator.verify_number(e164)))

        if tasks:
            platform_keys = [t[0] for t in tasks]
            results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)

            for key, res in zip(platform_keys, results):
                if isinstance(res, Exception):
                    logger.error(f"Platform check failed for {key} ({e164}): {res}")
                    if key == "whatsapp":
                        wa_result = WhatsAppResult(isRegistered=False, error=str(res))
                    elif key == "telegram":
                        tg_result = TelegramResult(isRegistered=False, hasUsername=False, error=str(res))
                else:
                    if key == "whatsapp":
                        wa_result = res
                    elif key == "telegram":
                        tg_result = res

    # Compute 0-100 Lead Quality Score & Channel Recommendation
    score, recommended_ch, risk_lvl = compute_lead_quality(
        valid_format=sanitized.valid_format,
        number_type=sanitized.number_type,
        wa_result=wa_result,
        tg_result=tg_result
    )

    return ValidationRecord(
        input=raw_number,
        e164=e164,
        country=sanitized.country,
        validFormat=True,
        carrier=sanitized.carrier,
        whatsapp=wa_result,
        telegram=tg_result,
        timezone=sanitized.timezone,
        localTime=sanitized.local_time,
        isBusinessHours=sanitized.is_business_hours,
        leadQualityScore=score,
        recommendedChannel=recommended_ch,
        riskLevel=risk_lvl,
        customFields=custom_fields,
        verifiedAt=now_iso,
    )


async def main() -> None:
    """Apify Actor lifecycle execution."""
    async with Actor:
        raw_input: Dict[str, Any] = await Actor.get_input() or {}
        actor_input = ActorInput(**raw_input)

        # Handle Apify Proxy configuration if configured
        proxy_url: Optional[str] = None
        if actor_input.proxyConfiguration:
            try:
                proxy_config = await Actor.create_proxy_configuration(
                    actor_proxy_input=actor_input.proxyConfiguration
                )
                if proxy_config:
                    proxy_url = await proxy_config.new_url()
                    logger.info("Configured Apify Proxy for outgoing validation requests.")
            except Exception as e:
                logger.warning(f"Could not initialize proxy configuration: {e}")

        # Normalize phone inputs with full CRM column passthrough
        input_records = normalize_input_records(
            actor_input.phoneNumbers,
            actor_input.csvContent
        )

        if not input_records:
            logger.warning("No phone numbers found in input. Exiting.")
            return

        logger.info(f"Loaded {len(input_records)} distinct phone records for validation.")
        logger.info(f"Active platforms: {actor_input.platforms}, Concurrency: {actor_input.concurrencyLimit}")

        # Initialize validators
        phone_validator = PhoneValidator(default_region=actor_input.defaultCountry)

        wa_limiter = AsyncRateLimiter(
            requests_per_second=5.0,
            max_concurrency=actor_input.concurrencyLimit
        )
        tg_limiter = AsyncRateLimiter(
            requests_per_second=2.0,
            max_concurrency=min(3, actor_input.concurrencyLimit)
        )

        wa_validator = (
            WhatsAppValidator(
                api_token=actor_input.whatsappApiToken,
                phone_number_id=actor_input.whatsappPhoneNumberId,
                rate_limiter=wa_limiter,
                simulation_mode=actor_input.simulationMode,
                proxy_url=proxy_url,
            )
            if "whatsapp" in actor_input.platforms
            else None
        )

        tg_validator = (
            TelegramValidator(
                api_id=actor_input.telegramApiId,
                api_hash=actor_input.telegramApiHash,
                session_string=actor_input.telegramSessionString,
                rate_limiter=tg_limiter,
                simulation_mode=actor_input.simulationMode,
            )
            if "telegram" in actor_input.platforms
            else None
        )

        # Semaphore for overall task pool concurrency
        semaphore = asyncio.Semaphore(actor_input.concurrencyLimit)

        # Step 1: Pre-sanitize all numbers with libphonenumber & timezone
        sanitized_items = [
            (entry, phone_validator.sanitize_and_validate(entry.raw_number))
            for entry in input_records
        ]

        valid_count = sum(1 for _, s in sanitized_items if s.valid_format)
        invalid_count = len(sanitized_items) - valid_count
        logger.info(f"Phone sanitization complete: {valid_count} valid, {invalid_count} malformed/invalid.")

        # Step 2: Stream records to Apify dataset in batches
        batch_size = 20
        dataset_buffer: List[Dict[str, Any]] = []

        try:
            tasks = [
                process_single_number(
                    entry=entry,
                    sanitized=sanitized,
                    platforms=actor_input.platforms,
                    wa_validator=wa_validator,
                    tg_validator=tg_validator,
                    semaphore=semaphore,
                )
                for entry, sanitized in sanitized_items
            ]

            for future in asyncio.as_completed(tasks):
                record: ValidationRecord = await future
                dataset_buffer.append(record.to_dataset_dict())

                if len(dataset_buffer) >= batch_size:
                    await Actor.push_data(dataset_buffer)
                    dataset_buffer.clear()

            if dataset_buffer:
                await Actor.push_data(dataset_buffer)
                dataset_buffer.clear()

            logger.info(f"Successfully pushed all {len(input_records)} validation records to Apify Dataset.")

        finally:
            if wa_validator:
                await wa_validator.close()
            if tg_validator:
                await tg_validator.close()


if __name__ == "__main__":
    asyncio.run(main())
