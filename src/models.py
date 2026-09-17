"""Data models and schemas for CRM phone validation and lead scoring."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class WhatsAppResult(BaseModel):
    """Result of WhatsApp registration check."""
    isRegistered: bool = False
    accountType: Optional[str] = None  # "business", "regular", or "unknown"
    error: Optional[str] = None


class TelegramResult(BaseModel):
    """Result of Telegram registration check."""
    isRegistered: bool = False
    hasUsername: bool = False
    username: Optional[str] = None
    userId: Optional[int] = None
    isPremium: bool = False
    error: Optional[str] = None


def compute_lead_quality(
    valid_format: bool,
    number_type: str,
    wa_result: Optional[WhatsAppResult],
    tg_result: Optional[TelegramResult]
) -> Tuple[int, str, str]:
    """Compute 0-100 Lead Quality Score, Recommended Outreach Channel, and Risk Level.

    Returns:
        Tuple[score (0-100), recommended_channel, risk_level]
    """
    if not valid_format:
        return 0, "None", "Invalid Number"

    num_type_lower = (number_type or "").lower()

    # Landlines / Toll Free numbers cannot receive standard mobile messaging
    if "fixed" in num_type_lower or "toll" in num_type_lower:
        return 15, "Email Only (Landline)", "High (Non-Mobile)"

    # VoIP / Virtual numbers (e.g. Google Voice, Twilio, TextNow)
    if "voip" in num_type_lower:
        base_score = 35
        risk = "Medium (VoIP/Burner)"
    else:
        base_score = 50
        risk = "Low"

    # Messaging availability bonus
    wa_active = bool(wa_result and wa_result.isRegistered)
    tg_active = bool(tg_result and tg_result.isRegistered)

    score = base_score
    if wa_active:
        score += 25
        if wa_result.accountType == "business":
            score += 5
    if tg_active:
        score += 15
        if tg_result.hasUsername:
            score += 5
        if tg_result.isPremium:
            score += 5

    score = min(100, score)

    # Determine recommended primary outreach channel
    if wa_active:
        recommended = "WhatsApp"
    elif tg_active:
        recommended = "Telegram"
    elif "voip" in num_type_lower:
        recommended = "Call (VoIP)"
    elif "mobile" in num_type_lower:
        recommended = "SMS / Phone"
    else:
        recommended = "Email Only"

    return score, recommended, risk


class ValidationRecord(BaseModel):
    """Output schema adhering to Apify Dataset requirements and CRM CSV passthrough."""
    input: str
    e164: Optional[str] = None
    country: Optional[str] = None
    validFormat: bool = False
    carrier: Optional[str] = None
    whatsapp: Optional[WhatsAppResult] = None
    telegram: Optional[TelegramResult] = None
    timezone: Optional[str] = None
    localTime: Optional[str] = None
    isBusinessHours: Optional[bool] = None
    leadQualityScore: int = 0
    recommendedChannel: str = "None"
    riskLevel: str = "Low"
    customFields: Optional[Dict[str, Any]] = None
    verifiedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    error: Optional[str] = None

    def to_dataset_dict(self) -> Dict[str, Any]:
        """Format strictly according to Apify dataset requirements, flattening custom CSV columns."""
        res: Dict[str, Any] = {}

        # 1. First, unpack custom CSV input fields to preserve column order for CRM re-import
        if self.customFields:
            for k, v in self.customFields.items():
                res[k] = v

        # 2. Append enriched phone validation fields
        res.update({
            "input": self.input,
            "e164": self.e164,
            "country": self.country,
            "validFormat": self.validFormat,
            "carrier": self.carrier,
            "leadQualityScore": self.leadQualityScore,
            "recommendedChannel": self.recommendedChannel,
            "riskLevel": self.riskLevel,
            "timezone": self.timezone,
            "localTime": self.localTime,
            "isBusinessHours": self.isBusinessHours,
        })

        if self.whatsapp:
            res["whatsapp"] = {
                "isRegistered": self.whatsapp.isRegistered,
                "accountType": self.whatsapp.accountType or "unknown"
            }
            if self.whatsapp.error:
                res["whatsapp"]["error"] = self.whatsapp.error

        if self.telegram:
            res["telegram"] = {
                "isRegistered": self.telegram.isRegistered,
                "hasUsername": self.telegram.hasUsername,
                "isPremium": self.telegram.isPremium,
            }
            if self.telegram.username:
                res["telegram"]["username"] = self.telegram.username
            if self.telegram.error:
                res["telegram"]["error"] = self.telegram.error

        res["verifiedAt"] = self.verifiedAt
        if self.error:
            res["error"] = self.error

        return res


class ActorInput(BaseModel):
    """Apify Actor parsed input schema."""
    phoneNumbers: List[str] = Field(default_factory=list)
    csvContent: Optional[str] = None
    platforms: List[str] = Field(default_factory=lambda: ["whatsapp", "telegram"])
    defaultCountry: str = "FR"
    concurrencyLimit: int = 5
    proxyConfiguration: Optional[Dict[str, Any]] = None
    whatsappApiToken: Optional[str] = None
    whatsappPhoneNumberId: Optional[str] = None
    telegramApiId: Optional[int] = None
    telegramApiHash: Optional[str] = None
    telegramSessionString: Optional[str] = None
    simulationMode: bool = False
