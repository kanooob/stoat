import os
import asyncio
import threading
import random
import time
from flask import Flask
import revolt
import config

# --- PARTIE WEB ---
app = Flask(__name__)
@app.route('/')
def home():
    return "🦦 Stoat Bot : Actif et surveillé par UptimeRobot."

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_timestamp = time.time()
        self.starboard_cache = set() # Pour éviter les doublons sur le Starboard

    async def on_ready(self):
        print(f"✅ Connecté : {self.user.name}")
        print("🦦 L'hermine est prête !")

    # --- STARBOARD ---
    async def on_reaction_add(self, message: revolt.Message, user: revolt.User, emoji_id: str):
        # On vérifie si c'est l'emoji de la config
        if emoji_id == config.STAR_EMOJI:
            # On récupère le message complet pour compter les réactions
            msg = await message.channel.fetch_message(message.id)
            count = 0
            for reaction in msg.reactions:
                if reaction == config.STAR_EMOJI:
                    count = msg.reactions[reaction]
            
            # Si on atteint la limite et que le message n'est pas déjà dans le cache
            if count >= config.STARBOARD_LIMIT and msg.id not in self.starboard_cache:
                star_channel = self.get_channel(config.STARBOARD_CHANNEL_ID)
                if star_channel:
                    self.starboard_cache.add(msg.id)
                    embed_text = (
                        f"🌟 **Nouveau message star !**\n"
                        f"Posté par {msg.author.mention} dans {msg.channel.mention}\n\n"
                        f"> {msg.content}\n\n"
                        f"[Aller au message]({msg.url})"
                    )
                    await star_channel.send(embed_text)

    # --- ACCUEIL ---
    async def on_member_join(self, member: revolt.Member):
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        cmd = parts[0].lower()

        if cmd == "!ping":
            st = time.time()
            m = await message.reply("Calcul...")
            lt = round((time.time() - st) * 1000)
            await m.edit(content=f"Pong ! 🏓 (**{lt}ms**)")

        elif cmd == "!uptime":
            uptime_sec = int(time.time() - self.start_timestamp)
            h = uptime_sec // 3600
            m = (uptime_sec % 3600) // 60
            s = uptime_sec % 60
            await message.reply(f"🦦 Je tourne depuis **{h}h {m}m {s}s**.\nStatut : [UptimeRobot](https://stats.uptimerobot.com/gZPMLgzGuw)")

        elif cmd == "!coinflip":
            await message.reply(f"🪙 **{random.choice(['Pile', 'Face'])}**")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 Avatar de **{u.name}** : {u.avatar_url}")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Permission refusée.")
            try:
                amt = int(parts[1]) if len(parts) > 1 else 10
                await message.channel.clear(amt)
            except: pass

        elif cmd == "!help":
            await message.reply("**Commandes :** `!ping`, `!uptime`, `!coinflip`, `!avatar`, `!clear`, `!serverinfo`")

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
