import streamlit as st
import pandas as pd
import json
import re
from api_client import get_json
from urllib.parse import quote
from _global import STATE_COLORS, STATE_ICONS, GOVERNMENT_COLORS

from system_info_aesthetics import *



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

def build_stable_options(base_list, current_value, snapshot_value):
    base = list(dict.fromkeys([x for x in ([current_value, snapshot_value] + (base_list or [])) if x]))
    options = [""] + base
    idx = 0
    if current_value in options:
        idx = options.index(current_value)
    elif snapshot_value in options:
        idx = options.index(snapshot_value)
    return options, idx

RESET_WIDGET_KEYS = [
    "system_name_filter",
    "faction_filter",
    "controlling_faction_filter",
    "controlling_power_filter",
    "power_filter",
    "state_filter",
    "pending_state_filter",
    "recovering_state_filter",
    "has_conflict_filter",
    "controlling_faction_in_conflict_filter",
    "population_preset_filter",
    "population_min_filter",
    "population_max_filter",
    "powerplay_state_filter",
]

POP_PRESETS = {
    "All": (None, None),
    "1 – 100,000": (1, 100_000),
    "100,000 – 1,000,000": (100_000, 1_000_000),
    "1,000,000 – 100,000,000": (1_000_000, 100_000_000),
    "100,000,000 – 500,000,000": (100_000_000, 500_000_000),
    "500,000,000 – 1,000,000,000": (500_000_000, 1_000_000_000),
    "1,000,000,000+": (1_000_000_000, None),
    "Custom…": ("custom", "custom"),
}

def _fmt_us(n) -> str:
    if n is None:
        return "∞"
    return f"{n:,}"

def build_population_param(pop_min, pop_max) -> str:
    """
    Returns 'min-max' per API spec. Open upper bound -> 'min-'.
    Whole range -> None (do not include the parameter).
    """
    if pop_min is None and pop_max is None:
        return None
    if pop_min is None:
        pop_min = 0
    if pop_max is None:
        return f"{int(pop_min)}-"
    return f"{int(pop_min)}-{int(pop_max)}"

def _apply_reset_if_requested():
    """Wenn _do_reset gesetzt ist, alle Widget-Keys & Suche zurücksetzen.
       Muss VOR dem Rendern der Widgets aufgerufen werden!"""
    if st.session_state.get("_do_reset"):
        # Widget-Keys entfernen -> Widgets starten mit Default
        for k in RESET_WIDGET_KEYS:
            st.session_state.pop(k, None)

        # Suchzustand zurücksetzen
        st.session_state.run_search = False
        st.session_state.params_snapshot = {}
        st.session_state.system_name_snapshot = ""

        # Flag löschen
        st.session_state._do_reset = False

def render_grouped_header(sysinfo: dict, pp0: dict, conflicts_count: int = 0):
    allegiance = sysinfo.get("allegiance") or "-"
    government_raw = sysinfo.get("government")
    security_raw = sysinfo.get("security")
    population = sysinfo.get("population")

    government = humanize_constant(government_raw, "gov")
    security   = humanize_constant(security_raw, "sec")

    controlling = sysinfo.get("controlling_faction") or "-"
    controlling_power = sysinfo.get("controlling_power") or "-"

    # PowerPlay (erste Zeile, optional)
    powers_list = parse_json_str_list(pp0.get("power"))
    p_state     = pp0.get("powerplay_state") or "-"
    ctrl_prog   = pp0.get("control_progress")
    underm      = pp0.get("undermining")
    reinf       = pp0.get("reinforcement")

    # ---- Gruppen zusammenstellen ----
    sys_items = [
        chip("Security", security, chip_class_for_security(security)),
        chip("Population", f"{int(population):,}".replace(",", ".")) if isinstance(population, int) else "",
        chip("Conflicts", str(int(conflicts_count)), "warn" if conflicts_count else "neut"),
    ]

    faction_items = [
        chip("Controlling Faction", controlling, "ok"),
        chip("Allegiance", allegiance, "info"),
        chip("Government", government, chip_class_for_government(government)),
    ]

    pp_items = [
        chip("Controlling Power", controlling_power, "pp" if controlling_power != "-" else "neut"),
        chip("Powers (nearby)", ", ".join(powers_list), "pp") if powers_list else "",
        chip("PowerPlay", p_state, "pp") if p_state and p_state != "-" else "",
        chip("Ctrl-Progress", f"{float(ctrl_prog):.1%}", "pp") if isinstance(ctrl_prog, (int, float)) else "",
        chip("Undermining", f"{int(underm):,}".replace(",", "."), "warn" if (isinstance(underm, (int, float)) and underm > 0) else "neut") if isinstance(underm, (int, float)) else "",
        chip("Reinforcement", f"{int(reinf):,}".replace(",", "."), "ok" if (isinstance(reinf, (int, float)) and reinf > 0) else "neut") if isinstance(reinf, (int, float)) else "",
    ]

    # ---- CSS + HTML (Gruppenüberschriften + Chips) ----
    css = chip_css() + """
    <style>
      .valk-group { margin:.35rem 0 1rem 0; }
      .valk-title { font-size:.9rem; opacity:.85; margin-bottom:.35rem; 
                    text-transform:uppercase; letter-spacing:.06em; }
    </style>
    """
    def row(title, items):
        row_html = ''.join([i for i in items if i])
        if not row_html:
            return ""
        return f'<div class="valk-group"><div class="valk-title">{title}</div><div class="valk-badges">{row_html}</div></div>'

    html = css + row("System Info", sys_items) + row("Faction Info", faction_items) + row("Powerplay", pp_items)
    st.markdown(html, unsafe_allow_html=True)

def render_header_chips(sysinfo: dict, pp0: dict, conflict_count: int = 0):
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
    if conflict_count > 0:
        items.append(chip("Conflicts", str(conflict_count), "red"))

    html = chip_css() + '<div class="valk-badges">' + "".join([i for i in items if i]) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ============================
# CMDR Events / Leaderboard
# ============================
SUMMARY_ENDPOINTS = [
    ("Market Events",         "market-events"),
    ("Missions Completed",    "missions-completed"),
    ("Missions Failed",       "missions-failed"),
    ("Bounty Vouchers",       "bounty-vouchers"),
    ("Combat Bonds",          "combat-bonds"),
    ("Exploration Sales",     "exploration-sales"),
    ("Bounty Fines",          "bounty-fines"),
    ("Influence by Faction",  "influence-by-faction"),
    ("Influence EIC",         "influence-eic"),
]

def _alias_col(name: str) -> str:
    """Robuste Alias-Erkennung für API-Spaltennamen (case/variante-insensitiv)."""
    n = re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")
    if "cmdr" in n or "commander" in n: return "cmdr"
    if "rank" in n: return "sq_rank"
    if "faction" in n: return "faction"

    # typische Value-Spalten
    if "buy" in n: return "buy"
    if "sell" in n: return "sell"
    if "quantity" in n: return "total_quantity"
    if "volume" in n: return "total_volume"
    if "completed" in n: return "missions_completed"
    if "failed" in n: return "missions_failed"
    if "voucher" in n: return "bounty_vouchers"
    if "bond" in n: return "combat_bonds"
    if "sale" in n: return "exploration_sales"
    if "fine" in n: return "bounty_fines"
    if "influence" in n: return "influence"
    if "credit" in n or n.endswith("_cr"): return "credits"
    if n in ("total","sum","amount","value"): return n
    return n  # fallback

def _pretty_header(alias: str) -> str:
    """Schöne, konsistente Spaltenüberschriften."""
    mapping = {
        "cmdr": "Cmdr.",
        "sq_rank": "Sq.-Rank",
        "faction": "Faction",
        "buy": "Buy (Cr.)",
        "sell": "Sell (Cr.)",
        "total_quantity": "Total Quantity (tons)",
        "total_volume": "Total Volume (Cr.)",
        "missions_completed": "Missions completed",
        "missions_failed": "Missions failed",
        "bounty_vouchers": "Bounty Vouchers (Cr.)",
        "combat_bonds": "Combat Bonds (Cr.)",
        "exploration_sales": "Exploration Sales (Cr.)",
        "bounty_fines": "Bounty Fines (Cr.)",
        "credits": "Credits (Cr.)",
        "influence": "Influence",
        "total": "Total",
        "sum": "Sum",
        "amount": "Amount",
        "value": "Value",
    }
    # Fallback: schöne Titelcase + Spaces
    return mapping.get(alias, re.sub(r"_+", " ", alias).title())

def _fmt_us_num(x):
    if x is None or (isinstance(x, float) and pd.isna(x)): return ""
    try:
        v = float(x)
        if abs(v - int(v)) < 1e-9:
            return f"{int(v):,}"
        return f"{v:,.2f}"
    except Exception:
        return str(x)

def _normalize_activity_df(label: str, data) -> tuple[pd.DataFrame, list[str]]:
    """
    Baut einen DataFrame, normalisiert Spalten:
    - Cmdr. zuerst, danach Sq.-Rank, dann optionale Textspalten (z. B. Faction), dann Value-Spalten
    - Schöne Header, numerische Spalten erkannt
    Gibt (df, numeric_cols) zurück.
    """
    df = pd.DataFrame(data)
    if df.empty:
        return df, []

    # 1) Alias-Erkennung & Umbenennen → schöne Header
    alias_map = {c: _alias_col(c) for c in df.columns}
    pretty_map = {c: _pretty_header(alias_map[c]) for c in df.columns}
    df = df.rename(columns=pretty_map)

    # 2) Numerische Spalten bestimmen
    #    (erst versuchen zu konvertieren, wo sinnvoll)
    for c in df.columns:
        if df[c].dtype == object:
            try:
                df[c] = pd.to_numeric(df[c].str.replace(",", ""), errors="ignore")
            except Exception:
                pass
    numeric_cols = list(df.select_dtypes(include=["number"]).columns)

    # 3) Order bestimmen:
    #    Cmdr. → Sq.-Rank → optionale Textspalten (Faction, ...) → alle numerischen Werte
    left = []
    if "Cmdr." in df.columns: left.append("Cmdr.")
    if "Sq.-Rank" in df.columns: left.append("Sq.-Rank")
    # optionale Deskriptoren (außer Cmdr./Sq.-Rank), die NICHT numerisch sind
    descr = [c for c in ["Faction"] if c in df.columns and c not in numeric_cols]
    values = [c for c in df.columns if c not in left + descr]
    # Value-Spalten: numerische zuerst, dann evtl. restliche
    values_num = [c for c in values if c in numeric_cols]
    values_rest = [c for c in values if c not in numeric_cols]
    new_order = left + descr + values_num + values_rest
    df = df[new_order]

    # 4) Index „No.“ setzen
    df = df.reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "No."

    return df, values_num

def fetch_all_cmdr_summaries(system_name: str, period: str) -> dict:
    """
    Ruft alle Summary-APIs lazy ab: /api/summary/<endpoint>?period=<ct|lt>&system_name=<name>
    Gibt Dict[Label] -> Daten (Liste/Dict) zurück.
    """
    params = {"period": period, "system_name": system_name}
    out = {}
    for label, endpoint in SUMMARY_ENDPOINTS:
        try:
            out[label] = get_json(f"summary/{endpoint}", params=params) or []
        except Exception as e:
            out[label] = {"error": str(e)}
    return out

def render_cmdr_events_block(system_name: str, period: str, results: dict):
    """
    Zeigt die geladenen Summary-Daten in Tabs an – mit Cmdr.-first, schönen Headers,
    rechtsbündigen en-US Zahlen & sinnvoller Sortierung.
    """
    with st.expander(f"👨‍🚀 CMDR Events — {system_name} [{period.upper()}]", expanded=True):
        tabs = st.tabs([label for (label, _) in SUMMARY_ENDPOINTS])
        for (label, _), tab in zip(SUMMARY_ENDPOINTS, tabs):
            with tab:
                data = results.get(label, [])
                if isinstance(data, dict) and data.get("error"):
                    st.error(f"{label}: {data['error']}")
                    continue
                df, num_cols = _normalize_activity_df(label, data)
                if df.empty:
                    st.info("No data.")
                    continue

                # sortiere nach erster Value-Spalte (numerisch), falls vorhanden
                if num_cols:
                    df = df.sort_values(num_cols[0], ascending=False)

                # Styling: Zahlenspalten rechtsbündig + en-US format
                fmt = {c: _fmt_us_num for c in num_cols}
                styled = (
                    df.style
                      .format(fmt)
                      .set_properties(subset=num_cols, **{"text-align": "right", "min-width": "110px"})
                )
                st.table(styled)

# ============================
# Conflicts-Mapping & Renderer
# ============================
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

# =============================
# Minor Factions Table Renderer
# =============================
def render_minor_factions_table(factions: list) -> None:
    """
    Tabellendarstellung der Minor Factions – identisch zur Systemseite.
    Erwartet die rohe Liste aus dem API-Response unter entry['factions'].
    """
    if not factions:
        st.info("No minor factions found.")
        return

    df = pd.DataFrame([
        {
            "Name": f.get("name", ""),
            "Allegiance": f.get("allegiance", ""),
            "Government": humanize_constant(f.get("government", ""), "gov") if f.get("government") else "",
            "State": "" if (f.get("state") in (None, "", "None")) else f.get("state"),
            "Influence": f.get("influence", 0.0),
            "Active States": ", ".join(to_state_list(f.get("active_states"))),
            "Pending": ", ".join(to_state_list(f.get("pending_states"))),
            "Recovering": ", ".join(to_state_list(f.get("recovering_states"))),
        }
        for f in factions if isinstance(f, dict)
    ])

    if df.empty:
        st.info("No minor factions found.")
        return

    df = df.sort_values(by="Influence", ascending=False).reset_index(drop=True)
    df.index = df.index + 1
    df.index.name = "#"

    styled = (
        df.style
          .applymap(style_state, subset=["State"])
          .applymap(style_states_cell, subset=["Active States"])
          .applymap(style_states_cell, subset=["Pending"])
          .applymap(style_states_cell, subset=["Recovering"])
          .format({
              "Influence": fmt_pct,
              "State": fmt_state_text,
              "Active States": fmt_states_text,
              "Pending": fmt_states_text,
              "Recovering": fmt_states_text,
          })
          .set_properties(subset=["Influence"], **{"text-align": "right", "min-width": "90px", "max-width": "90px"})
          .set_properties(subset=["Name"], **{"min-width": "200px", "max-width": "200px"})
          .set_properties(subset=["Allegiance"], **{"min-width": "100px", "max-width": "100px"})
          .set_properties(subset=["Government"], **{"min-width": "120px", "max-width": "120px"})
          .set_properties(subset=["State"], **{"text-align": "center", "min-width": "140px", "max-width": "160px"})
          .set_properties(subset=["Active States", "Pending", "Recovering"], **{"min-width": "180px", "max-width": "220px"})
    )
    st.table(styled)

# ================================
# System Activities Table Renderer
# ================================
def fetch_system_activities(system_name: str, period: str):
    params = {"system": system_name, "period": period}  # ct|lt|tickid
    data = get_json("activities/system-summary", params=params) or []
    # Server kann einzelnes Objekt liefern → Liste herstellen
    if isinstance(data, dict):
        data = [data]
    # nur Sicherheitshalber: auf das angefragte System filtern
    if system_name:
        data = [r for r in data if (r.get("system") or "").lower() == system_name.lower()]
    return data



def render_system_activities_table(rows: list):
    if not rows:
        st.info("No data.")
        return

    rows = sorted(rows, key=lambda r: str(r.get("tickid", "")), reverse=True)
    r = rows[0]

    # System NICHT als Spalte, sondern als Index; KEINE Tick/tickid-Spalte mehr
    table_row = {
        "System": r.get("system", "-"),
        # INF
        "INF Pri": r.get("total_inf_primary", 0),
        "INF Sec": r.get("total_inf_secondary", 0),
        # TRADE (Buy / Sell)
        "Buy Items":  r.get("buy_items_total", 0),
        "Buy Value":  r.get("buy_value_total", 0),
        "Sell Items": r.get("sell_items_total", 0),
        "Sell Value": r.get("sell_value_total", 0),
        "Profit":     r.get("sell_profit_total", 0),
        # BM / BVs / Exploration / CBs / Fails
        "BM":     r.get("total_trade_bm", 0),
        "BVs":    r.get("total_bvs", 0),
        "Expl":   r.get("total_exploration", 0),
        "CBs":    r.get("total_cbs", 0),
        "Fails":  r.get("total_mission_fails", 0),
        # Murders / S&R
        "Murders (Ground)": r.get("total_murders_ground", 0),
        "Murders (Ship)":   r.get("total_murders_ship", 0),
        "S&R":              r.get("total_sandr", 0),
        # CZs Space/Ground
        "SpaceCZ L": r.get("cz_space_L", 0),
        "SpaceCZ M": r.get("cz_space_M", 0),
        "SpaceCZ H": r.get("cz_space_H", 0),
        "GroundCZ L": r.get("cz_ground_L", 0),
        "GroundCZ M": r.get("cz_ground_M", 0),
        "GroundCZ H": r.get("cz_ground_H", 0),
    }

    df = pd.DataFrame([table_row]).set_index("System")

    num_cols = list(df.columns)
    styled = (
        df.style
        .format({c: _fmt_en_num for c in num_cols})
        .set_properties(subset=num_cols, **{"text-align": "right", "min-width": "90px"})
        # ⬇️ NEU: Index-Spalte breiter machen
        .set_table_styles([
            {"selector": "th.row_heading", "props": "min-width:200px;"},
            {"selector": "th.row_heading.level0", "props": "min-width:200px;"},
        ])
    )
    st.table(styled)


# =================================
# Faction Activities Table Renderer
# =================================
def fetch_faction_activities(system_name: str, period: str):
    # period: ct|lt|tickid
    params = {"system": system_name, "period": period, "group": "faction"}
    data = get_json("activities/system-summary", params=params) or []
    if isinstance(data, dict):
        data = [data]
    # Nur Sicherheit: auf System filtern
    if system_name:
        data = [r for r in data if (r.get("system") or "").lower() == system_name.lower()]
    return data

def render_faction_activities_table(rows: list):
    """
    Erwartet Response-Liste aus /api/activities/system-summary?group=faction.
    Zeigt je Minor Faction eine Zeile
    """
    if not rows:
        st.info("No data.")
        return

    # Nur nach Faction sortieren (State entfällt)
    rows = sorted(rows, key=lambda r: str(r.get("faction", "")))

    # In DataFrame überführen – NUR gewünschte Spalten
    table = []
    for r in rows:
        table.append({
            "Faction": r.get("faction", "-"),
            # INF
            "INF Pri": r.get("total_inf_primary", 0),
            "INF Sec": r.get("total_inf_secondary", 0),
            # TRADE (Buy / Sell / Profit)
            "Buy Items":  r.get("buy_items_total", 0),
            "Buy Value":  r.get("buy_value_total", 0),
            "Sell Items": r.get("sell_items_total", 0),
            "Sell Value": r.get("sell_value_total", 0),
            "Profit":     r.get("sell_profit_total", 0),
            # BM / BVs / Exploration / CBs / Fails
            "BM":    r.get("total_trade_bm", 0),
            "BVs":   r.get("total_bvs", 0),
            "Expl":  r.get("total_exploration", 0),
            "CBs":   r.get("total_cbs", 0),
            "Fails": r.get("total_mission_fails", 0),
            # Murders / S&R
            "Murders (Ground)": r.get("total_murders_ground", 0),
            "Murders (Ship)":   r.get("total_murders_ship", 0),
            "S&R":              r.get("total_sandr", 0),
            # CZs
            "SpaceCZ L":  r.get("cz_space_L", 0),
            "SpaceCZ M":  r.get("cz_space_M", 0),
            "SpaceCZ H":  r.get("cz_space_H", 0),
            "GroundCZ L": r.get("cz_ground_L", 0),
            "GroundCZ M": r.get("cz_ground_M", 0),
            "GroundCZ H": r.get("cz_ground_H", 0),
        })

    df = pd.DataFrame(table).set_index("Faction")

    # Formatter (en-US) + rechtsbündige Zahlen
    def _fmt_en_num(x):
        try:
            v = float(x)
            return f"{v:,.0f}" if abs(v - int(v)) < 1e-9 else f"{v:,.2f}"
        except Exception:
            return "" if x is None else x

    num_cols = list(df.columns)
    styled = (
        df.style
        .format({c: _fmt_en_num for c in num_cols})
        .set_properties(subset=num_cols, **{"text-align": "right", "min-width": "80px"})
        # ⬇️ NEU: Index-Spalte breiter machen
        .set_table_styles([
            {"selector": "th.row_heading", "props": "min-width:200px;"},
            {"selector": "th.row_heading.level0", "props": "min-width:200px;"},
        ])
    )
    st.table(styled)


# ============================
# Page Render, Filter & Search
# ============================
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

def get_list_from_api(endpoint, label="name"):
    try:
        data = get_json(endpoint)
        if isinstance(data, list):
            # Falls die API eine Liste von Strings liefert
            if all(isinstance(x, str) for x in data):
                return sorted(data)
            # Falls die API eine Liste von Dicts liefert
            elif all(isinstance(x, dict) and label in x for x in data):
                return sorted([x[label] for x in data])
        return []
    except Exception as e:
        # Debug: Show error information in Streamlit
        st.error(f"Error loading {endpoint}: {str(e)}")
        return []

def render():
    st.title("System Information")
    st.text("Shows system summary and minor factions. Filter by API parameters.")

    # Dropdown-Listen laden (können leer/flackernd sein)
    system_names = get_list_from_api("lists/systems")
    factions = get_list_from_api("lists/factions")
    controlling_factions = get_list_from_api("lists/controlling-factions")
    controlling_powers = get_list_from_api("lists/controlling-powers")
    powers = controlling_powers  # gleiche Liste wie controlling_power

    # STATE-Init (oben in render(), vor dem UI)
    if "run_search" not in st.session_state:
        st.session_state.run_search = False
    if "params_snapshot" not in st.session_state:
        st.session_state.params_snapshot = {}
    if "system_name_snapshot" not in st.session_state:
        st.session_state.system_name_snapshot = ""

    # Reset ggf. anwenden, BEVOR Widgets gerendert werden
    _apply_reset_if_requested()

    # CSS für kompakte Filter-UI
    inject_compact_filter_css(width_px=200)
    inject_three_col_rows_css(col_px=200, gap_rem=.22)

    # FILTER als FORM – löst keine Suche aus, bis "Search" geklickt wird
    with st.form("system_filters"):
        # --- aktuelle Werte/Snapshots wie gehabt ---
        current_sel = st.session_state.get("system_name_filter", "")
        last_snapshot = st.session_state.get("system_name_snapshot", "")
        snap = st.session_state.get("params_snapshot", {})

        base = list(dict.fromkeys([x for x in ([current_sel, last_snapshot] + (system_names or [])) if x]))
        system_name_options = [""] + base

        sel_index = 0
        if current_sel and current_sel in system_name_options:
            sel_index = system_name_options.index(current_sel)
        elif last_snapshot and last_snapshot in system_name_options:
            sel_index = system_name_options.index(last_snapshot)

        # =========================
        # System (Expander)
        # =========================
        with st.expander("System", expanded=True):
            st.markdown('<span id="sys-row"></span>', unsafe_allow_html=True)

            # 3 Felder + Spacer
            sys_cols = st.columns(3)

            with sys_cols[0]:
                system_name = st.selectbox("System Name", system_name_options, index=sel_index,
                                           key="system_name_filter")
            with sys_cols[1]:
                population_preset = st.selectbox("Population", list(POP_PRESETS.keys()), index=0,
                                                 key="population_preset_filter")
            with sys_cols[2]:
                has_conflict = st.checkbox("Has Conflict", value=False, key="has_conflict_filter")

            # Ableitung Min/Max + optional Custom
            pop_min, pop_max = POP_PRESETS[population_preset]
            if pop_min == "custom" and pop_max == "custom":
                cx1, cx2 = st.columns(2)
                with cx1:
                    pop_min = st.number_input("Min (incl.)", min_value=0, step=1, format="%d",
                                              key="population_min_filter")
                with cx2:
                    no_upper = st.checkbox("No upper limit", value=False)
                    if no_upper:
                        pop_max = None
                    else:
                        pop_max = st.number_input("Max (incl.)", min_value=0, step=1, format="%d",
                                                  key="population_max_filter")

            # Statuszeile
            if pop_min is None and pop_max is None:
                st.caption("Active range: **All**")
            elif pop_max is None:
                st.caption(f"Active range: **{_fmt_us(pop_min)}+**")
            else:
                st.caption(f"Active range: **{_fmt_us(pop_min)} – {_fmt_us(pop_max)}**")

        # =========================
        # Faction (Expander)
        # =========================
        with st.expander("Faction", expanded=False):
            # Zeile 1
            st.markdown('<span id="fac-row-1"></span>', unsafe_allow_html=True)
            f1_cols = st.columns(4)
            with f1_cols[0]:
                cur = st.session_state.get("faction_filter", "")
                snap_val = snap.get("faction", "")
                opts, idx = build_stable_options(factions, cur, snap_val)
                faction = st.selectbox("Faction", opts, index=idx, key="faction_filter")
            with f1_cols[1]:
                cur = st.session_state.get("controlling_faction_filter", "")
                snap_val = snap.get("controlling_faction", "")
                opts, idx = build_stable_options(controlling_factions, cur, snap_val)
                controlling_faction = st.selectbox("Controlling Faction", opts, index=idx,
                                                   key="controlling_faction_filter")
            with f1_cols[2]:
                state = st.selectbox("State", [""] + list(STATE_COLORS.keys()), key="state_filter")

            with f1_cols[3]:
                government = st.selectbox("Government", [""] + list(GOVERNMENT_COLORS.keys()),
                                          key="government_filter")

            # Zeile 2
            st.markdown('<span id="fac-row-2"></span>', unsafe_allow_html=True)
            f2_cols = st.columns(3)
            with f2_cols[0]:
                pending_state = st.selectbox("Pending State", [""] + list(STATE_COLORS.keys()),
                                             key="pending_state_filter")
            with f2_cols[1]:
                recovering_state = st.selectbox("Recovering State", [""] + list(STATE_COLORS.keys()),
                                                key="recovering_state_filter")
            with f2_cols[2]:
                controlling_faction_in_conflict = st.checkbox(
                    "Controlling Faction in conflict",
                    value=False,
                    help="Only systems where the chosen Controlling Faction is in conflict.",
                    key="controlling_faction_in_conflict_filter"
                )

        # =========================
        # Power (Expander)
        # =========================
        with st.expander("Power", expanded=False):
            st.markdown('<span id="pow-row"></span>', unsafe_allow_html=True)

            p_cols = st.columns(3)
            with p_cols[0]:
                cur = st.session_state.get("controlling_power_filter", "")
                snap_val = snap.get("controlling_power", "")
                opts, idx = build_stable_options(controlling_powers, cur, snap_val)
                controlling_power = st.selectbox("Controlling Power", opts, index=idx, key="controlling_power_filter")
            with p_cols[1]:
                cur = st.session_state.get("power_filter", "")
                snap_val = snap.get("power", "")
                opts, idx = build_stable_options(powers, cur, snap_val)
                power = st.selectbox("Power", opts, index=idx, key="power_filter")
            with p_cols[2]:
                powerplay_state = st.selectbox(
                    "Powerplay State",
                    [""] + ["Unoccupied", "Fortified", "Exploited", "Stronghold"],
                    key="powerplay_state_filter"
                )

        # =========================
        # Parameter zusammenstellen
        # =========================
        params = {}
        if faction: params["faction"] = faction
        if controlling_faction: params["controlling_faction"] = controlling_faction
        if controlling_power: params["controlling_power"] = controlling_power
        if power: params["power"] = power
        if powerplay_state: params["powerplay_state"] = powerplay_state
        if state: params["state"] = state
        if government: params["government"] = government
        if pending_state: params["pending_state"] = pending_state
        if recovering_state: params["recovering_state"] = recovering_state
        if has_conflict: params["has_conflict"] = "true"
        if controlling_faction_in_conflict: params["cf_in_conflict"] = "true"

        pop_param = build_population_param(pop_min, pop_max)
        if pop_param: params["population"] = pop_param

        # Buttons kompakt nebeneinander
        st.markdown('<div class="btn-row">', unsafe_allow_html=True)
        bcol1, bcol2 = st.columns([1, 1])
        with bcol1:
            submitted = st.form_submit_button("Search")
        with bcol2:
            # Hinweis: Reset-Button bleibt außerhalb der Form funktionsgleich – hier nur Dummy-Info
            st.caption("Use **Reset** below to clear all filters.")
        st.markdown('</div>', unsafe_allow_html=True)

        # Validierungen/Submit Handling wie gehabt
        if submitted:
            if controlling_faction_in_conflict and not controlling_faction:
                st.error('Bitte wähle eine **Controlling Faction**, wenn du "Controlling Faction in conflict" aktivierst.')
            elif (pop_min is not None and pop_max is not None) and (pop_min > pop_max):
                st.error("Population range is invalid: Min must not be greater than Max.")
            else:
                st.session_state.system_name_snapshot = st.session_state.get("system_name_filter", "")
                st.session_state.params_snapshot = params
                st.session_state.run_search = True
                st.rerun()

    # Reset-Button: Nur Flag setzen und rerun -> Keys werden oben zurückgesetzt
    if st.button("Reset"):
        st.session_state._do_reset = True
        st.rerun()

    # Gate: Ohne Search-Klick nichts laden
    if not st.session_state.run_search:
        st.info("Setze Filter und klicke **Search**, um Daten zu laden.")
        return

    # Snapshots für die Suche
    system_name = st.session_state.system_name_snapshot
    params = st.session_state.params_snapshot

    # <<< NEW: now catch empty search case first >>>
    if not system_name and not {k: v for k, v in params.items() if v not in ("", None)}:
        st.warning("Please enter a system name or at least one filter.")
        return
    st.markdown(f"Results for System: **{system_name or '*'}'** with Filters: `{params}`")

    # --- Fetch data (only /system-summary; safely parse 400-body) ---
    try:
        path = f"system-summary/{quote(system_name, safe='')}" if system_name else "system-summary"
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

        # Anzahl der Conflicts bestimmen
        conflicts = entry.get("conflicts", []) or []
        conflict_count = len(conflicts)

        # Header-Chips (inkl. Government/Security Mapping und Conflict-Chip)
        #render_header_chips(sysinfo, pp0, conflict_count)
        render_grouped_header(sysinfo, pp0, conflict_count)

        # Buttons CMDR Events / System Activities / Faction Activities
        c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1, 1, 1, 1])

        clicked = {
            "cmdr_ct": c1.button("CMDR Events (CT)", key=f"cmdr_ct_{sys_name}"),
            "cmdr_lt": c2.button("CMDR Events (LT)", key=f"cmdr_lt_{sys_name}"),
            "sys_ct": c3.button("System Activities (CT)", key=f"sys_ct_{sys_name}"),
            "sys_lt": c4.button("System Activities (LT)", key=f"sys_lt_{sys_name}"),
            "fac_ct": c5.button("Faction Activities (CT)", key=f"fac_ct_{sys_name}"),
            "fac_lt": c6.button("Faction Activities (LT)", key=f"fac_lt_{sys_name}"),
        }

        # CMDR Events
        if clicked["cmdr_ct"] or clicked["cmdr_lt"]:
            period = "ct" if clicked["cmdr_ct"] else "lt"
            results = fetch_all_cmdr_summaries(sys_name, period)
            render_cmdr_events_block(sys_name, period, results)

        # System Activities
        if clicked["sys_ct"] or clicked["sys_lt"]:
            period = "ct" if clicked["sys_ct"] else "lt"
            rows = fetch_system_activities(sys_name, period)
            with st.expander(f"🛰️ System Activities — {sys_name} [{period.upper()}]", expanded=True):
                render_system_activities_table(rows)

        # Faction Activities
        if clicked["fac_ct"] or clicked["fac_lt"]:
            period = "ct" if clicked["fac_ct"] else "lt"
            rows = fetch_faction_activities(sys_name, period)
            with st.expander(f"🏳️ Faction Activities — {sys_name} [{period.upper()}]", expanded=True):
                render_faction_activities_table(rows)

        # --- Minor Factions ---
        minor_factions = entry.get("factions") or entry.get("minor_factions") or []
        with st.expander("📊 Minor Factions", expanded=False):
            render_minor_factions_table(minor_factions)

        # --- Conflicts ---
        conflicts = entry.get("conflicts", []) or []
        with st.expander("⚔️ Conflicts", expanded=False):
            if conflicts:
                render_conflicts_table(conflicts)
            else:
                st.info("No conflicts found.")

        st.markdown("---")
