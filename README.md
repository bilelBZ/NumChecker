# CRM Phone & Messaging Validator (WhatsApp & Telegram)

**CRM Phone & Messaging Validator** is a bulk phone and messaging availability checker: feed it a list of phone numbers or an Apollo/HubSpot CSV and get back standardized formatting, carrier details, and registered availability for WhatsApp and Telegram. Download the results as JSON, CSV, Excel, HTML, or XML.

Use it to check if a number is on WhatsApp or Telegram, clean CRM phone lists, detect timezones, and verify leads before a sales campaign. It runs in the cloud and needs no coding.

**Full CRM CSV Passthrough:** Upload your Apollo, HubSpot, or Salesforce CSV export. The Actor keeps all your original columns (`First Name`, `Company`, `Email`, `Custom Tags`, etc.) and appends the validation results directly to each row.

---

## What does it do?

For each phone number or CSV lead, the Actor:
- **Standardizes format first** — parses numbers to international E.164 format and identifies carrier brand and line type (`Mobile`, `Fixed Line`, `VoIP`, `Toll Free`), so every charge goes to a real check.
- **Checks WhatsApp registration** — confirms whether the number is a registered WhatsApp account and identifies Business vs. Regular profiles.
- **Checks Telegram registration** — confirms whether the number is registered on Telegram, extracts public `@username`, and checks Telegram Premium status.
- **Detects Timezone & Business Hours** — resolves the local IANA timezone and calculates whether it is safe to contact right now (Monday–Friday, 9:00 AM – 6:00 PM local time).
- **Calculates Lead Quality Score** — gives an instant 0–100 reachability score and recommends the best outreach channel (`WhatsApp`, `Telegram`, `SMS / Phone`, or `Email Only`).

---

## What data does it return?

Each result is one row per phone number (or one row per CSV record):

| Data | Details |
| :--- | :--- |
| **🏢 CRM Columns** | All your original columns from your uploaded CSV (First Name, Company, Email, etc.) preserved intact |
| **📱 Number (E.164)** | The standardized phone number with country prefix (e.g., `+14155552671`) |
| **🏷️ Carrier & Type** | Network carrier name (e.g., Orange, Verizon) and line classification (`Mobile`, `Fixed Line`, `VoIP`) |
| **💬 WhatsApp** | Registration status (`true` / `false`) and account type (`business` / `regular`) |
| **✈️ Telegram** | Registration status (`true` / `false`), public `@username`, and Telegram Premium badge |
| **🕒 Timezone & Local Time** | Lead's local IANA timezone (e.g., `America/Los_Angeles`) and current local time |
| **☀️ Business Hours** | Whether the lead is currently within business hours (`true` / `false`) |
| **📊 Lead Quality Score** | 0–100 composite deliverability score and recommended outreach channel |
| **🕒 Verified At** | UTC timestamp of when the check was performed |

Every number that could be processed gets its own row with full intelligence. If a number is malformed or invalid, it is flagged with `validFormat: false`, `leadQualityScore: 0`, and a clear error explanation so you can purge dead leads immediately.

---

## Input

Provide an array of phone numbers, or paste raw CSV text with lead details:

### Option A: Simple Phone List
```json
{
  "phoneNumbers": [
    "+14155552671",
    "+33612345678",
    "+447911123456"
  ],
  "platforms": ["whatsapp", "telegram"],
  "defaultCountry": "US"
}
```

### Option B: CRM CSV Passthrough (Apollo / HubSpot)
```json
{
  "csvContent": "First Name,Company,Email,phone\nSarah,FinTech Corp,sarah@fintech.io,+14155552671\nMarc,SaaS Lab,marc@saas.com,+33612345678",
  "platforms": ["whatsapp", "telegram"]
}
```

---

## Output

```json
[
  {
    "First Name": "Sarah",
    "Company": "FinTech Corp",
    "Email": "sarah@fintech.io",
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
  },
  {
    "First Name": "Marc",
    "Company": "SaaS Lab",
    "Email": "marc@saas.com",
    "input": "+33612345678",
    "e164": "+33612345678",
    "country": "FR",
    "validFormat": true,
    "carrier": "Orange",
    "leadQualityScore": 75,
    "recommendedChannel": "WhatsApp",
    "riskLevel": "Low",
    "timezone": "Europe/Paris",
    "localTime": "06:15 PM",
    "isBusinessHours": false,
    "whatsapp": {
      "isRegistered": true,
      "accountType": "regular"
    },
    "telegram": {
      "isRegistered": false,
      "hasUsername": false,
      "isPremium": false
    },
    "verifiedAt": "2026-09-17T16:07:11Z"
  }
]
```

---

## Pricing

Pay only for the results you get — one flat charge per lead verified. Numbers that are completely invalid or couldn't be checked are never charged.

---

## Real-time API

Need checks on demand? Call the Actor like a live API from your backend, CRM, or automation platform (Make.com, Zapier, n8n):

```bash
curl -X POST "https://api.apify.com/v2/acts/<YOUR_USERNAME>~crm-phone-messaging-validator/run-sync-get-dataset-items?token=<YOUR_APIFY_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "phoneNumbers": ["+14155552671", "+33612345678"],
    "platforms": ["whatsapp", "telegram"]
  }'
```

The response is a JSON array containing the verified data, lead scores, timezones, and messaging availability straight back in the HTTP response.
