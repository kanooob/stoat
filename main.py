import config # Importation de ton fichier config

class MyBot(revolt.Client):
    # ... (reste du code)

    async def on_member_join(self, member: revolt.Member):
        # 1. Envoi du message de bienvenue
        channel = self.get_channel(config.WELCOME_CHANNEL_ID)
        if channel:
            # On compte les membres du serveur
            count = len(member.server.members)
            msg = config.WELCOME_MESSAGE.format(user=member.mention, count=count)
            await channel.send(msg)

        # 2. Attribution des rôles automatiques
        for role_id in config.AUTO_ROLES:
            try:
                # Note: Le bot doit avoir les permissions de gérer les rôles
                await member.add_role(role_id)
            except Exception as e:
                print(f"Erreur attribution rôle {role_id}: {e}")
