FROM nodered/node-red:4.0.9-22

USER root

# Instalar paletas junto al runtime (no copiar un node_modules ajeno sobre
# /usr/src/node-red: eso pisa minipass/tar y Node-RED no arranca).
# Tampoco van en /data: el bind-mount ./nodered:/data las ocultaría.
WORKDIR /usr/src/node-red
COPY package.json /tmp/palettes/package.json
RUN npm install --omit=dev --unsafe-perm --no-update-notifier --no-fund \
      $(node -p "Object.entries(require('/tmp/palettes/package.json').dependencies).map(([k,v])=>k+'@'+v).join(' ')") \
    && rm -rf /tmp/palettes

COPY --chown=node-red:node-red package.json /data/package.json
COPY --chown=node-red:node-red settings.js /data/settings.js
COPY --chown=node-red:node-red flows.json /data/flows.json
COPY --chown=node-red:node-red lab /data/lab

USER node-red
WORKDIR /usr/src/node-red
