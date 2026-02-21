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
                       f"El contacto y la succión son su mayor fuente de calma. Si se duerme, pasa a la fase de sueño directamente.")
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
                    f"Llévalo a dormir en cuanto veas señales, no esperes al llanto.")
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

    # --- AGENDA PREDICTIVA DE 12 HORAS (TRABAJO EN EQUIPO) ---
    st.markdown("---")
    st.subheader("📅 Planificador Familiar (Próximas 12h)")
    st.caption("Previsión de turnos para proteger el descanso de mamá ('Dream Window').")

    cursor_time = now
    limit_time = now + timedelta(hours=12)
    current_phase = st.session_state.phase
    sim_elapsed_min = elapsed_min
    feed_type = baby.get('feed', 'Mixta')
    
    agenda = []
    
    # Bucle que simula el futuro hasta 12 horas o máximo 10 eventos
    while cursor_time < limit_time and len(agenda) < 10:
        is_night = cursor_time.hour >= 20 or cursor_time.hour < 7
        # Turno de papá (Dream Window) asumido entre las 21:00 y las 03:00
        is_papas_shift = cursor_time.hour >= 21 or cursor_time.hour < 3

        if current_phase in ["idle", "activity"]:
            min_to_sleep = max(0, aw_max - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_sleep)
            
            if is_papas_shift:
                mama_role = "💤 DURMIENDO (Dream Window)"
                papa_role = "💪 Duerme al bebé en brazos/cuna"
                bg_color = "#EDE9FE" # Morado suave
                border_color = "#8B5CF6"
            else:
                mama_role = "Libre / Descanso / Ducha"
                papa_role = "Vigila el sueño o hace tareas"
                bg_color = "#ECFDF5" # Verde suave
                border_color = "#10B981"

            agenda.append({
                "hora": cursor_time.strftime("%H:%M"), "icono": "😴", 
                "evento": "Se duerme", "mama": mama_role, "papa": papa_role,
                "bg": bg_color, "border": border_color
            })
            current_phase = "sleeping"
            sim_elapsed_min = 0
            
        elif current_phase == "sleeping":
            # De día duerme ~1h, de noche los bloques pueden ser de ~3h
            sleep_duration = 180 if is_night else 60
            min_to_wake = max(0, sleep_duration - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_wake)
            
            if is_papas_shift:
                if "Fórmula" in feed_type or "Mixta" in feed_type:
                    mama_role = "💤 DURMIENDO (Del tirón)"
                    papa_role = "🍼 Prepara y da biberón completo"
                else:
                    mama_role = "🤱 Da pecho en cama (Semi-dormida)"
                    papa_role = "🧷 Trae bebé, cambia pañal y saca gases"
                bg_color = "#EFF6FF" # Azul suave
                border_color = "#3B82F6"
            else:
                mama_role = "🤱 Alimenta al bebé"
                papa_role = "Acompaña / Prepara comida"
                bg_color = "#F9FAFB" # Gris claro
                border_color = "#D1D5DB"

            agenda.append({
                "hora": cursor_time.strftime("%H:%M"), "icono": "🍼", 
                "evento": "Despierta y pide toma", "mama": mama_role, "papa": papa_role,
                "bg": bg_color, "border": border_color
            })
            current_phase = "feeding"
            sim_elapsed_min = 0
            
        elif current_phase == "feeding":
            # Asumimos que la toma dura unos 30 mins
            min_to_play = max(0, 30 - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_play)
            
            if is_night:
                # Si es de noche, no hay actividad. Vuelve a dormir.
                current_phase = "sleeping"
                sim_elapsed_min = 0
                continue 
            else:
                mama_role = "Juego suave / Estimulación"
                papa_role = "Juego suave / Estimulación"
                bg_color = "#F9FAFB"
                border_color = "#D1D5DB"
                
                agenda.append({
                    "hora": cursor_time.strftime("%H:%M"), "icono": "🎯", 
                    "evento": "Termina toma, juego", "mama": mama_role, "papa": papa_role,
                    "bg": bg_color, "border": border_color
                })
                current_phase = "activity"
                sim_elapsed_min = 0

    # Renderizar la agenda en pantalla usando HTML para un diseño atractivo
    for item in agenda:
        st.markdown(f"""
        <div style='background-color: {item['bg']}; border-left: 5px solid {item['border']}; padding: 12px; margin-bottom: 10px; border-radius: 6px;'>
            <div style='font-size: 1.1em; color: #1F2937; margin-bottom: 4px;'>
                <b>{item['hora']}</b> | {item['icono']} <b>{item['evento']}</b>
            </div>
            <div style='font-size: 0.9em; line-height: 1.4;'>
                <span style='color: #4B5563;'><b>👩 Mamá:</b> {item['mama']}</span><br>
                <span style='color: #4B5563;'><b>👨 Papá:</b> {item['papa']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS BÁSICAS ---
    st.markdown("---")
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    tomas_hoy = len([l for l in logs_hoy if l['type'] == "feeding"])
    
    st.metric("Tomas registradas hoy", f"{tomas_hoy} / 8+", help="Las tomas son a demanda. El 8 es un mínimo orientativo para asegurar hidratación.")

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
            
            texto = f"**{hora}** | {icono} {l['type'].replace('diaper_', 'Pañal ')}"
            if l.get('durMin'): texto += f" *(Duración: {l['durMin']} min)*"
            if l.get('color'): texto += f" - Alerta color: {l['color'].split(' ')[0]}"
                
            st.markdown(f"- {texto}")
            
    st.markdown("---")
    if st.button("🗑️ Borrar todos los datos", type="primary"):
        st.session_state.clear()
        st.rerun()

def render_diaper():
    st.subheader("🧷 Pañal")
    tipo = st.radio("Contenido:", ["Pipí 💧", "Caca 💩", "Pipí + Caca 💧💩"])
    
    color = None
    if "Caca" in tipo:
        color = st.selectbox("Color de la caca (Importante para la salud)", 
                             ["Mostaza 🟡 (Normal)", "Verde 💚 (Normal/Transición)", "Meconio ⬛ (Normal primeros días)", 
                              "Blanca/Gris ⬜ (⚠️ Alerta pediátrica)", "Roja/Sangre 🔴 (⚠️ Alerta pediátrica)"])
    
    c1, c2 = st.columns(2)
    if c1.button("Guardar", type="primary"):
        log_type = "diaper_wet" if "Solo pipí" in tipo else "diaper_dirty" if "Caca 💩" in tipo else "diaper_both"
        add_log(log_type, color=color)
        
        if color and ("Blanca" in color or "Roja" in color):
            st.error("⚠️ Los colores blanco/gris o rojo en las heces requieren valoración pediátrica. Contacta con tu médico.")
        else:
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
