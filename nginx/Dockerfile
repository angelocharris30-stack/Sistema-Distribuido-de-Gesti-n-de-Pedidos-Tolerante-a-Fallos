# Etapa 1: compila el frontend React
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# Etapa 2: NGINX sirve el frontend y balancea /api hacia api1/api2
FROM nginx:1.27-alpine
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
