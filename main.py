import os, asyncio, threading, random, time
from datetime import datetime
from flask import Flask
import revolt
import config

# --- PARTIE WEB (Keep-Alive) ---
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
        print(f"✅ Connecté en tant que : {self.user.name}")
        try:
            await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
        except: pass
        
        await self.send_log(f"🚀 **Bot Démarré**\nStatut actuel : `{self.custom_status}`")
        
        if not self.loop_started:
            self.loop_started = True
            asyncio.create_task(self.update_date_loop())

    # --- LOGIQUE AUTOMATIQUE ---
    async def update_date_loop(self):
        """Boucle qui met à jour la date dans le statut à minuit."""
        while not self.is_closed():
            current_date = datetime.now().strftime("%d/%m/%Y")
            if current_date != self.last_date:
                self.last_date = current_date
                # On ne met à jour que si l'utilisateur n'a pas mis un statut perso via !setstatus
                if "| !help" in self.custom_status or self.custom_status == "":
                    self.custom_status = f"{current_date} | !help"
                    try:
                        await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
                        await self.send_log(f"📅 **Mise à jour auto** : Statut actualisé au `{current_date}`")
                    except: pass
            await asyncio.sleep(60)

    async def send_log(self, text):
        """Envoie un message dans le salon de logs défini dans config.py."""
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try: 
                timestamp = datetime.now().strftime("%H:%M:%S")
                await channel.send(f"🕒 `{timestamp}` | {text}")
            except: pass

    # --- ÉVÉNEMENTS ---
    async def on_message_delete(self, message: revolt.Message):
        if message.author.bot: return
        auteur = message.author.name if message.author else "Inconnu"
        contenu = message.content if message.content else "*Contenu vide ou média*"
        await self.send_log(f"🗑️ **Message Supprimé**\n**Auteur :** {auteur}\n**Salon :** {message.channel.mention}\n**Contenu :** {contenu}")

    async def on_message_update(self, before: revolt.Message, after: revolt.Message):
        if after.author.bot or before.content == after.content: return
        await self.send_log(f"📝 **Message Modifié**\n**Auteur :** {after.author.name}\n**Ancien :** {before.content}\n**Nouveau :** {after.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_log(f"📥 **Arrivée** : {member.mention}")
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            try: await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
            except: pass
        for r_id in config.AUTO_ROLES:
            try: await member.add_role(r_id)
            except: pass

    async def on_member_leave(self, server: revolt.Server, user: revolt.User):
        await self.send_log(f"📤 **Départ** : {user.name}")

    async def on_reaction_add(self, message: revolt.Message, user: revolt.User, emoji_id: str):
        if emoji_id == config.STAR_EMOJI:
            msg = await message.channel.fetch_message(message.id)
            count = msg.reactions.get(config.STAR_EMOJI, 0)
            if count >= config.STARBOARD_LIMIT and msg.id not in self.starboard_cache:
                star_channel = self.get_channel(config.STARBOARD_CHANNEL_ID)
                if star_channel:
                    self.starboard_cache.add(msg.id)
                    await star_channel.send(f"🌟 **Starboard** | De {msg.author.mention} dans {msg.channel.mention}\n\n{msg.content}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        # --- MENU D'AIDE ---
        if cmd == "!help":
            help_msg = (
                "### 🦦 **Stoat Bot - Menu d'aide**\n"
                "--- \n"
                "🎮 **Divertissement**\n"
                "> `!8ball <question>` : Pose une question à l'hermine.\n"
                "> `!roll <nb>` : Lance un dé (par défaut 6).\n"
                "> `!gif <texte>` : Cherche un GIF sur Tenor.\n\n"
                "🛠️ **Utilitaires**\n"
                "> `!ping` : Latence du bot.\n"
                "> `!uptime` : Temps de fonctionnement.\n"
                "> `!avatar <@user>` : Affiche l'avatar d'un membre.\n"
                "> `!serverinfo` : Détails sur le serveur.\n\n"
                "🛡️ **Modération**\n"
                "> `!clear <nb>` : Supprime X messages (max 100).\n"
                "> `!setstatus <texte>` : Modifie le statut du bot.\n"
                "--- \n"
                "*Développé par Galaxie_s9*"
            )
            await message.reply(help_msg)

        # --- COMMANDES FUN ---
        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose-moi une question !")
            reponses = ["C'est certain 🦦", "Sans aucun doute", "Demande plus tard", "Ma réponse est non", "Très probable", "Je n'en suis pas sûr..."]
            await message.reply(f"🎱 **{message.author.name}**, ma réponse est : **{random.choice(reponses)}**")

        elif cmd == "!roll":
            try:
                max_v = int(args[0]) if args else 6
                if max_v < 1: throw_err
                await message.reply(f"🎲 **Dé :** Tu as obtenu un `{random.randint(1, max_v)}` sur {max_v} !")
            except: await message.reply("❌ Précise un nombre entier positif (ex: !roll 20).")

        elif cmd == "!gif":
            search = "+".join(args) if args else "otter"
            await message.reply(f"🎬 **GIF pour '{' '.join(args) if args else 'loutre'}'** :\nhttps://tenor.com/search/{search}-gifs")

        # --- COMMANDES TOOLS ---
        elif cmd == "!ping":
            start = time.time()
            m = await message.reply("🏓 Calcul...")
            end = time.time()
            await m.edit(content=f"🏓 **Pong !** Latence : `{round((end - start) * 1000)}ms`")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            jours = upt // 86400
            heures = (upt % 86400) // 3600
            minutes = (upt % 3600) // 60
            await message.reply(f"🕒 Je suis en ligne depuis : **{jours}j {heures}h {minutes}m**.")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 **Avatar de {u.name}** :\n{u.avatar_url}")

        elif cmd == "!serverinfo":
            s = message.server
            creation_date = datetime.fromtimestamp(s.id.timestamp / 1000).strftime("%d/%m/%Y")
            info = (
                f"🏘️ **Nom du Serveur :** {s.name}\n"
                f"👑 **Propriétaire :** <@{s.owner_id}>\n"
                f"👥 **Membres :** `{len(s.members)}` membres\n"
                f"📅 **Créé le :** {creation_date}"
            )
            await message.reply(info)

        # --- COMMANDES MODO/ADMIN ---
        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages:
                return await message.reply("❌ Permission 'Gérer les messages' manquante.")
            try:
                amt = int(args[0]) if args else 10
                if amt > 100: amt = 100  # Limite de sécurité
                await message.channel.clear(amt)
                m = await message.channel.send(f"🧹 **{amt}** messages ont été balayés !")
                await asyncio.sleep(3)
                await m.delete()
                await self.send_log(f"🧹 **Nettoyage** : {amt} messages supprimés par {message.author.name} dans {message.channel.mention}")
            except: pass

        elif cmd == "!setstatus":
            if not message.author.get_permissions().manage_server:
                return await message.reply("❌ Permission 'Gérer le serveur' manquante.")
            new_status = " ".join(args) if args else f"{self.last_date} | !help"
            self.custom_status = new_status
            try:
                await self.edit_status(text=new_status, presence=revolt.PresenceType.online)
                await message.reply(f"✅ Statut mis à jour : `{new_status}`")
            except: 
                await message.reply("❌ Erreur lors du changement de statut.")

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : Le token est introuvable dans les variables d'environnement.")
        return
        
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        print("👋 Bot arrêté manuellement.")
