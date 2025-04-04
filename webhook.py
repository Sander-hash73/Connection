from flask import Flask, request
import requests
import logging

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
        position_size = float(data.get("position_size", 0))
    except (ValueError, TypeError):
        logging.error("Ongeldige waarde voor position_size")
        return {"status": "error", "message": "Invalid position_size"}, 400

    access_token = get_deribit_access_token()
    if not access_token:
        logging.error("Geen access token ontvangen van Deribit.")
        return {"status": "error", "message": "Geen access token"}, 500

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

    return {"status": "ok"}

if __name__ == "__main__":
    app.run(port=5000)
