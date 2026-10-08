"""Procedural models for the modernized Raider Network item icons.
Convention: long items lie along X with their connector/front end at +X; the studio camera looks from front-right-above.
Each model is built from primitives and PBR materials; proportions and identifying features follow the in-game
reference icon (RaidTheory images/items/<id>.png), which is used only as a visual reference."""
import math
from trn3d import item, box, cyl, prism, sphere, torus, tube, helix, boolean, group, mat, D, sphere_path


# ------------------------------------------------------------------ ARC "driver" family (Leaper Pulse Unit, Rocketeer Driver)
def coil_driver(P, clamp_m, pin_m, strap=False, length=2.3):
    L = length; objs = []
    objs.append(cyl(0.30, L * 0.82, (0.05, 0, 0), (0, D(90), 0), P['gun']))                       # core tube
    # rear cap: stacked black rings
    objs.append(cyl(0.34, 0.42, (-L * 0.42, 0, 0), (0, D(90), 0), P['rubber'], bevel=0.03))
    for k in range(4):
        objs.append(torus(0.345, 0.018, (-L * 0.42 - 0.15 + k * 0.1, 0, 0), (0, D(90), 0), P['black']))
    objs.append(cyl(0.27, 0.12, (-L * 0.42 - 0.26, 0, 0), (0, D(90), 0), P['gun'], bevel=0.02))
    objs.append(cyl(0.16, 0.04, (-L * 0.42 - 0.33, 0, 0), (0, D(90), 0), P['black']))
    # six coil slabs around the core, with end clamps
    slab_len = L * 0.52; x0 = 0.06
    for k in range(6):
        a = D(30 + 60 * k)
        y, z = math.cos(a) * 0.37, math.sin(a) * 0.37
        rot = (a - D(90), 0, 0)
        objs.append(box((slab_len, 0.30, 0.075), (x0, y, z), rot, P['coil'], bevel=0.008))
        for xe in (x0 - slab_len / 2 - 0.03, x0 + slab_len / 2 + 0.03):
            objs.append(box((0.07, 0.36, 0.13), (xe, y * 1.02, z * 1.02), rot, clamp_m, bevel=0.012))
        # dark spine between slabs
        b = a + D(30)
        objs.append(box((slab_len + 0.1, 0.06, 0.06), (x0, math.cos(b) * 0.33, math.sin(b) * 0.33), (b, 0, 0), P['gun'], bevel=0.01))
    # front fork plates (open frame around the connector)
    fx = x0 + slab_len / 2 + 0.3
    for k in range(3):   # open three-prong front frame that reaches past the recessed connector
        a = D(30 + 120 * k)
        y, z = math.cos(a) * 0.36, math.sin(a) * 0.36
        objs.append(box((0.46, 0.2, 0.05), (fx - 0.05, y, z), (a - D(90), 0, 0), P['gun'], bevel=0.012))
        objs.append(box((0.05, 0.22, 0.08), (fx + 0.17, y * 1.03, z * 1.03), (a - D(90), 0, 0), clamp_m, bevel=0.008))
    # connector: copper ring + dark face + pins, sitting between the prongs
    cx = fx - 0.02
    objs.append(cyl(0.21, 0.16, (cx, 0, 0), (0, D(90), 0), P['copper'], bevel=0.015))
    objs.append(cyl(0.17, 0.02, (cx + 0.08, 0, 0), (0, D(90), 0), P['black']))
    pins = [(0, 0)] + [(0.065 * math.cos(D(60 * i)), 0.065 * math.sin(D(60 * i))) for i in range(6)] + \
           [(0.125 * math.cos(D(30 * i)), 0.125 * math.sin(D(30 * i))) for i in range(12)]
    for py, pz in pins:
        objs.append(cyl(0.022, 0.05, (cx + 0.1, py, pz), (0, D(90), 0), pin_m, verts=16, bevel=0.004))
    if strap:  # woven fabric carry strap arching over the rear section
        sm = mat('strap', (0.13, 0.2, 0.09), rough=0.9, stripes=(220, (0.05, 0.08, 0.04), 'X'), wear=0)
        n = 9
        for i in range(n):
            t = i / (n - 1); ang = math.pi * t
            x = -L * 0.44 + 0.55 * t; zz = 0.36 + 0.22 * math.sin(ang)
            tilt = math.atan2(0.22 * math.pi * math.cos(ang), 0.55)
            objs.append(box((0.085, 0.17, 0.025), (x, 0, zz), (0, -tilt, 0), sm, bevel=0.004))
    return group(objs, rot=(0, 0, 0))


@item('leaper-pulse-unit', azim=-64, elev=28)
def leaper_pulse_unit(P):
    coil_driver(P, P['brass'], P['copper'], strap=True)


@item('rocketeer-driver', azim=-64, elev=28)
def rocketeer_driver(P):
    coil_driver(P, mat('clampgreen', (0.24, 0.33, 0.2), metal=0.2, rough=0.5, bump=0.1), P['blue'], strap=False, length=2.15)


# ------------------------------------------------------------------ Bastion Cell
@item('bastion-cell', azim=-42, elev=22)
def bastion_cell(P):
    o = []
    # octagonal armoured housing along X
    o.append(prism(0.62, 1.15, 8, (0.25, 0, 0), (0, D(90), 0), P['gun'], bevel=0.03, twist=D(22.5)))
    # raised armour plates on each face
    for k in range(8):
        a = D(22.5 + 45 * k + 22.5)
        o.append(box((0.9, 0.34, 0.05), (0.25, math.cos(a) * 0.6, math.sin(a) * 0.6), (a - D(90), 0, 0), P['black'], bevel=0.015))
    # front face: recessed panel with Y-shaped channels and axle
    o.append(prism(0.5, 0.06, 8, (0.84, 0, 0), (0, D(90), 0), P['black'], bevel=0.01, twist=D(22.5)))
    for k in range(3):   # raised Y-shaped ribs with recessed channels between them
        a = D(90 + 120 * k)
        o.append(box((0.05, 0.12, 0.36), (0.875, math.cos(a) * 0.24, math.sin(a) * 0.24), (D(-120 * k), 0, 0), P['gun'], bevel=0.02))
        o.append(box((0.02, 0.03, 0.3), (0.9, math.cos(a) * 0.24, math.sin(a) * 0.24), (D(-120 * k), 0, 0), P['black'], bevel=0.004))
    o.append(prism(0.47, 0.03, 8, (0.86, 0, 0), (0, D(90), 0), P['steel'], bevel=0.005, twist=D(22.5)))
    o.append(prism(0.45, 0.05, 8, (0.865, 0, 0), (0, D(90), 0), P['black'], bevel=0.005, twist=D(22.5)))
    o.append(cyl(0.12, 0.1, (0.9, 0, 0), (0, D(90), 0), P['gun']))
    o.append(cyl(0.05, 0.32, (1.02, 0, 0), (0, D(90), 0), P['steel'], bevel=0.008))
    # rear section: dark collar ringed by tan padded blocks, with a corrugated conduit loop and clamps
    o.append(cyl(0.6, 0.5, (-0.55, 0, 0), (0, D(90), 0), P['gun'], bevel=0.02))
    pad = mat('tanpad', (0.4, 0.27, 0.2), rough=0.8, bump=0.3, noise_scale=120)
    for k in range(8):
        a = D(22.5 + 45 * k)
        o.append(box((0.42, 0.34, 0.12), (-0.58, math.cos(a) * 0.62, math.sin(a) * 0.62), (a - D(90), 0, 0), pad, bevel=0.04, segs=4))
    ring = []
    for k in range(48):   # corrugated conduit: a ring of short ribbed segments
        a = D(k * 7.5)
        o.append(torus(0.045, 0.02, (-0.3, math.cos(a) * 0.66, math.sin(a) * 0.66), (a, D(90), 0), P['black']))
    for k in range(4):
        a = D(45 + 90 * k)
        o.append(box((0.12, 0.1, 0.1), (-0.3, math.cos(a) * 0.68, math.sin(a) * 0.68), (a, 0, 0), P['steel'], bevel=0.015))
    o.append(prism(0.635, 0.025, 8, (-0.1, 0, 0), (0, D(90), 0), P['copper'], bevel=0.004, twist=D(22.5)))   # thin copper trim
    o.append(cyl(0.42, 0.08, (-0.82, 0, 0), (0, D(90), 0), P['black']))


# ------------------------------------------------------------------ Bombardier Cell
@item('bombardier-cell', azim=-55, elev=30)
def bombardier_cell(P):
    o = []
    o.append(box((2.1, 0.66, 0.66), (0, 0, 0), m=P['white'], bevel=0.14, segs=6))                     # long rounded white canister
    for y in (-0.31, 0.31):                                                                                # dark rails on the four long edges
        for z in (-0.31, 0.31):
            o.append(box((2.05, 0.1, 0.1), (-0.02, y, z), m=P['black'], bevel=0.03))
            for x in (-1.0, 0.0, 0.95):
                o.append(box((0.12, 0.15, 0.15), (x, y, z), m=P['gun'], bevel=0.03))
    for x in (-0.45, 0.45):                                                                                # panel seams
        o.append(box((0.01, 0.665, 0.665), (x, 0, 0), m=P['grey'], bevel=0.0))
    # front hatch: heavy rounded frame, brass inner face, recessed panel with a steel latch
    ochre = mat('ochre', (0.45, 0.32, 0.12), rough=0.6, bump=0.15, noise_scale=40)
    o.append(box((0.06, 0.92, 0.95), (1.02, 0, 0), m=ochre, bevel=0.12, segs=6))                         # ochre back plate inside the open frame
    for (sy, sz, y, z) in ((0.06, 0.95, -0.45, 0), (0.06, 0.95, 0.45, 0), (0.92, 0.06, 0, 0.46), (0.92, 0.06, 0, -0.46)):
        o.append(box((0.32, sy, sz), (1.16, y, z), m=P['steel'], bevel=0.025))                         # open rounded frame rails
    o.append(box((0.08, 0.5, 0.62), (1.2, 0.02, 0), m=P['white'], bevel=0.05, segs=4))
    o.append(box((0.05, 0.14, 0.3), (1.24, 0.1, 0.05), m=P['steel'], bevel=0.03))
    for z in (-0.4, 0.4):
        for y in (-0.4, 0.4):
            o.append(box((0.12, 0.12, 0.12), (1.12, y, z), m=P['black'], bevel=0.03))


# ------------------------------------------------------------------ Ion Sputter
@item('ion-sputter', azim=-30, elev=30)
def ion_sputter(P):
    o = []
    o.append(box((1.7, 1.25, 0.42), (0, 0, 0), m=P['offwhite'], bevel=0.035, segs=4))                  # instrument case
    o.append(box((1.6, 0.02, 0.32), (0, -0.63, -0.01), m=P['grey'], bevel=0.0))                        # front panel inset
    # analog meter
    o.append(box((0.36, 0.03, 0.22), (0.05, -0.64, 0.0), m=P['black'], bevel=0.01))
    o.append(box((0.3, 0.02, 0.17), (0.05, -0.655, 0.0), m=mat('dialface', (0.85, 0.82, 0.72), rough=0.4), bevel=0.0))
    o.append(box((0.006, 0.01, 0.13), (0.07, -0.665, -0.01), (0, D(25), 0), P['black'], bevel=0.0))
    # red digital readout
    o.append(box((0.22, 0.03, 0.08), (-0.45, -0.64, 0.06), m=mat('led', (0.3, 0.02, 0.01), emission=(1, 0.08, 0.02, 3)), bevel=0.005))
    # button grids
    for gx in (-0.58, -0.36, 0.37, 0.52):
        for r in range(2):
            for c in range(2):
                o.append(box((0.045, 0.03, 0.035), (gx + c * 0.06, -0.645, -0.06 - r * 0.06), m=P['black'], bevel=0.006))
    o.append(cyl(0.05, 0.05, (0.68, -0.65, -0.02), (D(90), 0, 0), P['black'], bevel=0.01))            # knob
    # vent grille on left side
    for k in range(9):
        o.append(box((0.012, 0.3, 0.012), (-0.86, -0.25, 0.12 - k * 0.025), m=P['black'], bevel=0.0))
    # top: spindle stack and flat disc
    o.append(cyl(0.22, 0.05, (-0.12, 0.05, 0.235), m=P['steel']))
    o.append(cyl(0.17, 0.08, (-0.12, 0.05, 0.28), m=P['chrome']))
    o.append(cyl(0.1, 0.06, (-0.12, 0.05, 0.34), m=P['steel']))
    o.append(cyl(0.035, 0.12, (-0.12, 0.05, 0.4), m=P['copper']))
    o.append(cyl(0.26, 0.025, (0.38, 0.25, 0.225), m=P['grey']))
    # cables arcing from the back
    for k, mm in enumerate((P['red'], P['copper'], P['red'])):
        y = 0.2 + k * 0.08
        tube([(-0.55 + k * 0.05, y, 0.21), (-0.55 + k * 0.03, y + 0.05, 0.55), (-0.3, y, 0.62), (-0.18, 0.1, 0.5), (-0.13, 0.06, 0.41)], 0.014, mm)


# ------------------------------------------------------------------ Surveyor Vault
@item('surveyor-vault', azim=-30, elev=22)
def surveyor_vault(P):
    o = []
    s = sphere(0.9, (0, 0, 0), mat('greypaint', (0.42, 0.43, 0.43), rough=0.38, coat=0.4, bump=0.04))
    # vertical access slot on the front-left (cut with a boolean) + mechanism inside
    cut = box((0.34, 0.5, 0.95), (0.12, -0.82, 0.1), (0, 0, D(-20)), None, bevel=0.03)
    boolean(s, cut)
    o.append(box((0.22, 0.25, 0.65), (0.14, -0.68, 0.12), (0, 0, D(-20)), P['steel'], bevel=0.02))
    o.append(box((0.08, 0.2, 0.5), (0.2, -0.75, 0.12), (0, 0, D(-20)), P['chrome'], bevel=0.01))
    # top opening collar
    o.append(cyl(0.42, 0.14, (0, 0, 0.83), m=P['gun'], bevel=0.02))
    o.append(torus(0.42, 0.03, (0, 0, 0.9), m=P['gun']))
    o.append(torus(0.36, 0.012, (0, 0, 0.82), m=P['brass']))
    o.append(cyl(0.3, 0.08, (0, 0, 0.88), m=P['black']))
    # equator seam and panel lines
    o.append(torus(0.905, 0.012, (0, 0, -0.18), m=P['grey']))
    # brass binding wire lying on the shell, with flush round fittings where it is anchored
    W1 = [(-70, 52), (-48, 20), (-28, -8), (-5, -35), (25, -45), (52, -25), (68, 8)]
    W2 = [(-100, -8), (-72, -28), (-35, -40), (5, -22), (32, 12), (45, 45)]
    sphere_path(W1, 0.915, m=P['brass']); sphere_path(W2, 0.915, m=P['brass'])
    for a, e in (W1[0], W1[3], W1[-1], W2[0], W2[2], W2[-1]):
        x, y, z = (0.9 * math.cos(D(e)) * math.sin(D(a)), -0.9 * math.cos(D(e)) * math.cos(D(a)), 0.9 * math.sin(D(e)))
        sphere(0.055, (x, y, z), P['steel'], scale=(1, 1, 1))


# ------------------------------------------------------------------ Hornet Driver
@item('hornet-driver', azim=-36, elev=24)
def hornet_driver(P):
    o = []
    o.append(prism(0.36, 1.9, 8, (0, 0, 0), (0, D(90), 0), P['black'], bevel=0.02, twist=D(22.5)))   # octagonal body
    o.append(box((1.1, 0.3, 0.16), (-0.2, -0.32, -0.22), m=P['gun'], bevel=0.02))                      # side housing
    o.append(cyl(0.385, 0.42, (-0.05, 0, 0), (0, D(90), 0), P['tape'], verts=10, bevel=0.0))         # duct-tape wrap
    o.append(cyl(0.4, 0.3, (0.95, 0, 0), (0, D(90), 0), mat('bronze', (0.42, 0.26, 0.12), metal=0.9, rough=0.45, bump=0.1), verts=8, bevel=0.02))
    o.append(cyl(0.28, 0.04, (1.11, 0, 0), (0, D(90), 0), P['black']))
    # cluster of yellow/blue tube ends
    for i, (py, pz) in enumerate([(0, 0)] + [(0.1 * math.cos(D(60 * k)), 0.1 * math.sin(D(60 * k))) for k in range(6)] + [(0.2 * math.cos(D(30 * k)), 0.2 * math.sin(D(30 * k))) for k in range(12)]):
        o.append(cyl(0.04, 0.1, (1.14, py, pz), (0, D(90), 0), P['brass'] if i % 3 else P['blue'], verts=20, bevel=0.006))
        o.append(cyl(0.022, 0.11, (1.15, py, pz), (0, D(90), 0), P['black'], verts=16, bevel=0.0))
    # blue cables running along the body
    for k, a in enumerate((60, 95, 125, 160)):
        y, z = math.cos(D(a)) * 0.42, math.sin(D(a)) * 0.42
        tube([(-0.95, y * 0.9, z * 0.9), (-0.5, y * 1.08, z * 1.08), (0.2, y * 1.05, z * 1.05), (0.8, y * 1.0, z * 1.0), (1.05, y * 0.6, z * 0.6)], 0.022, P['blue'])
    tube([(-0.8, -0.2, 0.42), (-0.2, -0.15, 0.48), (0.5, -0.1, 0.43), (1.05, -0.05, 0.25)], 0.012, P['brass'])
    o.append(prism(0.37, 0.12, 8, (-0.95, 0, 0), (0, D(90), 0), P['gun'], bevel=0.02, twist=D(22.5)))


# ------------------------------------------------------------------ Spotter Relay
@item('spotter-relay', azim=-50, elev=28)
def spotter_relay(P):
    import bpy
    o = []
    body = prism(0.4, 1.6, 8, (0, 0, 0), (0, D(90), 0), P['white'], bevel=0.03, twist=D(22.5))
    body.scale = (1, 1, 0.82)
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.4, radius2=0.27, depth=0.32, location=(0.96, 0, 0), rotation=(0, D(90), D(22.5)))
    nose = bpy.context.object; nose.scale = (0.82, 1, 1); nose.data.materials.append(P['white'])
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.4, radius2=0.2, depth=0.36, location=(-0.98, 0, 0), rotation=(0, D(-90), D(22.5)))
    tail = bpy.context.object; tail.scale = (0.82, 1, 1); tail.data.materials.append(P['white'])
    for side in (-1, 1):   # tan armour on the lower chamfers
        o.append(box((1.5, 0.05, 0.26), (0.0, side * 0.3, -0.2), (D(-35 * side), 0, 0), P['tan'], bevel=0.01))
    for x in (-0.45, 0.35):   # dark clamp bands
        b = prism(0.43, 0.32, 8, (x, 0, 0), (0, D(90), 0), P['gun'], bevel=0.03, twist=D(22.5)); b.scale = (1, 1, 0.84)
    o.append(cyl(0.22, 0.2, (1.17, 0, 0), (0, D(90), 0), P['gun'], bevel=0.02))
    o.append(cyl(0.16, 0.06, (1.28, 0, 0), (0, D(90), 0), P['steel'], bevel=0.01))
    o.append(cyl(0.11, 0.05, (1.31, 0, 0), (0, D(90), 0), P['glass']))
    o.append(box((0.05, 0.05, 0.15), (1.32, 0, 0), m=P['black'], bevel=0.01))
    for a in (D(150), D(210)):   # rear fins
        o.append(box((0.32, 0.025, 0.22), (-0.95, math.cos(a) * 0.32, math.sin(a) * 0.28), (a, 0, 0), P['gun'], bevel=0.006))


# ------------------------------------------------------------------ Geiger Counter
@item('geiger-counter', azim=-20, elev=40)
def geiger_counter(P):
    o = []
    o.append(box((1.0, 0.36, 1.25), (0, 0, 0), m=P['black'], bevel=0.12, segs=6))                     # dark rubber bumper
    o.append(box((0.9, 0.38, 1.12), (0, -0.01, 0), m=P['yellow'], bevel=0.1, segs=6))                  # yellow face
    o.append(box((0.6, 0.06, 0.42), (0, -0.19, 0.2), m=P['black'], bevel=0.03))                        # meter bezel
    o.append(box((0.5, 0.03, 0.32), (0, -0.215, 0.2), m=mat('dialface2', (0.75, 0.73, 0.66), rough=0.4)))
    o.append(box((0.005, 0.01, 0.24), (0.03, -0.235, 0.16), (0, D(-30), 0), P['black'], bevel=0.0))
    o.append(box((0.5, 0.012, 0.32), (0, -0.233, 0.2), m=mat('dialglass', (0.6, 0.7, 0.75), rough=0.03, coat=1, spec=1)))
    o.append(cyl(0.11, 0.08, (0.03, -0.22, -0.25), (D(90), 0, 0), P['black'], bevel=0.02))           # range knob
    o.append(box((0.04, 0.1, 0.14), (0.03, -0.27, -0.25), m=P['black'], bevel=0.01))
    for x, z in ((-0.38, 0.5), (0.38, 0.5), (-0.38, -0.5), (0.38, -0.5)):
        o.append(cyl(0.03, 0.03, (x, -0.2, z), (D(90), 0, 0), P['steel']))
    # probe on top-left with strap
    o.append(cyl(0.11, 0.6, (-0.35, 0.0, 0.78), (0, D(90), 0), P['black'], bevel=0.02))
    o.append(cyl(0.12, 0.06, (-0.66, 0.0, 0.78), (0, D(90), 0), P['steel'], bevel=0.01))
    o.append(cyl(0.08, 0.02, (-0.69, 0.0, 0.78), (0, D(90), 0), P['glass']))
    o.append(box((0.08, 0.26, 0.2), (-0.2, 0, 0.72), m=P['grey'], bevel=0.02))
    # coiled cable from the probe down the right side
    o.append(helix((0.0, 0.0, 0.8), 0.55, 0.05, 0.022, 9, P['rubber'], axis='X', drop=(0, 0.05, 0)))
    o.append(tube([(0.55, 0.05, 0.8), (0.75, 0.06, 0.6), (0.78, 0.04, 0.2), (0.7, 0.0, -0.2)], 0.022, P['rubber']))
    group(o, rot=(D(-62), 0, D(8)))


# ------------------------------------------------------------------ Advanced Electrical Components
@item('advanced-electrical-components', azim=-28, elev=48)
def advanced_electrical_components(P):
    o = []
    o.append(box((1.6, 1.3, 0.06), (0, 0, -0.12), m=P['grey'], bevel=0.02))
    for (sx, sy, x, y) in ((1.6, 0.07, 0, -0.615), (1.6, 0.07, 0, 0.615), (0.07, 1.3, -0.765, 0), (0.07, 1.3, 0.765, 0)):
        o.append(box((sx, sy, 0.27), (x, y, 0.0), m=P['grey'], bevel=0.02))
    for x in (-0.79, 0.79):                                                                                # corner latches
        for y in (-0.4, 0.4):
            o.append(box((0.04, 0.12, 0.08), (x, y, 0.08), m=P['grey'], bevel=0.01))
    o.append(box((1.48, 1.18, 0.02), (0, 0, -0.1), m=P['trayg'], bevel=0.0))
    for x in (-0.25, 0.3):                                                                                 # dividers
        o.append(box((0.02, 1.18, 0.16), (x, 0, -0.02), m=P['trayg'], bevel=0.0))
    o.append(box((0.55, 0.02, 0.16), (0.03, 0.05, -0.02), m=P['trayg'], bevel=0.0))
    o.append(box((0.45, 0.02, 0.16), (0.53, -0.15, -0.02), m=P['trayg'], bevel=0.0))
    for k in range(14):                                                                                    # ribbed outer wall
        o.append(box((0.04, 0.05, 0.2), (-0.7 + k * 0.105, -0.655, -0.02), m=P['grey'], bevel=0.006))
    for k in range(11):
        o.append(box((0.05, 0.04, 0.2), (0.805, -0.55 + k * 0.11, -0.02), m=P['grey'], bevel=0.006))
    # contents: chips, PCB, wire bundle
    import random; random.seed(7)
    for k in range(9):
        x = random.uniform(-0.2, 0.25); y = random.uniform(-0.5, 0.0)
        o.append(box((0.09, 0.09, 0.025), (x, y, -0.08), (0, 0, random.uniform(0, 1.5)), P['black'], bevel=0.004))
    o.append(box((0.42, 0.34, 0.02), (0.55, 0.25, -0.08), (0, 0, D(10)), P['pcb'], bevel=0.004))
    for k in range(6):
        o.append(box((0.05, 0.04, 0.02), (0.45 + (k % 3) * 0.1, 0.18 + (k // 3) * 0.12, -0.065), m=P['black'], bevel=0.003))
    for k, mm in enumerate((P['red'], P['blue'], P['red'], P['blue'])):
        tube([(-0.68, 0.45 - k * 0.04, -0.07), (-0.45, 0.35 - k * 0.04, -0.07), (-0.3, 0.1 - k * 0.04, -0.07)], 0.012, mm)
    o.append(box((0.3, 0.3, 0.05), (-0.48, -0.3, -0.07), m=P['gun'], bevel=0.01))


# ------------------------------------------------------------------ Comet Igniter
@item('comet-igniter', azim=-42, elev=18)
def comet_igniter(P):
    o = []
    for side in (-1, 1):                                                                                   # two white shell halves split by a dark core band
        sh = sphere(0.8, (0.05 * side, 0, 0), P['white'], scale=(0.9, 1, 1))
        cut = box((2.0, 2.0, 2.0), (-side * 1.0 + side * 0.17, 0, 0), bevel=0)
        boolean(sh, cut)
        o.append(sh)
    o.append(cyl(0.72, 0.36, (0, 0, 0), (0, D(90), 0), P['black'], bevel=0.02))
    for k in range(11):
        o.append(torus(0.725, 0.01, (-0.15 + k * 0.03, 0, 0), (0, D(90), 0), P['gun']))
    # front oval plate with two dark lenses
    plate = cyl(0.42, 0.1, (0.74, 0, 0), (0, D(90), 0), P['white'], bevel=0.035)
    plate.scale = (1, 0.78, 1.25)
    rec = cyl(0.2, 0.06, (0.79, 0, 0), (0, D(90), 0), P['black'], bevel=0.012)
    rec.scale = (1, 0.88, 1.7)
    for z in (0.15, -0.15):
        o.append(cyl(0.1, 0.07, (0.81, 0, z), (0, D(90), 0), P['glass'], bevel=0.006))
        o.append(torus(0.105, 0.014, (0.845, 0, z), (0, D(90), 0), P['steel']))
