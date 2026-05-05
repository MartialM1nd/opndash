import os
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"
if ENV_FILE.exists():
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)

OPNSENSE_URL = os.getenv("OPNSENSE_URL", "https://10.10.5.1:10443")
OPNSENSE_API_KEY = os.getenv("OPNSENSE_API_KEY", "")
OPNSENSE_API_SECRET = os.getenv("OPNSENSE_API_SECRET", "")
OPNSENSE_VERIFY_SSL = os.getenv("OPNSENSE_VERIFY_SSL", "false").lower() == "true"

DASHBOARD_USERNAME = os.getenv("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "changeme")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")

REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "5"))

SESSION_TYPE = "filesystem"
SESSION_PERMANENT = True
SESSION_USE_SIGNER = True
PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30

from flask import Flask, render_template, jsonify, request, redirect, url_for, session, flash
from functools import wraps
import urllib3
from werkzeug.middleware.proxy_fix import ProxyFix
import requests
from requests.auth import HTTPBasicAuth

if not OPNSENSE_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

opnsense_session = requests.Session()

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=2, x_proto=1, x_host=1, x_port=1)

app.config["SESSION_TYPE"] = SESSION_TYPE
app.config["SESSION_PERMANENT"] = SESSION_PERMANENT
app.config["SESSION_USE_SIGNER"] = SESSION_USE_SIGNER
app.config["PERMANENT_SESSION_LIFETIME"] = PERMANENT_SESSION_LIFETIME

from flask_session import Session
Session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def get_opnsense_auth():
    return HTTPBasicAuth(OPNSENSE_API_KEY, OPNSENSE_API_SECRET)

def api_request(endpoint):
    url = f"{OPNSENSE_URL}{endpoint}"
    try:
        response = opnsense_session.get(url, auth=get_opnsense_auth(), verify=OPNSENSE_VERIFY_SSL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

@app.route("/api/traffic/history")
@login_required
def get_traffic_history():
    resolution = int(request.args.get("range", 1))

    interfaces_data = {}
    for iface in ["wan", "opt3"]:
        endpoint = f"/api/diagnostics/systemhealth/get_system_health/{iface}-traffic/{resolution}"
        data = api_request(endpoint)

        if "error" in data:
            continue

        iface_data = {
            "in": [],
            "out": []
        }

        if "set" in data and "data" in data["set"]:
            for item in data["set"]["data"]:
                key = item.get("key", "")
                values = item.get("values", [])

                if key == "inpass":
                    for v in values:
                        iface_data["in"].append({"t": v[0], "v": v[1]})
                elif key == "outpass":
                    for v in values:
                        iface_data["out"].append({"t": v[0], "v": v[1]})

        interfaces_data[iface] = iface_data

    return jsonify({
        "resolution": resolution,
        "interfaces": interfaces_data
    })

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("authenticated"):
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    remember = request.form.get("remember") == "on"

    if username == DASHBOARD_USERNAME and password == DASHBOARD_PASSWORD:
        session["authenticated"] = True
        session.permanent = remember
        return redirect(url_for("dashboard"))

    flash("Invalid credentials", "error")
    return render_template("login.html", error="Invalid username or password")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/gateways")
@login_required
def get_gateways():
    return jsonify(api_request("/api/routing/settings/searchGateway"))

@app.route("/api/traffic")
@login_required
def get_traffic():
    return jsonify(api_request("/api/diagnostics/traffic/_interface"))

@app.route("/api/haproxy/services")
@login_required
def get_haproxy_services():
    return jsonify(api_request("/api/haproxy/statistics/counters"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)