import os
import asyncio
import threading
import random
from flask import Flask
import revolt
import config

# --- PARTIE WEB (Pour Render) ---
app = Flask(__name__)
@app.route('/')
def home():
    return "<body style='background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;'><h1>🦦 Stoat Bot : Actif</h1><p>Prêt à gérer Revolt.</p></body>"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    
    async def on_ready(self):
        print(f"L'hermine {self.user.name} est sortie de son terrier !")

    # --- ACCUEIL & AUTO-ROLE ---
    async def on_member_join(self, member: revolt.Member):
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
        
        for role_id in config.AUTO_ROLES:
            try: await member.add_role(role_id)
            except: print(f"Erreur : Impossible de donner le rôle {role_id}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if message.author.bot or not message.content.startswith("!"):
            return

        cmd = message.content.split(" ")
        base = cmd[0].lower()

        # --- FUN ---
        if base == "!ping":
            await message.reply("Pong ! 🦦")

        elif base == "!coinflip":
            res = random.choice(["Pile", "Face"])
            await message.reply(f"La pièce est tombée sur... **{res}** ! 🪙")

        elif base == "!serverinfo":
            server = message.server
            await message.reply(f"**{server.name}**\nMembres : {len(server.members)}\nID : {server.id}")

        elif base == "!avatar":
            user = message.mentions[0] if message.mentions else message.author
            await message.reply(f"Voici l'avatar de **{user.name}** : {user.avatar_url}")

        # --- MODERATION (Commandes sensibles) ---
        elif base == "!clear":
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Désolé, tu n'as pas la permission de gérer les messages !")
            
            try:
                count = int(cmd[1]) if len(cmd) > 1 else 10
                await message.channel.clear(count)
                await message.channel.send(f"🧹 **{count}** messages ont été balayés par l'hermine !", delete_after=5)
            except:
                await message.reply("Erreur : Utilise `!clear [nombre]`")

        elif base == "!kick":
            if not message.author.get_permissions().kick_members:
                return await message.reply("❌ Tu n'as pas le droit d'expulser des gens !")
            
            if message.mentions:
                target = message.mentions[0]
                try:
                    await target.kick()
                    await message.reply(f"🔨 **{target.name}** a été expulsé par l'hermine.")
                except:
                    await message.reply("Je ne peux pas expulser ce membre (peut-être a-t-il plus de pouvoirs que moi).")
            else:
                await message.reply("Mentionne quelqu'un : `!kick @user`")

        elif base == "!help":
            await message.reply("**Commandes Stoat :**\n`!ping`, `!coinflip`, `!serverinfo`, `!avatar`, `!clear [nb]`, `!kick @user`")

# --- LANCEMENT ---
async def start():
    token = os.environ.get("REVOLT_TOKEN")
    async with revolt.Client(revolt.utils.HTTPClient(), token) as client:
        bot = StoatBot(client.http)
        await bot.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start())
