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
    npmlog.info("Bot", "--- DÉBUT DIAGNOSTIC ---");
    
    // Test réseau : Vérifier si la sortie vers le web est possible
    https.get('https://google.com', (res) => {
      npmlog.info("Réseau", `Test Google: ${res.statusCode} (Internet OK)`);
    }).on('error', (e) => {
      npmlog.error("Réseau", "INTERNET BLOQUÉ sur Render !");
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
        GatewayIntentBits.DirectMessages, // Ajouté pour plus de stabilité
      ],
      partials: [Partials.Channel], // Nécessaire pour certains types de messages
      makeCache: () => new Collection(), // Désactivation du cache lourd
    });

    this.discord.once("ready", () => {
      npmlog.info("Discord", `!!! SUCCÈS TOTAL !!! Connecté : ${this.discord.user?.tag}`);
    });

    // Capture des erreurs réseau spécifiques à Discord
    this.discord.on("error", (err) => npmlog.error("Discord", "ERREUR SOCKET:", err.message));
    this.discord.on("debug", (msg) => {
        // Log uniquement les étapes de connexion pour ne pas polluer
        if(msg.toLowerCase().includes("identif") || msg.toLowerCase().includes("session")) {
            npmlog.info("Discord-Debug", msg);
        }
    });

    npmlog.info("Discord", "Lancement de login()...");
    const token = process.env.DISCORD_TOKEN?.trim();
    
    if(!token || token.length < 50) {
        npmlog.error("Discord", "ERREUR: Le Token est vide ou invalide !");
        return;
    }

    // Sécurité : Si après 30s rien ne se passe, on signale un timeout
    const loginTimeout = setTimeout(() => {
        npmlog.warn("Discord", "ALERTE: Pas de réponse de Discord après 30s (Problème d'Intents ou de Token)");
    }, 30000);

    this.discord.login(token)
      .then(() => {
        clearTimeout(loginTimeout);
        npmlog.info("Discord", "Promesse login() résolue avec succès.");
      })
      .catch((err) => {
        clearTimeout(loginTimeout);
        npmlog.error("Discord", "LOGIN REJETÉ PAR DISCORD :");
        npmlog.error("Discord", err.message);
      });
  }

  setupRevoltBot() {
    this.revolt = new RevoltClient({ 
        apiURL: process.env.API_URL || "https://api.revolt.chat",
        autoReconnect: true 
    });

    this.revolt.once("ready", () => {
      npmlog.info("Revolt", `SUCCÈS : Connecté en tant que ${this.revolt.user?.username}`);
    });

    this.revolt.loginBot(process.env.REVOLT_TOKEN!).catch(e => {
        npmlog.error("Revolt", "Erreur connexion Revolt :");
        npmlog.error("Revolt", e.message);
    });
  }
}
