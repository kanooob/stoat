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
        await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
        await self.send_log(f"🚀 **Bot Démarré**\nStatut : `{self.custom_status}`")
        
        if not self.loop_started:
            self.loop_started = True
            asyncio.create_task(self.update_date_loop())

    async def update_date_loop(self):
        while not self.is_closed():
            current_date = datetime.now().strftime("%d/%m/%Y")
            if current_date != self.last_date:
                self.last_date = current_date
                self.custom_status = f"{current_date} | !help"
                try:
                    await self.edit_status(text=self.custom_status, presence=revolt.PresenceType.online)
                    await self.send_log(f"📅 **Mise à jour auto** : La date est maintenant `{current_date}`")
                except: pass
            await asyncio.sleep(60)

    async def send_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try: await channel.send(f"🕒 `{time.strftime('%H:%M:%S')}` | {text}")
            except: pass

    # --- ÉVÉNEMENTS ---
    async def on_message_delete(self, message: revolt.Message):
        if message.author.bot: return
        auteur = message.author.name if message.author else "Inconnu"
        contenu = message.content if message.content else "*Contenu introuvable*"
        await self.send_log(f"🗑️ **Message Supprimé**\n**Auteur :** {auteur}\n**Salon :** {message.channel.mention}\n**Contenu :** {contenu}")

    async def on_message_update(self, before: revolt.Message, after: revolt.Message):
        if after.author.bot or before.content == after.content: return
        await self.send_log(f"📝 **Message Modifié**\n**Auteur :** {after.author.name}\n**Ancien :** {before.content}\n**Nouveau :** {after.content}")

    async def on_member_join(self, member: revolt.Member):
        await self.send_log(f"📥 **Arrivée** : {member.mention}")
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            count = len(member.server.members)
            await channel.send(config.WELCOME_MESSAGE.format(user=member.mention, count=count))
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
                    await star_channel.send(f"🌟 **Star !** de {msg.author.mention}\n> {msg.content}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if message.author.bot or not message.content.startswith("!"):
            return

        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!help":
            help_msg = (
                "### 🦦 **Stoat Bot - Menu d'aide**\n"
                "--- \n"
                "🎮 **Divertissement**\n"
                "> `!8ball <question>` : Interroge l'hermine magique.\n"
                "> `!roll <nb>` : Lance un dé (ex: !roll 100).\n"
                "> `!gif <texte>` : Cherche un GIF sur Tenor.\n\n"
                "🛠️ **Utilitaires**\n"
                "> `!ping` : Affiche la latence du serveur.\n"
                "> `!uptime` : Temps depuis le dernier réveil.\n"
                "> `!avatar <@user>` : Vole l'avatar d'un membre.\n"
                "> `!serverinfo` : Infos sur le serveur actuel.\n\n"
                "🛡️ **Modération**\n"
                "> `!clear <nb>` : Supprime les messages (Modo).\n"
                "> `!setstatus <texte>` : Change le statut (Admin).\n"
                "--- \n"
                "*Bot fait par Galaxie_s9*"
            )
            await message.reply(help_msg)

        elif cmd == "!ping":
            st = time.time()
            m = await message.reply("🏓 Calcul...")
            lt = round((time.time() - st) * 1000)
            await m.edit(content=f"🏓 **Pong !** Latence : `{lt}ms`")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose-moi une question !")
            reponses = ["C'est certain 🦦", "Sans aucun doute", "Demande plus tard", "Ma réponse est non", "Très probable"]
            await message.reply(f"🎱 **Réponse :** {random.choice(reponses)}")

        elif cmd == "!roll":
            try:
                max_v = int(args[0]) if args else 6
                await message.reply(f"🎲 **Dé :** `{random.randint(1, max_v)}` (1-{max_v})")
            except: await message.reply("❌ Nombre invalide !")

        elif cmd == "!gif":
            search = "+".join(args) if args else "otter"
            await message.reply(f"🎬 **GIF :** https://tenor.com/search/{search}-gifs")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis **{h}h {m}m**.")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            await message.reply(f"📷 **Avatar de {u.name}** :\n{u.avatar_url}")

        elif cmd == "!serverinfo":
            s = message.server
            await message.reply(f"🏘️ **Serveur :** {s.name}\n👤 **Owner :** <@{s.owner_id}>\n👥 **Membres :** `{len(s.members)}`")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args else 10
                await message.channel.clear(amt)
                await self.send_log(f"🧹 **Nettoyage** : {amt} messages par {message.author.name}")
            except: pass

        elif cmd == "!setstatus":
            if not message.author.get_permissions().manage_server: return
            new_status = " ".join(args) if args else f"{self.last_date} | !help"
            self.custom_status = new_status
            await self.edit_status(text=new_status, presence=revolt.PresenceType.online)
            await message.reply(f"✅ Statut mis à jour.")

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        await client.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
