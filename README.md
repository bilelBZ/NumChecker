# B2B CRM Lead Cleaner: WhatsApp & Telegram Validator (Apollo & HubSpot Ready)

Production-grade, high-performance Apify Actor built for B2B sales teams, growth marketers, and agencies. Standardizes phone numbers using Google's `libphonenumber`, detects carrier/VoIP details, calculates 0–100 lead quality scores, detects local timezones & business hours, and concurrently checks messaging availability across WhatsApp and Telegram—**while preserving all original CRM CSV columns**.

---

## 🚀 Key Features

- **🔄 Full CRM CSV Column Passthrough:** Upload CSV exports directly from Apollo.io, HubSpot, or Salesforce. The Actor preserves all original columns (`First Name`, `Company`, `Email`, `Deal Size`) and appends validation intelligence to the same rows.
- **📊 0–100 Lead Quality Score & Best Channel:** Provides an instant composite score (`leadQualityScore: 95`) and recommends the primary outreach channel (`"WhatsApp"`, `"Telegram"`, `"SMS / Phone"`, or `"Email Only"`).
- **🕒 Timezone & "Safe-to-Contact" Window:** Detects the lead's local IANA timezone (`America/New_York`), calculates local current time, and outputs `isBusinessHours: true/false` to prevent sending messages in the middle of the night.
- **📱 Google libphonenumber Standardization:** Formats numbers to E.164 (`+33612345678`), detects ISO country codes, carrier brands (Orange, Verizon), and line types (`Mobile`, `Fixed Line`, `VoIP`, `Toll Free`).
- **💬 Dual-Mode WhatsApp Verification:** Works with either 100% free Playwright WhatsApp Web sessions or the official Meta WhatsApp Cloud API.
- **✈️ Telegram MTProto & Premium Detection:** Uses `Telethon` to resolve registration, public `@username`, and whether the user is a **Telegram Premium** subscriber.
- **🛡️ Anti-Ban Zero Address Book Pollution:** Automatically executes `DeleteContactsRequest` immediately after resolution to keep the Telegram account safe and unflagged.
- **⚡ Cost-Saving Offline Pre-Filter:** Invalid strings, landlines, and non-messaging numbers are detected offline in <1ms without spending network bandwidth or proxy quotas.

---

## 📋 Output Dataset Format

When processing a CRM CSV, all original columns are preserved alongside the enriched intelligence:

```json
{
  "First Name": "Sarah",
  "Company": "FinTech Corp",
  "Email": "sarah@fintech.io",
  "Status": "New Lead",
  "input": "+14155552671",
  "e164": "+14155552671",
  "country": "US",
  "validFormat": true,
  "carrier": "T-Mobile",
  "leadQualityScore": 95,
  "recommendedChannel": "WhatsApp",
  "riskLevel": "Low",
  "timezone": "America/Los_Angeles",
  "localTime": "09:15 AM",
  "isBusinessHours": true,
  "whatsapp": {
    "isRegistered": true,
    "accountType": "business"
  },
  "telegram": {
    "isRegistered": true,
    "hasUsername": true,
    "isPremium": true
  },
  "verifiedAt": "2026-09-17T16:07:11Z"
}
```

If a number is malformed or invalid:
```json
{
  "First Name": "John",
  "Company": "Unknown",
  "input": "12345",
  "validFormat": false,
  "leadQualityScore": 0,
  "recommendedChannel": "None",
  "riskLevel": "Invalid Number",
  "verifiedAt": "2026-09-17T16:07:11Z",
  "error": "Parsing error: The string supplied did not seem to be a phone number."
}
```

---

## ⚙️ Input Configuration (`.actor/input_schema.json`)

| Field | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `csvContent` | `string` | `null` | Raw CSV text from Apollo, HubSpot, or Salesforce (preserves all columns). |
| `phoneNumbers` | `array` | `[...]` | Alternative array of raw phone numbers. |
| `platforms` | `array` | `["whatsapp", "telegram"]` | Selected platforms to check. |
| `defaultCountry` | `string` | `"FR"` | Fallback ISO country code for national numbers. |
| `concurrencyLimit` | `integer` | `5` | Maximum concurrent verification workers. |
| `proxyConfiguration` | `object` | `null` | Apify Proxy configuration (residential or datacenter). |
| `whatsappApiToken` | `string` (secret) | `null` | Optional Meta Graph API access token (if using Cloud API). |
| `whatsappPhoneNumberId` | `string` | `null` | Optional WhatsApp Business Phone Number ID. |
| `telegramApiId` | `integer` | `null` | Free Telegram App API ID (from my.telegram.org). |
| `telegramApiHash` | `string` (secret) | `null` | Free Telegram App API Hash (from my.telegram.org). |
| `telegramSessionString` | `string` (secret) | `null` | Free Telethon StringSession. |
| `simulationMode` | `boolean` | `false` | Dry-run simulation for testing without credentials. |

---

## 🛠️ Local Development & Testing

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m pytest -v tests/
```

### 3. One-Time Free WhatsApp Web Linking
```bash
python -m src.auth_whatsapp
```

### 4. Run Locally
```bash
python -m src.main
```

---

## 🚢 Deploying & Monetizing on Apify

1. **Log in to Apify**:
   ```bash
   apify login
   ```
2. **Push to Apify**:
   ```bash
   apify push
   ```
3. **Monetize on Apify Store**:
   - In your Apify Console $\rightarrow$ **Publication** tab:
   - Select **Pay per result** (suggested: `$0.005` to `$0.01` per verified lead) or **Monthly subscription** (suggested: `$29` to `$49`/month).
