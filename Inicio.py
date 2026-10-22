import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string

# ------------------------------------------------------------------
# CONFIGURACIÓN GENERAL & IDENTIDAD KROV NOIR
# ------------------------------------------------------------------
st.set_page_config(
    page_title="Sentinel // Recepción Telemetría",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&family=Spectral:wght@600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #030407 !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

/* Tarjetas HUD Krov */
.hud-panel {
    background: linear-gradient(145deg, rgba(14, 18, 30, 0.95) 0%, rgba(6, 8, 14, 0.98) 100%);
    border: 1px solid rgba(212, 175, 55, 0.25);
    border-top: 3px solid #d4af37;
    border-radius: 8px;
    padding: 18px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
    margin-bottom: 14px;
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    color: #d4af37;
    text-transform: uppercase;
}

.kpi-value {
    font-family: 'Spectral', Georgia, serif;
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.1;
}

.xp-badge {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid #00f0ff;
    color: #00f0ff;
    padding: 4px 10px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
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
# ESTADO DE SESIÓN & GAMIFICACIÓN
# ------------------------------------------------------------------
if 'xp' not in st.session_state:
    st.session_state.xp = 120
if 'scan_streak' not in st.session_state:
    st.session_state.scan_streak = 0
if 'last_telemetry' not in st.session_state:
    st.session_state.last_telemetry = None
if 'history' not in st.session_state:
    st.session_state.history = []

def calcular_rango(xp):
    if xp < 250: return "Operador Cadete [Nvl 1]"
    elif xp < 600: return "Especialista Ciberfísico [Nvl 2]"
    elif xp < 1200: return "Comandante de Red IoT [Nvl 3]"
    return "Arquitecto Sentinel [Master]"

# ------------------------------------------------------------------
# CLIENTE MQTT RESILIENTE (PAHO 1.X Y 2.X COMPATIBLE)
# ------------------------------------------------------------------
def get_mqtt_client(client_prefix):
    rand_suffix = "".join(random.choices(string.ascii_letters + string.digits, k=6))
    cid = f"{client_prefix}_{rand_suffix}"
    try:
        import paho.mqtt.enums as mqtt_enums
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            return mqtt.Client(client_id=cid)

def escuchar_sensor(broker, port, topic, timeout_sec=3.5):
    resultado = {"success": False, "payload": None, "error": None}
    
    def on_message(client, userdata, message):
        raw = message.payload.decode("utf-8", errors="ignore")
        try:
            resultado["payload"] = json.loads(raw)
        except Exception:
            resultado["payload"] = {"Lectura_Raw": raw}
        resultado["success"] = True

    client = get_mqtt_client("Krov_Sensor")
    client.on_message = on_message
    
    try:
        client.connect(broker, port, keepalive=15)
        client.subscribe(topic)
        client.loop_start()
        
        limite = time.time() + timeout_sec
        while not resultado["success"] and time.time() < limite:
            time.sleep(0.05)
            
        client.loop_stop()
        client.disconnect()
    except Exception as e:
        resultado["error"] = str(e)
        
    return resultado

# ------------------------------------------------------------------
# BARRA LATERAL: PARÁMETROS DE RED
# ------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="kpi-title">KROV // CONFIGURACIÓN BROKER</div>', unsafe_allow_html=True)
    st.write("")
    broker_input = st.text_input("Broker Endpoint:", value="broker.mqttdashboard.com")
    port_input = st.number_input("Puerto TCP:", value=1883, min_value=1, max_value=65535)
    topic_input = st.text_input("Tópico Telemetría:", value="Sensor/THP2")
    
    modo_simulacion = st.toggle("Modo Simulación de Respaldo", value=False, 
                                help="Genera datos sintéticos si el circuito Wokwi no está conectado.")
    
    st.divider()
    st.markdown(f"**Rango:** `{calcular_rango(st.session_state.xp)}`")
    st.markdown(f"**XP Total:** `{st.session_state.xp} pts`")
    st.markdown(f"**Racha de Análisis:** `{st.session_state.scan_streak} scans`")

# ------------------------------------------------------------------
# ENCABEZADO PRINCIPAL
# ------------------------------------------------------------------
c_head, c_xp = st.columns([3, 1])
with c_head:
    st.title("Telemetría Ciberfísica Sentinel")
    st.caption("Recepción e inspección en tiempo real de nodos microcontroladores ESP32 (Wokwi / IoT)")
with c_xp:
    st.write("")
    st.markdown(f'<div style="text-align:right;"><span class="xp-badge">⚡ {st.session_state.xp} XP</span></div>', unsafe_allow_html=True)

st.write("")

# Botón de Captura
if st.button("📡 Escanear Telemetría de Sensores", use_container_width=True):
    with st.spinner("Sintonizando canal ciberfísico en el broker..."):
        if modo_simulacion:
            time.sleep(0.4)
            data = {
                "Temperatura": round(random.uniform(19.5, 31.0), 2),
                "Humedad": round(random.uniform(42.0, 78.0), 1),
                "Presion": round(random.uniform(995.0, 1022.0), 1)
            }
            res = {"success": True, "payload": data, "error": None}
        else:
            res = escuchar_sensor(broker_input, int(port_input), topic_input)

    if res["success"]:
        st.session_state.last_telemetry = res["payload"]
        st.session_state.xp += 35
        st.session_state.scan_streak += 1
        st.session_state.history.append({"t": time.strftime("%H:%M:%S"), "val": res["payload"]})
        st.success("✅ Telemetría sincronizada correctamente (+35 XP).")
    else:
        st.session_state.scan_streak = 0
        st.error(f"⚠️ Enlace sin respuesta: {res['error'] or 'No se detectó publicación del ESP32 en el plazo asignado.'}")
        st.info("💡 Tip: Inicia la simulación en Wokwi o activa el 'Modo Simulación de Respaldo' en la barra lateral.")

# ------------------------------------------------------------------
# VISUALIZACIÓN HUD & DIAGNÓSTICO
# ------------------------------------------------------------------
if st.session_state.last_telemetry:
    telemetry = st.session_state.last_telemetry
    
    st.markdown("---")
    st.markdown('<div class="kpi-title">● DIAGNÓSTICO AMBIENTAL CIBERFÍSICO</div>', unsafe_allow_html=True)
    st.write("")
    
    if isinstance(telemetry, dict):
        cols = st.columns(len(telemetry))
        for i, (k, v) in enumerate(telemetry.items()):
            with cols[i]:
                st.markdown(f"""
                <div class="hud-panel">
                    <div class="kpi-title">{k.upper()}</div>
                    <div class="kpi-value">{v}</div>
                    <div style="font-size:0.75rem; color:#94a3b8; margin-top:4px;">Canal nominal verificado</div>
                </div>
                """, unsafe_allow_html=True)
                
        # Mini-análisis gamificado
        st.markdown('<div class="hud-panel">', unsafe_allow_html=True)
        st.markdown("**Evaluación del Sector:**")
        temp = float(telemetry.get("Temperatura", telemetry.get("Temp", 24)))
        if temp > 28:
            st.warning("🔥 Alerta Térmica: Gradiente superior al estándar. Activar ventilación forzada.")
        else:
            st.info("❄️ Sector Estable: Variables bioclimáticas dentro del margen de seguridad Krov.")
        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.code(str(telemetry))
