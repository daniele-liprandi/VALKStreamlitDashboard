import streamlit as st
import pandas as pd
import json
import re
from api_client import get_json

# =========================
# Colors & Mappings
# =========================
STATE_COLORS = {
    "War": "#e74c3c",
    "CivilWar": "#e74c3c",
    "Election": "#e67e22",
    "Elections": "#e67e22",
    "Expansion": "#3498db",
    "Boom": "#2980b9",
    "Bust": "#f1c40f",
    "CivilUnrest": "#f39c12",
    "Famine": "#8e44ad",
    "Outbreak": "#16a085",
    "Investment": "#27ae60",
    "PublicHoliday": "#9b59b6",
    "InfrastructureFailure": "#7f8c8d",
    "Drought": "#d35400",
    "Blight": "#8e44ad",
    "Bust2": "#f1c40f",  # falls API-Varianten existieren
    "PirateAttack": "#16a085",
    "Retreat": "#95a5a6",
    "None": "#181c22",
    "": "#181c22",
}

STATE_ICONS = {
    "War": "⚔️",
    "CivilWar": "⚔️",
    "Election": "🗳️",
    "Elections": "🗳️",
    "Expansion": "🡅",
    "Boom": "📈",
    "Bust": "📉",
    "CivilUnrest": "🔥",
    "Famine": "🍞❌",
    "Outbreak": "🧪",
    "Investment": "💰",
    "PublicHoliday": "🎉",
    "InfrastructureFailure": "🧱",
    "Drought": "🌵",
    "Blight": "🌿❌",
    "PirateAttack": "☠️",
    "Retreat": "⬇️",
    "None": "•",
    "": "•",
}

def _pretty_state_name(s: str) -> str:
    if not s:
        return ""
    # bekanntere Sonderfälle schöner schreiben
    specials = {
        "CivilWar": "Civil War",
        "PublicHoliday": "Public Holiday",
        "InfrastructureFailure": "Infrastructure Failure",
    }
    if s in specials:
        return specials[s]
    # CamelCase → "Camel Case"
    return re.sub(r"(?<!^)(?=[A-Z])", " ", s)

def _parse_states(cell) -> list[str]:
    if not cell:
        return []
    if isinstance(cell, list):
        items = cell
    else:
        items = [x.strip() for x in str(cell).split(",")]
    return [x for x in items if x and x != "None"]

# === Textformatierung (zeigt die Icons) ===
def fmt_state_text(val: str) -> str:
    if not val or val == "None":
        return ""
    return f"{STATE_ICONS.get(val, '•')} {_pretty_state_name(val)}"

def fmt_states_text(cell) -> str:
    states = _parse_states(cell)
    if not states:
        return ""
    return " · ".join(f"{STATE_ICONS.get(s, '•')} {_pretty_state_name(s)}" for s in states)

# === Hintergrund-Färbung ===
def style_state(val: str) -> str:
    if not val or val == "None":
        return ""
    c = STATE_COLORS.get(val, "#181c22")
    return f"background-color:{c}; color:#fff; font-weight:600;"

def style_states_cell(cell) -> str:
    states = _parse_states(cell)
    if not states:
        return ""
    # Ein State → normale Hintergrundfarbe
    if len(states) == 1:
        c = STATE_COLORS.get(states[0], "#181c22")
        return f"background-color:{c}; color:#fff; font-weight:600;"
    # Mehrere States → gleich breite Streifen (linear-gradient)
    n = len(states)
    stops = []
    for i, s in enumerate(states):
        start = int(i * 100 / n)
        end = int((i + 1) * 100 / n)
        color = STATE_COLORS.get(s, "#181c22")
        stops.append(f"{color} {start}% {end}%")
    gradient = ", ".join(stops)
    # Weißer Text + leichte Outline für Lesbarkeit
    return (
        f"background: linear-gradient(90deg, {gradient}); "
        f"color:#fff; font-weight:700; text-shadow: 0 1px 2px rgba(0,0,0,.35);"
    )

def fmt_pct(x: float) -> str:
    try:
        return f"{x:.2%}"
    except Exception:
        return ""

# Optional Override-Tabellen (falls bestimmte Keys hübscher heißen sollen)
GOV_OVERRIDES = {
    "$government_Corporate;": "Corporate",
    "$government_Dictatorship;": "Dictatorship",
    "$government_Feudal;": "Feudal",
    "$government_Patronage;": "Patronage",
    "$government_Democracy;": "Democracy",
    "$government_Communism;": "Communism",
    "$government_Confederacy;": "Confederacy",
    "$government_Cooperative;": "Cooperative",
    "$government_Anarchy;": "Anarchy",
    "$government_PrisonColony;": "Prison Colony",
}

SEC_OVERRIDES = {
    "$SYSTEM_SECURITY_low;": "Low",
    "$SYSTEM_SECURITY_medium;": "Medium",
    "$SYSTEM_SECURITY_high;": "High",
    "$SYSTEM_SECURITY_anarchy;": "Anarchy",
}

# Farbklassen für Chips (CSS Klassen -> Farben)
CHIP_COLORS = {
    "ok": "#064e3b",       # green
    "warn": "#5b3206",     # amber
    "info": "#0f2942",     # blue
    "pp": "#2b193e",       # violet
    "neut": "#27272a",     # gray
    "red": "#3b0d0d",      # red
    "vio": "#3a225f",      # alternative violet
    "sky": "#103048",      # alternative blue
}

# Security -> Farbklasse
def chip_class_for_security(label: str) -> str:
    s = (label or "").strip().lower()
    if s == "high":
        return "ok"
    if s == "medium":
        return "info"
    if s in ("low", "anarchy"):
        return "warn" if s == "low" else "red"
    return "neut"

# Government -> Farbklasse (grob gruppiert)
def chip_class_for_government(label: str) -> str:
    g = (label or "").strip().lower()
    if g in ("corporate", "cooperative"):
        return "sky"
    if g in ("democracy", "confederacy"):
        return "info"
    if g in ("dictatorship", "anarchy", "prison colony"):
        return "red"
    if g in ("patronage", "feudal"):
        return "vio"
    if g in ("communism",):
        return "warn"
    return "neut"

# Helpers (formatting & parsing)
def humanize_constant(val: str, kind: str) -> str:
    """Wandelt FDev-Keys ($government_X; / $SYSTEM_SECURITY_Y;) in Lesetext."""
    if not val:
        return "-"
    if kind == "gov":
        if val in GOV_OVERRIDES:
            return GOV_OVERRIDES[val]
    if kind == "sec":
        if val in SEC_OVERRIDES:
            return SEC_OVERRIDES[val]
    # generischer Fallback
    s = str(val).replace("$", "").replace(";", "")
    s = s.replace("government_", "").replace("SYSTEM_SECURITY_", "")
    s = s.replace("_", " ").title()
    return s or "-"

def color_state(val):
    color = STATE_COLORS.get(val, "#181c22")
    return f"background-color:{color};color:#fff;" if val and val != "None" else ""

def color_states_cell(cell):
    if not cell:
        return ""
    states = [s.strip() for s in cell.split(",") if s.strip()]
    if not states:
        return ""
    color = STATE_COLORS.get(states[0], "#181c22")
    return f"background-color:{color};color:#fff;"

def to_state_list(val):
    """'null'/None/JSON-String/Liste -> Liste reiner State-Namen"""
    if val in (None, "null", "None", ""):
        return []
    if isinstance(val, list):
        out = []
        for x in val:
            if isinstance(x, dict) and "State" in x:
                out.append(x["State"])
            elif isinstance(x, str):
                out.append(x)
        return out
    if isinstance(val, str):
        try:
            obj = json.loads(val)
            return to_state_list(obj)
        except Exception:
            return [s.strip() for s in val.split(",") if s.strip()]
    return []

def parse_json_str_list(val):
    """Für powerplays.power (JSON-String mit Stringliste)."""
    if not val:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            obj = json.loads(val)
            if isinstance(obj, list):
                return [str(x) for x in obj]
        except Exception:
            return [val]
    return [str(val)]

# =========================
# Chip UI
# =========================

def chip_css():
    return f"""
    <style>
      .valk-badges {{ display:flex; flex-wrap:wrap; gap:.5rem; margin:.35rem 0 .85rem 0; }}
      .valk-badge {{ font-size:.85rem; line-height:1; padding:.45rem .6rem; border-radius:999px;
                     background:#1f2937; border:1px solid #374151; display:inline-flex; gap:.35rem;
                     align-items:center; white-space:nowrap; }}
      .valk-badge .lbl {{ opacity:.75; }}
      {"".join([f".valk-badge.{k}{{background:{v};border-color:{v};}}" for k,v in CHIP_COLORS.items()])}
    </style>
    """

def chip(label, value, klass="neut"):
    if value in (None, "", "-", "null"):
        return ""
    return f'<div class="valk-badge {klass}"><span class="lbl">{label}:</span><strong>{value}</strong></div>'

def render_header_chips(sysinfo: dict, pp0: dict):
    allegiance = sysinfo.get("allegiance") or "-"
    government_raw = sysinfo.get("government")
    security_raw = sysinfo.get("security")
    population = sysinfo.get("population")

    government = humanize_constant(government_raw, "gov")
    security = humanize_constant(security_raw, "sec")

    controlling = sysinfo.get("controlling_faction") or "-"
    controlling_power = sysinfo.get("controlling_power") or "-"

    powers_list = parse_json_str_list(pp0.get("power"))
    p_state = pp0.get("powerplay_state") or "-"
    ctrl_prog = pp0.get("control_progress")
    underm = pp0.get("undermining")
    reinf = pp0.get("reinforcement")

    items = [
        chip("Controlling Faction", controlling, "ok"),
        chip("Controlling Power", controlling_power, "pp" if controlling_power != "-" else "neut"),
        chip("Allegiance", allegiance, "info"),
        chip("Government", government, chip_class_for_government(government)),
        chip("Security", security, chip_class_for_security(security)),
        chip("Population", f"{int(population):,}".replace(",", ".")) if isinstance(population, int) else "",
    ]
    if powers_list:
        items.append(chip("Powers (nearby)", ", ".join(powers_list), "pp"))
    if p_state and p_state != "-":
        items.append(chip("PowerPlay", p_state, "pp"))
    if isinstance(ctrl_prog, (int, float)):
        items.append(chip("Ctrl-Progress", f"{ctrl_prog:.1%}", "pp"))
    if isinstance(underm, (int, float)) and underm >= 0:
        items.append(chip("Undermining", f"{int(underm):,}".replace(",", "."), "warn" if underm else "neut"))
    if isinstance(reinf, (int, float)) and reinf >= 0:
        items.append(chip("Reinforcement", f"{int(reinf):,}".replace(",", "."), "ok" if reinf else "neut"))

    html = chip_css() + '<div class="valk-badges">' + "".join([i for i in items if i]) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ============================
# Conflicts-Mapping & Renderer
# ============================
import pandas as pd

CONFLICT_TYPE_LABELS = {
    "war": "⚔️ War",
    "civilwar": "🏛 Civil War",
    "election": "🗳 Election",
}
CONFLICT_TYPE_COLORS = {
    "War": "#c0392b",        # rot
    "Civil War": "#e67e22",  # orange
    "Election": "#3498db",   # blau
}
CONFLICT_STATUS_COLORS = {
    "active": "#065f46",     # grün
    "pending": "#92400e",    # amber
    "ended": "#374151",      # grau (fallback)
}

LEAD_GREEN = "#065f46"      # führt
TRAIL_RED  = "#7f1d1d"      # verliert
TIE_YELLOW = "#a16207"      # unentschieden
CELL_TEXT  = "#ffffff"

def _conflict_row_style(row: pd.Series) -> pd.Series:
    """Gibt pro Spalte CSS-Styles zurück (Pandas Styler row-wise)."""
    styles = {}

    # Type einfärben
    tlabel = row.get("Type", "")
    tcolor = CONFLICT_TYPE_COLORS.get(tlabel, "#374151")
    styles["Type"] = f"background-color:{tcolor};color:{CELL_TEXT};"

    # Status einfärben
    status = str(row.get("Status", "") or "").lower()
    scolor = CONFLICT_STATUS_COLORS.get(status, "#374151")
    styles["Status"] = f"background-color:{scolor};color:{CELL_TEXT};"

    # Leader/Loser markieren (Won D1 / Won D2)
    d1 = int(row.get("Won D1") or 0)
    d2 = int(row.get("Won D2") or 0)

    if d1 == 0 and d2 == 0:
        # Noch keine gewerteten Tage -> KEINE farbliche Markierung der Fraktionen
        pass
    elif d1 > d2:
        styles["Faction 1"] = f"background-color:{LEAD_GREEN};color:{CELL_TEXT};"
        styles["Faction 2"] = f"background-color:{TRAIL_RED};color:{CELL_TEXT};"
    elif d2 > d1:
        styles["Faction 2"] = f"background-color:{LEAD_GREEN};color:{CELL_TEXT};"
        styles["Faction 1"] = f"background-color:{TRAIL_RED};color:{CELL_TEXT};"
    else:
        # Unentschieden (aber mind. einer > 0)
        styles["Faction 1"] = f"background-color:{TIE_YELLOW};color:{CELL_TEXT};"
        styles["Faction 2"] = f"background-color:{TIE_YELLOW};color:{CELL_TEXT};"

    # Stakes etwas dezenter
    styles["Stake 1"] = "opacity:.9;"
    styles["Stake 2"] = "opacity:.9;"

    return pd.Series(styles)

def render_conflicts_table(conflicts: list):
    """Baut die stylische Conflicts-Tabelle und rendert sie."""
    if not conflicts:
        return

    rows = []
    for c in conflicts:
        # Label-Mapping für type
        raw_type = (c.get("war_type") or "").lower()
        type_label = CONFLICT_TYPE_LABELS.get(raw_type, raw_type.title() if raw_type else "-")
        rows.append({
            "Type": type_label,
            "Status": c.get("status") or "-",
            "Faction 1": c.get("faction1") or "-",
            "Stake 1": c.get("stake1") or "-",
            "Faction 2": c.get("faction2") or "-",
            "Stake 2": c.get("stake2") or "-",
            "Won D1": c.get("won_days1") or 0,
            "Won D2": c.get("won_days2") or 0,
        })

    df = pd.DataFrame(rows)

    # hübsche Breiten & Ausrichtung
    styled = (
        df.style
          .apply(_conflict_row_style, axis=1)
          .set_properties(subset=["Type"], **{"min-width": "110px", "max-width": "140px", "text-align": "center"})
          .set_properties(subset=["Status"], **{"min-width": "90px", "max-width": "110px", "text-align": "center"})
          .set_properties(subset=["Faction 1", "Faction 2"], **{"min-width": "220px"})
          .set_properties(subset=["Stake 1", "Stake 2"], **{"min-width": "200px", "max-width": "320px"})
          .set_properties(subset=["Won D1", "Won D2"], **{"min-width": "80px", "text-align": "center"})
    )
    st.table(styled)

# =========================
# Page Render
# =========================
def handle_too_many_systems_response(resp) -> bool:
    """Erkennt die API-Antwort bei zu vielen Treffern und rendert eine Nutzerinfo.
       Gibt True zurück, wenn die Antwort bereits verarbeitet wurde (früher return)."""
    if isinstance(resp, dict) and resp.get("error") and isinstance(resp.get("systems"), list):
        count = resp.get("count", 0)
        limit_hint = 100  # aktuell gesetztes Server-Limit
        st.error("Zu viele Systeme gefunden. Bitte schränke die Filter weiter ein.")
        st.caption(f"Gefundene Systeme: {count} (Limit: {limit_hint})")

        # Kleine Hilfestellung
        with st.expander("Vorschläge für Filter-Verfeinerung", expanded=True):
            st.write(
                "- **System Name** (präziser, mindestens 3 Zeichen)\n"
                "- **Controlling Faction / Power** ergänzen\n"
                "- **State / Pending / Recovering** festlegen\n"
                "- **Has Conflict** aktivieren, wenn relevant"
            )

        # Trefferliste anzeigen (st.table)
        systems = resp.get("systems", [])
        if systems:
            st.subheader("Trefferliste (Auszug)")
            st.table(pd.DataFrame({"System": systems}))

        return True
    return False

def render():
    st.title("System Information")
    st.text("Shows system summary and minor factions. Filter by API parameters.")

    # Filter
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns(8)
    with col1:
        system_name = st.text_input("System Name")
    with col2:
        faction = st.text_input("Faction")
    with col3:
        controlling_faction = st.text_input("Controlling Faction")
    with col4:
        controlling_power = st.text_input("Controlling Power")
    with col5:
        power = st.text_input("Power")
    with col6:
        state = st.selectbox("State", [""] + list(STATE_COLORS.keys()))
    with col7:
        pending_state = st.selectbox("Pending State", [""] + list(STATE_COLORS.keys()))
    with col8:
        recovering_state = st.selectbox("Recovering State", [""] + list(STATE_COLORS.keys()))

    has_conflict = st.checkbox("Has Conflict", value=False)

    params = {}
    if faction: params["faction"] = faction
    if controlling_faction: params["controlling_faction"] = controlling_faction
    if controlling_power: params["controlling_power"] = controlling_power
    if power: params["power"] = power
    if state: params["state"] = state
    if pending_state: params["pending_state"] = pending_state
    if recovering_state: params["recovering_state"] = recovering_state
    if has_conflict: params["has_conflict"] = "true"

    if (not system_name and not params) or (not system_name and len(params) == 1 and "has_conflict" in params):
        st.info("Please set at least one filter to load system data.")
        return

    # --- Daten holen (nur /system-summary; 400-Body sicher auswerten) ---
    try:
        path = f"system-summary/{system_name}" if system_name else "system-summary"
        data = get_json(path, params=params)

    except Exception as e:
        # Versuche, den JSON-Body der 4xx-Antwort auszulesen
        resp_json = None
        try:
            resp = getattr(e, "response", None)
            if resp is not None:
                resp_json = resp.json()
        except Exception:
            resp_json = None

        # Spezialfall „zu viele Systeme“ hübsch rendern + abbrechen
        if resp_json and handle_too_many_systems_response(resp_json):
            return

        # Kein Spezialfall → normaler Fehler
        st.error(f"Error loading data: {e}")
        return

    if isinstance(data, dict) and not ("error" in data and len(data) <= 3):
        data = [data]
    if not data:
        st.warning("No systems found.")
        return

    for entry in data:
        sysinfo = entry.get("system_info", {}) or {}
        sys_name = sysinfo.get("system_name", "Unknown")

        st.subheader(sys_name)

        # Powerplay (erste Zeile)
        pp_list = entry.get("powerplays") or []
        pp0 = pp_list[0] if pp_list else {}

        # Header-Chips (inkl. Government/Security Mapping)
        render_header_chips(sysinfo, pp0)

        # Minor Factions
        factions = entry.get("factions", []) or []
        if not factions:
            st.info("No minor factions found.")
            st.markdown("---")
            continue

        df = pd.DataFrame([
            {
                "Name": f.get("name", ""),
                "Allegiance": f.get("allegiance", ""),
                # Government kann in den Fraktionsdatensätzen leer sein; falls vorhanden: humanize
                "Government": humanize_constant(f.get("government", ""), "gov") if f.get("government") else "",
                "State": "" if (f.get("state") in (None, "", "None")) else f.get("state"),
                "Influence": f.get("influence", 0.0),
                "Active States": ", ".join(to_state_list(f.get("active_states"))),
                "Pending": ", ".join(to_state_list(f.get("pending_states"))),
                "Recovering": ", ".join(to_state_list(f.get("recovering_states"))),
            }
            for f in factions
        ])

        df = df.sort_values(by="Influence", ascending=False).reset_index(drop=True)
        df.index = df.index + 1
        df.index.name = "#"

        styled = (
            df.style
            # Farben (Hintergrund)
            .applymap(style_state, subset=["State"])
            .applymap(style_states_cell, subset=["Active States"])
            .applymap(style_states_cell, subset=["Pending"])
            .applymap(style_states_cell, subset=["Recovering"])
            # Icons + sprechende Labels
            .format({
                "Influence": fmt_pct,
                "State": fmt_state_text,
                "Active States": fmt_states_text,
                "Pending": fmt_states_text,
                "Recovering": fmt_states_text,
            })
            # Breiten/Alignment wie gehabt
            .set_properties(subset=["Influence"], **{
                "text-align": "right",
                "min-width": "90px", "max-width": "90px",
            })
            .set_properties(subset=["Name"], **{
                "min-width": "200px", "max-width": "200px",
            })
            .set_properties(subset=["Allegiance"], **{
                "min-width": "100px", "max-width": "100px",
            })
            .set_properties(subset=["Government"], **{
                "min-width": "120px", "max-width": "120px",
            })
            .set_properties(subset=["State"], **{
                "text-align": "center",
                "min-width": "140px", "max-width": "160px",
            })
            .set_properties(subset=["Active States", "Pending", "Recovering"], **{
                "min-width": "180px", "max-width": "220px",
            })
        )
        st.table(styled)

        # --- Conflicts ---
        conflicts = entry.get("conflicts", []) or []
        if conflicts:
            st.caption("Conflicts")
            render_conflicts_table(conflicts)

        st.markdown("---")
