# --- ÉTAPE DE BUILD ---
FROM node:20-alpine AS build

# Installation des dépendances nécessaires pour la compilation
RUN apk add --no-cache python3 g++ make
# On ajoute -sf pour forcer la création du lien même s'il existe déjà
RUN ln -sf /usr/bin/python3 /usr/bin/python

WORKDIR /build/
COPY package* ./
RUN npm install
COPY . .
RUN npm run build

# --- ÉTAPE DE PRODUCTION ---
FROM node:20-alpine AS prod
WORKDIR /app

# On ne copie que l'essentiel
COPY --from=build /build/package*.json ./
COPY --from=build /build/node_modules ./node_modules
COPY --from=build /build/build ./build

CMD ["npm", "start"]
