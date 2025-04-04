from flask import Flask, request
import requests
import logging
import re

app = Flask(__name__)

# Deribit API credentials
DERIBIT_CLIENT_ID = "zDMGWs4t"
DERIBIT_CLIENT_SECRET = "gA2H5m8hIfwS-cboRsDLhdqGBTalmtsfgvlYOgWAajo"
TICKER = "BTC-PERPETUAL"

# Logging configuratie
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("webhook.log"),
        logging.StreamHandler()
    ]
)

# Haal access token op via Deribit
def get_deribit_access_token():
    url = "https://www.deribit.com/api/v2/public/auth"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": DERIBIT_CLIENT_ID,
        "client_secret": DERIBIT_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        logging.error("Fout bij ophalen access token: %s", response.text)
        return None
    return response.json().get("result", {}).get("access_token")

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.content_type == 'application/json':
        data = request.get_json()
        message = data.get("message", "")
    elif request.content_type == 'text/plain':
        message = request.data.decode('utf-8')
    else:
        return {"message": "Unsupported content type", "status": "error"}, 415

    logging.info("Ontvangen bericht: %s", message)

    # Extract position size
    match = re.search(r"New strategy position is (-?\d+)", message)
    if not match:
        logging.error("Kon positie niet bepalen uit het bericht.")
        return {"message": "Geen geldige positie gevonden", "status": "error"}, 400

    position_size = int(match.group(1))
    access_token = get_deribit_access_token()
    if not access_token:
        return {"message": "Geen access token", "status": "error"}, 500

    headers = {"Authorization": f"Bearer {access_token}"}

    if position_size == 0:
        logging.info("🛑 Sluit positie")
        close_url = "https://www.deribit.com/api/v2/private/close_position"
        close_params = {"instrument_name": TICKER, "type": "market"}
        response = requests.post(close_url, json=close_params, headers=headers)
        logging.info("Close response: %s", response.json())
    elif position_size > 0:
        logging.info(f"🟢 Open LONG voor {position_size}")
        buy_url = "https://www.deribit.com/api/v2/private/buy"
        buy_params = {
            "instrument_name": TICKER,
            "amount": position_size,
            "type": "market"
        }
        response = requests.post(buy_url, json=buy_params, headers=headers)
        logging.info("Buy response: %s", response.json())
    else:
        logging.info(f"🔴 Open SHORT voor {abs(position_size)}")
        sell_url = "https://www.deribit.com/api/v2/private/sell"
        sell_params = {
            "instrument_name": TICKER,
            "amount": abs(position_size),
            "type": "market"
        }
        response = requests.post(sell_url, json=sell_params, headers=headers)
        logging.info("Sell response: %s", response.json())

    return {"message": "Order verwerkt", "status": "success"}



