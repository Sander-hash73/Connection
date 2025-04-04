from flask import Flask, request
import requests
import logging
import re

app = Flask(__name__)

# Deribit API credentials
DERIBIT_CLIENT_ID = "zDMGWs4t"
DERIBIT_CLIENT_SECRET = "gA2H5m8hIfwS-cboRsDLhdqGBTalmtsfgvlYOgWAajo"
TICKER = "BTC-PERPETUAL"

# Configureer logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("webhook.log"),
        logging.StreamHandler()
    ]
)

# Haal access token op
def get_deribit_access_token():
    url = "https://www.deribit.com/api/v2/public/auth"
    params = {
        "client_id": DERIBIT_CLIENT_ID,
        "client_secret": DERIBIT_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    if response.status_code != 200:
        logging.error("Fout bij ophalen access token: %s", response.text)
    return response.json().get("access_token")

# Webhook endpoint
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info("Ontvangen data: %s", data)

    try:
        # Verkrijg de signaaltekst
        signal_text = data.get("message", "")  # Aangepast naar 'message' als je geen 'signal' hebt
        logging.info(f"Verwerkte signaaltekst: {signal_text}")
        
        # Gebruik een reguliere expressie om de waarde van 'position_size' te extraheren
        match = re.search(r"@ (\d+\.\d+)", signal_text)
        if match:
            position_size = float(match.group(1))  # Haal de waarde van @ en converteer naar float
        else:
            position_size = 0  # Standaardwaarde als we geen match vinden
    except (ValueError, TypeError):
        logging.error("Ongeldige waarde voor position_size")
        return {"status": "error", "message": "Invalid position_size"}, 400

    ticker = data.get("ticker", "BTC-PERPETUAL")
    access_token = get_deribit_access_token()

    if not access_token:
        logging.error("Geen access token ontvangen van Deribit.")
        return {"status": "error", "message": "Geen access token"}, 500

    headers = {"Authorization": f"Bearer {access_token}"}

    # Positie sluiten (position_size == 0)
    if position_size == 0:
        logging.info("🛑 Sluit positie")
        close_url = "https://www.deribit.com/api/v2/private/close_position"
        close_params = {"instrument_name": ticker, "type": "market"}
        response = requests.post(close_url, json=close_params, headers=headers)
        logging.info("Close response: %s", response.json())

    # Long positie openen (position_size > 0)
    elif position_size > 0:
        logging.info(f"🟢 Open LONG voor {position_size}")
        buy_url = "https://www.deribit.com/api/v2/private/buy"
        buy_params = {
            "instrument_name": ticker,
            "amount": position_size,
            "type": "market"
        }
        response = requests.post(buy_url, json=buy_params, headers=headers)
        logging.info("Buy response: %s", response.json())

    # Short positie openen (position_size < 0)
    elif position_size < 0:
        logging.info(f"🔴 Open SHORT voor {abs(position_size)}")
        sell_url = "https://www.deribit.com/api/v2/private/sell"
        sell_params = {
            "instrument_name": ticker,
            "amount": abs(position_size),
            "type": "market"
        }
        response = requests.post(sell_url, json=sell_params, headers=headers)
        logging.info("Sell response: %s", response.json())

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000)
