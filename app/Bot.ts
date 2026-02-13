import { Client as DiscordClient, Collection, GatewayIntentBits, Partials } from "discord.js";
import { Client as RevoltClient } from "revolt.js";
import { REST } from "@discordjs/rest";
import npmlog from "npmlog";
import https from "https";

import { Main } from "./Main";
import { handleDiscordMessage, initiateDiscordChannel } from "./discord";
import { handleRevoltMessage } from "./revolt";
import { slashCommands } from "./discord/commands";
import UniversalExecutor from "./universalExecutor";
import { revoltCommands } from "./revolt/commands";

export class Bot {
  private discord: DiscordClient;
  private revolt: RevoltClient;
  private commands: Collection<string, any>;
  private rest: REST;
  private executor: UniversalExecutor;

  constructor(private usingJsonMappings: boolean) {}

  public async start() {
    npmlog.info("Bot", "--- DÉBUT DU DERNIER DIAGNOSTIC ---");
    
    // Test de sortie internet
    https.get('https://google.com', (res) => {
      npmlog.info("Réseau", `Connexion sortante : OK (Code ${res.statusCode})`);
    }).on('error', (e) => {
      npmlog.error("Réseau", "ERREUR : Sortie internet bloquée.");
    });

    this.setupDiscordBot();
    this.setupRevoltBot();
  }

  setupDiscordBot() {
    npmlog.info("Discord", "Initialisation du client...");
    
    this.discord = new DiscordClient({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.DirectMessages,
      ],
      partials: [Partials.Channel, Partials.Message],
      makeCache: () => new Collection(), 
    });

    // Événement de succès
    this.discord.once("ready", () => {
      npmlog.info("Discord", "✅ VICTOIRE ! Le bot est en ligne.");
      npmlog.info("Discord", `Connecté en tant que : ${this.discord.user?.tag}`);
    });

    // Capture des messages de DEBUG (Crucial maintenant)
    this.discord.on("debug", (info) => {
      if (info.includes("Heartbeat") || info.includes("Identif") || info.includes("Session")) {
        npmlog.info("Discord-Debug", info);
      }
    });

    this.discord.on("error", (err) => {
      npmlog.error("Discord", "ERREUR DÉTECTÉE :");
      npmlog.error("Discord", err.message);
    });

    npmlog.info("Discord", "Appel de login()...");
    const token = process.env.DISCORD_TOKEN?.trim();

    if (!token) {
      npmlog.error("Discord", "Le Token est manquant dans les variables Render.");
      return;
    }

    this.discord.login(token).catch((err) => {
      npmlog.error("Discord", "LE LOGIN A ÉCHOUÉ :");
      npmlog.error("Discord", err.message);
    });
  }

  setupRevoltBot() {
    this.revolt = new RevoltClient({ 
        apiURL: process.env.API_URL || "https://api.revolt.chat",
        autoReconnect: true 
    });

    this.revolt.once("ready", () => {
      npmlog.info("Revolt", "✅ Revolt est connecté.");
    });

    this.revolt.loginBot(process.env.REVOLT_TOKEN!).catch(e => {
        npmlog.error("Revolt", "Erreur :");
        npmlog.error("Revolt", e.message);
    });
  }
}
