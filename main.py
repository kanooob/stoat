import os
import asyncio
import threading
import random
import time
import logging
from datetime import datetime
from typing import Optional

import pytz
from flask import Flask
import revolt
import config

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Stoat")
FRANCE_TZ = pytz.timezone('Europe/Paris')

class StoatStats:
    """Gestionnaire d'état pour le dashboard web."""
    def __init__(self):
        self.online = True
        self.connected = False
        self.last_command = "Aucune"
        self.latency = "0ms"
        self.start_time = time.time()

    def get_uptime_str(self) -> str:
        upt = int(time.time() - self.start_time)
        h, r = divmod(upt, 3600)
        m, s = divmod(r, 60)
        return f"{h}h {m}m {s}s"

stats = StoatStats()

# --- PARTIE WEB (TABLEAU DE BORD) ---
app = Flask(__name__)

@app.route('/')
def home():
    color = "#2ecc71" if stats.connected else "#e74c3c"
    status_text = "✅ Connecté" if stats.connected else "❌ Déconnecté"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stoat Monitor</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: sans-serif; background: #121212; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .container {{ background: #1e1e1e; padding: 30px; border-radius: 15px; border-top: 5px solid {color}; box-shadow: 0 10px 20px rgba(0,0,0,0.3); }}
            h2 {{ color: {color}; margin-top: 0; }}
            .info {{ margin: 10px 0; font-size: 1.1em; }}
            code {{ background: #2c3e50; padding: 3px 7px; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🦦 Stoat Status</h2>
            <p class="info">État : <b>{status_text}</b></p>
            <p class="info">Uptime : {stats.get_uptime_str()}</p>
            <p class="info">Dernière commande : <code>{stats.last_command}</code></p>
            <p class="info">Latence : <b style="color:#3498db;">{stats.latency}</b></p>
        </div>
    </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def log_system(self, text):
        """Envoie un log dans le salon système."""
        channel = self.get_channel(config.SYSTEM_LOGS_ID)
        if channel:
            now = datetime.now(FRANCE_TZ).strftime('%H:%M:%S')
            try: await channel.send(f"🖥️ `[{now}]` {text}")
            except: print(f"Erreur log: {text}")

    async def log_event(self, text):
        """Envoie un log dans le salon des événements."""
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            now = datetime.now(FRANCE_TZ).strftime('%H:%M:%S')
            try: await channel.send(f"📜 `[{now}]` {text}")
            except: await self.log_system(f"⚠️ Erreur Envoi Log Event")

    # --- ÉVÉNEMENTS (LOGS DE MODÉRATION) ---
    async def on_ready(self):
        stats.connected = True
        await self.log_system("**Système :** Bot allumé et prêt.")
        asyncio.create_task(self.health_check_loop())

    async def on_message_delete(self, message: revolt.Message):
        if not message.author or message.author.bot: return
        await self.log_event(f"🗑️ **Message supprimé** | `{message.author.name}` dans <#{message.channel.id}>\n> {message.content}")

    async def on_message_edit(self, message: revolt.Message, old_content: str):
        if not message.author or message.author.bot: return
        await self.log_event(f"📝 **Message édité** | `{message.author.name}`\n**Avant :** {old_content}\n**Après :** {message.content}")

    async def on_member_join(self, member: revolt.Member):
        # Le texte de bienvenue parfait
        welcome_msg = (
            f"### 🌊 **Nouvelle arrivée !**\n"
            f"Bienvenue parmi nous, <@{member.id}> ! 🦦\n\n"
            f"On est ravi de te voir ici. N'hésite pas à venir discuter !"
        )
        await self.log_event(f"📥 **Bienvenue** | `{member.name}` a rejoint le serveur.")
        # Optionnel : envoyer le message dans un salon public si configurer
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel: await channel.send(welcome_msg)

    async def on_member_leave(self, member: revolt.Member):
        await self.log_event(f"📤 **Départ** | `{member.name}` a quitté le serveur.")

    # --- LOGIQUE DES COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"): return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        stats.last_command = cmd

        try:
            if cmd == "!help":
                await message.reply("### 🦦 **Aide Stoat**\n`!ping`, `!uptime`, `!serveurinfo`, `!8ball`, `!roll`, `!clear`")

            elif cmd == "!ping":
                s = time.time()
                m = await message.reply("🏓...")
                stats.latency = f"{round((time.time() - s) * 1000)}ms"
                await m.edit(content=f"🏓 Pong ! `{stats.latency}`")

            elif cmd == "!8ball":
                if not args: return await message.reply("🔮 Pose une question !")
                reps = ["Oui", "Non", "C'est possible", "Absolument !", "Oublie ça."]
                await message.reply(f"🎱 | {random.choice(reps)}")

            elif cmd == "!roll":
                faces = int(args[0]) if args and args[0].isdigit() else 6
                await message.reply(f"🎲 | Résultat : **{random.randint(1, faces)}** (Dé {faces})")

            elif cmd == "!serveurinfo":
                s = message.server
                await message.reply(f"🏰 **{s.name}**\n👤 Owner: <@{s.owner_id}>\n👥 Membres: {len(s.members)}")

            elif cmd == "!uptime":
                await message.reply(f"🕒 En ligne depuis : **{stats.get_uptime_str()}**")

            elif cmd == "!clear":
                if not message.author.get_permissions().manage_messages:
                    return await message.reply("❌ Permission `Gérer les messages` requise.")
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
                await self.log_system(f"🧹 **Modération :** {amt} messages supprimés par `{message.author.name}`.")

        except Exception as e:
            await self.log_system(f"⚠️ **Erreur Commande `{cmd}` :** `{e}`")

    # --- HEARTBEAT & MAINTENANCE ---
    async def health_check_loop(self):
        """Vérifie que le bot est toujours actif (Heartbeat)."""
        while True:
            await asyncio.sleep(300) # Toutes les 5 minutes
            try:
                await self.fetch_user(self.user.id)
                stats.connected = True
            except:
                stats.connected = False
                logger.warning("Connexion perdue, tentative de reconnexion...")
                await self.stop()

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    while True:
        stats.connected = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            logger.error(f"Erreur fatale, relance dans 15s : {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    # Lancement du site web en arrière-plan
    threading.Thread(target=run_flask, daemon=True).start()
    # Lancement du bot
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Arrêt demandé par l'utilisateur.")
