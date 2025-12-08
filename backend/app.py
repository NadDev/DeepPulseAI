from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Configuration
COINGECKO_API = "https://api.coingecko.com/api/v3"

# In-memory storage (replace with database in production)
portfolios = {}

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

@app.route('/api/crypto/prices', methods=['GET'])
def get_crypto_prices():
    """Get current cryptocurrency prices"""
    try:
        # Get top cryptocurrencies by market cap
        response = requests.get(
            f"{COINGECKO_API}/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 50,
                "page": 1,
                "sparkline": False
            }
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/crypto/search', methods=['GET'])
def search_crypto():
    """Search for cryptocurrencies"""
    query = request.args.get('q', '')
    try:
        response = requests.get(f"{COINGECKO_API}/search", params={"query": query})
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/crypto/<coin_id>', methods=['GET'])
def get_crypto_details(coin_id):
    """Get detailed information about a specific cryptocurrency"""
    try:
        response = requests.get(
            f"{COINGECKO_API}/coins/{coin_id}",
            params={
                "localization": False,
                "tickers": False,
                "market_data": True,
                "community_data": False,
                "developer_data": False
            }
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/crypto/<coin_id>/chart', methods=['GET'])
def get_crypto_chart(coin_id):
    """Get historical price data for charts"""
    days = request.args.get('days', '7')
    try:
        response = requests.get(
            f"{COINGECKO_API}/coins/{coin_id}/market_chart",
            params={
                "vs_currency": "usd",
                "days": days
            }
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get user portfolio"""
    user_id = request.args.get('user_id', 'default')
    return jsonify(portfolios.get(user_id, []))

@app.route('/api/portfolio', methods=['POST'])
def add_to_portfolio():
    """Add cryptocurrency to portfolio"""
    data = request.json
    user_id = data.get('user_id', 'default')

    if user_id not in portfolios:
        portfolios[user_id] = []

    portfolio_item = {
        "id": len(portfolios[user_id]) + 1,
        "coin_id": data.get('coin_id'),
        "symbol": data.get('symbol'),
        "name": data.get('name'),
        "amount": data.get('amount'),
        "purchase_price": data.get('purchase_price'),
        "purchase_date": data.get('purchase_date', datetime.now().isoformat())
    }

    portfolios[user_id].append(portfolio_item)
    return jsonify(portfolio_item), 201

@app.route('/api/portfolio/<int:item_id>', methods=['DELETE'])
def remove_from_portfolio(item_id):
    """Remove cryptocurrency from portfolio"""
    user_id = request.args.get('user_id', 'default')

    if user_id in portfolios:
        portfolios[user_id] = [item for item in portfolios[user_id] if item['id'] != item_id]
        return jsonify({"message": "Item removed"}), 200

    return jsonify({"error": "Portfolio not found"}), 404

@app.route('/api/portfolio/<int:item_id>', methods=['PUT'])
def update_portfolio_item(item_id):
    """Update portfolio item"""
    user_id = request.args.get('user_id', 'default')
    data = request.json

    if user_id in portfolios:
        for item in portfolios[user_id]:
            if item['id'] == item_id:
                item.update({
                    "amount": data.get('amount', item['amount']),
                    "purchase_price": data.get('purchase_price', item['purchase_price'])
                })
                return jsonify(item), 200

    return jsonify({"error": "Item not found"}), 404

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
