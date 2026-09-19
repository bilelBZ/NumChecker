"""Comprehensive test suite for CRM phone validation actor with B2B intelligence."""
import asyncio
import pytest
from src.models import (
    TelegramResult,
    ValidationRecord,
    WhatsAppResult,
    compute_lead_quality,
)
from src.utils.input_parser import (
    normalize_input_records,
    normalize_phone_input_list,
    parse_csv_phone_numbers,
    parse_csv_records,
)
from src.utils.rate_limiter import AsyncRateLimiter, retry_with_backoff
from src.validators.phone import PhoneValidator
from src.validators.telegram import TelegramValidator
from src.validators.whatsapp import WhatsAppValidator


def test_phone_sanitization_valid_french():
    validator = PhoneValidator(default_region="FR")
    res = validator.sanitize_and_validate("+33612345678")
    assert res.valid_format is True
    assert res.e164 == "+33612345678"
    assert res.country == "FR"
    assert res.is_messaging_capable is True
    assert res.carrier is not None
    assert res.timezone is not None
    assert res.local_time is not None


def test_phone_sanitization_national_format():
    validator = PhoneValidator(default_region="FR")
    res = validator.sanitize_and_validate("06 12 34 56 78")
    assert res.valid_format is True
    assert res.e164 == "+33612345678"
    assert res.country == "FR"


def test_phone_sanitization_us_timezone():
    validator = PhoneValidator(default_region="US")
    res = validator.sanitize_and_validate("+14155552671")
    assert res.valid_format is True
    assert res.e164 == "+14155552671"
    assert res.country == "US"
    assert "America/Los_Angeles" in res.timezone
    assert res.local_time is not None
    assert isinstance(res.is_business_hours, bool)


def test_phone_sanitization_invalid_number():
    validator = PhoneValidator(default_region="FR")
    res = validator.sanitize_and_validate("12345")
    assert res.valid_format is False
    assert res.e164 is None
    assert res.is_messaging_capable is False
    assert res.timezone is None


def test_csv_parser_passthrough():
    csv_sample = """First Name,Company,Email,phone,Custom Tag
Alice,Acme Corp,alice@acme.com,+33612345678,VIP
Bob,Stark Ind,bob@stark.com,+14155552671,Prospect
"""
    records = parse_csv_records(csv_sample)
    assert len(records) == 2
    assert records[0].raw_number == "+33612345678"
    assert records[0].custom_fields == {
        "First Name": "Alice",
        "Company": "Acme Corp",
        "Email": "alice@acme.com",
        "Custom Tag": "VIP",
    }
    assert records[1].raw_number == "+14155552671"
    assert records[1].custom_fields["Company"] == "Stark Ind"


def test_normalize_phone_input_list_deduplication():
    array_inputs = ["+33612345678", " +14155552671 "]
    csv_inputs = "phone\n+33612345678\n+447911123456"

    combined = normalize_phone_input_list(array_inputs, csv_inputs)
    assert len(combined) == 3
    assert combined == ["+33612345678", "+14155552671", "+447911123456"]


@pytest.mark.asyncio
async def test_rate_limiter():
    limiter = AsyncRateLimiter(requests_per_second=20.0, max_concurrency=2)
    start = asyncio.get_event_loop().time()

    async def worker():
        async with limiter:
            await asyncio.sleep(0.01)

    await asyncio.gather(*[worker() for _ in range(4)])
    elapsed = asyncio.get_event_loop().time() - start
    assert elapsed >= 0.05


@pytest.mark.asyncio
async def test_retry_with_backoff():
    attempts = 0

    async def flaky():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise ValueError("Temporary failure")
        return "success"

    res = await retry_with_backoff(flaky, max_retries=3, initial_delay=0.01, jitter=False)
    assert res == "success"
    assert attempts == 3


def test_lead_quality_scoring():
    # 1. Invalid number -> 0 score
    score, ch, risk = compute_lead_quality(False, "Invalid", None, None)
    assert score == 0
    assert risk == "Invalid Number"

    # 2. Landline / Fixed -> 15 score, Email Only
    score, ch, risk = compute_lead_quality(True, "Fixed Line", None, None)
    assert score == 15
    assert ch == "Email Only (Landline)"
    assert risk == "High (Non-Mobile)"

    # 3. Mobile with WhatsApp business & Telegram premium -> 100 score
    wa = WhatsAppResult(isRegistered=True, accountType="business")
    tg = TelegramResult(isRegistered=True, hasUsername=True, isPremium=True)
    score, ch, risk = compute_lead_quality(True, "Mobile", wa, tg)
    assert score == 100
    assert ch == "WhatsApp"
    assert risk == "Low"

    # 4. Mobile with Telegram only -> 70 score, Telegram channel
    tg_only = TelegramResult(isRegistered=True, hasUsername=True, isPremium=False)
    score, ch, risk = compute_lead_quality(True, "Mobile", None, tg_only)
    assert score == 70
    assert ch == "Telegram"


@pytest.mark.asyncio
async def test_whatsapp_simulation():
    wa = WhatsAppValidator(simulation_mode=True)
    res = await wa.verify_number("+33612345678")
    assert isinstance(res, WhatsAppResult)
    assert res.isRegistered is True


@pytest.mark.asyncio
async def test_telegram_simulation_premium():
    tg = TelegramValidator(simulation_mode=True)
    # Ends in 4 -> simulated as isPremium
    res = await tg.verify_number("+33612345674")
    assert isinstance(res, TelegramResult)
    assert res.isRegistered is True
    assert res.isPremium is True


def test_dataset_output_csv_passthrough_matching():
    record = ValidationRecord(
        input="+33612345678",
        e164="+33612345678",
        country="FR",
        validFormat=True,
        carrier="Mobile",
        timezone="Europe/Paris",
        localTime="05:00 PM",
        isBusinessHours=True,
        leadQualityScore=95,
        recommendedChannel="WhatsApp",
        riskLevel="Low",
        customFields={
            "First Name": "Alice",
            "Company": "Acme Corp",
            "Apollo ID": "12345"
        },
        whatsapp=WhatsAppResult(isRegistered=True, accountType="business"),
        telegram=TelegramResult(isRegistered=True, hasUsername=True, isPremium=True),
        verifiedAt="2026-09-17T11:50:00Z"
    )
    d = record.to_dataset_dict()

    # Verify custom CRM columns are preserved at root
    assert d["First Name"] == "Alice"
    assert d["Company"] == "Acme Corp"
    assert d["Apollo ID"] == "12345"
    # Verify enriched intelligence metrics
    assert d["e164"] == "+33612345678"
    assert d["leadQualityScore"] == 95
    assert d["recommendedChannel"] == "WhatsApp"
    assert d["timezone"] == "Europe/Paris"
    assert d["isBusinessHours"] is True
    assert d["telegram"]["isPremium"] is True
