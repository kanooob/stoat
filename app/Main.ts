import { Webhook } from "discord.js";
import dotenv from "dotenv";
import npmlog from "npmlog";
import { DataTypes, Sequelize } from "sequelize";

import { Bot } from "./Bot";
import { CachedMessage, Mapping } from "./interfaces";
import { MappingModel } from "./models/Mapping";
import getMappings from "./util/mappings";

export class Main {
  static mappings: Mapping[] = [];
  static webhooks: Webhook[] = [];

  /** Cache des messages pour éviter les boucles */
  static discordCache: CachedMessage[] = [];
  static revoltCache: CachedMessage[] = [];

  private bot: Bot;

  constructor() {
    dotenv.config();

    const discordToken = process.env.DISCORD_TOKEN;
    const revoltToken = process.env.REVOLT_TOKEN;

    if (!discordToken || !revoltToken) {
      npmlog.error("Main", "TOKEN MANQUANT : Vérifie tes variables d'environnement sur Render !");
      throw new Error("Tokens non fournis");
    }

    Main.webhooks = [];
    Main.discordCache = [];
    Main.revoltCache = [];
  }

  /**
   * Initialisation de Sequelize (SQLite)
   */
  async initDb(): Promise<Mapping[]> {
    try {
      const sequelize = new Sequelize({
        dialect: "sqlite",
        storage: "revcord.sqlite",
        logging: false,
      });

      await sequelize.authenticate();
      npmlog.info("db", "Connexion SQLite établie.");

      MappingModel.init(
        {
          id: { type: DataTypes.INTEGER, autoIncrement: true, primaryKey: true },
          discordChannel: { type: DataTypes.STRING },
          revoltChannel: { type: DataTypes.STRING },
          discordChannelName: { type: DataTypes.STRING },
          revoltChannelName: { type: DataTypes.STRING },
          allowBots: { type: DataTypes.BOOLEAN, defaultValue: true },
        },
        { sequelize, modelName: "mapping" }
      );

      await sequelize.sync({ alter: true });

      const mappingsInDb = await MappingModel.findAll({});
      return mappingsInDb.map((mapping) => ({
        discord: mapping.discordChannel,
        revolt: mapping.revoltChannel,
        allowBots: mapping.allowBots,
      }));
    } catch (e) {
      npmlog.error("db", "Erreur SQLite : " + e);
      return [];
    }
  }

  /**
   * Lancement du serveur et des bots
   */
  public async start(): Promise<void> {
    let usingJson = false;

    // 1. Priorité au fichier mappings.json
    try {
      const jsonMappings = await getMappings();
      if (jsonMappings && jsonMappings.length > 0) {
        Main.mappings = jsonMappings;
        usingJson = true;
        npmlog.info("Main", `Fichier JSON détecté : ${jsonMappings.length} salon(s) configuré(s).`);
      }
    } catch (e) {
      npmlog.warn("Main", "Aucun fichier mappings.json valide trouvé, passage à SQLite...");
    }

    // 2. Si pas de JSON, on utilise SQLite
    if (!usingJson) {
      Main.mappings = await this.initDb();
      if (Main.mappings.length === 0) {
        npmlog.warn("Main", "Attention : Aucun mapping trouvé (ni JSON, ni DB). Le bot sera muet.");
      }
    }

    // 3. Démarrage du bot
    this.bot = new Bot(usingJson);
    this.bot.start();
  }
}
