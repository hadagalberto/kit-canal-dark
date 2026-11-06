# Uma imagem para tudo: agendador, worker e painel usam a mesma, com comandos
# diferentes no docker-compose.yml. Node + Chrome (render Remotion), ffmpeg
# (áudio e conferência do MP4) e Python (o pipeline).
FROM node:22-bookworm-slim

# Bibliotecas do Chrome Headless Shell (docs do Remotion) + ffmpeg + Python.
RUN apt-get update && apt-get install -y --no-install-recommends \
      libnss3 libdbus-1-3 libatk1.0-0 libgbm-dev libasound2 libxrandr2 \
      libxkbcommon-dev libxfixes3 libxcomposite1 libxdamage1 libatk-bridge2.0-0 \
      libpango-1.0-0 libcairo2 libcups2 ffmpeg ca-certificates fonts-dejavu-core \
      python3 python3-venv tini \
    && rm -rf /var/lib/apt/lists/*

# Python num venv próprio (o Debian não deixa pip no sistema).
COPY requirements.txt /tmp/requirements.txt
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt
# Redes opcionais: instagrapi é pesada, só entra se pedir no build
# (INSTALAR_INSTAGRAM=1 no .env, depois docker compose build).
ARG INSTALAR_INSTAGRAM=0
RUN if [ "$INSTALAR_INSTAGRAM" = "1" ]; then /opt/venv/bin/pip install --no-cache-dir "instagrapi==3.0.21"; fi
ENV PATH="/opt/venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Projeto Remotion. node_modules fica dentro da imagem, nunca num volume do
# Windows (lento demais).
WORKDIR /app/video
COPY video/package.json video/package-lock.json ./
RUN npm ci --no-audit --no-fund
# Baixa o Chrome no build, não no primeiro render.
RUN npx remotion browser ensure
COPY video/ ./

# As pastas de dados do vídeo apontam para o volume /dados, como no
# deploy/render.sh original: notícias, voz/trilha e MP4 vivem fora da imagem.
RUN rm -rf news public/filmes out \
    && mkdir -p out /dados \
    && ln -s /dados/news news \
    && ln -s /dados/filmes public/filmes \
    && ln -s /dados/out out/filmes

WORKDIR /app
COPY pipeline ./pipeline
COPY publicadores ./publicadores
COPY agendador ./agendador
COPY painel ./painel
COPY canais ./canais
COPY exemplos ./exemplos
COPY testes ./testes

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["python", "-m", "agendador.agendador"]
