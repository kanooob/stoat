import { Client as DiscordClient, Collection, GatewayIntentBits } from "discord.js";
import { Client as RevoltClient } from "revolt.js";
import { REST } from "@discordjs/rest";
import npmlog from "npmlog";

import { Main } from "./Main";
import {
  handleDiscordMessage,
  handleDiscordMessageDelete,
  handleDiscordMessageUpdate,
  initiateDiscordChannel,
} from "./discord";
import {
  handleRevoltMessage,
  handleRevoltMessageDelete,
  handleRevoltMessageUpdate,
} from "./revolt";
import { registerSlashCommands } from "./discord/slash";
import { DiscordCommand, PartialDiscordMessage, RevoltCommand } from "./interfaces";
import { slashCommands } from "./discord/commands";
import UniversalExecutor from "./universalExecutor";
import { revoltCommands } from "./revolt/commands";

export class Bot {
  private discord: DiscordClient;
  private revolt: RevoltClient;
  private commands: Collection<string, DiscordCommand>;
  private rest: REST;
  private commandsJson: any;
  private revoltCommands: Collection<string, RevoltCommand>;
  private executor: UniversalExecutor;

  constructor(private usingJsonMappings: boolean) {}

  public async start() {
    npmlog.info("Bot", "Lancement de la séquence de démarrage...");
    // On lance les deux en parallèle pour éviter qu'un blocage de l'un n'empêche l'autre
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
      ],
      allowedMentions: { parse: [] },
    });

    // On définit l'événement ready AVANT de tenter le login
    this.discord.once("ready", async () => {
      npmlog.info("Discord", `SUCCÈS : Connecté en tant que ${this.discord.user?.tag}`);

      try {
        this.executor = new UniversalExecutor(this.discord, this.revolt);
        this.rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN!);

        this.commands = new Collection();
        slashCommands.forEach((command) => {
          this.commands.set(command.data.name, command);
        });

        this.commandsJson = this.commands.map((command) => command.data.toJSON());

        if (!this.usingJsonMappings) {
          this.discord.guilds.cache.forEach((guild) => {
            registerSlashCommands(this.rest, this.discord, guild.id, this.commandsJson);
          });
        }

        if (Main.mappings) {
          npmlog.info("Discord", `Initialisation de ${Main.mappings.length} salons...`);
          for (const mapping of Main.mappings) {
            try {
              const channel = await this.discord.channels.fetch(mapping.discord);
              if (channel) await initiateDiscordChannel(channel as any, mapping);
            } catch (err) {
              npmlog.error("Discord", `Erreur sur le salon ${mapping.discord}`);
            }
          }
        }
      } catch (e) {
        npmlog.error("Discord", "Erreur fatale dans le setup 'ready'", e);
      }
    });

    this.discord.on("messageCreate", (message) => {
      handleDiscordMessage(this.revolt, this.discord, message);
    });

    // Tentative de login avec debug
    npmlog.info("Discord", "Tentative de login en cours...");
    this.discord.login(process.env.DISCORD_TOKEN).catch((err) => {
      npmlog.error("Discord", "LE LOGIN A ÉCHOUÉ !");
      npmlog.error("Discord", err);
    });
  }

  setupRevoltBot() {
    this.revolt = new RevoltClient({ apiURL: process.env.API_URL, autoReconnect: true });

    this.revolt.once("ready", () => {
      npmlog.info("Revolt", `SUCCÈS : Connecté en tant que ${this.revolt.user?.username}`);
      this.revoltCommands = new Collection();
      revoltCommands.forEach((command) => {
        this.revoltCommands.set(command.data.name, command);
      });
    });

    this.revolt.on("message", async (message) => {
      if (typeof message.content !== "string") return;
      const target = Main.mappings?.find((m) => m.revolt === message.channel_id);

      if (message.content.startsWith("rc!")) {
        if (this.usingJsonMappings || !this.revoltCommands) return;
        const args = message.content.split(" ");
        const command = this.revoltCommands.get(args[0].slice(3));
        if (command && this.executor) {
          command.execute(message, args.slice(1).join(" "), this.executor).catch(e => npmlog.error("Revolt", e));
        }
      } else if (target && message.author_id !== this.revolt.user?._id) {
        handleRevoltMessage(this.discord, this.revolt, message, target);
      }
    });

    this.revolt.loginBot(process.env.REVOLT_TOKEN!).catch((err) => {
      npmlog.error("Revolt", "ERREUR CONNEXION REVOLT:", err);
    });
  }
}
