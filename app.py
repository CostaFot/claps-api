import os
import json
import base64
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins=["https://www.costafotiadis.com"])

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "CostaFot/claps")
GITHUB_FILE = "claps.json"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE}"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def get_claps_file():
    """Fetch claps.json from GitHub. Returns (data_dict, sha)."""
    resp = requests.get(GITHUB_API, headers=HEADERS)
    if resp.status_code == 404:
        return {}, None
    resp.raise_for_status()
    body = resp.json()
    content = base64.b64decode(body["content"]).decode("utf-8")
    return json.loads(content), body["sha"]


def save_claps_file(data, sha):
    """Commit updated claps.json back to GitHub."""
    content = base64.b64encode(json.dumps(data, indent=2).encode()).decode()
    payload = {
        "message": "chore: update clap counts",
        "content": content,
    }
    if sha:
        payload["sha"] = sha
    resp = requests.put(GITHUB_API, headers=HEADERS, json=payload)
    resp.raise_for_status()


def notify_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT_ID, "text": message},
        timeout=5,
    )


def normalise_url(url):
    """Strip trailing slash and query params for a stable key."""
    return url.split("?")[0].rstrip("/")


@app.route("/claps", methods=["GET"])
def get_claps():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url param required"}), 400
    data, _ = get_claps_file()
    key = normalise_url(url)
    return jsonify({"url": key, "claps": data.get(key, 0)})


@app.route("/claps", methods=["POST"])
def add_clap():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "url param required"}), 400
    key = normalise_url(url)
    data, sha = get_claps_file()
    data[key] = data.get(key, 0) + 1
    save_claps_file(data, sha)
    notify_telegram(f"New clap on {key} (total: {data[key]})")
    return jsonify({"url": key, "claps": data[key]})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
