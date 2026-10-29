import streamlit as st
import streamlit.components.v1 as components
import paho.mqtt.client as mqtt
import json
import time
import random
import threading

# ==============================================================================
# CONFIGURACIÓN GENERAL Y ESTILOS
# ==============================================================================
WOKWI_PROJECT_ID = "479234255516779521"

st.set_page_config(
    page_title="Telemetría IoT // Gemelo Digital",
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

.block-container {
    max-width: 1400px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2rem !important;
}

.status-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    letter-spacing: 0.08em;
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
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.55);
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    color: #94a3b8;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.kpi-value {
    font-size: 2.1rem;
    font-weight: 700;
    color: #ffffff;
    margin: 4px 0;
}

.panel-card {
    background: linear-gradient(145deg, #0d152d 0%, #080d1e 100%);
    border: 1px solid rgba(56, 189, 248, 0.22);
    border-radius: 10px;
    padding: 18px;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
    margin-bottom: 1rem;
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
# CLIENTE MQTT RESILIENTE Y PERSISTENTE
# ==============================================================================
def create_mqtt_client(client_prefix: str) -> mqtt.Client:
    cid = f"{client_prefix}_{int(time.time())}_{random.randint(1000, 9999)}"
    try:
        return mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except (AttributeError, TypeError):
        return mqtt.Client(client_id=cid, clean_session=True)

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
# ENCABEZADO Y KPIS SUPERIORES
# ==============================================================================
c_title, c_status = st.columns([3, 1])
with c_title:
    st.title("📡 Monitor Central // Gemelo Digital")
    st.caption(f"Nodo emulado: `{gateway.device_id}` | Protocolo: `MQTT v3.1.1` | Tópico: `{gateway.topic_telemetry}`")

with c_status:
    st.write("")
    if is_connected and (time.time() - last_rx < 8) and total_packets > 0:
        st.markdown('<div style="text-align:right;"><span class="status-badge badge-online">● EN LÍNEA (TELEMETRÍA RX)</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align:right;"><span class="status-badge badge-waiting">○ ESPERANDO EMULADOR</span></div>', unsafe_allow_html=True)

st.write("")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Temperatura</div>
        <div class="kpi-value">{data['temperature']:.1f}<span style="font-size:1.1rem; color:#94a3b8;"> °C</span></div>
        <div style="font-size:0.75rem; color:#38bdf8;">DHT22 Sensor</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">Humedad</div>
        <div class="kpi-value">{data['humidity']:.1f}<span style="font-size:1.1rem; color:#94a3b8;"> %</span></div>
        <div style="font-size:0.75rem; color:#60a5fa;">Humedad Relativa</div>
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
        <div class="kpi-title">Uptime Hardware</div>
        <div class="kpi-value">{mins:02d}:{secs:02d}<span style="font-size:1.1rem; color:#94a3b8;"> m:s</span></div>
        <div style="font-size:0.75rem; color:#cbd5e1;">Paquetes: {total_packets}</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ==============================================================================
# PANTALLA DIVIDIDA: DIAGNÓSTICO A LA IZQUIERDA Y HARDWARE A LA DERECHA
# ==============================================================================
col_diag, col_twin = st.columns([1, 1.4], gap="large")

with col_diag:
    temp_val = data['temperature']
    if temp_val > 28.0:
        cond_label = "Alerta Térmica Elevada"
        cond_color = "#f59e0b"
        cond_desc = "La temperatura supera el umbral estándar de 28 °C."
    else:
        cond_label = "Condiciones Nominales"
        cond_color = "#2dd4bf"
        cond_desc = "Variables termo-higrométricas en rango seguro."

    st.markdown(f"""
    <div class="panel-card" style="border-left: 4px solid {cond_color};">
        <div style="font-family:'JetBrains Mono'; font-size:0.72rem; color:{cond_color}; text-transform:uppercase; letter-spacing:0.1em; font-weight:600;">Estado Ambiental</div>
        <div style="font-size:1.2rem; font-weight:700; color:#ffffff; margin:4px 0 6px 0;">{cond_label}</div>
        <div style="font-size:0.88rem; color:#cbd5e1; line-height:1.5;">{cond_desc}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="panel-card">
        <div style="font-family:'JetBrains Mono'; font-size:0.72rem; color:#38bdf8; text-transform:uppercase; letter-spacing:0.1em; font-weight:600; margin-bottom:6px;">Enlace Telemétrico</div>
        <div style="font-size:0.86rem; color:#cbd5e1; line-height:1.6;">
            ● <b>Broker:</b> <code>broker.mqttdashboard.com:1883</code><br>
            ● <b>Suscripción:</b> <code>{gateway.topic_telemetry}</code><br>
            ● <b>Último paquete:</b> hace {max(0, int(time.time() - last_rx)) if last_rx > 0 else '—'} segundos
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🔄 Refrescar Panel de Métricas", use_container_width=True):
        st.rerun()

with col_twin:
    # Marco de simulación Wokwi tipo chassis
    components.html(
        f"""
        <div style="background: linear-gradient(145deg, #0d152d 0%, #080d1e 100%);
                    border: 1px solid rgba(56, 189, 248, 0.28);
                    border-top: 3px solid #38bdf8;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.7), 0 0 20px rgba(56,189,248,0.12);">
            <div style="display: flex; justify-content: space-between; align-items: center;
                        padding: 10px 16px; background: rgba(6, 9, 19, 0.9);
                        border-bottom: 1px solid rgba(56, 189, 248, 0.2);
                        font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;">
                <div style="color: #cbd5e1; display: flex; align-items: center; gap: 8px;">
                    <span style="color: #38bdf8;">✦</span> GEMELO DIGITAL // ESP32 WOKWI
                </div>
                <div style="color: #2dd4bf; display: flex; align-items: center; gap: 6px;">
                    <span style="display:inline-block; width:7px; height:7px; border-radius:50%; background:#2dd4bf; box-shadow:0 0 8px #2dd4bf;"></span>
                    CANAL ACTIVO
                </div>
            </div>
            <iframe 
                src="https://wokwi.com/projects/{WOKWI_PROJECT_ID}?embed=1&view=diagram" 
                width="100%" 
                height="530" 
                style="border: none; display: block; background: #0c1222;"
                allow="fullscreen; autoplay">
            </iframe>
        </div>
        """,
        height=580
    )
