import { Client as DiscordClient, Collection, GatewayIntentBits } from "discord.js";
import { Client as RevoltClient } from "revolt.js";
import { REST } from "@discordjs/rest";
import npmlog from "npmlog";
import https from "https"; // Pour le test de connexion

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
    npmlog.info("Bot", "--- DÉBUT DIAGNOSTIC ---");
    
    // Test réseau : Est-ce que le bot peut sortir sur le web ?
    https.get('https://google.com', (res) => {
      npmlog.info("Réseau", `Test Google: ${res.statusCode} (Internet OK)`);
    }).on('error', (e) => {
      npmlog.error("Réseau", "INTERNET BLOQUÉ : Render ne laisse pas sortir le bot.");
    });

    this.setupDiscordBot();
    this.setupRevoltBot();
  }

  setupDiscordBot() {
    npmlog.info("Discord", "Création du client...");
    
    this.discord = new DiscordClient({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMessages,
      ],
      // Désactivation du cache pour forcer la connexion brute
      makeCache: () => new Collection(), 
    });

    this.discord.once("ready", () => {
      npmlog.info("Discord", `!!! SUCCÈS TOTAL !!! Connecté : ${this.discord.user?.tag}`);
    });

    // Écouter TOUTES les erreurs possibles
    this.discord.on("error", (err) => npmlog.error("Discord", "ERREUR SOCKET:", err));
    this.discord.on("debug", (msg) => {
        if(msg.includes("identif")) npmlog.info("Discord-Debug", msg);
    });

    npmlog.info("Discord", "Lancement de login()...");
    const token = process.env.DISCORD_TOKEN?.trim();
    
    if(!token) {
        npmlog.error("Discord", "ERREUR: Le Token est vide dans les variables Render !");
        return;
    }

    this.discord.login(token).then(() => {
        npmlog.info("Discord", "Promesse login() résolue.");
    }).catch((err) => {
        npmlog.error("Discord", "LOGIN REJETÉ PAR DISCORD:");
        npmlog.error("Discord", err.message);
    });
  }

  setupRevoltBot() {
    this.revolt = new RevoltClient({ 
        apiURL: process.env.API_URL || "https://api.revolt.chat",
        autoReconnect: true 
    });

    this.revolt.once("ready", () => {
      npmlog.info("Revolt", `Connecté en tant que ${this.revolt.user?.username}`);
    });

    this.revolt.loginBot(process.env.REVOLT_TOKEN!).catch(e => npmlog.error("Revolt", e));
  }
}
