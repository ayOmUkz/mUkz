FROM node:20-alpine AS build
WORKDIR /srv
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine
WORKDIR /srv
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1
COPY --from=build /srv ./
EXPOSE 3000
USER node
CMD ["npx", "next", "start", "-H", "0.0.0.0"]
