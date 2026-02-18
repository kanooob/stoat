import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# --- VARIABLES D'ÉTAT POUR LE SITE ---
bot_stats = {
    "online": True,
    "connected_to_stoat": False,
    "last_command": "En attente...",
    "latency": "Calcul en cours...",
    "start_time": time.time()
}

FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time_info():
    now = datetime.now(FRANCE_TZ)
    offset = now.utcoffset().total_seconds() / 3600
    utc_str = f"UTC+{int(offset)}" if offset > 0 else f"UTC{int(offset)}"
    return now, utc_str

# --- PARTIE WEB (FLASK) ---
app = Flask(__name__)

@app.route('/')
def home(): 
    is_connected = bot_stats["connected_to_stoat"]
    status_stoat = "✅ Connecté" if is_connected else "❌ Déconnecté (Reconnexion...)"
    color = "#2ecc71" if is_connected else "#e74c3c"
    
    upt = int(time.time() - bot_stats["start_time"])
    hours, remainder = divmod(upt, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m"

    favicon_color = "2ecc71" if is_connected else "e74c3c"
    favicon_url = f"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%23{favicon_color}'/></svg>"
    
    return f"""
    <html>
        <head>
            <title>Stoat Bot Status</title>
            <meta http-equiv="refresh" content="30">
            <link rel="icon" href="{favicon_url}">
        </head>
        <body style="font-family: sans-serif; background: #1e1e1e; color: white; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="background: #252525; padding: 30px; border-radius: 15px; border-top: 5px solid {color}; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
                <h2>🦦 Stoat Bot Status</h2>
                <p>📡 <b>Connexion Stoat :</b> <span style="color: {color};">{status_stoat}</span></p>
                <p>🕒 <b>Uptime :</b> {uptime_str}</p>
                <p>🏓 <b>Ping :</b> <span style="color: #3498db;">{bot_stats['latency']}</span></p>
            </div>
        </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    async def on_ready(self):
        bot_stats["connected_to_stoat"] = True
        await self.send_system_log("⚙️ **Système :** Bot Stoat initialisé et prêt.")
        asyncio.create_task(self.health_check_task())
        asyncio.create_task(self.auto_reconnect_task())

    # --- SYSTEME DE LOGS SEPARES ---
    async def send_system_log(self, text):
        """Log pour l'allumage et le système"""
        channel = self.get_channel(config.SYSTEM_LOGS_ID)
        if channel:
            now, _ = get_fr_time_info()
            await channel.send(f"🖥️ `[{now.strftime('%H:%M:%S')}]` {text}")

    async def send_event_log(self, text):
        """Log pour les messages et membres"""
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            now, _ = get_fr_time_info()
            await channel.send(f"📜 `[{now.strftime('%H:%M:%S')}]` {text}")

    # --- VERIFICATION TOUTES LES 5 MIN ---
    async def health_check_task(self):
        while True:
            await asyncio.sleep(300) # 5 minutes
            try:
                # Test simple de latence pour vérifier si le bot répond toujours
                start = time.time()
                await self.fetch_user(self.user.id)
                bot_stats["latency"] = f"{round((time.time() - start) * 1000)}ms"
                print("💓 Health Check: OK")
            except Exception as e:
                print(f"💓 Health Check: ÉCHEC - {e}")
                await self.send_system_log("⚠️ **Alerte :** Le bot ne répond plus aux requêtes. Tentative de redémarrage...")
                await self.stop()

    async def auto_reconnect_task(self):
        await asyncio.sleep(3600)
        await self.send_system_log("🔄 **Système :** Redémarrage cyclique pour entretien.")
        await self.stop()

    # --- LOGS D'ÉVÉNEMENTS (Edit, Sup, Join, Leave) ---
    async def on_message_delete(self, message: revolt.Message):
        if message.author.bot: return
        await self.send_event_log(f"🗑️ **Message supprimé** de `{message.author.name}` dans <#{message.channel.id}>\n> {message.content}")

    async def on_message_edit(self, message: revolt.Message, old_content: str):
        if message.author.bot: return
        await self.send_event_log(f"📝 **Message modifié** par `{message.author.name}`\n**Avant :** {old_content}\n**Après :** {message.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_event_log(f"📥 **Nouveau membre :** `{member.name}` vient de rejoindre.")

    async def on_member_leave(self, member: revolt.Member):
        await self.send_event_log(f"📤 **Départ :** `{member.name}` a quitté le serveur.")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"): return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        bot_stats["last_command"] = cmd

        if cmd == "!help":
            await message.reply("### 🦦 **Menu d'Aide**\n`!ping`, `!uptime`, `!8ball`, `!roll`, `!clear`, `!serveurinfo`")

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            latency = f"{round((time.time() - s) * 1000)}ms"
            bot_stats["latency"] = latency
            await m.edit(content=f"🏓 Pong ! `{latency}`")

        elif cmd == "!serveurinfo":
            server = message.server
            info = (
                f"### 🏰 **Infos Serveur : {server.name}**\n"
                f"> 👤 **Propriétaire :** <@{server.owner_id}>\n"
                f"> 👥 **Membres :** {len(server.members)}\n"
                f"> 💬 **Salons :** {len(server.channels)}"
            )
            await message.reply(info)

        elif cmd == "!uptime":
            upt = int(time.time() - bot_stats["start_time"])
            await message.reply(f"🕒 En ligne depuis : **{upt // 3600}h {(upt % 3600) // 60}m**.")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            amt = int(args[0]) if args and args[0].isdigit() else 10
            await message.channel.clear(min(amt, 100))

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    while True:
        bot_stats["connected_to_stoat"] = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            print(f"💥 Erreur: {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
