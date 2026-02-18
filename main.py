import os, asyncio, threading, random, time
from datetime import datetime
import pytz
from flask import Flask
import revolt
import config

# --- VARIABLES D'ÉTAT ---
bot_stats = {
    "online": True,
    "connected_to_stoat": False,
    "last_command": "Aucune",
    "latency": "0ms",
    "start_time": time.time()
}

FRANCE_TZ = pytz.timezone('Europe/Paris')

def get_fr_time_info():
    now = datetime.now(FRANCE_TZ)
    offset = now.utcoffset().total_seconds() / 3600
    utc_str = f"UTC+{int(offset)}" if offset > 0 else f"UTC{int(offset)}"
    return now, utc_str

# --- PARTIE WEB ---
app = Flask(__name__)

@app.route('/')
def home(): 
    is_connected = bot_stats["connected_to_stoat"]
    status_stoat = "✅ Connecté" if is_connected else "❌ Déconnecté"
    color = "#2ecc71" if is_connected else "#e74c3c"
    upt = int(time.time() - bot_stats["start_time"])
    h, r = divmod(upt, 3600)
    m, s = divmod(r, 60)

    return f"""
    <html>
        <head><title>Stoat Bot</title><meta http-equiv="refresh" content="30"></head>
        <body style="font-family: sans-serif; background: #121212; color: white; display: flex; justify-content: center; align-items: center; height: 100vh;">
            <div style="background: #1e1e1e; padding: 30px; border-radius: 15px; border-top: 5px solid {color};">
                <h2>🦦 Stoat Status</h2>
                <p>État : <b style="color:{color};">{status_stoat}</b></p>
                <p>Uptime : {h}h {m}m {s}s</p>
                <p>Dernier : <code>{bot_stats['last_command']}</code> | Ping : {bot_stats['latency']}</p>
            </div>
        </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- LE BOT STOAT ---
class StoatBot(revolt.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_date = datetime.now(FRANCE_TZ).strftime("%d/%m/%Y")

    async def on_ready(self):
        bot_stats["connected_to_stoat"] = True
        await self.send_system_log("⚙️ **Système :** Bot allumé et prêt.")
        asyncio.create_task(self.health_check_loop())
        asyncio.create_task(self.daily_task())

    async def send_system_log(self, text):
        channel = self.get_channel(config.SYSTEM_LOGS_ID)
        if channel:
            now, _ = get_fr_time_info()
            try: await channel.send(f"🖥️ `[{now.strftime('%H:%M:%S')}]` {text}")
            except: print(f"Impossible d'envoyer log système: {text}")

    async def send_event_log(self, text):
        channel = self.get_channel(config.LOGS_CHANNEL_ID)
        if channel:
            now, _ = get_fr_time_info()
            try: await channel.send(f"📜 `[{now.strftime('%H:%M:%S')}]` {text}")
            except Exception as e: await self.send_system_log(f"⚠️ Erreur Envoi Log Event: {e}")

    # --- ÉVÉNEMENTS (Correction Welcome/Edit) ---
    async def on_message_delete(self, message: revolt.Message):
        try:
            if not message.author or message.author.bot: return
            await self.send_event_log(f"🗑️ **Message supprimé** | `{message.author.name}` dans <#{message.channel.id}>\n> {message.content}")
        except Exception as e: await self.send_system_log(f"❌ Erreur on_message_delete: {e}")

    async def on_message_edit(self, message: revolt.Message, old_content: str):
        try:
            if not message.author or message.author.bot: return
            await self.send_event_log(f"📝 **Message édité** | `{message.author.name}`\n**Avant :** {old_content}\n**Après :** {message.content}")
        except Exception as e: await self.send_system_log(f"❌ Erreur on_message_edit: {e}")

    async def on_member_join(self, member: revolt.Member):
        try:
            await self.send_event_log(f"📥 **Bienvenue** | `{member.name}` a rejoint le serveur !")
        except Exception as e: await self.send_system_log(f"❌ Erreur on_member_join: {e}")

    async def on_member_leave(self, member: revolt.Member):
        try:
            await self.send_event_log(f"📤 **Départ** | `{member.name}` a quitté le serveur.")
        except Exception as e: await self.send_system_log(f"❌ Erreur on_member_leave: {e}")

    # --- COMMANDES ---
    async def on_message(self, message: revolt.Message):
        if not message.author or message.author.bot or not message.content.startswith("!"): return
        
        parts = message.content.split(" ")
        cmd = parts[0].lower()
        args = parts[1:]
        bot_stats["last_command"] = cmd

        try:
            if cmd == "!help":
                await message.reply("### 🦦 **Aide**\n`!ping`, `!uptime`, `!serveurinfo`, `!8ball`, `!roll`, `!clear`")

            elif cmd == "!ping":
                s = time.time()
                m = await message.reply("🏓...")
                bot_stats["latency"] = f"{round((time.time() - s) * 1000)}ms"
                await m.edit(content=f"🏓 Pong ! `{bot_stats['latency']}`")

            elif cmd == "!8ball":
                if not args: return await message.reply("🔮 Pose une question !")
                reps = ["Oui", "Non", "C'est possible", "Je ne pense pas", "Absolument !", "Oublie ça."]
                await message.reply(f"🎱 | {random.choice(reps)}")

            elif cmd == "!roll":
                faces = int(args[0]) if args and args[0].isdigit() else 6
                await message.reply(f"🎲 | Résultat : **{random.randint(1, faces)}** (Dé {faces})")

            elif cmd == "!serveurinfo":
                s = message.server
                await message.reply(f"🏰 **{s.name}**\n👤 Owner: <@{s.owner_id}>\n👥 Membres: {len(s.members)}")

            elif cmd == "!uptime":
                upt = int(time.time() - bot_stats["start_time"])
                await message.reply(f"🕒 En ligne depuis : **{upt // 3600}h {(upt % 3600) // 60}m**.")

            elif cmd == "!clear":
                if not message.author.get_permissions().manage_messages:
                    return await message.reply("❌ Tu n'as pas la permission `Gérer les messages`.")
                amt = int(args[0]) if args and args[0].isdigit() else 10
                await message.channel.clear(min(amt, 100))
                await self.send_system_log(f"🧹 **Modération :** {amt} messages supprimés par `{message.author.name}`.")

        except Exception as e:
            await self.send_system_log(f"⚠️ **Erreur Commande `{cmd}` :**\n`{e}`")

    # --- MAINTENANCE ---
    async def health_check_loop(self):
        while True:
            await asyncio.sleep(300)
            try:
                await self.fetch_user(self.user.id)
                bot_stats["connected_to_stoat"] = True
            except:
                bot_stats["connected_to_stoat"] = False
                await self.stop()

    async def daily_task(self):
        while True:
            await asyncio.sleep(3600)
            await self.stop()

# --- LANCEMENT ---
async def start_bot():
    token = os.environ.get("REVOLT_TOKEN")
    while True:
        bot_stats["connected_to_stoat"] = False
        try:
            async with revolt.utils.client_session() as session:
                client = StoatBot(session, token, api_url="https://api.stoat.chat")
                await client.start()
        except Exception as e:
            print(f"Relance... {e}")
            await asyncio.sleep(15)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(start_bot())
