/**
 * Normaliza una muestra OT (Modbus o OPC UA) al JSON de POST /api/iiot/ingest.
 * timestamp ISO-8601 UTC lo pone este agente. No inventa total_count: 0.
 */

function omitEmpty(obj) {
  if (!obj || typeof obj !== "object") return undefined;
  const out = {};
  for (const [key, value] of Object.entries(obj)) {
    if (value === undefined || value === null || value === "") continue;
    out[key] = value;
  }
  return Object.keys(out).length ? out : undefined;
}

function asInt(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return undefined;
  return Math.max(0, Math.trunc(n));
}

function asFinite(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return undefined;
  return Math.round(n * 1e4) / 1e4;
}

function mergeSnapshot(decoded, lab) {
  const keys = ((lab && lab.dyn) || []).map((slot) =>
    String((slot && slot.key) || "").trim(),
  );
  const context = (lab && lab.context) || {};
  return {
    ...decoded,
    dynKeys: keys,
    context,
  };
}

/**
 * @param {object} input
 * @param {object} input.snapshot  decodeHolding() + dynKeys + context
 * @param {string} input.assetId
 * @param {string|number|undefined} input.tenantId
 * @param {Date} [input.now]
 */
function buildIngestPayload(input) {
  const snapshot = input.snapshot || {};
  const assetId = String(input.assetId || "").trim();
  const tenantRaw = input.tenantId;
  const tenantId =
    tenantRaw === undefined || tenantRaw === null || tenantRaw === ""
      ? undefined
      : typeof tenantRaw === "number"
        ? tenantRaw
        : String(tenantRaw).trim() || undefined;
  const now = input.now instanceof Date ? input.now : new Date();
  const timestamp = now.toISOString();

  if (!assetId) {
    const err = new Error("ASKILL_ASSET_UUID vacío: no se arma asset_id");
    err.field = "asset_id";
    throw err;
  }

  const flags = snapshot.flags || {};
  const production = {};
  if (flags.total_count) {
    const n = asInt(snapshot.production && snapshot.production.total_count);
    if (n !== undefined) production.total_count = n;
  }
  if (flags.good_count) {
    const n = asInt(snapshot.production && snapshot.production.good_count);
    if (n !== undefined) production.good_count = n;
  }
  if (flags.reject_count) {
    const n = asInt(snapshot.production && snapshot.production.reject_count);
    if (n !== undefined) production.reject_count = n;
  }

  const energy = {};
  if (flags.power_kw) {
    const n = asFinite(snapshot.energy && snapshot.energy.power_kw);
    if (n !== undefined) energy.power_kw = n;
  }
  if (flags.consumption_kwh) {
    const n = asFinite(snapshot.energy && snapshot.energy.consumption_kwh);
    if (n !== undefined) energy.consumption_kwh = n;
  }

  const dynamic_variables = {};
  const dyn = snapshot.dyn || [];
  const dynKeys = snapshot.dynKeys || [];
  for (let i = 0; i < 4; i += 1) {
    const slot = dyn[i] || {};
    const key = dynKeys[i] || "";
    if (!slot.on || !key) continue;
    const n = asFinite(slot.value);
    if (n === undefined) continue;
    dynamic_variables[key] = n;
  }

  const health = {};
  if (flags.vibration_rms_mm_s) {
    const n = asFinite(snapshot.health && snapshot.health.vibration_rms_mm_s);
    if (n !== undefined) health.vibration_rms_mm_s = n;
  }
  if (flags.temperature_bearing_c) {
    const n = asFinite(snapshot.health && snapshot.health.temperature_bearing_c);
    if (n !== undefined) health.temperature_bearing_c = n;
  }
  const dynObj = omitEmpty(dynamic_variables);
  if (dynObj) health.dynamic_variables = dynObj;

  const telemetry = {
    heartbeat: Boolean(snapshot.heartbeat),
  };
  if (
    snapshot.machine_status !== undefined &&
    snapshot.machine_status !== null &&
    snapshot.machine_status !== ""
  ) {
    telemetry.machine_status = Math.min(
      3,
      Math.max(0, Math.trunc(Number(snapshot.machine_status))),
    );
  }

  const ctx = omitEmpty({
    order_id: snapshot.context && snapshot.context.order_id,
    sku: snapshot.context && snapshot.context.sku,
  });
  if (ctx) telemetry.context = ctx;

  const prodObj = omitEmpty(production);
  if (prodObj) telemetry.production = prodObj;
  const energyObj = omitEmpty(energy);
  if (energyObj) telemetry.energy = energyObj;
  const healthObj = omitEmpty(health);
  if (healthObj) telemetry.health = healthObj;

  if (
    telemetry.machine_status === undefined &&
    !(energyObj && energyObj.power_kw !== undefined)
  ) {
    const err = new Error(
      "Contrato Askill: hace falta machine_status o power_kw",
    );
    err.field = "telemetry";
    throw err;
  }

  const body = {
    asset_id: assetId,
    timestamp,
    telemetry,
  };
  if (tenantId !== undefined) body.tenant_id = tenantId;
  return body;
}

function parseOpcUaRead(payload) {
  const map = {};
  const rows = Array.isArray(payload)
    ? payload
    : payload && Array.isArray(payload.value)
      ? payload.value
      : null;
  if (rows) {
    for (const row of rows) {
      if (row == null) continue;
      if (typeof row === "object") {
        const id = String(row.nodeId || row.browseName || row.name || "");
        const short = id.replace(/^ns=\d+;s=/, "");
        const value =
          row.value !== undefined
            ? row.value
            : row.payload !== undefined
              ? row.payload
              : row;
        map[short] = value && typeof value === "object" && "value" in value
          ? value.value
          : value;
      }
    }
    return map;
  }
  if (payload && typeof payload === "object") {
    for (const [key, value] of Object.entries(payload)) {
      map[String(key).replace(/^ns=\d+;s=/, "")] = value;
    }
  }
  return map;
}

function snapshotFromOpcUa(map) {
  const num = (key) => {
    const v = map[key];
    if (v && typeof v === "object" && "value" in v) return v.value;
    return v;
  };
  const flags = Number(num("SIM.flags") || 0);
  const FLAG = require("./modbus-codec").FLAG;
  return {
    machine_status: Number(num("SIM.machine_status") || 0),
    heartbeat: Boolean(num("SIM.heartbeat")),
    flags: {
      total_count: Boolean(flags & FLAG.total_count),
      good_count: Boolean(flags & FLAG.good_count),
      reject_count: Boolean(flags & FLAG.reject_count),
      power_kw: Boolean(flags & FLAG.power_kw),
      consumption_kwh: Boolean(flags & FLAG.consumption_kwh),
      vibration_rms_mm_s: Boolean(flags & FLAG.vibration_rms_mm_s),
      temperature_bearing_c: Boolean(flags & FLAG.temperature_bearing_c),
    },
    production: {
      total_count: Number(num("SIM.total_count") || 0),
      good_count: Number(num("SIM.good_count") || 0),
      reject_count: Number(num("SIM.reject_count") || 0),
    },
    energy: {
      power_kw: Number(num("SIM.power_kw") || 0),
      consumption_kwh: Number(num("SIM.consumption_kwh") || 0),
    },
    health: {
      vibration_rms_mm_s: Number(num("SIM.vibration_rms_mm_s") || 0),
      temperature_bearing_c: Number(num("SIM.temperature_bearing_c") || 0),
    },
    dyn: [0, 1, 2, 3].map((i) => ({
      on: Boolean(flags & FLAG[`dyn${i}`]),
      value: Number(num(`SIM.dyn${i}.value`) || 0),
      key: String(num(`SIM.dyn${i}.key`) || ""),
    })),
    context: {
      order_id: String(num("SIM.order_id") || ""),
      sku: String(num("SIM.sku") || ""),
    },
  };
}

module.exports = {
  omitEmpty,
  mergeSnapshot,
  buildIngestPayload,
  parseOpcUaRead,
  snapshotFromOpcUa,
};
