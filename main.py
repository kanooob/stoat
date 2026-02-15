import os
import asyncio
import threading
import random
from flask import Flask
import revolt
import config  # Importe tes IDs depuis config.py

# --- PARTIE WEB (Indispensable pour Render & UptimeRobot) ---
app = Flask(__name__)

@app.route('/')
def home():
    return """
    <body style="background:#121212;color:#00d1b2;text-align:center;padding:50px;font-family:sans-serif;">
        <h1 style="border:2px solid #00d1b2;display:inline-block;padding:20px;border-radius:15px;">🦦 Stoat Bot : Actif</h1>
        <p style="font-size:1.2em;">L'hermine est en ligne et surveille Revolt.</p>
    </body>
    """

def run_flask():
    # Render définit automatiquement un PORT, sinon on utilise 8080
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT (REVOLT) ---
class StoatBot(revolt.Client):
    
    async def on_ready(self):
        print(f"✅ Connecté en tant que {self.user.name}")
        print("🦦 L'hermine est sortie de son terrier !")

    # --- SYSTÈME D'ACCUEIL ---
    async def on_member_join(self, member: revolt.Member):
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            # Envoi du message configuré
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
        
        # Attribution automatique des rôles
        for role_id in config.AUTO_ROLES:
            try:
                await member.add_role(role_id)
            except Exception as e:
                print(f"⚠️ Erreur Auto-Role ({role_id}) : {e}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        # On ignore les messages des bots et ceux qui ne commencent pas par !
        if message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        base = parts[0].lower()

        # --- COMMANDES FUN ---
        if base == "!ping":
            await message.reply("Pong ! 🦦")

        elif base == "!coinflip":
            res = random.choice(["Pile", "Face"])
            await message.reply(f"🪙 La pièce tourne... et tombe sur : **{res}** !")

        elif base == "!avatar":
            user = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 Avatar de **{user.name}** : {user.avatar_url}")

        elif base == "!serverinfo":
            s = message.server
            await message.reply(f"🏠 **Serveur :** {s.name}\n👥 **Membres :** {len(s.members)}\n🆔 **ID :** `{s.id}`")

        # --- COMMANDES MODÉRATION (SÉCURISÉES) ---
        elif base == "!clear":
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Tu n'as pas la permission de gérer les messages.")
            
            try:
                amount = int(parts[1]) if len(parts) > 1 else 10
                amount = min(amount, 100) # Limite de sécurité
                await message.channel.clear(amount)
                await message.channel.send(f"🧹 **{amount}** messages balayés !", delete_after=5)
            except:
                await message.reply("Usage : `!clear [nombre]`")

        elif base == "!kick":
            if not message.author.get_permissions().kick_members:
                return await message.reply("❌ Permission insuffisante pour expulser.")
            
            if message.mentions:
                target = message.mentions[0]
                try:
                    await target.kick()
                    await message.reply(f"🔨 **{target.name}** a été expulsé.")
                except:
                    await message.reply("❌ Impossible d'expulser ce membre.")
            else:
                await message.reply("Usage : `!kick @user`")

        elif base == "!help":
            help_text = (
                "**📜 Liste des commandes :**\n"
                "`!ping` - Test de réponse\n"
                "`!coinflip` - Pile ou Face\n"
                "`!avatar` - Voir l'avatar de quelqu'un\n"
                "`!serverinfo` - Infos sur le serveur\n"
                "`!clear [nb]` - Supprimer des messages (Modo)\n"
                "`!kick @user` - Expulser un membre (Modo)"
            )
            await message.reply(help_text)

# --- LANCEMENT ---
async def start():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : La variable d'environnement REVOLT_TOKEN est vide !")
        return

    # Utilisation de la session client moderne pour revolt.py
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token)
        await client.start()

if __name__ == "__main__":
    # Lancement du serveur Web Flask (Thread séparé)
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Lancement du bot Revolt
    try:
        asyncio.run(start())
    except KeyboardInterrupt:
        print("🔌 Déconnexion...")
