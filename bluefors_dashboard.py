"""
Dilution Refrigerator — Bluefors-style Flow Schematic
Interactive, object-oriented dashboard built with Streamlit + Matplotlib.

Run with:
    pip install -r requirements.txt
    streamlit run dr_flow_dashboard.py
"""
import io
import streamlit as st
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["figure.dpi"] = 300
matplotlib.rcParams["savefig.dpi"] = 300
matplotlib.rcParams["lines.antialiased"] = True
matplotlib.rcParams["patch.antialiased"] = True
matplotlib.rcParams["text.antialiased"] = True
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, Arc, Polygon, PathPatch
from matplotlib.path import Path
from dataclasses import dataclass, field

# =====================================================================
# THEME 
# =====================================================================
BG          = "#FFFFFF"
INK         = "#101418"
MUTED       = "#5B6672"
MUTED2      = "#8B95A1"
LINE_IDLE   = "#101418"
FLOW        = "#1E6FE0"
VALVE_OPEN  = "#1E6FE0"
VALVE_SHUT  = "#EDEFF2"
KNOB_FACE   = "#F3F4F6"
PANEL_BAR   = "#0C0F13"
MONO        = "monospace"
CANVAS_W, CANVAS_H = 1350, 1050

# =====================================================================
# OBJECT MODEL
# =====================================================================

@dataclass
class Gauge:
    id: str
    label: str
    cx: float; cy: float
    value: str = "0.00"
    unit: str = ""


@dataclass
class FlowBox:
    """The 'FLOW  0.00  mmol/s' readout — distinct from P1-P6 pressure gauges."""
    cx: float; cy: float
    value: str = "0.00"
    unit: str = "mmol/s"


@dataclass
class Panel:
    """Front-panel style button (Pulse Tube / heat-switch panel / EXT)."""
    id: str
    label: str
    x: float; y: float; w: float; h: float
    on: bool = False

    def toggle(self):
        self.on = not self.on


@dataclass
class Vessel:
    id: str
    label: str
    x: float; y: float; w: float; h: float
    label_outside: bool = False    # True: draw label above the box instead of centered inside it
    level: float = None            # 0.0-1.0 fill fraction to render as a liquid level; None = no fill drawn


@dataclass
class Pump:
    id: str
    label: str
    cx: float; cy: float; r: float
    kind: str                      # "turbo" | "scroll" | "compressor"
    on: bool = False

    def toggle(self):
        self.on = not self.on


@dataclass
class Valve:
    id: str
    label: str                     # extra annotation, e.g. "(GATE)", "AUX", "VENT"
    cx: float; cy: float
    rotation: float = 0
    small: bool = False            # True for the manual bypass valves (BPV1-3, TEST, MV1, TANK_V)
    show_id: bool = True           # False for MV1
    open: bool = False

    def toggle(self):
        self.open = not self.open


@dataclass
class Pipe:
    id: str
    label: str
    points: list
    state: str = "off"             # "off" | "forward" | "reverse"

    def cycle(self):
        self.state = {"off": "forward", "forward": "reverse", "reverse": "off"}[self.state]


# =====================================================================
# LAYOUT  (coordinates on a 1350 x 1050 canvas, y grows downward)
# =====================================================================

JUNCTIONS = [
    (560, 230), (650, 195), (1010, 140), (1010, 190), (1180, 190),
    (1010, 325), (1180, 325), (1010, 710), (1010, 680),
    (790, 760), (790, 840), (1060, 930), (1220, 930), (150, 800),
    (300, 230), (650, 230), (830, 470), (1010, 470), (1010, 760),
    (1010, 930), (500, 700), (650, 700), (150, 700), (300, 700), (400, 700),
]

# =====================================================================
# LABEL PLACEMENT 
# -----------------------------------------------------------------------

DIR_ALIGN = {
    "up":          dict(ha="center", va="bottom"),
    "down":        dict(ha="center", va="top"),
    "left":        dict(ha="right",  va="center"),
    "right":       dict(ha="left",   va="center"),
    "upper_right": dict(ha="left",   va="bottom"),
    "upper_left":  dict(ha="right",  va="bottom"),
    "lower_right": dict(ha="left",   va="top"),
    "lower_left":  dict(ha="right",  va="top"),
}

# (x, y, direction) — direction only used to pick ha/va above. The
# search also treats every other label's box as an obstacle once it's
# placed (pumps first, then valve IDs, then valve annotations), so two
# labels never land on top of each other either.

VALVE_ID_POS = {
    "V1": (626.2, 206.2, "upper_left"), "V2": (760.0, 263.0, "down"),
    "V3": (853.8, 306.2, "upper_right"), "V4": (1033.8, 226.2, "upper_right"),
    "V5": (1105.0, 157.4, "up"), "V6": (1105.0, 292.4, "up"),
    "V7": (1133.8, 486.2, "upper_right"), "V8": (1033.8, 526.2, "upper_right"),
    "V9": (1133.8, 636.2, "upper_right"), "V10": (704.7, 734.7, "upper_left"),
    "V11": (825.3, 904.7, "upper_right"), "V12": (900.0, 873.0, "down"),
    "V13": (976.3, 800.0, "left"), "V14": (325.3, 154.7, "upper_right"),
    "V15": (500.0, 197.4, "up"), "V16": (325.3, 594.7, "upper_right"),
    "V17": (525.3, 594.7, "upper_right"), "V18": (600.0, 667.4, "up"),
    "V19": (525.3, 734.7, "upper_right"), "V20": (425.3, 734.7, "upper_right"),
    "V21": (175.3, 734.7, "upper_right"), "V22": (325.3, 734.7, "upper_right"),
    "V23": (220.0, 790.0, "up"), "TEST": (270.0, 305.4, "up"),
    "BPV1": (1275.7, 236.3, "upper_right"), "BPV2": (800.0, 625.4, "up"),
    "BPV3": (1080.7, 779.3, "upper_right"), "TANK_V": (1251.3, 875.0, "right"),
}

VALVE_LABEL_POS = {
    # Only V1 carries an annotation ("(GATE)"); every other valve.label
    # is "" so nothing else needs a position here.
    "V1": (678.6, 258.6, "lower_right"),
}

PUMP_LABEL_POS = {
    "COM": (1215.9, 292.9, "lower_right"), "TURBO1": (696.3, 396.3, "lower_right"),
    "SCROLL1": (855.3, 715.3, "upper_left"), "TURBO2": (344.8, 894.8, "lower_right"),
    "SCROLL2": (106.8, 893.2, "lower_left"),
}


def build_diagram():
    panels = {
        "PULSE_TUBE": Panel("PULSE_TUBE", "PULSE TUBE", 20, 34,  75, 80),
        "HS_STILL":   Panel("HS_STILL",   "HS-STILL",   20, 124, 75, 80),
        "HS_MC":      Panel("HS_MC",      "HS-MC",      20, 214, 75, 80),
        "EXT":        Panel("EXT",        "EXT",        20, 304, 75, 80),
    }

    vessels = {
        "TRAP": Vessel("TRAP", "TRAP", 1080, 570, 60, 45),
        "TANK": Vessel("TANK", "MIXTURE TANK", 1180, 700, 80, 150, label_outside=True, level=1.0),
    }

    gauges = {
        "P1": Gauge("P1", "P1", 180,  140, ""),
        "P2": Gauge("P2", "P2", 460,  140, "8.60E-1"),
        "P3": Gauge("P3", "P3", 910,  140, "6.14E+0"),
        "P4": Gauge("P4", "P4", 905,  615, "1.64E+2"),
        "P5": Gauge("P5", "P5", 1100, 985, "8.11E+2"),
        "P6": Gauge("P6", "P6", 30,   700, "5.08E-1"),
    }

    flow_box = FlowBox(1010, 402, "0.00")

    pumps = {
        "COM":     Pump("COM",     "COM.",       1180, 257, 37, "compressor"),
        "TURBO1":  Pump("TURBO1",  "TURBO 1",     650, 350, 45, "turbo"),
        "SCROLL1": Pump("SCROLL1", "SCROLL 1",    900, 760, 41, "scroll"),
        "TURBO2":  Pump("TURBO2",  "TURBO 2",     300, 850, 43, "turbo"),
        "SCROLL2": Pump("SCROLL2", "SCROLL 2",    150, 850, 39, "scroll"),
    }

    valves = {
        "V1":   Valve("V1",   "(GATE)",   650,  230),
        "V2":   Valve("V2",   "",         760,  230),
        "V3":   Valve("V3",   "",         830,  330),
        "V4":   Valve("V4",   "",        1010,  250),
        "V5":   Valve("V5",   "",        1105,  190),
        "V6":   Valve("V6",   "",        1105,  325),
        "V7":   Valve("V7",   "",        1110,  510),
        "V8":   Valve("V8",   "",        1010,  550),
        "V9":   Valve("V9",   "",        1110,  660),
        "V10":  Valve("V10",  "",         730,  760),
        "V11":  Valve("V11",  "",         800,  930),
        "V12":  Valve("V12",  "",         900,  840),
        "V13":  Valve("V13",  "",        1010,  800),
        "V14":  Valve("V14",  "",         300,  180),
        "V15":  Valve("V15",  "",         500,  230),
        "V16":  Valve("V16",  "",         300,  620),
        "V17":  Valve("V17",  "",         500,  620),
        "V18":  Valve("V18",  "",         600,  700),
        "V19":  Valve("V19",  "",         500,  760),
        "V20":  Valve("V20",  "",         400,  760),
        "V21":  Valve("V21",  "",         150,  760),
        "V22":  Valve("V22",  "",         300,  760),
        "V23":  Valve("V23",  "",         220,  850),
        "TEST": Valve("TEST", "",         270,  330, small=True),
        "BPV1": Valve("BPV1", "",        1255,  257, small=True),
        "BPV2": Valve("BPV2", "",         800,  650, small=True),
        "BPV3": Valve("BPV3", "",        1060,  800, small=True),
        "MV1":  Valve("MV1",  "",         834,  840, small=True, show_id=False),
        "TANK_V": Valve("TANK_V", "",    1220,  875, rotation=90, small=True),
    }

    pipes = {
        # --- LEFT / VACUUM CAN ---
        "VACCAN_TOP":     Pipe("VACCAN_TOP",     "Vacuum can top",        [(300, 80), (300, 158)]),
        "P1_TAP":         Pipe("P1_TAP",         "P1 tap",                [(188, 140), (300, 140)]),
        "V14_DOWN":       Pipe("V14_DOWN",       "V14 down to TEST tee",  [(300, 202), (300, 330)]),
        "TEST_BRANCH":    Pipe("TEST_BRANCH",    "TEST branch",           [(300, 330), (250, 330)]),
        "V14_TO_V16":     Pipe("V14_TO_V16",     "TEST tee down to V16",  [(300, 330), (300, 598)]),
        "V14_TO_V15":     Pipe("V14_TO_V15",     "V14 to V15",            [(300, 202), (300, 230), (478, 230)]),
        "V15_TO_MAIN":    Pipe("V15_TO_MAIN",    "V15 to main node",      [(522, 230), (650, 230)]),
        "P2_TAP":         Pipe("P2_TAP",         "P2 tap",                [(560, 230), (560, 140), (460, 140)]),

        # --- V1 / V2 / V3 / TURBO1 ---
        "STILL_TO_V1":    Pipe("STILL_TO_V1",    "Still line to V1",      [(650, 80), (650, 208)]),
        "V1_TO_MAIN":     Pipe("V1_TO_MAIN",     "V1 bottom to main node",[(650, 252), (650, 230)]),
        "V1_TO_V2":       Pipe("V1_TO_V2",       "V1 to V2",              [(650, 230), (738, 230)]),
        "V2_TO_V3":       Pipe("V2_TO_V3",       "V2 down to V3",         [(782, 230), (830, 230), (830, 308)]),
        "V1_V2_BYPASS":   Pipe("V1_V2_BYPASS",   "V1/V2 bypass",          [(650, 195), (830, 195), (830, 230)]),
        "V3_TO_MAINLINE": Pipe("V3_TO_MAINLINE", "V3 to main line",       [(830, 352), (830, 470), (1010, 470)]),
        "TURBO1_INTAKE":  Pipe("TURBO1_INTAKE",  "Turbo 1 intake",        [(650, 252), (650, 318)]),
        "TURBO1_EXHAUST": Pipe("TURBO1_EXHAUST", "Turbo 1 exhaust (upper)", [(650, 382), (650, 470)]),
        "MAIN_OVERPASS":  Pipe("MAIN_OVERPASS",  "Main line overpass",    [(500, 470), (1010, 470)]),

        # --- 3-He / V4 / FLOW / COM ---
        "HE3_IN":         Pipe("HE3_IN",         "3-He in",               [(1010, 80), (1010, 228)]),
        "P3_TAP":         Pipe("P3_TAP",         "P3 tap",                [(1010, 140), (948, 140)]),
        "V4_TO_FLOW":     Pipe("V4_TO_FLOW",     "V4 to flow to main",    [(1010, 272), (1010, 470)]),
        "V5_TAP":         Pipe("V5_TAP",         "V5 tap",                [(1010, 190), (1083, 190)]),
        "V5_BPV1_TOP":    Pipe("V5_BPV1_TOP",    "V5 to BPV1 (top)",      [(1127, 190), (1180, 190)]),
        "V5COM_TOP_DOWN": Pipe("V5COM_TOP_DOWN", "V5/COM top node to COM",[(1180, 190), (1180, 222)]),
        "V6_TAP":         Pipe("V6_TAP",         "V6 tap",                [(1010, 325), (1083, 325)]),
        "V6_BPV1_BOTTOM": Pipe("V6_BPV1_BOTTOM", "V6 to BPV1 (bottom)",   [(1127, 325), (1180, 325)]),
        "COM_BOTTOM_NODE":Pipe("COM_BOTTOM_NODE","COM bottom to node",    [(1180, 292), (1180, 325)]),
        "BPV1_BYPASS":    Pipe("BPV1_BYPASS",    "BPV1 bypass around COM",[(1180, 190), (1255, 190), (1255, 325), (1180, 325)]),

        # --- MAIN / TRAP / V7 / V8 / V9 ---
        "MAIN_FROM_FLOW": Pipe("MAIN_FROM_FLOW", "Main line from flow",   [(1010, 470), (1010, 488)]),
        "V7_TO_TRAP_TAP": Pipe("V7_TO_TRAP_TAP", "V7 branch to trap",     [(1010, 470), (1110, 470), (1110, 488)]),
        "V7_DOWN_TO_TRAP":Pipe("V7_DOWN_TO_TRAP","V7 down to trap",       [(1110, 532), (1110, 570)]),
        "TRAP_TO_V9":     Pipe("TRAP_TO_V9",     "Trap to V9",            [(1110, 615), (1110, 638)]),
        "V9_TO_MAIN":     Pipe("V9_TO_MAIN",     "V9 to main node",       [(1110, 682), (1110, 710), (1010, 710)]),
        "V8_GAP_PLAIN":   Pipe("V8_GAP_PLAIN",   "Plain run above V8",    [(1010, 488), (1010, 500)]),
        "V8_MAIN_PATH":   Pipe("V8_MAIN_PATH",   "V8 main path",          [(1010, 500), (1010, 525)]),
        "V8_DOWN_CONT":   Pipe("V8_DOWN_CONT",   "V8 down, continuing",   [(1010, 575), (1010, 760)]),
        "P4_TAP":         Pipe("P4_TAP",         "P4 tap",                [(1010, 615), (905, 615)]),

        # --- BACKING MANIFOLD ---
        "V16_TO_MANIFOLD":Pipe("V16_TO_MANIFOLD","V16 to backing manifold", [(300, 642), (300, 700)]),
        "BACKING_MANIFOLD":Pipe("BACKING_MANIFOLD","Main backing manifold", [(100, 700), (600, 700)]),
        "P6_TAP":         Pipe("P6_TAP",         "P6 tap",                [(100, 700), (68, 700)]),
        "V17_UPPER_BRANCH":Pipe("V17_UPPER_BRANCH","V17 branch from upper main", [(500, 470), (500, 598)]),
        "V17_TO_MANIFOLD":Pipe("V17_TO_MANIFOLD","V17 to backing manifold", [(500, 642), (500, 700)]),
        "V19_UP":         Pipe("V19_UP",         "V19 up branch",         [(500, 700), (500, 738)]),
        "V19_DOWN":       Pipe("V19_DOWN",       "V19 down branch",       [(500, 782), (500, 840)]),
        "V20_UP":         Pipe("V20_UP",         "V20 up branch",         [(400, 700), (400, 738)]),
        "V20_DOWN":       Pipe("V20_DOWN",       "V20 down branch",       [(400, 782), (400, 840)]),
        "V21_UP":         Pipe("V21_UP",         "V21 up branch",         [(150, 700), (150, 738)]),
        "V22_UP":         Pipe("V22_UP",         "V22 up branch",         [(300, 700), (300, 738)]),

        # --- TURBO 1 EXHAUST / V18 ---
        "TURBO1_EXH_DOWN":Pipe("TURBO1_EXH_DOWN","Turbo 1 exhaust down",  [(650, 382), (650, 700)]),
        "MANIFOLD_TO_V18":Pipe("MANIFOLD_TO_V18","Manifold enters V18",   [(600, 700), (578, 700)]),
        "V18_TO_EXH_NODE":Pipe("V18_TO_EXH_NODE","V18 to exhaust node",   [(622, 700), (650, 700)]),
        "EXH_TO_V10":     Pipe("EXH_TO_V10",     "Exhaust to V10",        [(650, 700), (650, 760), (708, 760)]),

        # --- SCROLL 1 ---
        "V10_TO_SCROLL1": Pipe("V10_TO_SCROLL1", "V10 to Scroll 1",       [(752, 760), (868, 760)]),
        "SCROLL1_TO_P4N": Pipe("SCROLL1_TO_P4N", "Scroll 1 outlet to P4 node", [(932, 760), (1010, 760)]),
        "BPV2_UPPER":     Pipe("BPV2_UPPER",     "BPV2 bypass (upper)",   [(650, 700), (650, 650), (778, 650)]),
        "BPV2_LOWER":     Pipe("BPV2_LOWER",     "BPV2 bypass (lower)",   [(822, 650), (960, 650), (960, 760)]),

        # --- Lower bypass network ---
        "TAP_TO_V11":     Pipe("TAP_TO_V11",     "Tap down to V11",       [(790, 760), (790, 930)]),
        "V11_LEFT":       Pipe("V11_LEFT",       "V11 left stub",         [(790, 930), (778, 930)]),
        "V11_TO_MAIN":    Pipe("V11_TO_MAIN",    "V11 to main run",       [(822, 930), (1010, 930)]),
        "TAP_TO_MV1":     Pipe("TAP_TO_MV1",     "Tap to MV1 (left)",     [(790, 840), (816, 840)]),
        "MV1_TO_V12":     Pipe("MV1_TO_V12",     "MV1 to V12",            [(852, 840), (878, 840)]),
        "V12_TO_MAIN":    Pipe("V12_TO_MAIN",    "V12 to main run",       [(922, 840), (1010, 840)]),
        "SCROLL1_V13_TEE":Pipe("SCROLL1_V13_TEE","Scroll1 tee down to V13", [(1010, 760), (1010, 778)]),
        "V13_DOWN":       Pipe("V13_DOWN",       "V13 down",              [(1010, 822), (1010, 930)]),

        # --- BPV3 / MIXTURE TANK ---
        "RUN_TO_TANKLINE":Pipe("RUN_TO_TANKLINE","V11/V12 run to tank line", [(1010, 930), (1220, 930)]),
        "SCROLL1_BPV3_TEE":Pipe("SCROLL1_BPV3_TEE","Scroll1 tee to BPV3", [(1010, 760), (1060, 760)]),
        "BPV3_TEE_DOWN":  Pipe("BPV3_TEE_DOWN",  "BPV3 tee down",         [(1060, 760), (1060, 778)]),
        "BPV3_DOWN_RUN":  Pipe("BPV3_DOWN_RUN",  "BPV3 down to run",      [(1060, 822), (1060, 930)]),
        "P5_TAP":         Pipe("P5_TAP",         "P5 tap",                [(1138, 985), (1220, 985), (1220, 930)]),
        "TANKLINE_TO_TANK":Pipe("TANKLINE_TO_TANK","Tank line up to tank", [(1220, 930), (1220, 850)]),
        "TANK_OUTLET_DOWN":Pipe("TANK_OUTLET_DOWN","Tank outlet down",    [(1220, 900), (1220, 930)]),

        # --- TURBO 2 / SCROLL 2 ---
        "V21_TO_SCROLL2": Pipe("V21_TO_SCROLL2", "V21 to Scroll 2",       [(150, 782), (150, 818)]),
        "SCROLL2_EXHAUST":Pipe("SCROLL2_EXHAUST","Scroll 2 exhaust",      [(150, 882), (150, 970)]),
        "SCROLL2_TAP_V23":Pipe("SCROLL2_TAP_V23","Scroll2 tap to V23",    [(150, 800), (220, 800), (220, 828)]),
        "V22_TO_TURBO2":  Pipe("V22_TO_TURBO2",  "V22 to Turbo 2",        [(300, 782), (300, 818)]),
        "TURBO2_EXH_V23": Pipe("TURBO2_EXH_V23", "Turbo2 exhaust to V23", [(300, 882), (300, 930), (220, 930), (220, 872)]),
    }
    return panels, vessels, gauges, pumps, valves, pipes, flow_box


# =====================================================================
# SOP
# =====================================================================

SOP_STEPS = [
    # ============== Section 1.1-1.2: Checks & Retrieve Residual Mixture ==============
    {
        "name": "1.1  System checks before cooling down",
        "note": "SOP §1.1. Ideally done while preparing devices for cool-down. Check cooling "
                "water is filled, cold trap is clean enough, and no screws or tools are left "
                "inside the fridge. Check that all required heaters and sensors are set "
                "appropriately and functioning. Close the cans with seams matching — o-rings "
                "and o-ring surfaces must be clean and greased, especially with no hair; use "
                "about half a pea size of grease.",
        "valves": {}, "pumps": {}, "panels": {}, "pipes": {},
        "gauges": {"P1": "", "P2": "8.60E-1", "P3": "6.14E+0", "P4": "1.64E+2",
                   "P5": "8.11E+2", "P6": "5.08E-1"},
        "flow": "0.00",
    },
    {
        "name": "1.2 steps 1-2  Retrieve residual mixture — circulate",
        "note": "SOP §1.2. Motivation: retrieve any residual mixture that accumulated in the "
                "circulation line — if skipped, this leads to mixture loss over time. Make sure "
                "all valves are closed, especially the manual (tank) valve. Turn on Scroll1, "
                "open V13 and V10, open V2 to equalize the pressure over V1. Wait a while, then "
                "open V1, V3 and V4.",
        "valves": {"V13": True, "V10": True, "V2": True, "V1": True, "V3": True, "V4": True},
        "pumps": {"SCROLL1": True},
        "panels": {},
        "pipes": {"V1_TO_MAIN": "forward", "V1_TO_V2": "forward", "V2_TO_V3": "forward",
                  "V3_TO_MAINLINE": "forward", "V4_TO_FLOW": "forward", "MAIN_OVERPASS": "forward",
                  "TURBO1_EXH_DOWN": "forward", "EXH_TO_V10": "forward",
                  "V10_TO_SCROLL1": "forward", "SCROLL1_TO_P4N": "forward",
                  "SCROLL1_V13_TEE": "forward", "V13_DOWN": "forward"},
        "gauges": {"P2": "6.20E-1", "P3": "5.40E-1"},
        "flow": "0.00",
    },
    {
        "name": "1.2 steps 3-5  Stabilize & isolate progressively",
        "note": "SOP §1.2 steps 3-5. Continue until pressures stabilize: P3 should read ~0, P2 "
                "in the low e-2 to e-3 mbar range, and P4/P5 around 760-770 mbar (~30-60 min). "
                "Then close V4, V3, V1, V2, V10, Scroll1 and V13 in that order, pumping "
                "progressively smaller sections — note the values in the cool-down notes on "
                "Notion. If planning to clean the cold trap, see SOP §3.2 for additional steps "
                "first.",
        "valves": {}, "pumps": {}, "panels": {}, "pipes": {},
        "gauges": {"P2": "4.50E-2", "P3": "0.00E+0", "P4": "7.65E+2", "P5": "7.62E+2"},
        "flow": "0.00",
    },

    # ==================== Section 1.3: Evacuate DU and the lines ====================
    {
        "name": "1.3 step 1  Evacuate service manifold",
        "note": "SOP §1.3 step 1. Start Scroll2, wait 10 s for the internal relay to switch, "
                "then open V21 to evacuate the service manifold.",
        "valves": {"V21": True},
        "pumps": {"SCROLL2": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward",
                  "BACKING_MANIFOLD": "forward", "P6_TAP": "forward"},
        "gauges": {"P6": "7.60E+2"},
        "flow": "0.00",
    },
    {
        "name": "1.3 steps 2-3  Equalize & open gate valve V1",
        "note": "SOP §1.3 steps 2-3. Open V2 to equalize the pressure over gate valve V1. "
                "CAUTION: gate valve V1 must NOT be operated when the pressure difference "
                "is >30 mbar — this can result in damage. Wait a few seconds for the pressure "
                "to equalize, then open gate valve V1 and close V2.",
        "valves": {"V21": True, "V2": True, "V1": True},
        "pumps": {"SCROLL2": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "V1_TO_MAIN": "forward", "V1_TO_V2": "forward", "P2_TAP": "forward"},
        "gauges": {"P6": "4.10E+1"},
        "flow": "0.00",
    },
    {
        "name": "1.3 step 4  Connect condensing & pumping sides",
        "note": "SOP §1.3 step 4. Open V3 and V4 to connect the condensing and pumping side of "
                "the dilution unit (DU).",
        "valves": {"V21": True, "V2": True, "V1": True, "V3": True, "V4": True},
        "pumps": {"SCROLL2": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "V1_TO_MAIN": "forward", "V1_TO_V2": "forward", "P2_TAP": "forward",
                  "V2_TO_V3": "forward", "V3_TO_MAINLINE": "forward", "V4_TO_FLOW": "forward"},
        "gauges": {"P6": "6.30E+0"},
        "flow": "0.00",
    },
    {
        "name": "1.3 steps 5-7  Evacuate DU with Turbo1",
        "note": "SOP §1.3 steps 5-7. Open V18 to connect the service manifold with the DU "
                "circulation circuit, evacuating the dilution unit. Wait for P6 < 1 mbar, then "
                "start Turbo1. Pump for 15 minutes to an hour.",
        "valves": {"V21": True, "V1": True, "V3": True, "V4": True, "V18": True},
        "pumps": {"SCROLL2": True, "TURBO1": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "MANIFOLD_TO_V18": "forward", "V18_TO_EXH_NODE": "forward", "EXH_TO_V10": "forward",
                  "TURBO1_INTAKE": "forward", "TURBO1_EXHAUST": "forward",
                  "V1_TO_MAIN": "forward", "V3_TO_MAINLINE": "forward", "V4_TO_FLOW": "forward"},
        "gauges": {"P6": "6.20E-2"},
        "flow": "0.00",
    },
    {
        "name": "1.3 step 8  Close all valves and pumps",
        "note": "SOP §1.3 step 8. Close all valves and switch off all pumps.",
        "valves": {}, "pumps": {}, "panels": {}, "pipes": {},
        "gauges": {"P6": "6.20E-2"},
        "flow": "0.00",
    },
    {
        "name": "1.3 step 9  Open manual valve to the tank",
        "note": "SOP §1.3 step 9. Open the manual valve to the tank.",
        "valves": {"TANK_V": True},
        "pumps": {}, "panels": {}, "pipes": {},
        "gauges": {"P6": "6.20E-2"},
        "flow": "0.00",
    },
    {
        "name": "1.3 steps 10-11  Check P4 in Cooldown database",
        "note": "SOP §1.3 steps 10-11. Make sure V10, V8 and V9 are off. Open Scroll 1 and V13, "
                "wait 10 sec, and check P4 — it should read 760 ± 5 mbar. Note down P4 and P5 in "
                "the Cooldown database, then close V13 and turn off Scroll 1.",
        "valves": {"TANK_V": True, "V13": True},
        "pumps": {"SCROLL1": True},
        "panels": {},
        "pipes": {"SCROLL1_V13_TEE": "forward", "V13_DOWN": "forward",
                  "RUN_TO_TANKLINE": "forward", "TANKLINE_TO_TANK": "forward",
                  "TANK_OUTLET_DOWN": "forward"},
        "gauges": {"P4": "7.60E+2", "P5": "7.61E+2"},
        "flow": "0.00",
    },

    # ========================= Section 1.4: Evacuate vacuum can =========================
    {
        "name": "1.4 steps 1-3  Rough pump VC",
        "note": "SOP §1.4. Goal: evacuate the vacuum can (VC) until P1 ≲ 2×10⁻³ mbar "
                "(typically ~1.5 hrs). The wing nuts will become loose once the VC is under "
                "vacuum — do NOT retighten them. Switch on Scroll2, wait 10 s for the internal "
                "relay, then open V21, V16 and V14 to rough-pump the VC. Turn on the P1 gauge "
                "once P6 < 1 mbar (after ~15 min).",
        "valves": {"V21": True, "V16": True, "V14": True},
        "pumps": {"SCROLL2": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "V16_TO_MANIFOLD": "forward", "VACCAN_TOP": "forward", "V14_TO_V16": "forward"},
        "gauges": {"P1": "3.20E+1"},
        "flow": "0.00",
    },
    {
        "name": "1.4 steps 4-5  Switch to Turbo1",
        "note": "SOP §1.4 steps 4-5. Close V16; open V18 and V15; switch on Turbo1. Pump until "
                "P1 ≲ 2×10⁻³ mbar (~1-2 hrs).",
        "valves": {"V21": True, "V14": True, "V18": True, "V15": True},
        "pumps": {"SCROLL2": True, "TURBO1": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "VACCAN_TOP": "forward", "V14_TO_V15": "forward", "V15_TO_MAIN": "forward",
                  "TURBO1_INTAKE": "forward", "TURBO1_EXHAUST": "forward",
                  "MAIN_OVERPASS": "forward", "TURBO1_EXH_DOWN": "forward",
                  "MANIFOLD_TO_V18": "forward", "V18_TO_EXH_NODE": "forward"},
        "gauges": {"P1": "8.70E-4"},
        "flow": "0.00",
    },
    {
        "name": "1.4 step 6  Leak check",
        "note": "SOP §1.4 step 6. Leak-check if anything on top of the fridge changed.",
        "valves": {"V21": True, "V14": True, "V18": True, "V15": True},
        "pumps": {"SCROLL2": True, "TURBO1": True},
        "panels": {},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "VACCAN_TOP": "forward", "V14_TO_V15": "forward", "V15_TO_MAIN": "forward",
                  "TURBO1_INTAKE": "forward", "TURBO1_EXHAUST": "forward",
                  "MAIN_OVERPASS": "forward", "TURBO1_EXH_DOWN": "forward",
                  "MANIFOLD_TO_V18": "forward", "V18_TO_EXH_NODE": "forward"},
        "gauges": {"P1": "2.00E-3"},
        "flow": "0.00",
    },

    # ======================= Section 1.5: Precool with Pulse Tube =======================
    {
        "name": "1.5 steps 1-2  Start pulse tube & heat switches",
        "note": "SOP §1.5. Goal: precool the system (4K, still and MXC stages) to below 4 K "
                "(~24 hrs) — or to 15 K if starting the Pulse Pre-Cool script afterwards. Make "
                "sure the Bluefors temperature controller, reader and logging are running. Set "
                "the Still Heater power to 6 mW and Relay Mode to SHORT (0 in the "
                "configuration — heater OFF); the panel shows grey with a blue toggle, "
                "switchable from software. Turn on the Pulse Tube and the two Heat Switches "
                "(HS-Still, HS-MC); monitor for 10-15 min — compressor output water should "
                "stay ≤40°C, current around 11-14 A.",
        "valves": {"V21": True, "V14": True, "V18": True, "V15": True},
        "pumps": {"SCROLL2": True, "TURBO1": True},
        "panels": {"PULSE_TUBE": True, "HS_STILL": True, "HS_MC": True},
        "pipes": {"V21_UP": "forward", "V21_TO_SCROLL2": "forward", "BACKING_MANIFOLD": "forward",
                  "VACCAN_TOP": "forward", "V14_TO_V15": "forward", "V15_TO_MAIN": "forward",
                  "TURBO1_INTAKE": "forward", "TURBO1_EXHAUST": "forward",
                  "MAIN_OVERPASS": "forward", "TURBO1_EXH_DOWN": "forward",
                  "MANIFOLD_TO_V18": "forward", "V18_TO_EXH_NODE": "forward"},
        "gauges": {"P1": "4.10E-5"},
        "flow": "0.00",
    },
    {
        "name": "1.5 step 3  Stop OVC pumping below 70 K",
        "note": "SOP §1.5 step 3. Once all flanges are below 70 K (typically ~12 hrs), stop "
                "pumping the outer vacuum can (OVC): close V14 first — always, in case of any "
                "air inside the VC — then V15, V18 and V21. Turn off Scroll2 and Turbo1.",
        "valves": {}, "pumps": {},
        "panels": {"PULSE_TUBE": True, "HS_STILL": True, "HS_MC": True},
        "pipes": {},
        "gauges": {"P1": "1.80E-5"},
        "flow": "0.00",
    },

    # ========================= Section 1.6: Pulse Pre-cooling (optional) =========================
    {
        "name": "1.6  Pulse pre-cooling (optional)",
        "note": "SOP §1.6. Optional step to decrease cooldown time; ideally started once the "
                "4K, still and MXC stages are ≲15 K (typically 1.5-2 hrs) and Turbo1 rotates at "
                "less than 100 Hz. Ensure the manual valve at the tank is open, then start PPC "
                "by running Pulse_Pre_Cool_v1.24.",
        "valves": {"TANK_V": True},
        "pumps": {},
        "panels": {"PULSE_TUBE": True, "HS_STILL": True, "HS_MC": True},
        "pipes": {"TANK_OUTLET_DOWN": "forward"},
        "gauges": {"P1": "1.80E-5"},
        "vessels": {"TANK": 0.95},
        "flow": "0.00",
    },

    # ========================== Section 1.7: Condensing Mixture ==========================
    {
        "name": "1.7 steps 1-2  Begin condensing",
        "note": "SOP §1.7. Requires 4K, still and MXC below 4 K (typically 6 hrs). CRITICAL: "
                "gate valve V1 must be open during normal operation — it's the only way for "
                "the mixture to return to the tank! Ensure the manual valve at the tank is "
                "open, then start condensing by running condense_wLN2_v1_24.",
        "valves": {"TANK_V": True, "V1": True},
        "pumps": {},
        "panels": {"PULSE_TUBE": True, "HS_STILL": True, "HS_MC": True},
        "pipes": {"TANK_OUTLET_DOWN": "forward", "V1_TO_MAIN": "forward"},
        "gauges": {"P1": "1.80E-5", "P5": "3.25E+2"},
        "vessels": {"TANK": 0.55},
        "flow": "0.00",
    },
    {
        "name": "1.7 step 3  Still heater / EXT — normal operation",
        "note": "SOP §1.7 step 3. The still heater should turn on automatically — check the EXT "
                "toggle on the small screen of the Bluefors temperature control unit; it stays "
                "grey until EXT is switched on. If it hasn't come on automatically, turn it on "
                "manually and wait for the base temperature to stabilise before starting "
                "measurements.",
        "valves": {"TANK_V": True, "V1": True, "V4": True, "V7": True, "V9": True,
                    "V10": True, "V13": True},
        "pumps": {"SCROLL1": True, "TURBO1": True},
        "panels": {"PULSE_TUBE": True, "EXT": True},
        "pipes": {"TANK_OUTLET_DOWN": "forward", "TURBO1_INTAKE": "forward",
                  "TURBO1_EXHAUST": "forward", "V1_TO_MAIN": "forward",
                  "HE3_IN": "forward", "V4_TO_FLOW": "forward",
                  "V7_TO_TRAP_TAP": "forward", "V7_DOWN_TO_TRAP": "forward",
                  "TRAP_TO_V9": "forward", "V9_TO_MAIN": "forward",
                  "EXH_TO_V10": "forward", "V10_TO_SCROLL1": "forward",
                  "SCROLL1_TO_P4N": "forward", "SCROLL1_V13_TEE": "forward",
                  "V13_DOWN": "forward", "RUN_TO_TANKLINE": "forward",
                  "TANKLINE_TO_TANK": "forward"},
        "gauges": {"P1": "1.80E-5", "P3": "4.85E+2", "P5": "1.10E+2"},
        "vessels": {"TANK": 0.12},
        "flow": "0.24",
    },
]



def snapshot_from_step(step):
    return {
        "valves": step.get("valves", {}),
        "pumps":  step.get("pumps", {}),
        "panels": step.get("panels", {}),
        "pipes":  step.get("pipes", {}),
        "flow":   step.get("flow", "0.00"),
        "gauges": step.get("gauges", {}),
        "vessels": step.get("vessels", {}),
    }


def apply_snapshot(snap):
    for vid, v in st.session_state.valves.items():
        v.open = snap["valves"].get(vid, False)
    for pid, p in st.session_state.pumps.items():
        p.on = snap["pumps"].get(pid, False)
    for pid, p in st.session_state.panels.items():
        p.on = snap.get("panels", {}).get(pid, False)
    for pid, p in st.session_state.pipes.items():
        p.state = snap["pipes"].get(pid, "off")
    st.session_state.flow_box.value = snap.get("flow", "0.00")
    for gid, g in st.session_state.gauges.items():
        g.value = snap.get("gauges", {}).get(gid, g.value)
    for vid, v in st.session_state.vessels.items():
        v.level = snap.get("vessels", {}).get(vid, v.level)


def init_state():
    if "valves" not in st.session_state:
        panels, vessels, gauges, pumps, valves, pipes, flow_box = build_diagram()
        st.session_state.panels = panels
        st.session_state.vessels = vessels
        st.session_state.gauges = gauges
        st.session_state.pumps = pumps
        st.session_state.valves = valves
        st.session_state.pipes = pipes
        st.session_state.flow_box = flow_box
        st.session_state.sop_index = 0
        apply_snapshot(snapshot_from_step(SOP_STEPS[0]))


# =====================================================================
# RENDERING
# =====================================================================

def valve_radius(small=False):
    """Single source of truth for bowtie-valve circle size, so label
    placement (render_figure) can stay in sync with what's actually drawn."""
    return 17 if small else 25


def draw_bowtie(ax, cx, cy, rotation, open_, small=False):
    r = valve_radius(small)
    s = 0.68 if small else 1.05
    verts = [(-14 * s, -9 * s), (-14 * s, 9 * s), (0, 0),
             (14 * s, 9 * s), (14 * s, -9 * s), (0, 0), (-14 * s, -9 * s)]
    face = KNOB_FACE
    ring = FLOW if open_ else INK
    lw = 2.6 if open_ else 1.5
    body = Circle((cx, cy), r, facecolor=face, edgecolor=ring, linewidth=lw, zorder=4)
    ax.add_patch(body)
    poly = Polygon(verts, closed=True,
                    facecolor=VALVE_OPEN if open_ else "#C7CDD4",
                    edgecolor=INK, linewidth=0.9, zorder=5)
    t = mtransforms.Affine2D().rotate_deg(rotation).translate(cx, cy) + ax.transData
    poly.set_transform(t)
    ax.add_patch(poly)


def draw_panel(ax, p: Panel):
    box = Rectangle((p.x, p.y), p.w, p.h, facecolor="none",
                     edgecolor=INK, linewidth=1.7, zorder=3)
    ax.add_patch(box)
    cx, cy = p.x + p.w / 2, p.y + p.h * 0.38
    ring = FLOW if p.on else INK
    ax.add_patch(Circle((cx, cy), 19, facecolor=KNOB_FACE, edgecolor=ring, linewidth=2.2, zorder=4))
    ax.add_patch(Circle((cx, cy), 9.5, facecolor="#E4E7EB", edgecolor=ring, linewidth=1, zorder=4))
    ax.text(cx, p.y + p.h - 13, p.label, color=INK, family=MONO, fontsize=8,
            weight="bold", ha="center", zorder=4)


def draw_vessel_box(ax, v: Vessel):
    box = FancyBboxPatch((v.x, v.y), v.w, v.h, boxstyle="round,pad=0,rounding_size=7",
                          facecolor="none", edgecolor=INK, linewidth=1.7, zorder=3)
    ax.add_patch(box)

    if v.level is not None:
        level = max(0.0, min(1.0, v.level))
        fill_h = v.h * level
        if fill_h > 0:
            fill = Rectangle((v.x, v.y + v.h - fill_h), v.w, fill_h,
                              facecolor=FLOW, alpha=0.16, edgecolor="none", zorder=2)
            fill.set_clip_path(box)
            ax.add_patch(fill)
            if level < 1.0:
                ax.plot([v.x, v.x + v.w], [v.y + v.h - fill_h] * 2,
                         color=FLOW, lw=1.4, alpha=0.6, zorder=2, solid_capstyle="butt")
        ax.text(v.x + v.w / 2, v.y + v.h / 2, f"{level * 100:.0f}%",
                color=FLOW, family=MONO, fontsize=11, weight="bold",
                ha="center", va="center", zorder=5)

    if v.label_outside:
        ax.text(v.x + v.w / 2, v.y - 8, v.label, color=INK, family=MONO,
                 fontsize=9, weight="bold", ha="center", va="bottom", zorder=4)
    else:
        ax.text(v.x + v.w / 2, v.y + v.h / 2, v.label, color=INK, family=MONO,
                fontsize=9, ha="center", va="center", zorder=4, wrap=True)


def draw_gauge(ax, g: Gauge):
    w, h = 112, 34
    box = FancyBboxPatch((g.cx - w / 2, g.cy - h / 2), w, h,
                          boxstyle="round,pad=0,rounding_size=16",
                          facecolor="white", edgecolor=INK, linewidth=1.4, zorder=4)
    ax.add_patch(box)
    ax.text(g.cx, g.cy, g.value, color=FLOW, family=MONO, fontsize=10.5,
            weight="bold", ha="center", va="center", zorder=5)
    ax.text(g.cx - w / 2, g.cy - h / 2 - 10, g.label, color=INK, family=MONO,
            fontsize=10, weight="bold", ha="left", va="bottom", zorder=5)


def draw_flow_box(ax, f: FlowBox):
    ax.text(f.cx - 100, f.cy, "FLOW", color=INK, family=MONO, fontsize=11,
            weight="bold", ha="left", va="center", zorder=5)
    w, h = 92, 38
    box = Rectangle((f.cx - w / 2, f.cy - h / 2), w, h,
                     facecolor="white", edgecolor=INK, linewidth=1.7, zorder=4)
    ax.add_patch(box)
    ax.text(f.cx, f.cy, f.value, color=FLOW, family=MONO, fontsize=14,
            weight="bold", ha="center", va="center", zorder=5)
    ax.text(f.cx + w / 2 + 12, f.cy, f.unit, color=INK, family=MONO, fontsize=11,
            weight="bold", ha="left", va="center", zorder=5)


def draw_pump(ax, p: Pump):
    color = FLOW if p.on else INK
    lw = 2.8 if p.on else 1.5
    ax.add_patch(Circle((p.cx, p.cy), p.r, facecolor=KNOB_FACE, edgecolor=color, linewidth=lw, zorder=4))
    ax.add_patch(Circle((p.cx, p.cy), p.r * 0.45, facecolor="#E4E7EB", edgecolor=color, linewidth=1, zorder=5))
    if p.kind == "turbo":
        for dx, dy in [(0, 1), (1, 0), (0.7, 0.7), (0.7, -0.7)]:
            ax.plot([p.cx - dx * p.r * 0.8, p.cx + dx * p.r * 0.8],
                     [p.cy - dy * p.r * 0.8, p.cy + dy * p.r * 0.8],
                     color=color, lw=1.7, alpha=0.5, zorder=5)
    elif p.kind == "scroll":
        for k, rr in enumerate([p.r * 0.3, p.r * 0.55]):
            ax.add_patch(Arc((p.cx, p.cy), rr * 2, rr * 2, theta1=30 + k * 40,
                              theta2=300 + k * 40, color=color, lw=1.7, zorder=5))
    lx, ly, direction = PUMP_LABEL_POS[p.id]
    align = DIR_ALIGN[direction]
    ax.text(lx, ly, p.label, color=INK, family=MONO, fontsize=9.3,
            zorder=6, weight="bold", **align)


def draw_pipe(ax, pipe: Pipe):
    xs = [pt[0] for pt in pipe.points]
    ys = [pt[1] for pt in pipe.points]
    flowing = pipe.state != "off"
    color = FLOW if flowing else LINE_IDLE
    lw = 3.2 if flowing else 1.9
    ax.plot(xs, ys, color=color, lw=lw, solid_capstyle="round", zorder=2)
    if flowing:
        a, b = (pipe.points[-2], pipe.points[-1]) if pipe.state == "forward" \
            else (pipe.points[1], pipe.points[0])
        ax.annotate("", xy=b, xytext=a,
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=0, mutation_scale=17),
                    zorder=3)


def draw_junction(ax, x, y):
    ax.add_patch(Circle((x, y), 4.5, facecolor=INK, edgecolor=INK, zorder=3))


def render_figure(dpi=300):
    margin_l, margin_r, margin_t, margin_b = -55, 30, -18, 20
    content_bottom = 1010
    fig, ax = plt.subplots(figsize=(14.4, 10.3), dpi=dpi)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(margin_l, CANVAS_W + margin_r)
    ax.set_ylim(margin_t, content_bottom + margin_b)
    ax.invert_yaxis()
    ax.axis("off")
    ax.set_aspect("equal")

    header_h = 38
    ax.add_patch(Rectangle((margin_l, margin_t), CANVAS_W - margin_l + margin_r, header_h,
                            facecolor=PANEL_BAR, zorder=1))
    ax.text(28, margin_t + header_h / 2, "BLUEFORS", color="white", family="sans-serif",
            fontsize=14, weight="bold", va="center", zorder=2)

    ax.text(300, 50, "VACUUM CAN", color=INK, family=MONO, fontsize=9.5, ha="center", zorder=3)
    ax.text(650, 50, "STILL", color=INK, family=MONO, fontsize=9.5, ha="center", zorder=3)
    ax.text(1010, 50, "3-HE IN", color=INK, family=MONO, fontsize=9.5, ha="center", zorder=3)
    ax.text(500, 868, "VENT", color=MUTED, family=MONO, fontsize=9.5, ha="center", zorder=3)
    ax.text(400, 868, "AUX", color=MUTED, family=MONO, fontsize=9.5, ha="center", zorder=3)
    ax.text(150, 998, "AIR", color=MUTED, family=MONO, fontsize=9.5, ha="center", zorder=3)

    for pipe in st.session_state.pipes.values():
        draw_pipe(ax, pipe)
    for x, y in JUNCTIONS:
        draw_junction(ax, x, y)
    for p in st.session_state.panels.values():
        draw_panel(ax, p)
    for v in st.session_state.vessels.values():
        draw_vessel_box(ax, v)
    for pmp in st.session_state.pumps.values():
        draw_pump(ax, pmp)
    for g in st.session_state.gauges.values():
        draw_gauge(ax, g)
    draw_flow_box(ax, st.session_state.flow_box)
    for v in st.session_state.valves.values():
        draw_bowtie(ax, v.cx, v.cy, v.rotation, v.open, small=v.small)
        if v.show_id and v.id in VALVE_ID_POS:
            id_x, id_y, direction = VALVE_ID_POS[v.id]
            align = DIR_ALIGN[direction]
            ax.text(id_x, id_y, v.id,
                    color=INK, family=MONO, fontsize=9, zorder=6,
                    weight="bold", **align)
        if v.label and v.id in VALVE_LABEL_POS:
            lbl_x, lbl_y, direction = VALVE_LABEL_POS[v.id]
            align = DIR_ALIGN[direction]
            ax.text(lbl_x, lbl_y, v.label,
                    color=MUTED, family=MONO, fontsize=8, zorder=6, **align)

    fig.tight_layout(pad=0.5)
    return fig


# =====================================================================
# APP
# =====================================================================

st.set_page_config(page_title="Dilution Refrigerator FLow Schematic", layout="wide")
init_state()

st.title("Dilution Refrigerator — Flow Schematic")
# ---- SOP stepper -----------------------------------------------------
step = SOP_STEPS[st.session_state.sop_index]

nav_l, nav_mid, nav_r = st.columns([1, 3, 1])
with nav_l:
    if st.button("⬅ Prev step", use_container_width=True,
                  disabled=st.session_state.sop_index == 0):
        st.session_state.sop_index -= 1
        apply_snapshot(snapshot_from_step(SOP_STEPS[st.session_state.sop_index]))
        st.rerun()
with nav_r:
    if st.button("Next step ➡", use_container_width=True,
                  disabled=st.session_state.sop_index == len(SOP_STEPS) - 1):
        st.session_state.sop_index += 1
        apply_snapshot(snapshot_from_step(SOP_STEPS[st.session_state.sop_index]))
        st.rerun()
with nav_mid:
    names = [s["name"] for s in SOP_STEPS]
    chosen = st.selectbox("SOP step", names, index=st.session_state.sop_index, label_visibility="collapsed")
    if names.index(chosen) != st.session_state.sop_index:
        st.session_state.sop_index = names.index(chosen)
        apply_snapshot(snapshot_from_step(step))
        st.rerun()

st.progress((st.session_state.sop_index + 1) / len(SOP_STEPS))
st.info(f"**{step['name']}** — {step['note']}")

fig = render_figure(dpi=150)

# Render vector SVG directly to Streamlit canvas for crisp display
svg_buf = io.StringIO()
fig.savefig(svg_buf, format="svg", facecolor=BG, bbox_inches="tight")
st.image(svg_buf.getvalue(), use_container_width=True)

plt.close(fig)

st.caption("Legend — black line: idle · blue dashed-style line + arrow: flowing, arrow = direction · "
           "blue ring: valve open / pump running · gray fill: valve shut / pump off.")