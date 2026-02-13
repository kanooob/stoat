# --- ÉTAPE DE BUILD ---
FROM node:20-alpine AS build

# Installation des dépendances nécessaires pour la compilation (sqlite3, etc.)
RUN apk add --no-cache python3 g++ make
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /build/
COPY package* ./
RUN npm install
COPY . .
RUN npm run build

# --- ÉTAPE DE PRODUCTION ---
FROM node:20-alpine AS prod
WORKDIR /app

# On ne copie que ce qui est nécessaire pour exécuter le bot
COPY --from=build /build/package*.json ./
COPY --from=build /build/node_modules ./node_modules
COPY --from=build /build/build ./build

# Si ton bot a besoin de stocker la base de données sqlite, 
# assure-toi que le dossier existe (optionnel selon ton code)
# RUN mkdir -p data

CMD ["npm", "start"]
