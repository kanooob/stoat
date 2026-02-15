import os
import asyncio
import threading
import random
from flask import Flask
import revolt
import config

# --- PARTIE WEB ---
app = Flask(__name__)

@app.route('/')
def home():
    return "🦦 Stoat Bot est en ligne !"

def run_flask():
    # Render utilise souvent le port 10000 par défaut
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    async def on_ready(self):
        print("✅ L'hermine est sortie de son terrier !")
        print(f"Connecté en tant que : {self.user.name}")

    async def on_member_join(self, member: revolt.Member):
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
        
        for role_id in config.AUTO_ROLES:
            try: await member.add_role(role_id)
            except Exception as e: print(f"Erreur rôle: {e}")

    async def on_message(self, message: revolt.Message):
        if message.author.bot or not message.content.startswith("!"):
            return

        content = message.content.lower()
        
        if content == "!ping":
            await message.reply("Pong ! 🦦")
        
        elif content == "!coinflip":
            await message.reply(f"🪙 C'est **{random.choice(['Pile', 'Face'])}** !")

        elif content == "!help":
            await message.reply("Commandes : `!ping`, `!coinflip`, `!avatar`, `!serverinfo`, `!clear`, `!kick`")

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : REVOLT_TOKEN manquant !")
        return

    # Utilisation de l'API Stoat (anciennement Revolt)
    # Si l'URL par défaut ne répond pas, on force celle de stoat
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

def main():
    # Lancer Flask dans un thread pour ne pas bloquer le bot
    t = threading.Thread(target=run_flask)
    t.daemon = True
    t.start()

    # Lancer le bot de manière asynchrone
    asyncio.run(start_bot())

if __name__ == "__main__":
    main()
