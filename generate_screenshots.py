import asyncio
import os
from playwright.async_api import async_playwright

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: #0b0f19; color: #f8fafc; padding: 25px; width: 1240px; height: 780px; overflow: hidden; }
.window { background: #111827; border-radius: 14px; border: 1px solid #1f2937; box-shadow: 0 25px 60px rgba(0,0,0,0.7); display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.titlebar { background: #0b0f19; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1f2937; }
.titlebar-left { display: flex; align-items: center; gap: 12px; font-weight: 700; font-size: 15px; }
.dots { display: flex; gap: 8px; }
.dot { width: 11px; height: 11px; border-radius: 50%; }
.dot-red { background: #ef4444; } .dot-yellow { background: #f59e0b; } .dot-green { background: #10b981; }
.main-layout { display: flex; flex: 1; overflow: hidden; }
.sidebar { width: 340px; background: #111827; border-right: 1px solid #1f2937; padding: 22px; display: flex; flex-direction: column; gap: 18px; }
.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: #9ca3af; }
.btn-qr { background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.4); color: #10b981; padding: 12px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; display: flex; align-items: center; justify-content: space-between; }
.badge-ready { background: #10b981; color: #042f1f; font-size: 11px; padding: 3px 8px; border-radius: 999px; font-weight: 800; }
.mode-toggle { background: #0b0f19; border: 1px solid #1f2937; border-radius: 8px; padding: 12px; display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 600; color: #10b981; }
.btn-upload { background: #1e293b; border: 1px dashed #374151; color: #cbd5e1; padding: 14px; border-radius: 8px; font-weight: 600; text-align: center; font-size: 13px; }
.btn-start { background: #10b981; color: #042f1f; padding: 14px; border-radius: 8px; font-weight: 800; text-align: center; font-size: 14px; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.2); }
.content { flex: 1; padding: 22px; display: flex; flex-direction: column; gap: 18px; background: #0b0f19; overflow: hidden; }
.stats-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.stat-card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 14px; text-align: center; }
.stat-val { font-size: 24px; font-weight: 800; color: #f8fafc; }
.stat-val.wa { color: #10b981; } .stat-val.tg { color: #38bdf8; } .stat-val.score { color: #f59e0b; }
.stat-lbl { font-size: 11px; color: #9ca3af; font-weight: 600; text-transform: uppercase; margin-top: 4px; }
.table-card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; flex: 1; display: flex; flex-direction: column; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left; }
th { background: #1e293b; color: #9ca3af; padding: 12px 14px; font-weight: 600; border-bottom: 1px solid #1f2937; }
td { padding: 12px 14px; border-bottom: 1px solid #1f2937; color: #e5e7eb; }
.tag-active { background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 4px 9px; border-radius: 6px; font-weight: 600; display: inline-block; }
.tag-biz { background: rgba(59, 130, 246, 0.15); color: #60a5fa; padding: 4px 9px; border-radius: 6px; font-weight: 600; display: inline-block; }
.tag-prem { background: rgba(168, 85, 247, 0.15); color: #c084fc; padding: 4px 9px; border-radius: 6px; font-weight: 600; display: inline-block; }
.tag-no { background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 4px 9px; border-radius: 6px; font-weight: 600; display: inline-block; }
.score-pill { font-weight: 800; color: #10b981; }
.bottom-bar { display: flex; justify-content: space-between; align-items: center; padding-top: 6px; }
.btn-export { background: #059669; color: white; padding: 11px 22px; border-radius: 8px; font-weight: 700; font-size: 13px; }
</style>
</head>
<body>
<div class="window">
  <div class="titlebar">
    <div class="titlebar-left">
      <div class="dots"><div class="dot dot-red"></div><div class="dot dot-yellow"></div><div class="dot dot-green"></div></div>
      <span>⚡ NumChecker — WhatsApp & Telegram Number Validator v1.0.0</span>
    </div>
    <div style="font-size: 13px; color: #94a3b8; font-weight: 500;">⚙️ Settings</div>
  </div>
  <div class="main-layout">
    <div class="sidebar">
      <div>
        <div class="section-title">WhatsApp Session Engine</div>
        <div class="btn-qr" style="margin-top: 8px;">
          <span>🔗 WhatsApp Web</span>
          <span class="badge-ready">🟢 Linked & Ready</span>
        </div>
      </div>
      <div>
        <div class="section-title">Validation Engine Mode</div>
        <div class="mode-toggle" style="margin-top: 8px;">
          <span>🟢 Live Network Mode</span>
          <span>● Active</span>
        </div>
      </div>
      <div>
        <div class="section-title">Imported Leads Dataset</div>
        <div class="btn-upload" style="margin-top: 8px;">📁 sample_apollo_leads.csv (128 contacts)</div>
      </div>
      <div style="margin-top: auto;">
        <div class="btn-start">▶ Start Batch Validation</div>
      </div>
    </div>
    <div class="content">
      <div class="stats-grid">
        <div class="stat-card"><div class="stat-val">128</div><div class="stat-lbl">Processed Leads</div></div>
        <div class="stat-card"><div class="stat-val wa">104</div><div class="stat-lbl">WhatsApp Active</div></div>
        <div class="stat-card"><div class="stat-val tg">76</div><div class="stat-lbl">Telegram Active</div></div>
        <div class="stat-card"><div class="stat-val score">88 / 100</div><div class="stat-lbl">Avg Lead Score</div></div>
      </div>
      <div class="table-card">
        <table>
          <thead>
            <tr>
              <th>Phone (E.164)</th>
              <th>Carrier</th>
              <th>WhatsApp</th>
              <th>Telegram</th>
              <th>Score</th>
              <th>Best Channel</th>
              <th>Timezone</th>
              <th>Outreach Window (TCPA)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><b>+216 53 014 175</b></td>
              <td>Orange (TN)</td>
              <td><span class="tag-active">✅ Active</span></td>
              <td><span class="tag-active">✅ Active</span></td>
              <td><span class="score-pill">95</span></td>
              <td>WhatsApp</td>
              <td>Africa/Tunis</td>
              <td>☀️ Yes (Open)</td>
            </tr>
            <tr>
              <td><b>+33 6 12 34 56 78</b></td>
              <td>SFR (FR)</td>
              <td><span class="tag-active">✅ Active</span></td>
              <td><span class="tag-prem">⭐ Premium</span></td>
              <td><span class="score-pill">95</span></td>
              <td>WhatsApp</td>
              <td>Europe/Paris</td>
              <td>☀️ Yes (Open)</td>
            </tr>
            <tr>
              <td><b>+44 7911 123456</b></td>
              <td>Vodafone (UK)</td>
              <td><span class="tag-biz">✅ Business</span></td>
              <td><span class="tag-active">✅ Active</span></td>
              <td><span class="score-pill">100</span></td>
              <td>WhatsApp</td>
              <td>Europe/London</td>
              <td>☀️ Yes (Open)</td>
            </tr>
            <tr>
              <td><b>+49 151 23456789</b></td>
              <td>Telekom (DE)</td>
              <td><span class="tag-active">✅ Active</span></td>
              <td><span class="tag-no">❌ Not on TG</span></td>
              <td><span class="score-pill">75</span></td>
              <td>WhatsApp</td>
              <td>Europe/Berlin</td>
              <td>☀️ Yes (Open)</td>
            </tr>
            <tr>
              <td><b>+1 415 555 2671</b></td>
              <td>Twilio (VoIP)</td>
              <td><span class="tag-no">❌ Not on WA</span></td>
              <td><span class="tag-no">❌ Not on TG</span></td>
              <td><span style="color:#f87171;font-weight:700;">35</span></td>
              <td>Call (VoIP)</td>
              <td>America/Los_Angeles</td>
              <td>🌙 Off-Hours</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="bottom-bar">
        <span style="font-size: 11px; color: #9ca3af; font-style: italic;">ℹ️ Outreach Window: Evaluates local time for TCPA/GDPR compliance (Mon–Fri, 9:00 AM – 6:00 PM).</span>
        <div class="btn-export">💾 Export Enriched CSV</div>
      </div>
    </div>
  </div>
</div>
</body>
</html>"""

SETTINGS_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: #0b0f19; color: #f8fafc; padding: 40px; width: 1240px; height: 780px; display: flex; align-items: center; justify-content: center; }
.modal { background: #111827; border: 1px solid #374151; border-radius: 16px; width: 680px; padding: 32px; box-shadow: 0 25px 60px rgba(0,0,0,0.8); }
.modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid #1f2937; padding-bottom: 16px; }
.modal-title { font-size: 18px; font-weight: 700; color: #fff; }
.field-group { margin-bottom: 20px; }
.field-label { font-size: 13px; font-weight: 600; color: #cbd5e1; margin-bottom: 8px; display: block; }
.field-desc { font-size: 12px; color: #9ca3af; margin-bottom: 8px; }
.input-text { width: 100%; background: #1e293b; border: 1px solid #374151; border-radius: 8px; padding: 12px; color: #fff; font-size: 13px; }
.toggle-row { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 14px 16px; border-radius: 8px; border: 1px solid #374151; }
.toggle-active { color: #10b981; font-weight: 700; font-size: 13px; }
.btn-save { background: #10b981; color: #042f1f; font-weight: 800; font-size: 14px; padding: 12px 24px; border-radius: 8px; border: none; cursor: pointer; float: right; margin-top: 10px; }
</style>
</head>
<body>
<div class="modal">
  <div class="modal-header">
    <div class="modal-title">⚙️ Validator Engine Settings</div>
    <div style="color: #9ca3af; font-size: 14px; cursor: pointer;">✕ Close</div>
  </div>

  <div class="field-group">
    <div class="toggle-row">
      <div>
        <div style="font-weight: 600; font-size: 14px;">Free WhatsApp Web Engine (0 API Costs)</div>
        <div class="field-desc" style="margin-bottom:0; margin-top:2px;">Runs headless Chromium locally using your linked phone session</div>
      </div>
      <span class="toggle-active">🟢 Active</span>
    </div>
  </div>

  <div class="field-group">
    <label class="field-label">Telegram MTProto API Configuration (Free from my.telegram.org)</label>
    <div class="field-desc">Optional: Direct connection to Telegram cloud servers with automated contact cleanup</div>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
      <input class="input-text" type="text" value="API ID: 29481048" readonly>
      <input class="input-text" type="text" value="API HASH: e4b28f9a••••••••" readonly>
    </div>
  </div>

  <div class="field-group">
    <label class="field-label">Outreach Business Hours Window</label>
    <div class="field-desc">TCPA compliance threshold: Monday–Friday 9:00 AM – 6:00 PM local lead timezone</div>
    <input class="input-text" type="text" value="Default Region: Automatic (E.164 Geolocation)" readonly>
  </div>

  <div style="clear: both;">
    <button class="btn-save">Save Configuration</button>
  </div>
</div>
</body>
</html>"""

CSV_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Inter', sans-serif; }
body { background: #0b0f19; color: #f8fafc; padding: 25px; width: 1240px; height: 780px; overflow: hidden; }
.window { background: #111827; border-radius: 14px; border: 1px solid #1f2937; box-shadow: 0 25px 60px rgba(0,0,0,0.7); display: flex; flex-direction: column; height: 100%; overflow: hidden; }
.titlebar { background: #0b0f19; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid #1f2937; }
.titlebar-left { display: flex; align-items: center; gap: 12px; font-weight: 700; font-size: 15px; }
.dots { display: flex; gap: 8px; }
.dot { width: 11px; height: 11px; border-radius: 50%; }
.dot-red { background: #ef4444; } .dot-yellow { background: #f59e0b; } .dot-green { background: #10b981; }
.content { flex: 1; padding: 28px; display: flex; flex-direction: column; gap: 20px; background: #0f172a; }
.header-box { display: flex; justify-content: space-between; align-items: center; }
.header-box h2 { font-size: 20px; font-weight: 800; color: #fff; }
.header-box p { color: #94a3b8; font-size: 13px; margin-top: 4px; }
.table-card { background: #111827; border: 1px solid #1f2937; border-radius: 10px; overflow: hidden; flex: 1; }
table { width: 100%; border-collapse: collapse; font-size: 12.5px; text-align: left; }
th { background: #1e293b; color: #9ca3af; padding: 12px 14px; font-weight: 600; border-bottom: 1px solid #1f2937; }
td { padding: 12px 14px; border-bottom: 1px solid #1f2937; color: #e5e7eb; }
.highlight-col { background: rgba(16, 185, 129, 0.05); }
.tag-active { background: rgba(16, 185, 129, 0.15); color: #34d399; padding: 4px 9px; border-radius: 6px; font-weight: 600; }
.tag-biz { background: rgba(59, 130, 246, 0.15); color: #60a5fa; padding: 4px 9px; border-radius: 6px; font-weight: 600; }
.tag-prem { background: rgba(168, 85, 247, 0.15); color: #c084fc; padding: 4px 9px; border-radius: 6px; font-weight: 600; }
.tag-no { background: rgba(239, 68, 68, 0.15); color: #f87171; padding: 4px 9px; border-radius: 6px; font-weight: 600; }
.btn-export { background: #10b981; color: #042f1f; padding: 12px 24px; border-radius: 8px; font-weight: 800; font-size: 13px; }
</style>
</head>
<body>
<div class="window">
  <div class="titlebar">
    <div class="titlebar-left">
      <div class="dots"><div class="dot dot-red"></div><div class="dot dot-yellow"></div><div class="dot dot-green"></div></div>
      <span>⚡ NumChecker — Apollo & CRM Export Passthrough Preview</span>
    </div>
  </div>
  <div class="content">
    <div class="header-box">
      <div>
        <h2>Full CRM Columns Preserved + Messaging Enrichment Appended</h2>
        <p>Your Apollo IDs, First Names, Company Names, and Emails remain 100% intact ready for re-import.</p>
      </div>
      <div class="btn-export">💾 Download Enriched CRM CSV</div>
    </div>
    <div class="table-card">
      <table>
        <thead>
          <tr>
            <th>First Name</th>
            <th>Company</th>
            <th>Apollo Email</th>
            <th>Original Phone</th>
            <th class="highlight-col">WhatsApp Status</th>
            <th class="highlight-col">Telegram Status</th>
            <th class="highlight-col">Carrier Brand</th>
            <th class="highlight-col">Lead Score</th>
            <th class="highlight-col">Safe Outreach Window</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><b>Alex</b></td>
            <td>Stripe Partner Inc</td>
            <td>alex@stripepartner.io</td>
            <td>+44 7911 123456</td>
            <td class="highlight-col"><span class="tag-biz">✅ Business</span></td>
            <td class="highlight-col"><span class="tag-active">✅ Active</span></td>
            <td class="highlight-col">Vodafone UK</td>
            <td class="highlight-col"><b style="color:#10b981;">100 / 100</b></td>
            <td class="highlight-col">☀️ 2:30 PM (Open)</td>
          </tr>
          <tr>
            <td><b>Sarah</b></td>
            <td>GrowthScale Media</td>
            <td>sarah@growthscale.co</td>
            <td>+33 6 12 34 56 78</td>
            <td class="highlight-col"><span class="tag-active">✅ Active</span></td>
            <td class="highlight-col"><span class="tag-prem">⭐ Premium</span></td>
            <td class="highlight-col">SFR France</td>
            <td class="highlight-col"><b style="color:#10b981;">95 / 100</b></td>
            <td class="highlight-col">☀️ 3:30 PM (Open)</td>
          </tr>
          <tr>
            <td><b>Karim</b></td>
            <td>NorthTech Labs</td>
            <td>karim@northtech.tn</td>
            <td>+216 53 014 175</td>
            <td class="highlight-col"><span class="tag-active">✅ Active</span></td>
            <td class="highlight-col"><span class="tag-active">✅ Active</span></td>
            <td class="highlight-col">Orange Tunisia</td>
            <td class="highlight-col"><b style="color:#10b981;">95 / 100</b></td>
            <td class="highlight-col">☀️ 3:30 PM (Open)</td>
          </tr>
          <tr>
            <td><b>David</b></td>
            <td>Apex Cold Dialing</td>
            <td>david@apexdial.com</td>
            <td>+1 415 555 2671</td>
            <td class="highlight-col"><span class="tag-no">❌ Not on WA</span></td>
            <td class="highlight-col"><span class="tag-no">❌ Not on TG</span></td>
            <td class="highlight-col">Twilio (VoIP)</td>
            <td class="highlight-col"><b style="color:#f87171;">35 / 100</b></td>
            <td class="highlight-col">🌙 6:30 AM (Off-Hours)</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
</body>
</html>"""

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="chrome")
        page = await browser.new_page(viewport={'width': 1240, 'height': 780})
        
        # 1. Screenshot Dashboard
        await page.set_content(DASHBOARD_HTML)
        await page.screenshot(path='appsumo_screenshot_1_dashboard.png')
        print('[+] Generated appsumo_screenshot_1_dashboard.png')

        # 2. Screenshot Settings
        await page.set_content(SETTINGS_HTML)
        await page.screenshot(path='appsumo_screenshot_2_settings.png')
        print('[+] Generated appsumo_screenshot_2_settings.png')

        # 3. Screenshot CRM Enrichment
        await page.set_content(CSV_HTML)
        await page.screenshot(path='appsumo_screenshot_3_crm_enrichment.png')
        print('[+] Generated appsumo_screenshot_3_crm_enrichment.png')

        await browser.close()

asyncio.run(run())

