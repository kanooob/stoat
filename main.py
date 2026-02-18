import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# --- VARIABLES D'ÉTAT PARTAGÉES ---
bot_stats = {
    "online": True,
    "connected_to_stoat": False,
    "last_command": "En attente...",
    "latency": "Calcul en cours...",
    "start_time": time.time(),
    "client_instance": None  # Pour permettre au site web de tester le bot
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
    # Vérification dynamique : le site teste si le bot peut parler à Stoat
    is_connected = bot_stats["connected_to_stoat"]
    
    # Calcul de l'uptime
    upt = int(time.time() - bot_stats["start_time"])
    h, r = divmod(upt, 3600)
    m, s = divmod(r, 60)
    
    status_stoat = "✅ Connecté & Opérationnel" if is_connected else "❌ Déconnecté (Relance en cours...)"
    color = "#2ecc71" if is_connected else "#e74c3c"
    favicon_color = "2ecc71" if is_connected else "e74c3c"

    return f"""
    <html>
        <head>
            <title>Stoat Bot Status</title>
            <meta http-equiv="refresh" content="30">
            <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%23{favicon_color}'/></svg>">
        </head>
        <body style="font-family: 'Segoe UI', sans-serif; background: #121212; color: white; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="background: #1e1e1e; padding: 40px; border-radius: 20px; border-left: 8px solid {color}; box-shadow: 0 15px 35px rgba(0,0,0,0.5); min-width: 350px;">
                <h2 style="margin: 0 0 20px 0; color: {color};">🦦 Stoat Control Panel</h2>
                <div style="background: #252525; padding: 15px; border-radius: 10px;">
                    <p style="margin: 5px 0;">🌐 <b>API Stoat :</b> {status_stoat}</p>
                    <p style="margin: 5px 0;">🕒 <b>Uptime :</b> {h}h {m}m {s}s</p>
                    <p style="margin: 5px 0;">⚡ <b>Dernier Appel :</b> <code>{bot_stats['last_command']}</code></p>
                    <p style="margin: 5px 0;">🏓 <b>Ping :</b> <span style="color: #3498db;">{bot_stats['latency']}</span></p>
                </div>
                <p style="font-size: 0.8em; color: #666; margin-top: 20px; text-align: center;"><i>Vérification temps réel activée</i></p>
            </div>
        </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_date = datetime.now(FRANCE_TZ).strftime("%d/%m/%Y")

    async def on_ready(self):
        bot_stats["connected_to_stoat"] = True
        bot_stats["client_instance"] = self
        
        await self.send_system_log("🚀 **Système :** Bot Stoat en ligne et connecté à l'API.")
        
        try:
            await self.edit_status(text=f"{self.last_date} | !help", presence=revolt.PresenceType.online)
        except: pass
        
        # Tâches de fond
        asyncio.create_task(self.health_check_loop())
        asyncio.create_task(self.daily_task())

    # --- GESTION DES LOGS ---
    async def send_system_log(self, text):
        """Logs techniques (Démarrage, erreurs)"""
        channel = self.get_channel(config.SYSTEM_LOGS_ID)
        if channel:
            now, _ = get_fr_time_info()
            try: await channel.send(f"🖥️ `[{now.strftime('%H:%M:%S')}]` {text}")
            except: pass

    async def send_event_log(self, text):
        """Logs serveurs (Messages, membres)"""
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            now, _ = get_fr_time_info()
            try: await channel.send(f"📜 `[{now.strftime('%H:%M:%S')}]` {text}")
            except: pass

    # --- SURVEILLANCE ET MAINTENANCE ---
    async def health_check_loop(self):
        """Vérifie toutes les 5 min si le bot peut toujours communiquer"""
        while True:
            await asyncio.sleep(300)
            try:
                start = time.time()
                await self.fetch_user(self.user.id)
                bot_stats["latency"] = f"{round((time.time() - start) * 1000)}ms"
                bot_stats["connected_to_stoat"] = True
            except Exception:
                bot_stats["connected_to_stoat"] = False
                await self.send_system_log("⚠️ **Alerte :** Perte de communication API. Tentative de reconnexion...")
                await self.stop()

    async def daily_task(self):
        """Auto-reconnect toutes les heures + Update date"""
        count = 0
        while True:
            await asyncio.sleep(60)
            count += 1
            # Update date sur le statut
            now = datetime.now(FRANCE_TZ)
            current_date = now.strftime("%d/%m/%Y")
            if current_date != self.last_date:
                self.last_date = current_date
                await self.edit_status(text=f"{self.last_date} | !help")

            # Reconnexion après 60 passages (1h)
            if count >= 60:
                await self.send_system_log("🔄 **Maintenance :** Rafraîchissement de la session horaire.")
                await self.stop()

    # --- ÉVÉNEMENTS DE LOGS ---
    async def on_message_delete(self, message: revolt.Message):
        if not message.author or message.author.bot: return
        await self.send_event_log(f"🗑️ **Message supprimé** | `{message.author.name}` dans <#{message.channel.id}>\n> {message.content}")

    async def on_message_edit(self, message: revolt.Message, old_content: str):
        if not message.author or message.author.bot: return
        await self.send_event_log(f"📝 **Message édité** | `{message.author.name}`\n**Ancien :** {old_content}\n**Nouveau :** {message.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_event_log(f"📥 **Arrivée :** `{member.name}` a rejoint le serveur.")

    async def on_member_leave(self, member: revolt.Member):
        await self.send_event_log(f"📤 **Départ :** `{member.name}` a quitté le serveur.")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        print(f"Message reçu : {message.content}") # <--- AJOUTE CETTE LIGNE ICI
        if not message.author or message.author.bot or not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        bot_stats["last_command"] = cmd

        if cmd == "!help":
            help_msg = (
                "### 🦦 **Stoat Bot v2.0**\n"
                "> `!ping` : Latence\n"
                "> `!uptime` : Temps de marche\n"
                "> `!serveurinfo` : Infos du serveur\n"
                "> `!8ball` & `!roll` : Fun\n"
                "> `!clear` : Modération"
            )
            await message.reply(help_msg)

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓 Calcul...")
            lat = round((time.time() - s) * 1000)
            bot_stats["latency"] = f"{lat}ms"
            await m.edit(content=f"🏓 Pong ! `{lat}ms`")

        elif cmd == "!serveurinfo":
            s = message.server
            await message.reply(f"🏰 **{s.name}**\n👤 **Owner:** <@{s.owner_id}>\n👥 **Membres:** {len(s.members)}")

        elif cmd == "!uptime":
            upt = int(time.time() - bot_stats["start_time"])
            await message.reply(f"🕒 En ligne depuis : **{upt // 3600}h {(upt % 3600) // 60}m**.")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            amt = int(args[0]) if args and args[0].isdigit() else 10
            await message.channel.clear(min(amt, 100))

# --- GESTION DU CYCLE DE VIE ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token: return print("ERREUR: REVOLT_TOKEN manquant")

    while True:
        bot_stats["connected_to_stoat"] = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            print(f"Erreur session: {e}")
        
        await asyncio.sleep(15) # Pause avant relance

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Arrêt.")
