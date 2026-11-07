"""
Miracle MCP Server - Reads from Supabase, serves Claude tools
"""
import json
import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

SUPABASE_URL = "https://rpxpigwiqjyuphhzsckf.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJweHBpZ3dpcWp5dXBoaHpzY2tmIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc5NDAyOTczMywiZXhwIjoyMTA5NjA1NzMzfQ.62fjRd_czsijoWI5Y94txuAbW3WZ7IauyM2bBUxEqbI"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def query_supabase(table, limit=500, filters=None):
    url = f"{SUPABASE_URL}/rest/v1/{table}?limit={limit}&order=row_num.asc"
    if filters:
        url += "&" + filters
    r = requests.get(url, headers=HEADERS)
    if r.status_code == 200:
        return r.json()
    return []

# MCP Server metadata
MCP_INFO = {
    "name": "miracle-accounting",
    "version": "1.0.0",
    "description": "Miracle Accounting Software connector for Vinit Mobile"
}

TOOLS = [
    {
        "name": "get_vouchers",
        "description": "Get vouchers/transactions from Miracle Accounting",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 100)", "default": 100}
            }
        }
    },
    {
        "name": "get_ledger",
        "description": "Get ledger entries from Miracle Accounting",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 100)", "default": 100}
            }
        }
    },
    {
        "name": "get_cashbook",
        "description": "Get cashbook entries from Miracle Accounting",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 100)", "default": 100}
            }
        }
    },
    {
        "name": "get_parties",
        "description": "Get parties/customers list from Miracle Accounting",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Max records (default 100)", "default": 100}
            }
        }
    }
]

@app.route("/")
def index():
    return jsonify({"status": "ok", "server": "miracle-mcp"})

@app.route("/.well-known/oauth-authorization-server")
def oauth_meta():
    base = request.host_url.rstrip("/")
    return jsonify({
        "issuer": base,
        "authorization_endpoint": f"{base}/oauth/authorize",
        "token_endpoint": f"{base}/oauth/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code"]
    })

@app.route("/oauth/authorize")
def oauth_authorize():
    redirect_uri = request.args.get("redirect_uri", "")
    state = request.args.get("state", "")
    code = "miracle_auth_code_123"
    return f'''<html><body>
    <h2>Miracle Accounting - Claude Access</h2>
    <p>Allow Claude to access Miracle Accounting data?</p>
    <a href="{redirect_uri}?code={code}&state={state}">
        <button style="background:#4CAF50;color:white;padding:10px 20px;border:none;cursor:pointer;font-size:16px">
            Allow Access
        </button>
    </a>
    </body></html>'''

@app.route("/oauth/token", methods=["POST"])
def oauth_token():
    return jsonify({
        "access_token": "miracle_token_vinitmobile",
        "token_type": "bearer",
        "expires_in": 86400
    })

@app.route("/mcp", methods=["POST"])
def mcp_endpoint():
    data = request.json
    method = data.get("method", "")
    req_id = data.get("id", 1)

    if method == "initialize":
        return jsonify({
            "jsonrpc": "2.0", "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": MCP_INFO
            }
        })

    elif method == "tools/list":
        return jsonify({
            "jsonrpc": "2.0", "id": req_id,
            "result": {"tools": TOOLS}
        })

    elif method == "tools/call":
        tool_name = data.get("params", {}).get("name", "")
        args = data.get("params", {}).get("arguments", {})
        limit = args.get("limit", 100)

        table_map = {
            "get_vouchers": "miracle_vouchers",
            "get_ledger": "miracle_ledger",
            "get_cashbook": "miracle_cashbook",
            "get_parties": "miracle_parties"
        }

        if tool_name in table_map:
            records = query_supabase(table_map[tool_name], limit=limit)
            return jsonify({
                "jsonrpc": "2.0", "id": req_id,
                "result": {
                    "content": [{
                        "type": "text",
                        "text": json.dumps(records, ensure_ascii=False, indent=2)
                    }]
                }
            })

        return jsonify({
            "jsonrpc": "2.0", "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
        })

    return jsonify({
        "jsonrpc": "2.0", "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"}
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
