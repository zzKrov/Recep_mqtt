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
    page_title="Lector de Sensores IoT // Krov",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------------
# ESTILOS OSCUROS LIMPIOS (SIN CAJAS VACÍAS)
# ------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #030407 !important;
    color: #f1f5f9 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

.kpi-card {
    background: #0d131f;
    border: 1px solid rgba(212, 175, 55, 0.35);
    border-top: 3px solid #d4af37;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.15em;
    color: #d4af37;
    text-transform: uppercase;
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 4px 0;
}

.score-badge {
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid #00f0ff;
    color: #00f0ff;
    padding: 4px 12px;
    border-radius: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
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
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 25px rgba(212, 175, 55, 0.6) !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------
# ESTADO Y PUNTUACIÓN
# ------------------------------------------------------------------
if 'xp' not in st.session_state:
    st.session_state.xp = 120
if 'scan_streak' not in st.session_state:
    st.session_state.scan_streak = 0
if 'last_telemetry' not in st.session_state:
    st.session_state.last_telemetry = None

def obtener_nivel(xp):
    if xp < 250: return "Nivel 1 · Principiante"
    elif xp < 600: return "Nivel 2 · Intermedio"
    elif xp < 1200: return "Nivel 3 · Avanzado"
    return "Nivel Master"

# ------------------------------------------------------------------
# CLIENTE MQTT COMPATIBLE
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
            res["payload"] = {"Lectura": raw}
        res["success"] = True

    c = get_mqtt_client("Krov_Sensor")
    c.on_message = on_message
    
    try:
        c.connect(broker, port, keepalive=15)
        c.subscribe(topic)
        c.loop_start()
        
        limite = time.time() + timeout_sec
        while not res["success"] and time.time() < limite:
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
    st.markdown("### Conexión del Sensor")
    broker_input = st.text_input("Servidor (Broker):", value="broker.mqttdashboard.com")
    port_input = st.number_input("Puerto:", value=1883)
    topic_input = st.text_input("Canal (Tópico):", value="Sensor/THP2")
    
    modo_sim = st.toggle("Modo prueba (Simular datos)", value=False, 
                         help="Activa este modo si Wokwi está apagado para probar la interfaz.")
    
    st.divider()
    st.markdown(f"**Tu rango:** `{obtener_nivel(st.session_state.xp)}`")
    st.markdown(f"**Puntos ganados:** `{st.session_state.xp} pts`")
    st.markdown(f"**Racha de lecturas:** `{st.session_state.scan_streak}`")

# ------------------------------------------------------------------
# CUERPO PRINCIPAL
# ------------------------------------------------------------------
c1, c2 = st.columns([3, 1])
with c1:
    st.title("Lector de Sensores IoT")
    st.caption("Recepción en tiempo real de temperatura, humedad y presión desde el microcontrolador")
with c2:
    st.write("")
    st.markdown(f'<div style="text-align:right;"><span class="score-badge">⚡ {st.session_state.xp} PUNTOS</span></div>', unsafe_allow_html=True)

st.write("")

if st.button("🔄 Leer datos del sensor", use_container_width=True):
    with st.spinner("Conectando con el sensor..."):
        if modo_sim:
            time.sleep(0.3)
            datos_prueba = {
                "Temperatura": round(random.uniform(20.0, 31.0), 1),
                "Humedad": round(random.uniform(45.0, 78.0), 1),
                "Presion": round(random.uniform(995.0, 1020.0), 1)
            }
            res = {"success": True, "payload": datos_prueba, "error": None}
        else:
            res = escuchar_sensor(broker_input, int(port_input), topic_input)

    if res["success"]:
        st.session_state.last_telemetry = res["payload"]
        st.session_state.xp += 30
        st.session_state.scan_streak += 1
        st.success("✅ Datos recibidos correctamente (+30 puntos).")
    else:
        st.session_state.scan_streak = 0
        st.error(f"No se recibieron datos: {res['error'] or 'El sensor no ha publicado datos recientemente.'}")
        st.info("Tip: Inicia la simulación en Wokwi o activa el switch 'Modo prueba' en la barra lateral.")

# ------------------------------------------------------------------
# RESULTADOS AUTOCONTENIDOS (SIN CAJAS VACÍAS NI BORDER=TRUE)
# ------------------------------------------------------------------
if st.session_state.last_telemetry:
    data = st.session_state.last_telemetry
    st.write("")
    
    if isinstance(data, dict):
        cols = st.columns(len(data))
        for i, (param, valor) in enumerate(data.items()):
            with cols[i]:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-title">{param}</div>
                    <div class="kpi-value">{valor}</div>
                    <div style="font-size:0.75rem; color:#94a3b8;">Lectura actual</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.write("")
        
        # Tarjeta de estado de una sola pieza (autocontenida)
        temp = float(data.get("Temperatura", data.get("Temp", 24)))
        if temp > 28:
            estado_texto = "Temperatura alta (más de 28 °C). Se recomienda encender ventilación."
            color_borde = "#f59e0b"
            etiqueta = "Caluroso"
        else:
            estado_texto = "Condiciones normales. Temperatura y humedad en rango agradable."
            color_borde = "#10b981"
            etiqueta = "Ambiente Estable"
            
        st.markdown(f"""
        <div style="background:#0d131f; border:1px solid rgba(255,255,255,0.1); border-left:4px solid {color_borde}; border-radius:8px; padding:16px;">
            <div style="font-weight:700; color:{color_borde}; font-size:0.95rem;">Estado: {etiqueta}</div>
            <div style="color:#cbd5e1; font-size:0.88rem; margin-top:4px;">{estado_texto}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.code(str(data))
