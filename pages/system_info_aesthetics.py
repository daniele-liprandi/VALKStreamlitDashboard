import streamlit as st
import pandas as pd
import json
import re
from api_client import get_json
from urllib.parse import quote
from _global import STATE_COLORS, STATE_ICONS, GOVERNMENT_COLORS

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


# Aesthetic helper functions for system_info
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

def _fmt_en_num(x):
    try:
        v = float(x)
        return f"{v:,.0f}" if abs(v - int(v)) < 1e-9 else f"{v:,.2f}"
    except Exception:
        return x

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

# Helpers (formatting, parsing, options, resets)
def humanize_constant(val: str, kind: str) -> str:
    """Wandelt FDev-Keys ($government_X; / $SYSTEM_SECURITY_Y;) in Lesetext."""
    if not val:
        return "-"
    if kind == "gov":
        print(f"DEBUG - Incoming gov value: '{val}'")  # Debug print
        print(f"DEBUG - Is in GOV_OVERRIDES: {val in GOV_OVERRIDES}")  # Debug check
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

# CSS für kompaktere Filter-UI
def inject_three_col_rows_css(col_px: int = 200, gap_rem: float = .24):
    st.markdown(f"""
    <style>
      :root {{
        --valk-col: {col_px}px;
        --valk-gap: {gap_rem}rem;
      }}

      /* kompakter: Widgets & Labels */
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stSelectbox"],
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stNumberInput"],
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stTextInput"] {{
        margin-bottom: .24rem !important;
      }}
      label {{ margin-bottom: .16rem !important; }}

      /* Jede markierte Zeile = 3 feste Spalten + flex Füller */
      #sys-row    + div[data-testid="stHorizontalBlock"],
      #fac-row-1  + div[data-testid="stHorizontalBlock"],
      #fac-row-2  + div[data-testid="stHorizontalBlock"],
      #pow-row    + div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: var(--valk-col) var(--valk-col) var(--valk-col) 1fr !important;
        gap: var(--valk-gap) !important;
        align-items: end !important;
        justify-content: start !important;
      }}
    </style>
    """, unsafe_allow_html=True)

def inject_aligned_rows_css(col_px: int = 260, chk_px: int = 180, gap_rem: float = .28):
    st.markdown(f"""
    <style>
      :root {{
        --valk-col: min({col_px}px, 20vw);
        --valk-chk: min({chk_px}px, 15vw);
        --valk-gap: {gap_rem}rem;
      }}

      /* dichter: Widgets & Labels */
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stSelectbox"],
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stNumberInput"],
      [data-testid="stExpander"] .streamlit-expanderContent [data-testid="stTextInput"] {{
        margin-bottom: .28rem !important;
      }}
      label {{ margin-bottom: .18rem !important; }}

      /* Responsive grid - stack for mobile */
      @media (max-width: 1200px) {{
        #sys-row + div[data-testid="stHorizontalBlock"],
        #fac-row + div[data-testid="stHorizontalBlock"],
        #pow-row + div[data-testid="stHorizontalBlock"] {{
          display: flex !important;
          flex-direction: column !important;
          gap: var(--valk-gap) !important;
        }}
        #sys-row + div[data-testid="stHorizontalBlock"] > div,
        #fac-row + div[data-testid="stHorizontalBlock"] > div,
        #pow-row + div[data-testid="stHorizontalBlock"] > div {{
          width: 100% !important;
          max-width: 400px !important;
        }}
      }}

      /* Wide screen */
      @media (min-width: 1201px) {{
        #sys-row + div[data-testid="stHorizontalBlock"],
        #fac-row + div[data-testid="stHorizontalBlock"],
        #pow-row + div[data-testid="stHorizontalBlock"] {{
          display: grid !important;
          grid-template-columns: repeat(3, 1fr) !important;
          gap: var(--valk-gap) !important;
          align-items: end !important;
        }}
      }}
    </style>
    """, unsafe_allow_html=True)

def inject_row_css(field_px: int = 260, checkbox_px: int = 160, gap_rem: float = .35):
    st.markdown(f"""
    <style>
      /* --- Kompaktere Widget-Abstände in Expandern --- */
      [data-testid="stExpander"] .streamlit-expanderContent 
        [data-testid="stSelectbox"],
      [data-testid="stExpander"] .streamlit-expanderContent 
        [data-testid="stMultiSelect"],
      [data-testid="stExpander"] .streamlit-expanderContent 
        [data-testid="stNumberInput"],
      [data-testid="stExpander"] .streamlit-expanderContent 
        [data-testid="stTextInput"],
      [data-testid="stExpander"] .streamlit-expanderContent 
        [data-testid="stDateInput"] {{
        margin-bottom: .35rem !important;
      }}
      [data-testid="stExpander"] .streamlit-expanderContent p {{
        margin: .25rem 0 !important;
      }}

      /* --- System-Reihe: System Name / Population / Has Conflict / Filler --- */
      #sys-row-start + div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: {field_px}px {field_px}px {checkbox_px}px 1fr !important;
        gap: {gap_rem}rem !important;
        align-items: end !important;
        justify-content: start !important;
      }}

      /* --- Faction-Reihe: 5 Selects + Checkbox + Filler --- */
      #fac-row-start + div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: repeat(5, {field_px}px) {checkbox_px}px 1fr !important;
        gap: {gap_rem}rem !important;
        align-items: end !important;
        justify-content: start !important;
      }}

      /* --- Power-Reihe: 3 Selects + Filler --- */
      #pow-row-start + div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: {field_px}px {field_px}px {field_px}px 1fr !important;
        gap: {gap_rem}rem !important;
        align-items: end !important;
        justify-content: start !important;
      }}
    </style>
    """, unsafe_allow_html=True)

def inject_sysrow_css(field_px: int = 260, checkbox_px: int = 160, gap_rem: float = .5):
    st.markdown(f"""
    <style>
      /* Wir targeten GENAU die Columns-Gruppe, die direkt auf den Marker folgt */
      #sys-row-start + div[data-testid="stHorizontalBlock"] {{
        display: grid !important;
        grid-template-columns: {field_px}px {field_px}px {checkbox_px}px 1fr !important;
        gap: {gap_rem}rem !important;
        align-items: end !important;   /* Checkbox unten bündig */
        justify-content: start !important;
      }}
    </style>
    """, unsafe_allow_html=True)

def inject_compact_filter_css(width_px: int = 260):
    # Globale Regeln, kein Scoping – sonst greift es in Streamlit nicht zuverlässig
    st.markdown(f"""
    <style>
      :root {{
        --valk-filter-width: min({width_px}px, 90vw);
        --valk-filter-width-mobile: min(300px, 95vw);
      }}

      /* ---------- kompakter Expander ---------- */
      [data-testid="stExpander"] details > summary {{
        padding: .35rem .5rem !important;
        font-size: .95rem !important;
      }}
      [data-testid="stExpander"] .streamlit-expanderContent {{
        padding: .35rem .25rem .25rem .25rem !important;
      }}

      /* ---------- Responsive Widget-Breiten ---------- */
      @media (max-width: 768px) {{
        :root {{
          --valk-filter-width: var(--valk-filter-width-mobile);
        }}
        
        /* Auf kleinen Bildschirmen: volle Breite nutzen */
        [data-testid="stSelectbox"],
        [data-testid="stMultiSelect"],
        [data-testid="stNumberInput"],
        [data-testid="stTextInput"],
        [data-testid="stDateInput"] {{
          width: 100% !important;
        }}
        
        [data-testid="stSelectbox"] > div,
        [data-testid="stMultiSelect"] > div,
        [data-testid="stNumberInput"] > div,
        [data-testid="stTextInput"] > div,
        [data-testid="stDateInput"] > div {{
          width: 100% !important;
          max-width: 100% !important;
          min-width: auto !important;
        }}
      }}

      @media (min-width: 769px) {{
        /* Desktop: feste Breiten beibehalten */
        [data-testid="stSelectbox"],
        [data-testid="stMultiSelect"],
        [data-testid="stNumberInput"],
        [data-testid="stTextInput"],
        [data-testid="stDateInput"] {{
          display: inline-block !important;
          flex: 0 0 auto !important;
        }}

        /* 1) Erste Wrapper-Ebene (Streamlit um das Widget) */
        [data-testid="stSelectbox"] > div,
        [data-testid="stMultiSelect"] > div,
        [data-testid="stNumberInput"] > div,
        [data-testid="stTextInput"] > div,
        [data-testid="stDateInput"] > div {{
          width: var(--valk-filter-width) !important;
          max-width: var(--valk-filter-width) !important;
          min-width: var(--valk-filter-width) !important;
        }}

        /* 2) Nächste Ebene im Select */
        [data-testid="stSelectbox"] > div > div,
        [data-testid="stMultiSelect"] > div > div {{
          width: var(--valk-filter-width) !important;
          max-width: var(--valk-filter-width) !important;
          min-width: var(--valk-filter-width) !important;
        }}

        /* 3) BaseWeb/React-Select Container selbst */
        [data-testid="stSelectbox"] div[data-baseweb="select"],
        [data-testid="stMultiSelect"] div[data-baseweb="select"],
        [data-testid="stSelectbox"] div[role="combobox"],
        [data-testid="stMultiSelect"] div[role="combobox"] {{
          width: var(--valk-filter-width) !important;
          max-width: var(--valk-filter-width) !important;
          min-width: var(--valk-filter-width) !important;
        }}

        /* 4) Inputs direkt */
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input {{
          width: var(--valk-filter-width) !important;
          max-width: var(--valk-filter-width) !important;
          min-width: var(--valk-filter-width) !important;
        }}
      }}

      /* Labels enger (mehr vertikale Dichte) */
      label {{ margin-bottom: .2rem !important; }}

      /* kompakte Button-Reihe - responsive */
      .btn-row > div {{ 
        display: flex !important; 
        gap: .5rem !important; 
        align-items: center !important; 
        flex-wrap: wrap !important;
      }}
      
      @media (max-width: 480px) {{
        .btn-row > div {{
          flex-direction: column !important;
          align-items: stretch !important;
        }}
      }}
    </style>
    """, unsafe_allow_html=True)

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
