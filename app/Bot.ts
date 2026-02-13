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
    npmlog.info("Bot", "Démarrage des services Discord et Revolt...");
    this.setupDiscordBot();
    this.setupRevoltBot();
  }

  setupDiscordBot() {
    this.discord = new DiscordClient({
      intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.MessageContent, // Assurez-vous que c'est activé sur le portail Discord !
        GatewayIntentBits.GuildMessages,
      ],
      allowedMentions: { parse: [] },
    });

    this.discord.once("ready", () => {
      npmlog.info(
        "Discord",
        `Connecté en tant que ${this.discord.user?.tag}`
      );

      this.rest = new REST().setToken(process.env.DISCORD_TOKEN!);
      
      // On initialise l'executor dès que Discord est prêt
      this.executor = new UniversalExecutor(this.discord, this.revolt);

      this.commands = new Collection();
      slashCommands.map((command) => {
        this.commands.set(command.data.name, command);
      });

      this.commandsJson = this.commands.map((command) => command.data.toJSON());

      if (!this.usingJsonMappings) {
        this.discord.guilds.cache.forEach((guild) => {
          registerSlashCommands(this.rest, this.discord, guild.id, this.commandsJson);
        });
      }

      // Initialisation des webhooks pour les mappings existants
      if (Main.mappings && Main.mappings.length > 0) {
        Main.mappings.forEach(async (mapping) => {
          const channel = this.discord.channels.cache.get(mapping.discord);
          try {
            if (channel) await initiateDiscordChannel(channel, mapping);
          } catch (e) {
            npmlog.error("Discord", "Erreur initialisation webhook pour le salon: " + mapping.discord);
          }
        });
      }
    });

    this.discord.on("interactionCreate", async (interaction) => {
      if (!interaction.isCommand() || this.usingJsonMappings) return;
      const command = this.commands.get(interaction.commandName);
      if (!command) return;

      try {
        await command.execute(interaction, this.executor);
      } catch (e) {
        npmlog.error("Discord", "Erreur Slash Command:", e);
      }
    });

    this.discord.on("messageCreate", (message) => {
      handleDiscordMessage(this.revolt, this.discord, message);
    });

    this.discord.on("messageUpdate", (oldMessage, newMessage) => {
      if (oldMessage.author?.id === this.discord.user?.id) return;
      const partialMessage: PartialDiscordMessage = {
        author: oldMessage.author,
        attachments: oldMessage.attachments,
        channelId: oldMessage.channelId,
        content: newMessage.content as string,
        embeds: newMessage.embeds,
        id: newMessage.id,
        mentions: newMessage.mentions,
      };
      handleDiscordMessageUpdate(this.revolt, partialMessage);
    });

    this.discord.on("messageDelete", (message) => {
      handleDiscordMessageDelete(this.revolt, message.id);
    });

    // Tentative de connexion avec log d'erreur
    this.discord.login(process.env.DISCORD_TOKEN).catch((err) => {
      npmlog.error("Discord", "IMPOSSIBLE DE SE CONNECTER À DISCORD. Vérifiez le TOKEN et les INTENTS.");
      npmlog.error("Discord", err);
    });
  }

  setupRevoltBot() {
    this.revolt = new RevoltClient({ apiURL: process.env.API_URL, autoReconnect: true });

    this.revolt.once("ready", () => {
      npmlog.info("Revolt", `Connecté en tant que ${this.revolt.user?.username}`);

      this.revoltCommands = new Collection();
      revoltCommands.map((command) => {
        this.revoltCommands.set(command.data.name, command);
      });
    });

    this.revolt.on("message", async (message) => {
      if (typeof message.content !== "string") return;

      const target = Main.mappings?.find(
        (mapping) => mapping.revolt === message.channel_id
      );

      if (message.content.toString().startsWith("rc!")) {
        const args = message.content.toString().split(" ");
        const commandName = args[0].slice("rc!".length);
        args.shift();
        const arg = args.join(" ");

        if (this.usingJsonMappings || !this.revoltCommands) return;

        const command = this.revoltCommands.get(commandName);
        if (!command) return;

        // SECURITÉ : On vérifie si l'executor est prêt avant de lancer la commande
        if (!this.executor) {
            return message.reply("Le pont n'est pas encore prêt. Discord est peut-être en train de se connecter...");
        }

        try {
          await command.execute(message, arg, this.executor);
        } catch (e) {
          npmlog.error("Revolt", "Erreur commande Revolt:", e);
        }
      } else if (
        target &&
        message.author_id !== this.revolt.user?._id &&
        (!message.author?.bot || target.allowBots)
      ) {
        handleRevoltMessage(this.discord, this.revolt, message, target);
      }
    });

    this.revolt.loginBot(process.env.REVOLT_TOKEN!).catch((err) => {
        npmlog.error("Revolt", "ERREUR CONNEXION REVOLT:", err);
    });
  }
}
