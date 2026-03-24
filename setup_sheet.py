import os
import json
import gspread
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, jsonify

app = Flask(__name__)

# ─────────────────────────────────────────
# HTML PAGE
# ─────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAMAZAT CANVAS — Sheet Setup</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #ffffff;
            padding: 20px;
            max-width: 600px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            color: #00d4ff;
            margin-bottom: 5px;
            font-size: 24px;
        }
        .subtitle {
            text-align: center;
            color: #888;
            margin-bottom: 30px;
            font-size: 13px;
        }
        .section {
            background: #1a1a1a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid #2a2a2a;
        }
        .section h2 {
            color: #00d4ff;
            margin-bottom: 15px;
            font-size: 16px;
            border-bottom: 1px solid #2a2a2a;
            padding-bottom: 10px;
        }
        .btn {
            width: 100%;
            padding: 14px;
            margin: 8px 0;
            border: none;
            border-radius: 8px;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.85; }
        .btn:disabled { opacity: 0.4; cursor: not-allowed; }
        .btn-setup { background: #00e676; color: #000; }
        .log-box {
            background: #111;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
            font-size: 13px;
            min-height: 60px;
            line-height: 1.8;
        }
        .success { color: #00e676; }
        .error { color: #ff5252; }
        .loading { color: #ffd740; }
        .info { color: #00d4ff; }
        .step { color: #aaa; }
        .warning {
            background: #3d3000;
            border: 1px solid #ffd740;
            border-radius: 8px;
            padding: 12px;
            color: #ffd740;
            font-size: 13px;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>

    <h1>🚀 LAMAZAT CANVAS</h1>
    <p class="subtitle">Google Sheet Auto Setup</p>

    <div class="section">
        <h2>📊 Sheet Setup</h2>

        <div class="warning">
            ⚠️ Ye script ek baar chalao — dobara chalane pe purana data overwrite ho sakta hai!
        </div>

        <button class="btn btn-setup" onclick="runSetup()" id="setup-btn">
            ▶️ Sheet Setup Shuru Karo
        </button>

        <div class="log-box" id="log-box">
            Button dabao — setup shuru hoga...
        </div>
    </div>

</body>
<script>
    function addLog(message, type) {
        const box = document.getElementById('log-box');
        const line = document.createElement('div');
        line.className = type || 'step';
        line.textContent = message;
        if (box.textContent === 'Button dabao — setup shuru hoga...') {
            box.innerHTML = '';
        }
        box.appendChild(line);
        box.scrollTop = box.scrollHeight;
    }

    function runSetup() {
        const btn = document.getElementById('setup-btn');
        btn.disabled = true;
        btn.textContent = '⏳ Setup chal raha hai...';

        addLog('⏳ Setup shuru ho raha hai...', 'loading');

        fetch('/run-setup')
            .then(r => r.json())
            .then(data => {
                data.logs.forEach(log => {
                    addLog(log.message, log.type);
                });

                if (data.success) {
                    btn.textContent = '✅ Setup Complete!';
                    btn.style.background = '#00e676';
                } else {
                    btn.disabled = false;
                    btn.textContent = '▶️ Dobara Try Karo';
                }
            })
            .catch(err => {
                addLog('❌ Request failed: ' + err, 'error');
                btn.disabled = false;
                btn.textContent = '▶️ Dobara Try Karo';
            });
    }
</script>
</html>
"""

# ─────────────────────────────────────────
# SHEET SETUP DATA
# ─────────────────────────────────────────

TABS = {
    "Products": [
        "product_id", "name", "category", "type", "score",
        "cj_video_url", "price_eur", "supplier",
        "signal_1", "signal_2", "signal_3", "signal_4", "signal_5",
        "days_in_pool", "status", "last_checked", "source"
    ],
    "Test Section": [
        "product_id", "name", "category", "type", "score",
        "cj_video_url", "price_eur", "supplier",
        "signal_1", "signal_2", "signal_3", "signal_4", "signal_5",
        "days_in_pool", "status", "last_checked", "source",
        "test_start_date", "test_end_date", "performance"
    ],
    "Schedule": [
        "product_id", "video_file_id", "product_name",
        "platform", "scheduled_time", "status", "posted_at"
    ],
    "API Tracker": [
        "api_name", "daily_limit", "used_today", "last_reset", "alert_sent"
    ],
    "Logs": [
        "timestamp", "action", "details", "status"
    ],
    "Automation Flag": [
        "flag_name", "status", "started_at", "stop_until"
    ]
}

API_TRACKER_DATA = [
    ["CJ Dropshipping", 1000, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["YouTube Data API", 10000, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["Groq API", 14400, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["Google Sheets API", 500, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["Instagram Playwright", 1000, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["TikTok Playwright", 2000, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
    ["Brevo Email", 300, 0, datetime.now().strftime("%Y-%m-%d"), "No"],
]

AUTOMATION_FLAG_DATA = [
    ["Automation1", "Running", datetime.now().strftime("%Y-%m-%d %H:%M"), ""],
    ["Automation2", "Running", datetime.now().strftime("%Y-%m-%d %H:%M"), ""],
    ["FilterBot", "Running", datetime.now().strftime("%Y-%m-%d %H:%M"), ""],
]

# ─────────────────────────────────────────
# SETUP LOGIC
# ─────────────────────────────────────────

def connect_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    creds_dict = json.loads(creds_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id)

def run_setup_logic():
    logs = []

    try:
        # Sheet connect karo
        logs.append({"message": "📡 Google Sheet se connect ho raha hai...", "type": "loading"})
        sheet = connect_sheet()
        logs.append({"message": "✅ Sheet connected!", "type": "success"})

        # Existing tabs fetch karo
        existing_tabs = [ws.title for ws in sheet.worksheets()]
        logs.append({"message": f"📋 Existing tabs: {', '.join(existing_tabs)}", "type": "info"})

        # Har tab check karo — nahi hai toh banao
        for tab_name, headers in TABS.items():
            if tab_name not in existing_tabs:
                worksheet = sheet.add_worksheet(title=tab_name, rows=1000, cols=len(headers) + 2)
                logs.append({"message": f"✅ Tab banaya: {tab_name}", "type": "success"})
            else:
                worksheet = sheet.worksheet(tab_name)
                logs.append({"message": f"ℹ️ Tab already hai: {tab_name}", "type": "info"})

            # Headers daalo — Row 1
            worksheet.update('A1', [headers])
            logs.append({"message": f"✅ Headers daale: {tab_name}", "type": "success"})

        # API Tracker data daalo
        api_tab = sheet.worksheet("API Tracker")
        for row in API_TRACKER_DATA:
            api_tab.append_row(row)
        logs.append({"message": "✅ API Tracker data daala!", "type": "success"})

        # Automation Flag data daalo
        flag_tab = sheet.worksheet("Automation Flag")
        for row in AUTOMATION_FLAG_DATA:
            flag_tab.append_row(row)
        logs.append({"message": "✅ Automation Flag data daala!", "type": "success"})

        # Default tab delete karo agar "Sheet1" hai
        try:
            default = sheet.worksheet("Sheet1")
            sheet.del_worksheet(default)
            logs.append({"message": "🗑 Default Sheet1 hataya!", "type": "info"})
        except:
            pass

        logs.append({"message": "🎉 Setup complete! Ab bots deploy kar sakte ho.", "type": "success"})
        return {"success": True, "logs": logs}

    except Exception as e:
        logs.append({"message": f"❌ Error: {str(e)}", "type": "error"})
        return {"success": False, "logs": logs}

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/")
def home():
    return HTML

@app.route("/run-setup")
def run_setup():
    result = run_setup_logic()
    return jsonify(result)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
