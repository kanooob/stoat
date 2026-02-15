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
    return "<body style='background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;'><h1>🦦 Stoat Bot : Actif</h1><p>Prêt à gérer Revolt/Stoat.</p></body>"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    async def on_ready(self):
        print(f"✅ Connecté en tant que : {self.user.name}")
        print("🦦 L'hermine est opérationnelle !")

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

        parts = message.content.split(" ")
        cmd = parts[0].lower()

        # --- FUN & UTILS ---
        if cmd == "!ping":
            start_time = time.time()
            msg = await message.reply("Calcul du ping... 🦦")
            # Calcul de la différence en millisecondes
            end_time = time.time()
            latency = round((end_time - start_time) * 1000)
            await msg.edit(content=f"Pong ! 🏓\nLatence : **{latency}ms**")

        elif cmd == "!coinflip":
            res = random.choice(["Pile", "Face"])
            await message.reply(f"🪙 La pièce est tombée sur : **{res}** !")

        elif cmd == "!avatar":
            user = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 Avatar de **{user.name}** : {user.avatar_url}")

        elif cmd == "!serverinfo":
            s = message.server
            await message.reply(f"🏠 **Serveur :** {s.name}\n👥 **Membres :** {len(s.members)}\n🆔 **ID :** `{s.id}`")

        # --- MODÉRATION ---
        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Tu n'as pas la permission 'Gérer les messages'.")
            try:
                amount = int(parts[1]) if len(parts) > 1 else 10
                amount = min(amount, 100)
                await message.channel.clear(amount)
                await message.channel.send(f"🧹 **{amount}** messages nettoyés !", delete_after=5)
            except:
                await message.reply("Usage : `!clear [nombre]`")

        elif cmd == "!kick":
            if not message.author.get_permissions().kick_members:
                return await message.reply("❌ Tu n'as pas la permission d'expulser.")
            if message.mentions:
                target = message.mentions[0]
                try:
                    await target.kick()
                    await message.reply(f"🔨 **{target.name}** a été expulsé.")
                except:
                    await message.reply("❌ Impossible d'expulser ce membre.")
            else:
                await message.reply("Usage : `!kick @user`")

        elif cmd == "!help":
            await message.reply("**Commandes Stoat :**\n`!ping`, `!coinflip`, `!avatar`, `!serverinfo`, `!clear [nb]`, `!kick @user`")

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : REVOLT_TOKEN manquant !")
        return

    async with revolt.utils.client_session() as session:
        # On force l'API Stoat pour éviter les problèmes de redirection
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
