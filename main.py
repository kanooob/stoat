import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# --- VARIABLES D'ÉTAT POUR LE SITE ---
bot_stats = {
    "online": False,
    "connected_to_stoat": False,
    "last_command": "Aucune",
    "latency": "N/A"
}

# Configuration du fuseau horaire français
FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time_info():
    """Retourne l'heure actuelle et le décalage UTC formaté (UTC+1/UTC+2)"""
    now = datetime.now(FRANCE_TZ)
    offset = now.utcoffset().total_seconds() / 3600
    utc_str = f"UTC+{int(offset)}" if offset > 0 else f"UTC{int(offset)}"
    return now, utc_str

# --- PARTIE WEB (FLASK) ---
app = Flask(__name__)

@app.route('/')
def home(): 
    status_stoat = "✅ Connecté" if bot_stats["connected_to_stoat"] else "❌ Déconnecté"
    return f"""
    <html>
        <head><title>Stoat Bot Status</title></head>
        <body style="font-family: sans-serif; background: #1e1e1e; color: white; padding: 20px;">
            <h2>🦦 Stoat Bot Status</h2>
            <hr>
            <p>🌐 <b>Bot en ligne :</b> ✅ Oui</p>
            <p>📡 <b>Connexion Stoat :</b> {status_stoat}</p>
            <p>⚡ <b>Dernière commande :</b> <code>{bot_stats['last_command']}</code></p>
            <p>🏓 <b>Ping :</b> {bot_stats['latency']}</p>
            <br>
            <small><i>Actualisé au chargement de la page.</i></small>
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
        self.start_timestamp = time.time()
        now, _ = get_fr_time_info()
        self.last_date = now.strftime("%d/%m/%Y")

    async def on_ready(self):
        bot_stats["connected_to_stoat"] = True
        print(f"✅ Bot connecté sur Stoat.chat : {self.user.name}")
        now, utc_offset = get_fr_time_info()
        time_str = now.strftime('%H:%M:%S')
        
        await self.send_log(f"🚀 **Bot Stoat en ligne !**\nHeure : `{time_str}` ({utc_offset})")
        
        try:
            await self.edit_status(text=f"{self.last_date} | !help", presence=revolt.PresenceType.online)
        except: pass
        
        asyncio.create_task(self.date_checker())

    async def date_checker(self):
        while True:
            await asyncio.sleep(60)
            now, _ = get_fr_time_info()
            now_date = now.strftime("%d/%m/%Y")
            if now_date != self.last_date:
                self.last_date = now_date
                try:
                    await self.edit_status(text=f"{now_date} | !help", presence=revolt.PresenceType.online)
                    await self.send_log(f"📅 Nouvelle journée : `{now_date}`")
                except: pass

    async def send_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try:
                now, _ = get_fr_time_info()
                ts = now.strftime("%H:%M:%S")
                await channel.send(f"🕒 `{ts}` | {text}")
            except: pass

    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content:
            return

        if not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        # Mise à jour de la dernière commande pour le site
        bot_stats["last_command"] = cmd

        if cmd == "!help":
            help_text = (
                "### 🦦 **Menu d'Aide - Stoat Bot**\n"
                "---\n"
                "🎮 **Divertissement**\n"
                "> `!8ball [question]` : Pose une question à la boule magique.\n"
                "> `!roll [nombre]` : Lance un dé (6 faces par défaut).\n"
                "\n"
                "🛠️ **Utilitaires**\n"
                "> `!ping` : Vérifie la latence du bot.\n"
                "> `!uptime` : Affiche le temps depuis l'allumage.\n"
                "\n"
                "🛡️ **Modération**\n"
                "> `!clear [nb]` : Supprime un nombre de messages.\n"
                "---\n"
                "*Besoin d'aide supplémentaire ? Contactez un administrateur.*"
            )
            await message.reply(help_text)

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            latency = round((time.time() - s) * 1000)
            bot_stats["latency"] = f"{latency}ms" # Mise à jour du ping pour le site
            await m.edit(content=f"🏓 Pong ! `{latency}ms`")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis : **{h}h {m}m**.")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose une question !")
            rep = ["Oui", "Non", "Peut-être", "C'est probable", "Absolument pas"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!roll":
            try:
                faces = int(args[0]) if args and args[0].isdigit() else 6
                if faces < 1: faces = 6
                resultat = random.randint(1, faces)
                await message.reply(f"🎲 | Tu as lancé un dé à {faces} faces et obtenu : **{resultat}**")
            except:
                await message.reply("🎲 | Erreur lors du lancer de dé.")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
            except Exception as e:
                print(f"Erreur clear: {e}")

# --- LANCEMENT AVEC SECURITE RECONNEXION ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : REVOLT_TOKEN manquant !")
        return

    while True:
        bot_stats["connected_to_stoat"] = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                print("📡 Tentative de connexion à Stoat.chat...")
                await client.start()
        except Exception as e:
            print(f"💥 Erreur de connexion : {e}")
            print("⏳ Nouvelle tentative de reconnexion dans 20 secondes...")
            await asyncio.sleep(20)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("Arrêt manuel du bot.")
