# WhatsApp & Telegram Number Checker (CRM Lead Validator)
### Standalone Windows Desktop Software & Full Python Source Code

Thank you for purchasing **WhatsApp & Telegram Number Checker**! This documentation covers everything you need to run, configure, and get the most out of the software.

---

## 🌟 Overview & Features

- **Double-Click Standalone Software (.exe):** Runs natively on Windows 10/11 without needing Python or external dependencies.
- **2-in-1 Dual Platform Validation:** Concurrently checks account registration for both **WhatsApp** (Regular & Business) and **Telegram** (Username & Telegram Premium).
- **Full CRM CSV Passthrough:** Upload lead exports from Apollo.io, HubSpot, Salesforce, or Google Sheets. The software retains all your original columns (`First Name`, `Company`, `Email`, `Custom Tags`) and appends the enriched data directly to each row.
- **0–100 Lead Quality Scoring:** Instant composite deliverability score and channel recommendation (`WhatsApp`, `Telegram`, `SMS`, `Email`).
- **Timezone & Safe-to-Contact Hours:** Resolves local IANA timezones and flags whether it is currently working hours (Monday–Friday 9:00 AM – 6:00 PM local time).
- **Google libphonenumber Standardization:** Converts numbers to E.164 (`+14155552671`) and detects carrier brands (Orange, Verizon, Vodafone) and line types (`Mobile`, `Fixed Line`, `VoIP`, `Toll Free`).
- **1-Click Clean CSV Export:** Export enriched leads directly back into CSV format ready for your CRM.

---

## 💻 System Requirements

- **Operating System:** Windows 10 or Windows 11 (64-bit)
- **RAM:** 2 GB minimum (4 GB recommended)
- **Disk Space:** 150 MB

---

## 🚀 Quick Start Guide (Using the .exe)

1. Open the `dist/` folder and double-click:
   ```text
   WhatsApp_Telegram_Validator.exe
   ```
2. **Connect WhatsApp (100% Free):**
   - Click the **"🔗 Link WhatsApp (Scan QR)"** button on the left panel.
   - A browser window opens to `web.whatsapp.com`. Open WhatsApp on your phone (`Settings` > `Linked Devices` > `Link a Device`) and scan the QR code once.
   - Once connected, your status badge turns **🟢 Linked & Ready**! Session data is saved locally on your computer.
3. **Choose Validation Mode:**
   - **🟢 Live Verification Mode:** Performs real-time checks directly against WhatsApp & Telegram networks.
   - **🧪 Offline Demo Mode:** Tests phone formatting, carrier brand, VoIP lines, timezones, and lead scores locally with zero network calls.
4. **Choose your input:**
   - **Upload CSV:** Click **"Choose CSV / File..."** and select your lead file (a sample file `sample_apollo_leads.csv` is provided in your package).
   - **Paste Numbers:** Click the "Paste Numbers" tab to paste raw phone numbers directly.
5. Select platforms to validate (**WhatsApp**, **Telegram**, or both).
6. Set your default country fallback (e.g., `US (+1)`, `FR (+33)`).
7. Click **▶ Start Validation**.
8. Watch the live progress bar, KPI stat cards, and results table update in real-time.
9. Click **💾 Export Enriched CSV** to save your clean, validated leads!

---

## ⚙️ Settings & Configuration

Click the **⚙️ Settings** button in the top-right corner to customize your setup:

### 1. Free WhatsApp Web Engine (QR Scan - Recommended)
- Zero Meta Graph API keys or monthly subscriptions needed. Scan once and validate unlimited numbers for free.

### 2. Live WhatsApp Cloud API (Optional Alternative)
- If you prefer the official Meta Graph API, enter your **WhatsApp Access Token** and **Phone Number ID**.

### 3. Live Telegram MTProto API (Optional)
- Enter your **Telegram API ID** and **API Hash** (obtained for free in 30 seconds from [my.telegram.org](https://my.telegram.org)) to perform direct live contact resolution with automated address-book cleanup.

---

## 📋 Data Fields Reference

| Column Header | Description |
| :--- | :--- |
| `First Name, Company, ...` | All original input columns preserved intact |
| `e164` | Standardized international phone number format |
| `carrier` | Carrier brand (e.g., T-Mobile, Orange) or line type (`Mobile`, `Fixed Line`, `VoIP`) |
| `leadQualityScore` | 0–100 composite deliverability score |
| `recommendedChannel` | Primary recommended outreach channel (`WhatsApp`, `Telegram`, `SMS / Phone`, `Email Only`) |
| `riskLevel` | Risk classification (`Low`, `Medium / VoIP`, `High`, `Invalid`) |
| `timezone` | Lead's local IANA timezone (e.g. `America/New_York`) |
| `localTime` | Current local time in lead's location |
| `isBusinessHours` | Safe to contact now: `true` / `false` |
| `whatsapp` | Registered status (`true` / `false`) and account type (`business` / `regular`) |
| `telegram` | Registered status (`true` / `false`), `@username`, and `isPremium` |
| `verifiedAt` | UTC timestamp of verification |

---

## 🛠️ Developer Source Code & Compiling

If you purchased the Developer License and wish to modify the Python code:

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
pip install customtkinter pyinstaller pillow
```

### 2. Run from Source
```powershell
python app_gui.py
```

### 3. Recompile into Standalone .exe
```powershell
python build_exe.py
```
The newly compiled executable will appear in `dist/WhatsApp_Telegram_Validator.exe`.

---

## 🤝 Support & Updates

If you have any questions or need custom feature additions, please contact us via the Envato / CodeCanyon author profile.
