/**
 * Node-RED settings — banco SIM-LAB.
 * El token Askill NO entra aquí; solo env en el HTTP Request / Function.
 */
module.exports = {
  uiPort: process.env.PORT || 1880,
  flowFile: "flows.json",
  flowFilePretty: true,
  credentialSecret: process.env.NODERED_CREDENTIAL_SECRET || false,
  exportGlobalContextKeys: false,
  httpAdminRoot: "/",
  httpNodeRoot: "/",
  ui: { path: "ui" },
  functionGlobalContext: {
    modbusCodec: require("./lab/modbus-codec"),
    normalizeAskill: require("./lab/normalize-askill"),
    labPresets: require("./lab/presets"),
  },
  logging: {
    console: { level: "info", metrics: false, audit: false },
  },
  editorTheme: {
    page: { title: "Askill SIM-LAB" },
    header: { title: "Askill SIM-LAB · banco de laboratorio" },
    projects: { enabled: false },
  },
  diagnostics: { enabled: true, ui: true },
};
