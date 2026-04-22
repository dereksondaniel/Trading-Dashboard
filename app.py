"""
Derek V7 TradingView Dashboard
- Receives webhooks from TradingView alerts
- Stores latest state per (symbol, timeframe) in SQLite
- Serves a mobile-friendly dashboard at /
"""
import os
import json
import sqlite3
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)

SECRET = os.environ.get("WEBHOOK_SECRET", "CHANGE_ME")
DB_PATH = os.environ.get("DB_PATH", "/tmp/tv_dashboard.db")

# ---------- DB ----------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS state (
                symbol TEXT,
                timeframe TEXT,
                payload TEXT,
                updated_at TEXT,
                PRIMARY KEY (symbol, timeframe)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT, timeframe TEXT, side TEXT, type TEXT,
                price REAL, created_at TEXT
            )
        """)

init_db()

# ---------- Webhook ----------
@app.route("/webhook", methods=["POST"])
def webhook():
    # TradingView sends raw body — parse manually in case content-type isn't JSON
    try:
        data = request.get_json(force=True, silent=True) or json.loads(request.data)
    except Exception:
        return jsonify(error="bad json"), 400

    if data.get("secret") != SECRET:
        abort(401)

    symbol = data.get("symbol", "UNKNOWN")
    tf = data.get("timeframe", "?")
    now = datetime.now(timezone.utc).isoformat()

    with db() as c:
        # Always update the latest state snapshot
        c.execute("""
            INSERT INTO state (symbol, timeframe, payload, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(symbol, timeframe) DO UPDATE SET
                payload=excluded.payload, updated_at=excluded.updated_at
        """, (symbol, tf, json.dumps(data), now))

        # Log discrete trade signals separately
        if data.get("type") in ("BREAKOUT", "REACTION"):
            c.execute("""
                INSERT INTO signals (symbol, timeframe, side, type, price, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (symbol, tf, data.get("side"), data.get("type"),
                  data.get("price"), now))

    return jsonify(ok=True)

# ---------- Dashboard ----------
DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Derek V7 Dashboard</title>
<style>
  :root { color-scheme: dark; }
  body { font-family: -apple-system, system-ui, sans-serif; background:#0e0e10; color:#eee; margin:0; padding:12px; }
  h1 { font-size:18px; margin:0 0 4px; }
  .sub { color:#888; font-size:12px; margin-bottom:12px; }
  .card { background:#1a1a1f; border-radius:10px; padding:12px; margin-bottom:10px; border-left:4px solid #444; }
  .card.long  { border-left-color:#16a34a; }
  .card.short { border-left-color:#dc2626; }
  .row { display:flex; justify-content:space-between; align-items:center; margin:4px 0; font-size:13px; }
  .sym { font-weight:600; font-size:16px; }
  .tf { color:#888; font-size:12px; margin-left:6px; }
  .badge { padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
  .bull { background:#16a34a; color:#fff; }
  .bear { background:#dc2626; color:#fff; }
  .neutral { background:#444; color:#ccc; }
  .signal { background:#2563eb; color:#fff; }
  .prices { display:grid; grid-template-columns: 1fr 1fr 1fr; gap:6px; margin-top:8px; font-size:12px; }
  .price-box { background:#0e0e10; padding:6px; border-radius:6px; text-align:center; }
  .price-box .label { color:#888; font-size:10px; text-transform:uppercase; }
  .price-box .val { font-weight:600; font-size:13px; }
  .entry .val { color:#3b82f6; }
  .sl .val { color:#dc2626; }
  .tp .val { color:#16a34a; }
  .stale { opacity:0.5; }
  .empty { text-align:center; color:#666; padding:40px 0; }
  .refresh { position:fixed; bottom:16px; right:16px; background:#2563eb; color:#fff;
             padding:10px 14px; border-radius:50px; text-decoration:none; font-size:13px; }
</style>
</head>
<body>
<h1>Derek V7 — Live Dashboard</h1>
<div class="sub">Last refresh: {{ now }} · auto-reloads every 30s</div>

{% if not rows %}
  <div class="empty">No data yet. Fire a TradingView alert to populate.</div>
{% endif %}

{% for r in rows %}
  {% set p = r.data %}
  {% set side_class = 'long' if p.get('side') == 'LONG' or p.get('trend','').startswith('Strong Bull') or p.get('trend','').startswith('Weak Bull')
                     else 'short' if p.get('side') == 'SHORT' or p.get('trend','').startswith('Strong Bear') or p.get('trend','').startswith('Weak Bear')
                     else '' %}
  <div class="card {{ side_class }} {{ 'stale' if r.stale }}">
    <div class="row">
      <div>
        <span class="sym">{{ p.get('symbol','?') }}</span>
        <span class="tf">{{ p.get('timeframe','?') }}</span>
      </div>
      <div>
        {% if p.get('type') in ['BREAKOUT','REACTION'] %}
          <span class="badge signal">{{ p.get('side') }} · {{ p.get('type') }}</span>
        {% else %}
          <span class="badge {{ 'bull' if 'Bull' in p.get('trend','') else 'bear' if 'Bear' in p.get('trend','') else 'neutral' }}">
            {{ p.get('trend','?') }}
          </span>
        {% endif %}
      </div>
    </div>

    <div class="row">
      <span style="color:#888">Structure</span>
      <span>{{ p.get('structure','?') }} · Swing {{ p.get('swing','?') }}</span>
    </div>
    <div class="row">
      <span style="color:#888">Zone / Reaction</span>
      <span>{{ p.get('zone','?') }} · {{ p.get('reaction','NONE') }}</span>
    </div>
    <div class="row">
      <span style="color:#888">BOS / CHoCH</span>
      <span>{{ p.get('bos','None') }} · {{ p.get('choch','None') }}</span>
    </div>
    <div class="row">
      <span style="color:#888">ATR / Session</span>
      <span>{{ p.get('atr_state','?') }} · {{ p.get('session','?') }}</span>
    </div>

    {% if p.get('entry') and p.get('sl') and p.get('tp') %}
    <div class="prices">
      <div class="price-box entry"><div class="label">Entry</div><div class="val">{{ p.entry }}</div></div>
      <div class="price-box sl"><div class="label">SL</div><div class="val">{{ p.sl }}</div></div>
      <div class="price-box tp"><div class="label">TP ({{ p.get('rr','?') }}R)</div><div class="val">{{ p.tp }}</div></div>
    </div>
    {% endif %}

    <div class="row" style="margin-top:6px;">
      <span style="color:#666;font-size:11px;">Price {{ p.get('price','?') }}</span>
      <span style="color:#666;font-size:11px;">{{ r.age }}</span>
    </div>
  </div>
{% endfor %}

<a class="refresh" href="/">Refresh</a>
<script>setTimeout(()=>location.reload(), 30000);</script>
</body>
</html>
"""

def humanize_age(iso_ts):
    try:
        then = datetime.fromisoformat(iso_ts)
        delta = datetime.now(timezone.utc) - then
        s = int(delta.total_seconds())
        if s < 60: return f"{s}s ago"
        if s < 3600: return f"{s//60}m ago"
        if s < 86400: return f"{s//3600}h ago"
        return f"{s//86400}d ago"
    except Exception:
        return "?"

@app.route("/")
def dashboard():
    with db() as c:
        rs = c.execute("""
            SELECT symbol, timeframe, payload, updated_at FROM state
            ORDER BY
              CASE timeframe WHEN '15' THEN 1 WHEN '60' THEN 2 ELSE 3 END,
              symbol
        """).fetchall()

    rows = []
    for r in rs:
        try:
            p = json.loads(r["payload"])
        except Exception:
            p = {}
        age_secs = (datetime.now(timezone.utc) - datetime.fromisoformat(r["updated_at"])).total_seconds()
        rows.append({
            "data": p,
            "age": humanize_age(r["updated_at"]),
            "stale": age_secs > 7200,  # >2h = stale
        })

    return render_template_string(DASHBOARD_HTML,
                                  rows=rows,
                                  now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

@app.route("/signals")
def signals():
    with db() as c:
        rs = c.execute("""
            SELECT * FROM signals ORDER BY id DESC LIMIT 50
        """).fetchall()
    return jsonify([dict(r) for r in rs])

@app.route("/health")
def health():
    return jsonify(ok=True, time=datetime.now(timezone.utc).isoformat())

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
