import streamlit as st
import paho.mqtt.client as mqtt
import json
import time
import random
import string

st.set_page_config(
    page_title="Telemetría IoT // Sensores",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilo Midnight / Galaxy Blue
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Plus+Jakarta+Sans:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
    background-color: #060913 !important;
    color: #e2e8f0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

.kpi-card {
    background: #0a1128;
    border: 1px solid rgba(56, 189, 248, 0.28);
    border-top: 3px solid #38bdf8;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6);
}

.kpi-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    color: #38bdf8;
    text-transform: uppercase;
}

.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 4px 0;
}

div.stButton > button {
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #0284c7 100%) !important;
    color: #ffffff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 600 !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 0.75rem 1.4rem !important;
    box-shadow: 0 0 16px rgba(37, 99, 235, 0.45) !important;
    transition: all 0.2s ease !important;
}

div.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 0 22px rgba(56, 189, 248, 0.6) !important;
}
</style>
""", unsafe_allow_html=True)

if 'scan_streak' not in st.session_state:
    st.session_state.scan_streak = 0
if 'last_telemetry' not in st.session_state:
    st.session_state.last_telemetry = None

def get_mqtt_client(prefix):
    cid = f"{prefix}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cid)
    except Exception:
        try:
            return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=cid)
        except Exception:
            return mqtt.Client(client_id=cid)

def escuchar_sensor(broker, port, topic, timeout_sec=4.0):
    res = {"success": False, "payload": None, "error": None}
    
    def on_message(client, userdata, message):
        raw = message.payload.decode("utf-8", errors="ignore")
        try:
            res["payload"] = json.loads(raw)
        except Exception:
            res["payload"] = {"Lectura": raw}
        res["success"] = True

    c = get_mqtt_client("Sensor_Reader")
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

with st.sidebar:
    st.markdown("### Parámetros de Enlace")
    broker_input = st.text_input("Broker MQTT:", value="broker.mqttdashboard.com")
    port_input = st.number_input("Puerto:", value=1883)
    prefijo_input = st.text_input("Prefijo de Usuario / Proyecto (opcional):", value="")
    base_topic = f"{prefijo_input.strip() + '/' if prefijo_input.strip() else ''}Sensor/THP2"
    topic_input = st.text_input("Tópico de Telemetría:", value=base_topic)
    
    modo_sim = st.toggle("Modo de prueba (simulación local)", value=False, 
                         help="Activa este modo para verificar la interfaz si el circuito Wokwi no está en ejecución.")
    st.divider()
    st.markdown(f"**Lecturas consecutivas:** `{st.session_state.scan_streak}`")

st.title("📡 Monitor de Sensores IoT")
st.caption("Recepción en tiempo real de temperatura, humedad y presión atmosférica desde microcontrolador ESP32.")

if st.button("🔄 Consultar telemetría del sensor", use_container_width=True):
    with st.spinner("Conectando con el broker..."):
        if modo_sim:
            time.sleep(0.2)
            res = {
                "success": True,
                "payload": {
                    "Temperatura": round(random.uniform(21.0, 29.5), 1),
                    "Humedad": round(random.uniform(45.0, 75.0), 1),
                    "Presion": round(random.uniform(995.0, 1018.0), 1)
                },
                "error": None
            }
        else:
            res = escuchar_sensor(broker_input, int(port_input), topic_input)

    if res["success"]:
        st.session_state.last_telemetry = res["payload"]
        st.session_state.scan_streak += 1
        st.success("Paquete de telemetría recibido correctamente.")
    else:
        st.session_state.scan_streak = 0
        st.error(f"No se recibieron datos: {res['error'] or 'Tiempo de espera agotado. Verifique que la simulación en Wokwi esté iniciada.'}")

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
                    <div style="font-size:0.75rem; color:#94a3b8;">Última lectura</div>
                </div>
                """, unsafe_allow_html=True)
                
        st.write("")
        temp = float(data.get("Temperatura", data.get("Temp", 24)))
        if temp > 28:
            estado_texto = "Temperatura por encima del umbral de confort (> 28 °C)."
            color_borde = "#f59e0b"
            etiqueta = "Alerta Térmica"
        else:
            estado_texto = "Variables ambientales dentro de los rangos nominales."
            color_borde = "#38bdf8"
            etiqueta = "Condiciones Normales"
            
        st.markdown(f"""
        <div style="background:#0a1128; border:1px solid rgba(255,255,255,0.08); border-left:4px solid {color_borde}; border-radius:8px; padding:14px;">
            <div style="font-weight:600; color:{color_borde}; font-size:0.92rem;">Diagnóstico: {etiqueta}</div>
            <div style="color:#cbd5e1; font-size:0.86rem; margin-top:2px;">{estado_texto}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.code(str(data))
