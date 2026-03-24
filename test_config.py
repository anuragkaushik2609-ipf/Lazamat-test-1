import os
import json
import asyncio
import requests
from flask import Flask, jsonify
from datetime import datetime

app = Flask(__name__)

# ─────────────────────────────────────────
# HTML PAGE — Browser mein dikhega
# ─────────────────────────────────────────

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LAMAZAT CANVAS — Config Test</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0f0f0f;
            color: #ffffff;
            padding: 20px;
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
        .env-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #222;
        }
        .env-row:last-child { border-bottom: none; }
        .env-name { color: #ccc; font-size: 14px; }
        .badge {
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        .green { background: #0d3320; color: #00e676; border: 1px solid #00e676; }
        .red { background: #3d0d0d; color: #ff5252; border: 1px solid #ff5252; }
        .yellow { background: #3d3000; color: #ffd740; border: 1px solid #ffd740; }
        .btn {
            width: 100%;
            padding: 12px;
            margin: 8px 0;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            cursor: pointer;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.85; }
        .btn-admin { background: #00d4ff; color: #000; }
        .btn-friend { background: #7c4dff; color: #fff; }
        .btn-sheet { background: #00e676; color: #000; }
        .result-box {
            background: #111;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 12px;
            margin-top: 10px;
            font-size: 13px;
            color: #aaa;
            min-height: 40px;
            display: none;
        }
        .result-box.show { display: block; }
        .success { color: #00e676; }
        .error { color: #ff5252; }
        .loading { color: #ffd740; }
        .timestamp {
            text-align: center;
            color: #444;
            font-size: 11px;
            margin-top: 20px;
        }
    </style>
</head>
<body>

    <h1>🚀 LAMAZAT CANVAS</h1>
    <p class="subtitle">Config & Environment Test Panel</p>

    <!-- Environment Variables Status -->
    <div class="section">
        <h2>🔑 Environment Variables</h2>
        <div id="env-list">Loading...</div>
    </div>

    <!-- Manual Tests -->
    <div class="section">
        <h2>🧪 Manual Tests</h2>

        <button class="btn btn-admin" onclick="testBot('admin')">
            📱 Send Test Message — Admin Bot
        </button>
        <div class="result-box" id="result-admin"></div>

        <button class="btn btn-friend" onclick="testBot('friend')">
            👥 Send Test Message — Friend Bot
        </button>
        <div class="result-box" id="result-friend"></div>

        <button class="btn btn-sheet" onclick="testSheet()">
            📊 Test Google Sheet Connection
        </button>
        <div class="result-box" id="result-sheet"></div>

    </div>

    <p class="timestamp" id="timestamp"></p>

    <script>
        // Timestamp
        document.getElementById('timestamp').textContent =
            'Page loaded: ' + new Date().toLocaleString('en-IN', {timeZone: 'Asia/Kolkata'});

        // Environment Variables fetch karo
        fetch('/check-env')
            .then(r => r.json())
            .then(data => {
                let html = '';
                data.forEach(item => {
                    let badgeClass = item.status === 'OK' ? 'green' : 'red';
                    let badgeText = item.status === 'OK' ? '✅ Set' : '❌ Missing';
                    html += `
                        <div class="env-row">
                            <span class="env-name">${item.name}</span>
                            <span class="badge ${badgeClass}">${badgeText}</span>
                        </div>
                    `;
                });
                document.getElementById('env-list').innerHTML = html;
            })
            .catch(() => {
                document.getElementById('env-list').innerHTML =
                    '<span class="error">Error loading env variables</span>';
            });

        // Bot test
        function testBot(type) {
            const resultBox = document.getElementById('result-' + type);
            resultBox.className = 'result-box show';
            resultBox.innerHTML = '<span class="loading">⏳ Sending...</span>';

            fetch('/test-bot/' + type)
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        resultBox.innerHTML = '<span class="success">✅ ' + data.message + '</span>';
                    } else {
                        resultBox.innerHTML = '<span class="error">❌ ' + data.message + '</span>';
                    }
                })
                .catch(() => {
                    resultBox.innerHTML = '<span class="error">❌ Request failed</span>';
                });
        }

        // Sheet test
        function testSheet() {
            const resultBox = document.getElementById('result-sheet');
            resultBox.className = 'result-box show';
            resultBox.innerHTML = '<span class="loading">⏳ Connecting...</span>';

            fetch('/test-sheet')
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        resultBox.innerHTML = '<span class="success">✅ ' + data.message + '</span>';
                    } else {
                        resultBox.innerHTML = '<span class="error">❌ ' + data.message + '</span>';
                    }
                })
                .catch(() => {
                    resultBox.innerHTML = '<span class="error">❌ Request failed</span>';
                });
        }
    </script>

</body>
</html>
"""

# ─────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────

@app.route("/")
def home():
    return HTML

@app.route("/check-env")
def check_env():
    variables = [
        "ADMIN_BOT_TOKEN",
        "FRIEND_BOT_TOKEN",
        "ADMIN_CHAT_ID",
        "GOOGLE_SHEET_ID",
        "GOOGLE_CREDENTIALS",
        "GROQ_API_KEY"
    ]
    result = []
    for var in variables:
        value = os.getenv(var)
        result.append({
            "name": var,
            "status": "OK" if value else "MISSING"
        })
    return jsonify(result)

@app.route("/test-bot/<bot_type>")
def test_bot(bot_type):
    try:
        if bot_type == "admin":
            token = os.getenv("ADMIN_BOT_TOKEN")
            chat_id = os.getenv("ADMIN_CHAT_ID")
            bot_name = "Admin Bot"
        elif bot_type == "friend":
            token = os.getenv("FRIEND_BOT_TOKEN")
            chat_id = os.getenv("ADMIN_CHAT_ID")
            bot_name = "Friend Bot"
        else:
            return jsonify({"success": False, "message": "Invalid bot type"})

        if not token or not chat_id:
            return jsonify({
                "success": False,
                "message": f"Token ya Chat ID missing hai — Environment Variables check karo"
            })

        # Telegram message bhejo
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": (
                f"✅ *LAMAZAT CANVAS — Test Message*\n\n"
                f"Bot: {bot_name}\n"
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Sab kuch sahi chal raha hai!"
            ),
            "parse_mode": "Markdown"
        }

        response = requests.post(url, json=payload, timeout=10)
        data = response.json()

        if data.get("ok"):
            return jsonify({
                "success": True,
                "message": f"{bot_name} se message bhej diya — Telegram check karo!"
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Telegram Error: {data.get('description', 'Unknown error')}"
            })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/test-sheet")
def test_sheet():
    try:
        import gspread
        import json
        from oauth2client.service_account import ServiceAccountCredentials

        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        credentials_json = os.getenv("GOOGLE_CREDENTIALS")

        if not sheet_id or not credentials_json:
            return jsonify({
                "success": False,
                "message": "GOOGLE_SHEET_ID ya GOOGLE_CREDENTIALS missing hai"
            })

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]

        creds_dict = json.loads(credentials_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id)
        worksheets = sheet.worksheets()
        tab_names = [ws.title for ws in worksheets]

        return jsonify({
            "success": True,
            "message": f"Sheet connected! Tabs: {', '.join(tab_names)}"
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
