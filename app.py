import streamlit as st
import datetime
from datetime import timedelta
import json
import os
import copy

st.set_page_config(page_title="BebéGuía", page_icon="🌙", layout="centered")

DB_FILE = 'bebe_db.json'

# ─── PERSISTENCIA ────────────────────────────────────────────
def load_data():
    if not os.path.exists(DB_FILE):
        return None
    try:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
        if data.get('baby', {}).get('birth'):
            data['baby']['birth'] = datetime.datetime.strptime(
                data['baby']['birth'], "%Y-%m-%d").date()
        for log in data.get('logs', []):
            log['ts'] = datetime.datetime.fromisoformat(log['ts'])
        if data.get('phaseStart'):
            data['phaseStart'] = datetime.datetime.fromisoformat(data['phaseStart'])
        return data
    except Exception:
        return None

def save_data():
    data = {
        'baby': st.session_state.baby,
        'logs': st.session_state.logs,
        'phase': st.session_state.phase,
        'phaseStart': st.session_state.phaseStart,
    }
    s = copy.deepcopy(data)
    if s['baby'] and s['baby'].get('birth'):
        s['baby']['birth'] = s['baby']['birth'].strftime("%Y-%m-%d")
    for log in s['logs']:
        log['ts'] = log['ts'].isoformat()
    if s['phaseStart']:
        s['phaseStart'] = s['phaseStart'].isoformat()
    with open(DB_FILE, 'w') as f:
        json.dump(s, f)

# ─── INICIALIZACIÓN ───────────────────────────────────────────
if 'initialized' not in st.session_state:
    db = load_data()
    if db:
        st.session_state.baby      = db.get('baby')
        st.session_state.logs      = db.get('logs', [])
        st.session_state.phase     = db.get('phase', 'idle')
        st.session_state.phaseStart= db.get('phaseStart')
        st.session_state.page      = "main"
    else:
        st.session_state.baby      = None
        st.session_state.logs      = []
        st.session_state.phase     = "idle"
        st.session_state.phaseStart= None
        st.session_state.page      = "setup"
    st.session_state.initialized = True

# ─── HELPERS ──────────────────────────────────────────────────
def age_days():
    b = st.session_state.baby
    if not b or not b.get('birth'):
        return 0
    return (datetime.date.today() - b['birth']).days

def get_aw_max(days):
    w = days // 7
    if w < 4:  return 75
    if w < 8:  return 90
    if w < 12: return 105
    if w < 16: return 120
    return 150

def elapsed_min():
    if not st.session_state.phaseStart:
        return 0
    return int((datetime.datetime.now() - st.session_state.phaseStart
                ).total_seconds() / 60)

def add_log(log_type, dur_min=0, color=None):
    log = {"type": log_type, "ts": datetime.datetime.now(),
           "durMin": dur_min, "color": color}
    st.session_state.logs.append(log)
    save_data()

def change_phase(new_phase):
    now = datetime.datetime.now()
    dur = elapsed_min()
    # Guard: evita duplicados en recargas rápidas
    if st.session_state.phaseStart and st.session_state.phase != "idle" and dur > 1:
        add_log(st.session_state.phase, dur)
    st.session_state.phase      = new_phase
    st.session_state.phaseStart = now
    save_data()

# ─── DIAPER MAP (FIX BUG 2) ───────────────────────────────────
DIAPER_TYPE_MAP = {
    "Pipí 💧":           "diaper_wet",
    "Caca 💩":           "diaper_dirty",
    "Pipí + Caca 💧💩":  "diaper_both",
    "Seco 🏜️":           "diaper_dry",
}
DIAPER_ICONS = {
    "diaper_wet": "💧", "diaper_dirty": "💩",
    "diaper_both": "💧💩", "diaper_dry": "🏜️",
}
PHASE_ICONS = {"feeding": "🍼", "sleeping": "😴", "activity": "🎯", "idle": "☀️"}

# ─── AGENDA PREDICTIVA (FIX BUG 1 + loop infinito) ───────────
def build_agenda(baby, now, current_phase, sim_elapsed):
    days = age_days()
    aw_max = get_aw_max(days)
    feed_type = baby.get('feed', 'Mixta')
    cursor = now
    limit  = now + timedelta(hours=12)
    agenda = []
    MAX_ITER = 30  # salvaguarda anti-bucle infinito

    for _ in range(MAX_ITER):
        if cursor >= limit or len(agenda) >= 10:
            break

        if current_phase in ("idle", "activity"):
            wait = max(1, aw_max - sim_elapsed)  # mínimo 1 min para avanzar
            cursor += timedelta(minutes=wait)
            # FIX BUG 1: evaluar turno DESPUÉS de avanzar cursor
            is_papas = cursor.hour >= 21 or cursor.hour < 3
            if is_papas:
                mama, papa = "💤 DURMIENDO", "💪 Duerme al bebé"
                bg, brd = "#EDE9FE", "#8B5CF6"
            else:
                mama, papa = "Libre / Ducha", "Vigila o tareas"
                bg, brd = "#ECFDF5", "#10B981"
            agenda.append(dict(hora=cursor.strftime("%H:%M"), icono="😴",
                               evento="Se duerme", mama=mama, papa=papa,
                               bg=bg, border=brd))
            current_phase = "sleeping"
            sim_elapsed = 0

        elif current_phase == "sleeping":
            is_night = cursor.hour >= 20 or cursor.hour < 7
            dur = 180 if is_night else 60
            wait = max(1, dur - sim_elapsed)
            cursor += timedelta(minutes=wait)
            is_papas = cursor.hour >= 21 or cursor.hour < 3
            if is_papas:
                if "Fórmula" in feed_type or "Mixta" in feed_type:
                    mama, papa = "💤 DURMIENDO (del tirón)", "🍼 Da biberón completo"
                else:
                    mama, papa = "🤱 Da pecho en cama", "🧷 Cambia pañal y saca gases"
                bg, brd = "#EFF6FF", "#3B82F6"
            else:
                mama, papa = "🤱 Alimenta al bebé", "Acompaña"
                bg, brd = "#F9FAFB", "#D1D5DB"
            agenda.append(dict(hora=cursor.strftime("%H:%M"), icono="🍼",
                               evento="Pide toma", mama=mama, papa=papa,
                               bg=bg, border=brd))
            current_phase = "feeding"
            sim_elapsed = 0

        elif current_phase == "feeding":
            wait = max(1, 30 - sim_elapsed)
            cursor += timedelta(minutes=wait)
            is_night = cursor.hour >= 20 or cursor.hour < 7
            if is_night:
                current_phase = "sleeping"
                sim_elapsed = 0
            else:
                agenda.append(dict(hora=cursor.strftime("%H:%M"), icono="🎯",
                                   evento="Termina toma", mama="Juego suave",
                                   papa="Juego suave", bg="#F9FAFB", border="#D1D5DB"))
                current_phase = "activity"
                sim_elapsed = 0

    return agenda

def render_agenda(agenda):
    for item in agenda:
        st.markdown(f"""
        <div style='background:{item["bg"]};border-left:5px solid {item["border"]};
                    padding:12px;margin-bottom:10px;border-radius:6px;'>
            <div style='font-size:1.1em;color:#1F2937;margin-bottom:4px;'>
                <b>{item["hora"]}</b> | {item["icono"]} <b>{item["evento"]}</b>
            </div>
            <div style='font-size:.9em;line-height:1.5;color:#4B5563;'>
                <b>👩 Mamá:</b> {item["mama"]}<br>
                <b>👨 Papá:</b> {item["papa"]}
            </div>
        </div>""", unsafe_allow_html=True)

# ─── VISTAS ───────────────────────────────────────────────────
def render_setup():
    st.markdown("<h1 style='text-align:center;color:#4B5563;'>🌙 BebéGuía</h1>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#9CA3AF;'>Tu guía en equipo.</p>",
                unsafe_allow_html=True)
    with st.form("setup_form"):
        name  = st.text_input("Nombre del bebé")
        birth = st.date_input("Fecha de nacimiento", max_value=datetime.date.today())
        feed  = st.selectbox("Alimentación", [
            "Lactancia materna exclusiva",
            "Mixta (pecho + biberón)",
            "Fórmula / Biberón",
        ])
        if st.form_submit_button("Empezar →", use_container_width=True) and name:
            st.session_state.baby = {"name": name, "birth": birth, "feed": feed}
            st.session_state.page = "main"
            change_phase("idle")
            st.rerun()

def render_settings():
    st.subheader("⚙️ Configuración")
    baby = st.session_state.baby
    feed_opts = ["Lactancia materna exclusiva", "Mixta (pecho + biberón)", "Fórmula / Biberón"]
    with st.form("settings_form"):
        new_name = st.text_input("Nombre", value=baby['name'])
        idx = feed_opts.index(baby['feed']) if baby['feed'] in feed_opts else 0
        new_feed = st.selectbox("Alimentación", feed_opts, index=idx)
        if st.form_submit_button("Guardar", use_container_width=True):
            st.session_state.baby.update(name=new_name, feed=new_feed)
            save_data()
            st.success("¡Guardado!")
            st.session_state.page = "main"
            st.rerun()
    if st.button("← Volver"):
        st.session_state.page = "main"; st.rerun()
    # Zona peligrosa al fondo
    st.markdown("---")
    with st.expander("⚠️ Zona peligrosa"):
        if st.button("🗑️ Borrar todos los datos", type="primary"):
            if os.path.exists(DB_FILE):
                os.remove(DB_FILE)
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

def render_main():
    baby = st.session_state.baby
    days = age_days()
    aw_max = get_aw_max(days)
    now = datetime.datetime.now()
    el = elapsed_min()

    # Cabecera
    c1, c2, c3 = st.columns([3, 1, 1])
    with c1:
        st.subheader(f"👶 {baby['name']}")
        weeks = days // 7
        st.caption(f"{days} días ({weeks} sem) · {baby['feed']}")
    with c2:
        if st.button("📋"): st.session_state.page = "history"; st.rerun()
    with c3:
        if st.button("⚙️"): st.session_state.page = "settings"; st.rerun()

    st.markdown("---")

    # Estado actual
    phase = st.session_state.phase
    if phase == "idle":
        st.info("☀️ **Despierto y tranquilo** — Si busca, ofrécele pecho o biberón.")

    elif phase == "feeding":
        st.success(f"🍼 **Comiendo** — hace {el} min\n\n"
                   "Si se duerme comiendo antes de los 4 meses: es normal, pásalo a dormir.")

    elif phase == "sleeping":
        st.markdown(
            f"<div style='background:#F3E8FF;padding:15px;border-radius:10px;margin-bottom:15px;'>"
            f"😴 <b>Durmiendo</b> — hace {el} min<br><br>"
            f"<i>SUEÑO SEGURO:</i> Boca arriba · superficie firme · sin mantas sueltas.</div>",
            unsafe_allow_html=True)
        is_day = 7 <= now.hour < 20
        if days < 30 and el >= 210:
            st.error("🚨 Lleva casi 4h sin comer. Despiértalo suavemente.")
        elif days >= 30 and is_day and el >= 120:
            st.warning("⚠️ Siesta larga (2h). Plantéate despertarle para proteger el sueño nocturno.")

    elif phase == "activity":
        pct = min(int(el / aw_max * 100), 100)
        color = "green" if pct < 60 else ("orange" if pct < 85 else "red")
        st.info(f"🎯 **Tiempo de juego** — hace {el} min  (ventana: {aw_max} min)")
        st.markdown(
            f"<div style='background:#E5E7EB;border-radius:8px;height:10px;'>"
            f"<div style='background:{color};width:{pct}%;height:10px;border-radius:8px;'></div></div>",
            unsafe_allow_html=True)
        if el >= aw_max:
            st.error(f"🚨 Ventana de sueño cerrada ({el} min). Acuéstalo ya.")
        elif el >= int(aw_max * 0.8):
            st.warning(f"⏰ Quedan ~{aw_max - el} min. Empieza a calmarlo.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Botones de acción
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🍼 Comer",  use_container_width=True): change_phase("feeding");  st.rerun()
    if c2.button("😴 Dormir", use_container_width=True): change_phase("sleeping"); st.rerun()
    if c3.button("🎯 Jugar",  use_container_width=True): change_phase("activity"); st.rerun()
    if c4.button("🧷 Pañal",  use_container_width=True): st.session_state.page = "diaper"; st.rerun()

    # Métricas rápidas de hoy
    st.markdown("---")
    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    tomas = sum(1 for l in logs_hoy if l['type'] == "feeding")
    wet   = sum(1 for l in logs_hoy if l['type'] in ("diaper_wet", "diaper_both"))
    col1, col2, col3 = st.columns(3)
    col1.metric("Tomas hoy", f"{tomas}", help="Mínimo orientativo: 8/día")
    col2.metric("Pañales mojados", f"{wet}", help="Mínimo: 6/día → buena hidratación")
    col3.metric("Tiempo despierto", f"{el} min", help=f"Ventana máx: {aw_max} min")

    # Agenda
    st.markdown("---")
    st.subheader("📅 Planificador Familiar (12h)")
    agenda = build_agenda(baby, now, phase, el)
    render_agenda(agenda)

def render_history():
    st.subheader("📋 Historial de hoy")
    if st.button("← Volver"): st.session_state.page = "main"; st.rerun()

    hoy = datetime.date.today()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]

    if not logs_hoy:
        st.info("Sin registros hoy.")
        return

    for l in reversed(logs_hoy):
        hora  = l['ts'].strftime("%H:%M")
        icono = DIAPER_ICONS.get(l['type'], PHASE_ICONS.get(l['type'], "📝"))
        # FIX BUG 3: sin f-strings anidados con las mismas comillas
        dur_txt = f" ({l['durMin']} min)" if l.get('durMin') else ""
        col_txt = f" — color: {l['color']}" if l.get('color') else ""
        st.markdown(f"- **{hora}** | {icono} `{l['type']}`{dur_txt}{col_txt}")

    # Exportar CSV
    st.markdown("---")
    lines = ["hora,tipo,duracion_min,color"]
    for l in logs_hoy:
        lines.append(f"{l['ts'].strftime('%H:%M')},{l['type']},"
                     f"{l.get('durMin','')},{l.get('color','')}")
    st.download_button("⬇️ Exportar CSV", "\n".join(lines),
                       file_name=f"bebe_{hoy}.csv", mime="text/csv")

def render_diaper():
    st.subheader("🧷 ¿Qué hay en el pañal?")
    # FIX BUG 2: usamos el mapa explícito
    tipo_label = st.radio("Contenido:", list(DIAPER_TYPE_MAP.keys()))

    color = None
    if "Caca" in tipo_label:
        color = st.selectbox("Color de la caca", [
            "Mostaza 🟡 (Normal)",
            "Verde 💚 (Normal/Transición)",
            "Meconio ⬛ (Normal primeros días)",
            "Blanca/Gris ⬜ (⚠️ Alerta pediátrica)",
            "Roja/Sangre 🔴 (⚠️ Alerta pediátrica)",
        ])

    c1, c2 = st.columns(2)
    if c1.button("Guardar", type="primary"):
        log_type = DIAPER_TYPE_MAP[tipo_label]
        add_log(log_type, color=color)
        if color and ("Blanca" in color or "Roja" in color):
            st.error("⚠️ Este color requiere valoración pediátrica. Contacta con tu médico.")
        else:
            st.session_state.page = "main"; st.rerun()
    if c2.button("Cancelar"):
        st.session_state.page = "main"; st.rerun()

# ─── ROUTER ───────────────────────────────────────────────────
pages = {
    "setup":    render_setup,
    "settings": render_settings,
    "main":     render_main,
    "diaper":   render_diaper,
    "history":  render_history,
}
pages.get(st.session_state.page, render_setup)()
