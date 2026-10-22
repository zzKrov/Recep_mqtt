import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Krov Sentinel // Telemetría Ciberfísica",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# ESTILOS KROV NOIR (ESTILIZACIÓN DE CONTENEDORES NATIVOS)
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&family=Spectral:wght@600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #030407 !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Estilización directa de contenedores nativos (Elimina cajas vacías al 100%) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(14, 18, 30, 0.95) 0%, rgba(6, 8, 14, 0.98) 100%) !important;
    border: 1px solid rgba(212, 175, 55, 0.28) !important;
    border-top: 3px solid #d4af37 !important;
    border-radius: 8px !important;
    padding: 1.2rem !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.75) !important;
    margin-bottom: 0.8rem !important;
}

.kpi-card {
    background: rgba(10, 14, 24, 0.92);
    border: 1px solid rgba(212, 175, 55, 0.25);
    border-top: 2px solid #d4af37;
    border-radius: 6px;
    padding: 14px;
    text-align: center;
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.16em;
    color: #d4af37;
    text-transform: uppercase;
}

.kpi-value {
    font-family: 'Spectral', Georgia, serif;
    font-size: 2.1rem;
    font-weight: 700;
    color: #ffffff;
    margin: 4px 0;
}

.xp-badge {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid #00f0ff;
    color: #00f0ff;
    padding: 4px 12px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    font-weight: 700;
}

div.stButton > button {
    background: linear-gradient(135deg, #d4af37 0%, #b45309 100%) !important;
    color: #030407 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.75rem 1.4rem !important;
    box-shadow: 0 0 20px rgba(212, 175, 55, 0.35) !important;
    transition: all 0.25s ease !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 30px rgba(212, 175, 55, 0.7) !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO & GAMIFICACIÓN
# ------------------------------------------------------------------
if 'xp' not in st.session_state:
    st.session_state.xp = 150
if 'scan_streak' not in st.session_state:
    st.session_state.scan_streak = 0
if 'last_telemetry' not in st.session_state:
    st.session_state.last_telemetry = None

def obtener_rango(xp):
    if xp < 300: return "Operador Cadete [Nvl 1]"
    elif xp < 800: return "Especialista Ciberfísico [Nvl 2]"
    elif xp < 1500: return "Comandante de Red IoT [Nvl 3]"
    return "Arquitecto Sentinel [Master]"

# ------------------------------------------------------------------
# CLIENTE MQTT RESILIENTE (SIN COLISIONES DE ID)
# ------------------------------------------------------------------
def get_mqtt_client(prefix):
    cid = f"{prefix}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            return mqtt.Client(client_id=cid)

def escuchar_sensor(broker, port, topic, timeout_sec=3.5):
    res = {"success": False, "payload": None, "error": None}
    
    def on_message(client, userdata, message):
        raw = message.payload.decode("utf-8", errors="ignore")
        try:
            res["payload"] = json.loads(raw)
        except Exception:
            res["payload"] = {"Lectura_Directa": raw}
        res["success"] = True

    c = get_mqtt_client("Krov_Sentinel")
    c.on_message = on_message
    
    try:
        c.connect(broker, port, keepalive=15)
        c.subscribe(topic)
        c.loop_start()
        
        t_limite = time.time() + timeout_sec
        while not res["success"] and time.time() < t_limite:
            time.sleep(0.05)
            
        c.loop_stop()
        c.disconnect()
    except Exception as e:
        res["error"] = str(e)
        
    return res

# ------------------------------------------------------------------
# BARRA LATERAL
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown("### KROV // BROKER SETUP")
    broker_input = st.text_input("Broker:", value="broker.mqttdashboard.com")
    port_input = st.number_input("Puerto TCP:", value=1883)
    topic_input = st.text_input("Tópico Sensor:", value="Sensor/THP2")
    
    modo_sim = st.toggle("Simulación de Respaldo", value=False, 
                         help="Activa datos sintéticos si la simulación de Wokwi no está corriendo.")
    
    st.divider()
    st.markdown(f"**Rango:** `{obtener_rango(st.session_state.xp)}`")
    st.markdown(f"**XP de Inspección:** `{st.session_state.xp} pts`")
    st.markdown(f"**Racha Consecutiva:** `{st.session_state.scan_streak} scans`")

# ------------------------------------------------------------------
# CUERPO PRINCIPAL
# ------------------------------------------------------------------
c1, c2 = st.columns([3, 1])
with c1:
    st.title("Telemetría Ciberfísica Sentinel")
    st.caption("Recepción e inspección ambiental de nodos microcontroladores ESP32 (Wokwi / IoT)")
with c2:
    st.write("")
    st.markdown(f'<div style="text-align:right;"><span class="xp-badge">⚡ {st.session_state.xp} XP</span></div>', unsafe_allow_html=True)

st.write("")

if st.button("📡 Escanear Telemetría de Sensores", use_container_width=True):
    with st.spinner("Sintonizando canal en broker MQTT..."):
        if modo_sim:
            time.sleep(0.3)
            datos_mock = {
                "Temperatura": round(random.uniform(21.0, 31.5), 1),
                "Humedad": round(random.uniform(45.0, 80.0), 1),
                "Presion": round(random.uniform(990.0, 1025.0), 1)
            }
            res = {"success": True, "payload": datos_mock, "error": None}
        else:
            res = escuchar_sensor(broker_input, int(port_input), topic_input)

    if res["success"]:
        st.session_state.last_telemetry = res["payload"]
        st.session_state.xp += 35
        st.session_state.scan_streak += 1
        st.success("✅ Telemetría sincronizada con éxito (+35 XP).")
    else:
        st.session_state.scan_streak = 0
        st.error(f"⚠️ Sin señal del ESP32: {res['error'] or 'Tiempo de espera agotado sin paquetes en el tópico.'}")
        st.info("💡 Consejo: Asegúrate de darle Play al circuito en Wokwi o activa el switch 'Simulación de Respaldo'.")

# ------------------------------------------------------------------
# RENDERIZADO DE TELEMETRÍA (100% AUTOCONTENIDO)
# ------------------------------------------------------------------
if st.session_state.last_telemetry:
    data = st.session_state.last_telemetry
    st.write("")
    
    if isinstance(data, dict):
        cols = st.columns(len(data))
        for i, (param, valor) in enumerate(data.items()):
            with cols[i]:
                # Tarjeta autocontenida: abre y cierra en el mismo bloque
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">{param.upper()}</div>
                    <div class="kpi-value">{valor}</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">Canal nominal</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.write("")
        # Contenedor nativo con border=True: CERO cajas vacías
        with st.container(border=True):
            st.markdown("#### Evaluación de Seguridad Ambiental")
            temp = float(data.get("Temperatura", data.get("Temp", 24)))
            if temp > 28:
                st.warning("🔥 Alerta Térmica: Gradiente superior a 28°C. Activar ventilación forzada.")
            else:
                st.success("❄️ Sector Estable: Variables bioclimáticas dentro del margen de seguridad Krov.")
    else:
        st.code(str(data))
