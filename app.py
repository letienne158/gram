import os
import json
import asyncio
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_file
from telethon import TelegramClient
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
import csv
import io
import tempfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)
CREDENTIALS_FILE = os.path.join(DATA_DIR, "credentials.json")
LAST_RESULTS_FILE = os.path.join(DATA_DIR, "last_results.json")
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))

# State global
search_state = {
    "running": False,
    "progress": 0,
    "total": 0,
    "current_keyword": "",
    "results": [],
    "error": None,
    "done": False
}

# Auth state
auth_state = {
    "step": "idle",  # idle, code_needed, password_needed, authenticated
    "phone_code_hash": None,
    "error": None,
    "client": None,
    "loop": None,
    "api_id": None,
    "api_hash": None,
    "phone": None
}


def save_credentials(api_id, api_hash, phone):
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump({"api_id": api_id, "api_hash": api_hash, "phone": phone}, f)


def load_credentials():
    if os.path.isfile(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "r") as f:
            return json.load(f)
    return None


def save_last_results():
    results = [r for r in search_state["results"] if r["type"] != "ERREUR"]
    if results:
        with open(LAST_RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"results": results, "done": search_state["done"]}, f, ensure_ascii=False)


def load_last_results():
    if os.path.isfile(LAST_RESULTS_FILE):
        with open(LAST_RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        search_state["results"] = data.get("results", [])
        search_state["done"] = data.get("done", True)


def reset_state():
    search_state.update({
        "running": False,
        "progress": 0,
        "total": 0,
        "current_keyword": "",
        "results": [],
        "error": None,
        "done": False
    })


def get_session_path():
    return os.path.join(tempfile.gettempdir(), "gram_session")


def get_or_create_loop():
    if auth_state["loop"] is None or auth_state["loop"].is_closed():
        auth_state["loop"] = asyncio.new_event_loop()
    return auth_state["loop"]


async def _connect(api_id, api_hash, phone):
    """Se connecte et envoie le code de vérification."""
    session_path = get_session_path()
    client = TelegramClient(session_path, int(api_id), api_hash)
    await client.connect()

    if await client.is_user_authorized():
        auth_state["client"] = client
        auth_state["step"] = "authenticated"
        return

    result = await client.send_code_request(phone)
    auth_state["client"] = client
    auth_state["phone_code_hash"] = result.phone_code_hash
    auth_state["step"] = "code_needed"


async def _verify_code(phone, code, phone_code_hash):
    """Vérifie le code reçu par Telegram."""
    client = auth_state["client"]
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        auth_state["step"] = "authenticated"
    except Exception as e:
        err_str = str(e).lower()
        if "two-steps verification" in err_str or "2fa" in err_str or "password" in err_str:
            auth_state["step"] = "password_needed"
        else:
            raise


async def _verify_password(password):
    """Vérifie le mot de passe 2FA."""
    client = auth_state["client"]
    await client.sign_in(password=password)
    auth_state["step"] = "authenticated"


async def search_telegram(keywords):
    """Recherche des groupes/canaux Telegram pour chaque mot-clé."""
    client = auth_state["client"]
    search_state["running"] = True
    search_state["total"] = len(keywords)
    search_state["done"] = False

    try:
        seen_ids = set()

        for i, keyword in enumerate(keywords):
            keyword = keyword.strip()
            if not keyword:
                continue

            search_state["progress"] = i + 1
            search_state["current_keyword"] = keyword

            try:
                result = await client(SearchRequest(
                    q=keyword,
                    limit=100
                ))

                for chat in result.chats:
                    if chat.id in seen_ids:
                        continue
                    seen_ids.add(chat.id)

                    chat_type = "Canal" if getattr(chat, 'broadcast', False) else "Groupe"
                    username = getattr(chat, 'username', None) or ""
                    link = f"https://t.me/{username}" if username else "N/A"
                    members = getattr(chat, 'participants_count', None) or "N/A"
                    title = getattr(chat, 'title', '') or ""
                    description = ""
                    restricted = getattr(chat, 'restricted', False)
                    scam = getattr(chat, 'scam', False)
                    fake = getattr(chat, 'fake', False)
                    verified = getattr(chat, 'verified', False)
                    date = getattr(chat, 'date', None)
                    date_str = date.strftime("%Y-%m-%d %H:%M") if date else "N/A"

                    try:
                        full = await client.get_entity(chat.id)
                        if hasattr(full, 'about') and full.about:
                            description = full.about
                    except Exception:
                        pass

                    search_state["results"].append({
                        "keyword": keyword,
                        "type": chat_type,
                        "title": title,
                        "username": username,
                        "link": link,
                        "members": members,
                        "description": description,
                        "verified": verified,
                        "scam": scam,
                        "fake": fake,
                        "restricted": restricted,
                        "date_creation": date_str,
                        "id": chat.id
                    })

            except Exception as e:
                search_state["results"].append({
                    "keyword": keyword,
                    "type": "ERREUR",
                    "title": str(e),
                    "username": "",
                    "link": "",
                    "members": "",
                    "description": "",
                    "verified": False,
                    "scam": False,
                    "fake": False,
                    "restricted": False,
                    "date_creation": "",
                    "id": ""
                })

            await asyncio.sleep(2)

    except Exception as e:
        search_state["error"] = str(e)
    finally:
        search_state["running"] = False
        search_state["done"] = True
        save_last_results()


def run_search_thread(keywords):
    loop = get_or_create_loop()
    loop.run_until_complete(search_telegram(keywords))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/auth/connect", methods=["POST"])
def auth_connect():
    """Étape 1 : connexion + envoi du code."""
    api_id = request.json.get("api_id", "").strip()
    api_hash = request.json.get("api_hash", "").strip()
    phone = request.json.get("phone", "").strip()

    if not api_id or not api_hash or not phone:
        return jsonify({"error": "Tous les champs sont requis."}), 400

    auth_state["api_id"] = api_id
    auth_state["api_hash"] = api_hash
    auth_state["phone"] = phone
    auth_state["error"] = None

    try:
        loop = get_or_create_loop()
        loop.run_until_complete(_connect(api_id, api_hash, phone))
        if auth_state["step"] == "authenticated":
            save_credentials(api_id, api_hash, phone)
        return jsonify({"step": auth_state["step"]})
    except Exception as e:
        auth_state["step"] = "idle"
        return jsonify({"error": str(e)}), 400


@app.route("/auth/verify", methods=["POST"])
def auth_verify():
    """Étape 2 : vérification du code."""
    code = request.json.get("code", "").strip()
    if not code:
        return jsonify({"error": "Code requis."}), 400

    try:
        loop = get_or_create_loop()
        loop.run_until_complete(
            _verify_code(auth_state["phone"], code, auth_state["phone_code_hash"])
        )
        if auth_state["step"] == "authenticated":
            save_credentials(auth_state["api_id"], auth_state["api_hash"], auth_state["phone"])
        return jsonify({"step": auth_state["step"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/auth/password", methods=["POST"])
def auth_password():
    """Étape 2bis : mot de passe 2FA."""
    password = request.json.get("password", "").strip()
    if not password:
        return jsonify({"error": "Mot de passe requis."}), 400

    try:
        loop = get_or_create_loop()
        loop.run_until_complete(_verify_password(password))
        if auth_state["step"] == "authenticated":
            save_credentials(auth_state["api_id"], auth_state["api_hash"], auth_state["phone"])
        return jsonify({"step": auth_state["step"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/auth/status")
def auth_status():
    return jsonify({"step": auth_state["step"]})


@app.route("/auth/credentials")
def auth_credentials():
    """Renvoie les credentials sauvegardés (pour pré-remplir le formulaire)."""
    creds = load_credentials()
    if creds:
        return jsonify(creds)
    return jsonify({})


@app.route("/search", methods=["POST"])
def search():
    if auth_state["step"] != "authenticated":
        return jsonify({"error": "Non authentifié. Connectez-vous d'abord."}), 401

    reset_state()

    file = request.files.get("keywords_file")
    if not file:
        return jsonify({"error": "Fichier de mots-clés requis."}), 400

    content = file.read().decode("utf-8", errors="ignore")
    keywords = [line.strip() for line in content.splitlines() if line.strip()]

    if not keywords:
        return jsonify({"error": "Le fichier ne contient aucun mot-clé."}), 400

    thread = threading.Thread(target=run_search_thread, args=(keywords,))
    thread.daemon = True
    thread.start()

    return jsonify({"status": "started", "total": len(keywords)})


@app.route("/status")
def status():
    return jsonify({
        "running": search_state["running"],
        "progress": search_state["progress"],
        "total": search_state["total"],
        "current_keyword": search_state["current_keyword"],
        "results_count": len(search_state["results"]),
        "results": search_state["results"],
        "error": search_state["error"],
        "done": search_state["done"]
    })


@app.route("/export/csv")
def export_csv():
    if not search_state["results"]:
        return jsonify({"error": "Aucun résultat à exporter."}), 400

    output = io.StringIO()
    fieldnames = ["keyword", "type", "title", "username", "link", "members",
                  "description", "verified", "scam", "fake", "restricted",
                  "date_creation", "id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in search_state["results"]:
        if row["type"] != "ERREUR":
            writer.writerow(row)

    output.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8")),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"telegram_results_{timestamp}.csv"
    )


@app.route("/export/json")
def export_json():
    if not search_state["results"]:
        return jsonify({"error": "Aucun résultat à exporter."}), 400

    results = [r for r in search_state["results"] if r["type"] != "ERREUR"]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = json.dumps(results, indent=2, ensure_ascii=False).encode("utf-8")

    return send_file(
        io.BytesIO(data),
        mimetype="application/json",
        as_attachment=True,
        download_name=f"telegram_results_{timestamp}.json"
    )


@app.route("/join", methods=["POST"])
def join_channel():
    """Rejoint un groupe ou canal Telegram."""
    if auth_state["step"] != "authenticated":
        return jsonify({"error": "Non authentifie."}), 401

    username = request.json.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username requis."}), 400

    try:
        loop = get_or_create_loop()
        async def _join():
            client = auth_state["client"]
            entity = await client.get_entity(username)
            await client(JoinChannelRequest(entity))
        loop.run_until_complete(_join())
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# === PROJECTS ===

@app.route("/projects", methods=["GET"])
def list_projects():
    """Liste tous les dossiers de projets et leurs recherches."""
    projects = []
    for folder in sorted(os.listdir(PROJECTS_DIR)):
        folder_path = os.path.join(PROJECTS_DIR, folder)
        if not os.path.isdir(folder_path):
            continue
        searches = []
        for f in sorted(os.listdir(folder_path)):
            if f.endswith(".json"):
                filepath = os.path.join(folder_path, f)
                with open(filepath, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                searches.append({
                    "filename": f,
                    "name": data.get("name", f),
                    "date": data.get("date", ""),
                    "results_count": len(data.get("results", []))
                })
        projects.append({"name": folder, "searches": searches})
    return jsonify(projects)


@app.route("/projects/create", methods=["POST"])
def create_project():
    """Crée un nouveau dossier de projet."""
    name = request.json.get("name", "").strip()
    if not name:
        return jsonify({"error": "Nom requis."}), 400
    safe_name = "".join(c for c in name if c.isalnum() or c in " -_").strip()
    if not safe_name:
        return jsonify({"error": "Nom invalide."}), 400
    path = os.path.join(PROJECTS_DIR, safe_name)
    if os.path.exists(path):
        return jsonify({"error": "Ce projet existe deja."}), 400
    os.makedirs(path)
    return jsonify({"status": "ok", "name": safe_name})


@app.route("/projects/delete", methods=["POST"])
def delete_project():
    """Supprime un dossier de projet."""
    name = request.json.get("name", "").strip()
    path = os.path.join(PROJECTS_DIR, name)
    if not os.path.isdir(path):
        return jsonify({"error": "Projet introuvable."}), 404
    import shutil
    shutil.rmtree(path)
    return jsonify({"status": "ok"})


@app.route("/projects/save", methods=["POST"])
def save_search():
    """Sauvegarde la recherche courante dans un projet."""
    project = request.json.get("project", "").strip()
    search_name = request.json.get("name", "").strip()

    if not project or not search_name:
        return jsonify({"error": "Projet et nom de recherche requis."}), 400

    project_path = os.path.join(PROJECTS_DIR, project)
    if not os.path.isdir(project_path):
        return jsonify({"error": "Projet introuvable."}), 404

    results = [r for r in search_state["results"] if r["type"] != "ERREUR"]
    if not results:
        return jsonify({"error": "Aucun resultat a sauvegarder."}), 400

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = "".join(c for c in search_name if c.isalnum() or c in " -_").strip()
    filename = f"{safe_name}_{timestamp}.json"

    data = {
        "name": search_name,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "keywords_count": len(set(r["keyword"] for r in results)),
        "results": results
    }

    filepath = os.path.join(project_path, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return jsonify({"status": "ok", "filename": filename})


@app.route("/projects/load", methods=["POST"])
def load_search():
    """Charge une recherche sauvegardee."""
    project = request.json.get("project", "").strip()
    filename = request.json.get("filename", "").strip()

    filepath = os.path.join(PROJECTS_DIR, project, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Fichier introuvable."}), 404

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


@app.route("/projects/delete-search", methods=["POST"])
def delete_search():
    """Supprime une recherche sauvegardee."""
    project = request.json.get("project", "").strip()
    filename = request.json.get("filename", "").strip()

    filepath = os.path.join(PROJECTS_DIR, project, filename)
    if not os.path.isfile(filepath):
        return jsonify({"error": "Fichier introuvable."}), 404

    os.remove(filepath)
    return jsonify({"status": "ok"})


def auto_reconnect():
    """Tente de se reconnecter avec la session et les credentials sauvegardés."""
    creds = load_credentials()
    if not creds:
        return
    session_path = get_session_path()
    if not os.path.isfile(session_path + ".session"):
        return
    try:
        loop = get_or_create_loop()
        loop.run_until_complete(_connect(creds["api_id"], creds["api_hash"], creds["phone"]))
        if auth_state["step"] == "authenticated":
            auth_state["api_id"] = creds["api_id"]
            auth_state["api_hash"] = creds["api_hash"]
            auth_state["phone"] = creds["phone"]
            print("  [OK] Reconnexion automatique reussie")
        else:
            auth_state["step"] = "idle"
    except Exception as e:
        print(f"  [!] Reconnexion echouee: {e}")
        auth_state["step"] = "idle"


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  GRAM - Telegram Group Scanner")
    print("  Interface : http://localhost:5000")
    print("=" * 50)
    # Charger les derniers résultats
    load_last_results()
    if search_state["results"]:
        search_state["done"] = True
        print(f"  [OK] {len(search_state['results'])} resultats charges")
    # Tenter la reconnexion automatique
    auto_reconnect()
    print()
    app.run(debug=False, port=5000)
