import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, FancyBboxPatch


# ============================================================
# Coordinate system
# ============================================================
#
# Origin = top-left
# x increases to the right
# y increases downward
#
# Units are arbitrary schematic units, chosen to match
# the proportions of the original Bluefors screenshot.
#
# ============================================================


# ------------------------------------------------------------
# Component coordinates
# ------------------------------------------------------------

V = {
    # upper section
    "V1":  (650, 230),
    "V2":  (760, 230),
    "V3":  (830, 330),

    "V4":  (1010, 250),
    "V5":  (1105, 215),
    "V6":  (1105, 300),

    "V7":  (1110, 510),
    "V8":  (1010, 620),
    "V9":  (1110, 660),

    # lower / scroll-1 section
    "V10": (730, 760),
    "V11": (800, 930),
    "V12": (900, 840),
    "V13": (1010, 800),

    # left / backing section
    "V14": (300, 180),
    "V15": (500, 230),
    "V16": (300, 620),

    "V17": (500, 620),
    "V18": (600, 700),
    "V19": (500, 760),
    "V20": (400, 760),

    "V21": (150, 760),
    "V22": (300, 760),
    "V23": (220, 850),
}

# Unlabeled manual valve visible in the diagram between N_SCROLL1_IN and
# the node feeding V12 (equivalent to "UNLABELED_MANUAL_1" in the P&ID table).
# FIX: was centered at x=800, only 10 units from the trunk at x=790 -
# since this symbol (unlike the round valves) has no background fill,
# the trunk line showed through/overlapped its left wing, making the
# left connection look broken/merged with the trunk instead of a clean
# tee. Recentered at the midpoint between the trunk (790) and V12's
# left edge (878) so both sides get a clearly visible stub.
MANUAL_UNLABELED = {
    "MV1": (834, 840),
}


BPV = {
    "BPV1": (1230, 257),
    "BPV2": (800, 650),
    "BPV3": (1060, 800),
    "TEST": (270, 330),
}


PUMPS = {
    "TURBO1": (650, 350),
    "TURBO2": (300, 850),
    "SCROLL1": (830, 760),
    "SCROLL2": (150, 850),
    "COM": (1180, 257),
}


GAUGES = {
    "P1":  (150, 140),
    "P2":  (500, 140),
    "P3":  (950, 140),
    "P4":  (950, 680),
    "P5":  (1100, 985),
    "P6":  (30, 700),
}


# ============================================================
# Drawing helpers
# ============================================================

fig, ax = plt.subplots(figsize=(16, 11))


def pipe(points, lw=2.2):
    """
    Draw a pipe as a sequence of (x,y) points.
    """
    xs, ys = zip(*points)
    ax.plot(xs, ys, color="black", lw=lw,
            solid_capstyle="round",
            solid_joinstyle="round",
            zorder=1)


def junction(x, y, r=5):
    """
    Black junction dot.
    """
    ax.add_patch(
        Circle(
            (x, y),
            r,
            facecolor="black",
            edgecolor="black",
            zorder=4,
        )
    )


def valve(name, x, y, orientation="vertical"):
    """
    Draw a valve as a circle.

    orientation is only used for visual orientation;
    connectivity is defined separately by the pipe network.
    """

    ax.add_patch(
        Circle(
            (x, y),
            22,
            facecolor="white",
            edgecolor="black",
            lw=1.5,
            zorder=5,
        )
    )

    # FIX: long labels like "V1 (GATE)" were overflowing the 22-radius
    # circle at fontsize 9. Shrink and wrap onto two lines for long names.
    fontsize = 9
    if len(name) > 4:
        name = name.replace(" (", "\n(")
        fontsize = 7

    ax.text(
        x,
        y,
        name,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontweight="bold",
        zorder=6,
    )


def manual_valve(name, x, y, orientation="horizontal"):
    """
    Simple butterfly/manual-valve symbol.
    """

    if orientation == "horizontal":
        ax.plot(
            [x - 18, x + 18],
            [y, y],
            color="black",
            lw=2,
            zorder=5,
        )

        ax.plot(
            [x - 10, x + 10],
            [y - 9, y + 9],
            color="black",
            lw=2,
            zorder=6,
        )

        ax.plot(
            [x - 10, x + 10],
            [y + 9, y - 9],
            color="black",
            lw=2,
            zorder=6,
        )

    else:
        ax.plot(
            [x, x],
            [y - 18, y + 18],
            color="black",
            lw=2,
            zorder=5,
        )

        ax.plot(
            [x - 9, x + 9],
            [y - 10, y + 10],
            color="black",
            lw=2,
            zorder=6,
        )

        ax.plot(
            [x + 9, x - 9],
            [y - 10, y + 10],
            color="black",
            lw=2,
            zorder=6,
        )

    ax.text(
        x,
        y - 27,
        name,
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
    )


def pump(name, x, y):
    """
    Pump symbol.
    """
    ax.add_patch(
        Circle(
            (x, y),
            32,
            facecolor="white",
            edgecolor="black",
            lw=2,
            zorder=5,
        )
    )

    ax.add_patch(
        Circle(
            (x, y),
            22,
            facecolor="white",
            edgecolor="black",
            lw=1,
            zorder=6,
        )
    )

    ax.text(
        x,
        y + 58,
        name,
        ha="center",
        va="bottom",
        fontsize=9,
        fontweight="bold",
    )


def gauge(name, x, y, value=None):
    """
    Pressure gauge / tap.
    """

    text = name
    if value is not None:
        text += f"\n{value}"

    ax.add_patch(
        FancyBboxPatch(
            (x - 38, y - 15),
            76,
            30,
            boxstyle="round,pad=0.02,rounding_size=10",
            facecolor="white",
            edgecolor="black",
            lw=1.2,
            zorder=5,
        )
    )

    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=8,
        zorder=6,
    )


def label(text, x, y, **kwargs):
    ax.text(
        x,
        y,
        text,
        fontsize=10,
        ha=kwargs.pop("ha", "center"),
        va=kwargs.pop("va", "center"),
        fontweight=kwargs.pop("fontweight", "normal"),
        **kwargs,
    )


# ============================================================
# PIPE NETWORK
# ============================================================

# ------------------------------------------------------------
# LEFT / VACUUM CAN
# ------------------------------------------------------------

pipe([
    (300, 80),
    (300, 158),
])

# FIX: P1 gauge box was floating, unconnected to the Vacuum Can line.
# Added the missing tap.
pipe([
    (188, 140),
    (300, 140),
])

pipe([
    (300, 202),
    (300, 330),
])

# TEST branch
pipe([
    (300, 330),
    (250, 330),
])

# FIX: this vertical run was previously cut off at y=330 (the TEST
# tee), leaving V16 completely disconnected from the V14/TEST
# column above it. The line actually continues straight down to V16.
pipe([
    (300, 330),
    (300, 598),
])

# V14 -> V15
pipe([
    (300, 202),
    (300, 230),
    (478, 230),
])

# V15 -> main node
pipe([
    (522, 230),
    (650, 230),
])

# P2 pressure tap
# FIX: this tap previously ran straight up from x=500, which is
# V15's own center - the line looked like it was coming out of the
# valve body instead of tapping the pipe. The real tee is on the
# V15->main-node run just to the right of V15, at x=560.
pipe([
    (560, 230),
    (560, 140),
    (500, 140),
])
junction(560, 230)

# ------------------------------------------------------------
# V1 / V2 / V3 / TURBO1
# ------------------------------------------------------------

# STILL -> V1
pipe([
    (650, 80),
    (650, 208),
])

# V1 bottom -> main node
pipe([
    (650, 252),
    (650, 230),
])

# V2
pipe([
    (650, 230),
    (738, 230),
])

pipe([
    (782, 230),
    (830, 230),
    (830, 308),
])

# ------------------------------------------------------------
# FIX: V1 and V2 are parallel paths (per diagram note "GATE;
# parallel path with V2"). There is a plain bypass wire from the
# STILL line (above V1) straight across to the V2/V3 node, so V1
# and V2 sit between the SAME two nodes. This was missing.
# ------------------------------------------------------------
pipe([
    (650, 195),
    (830, 195),
    (830, 230),
])
junction(650, 195)

# V3 bottom -> MAIN LINE
pipe([
    (830, 352),
    (830, 470),
    (1010, 470),
])

# IMPORTANT:
# This is the correction: V3 goes to the MAIN LINE,
# NOT directly into the FLOW meter.


# TURBO 1 intake
pipe([
    (650, 252),
    (650, 318),
])

# TURBO 1 exhaust
pipe([
    (650, 382),
    (650, 470),
])

# horizontal main line / overpass
pipe([
    (500, 470),
    (1010, 470),
])


# ------------------------------------------------------------
# 3-He / V4 / FLOW / COM
# ------------------------------------------------------------

# 3-He IN
pipe([
    (1010, 80),
    (1010, 228),
])

# FIX: P3's gauge box was floating next to the trunk with nothing
# actually drawn between them - just eyeballed close enough to look
# connected. Added a real tap pipe, matching P4/P6 style.
pipe([
    (1010, 140),
    (988, 140),
])
junction(1010, 140)

# V4 bottom -> FLOW -> main line
pipe([
    (1010, 272),
    (1010, 470),
])

# FLOW meter
ax.add_patch(
    Rectangle(
        (970, 380),
        80,
        45,
        facecolor="white",
        edgecolor="black",
        lw=1.5,
        zorder=5,
    )
)

# FIX: this label was rendering behind the FLOW box (box zorder=5,
# text defaulted to a lower zorder), so the "FLOW / 0.00" text was
# invisible. Forced the text above the box.
label("FLOW\n0.00", 1010, 402, fontweight="bold", zorder=6)


# V5
# FIX: previously this branch tapped the trunk at y=215 but then
# dropped down to meet V5 at y=250, creating an ugly dogleg that
# doesn't appear in the diagram - there the tee and V5 sit at the
# SAME height. Also fixed: V6 used to sit all the way down at
# y=380, which put its circle physically overlapping the FLOW meter
# box drawn at y=380-425. V5/V6 are now placed directly on their
# tee rows (215 and 300), which are symmetric around V4 (250) just
# like the diagram, and V6 now clears the FLOW box entirely.
pipe([
    (1010, 215),
    (1083, 215),
])
junction(1010, 215)

pipe([
    (1127, 215),
    (1180, 215),
])
junction(1180, 215)

# V5/COM-top node down to COM
pipe([
    (1180, 215),
    (1180, 225),
])

# V6
pipe([
    (1010, 300),
    (1083, 300),
])
junction(1010, 300)

pipe([
    (1127, 300),
    (1180, 300),
])
junction(1180, 300)

# COM bottom to node
pipe([
    (1180, 289),
    (1180, 300),
])

# ------------------------------------------------------------
# BPV1
#
# IMPORTANT:
# BPV1 is a parallel path around COM.
# It connects the V5/COM-top node to the V6/COM-bottom node.
# ------------------------------------------------------------

pipe([
    (1180, 215),
    (1230, 215),
    (1230, 300),
    (1180, 300),
])


# ------------------------------------------------------------
# MAIN / TRAP / V7 / V8 / V9
# ------------------------------------------------------------

# Main line from flow
pipe([
    (1010, 470),
    (1010, 488),
])

# V7 branch to TRAP
pipe([
    (1010, 470),
    (1110, 470),
    (1110, 488),
])

pipe([
    (1110, 532),
    (1110, 570),
])

# TRAP box
ax.add_patch(
    Rectangle(
        (1080, 570),
        60,
        45,
        facecolor="white",
        edgecolor="black",
        lw=1.5,
        zorder=3,
    )
)
label("TRAP", 1110, 592)

# FIX: V9 was at y=620 with the TRAP box bottom at y=615, so V9's
# top edge (598) cut 17 units into the TRAP box - clearly
# overlapping it. Moved V9 down to y=660 (top edge 638) for a clean
# gap below TRAP, and extended the node connection to match.
pipe([
    (1110, 615),
    (1110, 638),
])

# V9 -> main node
# FIX: V9's return and the P4 tap are two DISTINCT junctions on the
# main trunk in the original (P4 taps higher, V9 rejoins lower just
# above the V13 tee) - they were incorrectly collapsed onto the same
# point. Split them back apart.
pipe([
    (1110, 682),
    (1110, 710),
    (1010, 710),
])
junction(1010, 710)

# FIX: V7 was previously mis-placed at x=1010 (on top of the V8
# line), which put it in series with V8 instead of on its own
# parallel TRAP branch. Moving V7 to x=1110 (above TRAP/V9, next
# to the "V7 branch to TRAP" pipe below) opened a gap on the main
# V8 line that needs to be a plain pipe (no valve) straight through.
pipe([
    (1010, 488),
    (1010, 532),
])

# V8 main path
pipe([
    (1010, 532),
    (1010, 598),
])

pipe([
    (1010, 642),
    (1010, 760),
])

# P4 tap
# FIX: P4 taps the main trunk ABOVE the V9-return junction (710),
# not at the same point - these are two separate junctions in the
# original diagram with a short piece of trunk between them.
pipe([
    (1010, 680),
    (950, 680),
])
junction(1010, 680)


# ============================================================
# BACKING MANIFOLD
# ============================================================

# V16 -> backing manifold
pipe([
    (300, 642),
    (300, 700),
])

# Main backing manifold
pipe([
    (100, 700),
    (600, 700),
])

# FIX: P6 had no connector at all - its gauge box was just left
# sitting near the manifold's end point with nothing drawn between
# them. Added a straight horizontal tap running left off the
# manifold, in line with it, rather than dropping down.
pipe([
    (100, 700),
    (68, 700),
])
junction(100, 700)

# ------------------------------------------------------------
# IMPORTANT:
# V17, V19, V20 and V16 all meet the same manifold.
# V18 is immediately to the right of that intersection.
# ------------------------------------------------------------

# V17 branch from upper main to backing manifold
pipe([
    (500, 470),
    (500, 598),
])

pipe([
    (500, 642),
    (500, 700),
])

# V19 branch
# FIX: V19/V20/V21/V22 previously sat only 2 units below the
# manifold line, so their circles visibly overlapped it. Moved the
# valves down to y=760 (see dict) and extended these stub pipes to
# match, giving a clean gap above the manifold.
pipe([
    (500, 700),
    (500, 738),
])

pipe([
    (500, 782),
    (500, 840),
])

# V20 branch
pipe([
    (400, 700),
    (400, 738),
])

pipe([
    (400, 782),
    (400, 840),
])

# V21
pipe([
    (150, 700),
    (150, 738),
])

# V22
pipe([
    (300, 700),
    (300, 738),
])


# ------------------------------------------------------------
# TURBO 1 EXHAUST / V18
# ------------------------------------------------------------

# Turbo exhaust comes down
pipe([
    (650, 382),
    (650, 700),
])

# backing manifold enters V18
pipe([
    (600, 700),
    (578, 700),
])

# V18 right side -> Turbo exhaust node
pipe([
    (622, 700),
    (650, 700),
])

# branch from Turbo exhaust to V10
pipe([
    (650, 700),
    (650, 760),
    (708, 760),
])


# ============================================================
# SCROLL 1 SECTION
# ============================================================

# V10 -> Scroll 1
pipe([
    (752, 760),
    (798, 760),
])

# Scroll 1 outlet -> P4 node
pipe([
    (862, 760),
    (1010, 760),
])

# ------------------------------------------------------------
# BPV2
# Parallel path around SCROLL 1
# ------------------------------------------------------------

pipe([
    (650, 700),
    (650, 650),
    (778, 650),
])

pipe([
    (822, 650),
    (900, 650),
    (900, 760),
])

# ------------------------------------------------------------
# Lower bypass network
# ------------------------------------------------------------

# FIX: this branch previously dropped straight down from V10's own
# center (730,782), giving V10 3 connections (left, right, and this
# drop) instead of 2. In the original, the drop actually taps the
# junction BETWEEN V10 and Scroll1 (on the V10->Scroll1 connecting
# pipe), not V10 itself. Moved the tap to x=790 and added the
# junction dot there.
junction(790, 760)
pipe([
    (790, 760),
    (790, 930),
])

# V11
pipe([
    (790, 930),
    (778, 930),
])

pipe([
    (822, 930),
    (1010, 930),
])

# V12
# FIX: the diagram shows an unlabeled manual (butterfly) valve on
# this branch, between the N_SCROLL1_IN vertical line and V12. It
# was missing entirely from the script.
# FIX: this segment previously started at x=730 (V10's old, wrong
# drop point) which is well to the left of the actual vertical
# branch line (now correctly at x=790), so it was overshooting
# past the branch line before ever reaching V12/MV1. Start it at
# x=790 instead.
# FIX: endpoints updated to match MV1's recentering (now at x=834,
# half-width 18 -> tips at 816/852) so the stub actually reaches the
# valve symbol instead of stopping short/overlapping it. Also added
# a junction dot at the trunk tap, matching the reference image.
junction(790, 840)
pipe([
    (790, 840),
    (816, 840),
])

pipe([
    (852, 840),
    (878, 840),
])

pipe([
    (922, 840),
    (1010, 840),
])

# FIX: V13 was sitting exactly ON the 3-way junction where the V8
# return line and the Scroll1-outlet line meet (1010,760), giving it
# 3 connections instead of 2. In the original, that tee is a
# separate point ABOVE V13; V13 hangs below it with just a top and
# bottom port. V13's center was moved down to y=800 (see V dict) -
# add the short connector from the tee down to V13's top port.
pipe([
    (1010, 760),
    (1010, 778),
])

# V13
pipe([
    (1010, 822),
    (1010, 930),
])

# ============================================================
# BPV3 / MIXTURE TANK
# ============================================================

# FIX: BPV3 is actually a VERTICAL bypass valve that runs from the
# N_P4 node (shared with V8-bottom/V9-return/SCROLL1-output, up at
# y=700) straight down to the N_SCROLL1_RETURN bottom row -
# bypassing V13, exactly like V11/V12 do. It is NOT an inline valve
# on the horizontal run out to the mixture tank; that run is a
# plain, uninterrupted pipe.

pipe([
    (1010, 930),
    (1220, 930),
])

# FIX: BPV3's top branch was tapping the trunk at a stray y=700
# point. In the original it taps from the SAME junction as the
# Scroll1-outlet / V13-top tee (y=760), not a separate point.
pipe([
    (1010, 760),
    (1060, 760),
])
pipe([
    (1060, 760),
    (1060, 778),
])
pipe([
    (1060, 822),
    (1060, 930),
])
junction(1060, 930)

# FIX: P5 was tapping straight down from mid-span (x=1100), cutting
# across BPV3's branch. Matching the P6 treatment, route it instead
# as an L off to the side - here from the right, off the same
# bottom junction where the mixture tank's riser meets the run.
pipe([
    (1138, 985),
    (1220, 985),
    (1220, 930),
])
junction(1220, 930)

# Mixture tank connection
pipe([
    (1220, 930),
    (1220, 850),
])


# ============================================================
# MIXTURE TANK
# ============================================================

ax.add_patch(
    FancyBboxPatch(
        (1180, 700),
        80,
        150,
        boxstyle="round,pad=0.02,rounding_size=30",
        facecolor="white",
        edgecolor="black",
        lw=1.5,
        zorder=2,
    )
)

label("MIXTURE\nTANK", 1220, 775, fontweight="bold")

# tank outlet valve
manual_valve("TANK", 1220, 875, orientation="vertical")

pipe([
    (1220, 900),
    (1220, 930),
])


# ============================================================
# TURBO 2 / SCROLL 2
# ============================================================

# V21 -> Scroll 2
pipe([
    (150, 782),
    (150, 818),
])

# Scroll 2 exhaust
pipe([
    (150, 882),
    (150, 970),
])

# FIX: this branch previously tapped at (150,850), which is SCROLL2's
# own pump center - it rendered as if emerging from inside the pump
# body. The diagram clearly taps the line above SCROLL2, before the
# pump. Moved the tap to y=800 (between V21's outlet and SCROLL2's
# top edge), added a junction dot, and routed the branch to V23.
junction(150, 800)

# V23 branch (from pre-pump tap)
# FIX: the previous route dropped down to y=850 at x=170, but x=170
# sits well inside SCROLL2's pump radius (center 150, radius 32) -
# the wire was cutting straight through the SCROLL2 symbol. Instead
# run the branch horizontally at y=800 (clear above SCROLL2's top
# edge at y=818) all the way to V23's x position, then drop straight
# down into V23's top port - this passes outside SCROLL2 entirely.
pipe([
    (150, 800),
    (220, 800),
    (220, 828),
])

# FIX: removed a spurious straight pipe that had connected V23
# directly to TURBO2's pump center (242,850)-(300,850). That
# duplicated/shorted the proper connection, which is the
# "Turbo 2 exhaust -> V23" route below (V23's bottom port to
# TURBO2's exhaust) - the only V23/TURBO2 link shown in the diagram.

# V22 -> Turbo 2
pipe([
    (300, 782),
    (300, 818),
])

# Turbo 2 exhaust -> V23
pipe([
    (300, 882),
    (300, 930),
    (220, 930),
    (220, 872),
])


# ============================================================
# COMPONENT SYMBOLS
# ============================================================

# Standard valves
for name, (x, y) in V.items():
    orientation = (
        "horizontal"
        if name in {
            "V2", "V5", "V6", "V10",
            "V11", "V12", "V15", "V18", "V23"
        }
        else "vertical"
    )
    # FIX: diagram labels V1 as "V1 (GATE)"; the dict key alone
    # ("V1") was being used verbatim as the on-screen label.
    display_name = "V1 (GATE)" if name == "V1" else name
    valve(display_name, x, y, orientation)


# Manual valves
manual_valve("BPV1", *BPV["BPV1"], orientation="vertical")
manual_valve("BPV2", *BPV["BPV2"], orientation="horizontal")
manual_valve("BPV3", *BPV["BPV3"], orientation="vertical")
manual_valve("TEST", *BPV["TEST"], orientation="horizontal")

# Unlabeled manual valve (diagram shows no text label on this one)
manual_valve("", *MANUAL_UNLABELED["MV1"], orientation="horizontal")


# Pumps
for name, (x, y) in PUMPS.items():
    pump(name, x, y)


# Gauges
gauge("P1", *GAUGES["P1"])
gauge("P2\n8.60E-1", *GAUGES["P2"])
gauge("P3\n6.14E+0", *GAUGES["P3"])
gauge("P4\n1.64E+2", *GAUGES["P4"])
gauge("P5\n8.11E+2", *GAUGES["P5"])
gauge("P6\n5.08E-1", *GAUGES["P6"])


# ============================================================
# Labels
# ============================================================

label("VACUUM CAN", 300, 45, fontweight="bold")
label("STILL", 650, 45, fontweight="bold")
label("3-HE IN", 1010, 45, fontweight="bold")

label("VENT", 500, 865)
label("AUX", 400, 865)
label("AIR", 150, 995)

label("PULSE TUBE", 120, 80)
label("HS-STILL", 120, 170)
label("HS-MC", 120, 260)
label("EXT", 120, 350)


# ============================================================
# Junction dots
# ============================================================

junction(300, 230)
junction(650, 230)
junction(830, 470)

junction(1010, 470)
junction(1010, 760)
junction(1010, 930)

# Critical common backing-manifold intersection
junction(500, 700)

junction(650, 700)

junction(150, 700)
junction(300, 700)
junction(400, 700)

# ============================================================
# Formatting
# ============================================================

ax.set_xlim(0, 1350)
ax.set_ylim(1050, 0)

ax.set_aspect("equal")

ax.set_xlabel("X")
ax.set_ylabel("Y")

ax.set_xticks(range(0, 1400, 100))
ax.set_yticks(range(0, 1100, 100))

ax.grid(True, linestyle=":", alpha=0.35)

ax.set_title(
    "Bluefors Gas-Handling / Cryogenic Flow Schematic",
    fontsize=16,
    fontweight="bold",
)

plt.tight_layout()
plt.savefig('rendered.png', dpi=150)