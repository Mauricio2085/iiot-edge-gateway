/**
 * Mapa Holding Registers (unit 1, direcciones 0-based, FC3/FC16).
 * Enteros uint32 y float32 en big-endian IEEE-754 (ABCD, dos registros).
 *
 * | Addr | Words | Campo                         |
 * | 0    | 1     | machine_status 0–3            |
 * | 1    | 1     | heartbeat 0/1                 |
 * | 2    | 1     | flags (presencia, no valor)   |
 * | 3    | 1     | reserved                      |
 * | 4–5  | 2     | total_count uint32            |
 * | 6–7  | 2     | good_count uint32             |
 * | 8–9  | 2     | reject_count uint32           |
 * | 10–11| 2     | power_kw float32              |
 * | 12–13| 2     | consumption_kwh float32       |
 * | 14–15| 2     | vibration_rms_mm_s float32    |
 * | 16–17| 2     | temperature_bearing_c float32 |
 * | 18–19| 2     | dyn0.value float32            |
 * | 20–21| 2     | dyn1.value float32            |
 * | 22–23| 2     | dyn2.value float32            |
 * | 24–25| 2     | dyn3.value float32            |
 */

const HR_COUNT = 26;

const FLAG = {
  total_count: 1 << 0,
  good_count: 1 << 1,
  reject_count: 1 << 2,
  power_kw: 1 << 3,
  consumption_kwh: 1 << 4,
  vibration_rms_mm_s: 1 << 5,
  temperature_bearing_c: 1 << 6,
  dyn0: 1 << 7,
  dyn1: 1 << 8,
  dyn2: 1 << 9,
  dyn3: 1 << 10,
};

function clampStatus(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.min(3, Math.max(0, Math.trunc(n)));
}

function floatToRegs(value) {
  const buf = Buffer.alloc(4);
  buf.writeFloatBE(Number(value) || 0, 0);
  return [buf.readUInt16BE(0), buf.readUInt16BE(2)];
}

function regsToFloat(hi, lo) {
  const buf = Buffer.alloc(4);
  buf.writeUInt16BE((hi || 0) & 0xffff, 0);
  buf.writeUInt16BE((lo || 0) & 0xffff, 2);
  return buf.readFloatBE(0);
}

function uint32ToRegs(value) {
  const n = Math.max(0, Math.floor(Number(value) || 0));
  return [(n >>> 16) & 0xffff, n & 0xffff];
}

function regsToUint32(hi, lo) {
  return (((hi || 0) & 0xffff) << 16) + ((lo || 0) & 0xffff);
}

function defaultLab() {
  return {
    read_source: "modbus",
    machine_status: 1,
    heartbeat: true,
    include: {
      total_count: true,
      good_count: true,
      reject_count: true,
      power_kw: true,
      consumption_kwh: true,
      vibration_rms_mm_s: true,
      temperature_bearing_c: true,
    },
    production: {
      total_count: 15420,
      good_count: 15395,
      reject_count: 25,
    },
    energy: {
      power_kw: 45.2,
      consumption_kwh: 12450.8,
    },
    health: {
      vibration_rms_mm_s: 2.4,
      temperature_bearing_c: 58.5,
    },
    context: { order_id: "", sku: "" },
    dyn: [
      { on: true, key: "temp_camara_combustion_c", value: 450.2 },
      { on: true, key: "presion_linea_bar", value: 6.1 },
      { on: false, key: "", value: 0 },
      { on: false, key: "", value: 0 },
    ],
  };
}

function flagsFromLab(lab) {
  const inc = lab.include || {};
  const dyn = lab.dyn || [];
  let flags = 0;
  if (inc.total_count) flags |= FLAG.total_count;
  if (inc.good_count) flags |= FLAG.good_count;
  if (inc.reject_count) flags |= FLAG.reject_count;
  if (inc.power_kw) flags |= FLAG.power_kw;
  if (inc.consumption_kwh) flags |= FLAG.consumption_kwh;
  if (inc.vibration_rms_mm_s) flags |= FLAG.vibration_rms_mm_s;
  if (inc.temperature_bearing_c) flags |= FLAG.temperature_bearing_c;
  for (let i = 0; i < 4; i += 1) {
    const slot = dyn[i] || {};
    if (slot.on && String(slot.key || "").trim()) flags |= FLAG[`dyn${i}`];
  }
  return flags;
}

function encodeHolding(lab) {
  const regs = new Array(HR_COUNT).fill(0);
  const prod = lab.production || {};
  const energy = lab.energy || {};
  const health = lab.health || {};
  const dyn = lab.dyn || [];
  regs[0] = clampStatus(lab.machine_status);
  regs[1] = lab.heartbeat ? 1 : 0;
  regs[2] = flagsFromLab(lab);
  const t = uint32ToRegs(prod.total_count);
  const g = uint32ToRegs(prod.good_count);
  const r = uint32ToRegs(prod.reject_count);
  regs[4] = t[0];
  regs[5] = t[1];
  regs[6] = g[0];
  regs[7] = g[1];
  regs[8] = r[0];
  regs[9] = r[1];
  const pk = floatToRegs(energy.power_kw);
  const ck = floatToRegs(energy.consumption_kwh);
  const vb = floatToRegs(health.vibration_rms_mm_s);
  const tb = floatToRegs(health.temperature_bearing_c);
  regs[10] = pk[0];
  regs[11] = pk[1];
  regs[12] = ck[0];
  regs[13] = ck[1];
  regs[14] = vb[0];
  regs[15] = vb[1];
  regs[16] = tb[0];
  regs[17] = tb[1];
  for (let i = 0; i < 4; i += 1) {
    const words = floatToRegs((dyn[i] || {}).value);
    regs[18 + i * 2] = words[0];
    regs[19 + i * 2] = words[1];
  }
  return regs;
}

function decodeHolding(regs) {
  const r = Array.isArray(regs) ? regs : [];
  const flags = r[2] || 0;
  const dyn = [0, 1, 2, 3].map((i) => ({
    on: Boolean(flags & FLAG[`dyn${i}`]),
    value: regsToFloat(r[18 + i * 2], r[19 + i * 2]),
  }));
  return {
    machine_status: clampStatus(r[0]),
    heartbeat: Boolean(r[1]),
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
      total_count: regsToUint32(r[4], r[5]),
      good_count: regsToUint32(r[6], r[7]),
      reject_count: regsToUint32(r[8], r[9]),
    },
    energy: {
      power_kw: regsToFloat(r[10], r[11]),
      consumption_kwh: regsToFloat(r[12], r[13]),
    },
    health: {
      vibration_rms_mm_s: regsToFloat(r[14], r[15]),
      temperature_bearing_c: regsToFloat(r[16], r[17]),
    },
    dyn,
  };
}

function setPath(obj, path, value) {
  const parts = String(path).split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i += 1) {
    const key = parts[i];
    const next = parts[i + 1];
    const asIndex = /^\d+$/.test(next);
    if (cur[key] == null) cur[key] = asIndex ? [] : {};
    cur = cur[key];
  }
  const last = parts[parts.length - 1];
  cur[/^\d+$/.test(last) ? Number(last) : last] = value;
  return obj;
}

module.exports = {
  FLAG,
  HR_COUNT,
  clampStatus,
  defaultLab,
  encodeHolding,
  decodeHolding,
  flagsFromLab,
  setPath,
  floatToRegs,
  regsToFloat,
};
