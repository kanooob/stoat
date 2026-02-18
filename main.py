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

# Configuration du fuseau horaire français
FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time_info():
    """Retourne l'heure actuelle et le décalage UTC formaté"""
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
    
    # Calcul de l'uptime précis
    upt = int(time.time() - bot_stats["start_time"])
    hours, remainder = divmod(upt, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    favicon_color = "2ecc71" if is_connected else "e74c3c"
    favicon_url = f"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%23{favicon_color}'/></svg>"
    
    alert_script = ""
    if not is_connected:
        alert_script = "<script>const audioCtx = new (window.AudioContext || window.webkitAudioContext)(); const oscillator = audioCtx.createOscillator(); const gainNode = audioCtx.createGain(); oscillator.connect(gainNode); gainNode.connect(audioCtx.destination); oscillator.frequency.setValueAtTime(440, audioCtx.currentTime); gainNode.gain.setValueAtTime(0.05, audioCtx.currentTime); oscillator.start(); oscillator.stop(audioCtx.currentTime + 0.2);</script>"

    return f"""
    <html>
        <head>
            <title>Stoat Bot Status</title>
            <meta http-equiv="refresh" content="30">
            <link rel="icon" href="{favicon_url}">
        </head>
        <body style="font-family: sans-serif; background: #1e1e1e; color: white; padding: 20px; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0;">
            <div style="background: #252525; padding: 30px; border-radius: 15px; border-top: 5px solid {color}; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
                <h2 style="margin-top: 0;">🦦 Stoat Bot Status</h2>
                <hr style="border: 0; border-top: 1px solid #444;">
                <p>🌐 <b>Bot en ligne :</b> ✅ Oui</p>
                <p>📡 <b>Connexion Stoat :</b> <span style="color: {color};">{status_stoat}</span></p>
                <p>🕒 <b>Uptime :</b> {uptime_str}</p>
                <p>⚡ <b>Dernière commande :</b> <code style="background: #000; padding: 3px 7px; border-radius: 5px;">{bot_stats['last_command']}</code></p>
                <p>🏓 <b>Ping :</b> <span style="color: #3498db;">{bot_stats['latency']}</span></p>
                <br>
                <small style="color: #777;"><i>Actualisé automatiquement toutes les 30s.</i></small>
            </div>
            {alert_script}
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
        now, _ = get_fr_time_info()
        self.last_date = now.strftime("%d/%m/%Y")

    async def on_ready(self):
        bot_stats["connected_to_stoat"] = True
        print(f"✅ Bot connecté sur Stoat.chat : {self.user.name}")
        
        # Log système d'allumage
        now, utc_offset = get_fr_time_info()
        await self.send_system_log(f"🚀 **Bot Stoat en ligne !**\nHeure : `{now.strftime('%H:%M:%S')}` ({utc_offset})")
        
        try:
            await self.edit_status(text=f"{self.last_date} | !help", presence=revolt.PresenceType.online)
        except: pass
        
        # Tâches de fond
        asyncio.create_task(self.date_checker())
        asyncio.create_task(self.health_check_task())
        asyncio.create_task(self.auto_reconnect_task())

    # --- SYSTEME DE LOGS SEPARES ---
    async def send_system_log(self, text):
        """Salon 1 : Maintenance, Allumage, Erreurs"""
        channel = self.get_channel(config.SYSTEM_LOGS_ID)
        if channel:
            try:
                now, _ = get_fr_time_info()
                await channel.send(f"🖥️ `[{now.strftime('%H:%M:%S')}]` {text}")
            except: pass

    async def send_event_log(self, text):
        """Salon 2 : Activité des membres et messages"""
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try:
                now, _ = get_fr_time_info()
                await channel.send(f"📜 `[{now.strftime('%H:%M:%S')}]` {text}")
            except: pass

    # --- SURVEILLANCE ET MAINTENANCE ---
    async def health_check_task(self):
        """Vérifie toutes les 5min si le bot répond à l'API"""
        while True:
            await asyncio.sleep(300)
            try:
                start = time.time()
                await self.fetch_user(self.user.id)
                bot_stats["latency"] = f"{round((time.time() - start) * 1000)}ms"
            except Exception as e:
                await self.send_system_log(f"⚠️ **Alerte :** Problème de réponse API ({e}). Reconnexion...")
                await self.stop()

    async def auto_reconnect_task(self):
        """Rafraîchit la session toutes les heures"""
        await asyncio.sleep(3600)
        await self.send_system_log("🔄 **Système :** Redémarrage de session programmé.")
        await self.stop()

    async def date_checker(self):
        """Met à jour la date dans le statut à minuit"""
        while True:
            await asyncio.sleep(60)
            now, _ = get_fr_time_info()
            now_date = now.strftime("%d/%m/%Y")
            if now_date != self.last_date:
                self.last_date = now_date
                try:
                    await self.edit_status(text=f"{now_date} | !help", presence=revolt.PresenceType.online)
                    await self.send_system_log(f"📅 Nouvelle journée : `{now_date}`")
                except: pass

    # --- LOGS D'ÉVÉNEMENTS ---
    async def on_message_delete(self, message: revolt.Message):
        if not message.author or message.author.bot: return
        await self.send_event_log(f"🗑️ **Message supprimé** de `{message.author.name}` dans <#{message.channel.id}>\n> {message.content}")

    async def on_message_edit(self, message: revolt.Message, old_content: str):
        if not message.author or message.author.bot: return
        if old_content == message.content: return
        await self.send_event_log(f"📝 **Message modifié** par `{message.author.name}`\n**Ancien :** {old_content}\n**Nouveau :** {message.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_event_log(f"📥 **Nouveau membre :** `{member.name}` a rejoint le serveur.")

    async def on_member_leave(self, member: revolt.Member):
        await self.send_event_log(f"📤 **Départ :** `{member.name}` a quitté le serveur.")

    # --- GESTION DES COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        bot_stats["last_command"] = cmd

        if cmd == "!help":
            help_text = (
                "### 🦦 **Menu d'Aide**\n---\n"
                "🎮 `!8ball`, `!roll` | 🛠️ `!ping`, `!uptime`, `!serveurinfo` | 🛡️ `!clear`"
            )
            await message.reply(help_text)

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            lat = round((time.time() - s) * 1000)
            bot_stats["latency"] = f"{lat}ms"
            await m.edit(content=f"🏓 Pong ! `{lat}ms`")

        elif cmd == "!serveurinfo":
            s = message.server
            await message.reply(f"### 🏰 **{s.name}**\n> 👑 **Owner :** <@{s.owner_id}>\n> 👥 **Membres :** {len(s.members)}\n> 💬 **Salons :** {len(s.channels)}")

        elif cmd == "!uptime":
            upt = int(time.time() - bot_stats["start_time"])
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis : **{h}h {m}m**.")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose une question !")
            await message.reply(f"🎱 | {random.choice(['Oui', 'Non', 'Peut-être', 'Probablement', 'Jamais'])}")

        elif cmd == "!roll":
            faces = int(args[0]) if args and args[0].isdigit() else 6
            await message.reply(f"🎲 | Face : **{random.randint(1, faces)}**")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
            except: pass

# --- LANCEMENT SÉCURISÉ ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token: return print("❌ REVOLT_TOKEN manquant !")

    while True:
        bot_stats["connected_to_stoat"] = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                print("📡 Connexion en cours...")
                await client.start()
        except Exception as e:
            print(f"💥 Erreur de session: {e}")
        
        print("⏳ Reconnexion dans 15s...")
        await asyncio.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Arrêt.")
