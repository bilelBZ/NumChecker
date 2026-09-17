"""Phone number formatting, E.164 standardization, carrier, timezone and region validation."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

import phonenumbers
from phonenumbers import carrier as phone_carrier
from phonenumbers import geocoder, PhoneNumberType, NumberParseException
from phonenumbers import timezone as phone_timezone


NUMBER_TYPE_MAPPING = {
    PhoneNumberType.MOBILE: "Mobile",
    PhoneNumberType.FIXED_LINE_OR_MOBILE: "Fixed Line or Mobile",
    PhoneNumberType.FIXED_LINE: "Fixed Line",
    PhoneNumberType.TOLL_FREE: "Toll Free",
    PhoneNumberType.PREMIUM_RATE: "Premium Rate",
    PhoneNumberType.SHARED_COST: "Shared Cost",
    PhoneNumberType.VOIP: "VoIP",
    PhoneNumberType.PERSONAL_NUMBER: "Personal Number",
    PhoneNumberType.PAGER: "Pager",
    PhoneNumberType.UAN: "UAN",
    PhoneNumberType.VOICEMAIL: "Voicemail",
    PhoneNumberType.UNKNOWN: "Unknown",
}

# Number types capable of receiving SMS / messaging activation
MESSAGING_CAPABLE_TYPES = {
    PhoneNumberType.MOBILE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE,
    PhoneNumberType.VOIP,
    PhoneNumberType.PERSONAL_NUMBER,
}


@dataclass
class PhoneSanitizationResult:
    """Sanitized phone number attributes."""
    input_number: str
    e164: Optional[str]
    country: Optional[str]
    valid_format: bool
    is_possible: bool
    carrier: Optional[str]
    carrier_name: Optional[str]
    number_type: str
    is_messaging_capable: bool
    region_description: Optional[str]
    timezone: Optional[str] = None
    local_time: Optional[str] = None
    is_business_hours: Optional[bool] = None
    error: Optional[str] = None


class PhoneValidator:
    """High-performance libphonenumber validator with timezone intelligence."""

    def __init__(self, default_region: str = "FR"):
        self.default_region = (default_region or "FR").upper()

    def _compute_timezone(self, parsed) -> Tuple[Optional[str], Optional[str], Optional[bool]]:
        """Calculate primary IANA timezone, local current time, and business hours status."""
        tz_list = phone_timezone.time_zones_for_number(parsed)
        if not tz_list or tz_list == ("Etc/Unknown",):
            return None, None, None

        tz_name = tz_list[0]
        try:
            zi = ZoneInfo(tz_name)
            now_local = datetime.now(zi)
            local_time_str = now_local.strftime("%I:%M %p")
            # Business hours: Monday (0) to Friday (4), between 9:00 AM (9) and 6:00 PM (18)
            is_weekday = now_local.weekday() < 5
            is_working_hour = 9 <= now_local.hour < 18
            is_business_hours = is_weekday and is_working_hour
            return tz_name, local_time_str, is_business_hours
        except Exception:
            return tz_name, None, None

    def sanitize_and_validate(self, raw_number: str, region_override: Optional[str] = None) -> PhoneSanitizationResult:
        """Parse raw string, standardize to E.164, and detect carrier, timezone, and region."""
        region = (region_override or self.default_region).upper()
        raw_cleaned = (raw_number or "").strip()

        if not raw_cleaned:
            return PhoneSanitizationResult(
                input_number=raw_number,
                e164=None,
                country=None,
                valid_format=False,
                is_possible=False,
                carrier=None,
                carrier_name=None,
                number_type="Unknown",
                is_messaging_capable=False,
                region_description=None,
                error="Empty input"
            )

        try:
            parsed = phonenumbers.parse(raw_cleaned, region)
        except NumberParseException as e:
            return PhoneSanitizationResult(
                input_number=raw_number,
                e164=None,
                country=None,
                valid_format=False,
                is_possible=False,
                carrier=None,
                carrier_name=None,
                number_type="Unknown",
                is_messaging_capable=False,
                region_description=None,
                error=f"Parsing error: {e._msg}"
            )

        is_valid = phonenumbers.is_valid_number(parsed)
        is_possible = phonenumbers.is_possible_number(parsed)

        if not is_possible and not is_valid:
            return PhoneSanitizationResult(
                input_number=raw_number,
                e164=None,
                country=None,
                valid_format=False,
                is_possible=False,
                carrier=None,
                carrier_name=None,
                number_type="Invalid",
                is_messaging_capable=False,
                region_description=None,
                error="Invalid phone number structure"
            )

        e164_formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        country_iso = phonenumbers.region_code_for_number(parsed)
        if not country_iso:
            country_iso = region

        num_type_enum = phonenumbers.number_type(parsed)
        num_type_str = NUMBER_TYPE_MAPPING.get(num_type_enum, "Unknown")
        carrier_brand = phone_carrier.name_for_number(parsed, "en") or None
        region_desc = geocoder.description_for_number(parsed, "en") or None

        # Determine primary carrier display: carrier name or number type (e.g. "Mobile")
        carrier_display = carrier_brand if carrier_brand else num_type_str
        is_messaging_capable = is_valid and (num_type_enum in MESSAGING_CAPABLE_TYPES)

        # Calculate timezone and business hours
        tz_name, local_time, is_biz_hours = self._compute_timezone(parsed)

        return PhoneSanitizationResult(
            input_number=raw_number,
            e164=e164_formatted,
            country=country_iso,
            valid_format=is_valid,
            is_possible=is_possible,
            carrier=carrier_display,
            carrier_name=carrier_brand,
            number_type=num_type_str,
            is_messaging_capable=is_messaging_capable,
            region_description=region_desc,
            timezone=tz_name,
            local_time=local_time,
            is_business_hours=is_biz_hours,
            error=None if is_valid else "Number is possible but failed strict country validation"
        )
