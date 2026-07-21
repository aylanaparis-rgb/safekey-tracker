import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
from flask import Flask, render_template_string, request, jsonify, session, redirect, url_for
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from geopy.distance import geodesic

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mesh-app-secure-dev-key-101')

DB_FILE = "safekey.db"

STOREFRONT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SafeKey Privacy Tracker</title>
    <style>
        :root { --bg: #0f172a; --card: #1e293b; --accent: #3b82f6; --text: #f8fafc; --muted: #94a3b8; --success: #10b981; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; text-align: center; }
        .hero { max-width: 600px; margin: 40px auto; padding: 20px; }
        h1 { font-size: 2.5rem; margin-bottom: 10px; color: #fff; }
        p { color: var(--muted); font-size: 1.1rem; line-height: 1.6; }
        .grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; max-width: 900px; margin: 40px auto; }
        .feature-card, .price-card { background: var(--card); padding: 25px; border-radius: 16px; width: 280px; text-align: left; box-shadow: 0 4px 15px rgba(0,0,0,0.2); box-sizing: border-box; }
        .price-card { border: 2px solid var(--accent); text-align: center; }
        .price { font-size: 2rem; font-weight: bold; color: #fff; margin: 15px 0; }
        .btn { display: block; background: var(--accent); color: white; border: none; padding: 14px; border-radius: 8px; cursor: pointer; text-decoration: none; font-size: 16px; font-weight: bold; margin-top: 15px; text-align: center; }
        .btn:hover { background: #2563eb; }
        .btn-success { background: var(--success); }
        .btn-success:hover { background: #059669; }
        .btn-outline { background: transparent; border: 2px solid var(--muted); color: var(--text); }
        .btn-outline:hover { background: rgba(255,255,255,0.05); }
        .console-container { max-width: 450px; margin: auto; background: var(--card); padding: 25px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); box-sizing: border-box; }
        input[type="text"] { width: 100%; padding: 12px; margin: 15px 0; border-radius: 8px; border: 1px solid #475569; background: #334155; color: #fff; text-align: center; font-size: 16px; box-sizing: border-box; }
        .status-box { background: #334155; padding: 15px; border-radius: 8px; text-align: left; margin: 20px 0; border-left: 5px solid var(--accent); }
        .badge { background: rgba(59, 130, 246, 0.2); color: var(--accent); padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
        .error { color: #f87171; font-size: 14px; margin-top: 10px; }
    </style>
</head>
<body>
    {% if view == 'landing' %}
        <div class="hero">
            <span class="badge">Privacy-Focused Hardware Tracking</span>
            <h1>Lose your keys,<br>Not your identity.</h1>
            <p>SafeKey maps and isolates your home protection keys securely.</p>
            <a href="/login" class="btn btn-outline" style="display:inline-block; padding: 10px 25px;">Existing User Console →</a>
        </div>
        <div class="grid">
            <div class="price-card">
                <h3>Full Access Token</h3>
                <div class="price">$9.99 / year</div>
                <form action="/api/create-checkout-session" method="POST">
                    <input type="text" name="customer_email" placeholder="your-email@example.com" required autocomplete="off">
                    <button type="submit" class="btn btn-success">Purchase Access Token</button>
                </form>
            </div>
        </div>
    {% elif view == 'login' %}
        <div class="console-container" style="margin-top: 60px;">
            <h2>🔑 Unlock Console</h2>
            <form method="POST" action="/login">
                <input type="text" name="license_key" placeholder="SAFEKEY-XXXX-XXXX" required autocomplete="off">
                <button type="submit" class="btn">Access Dashboard</button>
            </form>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
            <br>
            <a href="/" style="color: var(--muted); text-decoration: none; font-size: 14px;">← Back to Homepage</a>
        </div>
    {% elif view == 'dashboard' %}
        <div class="console-container" style="margin-top: 40px;">
            <h2>📡 Tracking Management</h2>
            <p style="color: var(--muted);">Profile: {{ email }}</p>
            <div class="status-box">
                <p><b>Tracking Proximity:</b> <span id="status-text">Awaiting GPS Authorization...</span></p>
                <p><b>Boundary Displacement:</b> <span id="distance-text">Calculating...</span></p>
            </div>
            <button class="btn btn-success" onclick="updateLocation()">🔄 Check Key Proximity</button>
            <br><br>
            <a href="/logout" style="color: var(--muted); text-decoration: none; font-size: 14px;">Disconnect Console</a>
        </div>
        <script>
        function updateLocation() {
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(sendLocation, locError);
            }
        }
        function sendLocation(position) {
            fetch('/api/update-proximity', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ lat: position.coords.latitude, lon: position.coords.longitude })
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('status-text').innerText = data.status_message;
                document.getElementById('distance-text').innerText = data.distance;
            });
        }
        function locError(error) { document.getElementById('status-text').innerText = "Fault: Permissions denied."; }
        window.onload = updateLocation;
        </script>
    {% endif %}
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS licenses (license_key TEXT PRIMARY KEY, email TEXT, role TEXT, expires_at TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS safe_zones (email TEXT PRIMARY KEY, home_lat REAL, home_lon REAL)')
    cursor.execute("SELECT 1 FROM licenses WHERE license_key = 'SECURE_MESH_PASSPHRASE_77'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO licenses VALUES (?,?,?,?)", ("SECURE_MESH_PASSPHRASE_77", "aylanaparis@penguin", "admin", "9999-12-31 23:59:59"))
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template_string(STOREFRONT_TEMPLATE, view='landing', error=None)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        input_key = request.form.get('license_key', '').strip()
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT email, role, expires_at FROM licenses WHERE license_key = ?", (input_key,))
        record = cursor.fetchone()
        conn.close()
        if record:
            email, role, expires_str = record
            session['is_logged_in'] = True
            session['role'] = role
            session['user_email'] = email
            return render_template_string(STOREFRONT_TEMPLATE, view='dashboard', email=email, role=role)
        return render_template_string(STOREFRONT_TEMPLATE, view='login', error="Invalid key.")
    return render_template_string(STOREFRONT_TEMPLATE, view='login', error=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/api/update-proximity', methods=['POST'])

# --- AUTOMATED EMAIL ENGINE ---
def send_lost_key_alert(recipient_email):
    """Sends an immediate privacy-first email notification to the customer's phone."""
    sender_email = "alerts@yourdomain.com" 
    sender_password = "your-app-password"   # Use an App Password, never your raw password
    
    msg = MIMEText(
        f"🚨 ALERT: Your SafeKey tracking boundary has been breached. "
        f"Our system detects that your tracked house keys are no longer inside your Safe Home Zone. "
        f"Log into your secure console wrapper at https://127.0.0 to track proximity vectors."
    )
    msg['Subject'] = '⚠️ SafeKey Tracking Breach Alert!'
    msg['From'] = sender_email
    msg['To'] = recipient_email

    try:
        # Connect securely to standard out-bound mail server relays (Port 587 for TLS encryption)
        with smtplib.SMTP('://gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f" [ALERT] Secure notification delivered to {recipient_email}")
    except Exception as e:
        print(f" [ALERT ERROR] Email relay failed: {e}")

# --- UPDATED PROXIMITY ENDPOINT ---
@app.route('/api/update-proximity', methods=['POST'])
def update_proximity():
    if not session.get('is_logged_in'): 
        return jsonify({"error": "Unauthorized"}), 401
        
    data = request.get_json() or {}
    lat, lon, email = data.get('lat'), data.get('lon'), session.get('user_email')
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT home_lat, home_lon FROM safe_zones WHERE email = ?", (email,))
    zone = cursor.fetchone()
    
    if not zone:
        cursor.execute("INSERT INTO safe_zones VALUES (?,?,?)", (email, lat, lon))
        conn.commit()
        conn.close()
        return jsonify({"status_message": "Safe Zone established!", "distance": "0.0 meters"})
        
    conn.close()
    
    distance = geodesic((zone[0], zone[1]), (lat, lon)).meters
    
    if distance > 30:
        status = "⚠️ Key Out of Bounds! Tracking Alert Active."
        # Trigger the automated email pipeline!
        send_lost_key_alert(email)
    else:
        status = "🟢 Keys Secure."
        
    return jsonify({"status_message": status, "distance": f"{round(distance, 1)} meters away"})

def update_proximity():
    if not session.get('is_logged_in'): return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json() or {}
    lat, lon, email = data.get('lat'), data.get('lon'), session.get('user_email')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT home_lat, home_lon FROM safe_zones WHERE email = ?", (email,))
    zone = cursor.fetchone()
    if not zone:
        cursor.execute("INSERT INTO safe_zones VALUES (?,?,?)", (email, lat, lon))
        conn.commit()
        conn.close()
        return jsonify({"status_message": "Safe Zone established!", "distance": "0.0 meters"})
    conn.close()
    distance = geodesic((zone[0], zone[1]), (lat, lon)).meters
    status = "⚠️ Key Out of Bounds!" if distance > 30 else "🟢 Keys Secure."
    return jsonify({"status_message": status, "distance": f"{round(distance, 1)} meters away"})

@app.route('/api/create-checkout-session', methods=['POST'])
def checkout_session():
    buyer_email = request.form.get('customer_email', '').strip()
    new_key = f"SAFEKEY-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    expiry_time = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO licenses VALUES (?,?,?,?)", (new_key, buyer_email, "user", expiry_time))
    conn.commit()
    conn.close()
    return f"<h1>Success! Your Key is: {new_key}</h1><br><a href='/login'>Go Login</a>"

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host='0.0.0.0', port=port)
