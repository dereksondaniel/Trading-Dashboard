# Derek V7 Dashboard — Setup Guide

## What you're building
TradingView alerts → webhook → Railway server → mobile dashboard URL.
8 alerts total: 4 pairs (XAUUSD, EURUSD, GBPUSD, USDJPY) × 2 timeframes (15m, 1h).

---

## Step 1 — Push code to GitHub (5 min)
1. Create a new GitHub repo, e.g. `tv-dashboard`.
2. Upload these 4 files: `app.py`, `requirements.txt`, `Procfile`, `pine_webhook_additions.txt`.

## Step 2 — Deploy on Railway (5 min)
1. Go to railway.app, sign in with GitHub.
2. New Project → Deploy from GitHub repo → pick `tv-dashboard`.
3. Railway auto-detects Python and deploys.
4. Once deployed, go to **Settings → Networking → Generate Domain**.
   You'll get a URL like `https://tv-dashboard-production.up.railway.app`.
5. Go to **Variables** tab, add:
   - `WEBHOOK_SECRET` = `pick-any-long-random-string-like-Derek2026xK9`

   Copy that secret — you'll paste it into Pine in the next step.

## Step 3 — Update the Pine script (3 min)
1. Open your V7 indicator in TradingView Pine editor.
2. Paste the contents of `pine_webhook_additions.txt` near the end,
   right before the existing `// ALERTS` section.
   (Or replace the existing alertcondition block.)
3. **Find-and-replace** `REPLACE_WITH_YOUR_SECRET` with the secret you set in Railway.
4. Save and re-add the indicator to your chart.

## Step 4 — Create the alerts (10 min)
For each pair + timeframe (8 total), do this:

1. Load the pair on the chart, switch to the timeframe (15m or 1h).
2. Right-click chart → Add Alert.
3. **Condition**: `Derek Cheat Code Gold V7 Pro` → `V7 Status Update`
4. **Options**: `Once Per Bar Close`
5. **Expiration**: Open-ended (paid plans) or max allowed.
6. **Notifications tab** → enable **Webhook URL** →
   `https://YOUR-RAILWAY-URL.up.railway.app/webhook`
7. **Message**: leave as default (the Pine script already built the JSON).
8. Save.

Repeat for:
- XAUUSD 15m, XAUUSD 1h
- EURUSD 15m, EURUSD 1h
- GBPUSD 15m, GBPUSD 1h
- USDJPY 15m, USDJPY 1h

Optionally also add the 4 trade signal alerts (LONG Breakout, SHORT Breakout, LONG Reaction, SHORT Reaction) per pair if you want push notifications when something fires.

## Step 5 — View the dashboard
Open `https://YOUR-RAILWAY-URL.up.railway.app/` on your phone.
- Updates every time a candle closes on any alerted pair.
- Auto-refreshes every 30 seconds.
- Bookmark it / add to home screen.

---

## How to use it for trading
1. Glance at dashboard → see a pair showing `LONG · BREAKOUT` badge with Entry/SL/TP.
2. Confirm it on TradingView chart.
3. Place the order manually on MT5 using the displayed Entry / SL / TP levels.

## Plan limits
- TradingView **Essential** ($15/mo): 20 alerts, webhooks allowed. Enough for this setup.
- TradingView **Free**: no webhooks — you'll need Essential or above.

## Troubleshooting
- Nothing showing up? Check Railway logs (Deployments → View Logs). Most common issue: wrong secret.
- Test the webhook manually:
  ```
  curl -X POST https://YOUR-URL/webhook \
    -H "Content-Type: application/json" \
    -d '{"secret":"YOUR_SECRET","symbol":"TEST","timeframe":"15","trend":"Strong Bull","structure":"Bullish","price":1.234}'
  ```
  Then reload the dashboard — you should see a TEST card.
- `/health` endpoint confirms the server is up.
- `/signals` shows recent trade signals in JSON.

## Upgrades later
- Add PineConnector to auto-execute on MT5.
- Add multi-timeframe confluence column (show 15m + 1h side by side per pair).
- Add a Telegram bot alert when high-confluence signals fire.
