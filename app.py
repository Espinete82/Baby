import streamlit as st
import datetime
from datetime import timedelta

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="BebéGuía - El Camino Medio", page_icon="🌙", layout="centered")

# --- INICIALIZACIÓN DEL ESTADO ---
if 'baby' not in st.session_state:
    st.session_state.baby = None
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'phase' not in st.session_state:
    st.session_state.phase = "idle"  # idle, feeding, sleeping, activity
if 'phaseStart' not in st.session_state:
    st.session_state.phaseStart = None
if 'page' not in st.session_state:
    st.session_state.page = "setup"

# --- FUNCIONES AUXILIARES ---
def get_age_days(birth_date):
    if not birth_date: return 0
    return (datetime.date.today() - birth_date).days

def get_aw_max(days):
    weeks = days // 7
    if weeks < 4: return 75
    elif weeks < 8: return 90
    elif weeks < 12: return 105
    elif weeks < 16: return 120
    else: return 150

def add_log(log_type, dur_min=0, color=None):
    now = datetime.datetime.now()
    log = {"type": log_type, "ts": now, "durMin": dur_min, "color": color}
    st.session_state.logs.append(log)

def change_phase(new_phase):
    now = datetime.datetime.now()
    if st.session_state.phaseStart and st.session_state.phase != "idle":
        elapsed = (now - st.session_state.phaseStart).total_seconds() / 60
        add_log(st.session_state.phase, int(elapsed))
    
    st.session_state.phase = new_phase
    st.session_state.phaseStart = now

# --- VISTAS ---

def render_setup():
    st.markdown("<h1 style='text-align: center; color: #4B5563;'>🌙 BebéGuía</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF;'>Tu guía flexible: respeta su biología, protege tu descanso.</p>", unsafe_allow_html=True)
    
    with st.form("setup_form"):
        name = st.text_input("Nombre del bebé")
        birth = st.date_input("Fecha de nacimiento", max_value=datetime.date.today())
        feed = st.selectbox("Alimentación", ["Lactancia materna exclusiva", "Mixta (pecho + biberón)", "Fórmula / Biberón"])
        
        submitted = st.form_submit_button("Empezar →", use_container_width=True)
        if submitted and name:
            st.session_state.baby = {"name": name, "birth": birth, "feed": feed}
            st.session_state.page = "main"
            change_phase("idle")
            st.rerun()

def render_main():
    baby = st.session_state.baby
    days = get_age_days(baby['birth'])
    aw_max = get_aw_max(days)
    es_fase_1 = days < 120  # Lógica del "Camino Medio"
    
    # Cabecera
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(f"👶 {baby['name']}")
        st.caption(f"Edad: {days} días | Fase {'1 (Biología)' if es_fase_1 else '2 (Rutinas)'}")
    with col2:
        if st.button("📋", help="Historial"):
            st.session_state.page = "history"
            st.rerun()

    # Cálculo de tiempo transcurrido
    elapsed_min = 0
    now = datetime.datetime.now()
    if st.session_state.phaseStart:
        elapsed_min = int((now - st.session_state.phaseStart).total_seconds() / 60)

    # --- MENSAJES DINÁMICOS BASADOS EN LA EDAD (El Camino Medio) ---
    st.markdown("---")
    if st.session_state.phase == "idle":
        st.info("☀️ **Despierto y tranquilo**\n\nObserva sus señales (bostezos, mirada fija). La alimentación es a demanda, si busca, ofrécele.")
    
    elif st.session_state.phase == "feeding":
        if es_fase_1:
            st.success(f"🍼 **Comiendo** (hace {elapsed_min} min)\n\n"
                       f"**FASE 1 (Supervivencia):** Deja que se duerma comiendo. Es la biología actuando. "
                       f"El contacto y la succión son su mayor fuente de calma. Si se duerme, pasa a la fase de sueño. ¡Y mamá, bebe agua!")
        else:
            st.success(f"🍼 **Comiendo** (hace {elapsed_min} min)\n\n"
                       f"**FASE 2 (Transición):** A esta edad, si los despertares nocturnos os agotan, puedes probar a separar la toma del sueño (E.A.S.Y.). "
                       f"Intenta que coma, jugad un rato suave, y luego a dormir.")
    
    elif st.session_state.phase == "sleeping":
        st.markdown(f"<div style='background-color:#F3E8FF; padding:15px; border-radius:10px;'>"
                    f"😴 <b>Durmiendo</b> (hace {elapsed_min} min)<br><br>"
                    f"<i>SUEÑO SEGURO:</i> Boca arriba, superficie firme, sin mantas sueltas. "
                    f"{'Usa el porteo para alargar siestas si está irritable.' if es_fase_1 else 'Intenta que haga alguna siesta en su cuna para crear hábito.'}</div>", unsafe_allow_html=True)
    
    elif st.session_state.phase == "activity":
        if es_fase_1:
            st.info(f"🎯 **Despierto** (hace {elapsed_min} min)\n\n"
                    f"**FASE 1:** Ofrece brazos y porteo sin límite. De día luz natural y ruido; de noche oscuridad y silencio. "
                    f"Ventana de sueño: llévalo a dormir en cuanto veas señales, no esperes al llanto.")
        else:
            st.info(f"🎯 **Tiempo de juego** (hace {elapsed_min} min)\n\n"
                    f"**FASE 2:** Ideal para el movimiento libre (suelo). Observa las señales de cansancio para acostarlo adormilado pero despierto.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- BOTONES DE ACCIÓN RÁPIDA (Flexibles) ---
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🍼 Comer", use_container_width=True): change_phase("feeding"); st.rerun()
    if c2.button("😴 Dormir", use_container_width=True): change_phase("sleeping"); st.rerun()
    if c3.button("🎯 Jugar", use_container_width=True): change_phase("activity"); st.rerun()
    if c4.button("🧷 Pañal", use_container_width=True): st.session_state.page = "diaper"; st.rerun()

    # --- EL RELOJ PREDICTIVO (Línea de Ritmo Diario) ---
    st.markdown("---")
    st.markdown("### ⏱️ Reloj de Previsión Diaria")
    
    # Lógica predictiva
    prediccion_hora = ""
    prediccion_texto = ""
    prediccion_color = "#10B981" # Verde por defecto
    
    if st.session_state.phase in ["activity", "idle"]:
        min_restantes = aw_max - elapsed_min
        hora_predicha = now + timedelta(minutes=min_restantes)
        prediccion_hora = hora_predicha.strftime("%H:%M")
        
        if min_restantes > 15:
            prediccion_texto = f"Es probable que tenga sueño sobre las {prediccion_hora}."
        elif min_restantes >= 0:
            prediccion_texto = f"⚠️ Cierre de ventana de sueño inminente ({prediccion_hora}). Ve bajando luces."
            prediccion_color = "#F59E0B" # Naranja
        else:
            prediccion_texto = f"🚨 Ventana de sueño excedida. Evita sobreestimular y busca calmarle ya."
            prediccion_color = "#EF4444" # Rojo
            
    elif st.session_state.phase == "sleeping":
        prediccion_texto = f"Al despertar, lo biológicamente esperado es que pida toma 🍼."
        prediccion_color = "#8B5CF6" # Morado
    elif st.session_state.phase == "feeding":
        prediccion_texto = f"Si se duerme mamando/tomando biberón, ¡perfecto! Si no, pasad a juego suave 🎯."
        prediccion_color = "#3B82F6" # Azul

    # Visualización del "Reloj" (Timeline CSS)
    hora_actual_str = now.strftime("%H:%M")
    
    html_reloj = f"""
    <div style="background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); border: 1px solid #E5E7EB;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 10px; font-weight: bold; color: #4B5563;">
            <span>🌅 Mañana</span>
            <span style="color: {prediccion_color}; font-size: 1.2em;">🕒 Ahora: {hora_actual_str}</span>
            <span>🌙 Noche</span>
        </div>
        <div style="width: 100%; height: 12px; background: #E5E7EB; border-radius: 10px; position: relative; overflow: hidden;">
            <div style="width: {(now.hour * 60 + now.minute) / 1440 * 100}%; height: 100%; background: linear-gradient(90deg, #FCD34D 0%, #F59E0B 50%, #3B82F6 100%); border-radius: 10px;"></div>
        </div>
        <div style="margin-top: 15px; padding: 12px; border-left: 4px solid {prediccion_color}; background: #F9FAFB; border-radius: 0 8px 8px 0; font-size: 0.95em; color: #374151;">
            <b>🔮 Previsión:</b> {prediccion_texto}
        </div>
    </div>
    """
    st.markdown(html_reloj, unsafe_allow_html=True)

    # Métricas Positivas Diarias
    st.markdown("<br>", unsafe_allow_html=True)
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    tomas_hoy = len([l for l in logs_hoy if l['type'] == "feeding"])
    
    m1, m2 = st.columns(2)
    m1.metric("Tomas de hoy", f"{tomas_hoy} / 8+", help="Las tomas son a demanda. El 8 es un mínimo orientativo para asegurar hidratación.")
    
    # Botón de ritual de noche si son más de las 18:00
    if now.hour >= 18 and st.session_state.phase != "sleeping":
        if st.button("🌙 Iniciar Ritual de Noche", use_container_width=True):
            st.info("🛁 **Modo Noche Activado:**\n1. Baja luces de la casa.\n2. Baño / Masaje si le relaja.\n3. Entorno aburrido (sin pantallas).\n4. Toma final tranquila.")

def render_history():
    st.subheader("📋 Historial")
    if st.button("← Volver"):
        st.session_state.page = "main"
        st.rerun()
    
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    
    if not logs_hoy:
        st.write("Sin registros hoy.")
    else:
        for l in reversed(logs_hoy):
            hora = l['ts'].strftime("%H:%M")
            icono = {"feeding": "🍼", "sleeping": "😴", "activity": "🎯"}.get(l['type'], "🧷")
            st.markdown(f"- **{hora}** | {icono} {l['type']} {f'({l.get('durMin',0)} min)' if l.get('durMin') else ''}")

def render_diaper():
    st.subheader("🧷 Pañal")
    tipo = st.radio("Contenido:", ["Pipí 💧", "Caca 💩", "Pipí + Caca 💧💩"])
    c1, c2 = st.columns(2)
    if c1.button("Guardar", type="primary"):
        add_log(tipo)
        st.session_state.page = "main"
        st.rerun()
    if c2.button("Cancelar"):
        st.session_state.page = "main"
        st.rerun()

# --- RUTEO PRINCIPAL ---
if st.session_state.page == "setup": render_setup()
elif st.session_state.page == "main": render_main()
elif st.session_state.page == "diaper": render_diaper()
elif st.session_state.page == "history": render_history()
