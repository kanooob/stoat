import os, asyncio, threading, random, time
from datetime import datetime
from flask import Flask
import revolt
import config

# --- PARTIE WEB ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "<body style='background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;'><h1>🦦 Stoat Bot : Actif</h1><p>Surveillance et Logs en cours...</p></body>"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_timestamp = time.time()
        self.starboard_cache = set()
        self.last_date = datetime.now().strftime("%d/%m/%Y")
        self.custom_status = f"{self.last_date} | !help"
        self.loop_started = False

    async def on_ready(self):
        print(f"✅ Connecté : {self.user.name}")
        try:
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
        except: pass
        
        if not self.loop_started:
            self.loop_started = True
            asyncio.create_task(self.update_date_loop())

    async def update_date_loop(self):
        # Correction : On utilise une boucle simple, la déconnexion est gérée par start()
        while True:
            try:
                current_date = datetime.now().strftime("%d/%m/%Y")
                if current_date != self.last_date:
                    self.last_date = current_date
                    if "| !help" in self.custom_status:
                        self.custom_status = f"{current_date} | !help"
                        await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
                        await self.send_log(f"📅 **Mise à jour auto** : `{current_date}`")
            except:
                pass
            await asyncio.sleep(60)

    async def send_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try:
                ts = datetime.now().strftime("%H:%M:%S")
                await channel.send(f"🕒 `{ts}` | {text}")
            except: pass

    # --- ÉVÉNEMENTS ---
    async def on_message_delete(self, message: revolt.Message):
        if not message.author or message.author.bot: return
        await self.send_log(f"🗑️ **Message Supprimé**\n**Auteur :** {message.author.name}\n**Salon :** {message.channel.mention}\n**Contenu :** {message.content or '*Vide*'}")

    async def on_message_update(self, before: revolt.Message, after: revolt.Message):
        if not after.author or after.author.bot or before.content == after.content: return
        await self.send_log(f"📝 **Message Modifié**\n**Auteur :** {after.author.name}\n**Ancien :** {before.content}\n**Nouveau :** {after.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_log(f"📥 **Arrivée** : {member.mention}")
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            try: await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=len(member.server.members)))
            except: pass
        for r_id in config.AUTO_ROLES:
            try: await member.add_role(r_id)
            except: pass

    async def on_reaction_add(self, message: revolt.Message, user: revolt.User, emoji_id: str):
        if emoji_id == config.STAR_EMOJI:
            msg = await message.channel.fetch_message(message.id)
            count = msg.reactions.get(config.STAR_EMOJI, 0)
            if count >= config.STARBOARD_LIMIT and msg.id not in self.starboard_cache:
                sc = self.get_channel(config.STARBOARD_CHANNEL_ID)
                if sc:
                    self.starboard_cache.add(msg.id)
                    await sc.send(f"🌟 **Starboard** | {msg.author.mention}\n\n{msg.content}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"): return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!help":
            await message.reply(
                "### 🦦 **Stoat Bot Help**\n---\n"
                "> `!ping`, `!uptime`, `!avatar`, `!serverinfo`\n"
                "> `!8ball`, `!roll`, `!gif`\n"
                "> `!clear`, `!setstatus` (Staff)\n---\n"
                "*Fait par Galaxie_s9*"
            )

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            await m.edit(content=f"🏓 Pong ! `{round((time.time()-s)*1000)}ms`")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            await message.reply(f"🕒 En ligne depuis : **{upt//3600}h {(upt%3600)//60}m**.")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 **{u.name}**\n{u.avatar_url}")

        elif cmd == "!serverinfo":
            s = message.server
            await message.reply(f"🏘️ **{s.name}**\n👥 Membres : `{len(s.members)}`")

        elif cmd == "!8ball":
            rep = ["Oui", "Non", "Peut-être", "Certainement", "Même pas en rêve"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!roll":
            v = int(args[0]) if args and args[0].isdigit() else 6
            await message.reply(f"🎲 | `{random.randint(1, v)}`")

        elif cmd == "!gif":
            q = "+".join(args) if args else "otter"
            await message.reply(f"🎬 https://tenor.com/search/{q}-gifs")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
            except: pass

        elif cmd == "!setstatus":
            if not message.author.get_permissions().manage_server: return
            self.custom_status = " ".join(args) if args else f"{self.last_date} | !help"
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
            await message.reply("✅")

# --- LANCEMENT AVEC RECONNEXION ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    while True:
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            print(f"⚠️ Connexion perdue, tentative de reconnexion dans 5s... ({e})")
            await asyncio.sleep(5)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
