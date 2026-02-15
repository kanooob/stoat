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
    return "<body style='background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;'><h1>🦦 Stoat Bot : Actif</h1><p>Heure FR : OK</p></body>"

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
        self.loop_started = False

    async def on_ready(self):
        print(f"✅ Connecté en tant que : {self.user.name}")
        await self.send_log(f"🚀 **Bot Stoat en ligne !**\nHeure FR : `{get_fr_time().strftime('%H:%M:%S')}`")
        
        try:
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
        except: pass
        
        if not self.loop_started:
            self.loop_started = True
            self.loop.create_task(self.update_date_loop())

    async def update_date_loop(self):
        while True:
            try:
                current_date = get_fr_time().strftime("%d/%m/%Y")
                if current_date != self.last_date:
                    self.last_date = current_date
                    if "| !help" in self.custom_status:
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

    # --- ÉVÉNEMENTS ---
    async def on_message(self, message: revolt.Message):
        # Ignore les bots et les messages sans contenu
        if not message.author or message.author.bot or not message.content:
            return

        # Débug console : voir si le bot reçoit quelque chose
        print(f"📩 Message reçu de {message.author.name}: {message.content}")

        if not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!help":
            help_msg = (
                "### 🦦 **Stoat Bot Help**\n---\n"
                "🎮 **Fun** : `!8ball`, `!roll`, `!gif`\n"
                "🛠️ **Outils** : `!ping`, `!uptime`, `!avatar`, `!serverinfo`\n"
                "🛡️ **Staff** : `!clear`, `!setstatus`\n---\n"
                "*Fait par Galaxie_s9*"
            )
            await message.reply(help_msg)

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            await m.edit(content=f"🏓 Pong ! `{round((time.time()-s)*1000)}ms`")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis : **{h}h {m}m**.")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 **{u.name}**\n{u.avatar_url}")

        elif cmd == "!serverinfo":
            s = message.server
            await message.reply(f"🏘️ **{s.name}**\n👥 Membres : `{len(s.members)}` \n👑 Owner : <@{s.owner_id}>")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose une question !")
            rep = ["Oui", "Non", "Peut-être", "C'est probable", "Absolument pas"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!roll":
            v = int(args[0]) if args and args[0].isdigit() else 6
            await message.reply(f"🎲 | `{random.randint(1, v)}` (1-{v})")

        elif cmd == "!gif":
            q = "+".join(args) if args else "otter"
            await message.reply(f"🎬 https://tenor.com/search/{q}-gifs")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
                await self.send_log(f"🧹 **Nettoyage** : {amt} messages par {message.author.name}")
            except: pass

        elif cmd == "!setstatus":
            if not message.author.get_permissions().manage_server: return
            self.custom_status = " ".join(args) if args else f"{self.last_date} | !help"
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
            await message.reply("✅")

# --- LANCEMENT ---
async def main():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ Token manquant !")
        return

    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Erreur fatale : {e}")
