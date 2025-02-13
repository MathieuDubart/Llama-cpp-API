from flask import Flask, request, jsonify
from llama_cpp import Llama
import sqlite3
import uuid

app = Flask(__name__)

# Load your model
llm = Llama(model_path="./models/mistral-7b-instruct-v0.2.Q4_K_M.gguf", n_gpu_layers=50)

DB_PATH = "conversations.db"

def init_db():
    """Créer les tables si elles n'existent pas ou ajouter la colonne 'pre_prompt' si elle manque."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY
            )
        """)

        cursor.execute("PRAGMA table_info(conversations)")
        columns = [info[1] for info in cursor.fetchall()]
        if "pre_prompt" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN pre_prompt TEXT DEFAULT ''")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                user TEXT,
                bot TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        conn.commit()

init_db()

@app.route("/new_conversation", methods=["POST"])
def new_conversation():
    """Créer une nouvelle conversation."""
    data = request.json
    conversation_id = str(uuid.uuid4())
    pre_prompt = data.get("pre_prompt", "Tu es un assistant utile.")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO conversations (id, pre_prompt) VALUES (?, ?)", (conversation_id, pre_prompt))
        conn.commit()
    return jsonify({"conversation_id": conversation_id})


@app.route("/generate", methods=["POST"])
def generate():
    """Générer une réponse en utilisant le pré-prompt et les deux derniers messages pour le contexte."""
    data = request.json
    conversation_id = data.get("conversation_id")
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Aucun prompt fourni"}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT pre_prompt FROM conversations WHERE id=?", (conversation_id,))
        row = cursor.fetchone()
        pre_prompt = row[0] if row else ""

        cursor.execute("""
            SELECT user, bot FROM messages 
            WHERE conversation_id=? 
            ORDER BY id DESC LIMIT 2
        """, (conversation_id,))
        last_messages = cursor.fetchall()

    context = "\n".join([f"User: {msg[0]}\nBot: {msg[1]}" for msg in reversed(last_messages)])

    full_prompt = f"{pre_prompt}\n{context}\nUser: {prompt}\nBot:"

    response = llm(full_prompt, max_tokens=3000, temperature=0.8, stop=["\nUser:", "\nBot:"])
    bot_response = response["choices"][0]["text"].strip()

    user_message_cleaned = prompt.replace(pre_prompt, "").strip()
    bot_response_cleaned = clean_response(bot_response)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (conversation_id, user, bot) VALUES (?, ?, ?)",
            (conversation_id, user_message_cleaned, bot_response_cleaned)
        )
        conn.commit()

    return jsonify({"response": bot_response_cleaned, "conversation_id": conversation_id})



def clean_response(text):
    """Nettoyer le texte pour retirer les marqueurs 'User:' et 'Bot:'."""
    if text:
        text = text.replace("User:", "").replace("Bot:", "").strip()
    return text


@app.route("/get_conversation/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """Récupérer l'historique d'une conversation."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user, bot FROM messages WHERE conversation_id=?", (conversation_id,))
        messages = [{"user": msg[0], "bot": msg[1]} for msg in cursor.fetchall()]

    if not messages:
        return jsonify({"conversation_id": conversation_id, "messages": []})

    return jsonify({"conversation_id": conversation_id, "messages": messages})

@app.route("/list_conversations", methods=["GET"])
def list_conversations():
    """Lister toutes les conversations existantes."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM conversations")
        conversations = [row[0] for row in cursor.fetchall()]
    return jsonify({"conversations": conversations})

@app.route("/update_pre_prompt/<conversation_id>", methods=["POST"])
def update_pre_prompt(conversation_id):
    """Mettre à jour le pré-prompt d'une conversation."""
    data = request.json
    pre_prompt = data.get("pre_prompt", "")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE conversations SET pre_prompt=? WHERE id=?", (pre_prompt, conversation_id))
        conn.commit()
    return jsonify({"message": "Pré-prompt mis à jour", "conversation_id": conversation_id})

@app.route("/delete_conversation/<conversation_id>", methods=["DELETE"])
def delete_conversation(conversation_id):
    """Supprimer une conversation et ses messages."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE conversation_id=?", (conversation_id,))
        cursor.execute("DELETE FROM conversations WHERE id=?", (conversation_id,))
        conn.commit()
    return jsonify({"message": "Conversation supprimée", "conversation_id": conversation_id})

@app.route("/reset_db", methods=["POST"])
def reset_db():
    """Réinitialiser la base de données en supprimant toutes les conversations et messages."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM conversations")
        conn.commit()
    return jsonify({"message": "Base de données réinitialisée avec succès"})

@app.route("/get_pre_prompt/<conversation_id>", methods=["GET"])
def get_pre_prompt(conversation_id):
    """Récupérer le pré-prompt d'une conversation."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT pre_prompt FROM conversations WHERE id=?", (conversation_id,))
        row = cursor.fetchone()
        if row:
            return jsonify({"pre_prompt": row[0]})
        else:
            return jsonify({"error": "Conversation non trouvée"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
