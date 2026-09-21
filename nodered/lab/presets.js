/**
 * Escenarios de demo. La UI no expone el diccionario completo.
 */
function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function baseOff() {
  return {
    read_source: "modbus",
    machine_status: 1,
    heartbeat: true,
    include: {
      total_count: false,
      good_count: false,
      reject_count: false,
      power_kw: false,
      consumption_kwh: false,
      vibration_rms_mm_s: false,
      temperature_bearing_c: false,
    },
    production: { total_count: 0, good_count: 0, reject_count: 0 },
    energy: { power_kw: 0, consumption_kwh: 0 },
    health: { vibration_rms_mm_s: 0, temperature_bearing_c: 0 },
    context: { order_id: "", sku: "" },
    dyn: [
      { on: false, key: "", value: 0 },
      { on: false, key: "", value: 0 },
      { on: false, key: "", value: 0 },
      { on: false, key: "", value: 0 },
    ],
  };
}

const PRESETS = {
  running_oee: () => {
    const lab = baseOff();
    lab.machine_status = 1;
    lab.heartbeat = true;
    lab.include.total_count = true;
    lab.include.good_count = true;
    lab.include.reject_count = true;
    lab.include.power_kw = true;
    lab.production = { total_count: 15420, good_count: 15395, reject_count: 25 };
    lab.energy.power_kw = 45.2;
    return lab;
  },
  no_total: () => {
    const lab = baseOff();
    lab.machine_status = 1;
    lab.heartbeat = true;
    lab.include.power_kw = true;
    lab.energy.power_kw = 12.5;
    return lab;
  },
  fault_vib: () => {
    const lab = baseOff();
    lab.machine_status = 3;
    lab.heartbeat = true;
    lab.include.vibration_rms_mm_s = true;
    lab.include.temperature_bearing_c = true;
    lab.include.power_kw = true;
    lab.health.vibration_rms_mm_s = 8.4;
    lab.health.temperature_bearing_c = 91.2;
    lab.energy.power_kw = 0.2;
    return lab;
  },
  two_dyn: () => {
    const lab = baseOff();
    lab.machine_status = 1;
    lab.heartbeat = true;
    lab.include.power_kw = true;
    lab.energy.power_kw = 38.0;
    lab.dyn[0] = { on: true, key: "temp_camara_combustion_c", value: 450.2 };
    lab.dyn[1] = { on: true, key: "presion_linea_bar", value: 6.1 };
    return lab;
  },
};

function apply(name) {
  const key = String(name || "running_oee");
  const factory = PRESETS[key] || PRESETS.running_oee;
  return clone(factory());
}

function knobSnapshot(lab) {
  return {
    machine_status: lab.machine_status,
    heartbeat: lab.heartbeat,
    includeProduction: Boolean(
      lab.include.total_count || lab.include.good_count || lab.include.reject_count,
    ),
    total_count: lab.production.total_count,
    power_kw: lab.energy.power_kw,
    dyn0: lab.dyn[0] && lab.dyn[0].on ? lab.dyn[0].value : (lab.dyn[0] && lab.dyn[0].value) || 0,
  };
}

module.exports = { PRESETS, apply, knobSnapshot, baseOff };
