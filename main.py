import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# Configuration du fuseau horaire français
FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time():
    return datetime.now(FRANCE_TZ)

# --- PARTIE WEB (FLASK) ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Stoat Bot is running"

def run_flask():
    # Render a besoin que ce port soit ouvert
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_timestamp = time.time()
        self.last_date = get_fr_time().strftime("%d/%m/%Y")

    async def on_ready(self):
        print(f"✅ Bot connecté sur Stoat.chat en tant que : {self.user.name}")
        
        # Log de démarrage dans le salon de logs
        await self.send_log(f"🚀 **Bot Stoat en ligne !**\nHeure FR : `{get_fr_time().strftime('%H:%M:%S')}`")
        
        # Mise à jour du statut initial
        try:
            await self.edit_status(text=f"{self.last_date} | !help", presence=revolt.PresenceType.online)
        except: pass
        
        # Lancement de la boucle de changement de date
        asyncio.create_task(self.date_checker())

    async def date_checker(self):
        """Boucle qui vérifie le changement de jour chaque minute."""
        while True:
            await asyncio.sleep(60)
            now_date = get_fr_time().strftime("%d/%m/%Y")
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
                ts = get_fr_time().strftime("%H:%M:%S")
                await channel.send(f"🕒 `{ts}` | {text}")
            except: pass

    async def on_message(self, message: revolt.Message):
        # Ignore les bots et les messages vides
        if not message.author or message.author.bot or not message.content:
            return

        # Très important pour débugger : on affiche tout dans la console Render
        print(f"📩 [{message.author.name}] : {message.content}")

        if not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        # --- COMMANDES ---
        if cmd == "!help":
            await message.reply("### 🦦 **Stoat Bot Help**\n---\n`!ping`, `!avatar`, `!uptime`, `!8ball`, `!roll`, `!clear`")

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            latency = round((time.time() - s) * 1000)
            await m.edit(content=f"🏓 Pong ! `{latency}ms`")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            asset = u.avatar
            url = asset.url if asset else "Cet utilisateur n'a pas d'avatar."
            await message.reply(f"📷 **Avatar de {u.name}** :\n{url}")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis : **{h}h {m}m**.")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose une question !")
            rep = ["Oui", "Non", "Peut-être", "C'est probable", "Absolument pas"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
            except Exception as e:
                print(f"Erreur clear: {e}")

# --- LANCEMENT ---
async def main():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : Le token REVOLT_TOKEN est introuvable !")
        return

    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        print("📡 Lancement de la connexion...")
        await client.start()

if __name__ == "__main__":
    # 1. On lance le serveur Web en arrière-plan
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()
    
    # 2. On lance le bot
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Erreur lors de l'exécution : {e}")
