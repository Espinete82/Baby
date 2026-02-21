import streamlit as st
import datetime
from datetime import timedelta
import json
import os
import copy

# --- CONFIGURACIÓN DE LA APP ---
st.set_page_config(page_title="BebéGuía - Equipo de Crianza", page_icon="🌙", layout="centered")

DB_FILE = 'bebe_db.json'

# --- FUNCIONES DE BASE DE DATOS (Guardado Permanente) ---
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            try:
                data = json.load(f)
                if data.get('baby') and data['baby'].get('birth'):
                    data['baby']['birth'] = datetime.datetime.strptime(data['baby']['birth'], "%Y-%m-%d").date()
                for log in data.get('logs', []):
                    log['ts'] = datetime.datetime.fromisoformat(log['ts'])
                if data.get('phaseStart'):
                    data['phaseStart'] = datetime.datetime.fromisoformat(data['phaseStart'])
                return data
            except:
                return None
    return None

def save_data():
    data = {
        'baby': st.session_state.baby,
        'logs': st.session_state.logs,
        'phase': st.session_state.phase,
        'phaseStart': st.session_state.phaseStart
    }
    serializable = copy.deepcopy(data)
    if serializable['baby'] and serializable['baby'].get('birth'):
        serializable['baby']['birth'] = serializable['baby']['birth'].strftime("%Y-%m-%d")
    for log in serializable['logs']:
        log['ts'] = log['ts'].isoformat()
    if serializable['phaseStart']:
        serializable['phaseStart'] = serializable['phaseStart'].isoformat()
    
    with open(DB_FILE, 'w') as f:
        json.dump(serializable, f)

# --- INICIALIZACIÓN DEL ESTADO ---
if 'initialized' not in st.session_state:
    db_data = load_data()
    if db_data:
        st.session_state.baby = db_data.get('baby')
        st.session_state.logs = db_data.get('logs', [])
        st.session_state.phase = db_data.get('phase', 'idle')
        st.session_state.phaseStart = db_data.get('phaseStart')
        st.session_state.page = "main"
    else:
        st.session_state.baby = None
        st.session_state.logs = []
        st.session_state.phase = "idle"
        st.session_state.phaseStart = None
        st.session_state.page = "setup"
    st.session_state.initialized = True

# --- FUNCIONES AUXILIARES ---
def get_age_days(birth_date):
    if not birth_date: return 0
    # Permite calcular días incluso si aún no ha nacido (días negativos o cero)
    days = (datetime.date.today() - birth_date).days
    return days if days > 0 else 0

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
    save_data()

def change_phase(new_phase):
    now = datetime.datetime.now()
    if st.session_state.phaseStart and st.session_state.phase != "idle":
        elapsed = (now - st.session_state.phaseStart).total_seconds() / 60
        if elapsed > 1: 
            add_log(st.session_state.phase, int(elapsed))
    
    st.session_state.phase = new_phase
    st.session_state.phaseStart = now
    save_data()

# --- VISTAS ---

def render_setup():
    st.markdown("<h1 style='text-align: center; color: #4B5563;'>🌙 BebéGuía</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF;'>Tu guía en equipo, basada en biología y lactancia real.</p>", unsafe_allow_html=True)
    
    with st.form("setup_form"):
        name = st.text_input("Nombre del bebé")
        birth = st.date_input("Fecha de nacimiento (o fecha probable de parto)")
        feed = st.selectbox("Alimentación esperada/actual", ["Lactancia materna exclusiva", "Mixta (pecho + biberón)", "Fórmula / Biberón"])
        
        submitted = st.form_submit_button("Empezar →", use_container_width=True)
        if submitted and name:
            st.session_state.baby = {"name": name, "birth": birth, "feed": feed}
            st.session_state.page = "main"
            change_phase("idle")
            st.rerun()

def render_settings():
    st.subheader("⚙️ Configuración")
    
    with st.form("settings_form"):
        new_name = st.text_input("Nombre", value=st.session_state.baby['name'])
        
        feed_options = ["Lactancia materna exclusiva", "Mixta (pecho + biberón)", "Fórmula / Biberón"]
        current_feed_index = feed_options.index(st.session_state.baby['feed']) if st.session_state.baby['feed'] in feed_options else 0
        new_feed = st.selectbox("Cambiar método de alimentación", feed_options, index=current_feed_index)
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("Guardar Cambios", use_container_width=True):
            st.session_state.baby['name'] = new_name
            st.session_state.baby['feed'] = new_feed
            save_data()
            st.success("¡Guardado!")
            st.session_state.page = "main"
            st.rerun()
            
    if st.button("← Volver", use_container_width=True):
        st.session_state.page = "main"
        st.rerun()

def render_main():
    baby = st.session_state.baby
    days = get_age_days(baby['birth'])
    aw_max = get_aw_max(days)
    es_fase_1 = days < 120 
    
    # Cabecera con Botones
    col1, col2, col3 = st.columns([3, 1, 1])
    with col1:
        st.subheader(f"👶 {baby['name']}")
        st.caption(f"Edad: {days} días | {baby['feed']}")
    with col2:
        if st.button("📋", help="Ver Historial"): st.session_state.page = "history"; st.rerun()
    with col3:
        if st.button("⚙️", help="Ajustes"): st.session_state.page = "settings"; st.rerun()

    # Cálculo de tiempo transcurrido
    elapsed_min = 0
    now = datetime.datetime.now()
    if st.session_state.phaseStart:
        elapsed_min = int((now - st.session_state.phaseStart).total_seconds() / 60)

    # --- MENSAJES DINÁMICOS BASADOS EN LA EDAD ---
    st.markdown("---")
    if st.session_state.phase == "idle":
        st.info("☀️ **Despierto y tranquilo**\n\nLa alimentación es a demanda, si busca (abre la boca, se lleva manos a la cara), ofrécele.")
    
    elif st.session_state.phase == "feeding":
        st.success(f"🍼 **Comiendo** (hace {elapsed_min} min)\n\n"
                   f"Si se duerme comiendo, ¡perfecto! Pasa a la fase de sueño directamente.")
    
    elif st.session_state.phase == "sleeping":
        is_newborn = days < 30
        is_daytime = 7 <= now.hour < 20
        
        st.markdown(f"<div style='background-color:#F3E8FF; padding:15px; border-radius:10px; margin-bottom:15px;'>"
                    f"😴 <b>Durmiendo</b> (hace {elapsed_min} min)<br><br>"
                    f"<i>SUEÑO SEGURO:</i> Boca arriba, superficie firme, sin mantas sueltas.</div>", unsafe_allow_html=True)
        
        if is_newborn and elapsed_min >= 210: 
            st.error("🚨 **Alerta:** Lleva casi 4h sin comer. Despiértalo suavemente para evitar bajadas de azúcar.")
        elif not is_newborn and is_daytime and elapsed_min >= 120: 
            st.warning("⚠️ **Siesta larga:** Lleva 2 horas. Plantéate despertarle para proteger el sueño nocturno.")
    
    elif st.session_state.phase == "activity":
        st.info(f"🎯 **Tiempo de juego** (hace {elapsed_min} min)\n\n"
                f"Observa señales de cansancio (bostezos, mirada perdida) para acostarlo antes de que llore.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- BOTONES DE ACCIÓN RÁPIDA ---
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🍼 Comer", use_container_width=True): change_phase("feeding"); st.rerun()
    if c2.button("😴 Dormir", use_container_width=True): change_phase("sleeping"); st.rerun()
    if c3.button("🎯 Jugar", use_container_width=True): change_phase("activity"); st.rerun()
    if c4.button("🧷 Pañal", use_container_width=True): st.session_state.page = "diaper"; st.rerun()

    # --- AGENDA PREDICTIVA ---
    st.markdown("---")
    st.subheader("📅 Planificador Familiar en Equipo")
    st.caption("Previsión para las próximas 12 horas.")
    
    cursor_time = now
    limit_time = now + timedelta(hours=12)
    current_phase = st.session_state.phase
    sim_elapsed_min = elapsed_min
    feed_type = baby.get('feed', 'Mixta')
    
    agenda = []
    
    while cursor_time < limit_time and len(agenda) < 10:
        is_night = cursor_time.hour >= 20 or cursor_time.hour < 7
        is_papas_shift = cursor_time.hour >= 21 or cursor_time.hour < 3

        if current_phase in ["idle", "activity"]:
            min_to_sleep = max(0, aw_max - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_sleep)
            
            if is_papas_shift:
                mama_role, papa_role = "💤 DURMIENDO (Descanso vital)", "💪 Duerme al bebé en brazos/cuna"
                bg_color, border_color = "#EDE9FE", "#8B5CF6"
            else:
                mama_role, papa_role = "Libre / Ducha / Descanso", "Vigila o hace tareas"
                bg_color, border_color = "#ECFDF5", "#10B981"

            agenda.append({"hora": cursor_time.strftime("%H:%M"), "icono": "😴", "evento": "Se duerme", "mama": mama_role, "papa": papa_role, "bg": bg_color, "border": border_color})
            current_phase = "sleeping"
            sim_elapsed_min = 0
            
        elif current_phase == "sleeping":
            sleep_duration = 180 if is_night else 60
            min_to_wake = max(0, sleep_duration - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_wake)
            
            if is_papas_shift:
                if "Fórmula" in feed_type or "Mixta" in feed_type:
                    mama_role, papa_role = "💤 DURMIENDO (Del tirón)", "🍼 Prepara y da biberón"
                else:
                    # LÓGICA CORREGIDA PARA LME
                    if days < 40: # Primeros 40 días: establecimiento de lactancia
                        mama_role, papa_role = "🤱 Da pecho en cama (semi-dormida)", "🧷 Trae al bebé, cambia pañal y saca gases"
                    else: # A partir de los 40 días (si hay banco de leche)
                        mama_role, papa_role = "💤 DURMIENDO (Del tirón)", "🍼 Da leche materna extraída"
                        
                bg_color, border_color = "#EFF6FF", "#3B82F6"
            else:
                mama_role, papa_role = "🤱 Alimenta al bebé", "Acompaña / Prepara comida"
                bg_color, border_color = "#F9FAFB", "#D1D5DB"

            agenda.append({"hora": cursor_time.strftime("%H:%M"), "icono": "🍼", "evento": "Pide toma", "mama": mama_role, "papa": papa_role, "bg": bg_color, "border": border_color})
            current_phase = "feeding"
            sim_elapsed_min = 0
            
        elif current_phase == "feeding":
            min_to_play = max(0, 30 - sim_elapsed_min)
            cursor_time = cursor_time + timedelta(minutes=min_to_play)
            
            if is_night:
                current_phase = "sleeping"
                sim_elapsed_min = 0
                continue 
            else:
                agenda.append({"hora": cursor_time.strftime("%H:%M"), "icono": "🎯", "evento": "Termina toma", "mama": "Juego suave / Contacto", "papa": "Juego suave / Contacto", "bg": "#F9FAFB", "border": "#D1D5DB"})
                current_phase = "activity"
                sim_elapsed_min = 0

    for item in agenda:
        st.markdown(f"""
        <div style='background-color: {item['bg']}; border-left: 5px solid {item['border']}; padding: 12px; margin-bottom: 10px; border-radius: 6px;'>
            <div style='font-size: 1.1em; color: #1F2937; margin-bottom: 4px;'><b>{item['hora']}</b> | {item['icono']} <b>{item['evento']}</b></div>
            <div style='font-size: 0.9em; line-height: 1.4;'><span style='color: #4B5563;'><b>👩 Mamá:</b> {item['mama']}</span><br><span style='color: #4B5563;'><b>👨 Papá:</b> {item['papa']}</span></div>
        </div>
        """, unsafe_allow_html=True)

    # --- MÉTRICAS BÁSICAS ---
    st.markdown("---")
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    tomas_hoy = len([l for l in logs_hoy if l['type'] == "feeding"])
    
    st.metric("Tomas registradas hoy", f"{tomas_hoy} / 8+", help="Las tomas son a demanda. El 8 es un mínimo orientativo para el primer mes para asegurar hidratación y recuperación de peso.")

def render_history():
    st.subheader("📋 Historial")
    if st.button("← Volver"): st.session_state.page = "main"; st.rerun()
    
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    
    if not logs_hoy:
        st.write("Sin registros hoy.")
    else:
        for l in reversed(logs_hoy):
            hora = l['ts'].strftime("%H:%M")
            icono = {"feeding": "🍼", "sleeping": "😴", "activity": "🎯"}.get(l['type'], "🧷")
            st.markdown(f"- **{hora}** | {icono} {l['type'].replace('diaper_', 'Pañal ')} {f'({l.get("durMin",0)} min)' if l.get('durMin') else ''}")
            
    st.markdown("---")
    if st.button("🗑️ Borrar todos los datos", type="primary"):
        if os.path.exists(DB_FILE): os.remove(DB_FILE)
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

def render_diaper():
    st.subheader("🧷 Pañal")
    tipo = st.radio("Contenido:", ["Pipí 💧", "Caca 💩", "Pipí + Caca 💧💩"])
    
    color = None
    if "Caca" in tipo:
        color = st.selectbox("Color de la caca (Importante para la salud)", 
                             ["Mostaza 🟡 (Normal)", "Verde 💚 (Normal/Transición)", "Meconio ⬛ (Normal primeros 3-4 días)", 
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
elif st.session_state.page == "settings": render_settings()
elif st.session_state.page == "main": render_main()
elif st.session_state.page == "diaper": render_diaper()
elif st.session_state.page == "history": render_history()
