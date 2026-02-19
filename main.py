import os
import asyncio
import threading
import random
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Any

import pytz
from flask import Flask
import revolt
import config

# --- CONFIGURATION & LOGGING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Stoat")
FRANCE_TZ = pytz.timezone('Europe/Paris')

class StoatStats:
    """Gestionnaire d'état centralisé pour le dashboard."""
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

# --- PARTIE WEB (FLASK) ---
app = Flask(__name__)

@app.route('/')
def home():
    color = "#2ecc71" if stats.connected else "#e74c3c"
    status_text = "Opérationnel" if stats.connected else "Déconnecté"
    
    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <title>Stoat Monitor</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background: #0f0f0f; color: #eee; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .card {{ background: #1a1a1a; padding: 2rem; border-radius: 12px; border-left: 6px solid {color}; box-shadow: 0 10px 30px rgba(0,0,0,0.5); min-width: 320px; }}
            h2 {{ margin-top: 0; color: {color}; }}
            .stat-item {{ margin: 10px 0; font-size: 0.95rem; border-bottom: 1px solid #333; padding-bottom: 5px; }}
            code {{ background: #333; padding: 2px 6px; border-radius: 4px; color: #f1c40f; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h2>🦦 Stoat Dashboard</h2>
            <div class="stat-item">État: <b>{status_text}</b></div>
            <div class="stat-item">Uptime: <b>{stats.get_uptime_str()}</b></div>
            <div class="stat-item">Dernière action: <code>{stats.last_command}</code></div>
            <div class="stat-item">Latence API: <b style="color: #3498db;">{stats.latency}</b></div>
        </div>
    </body>
    </html>
    """

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_now(self):
        return datetime.now(FRANCE_TZ)

    async def log_to_channel(self, channel_id: str, emoji: str, text: str):
        """Méthode de log générique et sécurisée."""
        channel = self.get_channel(channel_id)
        if channel:
            try:
                timestamp = self.get_now().strftime('%H:%M:%S')
                await channel.send(f"{emoji} `[{timestamp}]` {text}")
            except Exception as e:
                logger.error(f"Erreur d'envoi de log: {e}")

    # --- ÉVÉNEMENTS ---
    async def on_ready(self):
        stats.connected = True
        await self.log_to_channel(config.SYSTEM_LOGS_ID, "⚙️", "**Système :** Stoat est en ligne.")
        asyncio.create_task(self.health_check_loop())

    async def on_message_delete(self, message: revolt.Message):
        if message.author and not message.author.bot:
            content = message.content[:100] + "..." if len(message.content) > 100 else message.content
            await self.log_to_channel(config.LOGS_CHANNEL_ID, "🗑️", 
                f"**Message supprimé** | `{message.author.name}` dans <#{message.channel.id}>\n> {content}")

    async def on_member_join(self, member: revolt.Member):
        await self.log_to_channel(config.LOGS_CHANNEL_ID, "📥", f"**Bienvenue** | `{member.name}` a rejoint.")

    # --- LOGIQUE DES COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        stats.last_command = cmd

        # Système de routage de commandes
        commands = {
            "!ping": self.cmd_ping,
            "!uptime": self.cmd_uptime,
            "!8ball": self.cmd_8ball,
            "!clear": self.cmd_clear,
            "!help": self.cmd_help
        }

        if cmd in commands:
            try:
                await commands[cmd](message, args)
            except Exception as e:
                await self.log_to_channel(config.SYSTEM_LOGS_ID, "⚠️", f"Erreur `{cmd}`: {e}")

    # --- FONCTIONS DE COMMANDES ---
    async def cmd_ping(self, message, args):
        start = time.time()
        msg = await message.reply("🏓 Calcul...")
        latency = round((time.time() - start) * 1000)
        stats.latency = f"{latency}ms"
        await msg.edit(content=f"🏓 Pong ! `{latency}ms`")

    async def cmd_8ball(self, message, args):
        if not args: return await message.reply("🔮 Pose une question !")
        reps = ["Oui", "Non", "C'est possible", "Absolument !", "Oublie ça."]
        await message.reply(f"🎱 | {random.choice(reps)}")

    async def cmd_uptime(self, message, args):
        await message.reply(f"🕒 En ligne depuis : **{stats.get_uptime_str()}**")

    async def cmd_clear(self, message, args):
        if not message.author.get_permissions().manage_messages:
            return await message.reply("❌ Permission manquante : `Gérer les messages`")
        
        amt = int(args[0]) if args and args[0].isdigit() else 10
        await message.channel.clear(min(amt, 100))
        await self.log_to_channel(config.SYSTEM_LOGS_ID, "🧹", f"Nettoyage de {amt} messages par `{message.author.name}`")

    async def cmd_help(self, message, args):
        help_text = "### 🦦 **Commandes Stoat**\n`!ping`, `!uptime`, `!8ball`, `!clear` [nb]"
        await message.reply(help_text)

    # --- MAINTENANCE ---
    async def health_check_loop(self):
        """Vérifie la connexion toutes les 5 minutes."""
        while True:
            await asyncio.sleep(300)
            try:
                await self.fetch_user(self.user.id)
                stats.connected = True
            except:
                stats.connected = False
                logger.warning("Connexion perdue. Tentative de reconnexion...")
                await self.stop()

# --- RUNNER ---
def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    while True:
        stats.connected = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            logger.error(f"Relance du bot dans 15s... Erreur: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    # Flask en thread séparé
    threading.Thread(target=run_flask, daemon=True).start()
    # Bot en boucle principale
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Arrêt manuel.")
