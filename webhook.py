from flask import Flask, request
import requests
import logging

app = Flask(__name__)

# Deribit API credentials
DERIBIT_CLIENT_ID = "zDMGWs4t"
DERIBIT_CLIENT_SECRET = "jgA2H5m8hIfwS-cboRsDLhdqGBTalmtsfgvlYOgWAajo"
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
    response = requests.post(url, data=params)

    # Log de response voor debugging
    logging.info("Response van Deribit API: %s", response.text)

    if response.status_code != 200:
        logging.error("Fout bij ophalen access token: %s", response.text)
        return None
    
    # Log de JSON response om te zien wat er wordt geretourneerd
    response_data = response.json()
    access_token = response_data.get("result", {}).get("access_token")
    
    # Log het access token om te controleren
    logging.info("Access token ontvangen: %s", access_token)
    
    return access_token
# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    # Zorg ervoor dat data altijd een waarde heeft
    data = None
    message = ""

    if request.content_type == 'application/json':
        data = request.get_json()
        message = data.get("message", "")
    elif request.content_type == 'text/plain':
        message = request.data.decode('utf-8')
        # Aangezien de data in tekstformaat is, kunnen we een fictief 'data' object aanmaken
        data = {"message": message}
    else:
        return {"message": "Unsupported content type", "status": "error"}, 415

    # Log het bericht
    logging.info(f"Ontvangen bericht: {message}")

    # Extract position size
    try:
        position_size = float(data.get("position_size", 0))
    except (ValueError, TypeError):
        logging.error("Ongeldige waarde voor position_size")
        return {"status": "error", "message": "Invalid position_size"}, 400

    # Haal toegangstoken op
    access_token = get_deribit_access_token()
    if not access_token:
        logging.error("Geen access token ontvangen van Deribit.")
        return {"status": "error", "message": "Geen access token"}, 500

    headers = {"Authorization": f"Bearer {access_token}"}

    # Sluit positie
    if position_size == 0:
        logging.info("🛑 Sluit positie")
        close_url = "https://www.deribit.com/api/v2/private/close_position"
        close_params = {"instrument_name": TICKER, "type": "market"}
        response = requests.post(close_url, json=close_params, headers=headers)
        logging.info("Close response: %s", response.json())

    # Open LONG positie
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

    # Open SHORT positie
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

    return {"message": "Ontvangen", "status": "success"}

if __name__ == "__main__":
    app.run(port=5000)
