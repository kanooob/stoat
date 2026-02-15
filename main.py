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

# --- PARTIE WEB ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Stoat Bot Online"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_timestamp = time.time()
        self.last_date = get_fr_time().strftime("%d/%m/%Y")
        self.custom_status = f"{self.last_date} | !help"

    async def on_ready(self):
        print(f"✅ Connecté : {self.user.name}")
        await self.send_log(f"🚀 **Bot Stoat en ligne !**\nHeure FR : `{get_fr_time().strftime('%H:%M:%S')}`")
        try:
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
        except: pass
        # Lancement de la boucle de date proprement
        asyncio.create_task(self.update_date_loop())

    async def update_date_loop(self):
        while not self.is_closed():
            try:
                current_date = get_fr_time().strftime("%d/%m/%Y")
                if current_date != self.last_date:
                    self.last_date = current_date
                    self.custom_status = f"{current_date} | !help"
                    await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
            except: pass
            await asyncio.sleep(60)

    async def send_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try:
                ts = get_fr_time().strftime("%H:%M:%S")
                await channel.send(f"🕒 `{ts}` | {text}")
            except: pass

    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content: return
        if not message.content.startswith("!"): return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!help":
            await message.reply("### 🦦 **Stoat Bot Help**\n---\n🎮 **Fun** : `!8ball`, `!roll`, `!gif`\n🛠️ **Outils** : `!ping`, `!uptime`, `!avatar`, `!serverinfo`\n🛡️ **Staff** : `!clear`, `!setstatus`")

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            await m.edit(content=f"🏓 Pong ! `{round((time.time()-s)*1000)}ms`")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            url = u.avatar.url if u.avatar else "Pas d'avatar."
            await message.reply(f"📷 **{u.name}**\n{url}")

        elif cmd == "!8ball":
            rep = ["Oui", "Non", "Peut-être", "C'est probable", "Absolument pas"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            amt = int(args[0]) if args and args[0].isdigit() else 10
            await message.channel.clear(min(amt, 100))

# --- LANCEMENT ---
async def start_client():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : REVOLT_TOKEN manquant dans les variables Render !")
        return

    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        print("📡 Tentative de connexion à Stoat.chat...")
        await client.start()

if __name__ == "__main__":
    # On lance Flask dans un thread séparé
    threading.Thread(target=run_flask, daemon=True).start()
    
    # On lance le bot
    try:
        asyncio.run(start_client())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"💥 Erreur Critique : {e}")
