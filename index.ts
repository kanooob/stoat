import { Main } from "./app/Main";
import * as http from "http"; // Utilise bien cette syntaxe

const port = process.env.PORT || 10000;

http.createServer((_req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Bot Revcord is running!');
}).listen(port, () => {
  console.log(`Render health check listening on port ${port}`);
});

const app = new Main();
app.start();
