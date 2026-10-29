import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# ==============================================================================
# CONFIGURACIÓN GENERAL Y ESTILOS
# ==============================================================================
st.set_page_config(
    page_title="Telemetría IoT // Monitor Central",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #060913 !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stSidebar"] { display: none !important; }

.status-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.1em;
}

.badge-online {
    background: rgba(45, 212, 191, 0.12);
    border: 1px solid #2dd4bf;
    color: #2dd4bf;
}

.badge-waiting {
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid #f59e0b;
    color: #f59e0b;
}

.kpi-card {
    background: linear-gradient(145deg, #0d152d 0%, #080d1e 100%);
    border: 1px solid rgba(56, 189, 248, 0.22);
    border-top: 3px solid #38bdf8;
    border-radius: 10px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #94a3b8;
    letter-spacing: 0.14em;
    text-transform: uppercase;
}

.kpi-value {
    font-size: 2.4rem;
    font-weight: 700;
    color: #ffffff;
    margin: 6px 0;
}

div.stButton > button {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0284c7 100%) !important;
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    border: 1px solid rgba(226, 232, 240, 0.2) !important;
    border-radius: 6px !important;
    padding: 0.65rem 1.2rem !important;
    box-shadow: 0 0 16px rgba(37, 99, 235, 0.45) !important;
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    box-shadow: 0 0 25px rgba(56, 189, 248, 0.6) !important;
    transform: translateY(-1px) !important;
}
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# FÁBRICA DE CLIENTE MQTT UNIVERSAL (COMPATIBLE PAHO 1.X Y 2.X)
# ==============================================================================
def create_mqtt_client(client_prefix: str) -> mqtt.Client:
    cid = f"{client_prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
    try:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=cid, clean_session=True)

# ==============================================================================
# GATEWAY IoT DE TELEMETRÍA PERSISTENTE
# ==============================================================================
class IoTTelemetryGateway:
    def __init__(self, broker: str = "broker.mqttdashboard.com", port: int = 1883, device_id: str = "esp32_main"):
        self.broker = broker
        self.port = port
        self.device_id = device_id
        self.topic_telemetry = f"devices/{device_id}/telemetry"

        self._lock = threading.Lock()
        self.connected = False
        self.last_update = 0
        self.packet_count = 0
        self.telemetry = {
            "temperature": 0.0,
            "humidity": 0.0,
            "pressure": 0.0,
            "uptime": 0
        }

        self._client = create_mqtt_client("Streamlit_Telemetry")
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._start()

    def _start(self):
        try:
            self._client.connect(self.broker, self.port, keepalive=30)
            self._client.loop_start()
        except Exception:
            self.connected = False

    def _on_connect(self, client, userdata, flags, *args, **kwargs):
        # args[0] es rc / reason_code en Paho 1.x y 2.x
        rc = args[0] if len(args) > 0 else 0
        success = (rc == 0) or (getattr(rc, "is_failure", False) is False)
        if success:
            with self._lock:
                self.connected = True
            client.subscribe(self.topic_telemetry, qos=0)

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        with self._lock:
            self.connected = False

    def _on_message(self, client, userdata, msg):
        try:
            raw = msg.payload.decode("utf-8", errors="ignore")
            data = json.loads(raw)
            with self._lock:
                self.telemetry["temperature"] = float(data.get("temperature", data.get("Temperatura", 0.0)))
                self.telemetry["humidity"] = float(data.get("humidity", data.get("Humedad", 0.0)))
                self.telemetry["pressure"] = float(data.get("pressure", data.get("Presion", 1013.25)))
                self.telemetry["uptime"] = int(data.get("uptime", 0))
                self.last_update = time.time()
                self.packet_count += 1
        except Exception:
            pass

    def get_snapshot(self):
        with self._lock:
            return dict(self.telemetry), self.connected, self.last_update, self.packet_count

@st.cache_resource
def get_telemetry_gateway() -> IoTTelemetryGateway:
    return IoTTelemetryGateway()

gateway = get_telemetry_gateway()
data, is_connected, last_rx, total_packets = gateway.get_snapshot()

# ==============================================================================
# INTERFAZ DE USUARIO
# ==============================================================================
c_title, c_status = st.columns([3, 1])
with c_title:
    st.title("Monitor Central de Telemetría")
    st.caption(f"Dispositivo activo: `{gateway.device_id}` | Tópico: `{gateway.topic_telemetry}`")

with c_status:
    st.write("")
    if is_connected and (time.time() - last_rx < 8) and total_packets > 0:
        st.markdown('<div style="text-align:right;"><span class="status-badge badge-online">● EN LÍNEA (TELEMETRÍA RX)</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:right;"><span class="status-badge badge-waiting">○ ESPERANDO DISPOSITIVO</span></div>', unsafe_allow_html=True)

st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Temperatura</div>
        <div class="kpi-value">{data['temperature']:.1f}<span style="font-size:1.1rem; color:#94a3b8;"> °C</span></div>
        <div style="font-size:0.75rem; color:#38bdf8;">DHT22 Calibrado</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Humedad Relativa</div>
        <div class="kpi-value">{data['humidity']:.1f}<span style="font-size:1.1rem; color:#94a3b8;"> %</span></div>
        <div style="font-size:0.75rem; color:#60a5fa;">Sensor Higrométrico</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Presión Barométrica</div>
        <div class="kpi-value">{data['pressure']:.1f}<span style="font-size:1.1rem; color:#94a3b8;"> hPa</span></div>
        <div style="font-size:0.75rem; color:#818cf8;">Presión Nominal</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    mins = data['uptime'] // 60
    secs = data['uptime'] % 60
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Tiempo Activo (Uptime)</div>
        <div class="kpi-value">{mins:02d}:{secs:02d}<span style="font-size:1.1rem; color:#94a3b8;"> m:s</span></div>
        <div style="font-size:0.75rem; color:#cbd5e1;">Paquetes recibidos: {total_packets}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")
col_btn, _ = st.columns([1, 4])
with col_btn:
    if st.button("🔄 Actualizar Cuadro", use_container_width=True):
        st.rerun()
