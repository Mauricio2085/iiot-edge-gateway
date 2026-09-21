#!/usr/bin/env python3
"""Genera nodered/flows.json del banco SIM-LAB (UI mínima + presets)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "nodered" / "flows.json"


def sid(name: str) -> str:
    h = 0x811C9DC5
    for ch in name.encode():
        h ^= ch
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}{h:08x}"[:16]


TAB_SRV = sid("tab.srv")
TAB_UI = sid("tab.ui")
TAB_RD = sid("tab.rd")
UI_BASE = sid("ui.base")
UI_TAB = sid("ui.tab")
MB_CLIENT = sid("mb.client")
OPC_EP = sid("opc.ep")
OPC_SRV = sid("opc.srv")

GROUPS = {
    "sc": sid("g.sc"),
    "kn": sid("g.kn"),
    "js": sid("g.js"),
}


def tab(i, label, info=""):
    return {
        "id": i,
        "type": "tab",
        "label": label,
        "disabled": False,
        "info": info,
    }


def comment(i, z, name, info, x, y):
    return {
        "id": i,
        "type": "comment",
        "z": z,
        "name": name,
        "info": info,
        "x": x,
        "y": y,
        "wires": [],
    }


def inject(i, z, name, x, y, wires, *, once=False, once_delay=0.1, repeat="", topic=""):
    return {
        "id": i,
        "type": "inject",
        "z": z,
        "name": name,
        "props": [{"p": "payload"}, {"p": "topic", "vt": "str"}],
        "repeat": repeat,
        "crontab": "",
        "once": once,
        "onceDelay": once_delay,
        "topic": topic,
        "payload": "",
        "payloadType": "date",
        "x": x,
        "y": y,
        "wires": [wires],
    }


def debug(i, z, name, x, y, complete="payload"):
    return {
        "id": i,
        "type": "debug",
        "z": z,
        "name": name,
        "active": True,
        "tosidebar": True,
        "console": False,
        "tostatus": True,
        "complete": complete,
        "targetType": "msg" if complete != "true" else "full",
        "statusVal": "payload",
        "statusType": "auto",
        "x": x,
        "y": y,
        "wires": [],
    }


def function(i, z, name, func, x, y, wires, outputs=1):
    return {
        "id": i,
        "type": "function",
        "z": z,
        "name": name,
        "func": func.strip() + "\n",
        "outputs": outputs,
        "timeout": 0,
        "noerr": 0,
        "initialize": "",
        "finalize": "",
        "libs": [],
        "x": x,
        "y": y,
        "wires": wires,
    }


def delay(i, z, name, ms, x, y, wires):
    return {
        "id": i,
        "type": "delay",
        "z": z,
        "name": name,
        "pauseType": "delay",
        "timeout": str(ms),
        "timeoutUnits": "milliseconds",
        "rate": "1",
        "nbRateUnits": "1",
        "rateUnits": "second",
        "randomFirst": "1",
        "randomLast": "5",
        "randomUnits": "seconds",
        "drop": False,
        "allowrate": False,
        "outputs": 1,
        "x": x,
        "y": y,
        "wires": [wires],
    }


def debounce(i, z, name, x, y, wires):
    return {
        "id": i,
        "type": "delay",
        "z": z,
        "name": name,
        "pauseType": "delay",
        "timeout": "400",
        "timeoutUnits": "milliseconds",
        "rate": "1",
        "nbRateUnits": "1",
        "rateUnits": "second",
        "randomFirst": "1",
        "randomLast": "5",
        "randomUnits": "seconds",
        "drop": True,
        "allowrate": False,
        "outputs": 1,
        "x": x,
        "y": y,
        "wires": [wires],
    }


def split_node(i, z, name, x, y, wires):
    return {
        "id": i,
        "type": "split",
        "z": z,
        "name": name,
        "splt": "\\n",
        "spltType": "str",
        "arraySplt": 1,
        "arraySpltType": "len",
        "stream": False,
        "addname": "",
        "property": "payload",
        "x": x,
        "y": y,
        "wires": [wires],
    }


FN_PRESET = r"""
const presets = global.get('labPresets');
const lab = presets.apply(msg.payload);
flow.set('lab', lab);
const sync = [
    { topic: 'machine_status', payload: lab.machine_status },
    { topic: 'heartbeat', payload: lab.heartbeat },
    { topic: 'include.production', payload: !!(lab.include.total_count || lab.include.good_count || lab.include.reject_count) },
    { topic: 'production.total_count', payload: lab.production.total_count },
    { topic: 'energy.power_kw', payload: lab.energy.power_kw },
    { topic: 'dyn.0.value', payload: (lab.dyn[0] && lab.dyn[0].value) || 0 },
];
return [sync, { lab }];
"""

FN_MERGE = r"""
const codec = global.get('modbusCodec');
const lab = flow.get('lab') || codec.defaultLab();
if (msg.topic === 'include.production') {
    const on = !!msg.payload;
    lab.include.total_count = on;
    lab.include.good_count = on;
    lab.include.reject_count = on;
    if (on && !lab.production.total_count) {
        lab.production.total_count = 15420;
        lab.production.good_count = 15395;
        lab.production.reject_count = 25;
    }
} else if (msg.topic === 'dyn.0.value') {
    if (!lab.dyn[0]) lab.dyn[0] = { on: true, key: 'temp_camara_combustion_c', value: 0 };
    lab.dyn[0].value = msg.payload;
    lab.dyn[0].on = true;
    if (!lab.dyn[0].key) lab.dyn[0].key = 'temp_camara_combustion_c';
} else if (msg.topic === 'energy.power_kw') {
    lab.energy.power_kw = msg.payload;
    lab.include.power_kw = true;
} else if (msg.topic) {
    codec.setPath(lab, msg.topic, msg.payload);
}
flow.set('lab', lab);
msg.lab = lab;
return msg;
"""

FN_ENCODE_MB = r"""
const codec = global.get('modbusCodec');
const lab = (msg.lab) || flow.get('lab') || codec.defaultLab();
const values = codec.encodeHolding(lab);
msg.payload = {
    value: values,
    fc: 16,
    unitid: 1,
    address: 0,
    quantity: values.length,
};
msg.lab = lab;
return msg;
"""

FN_POLL_MB = r"""
const codec = global.get('modbusCodec');
msg.payload = { fc: 3, unitid: 1, address: 0, quantity: codec.HR_COUNT };
return msg;
"""

FN_NORM_MB = r"""
const codec = global.get('modbusCodec');
const normalize = global.get('normalizeAskill');
const lab = flow.get('lab') || codec.defaultLab();
const regs = Array.isArray(msg.payload) ? msg.payload : (msg.payload && msg.payload.data) || [];
const decoded = codec.decodeHolding(regs);
const snapshot = normalize.mergeSnapshot(decoded, lab);
try {
    msg.payload = normalize.buildIngestPayload({
        snapshot,
        assetId: env.get('ASKILL_ASSET_UUID'),
        tenantId: env.get('ASKILL_TENANT_ID'),
        now: new Date(),
    });
    msg.headers = {
        Authorization: 'Bearer ' + (env.get('ASKILL_GATEWAY_TOKEN') || ''),
        'Content-Type': 'application/json',
    };
    msg.url = env.get('ASKILL_INGEST_URL') || '';
    msg.method = 'POST';
    msg.source = 'modbus-tcp';
    return [msg, null];
} catch (err) {
    msg.payload = { error: err.message, field: err.field || 'body', source: 'modbus-tcp' };
    return [null, msg];
}
"""

FN_OPC_READ_REQ = r"""
msg.topic = 'readmultiple';
msg.payload = [
    'ns=1;s=SIM.machine_status',
    'ns=1;s=SIM.heartbeat',
    'ns=1;s=SIM.flags',
    'ns=1;s=SIM.total_count',
    'ns=1;s=SIM.good_count',
    'ns=1;s=SIM.reject_count',
    'ns=1;s=SIM.power_kw',
    'ns=1;s=SIM.consumption_kwh',
    'ns=1;s=SIM.vibration_rms_mm_s',
    'ns=1;s=SIM.temperature_bearing_c',
    'ns=1;s=SIM.dyn0.key',
    'ns=1;s=SIM.dyn0.value',
    'ns=1;s=SIM.dyn1.key',
    'ns=1;s=SIM.dyn1.value',
];
return msg;
"""

FN_NORM_OPC = r"""
const normalize = global.get('normalizeAskill');
const codec = global.get('modbusCodec');
const lab = flow.get('lab') || codec.defaultLab();
const map = normalize.parseOpcUaRead(msg.payload);
const decoded = normalize.snapshotFromOpcUa(map);
const snapshot = normalize.mergeSnapshot(decoded, {
    ...lab,
    dyn: decoded.dyn.map((d, i) => ({
        on: d.on,
        key: d.key || ((lab.dyn[i] || {}).key) || '',
        value: d.value,
    })),
});
try {
    msg.payload = normalize.buildIngestPayload({
        snapshot,
        assetId: env.get('ASKILL_ASSET_UUID'),
        tenantId: env.get('ASKILL_TENANT_ID'),
        now: new Date(),
    });
    msg.headers = {
        Authorization: 'Bearer ' + (env.get('ASKILL_GATEWAY_TOKEN') || ''),
        'Content-Type': 'application/json',
    };
    msg.url = env.get('ASKILL_INGEST_URL') || '';
    msg.method = 'POST';
    msg.source = 'opcua-tcp';
    return [msg, null];
} catch (err) {
    msg.payload = { error: err.message, field: err.field || 'body', source: 'opcua-tcp' };
    return [null, msg];
}
"""

FN_FAN = r"""
const pretty = { ...msg, payload: JSON.stringify(msg.payload, null, 2) };
node.send([msg, pretty]);
return null;
"""

FN_HTTP_GATE = r"""
if (String(env.get('ENABLE_ASKILL_INGEST') || '').toLowerCase() === 'true') {
    return [msg, null];
}
msg.payload = { armed: false, hint: 'HTTP Request disabled + ENABLE_ASKILL_INGEST≠true' };
return [null, msg];
"""

FN_OPC_BOOT = r"""
const vars = [
    'ns=1;s=SIM.machine_status;datatype=UInt16;value=1',
    'ns=1;s=SIM.heartbeat;datatype=Boolean;value=true',
    'ns=1;s=SIM.flags;datatype=UInt16;value=0',
    'ns=1;s=SIM.total_count;datatype=UInt32;value=0',
    'ns=1;s=SIM.good_count;datatype=UInt32;value=0',
    'ns=1;s=SIM.reject_count;datatype=UInt32;value=0',
    'ns=1;s=SIM.power_kw;datatype=Float;value=0',
    'ns=1;s=SIM.consumption_kwh;datatype=Float;value=0',
    'ns=1;s=SIM.vibration_rms_mm_s;datatype=Float;value=0',
    'ns=1;s=SIM.temperature_bearing_c;datatype=Float;value=0',
    'ns=1;s=SIM.dyn0.key;datatype=String;value=',
    'ns=1;s=SIM.dyn0.value;datatype=Float;value=0',
    'ns=1;s=SIM.dyn1.key;datatype=String;value=',
    'ns=1;s=SIM.dyn1.value;datatype=Float;value=0',
];
msg.payload = vars.map((topic) => ({
    topic,
    payload: { opcuaCommand: 'addVariable' },
}));
return msg;
"""

FN_OPC_BOOT_MAP = r"""
msg.topic = msg.payload.topic;
msg.payload = msg.payload.payload;
return msg;
"""


def ui_group(i, name, order, width="6"):
    return {
        "id": i,
        "type": "ui_group",
        "name": name,
        "tab": UI_TAB,
        "order": order,
        "disp": True,
        "width": width,
        "collapse": False,
        "className": "",
    }


def ui_dropdown(i, z, name, label, group, topic, options, x, y, wires, order=1):
    return {
        "id": i,
        "type": "ui_dropdown",
        "z": z,
        "name": name,
        "label": label,
        "tooltip": "",
        "place": "Seleccionar",
        "group": group,
        "order": order,
        "width": 0,
        "height": 0,
        "passthru": False,
        "multiple": False,
        "options": options,
        "payload": "",
        "topic": topic,
        "topicType": "str",
        "className": "",
        "x": x,
        "y": y,
        "wires": [wires],
    }


def ui_switch(i, z, name, label, group, topic, x, y, wires, order=1):
    return {
        "id": i,
        "type": "ui_switch",
        "z": z,
        "name": name,
        "label": label,
        "tooltip": "",
        "group": group,
        "order": order,
        "width": 0,
        "height": 0,
        "passthru": False,
        "decouple": "false",
        "topic": topic,
        "topicType": "str",
        "style": "",
        "onvalue": True,
        "onvalueType": "bool",
        "onicon": "",
        "oncolor": "",
        "offvalue": False,
        "offvalueType": "bool",
        "officon": "",
        "offcolor": "",
        "animate": True,
        "className": "",
        "x": x,
        "y": y,
        "wires": [wires],
    }


def ui_numeric(i, z, name, label, group, topic, x, y, wires, *, mn=0, mx=1e9, step=1, order=1):
    return {
        "id": i,
        "type": "ui_numeric",
        "z": z,
        "name": name,
        "label": label,
        "tooltip": "",
        "group": group,
        "order": order,
        "width": 0,
        "height": 0,
        "passthru": False,
        "topic": topic,
        "topicType": "str",
        "format": "{{value}}",
        "min": mn,
        "max": mx,
        "step": step,
        "wrap": False,
        "className": "",
        "x": x,
        "y": y,
        "wires": [wires],
    }


def ui_button(i, z, name, label, group, topic, payload, x, y, wires, order=1):
    return {
        "id": i,
        "type": "ui_button",
        "z": z,
        "name": name,
        "group": group,
        "order": order,
        "width": 0,
        "height": 0,
        "passthru": False,
        "label": label,
        "tooltip": "",
        "color": "",
        "bgcolor": "",
        "className": "",
        "icon": "",
        "payload": payload,
        "payloadType": "str",
        "topic": topic,
        "topicType": "str",
        "x": x,
        "y": y,
        "wires": [wires],
    }


def ui_template(i, z, name, group, x, y, order=1):
    return {
        "id": i,
        "type": "ui_template",
        "z": z,
        "group": group,
        "name": name,
        "order": order,
        "width": "6",
        "height": "6",
        "format": "<pre style=\"margin:0;font-size:12px;white-space:pre-wrap;\">{{msg.payload}}</pre>",
        "storeOutMessages": True,
        "fwdInMessages": True,
        "resendOnRefresh": True,
        "templateScope": "local",
        "className": "",
        "x": x,
        "y": y,
        "wires": [[]],
    }


def ui_base():
    return {
        "id": UI_BASE,
        "type": "ui_base",
        "theme": {
            "name": "theme-dark",
            "lightTheme": {
                "default": "#0094CE",
                "baseColor": "#097479",
                "baseFont": "Helvetica Neue,Arial,sans-serif",
                "edited": True,
                "reset": False,
            },
            "darkTheme": {
                "default": "#097479",
                "baseColor": "#0f766e",
                "baseFont": "Helvetica Neue,Arial,sans-serif",
                "edited": True,
                "reset": False,
            },
            "customTheme": {
                "name": "Untitled Theme",
                "default": "#4B7930",
                "baseColor": "#4B7930",
                "baseFont": "Helvetica Neue,Arial,sans-serif",
            },
            "themeState": {
                "base-color": {"default": "#0f766e", "value": "#0f766e", "edited": True},
                "base-font": {"value": "Helvetica Neue,Arial,sans-serif"},
                "page-titlebar-backgroundColor": {"value": "#0f766e", "edited": False},
                "page-backgroundColor": {"value": "#111111", "edited": False},
                "page-sidebar-backgroundColor": {"value": "#333333", "edited": False},
                "group-textColor": {"value": "#2dd4bf", "edited": False},
                "group-borderColor": {"value": "#555555", "edited": False},
                "group-backgroundColor": {"value": "#333333", "edited": False},
                "widget-textColor": {"value": "#eeeeee", "edited": False},
                "widget-backgroundColor": {"value": "#0f766e", "edited": False},
                "widget-borderColor": {"value": "#333333", "edited": False},
            },
            "angularTheme": {
                "primary": "teal",
                "accents": "cyan",
                "warn": "red",
                "background": "grey",
            },
        },
        "site": {
            "name": "Askill SIM-LAB",
            "hideToolbar": "false",
            "allowSwipe": "false",
            "lockMenu": "false",
            "allowTempTheme": "true",
            "dateFormat": "DD/MM/YYYY",
            "sizes": {
                "sx": 48,
                "sy": 48,
                "gx": 6,
                "gy": 6,
                "cx": 6,
                "cy": 6,
                "px": 0,
                "py": 0,
            },
        },
    }


def mb_server():
    return {
        "id": sid("mb.server"),
        "type": "modbus-server",
        "z": TAB_SRV,
        "name": "SIM-LAB Modbus slave",
        "logEnabled": False,
        "hostname": "0.0.0.0",
        "port": "5020",
        "serverPort": 5020,
        "responseDelay": 50,
        "delayUnit": "ms",
        "coilsBufferSize": 2000,
        "holdingBufferSize": 2000,
        "inputBufferSize": 2000,
        "discreteBufferSize": 2000,
        "showErrors": True,
        "x": 240,
        "y": 120,
        "wires": [[], [], [], [], []],
    }


def mb_client():
    return {
        "id": MB_CLIENT,
        "type": "modbus-client",
        "name": "127.0.0.1:5020",
        "clienttype": "tcp",
        "bufferCommands": True,
        "stateLogEnabled": False,
        "queueLogEnabled": False,
        "failureLogEnabled": True,
        "tcpHost": "127.0.0.1",
        "tcpPort": "5020",
        "tcpType": "DEFAULT",
        "serialPort": "/dev/ttyUSB",
        "serialType": "RTU-BUFFERD",
        "serialBaudrate": "9600",
        "serialDatabits": "8",
        "serialStopbits": "1",
        "serialParity": "none",
        "serialConnectionDelay": "100",
        "serialAsciiResponseStartDelimiter": "0x3A",
        "unit_id": "1",
        "commandDelay": 1,
        "clientTimeout": 2000,
        "reconnectOnTimeout": True,
        "reconnectTimeout": 3000,
        "parallelUnitIdsAllowed": True,
        "showWarnings": True,
        "showLogs": False,
    }


def mb_flex_write(i, z, name, x, y, wires):
    return {
        "id": i,
        "type": "modbus-flex-write",
        "z": z,
        "name": name,
        "showStatusActivities": True,
        "showErrors": True,
        "showWarnings": True,
        "server": MB_CLIENT,
        "emptyMsgOnFail": False,
        "keepMsgProperties": True,
        "delayOnStart": True,
        "startDelayTime": "3",
        "x": x,
        "y": y,
        "wires": [wires, []],
    }


def mb_flex_getter(i, z, name, x, y, wires):
    return {
        "id": i,
        "type": "modbus-flex-getter",
        "z": z,
        "name": name,
        "showStatusActivities": True,
        "showErrors": True,
        "showWarnings": True,
        "logIOActivities": False,
        "server": MB_CLIENT,
        "useIOFile": False,
        "ioFile": "",
        "useIOForPayload": False,
        "emptyMsgOnFail": False,
        "keepMsgProperties": True,
        "delayOnStart": True,
        "startDelayTime": "3",
        "x": x,
        "y": y,
        "wires": [wires, []],
    }


def opc_server():
    return {
        "id": OPC_SRV,
        "type": "OpcUa-Server",
        "z": TAB_SRV,
        "port": "54840",
        "name": "SIM-LAB OPC UA (UaExpert)",
        "endpoint": "UA/SIMLAB",
        "endpointNone": True,
        "endpointSign": False,
        "endpointSignEncrypt": False,
        "endpointBasic128Rsa15": False,
        "endpointBasic256": False,
        "endpointBasic256Sha256": False,
        "registerServer": False,
        "constructDefaultAddressSpace": True,
        "allowAnonymous": True,
        "maxAllowedSessionNumber": 10,
        "maxConnectionsPerEndpoint": 10,
        "maxAllowedSubscriptionNumber": 50,
        "maxNodesPerBrowse": 0,
        "maxNodesPerHistoryReadData": 0,
        "maxNodesPerHistoryReadEvents": 0,
        "maxNodesPerHistoryUpdateData": 0,
        "maxNodesPerRead": 0,
        "maxNodesPerWrite": 0,
        "maxNodesPerMethodCall": 0,
        "maxNodesPerRegisterNodes": 0,
        "maxNodesPerNodeManagement": 0,
        "maxMonitoredItemsPerCall": 0,
        "maxNodesPerHistoryUpdateEvents": 0,
        "maxNodesPerTranslateBrowsePathsToNodeIds": 0,
        "x": 240,
        "y": 240,
        "wires": [[]],
    }


def opc_endpoint():
    return {
        "id": OPC_EP,
        "type": "OpcUa-Endpoint",
        "endpoint": "opc.tcp://askill-sim-lab:54840/UA/SIMLAB",
        "secpol": "None",
        "secmode": "None",
        "none": True,
        "login": False,
        "usercert": False,
        "usercertificate": "",
        "userprivatekey": "",
    }


def opc_client(i, z, name, action, x, y, wires):
    return {
        "id": i,
        "type": "OpcUa-Client",
        "z": z,
        "endpoint": OPC_EP,
        "action": action,
        "deadbandtype": "a",
        "deadbandvalue": 1,
        "time": 10,
        "timeUnit": "s",
        "certificate": "n",
        "localfile": "",
        "localkeyfile": "",
        "securitymode": "None",
        "securitypolicy": "None",
        "name": name,
        "x": x,
        "y": y,
        "wires": [wires],
    }


def http_request(i, z, name, x, y, wires):
    return {
        "id": i,
        "type": "http request",
        "z": z,
        "name": name,
        "method": "use",
        "ret": "obj",
        "paytoqs": "ignore",
        "url": "",
        "tls": "",
        "persist": False,
        "proxy": "",
        "insecureHTTPParser": False,
        "authType": "",
        "senderr": False,
        "headers": [],
        "x": x,
        "y": y,
        "wires": [wires],
        "d": True,
    }


def build():
    preset = sid("fn.preset")
    merge = sid("fn.merge")
    encode = sid("fn.enc.mb")
    debounce_id = sid("deb.write")
    write_mb = sid("mb.write")
    poll = sid("inj.poll")
    fn_mb_req = sid("fn.mb.req")
    fn_opc_req = sid("fn.opc.req")
    mb_get = sid("mb.get")
    opc_rd = sid("opc.rd")
    norm_mb = sid("fn.norm.mb")
    norm_opc = sid("fn.norm.opc")
    dbg_ok = sid("dbg.ok")
    dbg_err = sid("dbg.err")
    ui_json = sid("ui.json")
    fan = sid("fn.fan")
    sw_http = sid("sw.http")
    http = sid("http.askill")
    dbg_http = sid("dbg.http")
    dbg_off = sid("dbg.off")
    boot = sid("fn.opc.boot")
    boot_map = sid("fn.opc.bootmap")
    split_boot = sid("split.boot")

    nodes = [
        tab(
            TAB_SRV,
            "0 · Servidores OT",
            "Slave Modbus :5020 (camino feliz). Servidor OPC UA para UaExpert; la UI no escribe OPC.",
        ),
        tab(
            TAB_UI,
            "1 · Presets → Modbus",
            "Cuatro escenarios + pocos knobs. Solo FC16 TCP al slave.",
        ),
        tab(
            TAB_RD,
            "2 · Modbus → JSON",
            "Poll FC3 8 s. Inject opcional OPC UA. HTTP Request disabled.",
        ),
        ui_base(),
        {
            "id": UI_TAB,
            "type": "ui_tab",
            "name": "SIM-LAB",
            "icon": "dashboard",
            "disabled": False,
            "hidden": False,
        },
        ui_group(GROUPS["sc"], "Escenarios", 1, "6"),
        ui_group(GROUPS["kn"], "Ajuste fino", 2, "6"),
        ui_group(GROUPS["js"], "JSON ingest (debug)", 3, "6"),
        mb_client(),
        opc_endpoint(),
        mb_server(),
        opc_server(),
        comment(
            sid("c.srv"),
            TAB_SRV,
            "Modbus es el demo. OPC UA es optativo.",
            "UaExpert: opc.tcp://localhost:54840/UA/SIMLAB",
            240,
            60,
        ),
    ]

    nodes.append(
        inject(
            sid("inj.boot"),
            TAB_SRV,
            "Al arrancar: addVariable OPC",
            80,
            360,
            [sid("d.boot")],
            once=True,
            once_delay=4,
        )
    )
    nodes.append(delay(sid("d.boot"), TAB_SRV, "espera server", 2000, 240, 360, [boot]))
    nodes.append(function(boot, TAB_SRV, "lista addVariable", FN_OPC_BOOT, 430, 360, [[split_boot]]))
    nodes.append(split_node(split_boot, TAB_SRV, "1 var", 600, 360, [boot_map]))
    nodes.append(function(boot_map, TAB_SRV, "topic addVariable", FN_OPC_BOOT_MAP, 760, 360, [[OPC_SRV]]))

    widgets = []

    def add_w(node):
        widgets.append(node["id"])
        nodes.append(node)

    add_w(
        ui_button(
            sid("ui.p1"),
            TAB_UI,
            "p1",
            "1 · Running + OEE",
            GROUPS["sc"],
            "preset",
            "running_oee",
            80,
            80,
            [preset],
            1,
        )
    )
    add_w(
        ui_button(
            sid("ui.p2"),
            TAB_UI,
            "p2",
            "2 · Sin total_count",
            GROUPS["sc"],
            "preset",
            "no_total",
            80,
            120,
            [preset],
            2,
        )
    )
    add_w(
        ui_button(
            sid("ui.p3"),
            TAB_UI,
            "p3",
            "3 · Falla + vibración",
            GROUPS["sc"],
            "preset",
            "fault_vib",
            80,
            160,
            [preset],
            3,
        )
    )
    add_w(
        ui_button(
            sid("ui.p4"),
            TAB_UI,
            "p4",
            "4 · 2 dynamic_variables",
            GROUPS["sc"],
            "preset",
            "two_dyn",
            80,
            200,
            [preset],
            4,
        )
    )

    add_w(
        ui_dropdown(
            sid("ui.st"),
            TAB_UI,
            "status",
            "machine_status",
            GROUPS["kn"],
            "machine_status",
            [
                {"label": "0 — Apagado", "value": 0, "type": "num"},
                {"label": "1 — Running", "value": 1, "type": "num"},
                {"label": "2 — Parada programada", "value": 2, "type": "num"},
                {"label": "3 — Falla", "value": 3, "type": "num"},
            ],
            80,
            280,
            [merge],
            1,
        )
    )
    add_w(ui_switch(sid("ui.hb"), TAB_UI, "hb", "heartbeat", GROUPS["kn"], "heartbeat", 80, 320, [merge], 2))
    add_w(
        ui_switch(
            sid("ui.incp"),
            TAB_UI,
            "incp",
            "Incluir producción",
            GROUPS["kn"],
            "include.production",
            80,
            360,
            [merge],
            3,
        )
    )
    add_w(
        ui_numeric(
            sid("ui.tot"),
            TAB_UI,
            "tot",
            "total_count",
            GROUPS["kn"],
            "production.total_count",
            80,
            400,
            [merge],
            mn=0,
            mx=2147483647,
            step=1,
            order=4,
        )
    )
    add_w(
        ui_numeric(
            sid("ui.pk"),
            TAB_UI,
            "pk",
            "power_kw",
            GROUPS["kn"],
            "energy.power_kw",
            80,
            440,
            [merge],
            mn=0,
            mx=10000,
            step=0.1,
            order=5,
        )
    )
    add_w(
        ui_numeric(
            sid("ui.dyn"),
            TAB_UI,
            "dyn",
            "temp_camara_combustion_c",
            GROUPS["kn"],
            "dyn.0.value",
            80,
            480,
            [merge],
            mn=-50,
            mx=2000,
            step=0.1,
            order=6,
        )
    )
    nodes.append(
        ui_button(
            sid("ui.write"),
            TAB_UI,
            "write",
            "Escribir a Modbus ahora",
            GROUPS["kn"],
            "force_write",
            "write",
            80,
            520,
            [merge],
            7,
        )
    )

    nodes.append(function(preset, TAB_UI, "aplicar preset", FN_PRESET, 360, 140, [widgets, [encode]], outputs=2))
    nodes.append(function(merge, TAB_UI, "merge knobs", FN_MERGE, 360, 360, [[debounce_id]]))
    nodes.append(debounce(debounce_id, TAB_UI, "debounce 400ms", 560, 360, [encode]))
    nodes.append(function(encode, TAB_UI, "encode HR + FC16", FN_ENCODE_MB, 780, 240, [[write_mb]]))
    nodes.append(mb_flex_write(write_mb, TAB_UI, "Modbus TCP write", 1020, 240, [sid("dbg.wr.mb")]))
    nodes.append(debug(sid("dbg.wr.mb"), TAB_UI, "write Modbus OK", 1240, 240))

    nodes.append(
        inject(
            sid("inj.seed"),
            TAB_UI,
            "Semilla: Running + OEE",
            80,
            40,
            [preset],
            once=True,
            once_delay=4,
            topic="preset",
        )
    )
    # seed inject sends date payload — override with change? Use inject payload running_oee
    for n in nodes:
        if n["id"] == sid("inj.seed"):
            n["payload"] = "running_oee"
            n["payloadType"] = "str"
            n["topic"] = "preset"

    nodes.append(
        comment(
            sid("c.rd"),
            TAB_RD,
            "Poll Modbus 8 s · HTTP off",
            "Inject «OPC UA read una vez» no entra en el poll.",
            160,
            40,
        )
    )
    nodes.append(
        {
            "id": poll,
            "type": "inject",
            "z": TAB_RD,
            "name": "poll Modbus 8s",
            "props": [{"p": "payload"}, {"p": "topic", "vt": "str"}],
            "repeat": "8",
            "crontab": "",
            "once": True,
            "onceDelay": "8",
            "topic": "poll",
            "payload": "",
            "payloadType": "date",
            "x": 120,
            "y": 140,
            "wires": [[fn_mb_req]],
        }
    )
    nodes.append(function(fn_mb_req, TAB_RD, "FC3 request", FN_POLL_MB, 320, 140, [[mb_get]]))
    nodes.append(mb_flex_getter(mb_get, TAB_RD, "Modbus TCP read", 540, 140, [norm_mb]))
    nodes.append(
        function(
            norm_mb,
            TAB_RD,
            "normalizar Askill (Modbus)",
            FN_NORM_MB,
            780,
            140,
            [[fan], [dbg_err]],
            outputs=2,
        )
    )
    nodes.append(
        inject(
            sid("inj.opc"),
            TAB_RD,
            "OPC UA read una vez",
            120,
            280,
            [fn_opc_req],
        )
    )
    nodes.append(function(fn_opc_req, TAB_RD, "OPC UA readmultiple", FN_OPC_READ_REQ, 320, 280, [[opc_rd]]))
    nodes.append(opc_client(opc_rd, TAB_RD, "OPC UA TCP read", "read", 540, 280, [norm_opc]))
    nodes.append(
        function(
            norm_opc,
            TAB_RD,
            "normalizar Askill (OPC UA)",
            FN_NORM_OPC,
            780,
            280,
            [[fan], [dbg_err]],
            outputs=2,
        )
    )
    nodes.append(function(fan, TAB_RD, "fan-out objeto", FN_FAN, 1020, 180, [[sw_http, dbg_ok], [ui_json]], outputs=2))
    nodes.append(debug(dbg_ok, TAB_RD, "JSON ingest", 1260, 80, "payload"))
    nodes.append(debug(dbg_err, TAB_RD, "error normalizar", 1020, 360, "payload"))
    nodes.append(ui_template(ui_json, TAB_RD, "payload UI", GROUPS["js"], 1260, 200, 1))
    nodes.append(
        function(
            sw_http,
            TAB_RD,
            "¿ENABLE_ASKILL_INGEST?",
            FN_HTTP_GATE,
            1260,
            140,
            [[http], [dbg_off]],
            outputs=2,
        )
    )
    nodes.append(http_request(http, TAB_RD, "POST /api/iiot/ingest (OFF)", 1500, 120, [dbg_http]))
    nodes.append(debug(dbg_http, TAB_RD, "respuesta Askill", 1720, 120, "payload"))
    nodes.append(debug(dbg_off, TAB_RD, "ingest desarmado", 1500, 200, "payload"))

    return nodes


def main():
    nodes = build()
    ids = {n["id"] for n in nodes}
    for n in nodes:
        if "wires" not in n:
            continue
        cleaned = []
        for out in n["wires"]:
            if not isinstance(out, list):
                cleaned.append(out)
                continue
            cleaned.append([w for w in out if w in ids])
        n["wires"] = cleaned
    OUT.write_text(json.dumps(nodes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(nodes)} nodes)")


if __name__ == "__main__":
    main()
