import { Main } from "./app/Main";
import * as http from "http";

// Serveur minimal pour éviter que Render ne coupe le bot (offre gratuite)
const port = process.env.PORT || 10000;
http.createServer((_req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot Revcord is running!');
}).listen(port, () => {
  console.log(`Render health check listening on port ${port}`);
});

const app = new Main();
app.start();
