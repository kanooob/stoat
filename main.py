import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# Configuration du fuseau horaire français
FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time_info():
    """Retourne l'heure actuelle et le décalage UTC formaté (UTC+1/UTC+2)"""
    now = datetime.now(FRANCE_TZ)
    # Calcul du décalage en heures
    offset = now.utcoffset().total_seconds() / 3600
    utc_str = f"UTC+{int(offset)}" if offset > 0 else f"UTC{int(offset)}"
    return now, utc_str

# --- PARTIE WEB (FLASK) ---
app = Flask(__name__)
@app.route('/')
def home(): 
    return "Stoat Bot is running"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_timestamp = time.time()
        now, _ = get_fr_time_info()
        self.last_date = now.strftime("%d/%m/%Y")

    async def on_ready(self):
        print(f"✅ Bot connecté sur Stoat.chat : {self.user.name}")
        
        # Récupération de l'heure et du fuseau (UTC+1 ou +2)
        now, utc_offset = get_fr_time_info()
        time_str = now.strftime('%H:%M:%S')
        
        # Log de démarrage mis à jour selon ta demande
        await self.send_log(f"🚀 **Bot Stoat en ligne !**\nHeure : `{time_str}` ({utc_offset})")
        
        try:
            await self.edit_status(text=f"{self.last_date} | !help", presence=revolt.PresenceType.online)
        except: pass
        
        asyncio.create_task(self.date_checker())

    async def date_checker(self):
        while True:
            await asyncio.sleep(60)
            now, _ = get_fr_time_info()
            now_date = now.strftime("%d/%m/%Y")
            if now_date != self.last_date:
                self.last_date = now_date
                try:
                    await self.edit_status(text=f"{now_date} | !help", presence=revolt.PresenceType.online)
                    await self.send_log(f"📅 Nouvelle journée : `{now_date}`")
                except: pass

    async def send_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            try:
                now, _ = get_fr_time_info()
                ts = now.strftime("%H:%M:%S")
                await channel.send(f"🕒 `{ts}` | {text}")
            except: pass

    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content:
            return

        print(f"📩 [{message.author.name}] : {message.content}")

        if not message.content.startswith("!"):
            return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "!help":
            help_text = (
                "### 🦦 **Menu d'Aide - Stoat Bot**\n"
                "---\n"
                "🎮 **Divertissement**\n"
                "> `!8ball [question]` : Pose une question à la boule magique.\n"
                "> `!roll [nombre]` : Lance un dé (6 faces par défaut).\n"
                "\n"
                "🛠️ **Utilitaires**\n"
                "> `!ping` : Vérifie la latence du bot.\n"
                "> `!avatar [@user]` : Affiche l'avatar d'un membre.\n"
                "> `!uptime` : Affiche le temps depuis l'allumage.\n"
                "\n"
                "🛡️ **Modération**\n"
                "> `!clear [nb]` : Supprime un nombre de messages.\n"
                "---\n"
                "*Besoin d'aide supplémentaire ? Contactez un administrateur.*"
            )
            await message.reply(help_text)

        elif cmd == "!ping":
            s = time.time()
            m = await message.reply("🏓...")
            latency = round((time.time() - s) * 1000)
            await m.edit(content=f"🏓 Pong ! `{latency}ms`")

        elif cmd == "!avatar":
            u = message.mentions[0] if message.mentions else message.author
            url = u.avatar.url if u.avatar else "Cet utilisateur n'a pas d'avatar."
            await message.reply(f"📷 **Avatar de {u.name}** :\n{url}")

        elif cmd == "!uptime":
            upt = int(time.time() - self.start_timestamp)
            h, m = upt // 3600, (upt % 3600) // 60
            await message.reply(f"🕒 En ligne depuis : **{h}h {m}m**.")

        elif cmd == "!8ball":
            if not args: return await message.reply("🔮 Pose une question !")
            rep = ["Oui", "Non", "Peut-être", "C'est probable", "Absolument pas"]
            await message.reply(f"🎱 | {random.choice(rep)}")

        elif cmd == "!clear":
            if not message.author.get_permissions().manage_messages: return
            try:
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
            except Exception as e:
                print(f"Erreur clear: {e}")

# --- LANCEMENT ---
async def main():
    token = os.environ.get("REVOLT_TOKEN")
    if not token:
        print("❌ ERREUR : REVOLT_TOKEN manquant !")
        return

    async with revolt.utils.client_session() as session:
        client = StoatBot(session, token, api_url="https://api.stoat.chat")
        print("📡 Lancement de la connexion...")
        await client.start()

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"💥 Erreur : {e}")
