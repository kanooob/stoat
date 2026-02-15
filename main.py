import os
import asyncio
import threading
import random
from flask import Flask
import revolt
import config

# --- PARTIE WEB (Pour Render & Uptime) ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <body style="background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;">
        <h1>🦦 Stoat Bot : Actif</h1>
        <p>Statut : En ligne et opérationnel sur Revolt.</p>
    </body>
    """

def run_flask():
    # Render utilise le port 8080 ou celui défini en variable d'environnement
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
            # Utilisation de .format pour le message de config
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
        
        for role_id in config.AUTO_ROLES:
            try: 
                await member.add_role(role_id)
            except Exception as e: 
                print(f"Erreur Auto-Role : {e}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        # On ignore les bots et les messages sans préfixe
        if message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        base = parts[0].lower()

        # --- FUN ---
        if base == "!ping":
            await message.reply("Pong ! 🦦")

        elif base == "!coinflip":
            res = random.choice(["Pile", "Face"])
            await message.reply(f"La pièce est tombée sur... **{res}** ! 🪙")

        elif base == "!serverinfo":
            server = message.server
            await message.reply(f"**Serveur :** {server.name}\n**Membres :** {len(server.members)}\n**ID :** `{server.id}`")

        elif base == "!avatar":
            user = message.mentions[0] if message.mentions else message.author
            await message.reply(f"Voici l'avatar de **{user.name}** : {user.avatar_url}")

        # --- MODERATION ---
        elif base == "!clear":
            # Vérification des permissions
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Tu n'as pas la permission 'Gérer les messages'.")
            
            try:
                count = int(parts[1]) if len(parts) > 1 else 10
                # On limite à 100 max pour éviter les abus
                count = min(count, 100)
                await message.channel.clear(count)
                # Message temporaire (note: delete_after peut varier selon l'instance)
                await message.channel.send(f"🧹 **{count}** messages balayés !")
            except:
                await message.reply("Utilise : `!clear [nombre]`")

        elif base == "!kick":
            if not message.author.get_permissions().kick_members:
                return await message.reply("❌ Tu n'as pas la permission d'expulser.")
            
            if message.mentions:
                target = message.mentions[0]
                try:
                    await target.kick()
                    await message.reply(f"🔨 **{target.name}** a été renvoyé dans son terrier.")
                except:
                    await message.reply("Échec : Je n'ai pas les permissions nécessaires sur ce membre.")
            else:
                await message.reply("Mentionne quelqu'un : `!kick @user`")

        elif base == "!help":
            await message.reply("**Commandes Stoat :**\n`!ping`, `!coinflip`, `!serverinfo`, `!avatar`, `!clear`, `!kick`")

# --- LANCEMENT ---
async def start():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("CRITICAL: REVOLT_TOKEN est introuvable dans les variables d'environnement.")
        return

    # Correction de l'AttributeError : on initialise le client directement
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token)
        await client.start()

if __name__ == "__main__":
    # 1. Lancer le serveur Flask dans un thread à part
    web_thread = threading.Thread(target=run_flask, daemon=True)
    web_thread.start()
    
    # 2. Lancer le bot Revolt
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("Arrêt du bot...")
