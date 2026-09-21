FROM nodered/node-red:4.0.9-22

USER root
WORKDIR /data

COPY package.json /data/package.json
RUN npm install --omit=dev --unsafe-perm --no-update-notifier --no-fund \
    && chown -R node-red:node-red /data

COPY --chown=node-red:node-red settings.js /data/settings.js
COPY --chown=node-red:node-red flows.json /data/flows.json
COPY --chown=node-red:node-red lab /data/lab

USER node-red
WORKDIR /usr/src/node-red
