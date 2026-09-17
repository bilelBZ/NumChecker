# CRM Phone & Messaging Validator (WhatsApp & Telegram)

High-performance CRM data hygiene and lead enrichment Actor. Standardize phone numbers to international E.164 format, detect carriers and VoIP lines, calculate 0–100 lead reachability scores, resolve local timezones, and check registered messaging accounts on **WhatsApp** and **Telegram**—**while preserving all original CRM CSV columns**.

---

## 🎯 Why Use This Actor?

- **Zero Manual VLOOKUPs:** Unlike basic validators that only return phone numbers, this Actor keeps all your original CRM fields (`First Name`, `Company`, `Email`, `Deal Stage`, `Apollo ID`) and appends the enriched data directly to each row.
- **Cut Bounced Outreach by 40%+:** Filter out landlines, toll-free numbers, VoIP virtual lines, and malformed strings before launching cold outreach campaigns.
- **Prioritize Hot Leads Instantly:** Use the composite **0–100 Lead Quality Score** to immediately identify prospects who are active across both WhatsApp and Telegram.
- **Contact Leads at the Right Time:** Automatic timezone resolution and `isBusinessHours` flags ensure you never message prospects outside working hours.

---

## 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| **🔄 Full CRM Passthrough** | Preserves all incoming CSV columns from Apollo, HubSpot, or Salesforce and appends enriched validation fields to the exact same records. |
| **📊 0–100 Lead Quality Score** | Instant score evaluating deliverability, carrier type, and messaging presence, plus a `recommendedChannel` recommendation (`WhatsApp`, `Telegram`, `SMS / Phone`, or `Email Only`). |
| **🕒 Timezone & Safe Hours** | Resolves the lead's local IANA timezone (`America/New_York`), displays local current time, and flags `isBusinessHours: true/false` (Mon–Fri 9:00 AM – 6:00 PM local time). |
| **📱 Carrier & Line Detection** | Identifies mobile carriers (e.g., Orange, Verizon, Vodafone) and detects line types (`Mobile`, `Fixed Line`, `VoIP`, `Toll Free`). |
| **💬 WhatsApp Verification** | Checks registered accounts and identifies whether the profile is a **Business** or **Regular** account. |
| **✈️ Telegram & Premium Detection** | Verifies Telegram account presence, public `@username`, and whether the user is a **Telegram Premium** subscriber. |

---

## 📖 How It Works in 3 Simple Steps

1. **Upload or Paste Your Leads:** Provide a list of phone numbers or paste a raw CSV export from your CRM (Apollo, HubSpot, Salesforce).
2. **Choose Platforms & Settings:** Select WhatsApp, Telegram, or both. Choose your fallback default country for national numbers without international prefixes.
3. **Download Enriched CRM File:** Export your dataset as CSV, JSON, or Excel, and import it straight back into your CRM.

---

## 📋 Sample Output Dataset

When processing a CRM lead list, all original columns are preserved alongside the enriched intelligence:

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

If an input number is invalid:
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

## ⚙️ Input Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `csvContent` | `string` | Optional | Raw CSV text or export from Apollo, HubSpot, or Salesforce. All columns are preserved in output. |
| `phoneNumbers` | `array` | Optional | List of phone numbers to validate (international or national formats). |
| `platforms` | `array` | Yes | Messaging platforms to query: `["whatsapp", "telegram"]`. |
| `defaultCountry` | `string` | No (default: `"FR"`) | Fallback two-letter ISO country code (e.g., `US`, `FR`, `GB`) for numbers missing a `+` prefix. |
| `concurrencyLimit` | `integer` | No (default: `5`) | Maximum concurrent validation workers. |
| `proxyConfiguration` | `object` | Optional | Apify Proxy settings (Residential or Datacenter). |
| `simulationMode` | `boolean` | No (default: `false`) | Test run mode to simulate verification responses without making external network calls. |

---

## 🔌 Integrations & Automation

You can easily integrate this Actor into your automated lead workflows:

- **HubSpot / Salesforce:** Export contacts, run batch validation, and re-import enriched columns.
- **Make.com & Zapier:** Trigger this Actor whenever a new lead signs up via Webhooks, and sync validated status back to your database.
- **Apify API & Python/Node.js SDK:** Trigger runs programmatically from your own backend or ETL pipelines.

---

## ❓ Frequently Asked Questions (FAQ)

#### Does this Actor preserve my existing CSV columns?
**Yes.** All columns present in your uploaded CSV (such as `First Name`, `Last Name`, `Email`, `Company`, `Custom Tags`) are preserved and returned in the exact same output record alongside the enriched phone and messaging fields.

#### What phone number formats are supported?
Any format: international standard (`+33612345678`), formatted with spaces/dashes (`+1 (415) 555-2671`), or national format without country code (`06 12 34 56 78`) by setting the `defaultCountry` parameter.

#### How does timezone and business hours detection work?
The Actor resolves the exact IANA timezone (e.g., `America/New_York`, `Europe/Paris`) from the phone country code and geographical prefix, computes current local time, and flags `isBusinessHours: true` if the local time is Monday through Friday between 9:00 AM and 6:00 PM.
