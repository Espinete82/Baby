import streamlit as st
import datetime
from datetime import timedelta
import json
import os
import copy

st.set_page_config(page_title="BebéGuía", page_icon="🌙", layout="centered")

DB_FILE = 'bebe_db.json'

# ─── TIMEZONE ─────────────────────────────────────────────────
def now_local():
    offset = st.session_state.get('utc_offset', 1)
    return datetime.datetime.utcnow() + timedelta(hours=offset)

# ─── PERSISTENCIA ─────────────────────────────────────────────
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
    s = {
        'baby':       copy.deepcopy(st.session_state.baby),
        'logs':       copy.deepcopy(st.session_state.logs),
        'phase':      st.session_state.phase,
        'phaseStart': st.session_state.phaseStart,
        'utc_offset': st.session_state.get('utc_offset', 1),
        'dw_start':   st.session_state.get('dw_start', 21),
        'dw_end':     st.session_state.get('dw_end', 3),
        'work_hour':  st.session_state.get('work_hour', 7),
        'papa_mode':  st.session_state.get('papa_mode', '💼 Trabajando'),
    }
    if s['baby'] and s['baby'].get('birth'):
        birth = s['baby']['birth']
        if hasattr(birth, 'strftime'):
            s['baby']['birth'] = birth.strftime("%Y-%m-%d")
    for log in s['logs']:
        if hasattr(log['ts'], 'isoformat'):
            log['ts'] = log['ts'].isoformat()
    if s['phaseStart'] and hasattr(s['phaseStart'], 'isoformat'):
        s['phaseStart'] = s['phaseStart'].isoformat()
    with open(DB_FILE, 'w') as f:
        json.dump(s, f)

# ─── INICIALIZACIÓN ───────────────────────────────────────────
if 'initialized' not in st.session_state:
    db = load_data()
    if db:
        st.session_state.baby        = db.get('baby')
        st.session_state.logs        = db.get('logs', [])
        st.session_state.phase       = db.get('phase', 'idle')
        st.session_state.phaseStart  = db.get('phaseStart')
        st.session_state.utc_offset  = db.get('utc_offset', 1)
        st.session_state.dw_start    = db.get('dw_start', 21)
        st.session_state.dw_end      = db.get('dw_end', 3)
        st.session_state.work_hour   = db.get('work_hour', 7)
        st.session_state.papa_mode   = db.get('papa_mode', '💼 Trabajando')
        st.session_state.page        = "main"
    else:
        st.session_state.baby        = None
        st.session_state.logs        = []
        st.session_state.phase       = "idle"
        st.session_state.phaseStart  = None
        st.session_state.utc_offset  = 1
        st.session_state.dw_start    = 21
        st.session_state.dw_end      = 3
        st.session_state.work_hour   = 7
        st.session_state.papa_mode   = '💼 Trabajando'
        st.session_state.page        = "setup"
    st.session_state.initialized = True

# ─── HELPERS ──────────────────────────────────────────────────
def age_days():
    b = st.session_state.baby
    if not b or not b.get('birth'):
        return 0
    return (datetime.date.today() - b['birth']).days

def age_weeks():
    return age_days() // 7

def get_aw_range(days):
    w = days // 7
    if w < 2:  return 45,  75
    if w < 4:  return 50,  80
    if w < 8:  return 60,  90
    if w < 12: return 75, 105
    if w < 16: return 90, 120
    if w < 24: return 105, 150
    return 120, 180

def get_sleep_range(days, is_night):
    w = days // 7
    if is_night:
        if w < 2:  return  90, 150, "1.5–2.5h"
        if w < 4:  return 110, 180, "2–3h"
        if w < 8:  return 135, 210, "2.5–3.5h"
        if w < 12: return 150, 300, "2.5–5h"
        if w < 16: return 180, 360, "3–6h"
        return          240, 420, "4–7h"
    else:
        if w < 2:  return  20,  60, "20–60 min"
        if w < 4:  return  30,  70, "30–70 min"
        if w < 8:  return  30, 120, "30min–2h"
        if w < 12: return  45,  90, "45–90 min"
        if w < 16: return  60,  90, "1–1.5h"
        return           60, 120, "1–2h"

def get_sleep_durations(days, is_night):
    """Devuelve (duración_media_min, label) para la simulación de agenda."""
    lo, hi, lbl = get_sleep_range(days, is_night)
    avg = (lo + hi) // 2
    return avg, lbl

def get_feed_range(days):
    if "materna" in (st.session_state.baby or {}).get('feed', '').lower():
        return 10, 30
    return 10, 25

def get_aw_max(days):
    return get_aw_range(days)[1]

def phase_status(phase, elapsed, days):
    if phase == "activity":
        lo, hi = get_aw_range(days)
        if elapsed < lo:
            return 'ok', '#22C55E', f"✅ Normal — aún dentro del rango ({lo}–{hi} min despierto)"
        if elapsed <= hi:
            return 'warning', '#F59E0B', f"⚠️ Acercándose al límite — {hi - elapsed} min restantes (rango: {lo}–{hi} min)"
        return 'alert', '#EF4444', f"🚨 Ventana cerrada — lleva {elapsed} min (máx. {hi} min)"
    elif phase == "feeding":
        lo, hi = get_feed_range(days)
        if elapsed < lo:
            return 'ok', '#22C55E', f"✅ Toma en curso — normal hasta ~{hi} min"
        if elapsed <= hi:
            return 'ok', '#22C55E', f"✅ Duración normal ({lo}–{hi} min)"
        return 'warning', '#F59E0B', f"⚠️ Toma larga ({elapsed} min) — si está relajado y suelto, ya está satisfecho"
    elif phase == "sleeping":
        h = now_local().hour
        is_night = h >= 20 or h < 7
        lo, hi, _ = get_sleep_range(days, is_night)
        tipo = "nocturno" if is_night else "siesta"
        if elapsed < lo:
            return 'ok', '#8B5CF6', f"😴 Sueño {tipo} normal — mínimo esperado: {lo} min"
        if elapsed <= hi:
            return 'ok', '#8B5CF6', f"😴 Dentro del rango ({lo}–{hi} min) — despertará pronto"
        return 'warning', '#F59E0B', f"⚠️ Sueño largo ({elapsed} min) — máx. esperado {hi} min. Puede estar bien."
    return 'ok', '#6B7280', ""

def elapsed_min():
    if not st.session_state.phaseStart:
        return 0
    return int((now_local() - st.session_state.phaseStart).total_seconds() / 60)

def add_log(log_type, dur_min=0, color=None):
    log = {"type": log_type, "ts": now_local(), "durMin": dur_min, "color": color}
    st.session_state.logs.append(log)
    save_data()

def change_phase(new_phase):
    dur = elapsed_min()
    if st.session_state.phaseStart and st.session_state.phase != "idle" and dur > 1:
        add_log(st.session_state.phase, dur)
    st.session_state.phase      = new_phase
    st.session_state.phaseStart = now_local()
    save_data()

# ─── LACTANCIA POR EDAD → ROL DE PAPÁ ─────────────────────────
def papa_feed_method(days, feed_type):
    weeks = days // 7
    if "materna" in feed_type.lower():
        if weeks < 2:
            return "🪡 Da calostro con jeringa o dedo (no biberón aún)"
        elif weeks < 4:
            return "👆 Alimentación con dedo (finger feeding) si mamá no puede"
        elif weeks < 6:
            return "🍼 Puede ofrecer leche extraída en biberón (flujo lento)"
        else:
            return "🍼 Da biberón con leche materna extraída"
    elif "mixta" in feed_type.lower():
        if weeks < 2:
            return "🪡 Jeringa o dedo con leche materna/fórmula"
        elif weeks < 4:
            return "👆 Finger feeding o biberón con tetina de flujo lento"
        else:
            return "🍼 Prepara y da biberón completo (fórmula o leche extraída)"
    else:
        return "🍼 Prepara y da biberón completo"

# ─── CONFIGURACIÓN MODO PAPÁ ──────────────────────────────────
def get_papa_mode_config():
    mode = st.session_state.get('papa_mode', '💼 Trabajando')
    dw_s = st.session_state.get('dw_start', 21)
    dw_e = st.session_state.get('dw_end', 3)
    wh   = st.session_state.get('work_hour', 7)

    if '💼 Trabajando' in mode:
        return dict(
            mode_label="💼 Trabajando", day_duty=False,
            dw_start=dw_s, dw_end=dw_e, work_hour=wh,
            mama_day="🤱 Gestiona sola — ¡eres increíble!",
            papa_day="💼 En el trabajo", mama_note=None,
        )
    elif '🏠 Teletrabajo' in mode:
        return dict(
            mode_label="🏠 Teletrabajo", day_duty=True,
            day_shift_s=12, day_shift_e=14,
            dw_start=dw_s, dw_end=dw_e, work_hour=wh,
            mama_day="😴 Duerme / descansa (siesta de mediodía)",
            papa_day="🏠 Cuida al bebé entre reuniones (12–14h)",
            mama_note="📅 Papá cubre la siesta de mediodía (12–14h) → aprovecha para dormir.",
        )
    else:  # Vacaciones
        return dict(
            mode_label="🌴 Vacaciones", day_duty=True,
            day_shift_s=8, day_shift_e=14,
            dw_start=dw_s, dw_end=dw_e, work_hour=23,
            mama_day="😴 Duerme / ducha / come / respira",
            papa_day="🌴 Turno completo mañana (08–14h) — mamá descansa",
            mama_note="🌴 Papá lleva el turno de mañana (8–14h). Mamá: duerme sin culpa.",
        )

# ─── AGENDA EASY COMPLETA ─────────────────────────────────────
def build_agenda(baby, now, current_phase, sim_elapsed):
    """
    Genera la agenda EASY de 24h partiendo del estado actual del bebé.
    Cada ciclo: Eat · Activity · Sleep · You-time.
    """
    days      = age_days()
    aw_max    = get_aw_max(days)
    feed_type = baby.get('feed', 'Mixta')
    is_fase1  = days < 120

    cursor    = now
    limit     = now + timedelta(hours=24)
    agenda    = []
    MAX_ITER  = 80

    total_tomas    = 0
    mama_sleep_min = 0
    mama_free_min  = 0

    papa_was_on_duty = False
    papa_shift_start = None
    papa_shifts      = []

    dw_s = st.session_state.get('dw_start', 21)
    dw_e = st.session_state.get('dw_end', 3)

    def is_papas_shift(h):
        return h >= dw_s or h < dw_e

    for _ in range(MAX_ITER):
        if cursor >= limit or len(agenda) >= 30:
            break

        h        = cursor.hour
        is_night = h >= 20 or h < 7

        # ── ACTIVITY ─────────────────────────────────────────
        if current_phase == "activity":
            if is_night:
                current_phase = "sleeping"
                sim_elapsed   = 0
                continue

            act_dur = max(5, aw_max - 15)
            wait    = max(1, act_dur - sim_elapsed)
            cursor += timedelta(minutes=wait)
            h       = cursor.hour
            on_duty = is_papas_shift(h)
            act_desc = ("Piel con piel, canto, móvil contrastes"
                        if is_fase1 else "Tummy time, espejo, suelo")

            if on_duty:
                mama_sleep_min += act_dur
                mama_ev = "💤 Prepárate para dormir"
                papa_ev = f"🎯 {act_desc} · Vigila señales de sueño"
                bg, brd = "#EDE9FE", "#8B5CF6"
            else:
                mama_free_min += act_dur
                mama_ev = f"🎯 {act_desc}"
                papa_ev = f"🎯 {act_desc} · Señales: bostezos, mirada perdida"
                bg, brd = "#FFF7ED", "#F97316"

            if on_duty and not papa_was_on_duty:
                papa_shift_start = cursor - timedelta(minutes=act_dur)
                papa_was_on_duty = True
            elif not on_duty and papa_was_on_duty:
                papa_shifts.append((papa_shift_start, cursor))
                papa_was_on_duty = False

            agenda.append(dict(
                hora=cursor.strftime("%H:%M"), icono="🎯",
                evento=f"Fin actividad → a dormir ({act_dur} min)",
                mama=mama_ev, papa=papa_ev, bg=bg, border=brd
            ))
            current_phase = "sleeping"
            sim_elapsed   = 0

        # ── EAT ──────────────────────────────────────────────
        elif current_phase == "feeding":
            feed_dur = 25 if "materna" in feed_type.lower() else 20
            wait     = max(1, feed_dur - sim_elapsed)
            cursor  += timedelta(minutes=wait)
            h        = cursor.hour
            on_duty  = is_papas_shift(h)
            total_tomas += 1

            if on_duty:
                papa_role = papa_feed_method(days, feed_type)
                mama_role = "💤 DURMIENDO"
                bg, brd   = "#EFF6FF", "#3B82F6"
                mama_sleep_min += feed_dur
            else:
                papa_role = (papa_feed_method(days, feed_type)
                             if "materna" not in feed_type.lower()
                             else "🤝 Acompaña, saca gases")
                mama_role = "🤱 Da el pecho / biberón"
                bg, brd   = "#F0FDF4", "#22C55E"
                mama_free_min += feed_dur

            if on_duty and not papa_was_on_duty:
                papa_shift_start = cursor - timedelta(minutes=feed_dur)
                papa_was_on_duty = True
            elif not on_duty and papa_was_on_duty:
                papa_shifts.append((papa_shift_start, cursor))
                papa_was_on_duty = False

            agenda.append(dict(
                hora=cursor.strftime("%H:%M"), icono="🍼",
                evento=f"Toma #{total_tomas} terminada",
                mama=mama_role, papa=papa_role, bg=bg, border=brd
            ))
            current_phase = "sleeping" if is_night else "activity"
            sim_elapsed   = 0

        # ── SLEEP / IDLE ──────────────────────────────────────
        elif current_phase in ("sleeping", "idle"):
            sleep_dur, sleep_lbl = get_sleep_durations(days, is_night)

            wait          = max(1, sleep_dur - sim_elapsed)
            sleep_start   = cursor
            cursor       += timedelta(minutes=wait)
            wake_time_str = cursor.strftime("%H:%M")
            h             = cursor.hour
            on_duty       = is_papas_shift(h) or is_papas_shift(sleep_start.hour)

            papa_hint = (papa_feed_method(days, feed_type)
                         if "materna" not in feed_type.lower()
                         else "jeringa/dedo/biberón según semanas")

            if on_duty:
                mama_sleep_min += sleep_dur
                mama_role = "💤 DURMIENDO — bloque largo"
                papa_role = (f"😴 DUERME AHORA — ⏰ pon alarma a las {wake_time_str} "
                             f"| Al sonar: {papa_hint}")
                bg, brd   = "#EDE9FE", "#8B5CF6"
            else:
                mama_free_min += sleep_dur
                mama_role = "🛁 Ducha · Comida · Descanso (tú primero)"
                papa_role = "😴 Descansa / duerme mientras puedas"
                bg, brd   = "#ECFDF5", "#10B981"

            if on_duty and not papa_was_on_duty:
                papa_shift_start = sleep_start
                papa_was_on_duty = True
            elif not on_duty and papa_was_on_duty:
                papa_shifts.append((papa_shift_start, sleep_start))
                papa_was_on_duty = False

            agenda.append(dict(
                hora=sleep_start.strftime("%H:%M"), icono="🌙",
                evento=f"Bebé se duerme — despertará ~{wake_time_str} ({sleep_lbl})",
                mama=mama_role, papa=papa_role, bg=bg, border=brd
            ))
            current_phase = "feeding"
            sim_elapsed   = 0

    # Cerrar turno abierto si el horizonte lo corta
    if papa_was_on_duty and papa_shift_start:
        papa_shifts.append((papa_shift_start, cursor))

    papa_block_min = 0
    if papa_shifts:
        last_end = papa_shifts[-1][1]
        next_wake = next(
            (datetime.datetime.strptime(
                last_end.strftime("%Y-%m-%d") + " " + item["hora"], "%Y-%m-%d %H:%M")
             for item in agenda
             if datetime.datetime.strptime(
                 last_end.strftime("%Y-%m-%d") + " " + item["hora"], "%Y-%m-%d %H:%M"
             ) > last_end),
            last_end + timedelta(hours=3)
        )
        papa_block_min = int((next_wake - last_end).total_seconds() / 60)

    papa_duty_min = sum(
        int((e - s).total_seconds() / 60) for s, e in papa_shifts
    )

    summary = dict(
        tomas        = total_tomas,
        mama_sleep_h = round(mama_sleep_min / 60, 1),
        mama_free_h  = round(mama_free_min / 60, 1),
        papa_block_h = round(papa_block_min / 60, 1),
        papa_duty_h  = round(papa_duty_min / 60, 1),
    )
    return agenda, summary


def render_agenda(agenda, summary):
    if not agenda:
        st.info("Sin previsión disponible.")
        return

    st.markdown("#### 📊 Resumen proyectado (24h)")
    c1, c2, c3 = st.columns(3)
    c1.metric("🍼 Tomas mínimas", summary["tomas"],
              help="Tomas proyectadas en las próximas 24h según el ritmo actual")
    c2.metric("💤 Dream Window mamá", f"{summary['mama_sleep_h']}h",
              help="Horas nocturnas (21–03h) en que papá cubre → mamá duerme del tirón")
    c3.metric("🌿 Tiempo libre mamá", f"{summary['mama_free_h']}h",
              help="Siestas de día en que mamá puede ducharse, comer o descansar")

    c4, c5 = st.columns(2)
    c4.metric("🧔 Papá duerme del tirón", f"{summary['papa_block_h']}h",
              help="Desde que termina su turno (~03:00) hasta las 07:00 → su bloque seguido")
    c5.metric("🕐 Guardia total papá", f"{summary['papa_duty_h']}h",
              help="Horas activo de noche (21–03h) gestionando tomas")

    st.markdown("---")

    prev_is_night = None
    for item in agenda:
        h          = int(item["hora"].split(":")[0])
        is_night   = h >= 20 or h < 7
        if prev_is_night is not None and is_night != prev_is_night:
            label = "🌙 Noche" if is_night else "☀️ Día"
            st.markdown(f"<div style='text-align:center;color:#6B7280;font-size:.8em;"
                        f"padding:6px 0;border-top:1px dashed #D1D5DB;'>{label}</div>",
                        unsafe_allow_html=True)
        prev_is_night = is_night

        st.markdown(f"""
        <div style='background:{item["bg"]};border-left:5px solid {item["border"]};
                    padding:12px;margin-bottom:8px;border-radius:8px;'>
            <div style='font-size:1.05em;color:#1F2937;margin-bottom:5px;'>
                <b>{item["hora"]}</b> &nbsp;{item["icono"]}&nbsp; <b>{item["evento"]}</b>
            </div>
            <div style='font-size:.88em;line-height:1.6;color:#374151;'>
                <b>👩 Mamá:</b> {item["mama"]}<br>
                <b>👨 Papá:</b> {item["papa"]}
            </div>
        </div>""", unsafe_allow_html=True)

# ─── VISTAS ───────────────────────────────────────────────────
DIAPER_TYPE_MAP = {
    "Pipí 💧":          "diaper_wet",
    "Caca 💩":          "diaper_dirty",
    "Pipí + Caca 💧💩": "diaper_both",
    "Seco 🏜️":          "diaper_dry",
}
DIAPER_ICONS = {"diaper_wet":"💧","diaper_dirty":"💩","diaper_both":"💧💩","diaper_dry":"🏜️"}
PHASE_ICONS  = {"feeding":"🍼","sleeping":"😴","activity":"🎯","idle":"☀️"}

def render_setup():
    st.markdown("<h1 style='text-align:center;'>🌙 BebéGuía</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#9CA3AF;'>Tu guía en equipo.</p>",
                unsafe_allow_html=True)
    with st.form("setup_form"):
        name  = st.text_input("Nombre del bebé")
        birth = st.date_input("Fecha de nacimiento (o fecha prevista de parto)",
                              value=datetime.date.today())
        feed  = st.selectbox("Alimentación", [
            "Lactancia materna exclusiva",
            "Mixta (pecho + biberón)",
            "Fórmula / Biberón",
        ])
        tz = st.number_input("Tu zona horaria (UTC+?)", value=1, min_value=-12, max_value=14, step=1,
                             help="Europa Central = 1 (invierno) o 2 (verano/CEST)")
        col_dw1, col_dw2 = st.columns(2)
        dw_start = col_dw1.number_input("Dream Window papá — empieza (hora)", value=21, min_value=18, max_value=23, step=1,
                                         help="Hora en que papá asume el turno nocturno")
        dw_end   = col_dw2.number_input("Dream Window papá — termina (hora)", value=3, min_value=1, max_value=8, step=1,
                                         help="Hora en que termina el turno de papá")
        work_hour = st.number_input("Papá entra a trabajar a las (hora)", value=7, min_value=4, max_value=12, step=1,
                                    help="Define cuándo papá debe levantarse. Limita su bloque de sueño real.")
        papa_mode = st.selectbox("Modo papá hoy", ["💼 Trabajando", "🏠 Teletrabajo", "🌴 Vacaciones"],
                                 help="Ajusta el reparto de tareas en el planificador")
        if st.form_submit_button("Empezar →", use_container_width=True) and name:
            st.session_state.utc_offset = int(tz)
            st.session_state.dw_start   = int(dw_start)
            st.session_state.dw_end     = int(dw_end)
            st.session_state.work_hour  = int(work_hour)
            st.session_state.papa_mode  = papa_mode
            st.session_state.baby = {"name": name, "birth": birth, "feed": feed}
            st.session_state.page = "main"
            change_phase("idle")
            st.rerun()

def render_settings():
    st.subheader("⚙️ Configuración")
    baby = st.session_state.baby
    feed_opts = ["Lactancia materna exclusiva", "Mixta (pecho + biberón)", "Fórmula / Biberón"]
    with st.form("settings_form"):
        new_name  = st.text_input("Nombre", value=baby['name'])
        birth_val = baby.get('birth', datetime.date.today())
        if isinstance(birth_val, str):
            birth_val = datetime.datetime.strptime(birth_val, "%Y-%m-%d").date()
        new_birth = st.date_input("Fecha de nacimiento (o fecha prevista)", value=birth_val)
        idx      = feed_opts.index(baby['feed']) if baby['feed'] in feed_opts else 0
        new_feed = st.selectbox("Alimentación", feed_opts, index=idx)
        new_tz    = st.number_input("Zona horaria (UTC+?)",
                                   value=st.session_state.get('utc_offset', 1),
                                   min_value=-12, max_value=14, step=1)
        col_s1, col_s2 = st.columns(2)
        new_dw_start = col_s1.number_input("Dream Window papá — empieza",
                                            value=st.session_state.get('dw_start', 21),
                                            min_value=18, max_value=23, step=1)
        new_dw_end   = col_s2.number_input("Dream Window papá — termina",
                                            value=st.session_state.get('dw_end', 3),
                                            min_value=1, max_value=8, step=1)
        new_work     = st.number_input("Papá entra a trabajar a las",
                                       value=st.session_state.get('work_hour', 7),
                                       min_value=4, max_value=12, step=1)
        new_mode     = st.selectbox("Modo papá hoy",
                                    ["💼 Trabajando", "🏠 Teletrabajo", "🌴 Vacaciones"],
                                    index=["💼 Trabajando", "🏠 Teletrabajo", "🌴 Vacaciones"].index(
                                        st.session_state.get('papa_mode', '💼 Trabajando')))
        if st.form_submit_button("Guardar", use_container_width=True):
            st.session_state.baby.update(name=new_name, birth=new_birth, feed=new_feed)
            st.session_state.utc_offset = int(new_tz)
            st.session_state.dw_start   = int(new_dw_start)
            st.session_state.dw_end     = int(new_dw_end)
            st.session_state.work_hour  = int(new_work)
            st.session_state.papa_mode  = new_mode
            save_data()
            st.success("¡Guardado!")
            st.session_state.page = "main"
            st.rerun()
    if st.button("← Volver"):
        st.session_state.page = "main"; st.rerun()
    st.markdown("---")
    with st.expander("⚠️ Zona peligrosa"):
        if st.button("🗑️ Borrar todos los datos", type="primary"):
            if os.path.exists(DB_FILE): os.remove(DB_FILE)
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

def render_main():
    baby   = st.session_state.baby
    days   = age_days()
    aw_max = get_aw_max(days)
    now    = now_local()
    el     = elapsed_min()

    c1, c2, c3, c4, c5 = st.columns([3, 1, 1, 1, 1])
    with c1:
        days_to_birth = (baby.get('birth', datetime.date.today()) - datetime.date.today()).days
        if isinstance(baby.get('birth'), str):
            birth_d = datetime.datetime.strptime(baby['birth'], "%Y-%m-%d").date()
            days_to_birth = (birth_d - datetime.date.today()).days
        if days > 0:
            age_str = f"{days}d · {days//7}sem"
        elif days_to_birth > 0:
            age_str = f"⏳ Nacerá en {days_to_birth} días"
        else:
            age_str = "Día 0 · ¡Bienvenido al mundo!"
        st.subheader(f"👶 {baby['name']}")
        st.caption(f"{age_str} · {baby['feed']} · {now.strftime('%H:%M')} (UTC+{st.session_state.get('utc_offset',1)})")
    with c2:
        if st.button("📖"): st.session_state.page = "guide";   st.rerun()
    with c3:
        if st.button("📊"): st.session_state.page = "metrics"; st.rerun()
    with c4:
        if st.button("📋"): st.session_state.page = "history"; st.rerun()
    with c5:
        if st.button("⚙️"): st.session_state.page = "settings"; st.rerun()

    st.markdown("---")
    phase = st.session_state.phase

    if phase == "idle":
        st.info("☀️ **Despierto y tranquilo** — Ofrécele pecho/biberón cuando busque.")
    elif phase == "feeding":
        st.success(f"🍼 **Comiendo** — {el} min\n\n"
                   f"{'Si se duerme comiendo: normal antes de los 4 meses. Ponlo a dormir directamente.' if days < 120 else 'Intenta que termine despierto para separar toma y sueño.'}")
    elif phase == "sleeping":
        st.markdown(
            f"<div style='background:#F3E8FF;padding:15px;border-radius:10px;margin-bottom:12px;'>"
            f"😴 <b>Durmiendo</b> — {el} min<br>"
            f"<small>Boca arriba · superficie firme · sin mantas sueltas.</small></div>",
            unsafe_allow_html=True)
        if days < 30 and el >= 210:
            st.error("🚨 Casi 4h sin comer. Despiértalo suavemente.")
        elif days >= 30 and 7 <= now.hour < 20 and el >= 120:
            st.warning("⚠️ Siesta >2h de día. Plantéate despertarle para proteger el sueño nocturno.")
    elif phase == "activity":
        pct   = min(int(el / aw_max * 100), 100)
        color = "green" if pct < 60 else ("orange" if pct < 85 else "red")
        st.info(f"🎯 **Actividad** — {el} min · Ventana máx: {aw_max} min")
        st.markdown(
            f"<div style='background:#E5E7EB;border-radius:8px;height:12px;'>"
            f"<div style='background:{color};width:{pct}%;height:12px;border-radius:8px;'></div></div>",
            unsafe_allow_html=True)
        if el >= aw_max:
            st.error(f"🚨 Ventana cerrada ({el} min). Acuéstalo ya.")
        elif el >= int(aw_max * 0.8):
            st.warning(f"⏰ Quedan ~{aw_max - el} min. Empieza a calmarlo.")

    st.markdown("<br>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    if c1.button("🍼 Comer",  use_container_width=True): change_phase("feeding");  st.rerun()
    if c2.button("😴 Dormir", use_container_width=True): change_phase("sleeping"); st.rerun()
    if c3.button("🎯 Jugar",  use_container_width=True): change_phase("activity"); st.rerun()
    if c4.button("🧷 Pañal",  use_container_width=True): st.session_state.page = "diaper"; st.rerun()

    st.markdown("---")
    hoy = now.date()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    tomas = sum(1 for l in logs_hoy if l['type'] == "feeding")
    wet   = sum(1 for l in logs_hoy if l['type'] in ("diaper_wet", "diaper_both"))
    col1, col2, col3 = st.columns(3)
    col1.metric("Tomas hoy", tomas, help="Meta orientativa: ≥8/día")
    col2.metric("Pañales mojados", wet, help="Mínimo: 6/día")
    col3.metric("Tiempo en fase", f"{el} min")

    st.markdown("---")
    st.subheader("📅 Planificador EASY — Próximas 24h")
    st.caption("Se ajusta al ritmo real del bebé. Morado = turno de papá (Dream Window).")
    agenda, summary = build_agenda(baby, now, phase, el)
    render_agenda(agenda, summary)

def render_history():
    st.subheader("📋 Historial de hoy")
    if st.button("← Volver"): st.session_state.page = "main"; st.rerun()
    hoy = now_local().date()
    logs_hoy_idx = [(i, l) for i, l in enumerate(st.session_state.logs)
                    if l['ts'].date() == hoy]
    if not logs_hoy_idx:
        st.info("Sin registros hoy.")
    else:
        st.caption("Toca 🗑️ para borrar un registro incorrecto.")
        for global_i, l in reversed(logs_hoy_idx):
            hora  = l['ts'].strftime("%H:%M")
            icono = DIAPER_ICONS.get(l['type'], PHASE_ICONS.get(l['type'], "📝"))
            dur   = f" ({l['durMin']} min)" if l.get('durMin') else ""
            col   = f" — {l['color']}" if l.get('color') else ""
            c_txt, c_btn = st.columns([5, 1])
            c_txt.markdown(f"**{hora}** | {icono} `{l['type']}`{dur}{col}")
            if c_btn.button("🗑️", key=f"del_{global_i}"):
                st.session_state.logs.pop(global_i)
                save_data()
                st.rerun()
    st.markdown("---")
    lines = ["hora,tipo,duracion_min,color"]
    for _, l in logs_hoy_idx:
        lines.append(f"{l['ts'].strftime('%H:%M')},{l['type']},"
                     f"{l.get('durMin','')},{l.get('color','')}")
    st.download_button("⬇️ Exportar CSV", "\n".join(lines),
                       file_name=f"bebe_{hoy}.csv", mime="text/csv")

def render_diaper():
    st.subheader("🧷 ¿Qué hay en el pañal?")
    tipo_label = st.radio("Contenido:", list(DIAPER_TYPE_MAP.keys()))
    color = None
    if "Caca" in tipo_label:
        color = st.selectbox("Color:", [
            "Mostaza 🟡 (Normal)",
            "Verde 💚 (Normal/Transición)",
            "Meconio ⬛ (Normal primeros días)",
            "Blanca/Gris ⬜ (⚠️ Alerta pediátrica)",
            "Roja/Sangre 🔴 (⚠️ Alerta pediátrica)",
        ])
    c1, c2 = st.columns(2)
    if c1.button("Guardar", type="primary"):
        add_log(DIAPER_TYPE_MAP[tipo_label], color=color)
        if color and ("Blanca" in color or "Roja" in color):
            st.error("⚠️ Este color requiere valoración pediátrica.")
        else:
            st.session_state.page = "main"; st.rerun()
    if c2.button("Cancelar"):
        st.session_state.page = "main"; st.rerun()

def render_metrics():
    st.subheader("📊 Métricas del día")
    if st.button("← Volver"): st.session_state.page = "main"; st.rerun()

    now = now_local()
    hoy = now.date()
    logs_hoy = [l for l in st.session_state.logs if l['ts'].date() == hoy]
    days = age_days()

    if not logs_hoy and st.session_state.phase == "idle":
        st.info("Sin datos de hoy todavía. Empieza a registrar con los botones.")
        return

    sleep_logs = [l for l in logs_hoy if l['type'] == 'sleeping']
    feed_logs  = [l for l in logs_hoy if l['type'] == 'feeding']
    wet_logs   = [l for l in logs_hoy if l['type'] in ('diaper_wet', 'diaper_both')]
    dirty_logs = [l for l in logs_hoy if l['type'] in ('diaper_dirty', 'diaper_both')]

    total_sleep_min = sum(l.get('durMin', 0) for l in sleep_logs)
    current_el = elapsed_min()
    if st.session_state.phase == 'sleeping':
        total_sleep_min += current_el
    longest_sleep = max((l.get('durMin', 0) for l in sleep_logs), default=0)
    if st.session_state.phase == 'sleeping':
        longest_sleep = max(longest_sleep, current_el)

    mins_since_midnight = int((now - datetime.datetime.combine(hoy, datetime.time.min)).total_seconds() / 60)
    pct_sleep = round(total_sleep_min / mins_since_midnight * 100) if mins_since_midnight > 0 else 0
    sleep_ok = pct_sleep >= 55

    total_feed_min = sum(l.get('durMin', 0) for l in feed_logs)
    avg_feed = round(total_feed_min / len(feed_logs)) if feed_logs else 0
    feed_times = sorted([l['ts'] for l in feed_logs])
    if len(feed_times) >= 2:
        intervals = [(feed_times[i+1]-feed_times[i]).total_seconds()/60
                     for i in range(len(feed_times)-1)]
        avg_interval = round(sum(intervals)/len(intervals))
    else:
        avg_interval = None
    last_feed = max((l['ts'] for l in feed_logs), default=None)
    min_since_feed = int((now - last_feed).total_seconds()/60) if last_feed else None

    st.markdown("---")
    st.markdown("#### 😴 Sueño")
    c1, c2, c3 = st.columns(3)
    c1.metric("Total dormido hoy",
              f"{total_sleep_min//60}h {total_sleep_min%60}m",
              help="RN: 16–18h/día es normal")
    c2.metric("Tramo más largo", f"{longest_sleep} min",
              help="Con el tiempo este número irá creciendo")
    ok_txt = "✅ Bien" if sleep_ok else "⚠️ Poco"
    c3.metric("% día dormido", f"{pct_sleep}%", delta=ok_txt,
              help="Referencia RN: ≥65% del día")

    st.markdown("#### 🍼 Alimentación")
    c4, c5, c6 = st.columns(3)
    c4.metric("Tomas completadas", len(feed_logs),
              delta="✅ Bien" if len(feed_logs) >= 8 else "⚠️ Meta: 8",
              help="Meta orientativa: ≥8 tomas/día en primeras semanas")
    c5.metric("Duración media", f"{avg_feed} min" if avg_feed else "–",
              help="Normal: 10–25 min por toma")
    c6.metric("Intervalo medio entre tomas",
              f"{avg_interval} min" if avg_interval else "–",
              help="Recomendado <180 min en primeras 3 semanas")

    if min_since_feed is not None:
        alerta = days < 21 and min_since_feed > 180
        msg = (f"🔴 **Última toma hace {min_since_feed} min** — ¡Hay que alimentar!"
               if alerta else
               f"🟢 Última toma hace **{min_since_feed} min**")
        st.info(msg)

    st.markdown("#### 🧷 Pañales")
    c7, c8, c9 = st.columns(3)
    wet_ok = len(wet_logs) >= 6
    c7.metric("Mojados 💧", len(wet_logs),
              delta="✅ Bien" if wet_ok else "⚠️ Meta: 6",
              help="≥6 pañales mojados/día = buena hidratación")
    c8.metric("Con caca 💩", len(dirty_logs),
              help="Variable según edad y método de alimentación")
    total_diapers = len([l for l in logs_hoy if l['type'].startswith('diaper')])
    c9.metric("Total pañales", total_diapers)

    st.markdown("#### 📈 Línea de tiempo de hoy")
    if logs_hoy:
        icons_map = {"feeding":"🍼","sleeping":"😴","activity":"🎯",
                     "idle":"☀️","diaper_wet":"💧","diaper_dirty":"💩",
                     "diaper_both":"💧💩","diaper_dry":"🏜️"}
        events = sorted(logs_hoy, key=lambda x: x['ts'])
        timeline = "  →  ".join(
            f"{l['ts'].strftime('%H:%M')} {icons_map.get(l['type'],'📝')}"
            for l in events
        )
        st.markdown(f"<div style='font-size:0.85em;color:#374151;line-height:2;'>{timeline}</div>",
                    unsafe_allow_html=True)
    else:
        st.caption("Sin eventos registrados aún.")

def render_guide():
    st.subheader("📖 Guía de desarrollo")
    if st.button("← Volver"): st.session_state.page = "main"; st.rerun()

    days  = age_days()
    weeks = days // 7
    feed  = (st.session_state.baby or {}).get('feed', 'Lactancia materna exclusiva')

    max_w = max(weeks, 0)
    sel_w = st.slider("Ver guía para la semana:", 0, 24, max_w,
                      help="Mueve para explorar cómo evolucionará el bebé")
    sel_days = sel_w * 7

    if sel_w < 4:
        etapa = "🌱 Recién nacido (0–4 semanas)"; color = "#FEF9C3"
    elif sel_w < 8:
        etapa = "🌿 Primer mes (4–8 semanas)"; color = "#DCFCE7"
    elif sel_w < 12:
        etapa = "🌸 Segundo mes (8–12 semanas)"; color = "#E0F2FE"
    elif sel_w < 24:
        etapa = "🌻 3–6 meses (12–24 semanas)"; color = "#EDE9FE"
    else:
        etapa = "🌳 +6 meses"; color = "#FEE2E2"

    st.markdown(f"<div style='background:{color};padding:10px 14px;"
                f"border-radius:8px;font-weight:bold;margin-bottom:16px;'>"
                f"{etapa} — Semana {sel_w}</div>", unsafe_allow_html=True)

    st.markdown("### 😴 Sueño")
    aw_lo, aw_hi = get_aw_range(sel_days)
    lo_n, hi_n, lbl_n = get_sleep_range(sel_days, is_night=True)
    lo_d, hi_d, lbl_d = get_sleep_range(sel_days, is_night=False)

    if sel_w < 4:
        total_h = "16–20h"; notas_sueno = "No hay ritmo circadiano. Día = Noche para él. Normal despertar cada 2–3h."
    elif sel_w < 8:
        total_h = "15–17h"; notas_sueno = "Empieza a agrupar ligeramente por las noches. Aún normal despertar 2–3× noche."
    elif sel_w < 12:
        total_h = "~15h"; notas_sueno = "Inicia producción de melatonina. Empieza a distinguir día/noche."
    elif sel_w < 24:
        total_h = "12–16h"; notas_sueno = "Posible regresión de los 4 meses (cambio de ciclos de sueño). Normal y temporal."
    else:
        total_h = "12–14h"; notas_sueno = "Ciclos de sueño más parecidos al adulto."

    c1, c2, c3 = st.columns(3)
    c1.metric("Total/día", total_h)
    c2.metric("Bloque nocturno", lbl_n)
    c3.metric("Siesta diurna", lbl_d)
    st.caption(f"⏱️ Ventana de vigilia: **{aw_lo}–{aw_hi} min** despierto antes de la próxima siesta")
    st.info(f"💡 {notas_sueno}")

    st.markdown("### 🍼 Alimentación")
    is_breast = "materna" in feed.lower()

    if sel_w < 1:
        tomas_dia = "8–12"; ml_toma = "5–10 ml (calostro)"; intervalo = "cada 1–3h"
        nota_ali = "Estómago tamaño canica. El calostro es suficiente y perfecto. No suplementar sin indicación."
    elif sel_w < 2:
        tomas_dia = "8–12"; ml_toma = "20–60 ml"; intervalo = "cada 2–3h"
        nota_ali = "Sube la leche madura (días 3–5). Tomas muy frecuentes = estimulación de producción."
    elif sel_w < 4:
        tomas_dia = "8–10"; ml_toma = "60–90 ml"; intervalo = "cada 2–3h"
        nota_ali = "Si vacía el pecho/biberón y parece insatisfecho → sube 20–30 ml la próxima toma."
    elif sel_w < 8:
        tomas_dia = "7–9"; ml_toma = "90–120 ml"; intervalo = "cada 2.5–3.5h"
        nota_ali = "Tomas más espaciadas y eficientes. Normal que alguna dure solo 5–10 min."
    elif sel_w < 12:
        tomas_dia = "6–8"; ml_toma = "120–150 ml"; intervalo = "cada 3–4h"
        nota_ali = "Más despierto e interesado en el entorno. Puede distraerse durante la toma."
    elif sel_w < 24:
        tomas_dia = "5–7"; ml_toma = "150–180 ml"; intervalo = "cada 3.5–4.5h"
        nota_ali = "A los 6 meses se introduce alimentación complementaria. La leche sigue siendo principal."
    else:
        tomas_dia = "4–5"; ml_toma = "180–240 ml"; intervalo = "cada 4–5h"
        nota_ali = "Papillas y purés como complemento. Nunca en sustitución de la leche antes del año."

    c4, c5, c6 = st.columns(3)
    c4.metric("Tomas/día", tomas_dia)
    c5.metric("Cantidad/toma", ml_toma if not is_breast else "A demanda")
    c6.metric("Intervalo", intervalo)

    if is_breast:
        papa_metodo = papa_feed_method(sel_days, feed)
        st.success(f"👨 **Papá puede alimentar:** {papa_metodo}")
    st.info(f"💡 {nota_ali}")

    st.markdown("### 💩 Deposiciones")
    if sel_w < 1:
        dep_frec = "3–4/día (puede llegar a 8–10)"; dep_color = "Negro/verde oscuro (meconio)"
        dep_nota = "El meconio es normal. Debe desaparecer en 48–72h. Cuenta los pañales para valorar ingesta."
    elif sel_w < 2:
        dep_frec = "3–6/día"; dep_color = "Verde transición → mostaza"
        dep_nota = "Cambio de color = la leche madura está llegando. Buena señal."
    elif sel_w < 8:
        if is_breast:
            dep_frec = "1–8/día (muy variable)"; dep_color = "Mostaza, granulada, líquida"
            dep_nota = "Con lactancia materna es completamente normal no hacer caca varios días."
        else:
            dep_frec = "1–3/día"; dep_color = "Amarillo-marrón, más consistente"
            dep_nota = "Con fórmula son más consistentes y menos frecuentes. ≥1/día es normal."
    elif sel_w < 24:
        dep_frec = "1–4/día o cada 2–3 días"; dep_color = "Amarillo/marrón"
        dep_nota = "La frecuencia se regula con la edad. Lo importante es que sean blandas, no duras."
    else:
        dep_frec = "1–2/día"; dep_color = "Marrón, más adulta"
        dep_nota = "Con la alimentación complementaria el color y consistencia cambiarán según lo que coma."

    c7, c8 = st.columns(2)
    c7.metric("Frecuencia esperada", dep_frec)
    c8.metric("Color normal", dep_color)
    st.info(f"💡 {dep_nota}")
    st.error("🚨 **Consultar al pediatra si:** color blanco/gris/rojo, sangre visible, sin deposición + llanto intenso + abdomen duro.")

    st.markdown("### ⚖️ Peso y crecimiento")
    st.caption("Introduce el peso de nacimiento para calcular la curva esperada.")
    peso_nac = st.number_input("Peso al nacer (gramos)", value=3300, step=50,
                                min_value=1500, max_value=5000)
    if sel_w == 0:
        peso_esp = peso_nac; nota_peso = "Peso de referencia."
    elif sel_w <= 2:
        perdida = peso_nac * 0.07
        recuperacion = perdida / 2 * sel_w
        peso_esp = int(peso_nac - perdida + recuperacion)
        nota_peso = "Pérdida fisiológica normal hasta 10%. Recupera peso nacimiento ~2 semanas."
    elif sel_w <= 12:
        peso_esp = int(peso_nac + (sel_w - 2) * 180)
        nota_peso = "Ganancia esperada: 150–200g/semana en el primer trimestre."
    elif sel_w <= 24:
        base = peso_nac + 10 * 180
        peso_esp = int(base + (sel_w - 12) * 120)
        nota_peso = "Ganancia esperada: 100–130g/semana en el segundo trimestre."
    else:
        base = peso_nac + 10 * 180 + 12 * 120
        peso_esp = int(base + (sel_w - 24) * 80)
        nota_peso = "Ganancia esperada: ~70–90g/semana."

    c9, c10 = st.columns(2)
    c9.metric(f"Peso esperado semana {sel_w}",
              f"{peso_esp:,} g  ({round(peso_esp/1000,2)} kg)")
    c10.metric("Vs. nacimiento", f"{peso_esp - peso_nac:+,} g")
    st.info(f"💡 {nota_peso}")
    st.caption("⚠️ Estos valores son orientativos. El pediatra valorará la curva individual con percentiles.")

    st.markdown("### 🧠 Desarrollo esperado")
    if sel_w < 4:
        hitos = ["Fija la mirada a 20–30 cm", "Reflejo de búsqueda y succión",
                 "Responde a sonidos fuertes", "Mueve brazos y piernas simétricamente"]
        alertas = ["No responde a la voz", "No fija la mirada en ningún momento",
                   "Llanto muy agudo o ausente"]
    elif sel_w < 8:
        hitos = ["Sonrisa social (semana 6–8)", "Sigue objetos con los ojos",
                 "Vocaliza pequeños sonidos", "Levanta ligeramente la cabeza boca abajo"]
        alertas = ["Sin sonrisa social a los 2 meses", "No sigue objetos con la vista"]
    elif sel_w < 12:
        hitos = ["Ríe en voz alta", "Sigue objetos 180°", "Sostiene la cabeza mejor",
                 "Manotea objetos", "Reconoce caras familiares"]
        alertas = ["Sin vocalización", "No sostiene la cabeza en absoluto a las 12 semanas"]
    elif sel_w < 24:
        hitos = ["Se da la vuelta (4–5 meses)", "Agarra objetos", "Balbucea (ba, ma, da)",
                 "Se sienta con apoyo", "Reconoce su nombre"]
        alertas = ["Sin balbuceo a los 6 meses", "No intenta alcanzar objetos",
                   "No aguanta peso en las piernas al sostenerlo de pie"]
    else:
        hitos = ["Se sienta solo", "Pinza índice-pulgar", "Imita gestos",
                 "Gatea o intenta moverse", "Primeras palabras ~12 meses"]
        alertas = ["Sin movilidad dirigida", "Sin gestos imitativos", "Sin palabras a los 12 meses"]

    c11, c12 = st.columns(2)
    with c11:
        st.markdown("**✅ Hitos esperados:**")
        for h in hitos:
            st.markdown(f"- {h}")
    with c12:
        st.markdown("**🚨 Consultar si:**")
        for a in alertas:
            st.markdown(f"- {a}")

    st.markdown("### 🤗 Contacto y porteo")
    if sel_w < 8:
        st.success("Piel con piel ilimitado — regula temperatura, glucemia, frecuencia cardiaca y favorece la lactancia. "
                   "El porteo fisiológico desde el nacimiento es seguro y reduce el llanto hasta un 43%.")
    elif sel_w < 16:
        st.success("Porteo fisiológico recomendado. Posición en M, espalda redondeada, cara visible. "
                   "El contacto sigue siendo esencial para el desarrollo neurológico.")
    else:
        st.info("Sigue siendo beneficioso. A esta edad le interesa más explorar el entorno. "
                "Alterna porteo con tiempo en el suelo para favorecer el desarrollo motor.")

    st.markdown("---")
    st.caption("Fuentes: OMS, AAP, ESPGHAN, Sears (The Baby Book), Gonzalez (Un regalo para toda la vida)")


# ─── ROUTER ───────────────────────────────────────────────────
{
    "setup":    render_setup,
    "settings": render_settings,
    "main":     render_main,
    "diaper":   render_diaper,
    "history":  render_history,
    "metrics":  render_metrics,
    "guide":    render_guide,
}.get(st.session_state.page, render_setup)()
