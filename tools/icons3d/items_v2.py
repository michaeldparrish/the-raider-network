"""v6.2 premium models. Original procedural geometry; the RaidTheory in-game icon is used only as a visual reference
for shape, proportions, colours and identifying features (never as an image input, never traced)."""
import math, random
import bpy
from trn3d import item, box, cyl, prism, sphere, torus, tube, helix, boolean, group, mat, D, sphere_path


def rrect_ring(sx, sy, sz, wall, loc, m, bevel=0.06):
    """Open rounded-rectangle frame (a tube along X): outer box minus inner box."""
    o = box((sx, sy, sz), loc, m=m, bevel=bevel, segs=6)
    c = box((sx * 3, sy - 2 * wall, sz - 2 * wall), loc, m=None, bevel=bevel * 0.6, segs=6)
    boolean(o, c, bevel_first=True); return o


def ribbed_rail(x0, x1, y, z, w, h, m, rib_m, n=18):
    o = [box((x1 - x0, w, h), ((x0 + x1) / 2, y, z), m=m, bevel=0.018)]
    for k in range(n):
        x = x0 + 0.05 + k * (x1 - x0 - 0.1) / (n - 1)
        o.append(box((0.03, w * 1.04, h * 0.82), (x, y, z), m=rib_m, bevel=0.008))
    return o


# ------------------------------------------------------------------ Bombardier Cell
@item('bombardier-cell', azim=-40, elev=26)
def bombardier_cell(P):
    W = mat('bombwhite', (0.6, 0.6, 0.58), metal=0, rough=0.45, coat=0.2, bump=0.1, wear=0.7, scratches=0.6, dust=0.35, grime=0.7)
    ochre = mat('ochre2', (0.55, 0.38, 0.13), metal=0.0, rough=0.6, bump=0.3, noise_scale=30, scratches=0.25, dust=0.45, grime=0.45)
    o = []
    L, Y, Z = 2.3, 0.6, 0.74
    body = box((L, Y, Z), (-0.05, 0, 0), m=W, bevel=0.2, segs=8)                       # long canister, rounded edges
    o.append(body)
    seam = mat('seam', (0.08, 0.08, 0.08), rough=0.7, wear=0)
    for x in (-0.55, 0.25):                                                              # panel seams (thin inset lines)
        o.append(box((0.012, Y + 0.004, Z - 0.3), (x, 0, 0), m=seam, bevel=0))
        o.append(box((0.012, Y - 0.3, Z + 0.004), (x, 0, 0), m=seam, bevel=0))
    # two dark ribbed rails on the front (camera-facing, -Y) face, top and bottom
    for z in (Z / 2 - 0.08, -Z / 2 + 0.08):
        o += ribbed_rail(-1.15, 0.95, Y / 2 + 0.05, z, 0.11, 0.15, P['gun'], P['black'])
        for x in (-1.17, 0.97):
            o.append(box((0.1, 0.17, 0.2), (x, Y / 2 + 0.06, z), m=P['black'], bevel=0.03))
    # open rounded front frame with ochre cavity
    fx = 1.2
    ring = rrect_ring(0.34, Y + 0.34, Z + 0.4, 0.06, (fx, 0, 0), mat('framewhite', (0.62, 0.62, 0.6), metal=0.4, rough=0.35, wear=0.6, scratches=0.5), bevel=0.14)
    o.append(box((0.04, Y + 0.24, Z + 0.3), (fx - 0.15, 0, 0), m=ochre, bevel=0.1, segs=5))   # cavity back wall
    for sgn in (-1, 1):                                                                    # cavity side liners
        o.append(box((0.3, 0.02, Z + 0.26), (fx, sgn * (Y / 2 + 0.1), 0), m=ochre, bevel=0.005))
    # inner white block protruding into the frame, with vent plate and button
    o.append(rrect_ring(0.3, Y + 0.24, Z + 0.3, 0.025, (fx - 0.01, 0, 0), ochre, bevel=0.1))       # ochre liner inside the rim
    o.append(box((0.44, Y - 0.16, Z - 0.08), (fx + 0.02, 0, -0.03), m=W, bevel=0.07, segs=5))
    o.append(box((0.02, 0.2, 0.34), (fx + 0.245, -0.02, -0.08), m=P['steel'], bevel=0.03, segs=4))
    for k in range(7):
        o.append(box((0.012, 0.15, 0.012), (fx + 0.257, -0.02, 0.04 - k * 0.04), m=P['black'], bevel=0))
    o.append(cyl(0.04, 0.03, (fx + 0.255, -0.02, 0.2), (0, D(90), 0), P['steel'], bevel=0.008))
    for z in (0.12, -0.18):                                                                # side clamps on the frame
        o.append(box((0.16, 0.1, 0.12), (fx + 0.02, -Y / 2 - 0.2, z), m=P['black'], bevel=0.025))
    o.append(box((0.16, 0.12, 0.1), (fx + 0.02, 0.05, Z / 2 + 0.22), m=P['black'], bevel=0.025))
    for x in (-0.9, -0.2, 0.55):                                                           # small screws along the body
        for z in (0.16, -0.16):
            o.append(cyl(0.018, 0.012, (x, Y / 2 + 0.002, z), (D(90), 0, 0), P['steel'], verts=12, bevel=0.002))
    o.append(ring)
    group(o, rot=(0, 0, D(-88)))


# ------------------------------------------------------------------ ARC "driver" family v2 (Leaper Pulse Unit, Rocketeer Driver)
def driver_v2(P, cap_m, pin_m, strap=False, rear_flange=False):
    winding = mat('winding', (0.5, 0.26, 0.13), metal=0.9, rough=0.4, stripes=(420, (0.13, 0.065, 0.03), 'X'), dust=0.25, scratches=0.2)
    ridge = mat('ridge', (0.62, 0.34, 0.17), metal=1, rough=0.32, wear=0, scratches=0)
    o = []
    L = 1.5                                                        # core length; front at +X
    o.append(box((L, 0.52, 0.52), (0, 0, 0), m=P['black'], bevel=0.09, segs=4))
    for k in range(4):                                             # four faces: top, front(-Y), bottom, back(+Y)
        a = D(90 * k)
        n = (0, -math.sin(a), math.cos(a)); rot = (a, 0, 0)
        def at(d, lat=0.0):
            # point at distance d along the face normal, offset lat along the face's lateral axis
            t = (0, math.cos(a), math.sin(a))
            return (n[1] * d + t[1] * lat, n[2] * d + t[2] * lat)
        y, z = at(0.29)
        o.append(box((L - 0.02, 0.52, 0.07), (-0.02, y, z), rot, P['gun'], bevel=0.015))              # tray
        o.append(box((0.5, 0.3, 0.06), (L / 2 + 0.2, y, z), rot, P['gun'], bevel=0.015))           # prong running past the front
        for lat in (-0.115, 0.115):
            y2, z2 = at(0.335, lat)
            o.append(box((L - 0.12, 0.19, 0.03), (-0.05, y2, z2), rot, winding, bevel=0.004))            # copper winding pads
            yr, zr = at(0.352, lat)
            nr = 46
            for j in range(nr):                                                                             # raised winding ridges
                xr = -0.05 - (L - 0.16) / 2 + j * (L - 0.16) / (nr - 1)
                o.append(box((0.012, 0.18, 0.008), (xr, yr, zr), rot, ridge, bevel=0.0))
            y3, z3 = at(0.34, lat + (0.135 if lat > 0 else -0.135))
        y4, z4 = at(0.34, 0.0)
        o.append(box((L - 0.1, 0.03, 0.05), (-0.05, y4, z4), rot, P['gun'], bevel=0.006))               # centre divider
        for lat in (-0.235, 0.235):
            y5, z5 = at(0.345, lat)
            o.append(box((L - 0.05, 0.04, 0.07), (-0.05, y5, z5), rot, P['black'], bevel=0.01))         # side rails
        yc, zc = at(0.3)
        o.append(box((0.06, 0.32, 0.09), (L / 2 + 0.45, yc, zc), rot, cap_m, bevel=0.015))                   # front prong cap
        o.append(box((0.06, 0.54, 0.09), (L / 2 - 0.04, yc, zc), rot, cap_m, bevel=0.015))                   # tray front clamp
        o.append(box((0.06, 0.54, 0.09), (-L / 2 + 0.02, yc, zc), rot, cap_m, bevel=0.015))                 # rear cap
        for xb in (-0.35, 0.35):                                                                             # bolts on the caps
            pass
    # recessed connector between the prongs
    cx = L / 2 + 0.2
    o.append(cyl(0.21, 0.3, (cx, 0, 0), (0, D(90), 0), P['black'], bevel=0.02))
    o.append(torus(0.2, 0.024, (cx + 0.15, 0, 0), (0, D(90), 0), P['copper']))
    o.append(cyl(0.18, 0.02, (cx + 0.155, 0, 0), (0, D(90), 0), mat('connface', (0.05, 0.05, 0.055), rough=0.6, wear=0)))
    pins = [(0, 0)] + [(0.055 * math.cos(D(60 * i)), 0.055 * math.sin(D(60 * i))) for i in range(6)] + \
           [(0.108 * math.cos(D(30 * i + 15)), 0.108 * math.sin(D(30 * i + 15))) for i in range(12)]
    for py, pz in pins:
        o.append(cyl(0.021, 0.04, (cx + 0.175, py * 1.15, pz * 1.15), (0, D(90), 0), pin_m, verts=16, bevel=0.004))
    # rear: stepped black cylinder with grooves
    rx = -L / 2 - 0.3
    o.append(cyl(0.33, 0.55, (rx, 0, 0), (0, D(90), 0), P['rubber'], bevel=0.03))
    for k in range(5):
        o.append(torus(0.333, 0.012, (rx - 0.2 + k * 0.1, 0, 0), (0, D(90), 0), P['black']))
    o.append(cyl(0.36 if rear_flange else 0.3, 0.08, (rx - 0.3, 0, 0), (0, D(90), 0), P['steel'] if rear_flange else P['gun'], bevel=0.02))
    o.append(cyl(0.22, 0.04, (rx - 0.345, 0, 0), (0, D(90), 0), P['black'], bevel=0.008))
    o.append(cyl(0.27, 0.12, (-L / 2 - 0.02, 0, 0), (0, D(90), 0), P['gun'], bevel=0.02))
    if strap:   # woven green strap looping from the rear cylinder onto the top tray
        sm = mat('strap2', (0.12, 0.19, 0.08), rough=0.9, stripes=(260, (0.05, 0.08, 0.035), 'X'), wear=0, dust=0.2)
        n = 13
        for i in range(n):
            t = i / (n - 1); ang = math.pi * t
            x = rx - 0.05 + 0.62 * t; zz = 0.33 + 0.28 * math.sin(ang)
            tilt = math.atan2(0.28 * math.pi * math.cos(ang), 0.62)
            o.append(box((0.068, 0.2, 0.022), (x, 0, zz), (0, -tilt, 0), sm, bevel=0.004))
    return o


@item('leaper-pulse-unit', azim=-58, elev=34)
def leaper_pulse_unit(P):
    group(driver_v2(P, mat('capyellow', (0.62, 0.45, 0.08), metal=0.6, rough=0.4, wear=0.6, scratches=0.5, dust=0.2), P['copper'], strap=True), rot=(0, 0, D(-8)))


@item('rocketeer-driver', azim=-58, elev=34)
def rocketeer_driver(P):
    group(driver_v2(P, mat('capgreen', (0.22, 0.3, 0.17), metal=0.2, rough=0.55, wear=0.6, scratches=0.45, dust=0.25), P['blue'], rear_flange=True), rot=(0, 0, D(-8)))


# ------------------------------------------------------------------ Ion Sputter v2
@item('ion-sputter', azim=34, elev=30)
def ion_sputter(P):
    case = mat('iscase', (0.58, 0.56, 0.52), metal=0, rough=0.5, coat=0.1, bump=0.1, wear=0.85, scratches=0.8, dust=0.5, grime=0.9, tint_var=0.1)
    panel = mat('ispanel', (0.4, 0.45, 0.48), metal=0, rough=0.5, bump=0.05, wear=0.4, scratches=0.4, dust=0.2)
    sub = mat('issub', (0.3, 0.33, 0.35), metal=0, rough=0.55, wear=0.3, scratches=0.3)
    o = []
    W, Dp, H = 1.8, 1.3, 0.56                      # width (X), depth (Y), height (Z); front face at -Y
    o.append(box((W, Dp, H), (0, 0, 0), m=case, bevel=0.06, segs=5))
    # raised bezel around a recessed front panel
    fy = -Dp / 2
    o.append(box((W - 0.06, 0.04, H - 0.06), (0, fy - 0.01, 0), m=case, bevel=0.03, segs=4))
    o.append(box((W - 0.2, 0.03, H - 0.16), (0.03, fy - 0.025, -0.01), m=panel, bevel=0.012))
    # sub-panels
    for (x, w) in ((-0.55, 0.34), (0.42, 0.42)):
        o.append(box((w, 0.012, 0.24), (x, fy - 0.042, -0.01), m=sub, bevel=0.006))
    # red 7-segment readout
    o.append(box((0.22, 0.02, 0.07), (-0.55, fy - 0.05, 0.06), m=P['black'], bevel=0.006))
    o.append(box((0.19, 0.01, 0.045), (-0.55, fy - 0.058, 0.06), m=mat('isled', (0.35, 0.03, 0.02), rough=0.3, emission=(1, 0.1, 0.03, 4), wear=0), bevel=0.002))
    # button grids: red and black keys
    keys = []
    for gx0, cols, rows in ((-0.64, 3, 2), (0.27, 3, 2)):
        for r in range(rows):
            for c in range(cols):
                keys.append((gx0 + c * 0.065, -0.04 - r * 0.06, (r + c) % 3 == 0))
    for x, z, red in keys:
        o.append(box((0.042, 0.03, 0.032), (x, fy - 0.055, z), m=P['red'] if red else P['black'], bevel=0.007))
    # analog meter: black bezel, cream face, glass, needle, scale ticks
    o.append(box((0.42, 0.05, 0.27), (-0.05, fy - 0.05, -0.01), m=P['black'], bevel=0.02))
    o.append(box((0.36, 0.02, 0.21), (-0.05, fy - 0.07, -0.01), m=mat('isdial', (0.82, 0.79, 0.68), rough=0.45, wear=0.2, dust=0.1), bevel=0.004))
    for k in range(11):
        a = D(-50 + k * 10)
        o.append(box((0.003, 0.004, 0.03 if k % 5 == 0 else 0.018), (-0.05 + math.sin(a) * 0.12, fy - 0.081, -0.07 + math.cos(a) * 0.12), (0, a, 0), P['black'], bevel=0))
    o.append(box((0.004, 0.006, 0.15), (-0.05 + 0.03, fy - 0.084, -0.04), (0, D(22), 0), mat('needle', (0.6, 0.05, 0.03), rough=0.4, wear=0), bevel=0))
    # rotary knob with skirt
    o.append(cyl(0.065, 0.02, (0.66, fy - 0.05, -0.02), (D(90), 0, 0), P['steel'], bevel=0.004))
    o.append(cyl(0.048, 0.07, (0.66, fy - 0.085, -0.02), (D(90), 0, 0), P['black'], bevel=0.01))
    o.append(box((0.012, 0.02, 0.06), (0.66, fy - 0.12, 0.0), m=P['steel'], bevel=0.003))
    # left-side perforated vent
    sx = -W / 2
    o.append(box((0.01, 0.42, 0.24), (sx - 0.003, -0.25, -0.03), m=sub, bevel=0.004))
    for r in range(8):
        for c in range(14):
            o.append(cyl(0.008, 0.012, (sx - 0.006, -0.44 + c * 0.029, 0.065 - r * 0.027), (0, D(90), 0), P['black'], verts=8, bevel=0))
    # top: recessed circular well with a ribbed chrome spindle stack
    tz = H / 2
    wx, wy = -0.2, 0.0
    well = cyl(0.33, 0.06, (wx, wy, tz - 0.02), m=sub, bevel=0.01)
    o.append(torus(0.335, 0.018, (wx, wy, tz + 0.005), m=case))
    o.append(cyl(0.25, 0.04, (wx, wy, tz + 0.02), m=P['steel'], bevel=0.008))
    for k in range(6):
        o.append(cyl(0.2 - k * 0.006, 0.022, (wx, wy, tz + 0.055 + k * 0.026), m=P['chrome'], bevel=0.006))
        o.append(torus(0.2 - k * 0.006, 0.006, (wx, wy, tz + 0.067 + k * 0.026), m=P['steel']))
    o.append(cyl(0.12, 0.05, (wx, wy, tz + 0.23), m=P['steel'], bevel=0.008))
    o.append(cyl(0.05, 0.07, (wx, wy, tz + 0.29), m=P['black'], bevel=0.008))
    # terminal posts on a recessed dark strip at the back-left, cables arcing to the spindle top
    o.append(box((0.4, 0.14, 0.02), (-0.66, 0.38, tz + 0.002), m=P['black'], bevel=0.008))
    for k in range(4):
        px, py = -0.78 + k * 0.08, 0.38
        o.append(cyl(0.028, 0.08, (px, py, tz + 0.04), m=P['black'], bevel=0.006))
        o.append(cyl(0.018, 0.03, (px, py, tz + 0.095), m=P['brass'], bevel=0.004))
    cab = [mat('iscab1', (0.45, 0.06, 0.04), rough=0.45, wear=0, dust=0.1), mat('iscab2', (0.06, 0.06, 0.07), rough=0.5, wear=0)]
    for k in range(4):
        px, py = -0.78 + k * 0.08, 0.38
        tube([(px, py, tz + 0.1), (px, py - 0.05, tz + 0.45), (px + 0.25, py - 0.2, tz + 0.62), (wx - 0.04 + k * 0.02, wy + 0.05, tz + 0.5), (wx - 0.03 + k * 0.02, wy, tz + 0.32)], 0.012, cab[k % 2])
    # flat dish on the right and a label plate
    o.append(cyl(0.27, 0.025, (0.45, 0.22, tz + 0.012), m=mat('isdish', (0.42, 0.44, 0.45), metal=0.8, rough=0.45, scratches=0.6, dust=0.4), bevel=0.008))
    o.append(torus(0.27, 0.01, (0.45, 0.22, tz + 0.025), m=P['steel']))
    o.append(box((0.32, 0.18, 0.008), (0.45, -0.32, tz + 0.004), m=mat('islabel', (0.42, 0.44, 0.45), metal=0.6, rough=0.4, scratches=0.5), bevel=0.003))
    # rubber feet
    for x in (-W / 2 + 0.15, W / 2 - 0.15):
        for y in (-Dp / 2 + 0.15, Dp / 2 - 0.15):
            o.append(cyl(0.05, 0.03, (x, y, -H / 2 - 0.012), m=P['rubber'], bevel=0.006))


def on_sphere(R, a, e):
    return (R * math.cos(D(e)) * math.sin(D(a)), -R * math.cos(D(e)) * math.cos(D(a)), R * math.sin(D(e)))


def sphere_patch(R, a, e, w, h, depth, m, bevel=0.02):
    """A thin panel lying on the sphere surface at azimuth a / elevation e, facing outward."""
    x, y, z = on_sphere(R, a, e)
    return box((w, depth, h), (x, y, z), (D(-e), 0, D(a)), m, bevel=bevel)


# ------------------------------------------------------------------ Surveyor Vault v2
@item('surveyor-vault', azim=-28, elev=20)
def surveyor_vault(P):
    shell = mat('svshell', (0.36, 0.37, 0.38), metal=0.55, rough=0.3, coat=0.35, bump=0.05, wear=0.6, scratches=0.65, dust=0.3, grime=0.7)
    dark = mat('svdark', (0.08, 0.085, 0.09), metal=0.6, rough=0.45, wear=0.5, scratches=0.5, dust=0.3)
    R = 0.9
    s = sphere(R, (0, 0, 0), shell)
    # front-left vertical access slot (boolean) with a stacked lock mechanism inside
    cut = box((0.36, 0.7, 0.92), (0.0, 0, 0.12), m=None, bevel=0.04)
    cx, cy, _ = on_sphere(R - 0.05, +6, 0)
    cut.location = (cx, cy, 0); cut.rotation_euler = (0, 0, D(6))
    boolean(s, cut)
    bx, by, _ = on_sphere(R - 0.22, +6, 0)
    lx, ly, _ = on_sphere(R - 0.32, +6, 0)
    box((0.35, 0.04, 0.9), (lx, ly, 0.12), (0, 0, D(6)), mat('svcav', (0.03, 0.03, 0.035), rough=0.7, wear=0), bevel=0.01)
    for k, (h, w) in enumerate(((0.16, 0.13), (0.12, 0.1), (0.14, 0.12), (0.1, 0.09), (0.16, 0.13))):
        box((w, 0.16, h), (bx, by, 0.42 - k * 0.17), (0, 0, D(6)), P['chrome'] if k % 2 else P['steel'], bevel=0.02)
    box((0.06, 0.1, 0.8), (bx * 1.06, by * 1.06, 0.1), (0, 0, D(6)), P['gun'], bevel=0.01)
    box((0.26, 0.24, 0.06), (bx * 1.02, by * 1.02, -0.32), (0, 0, D(6)), P['steel'], bevel=0.015)
    # equator seam and a second panel line
    torus(math.sqrt(R * R - 0.22 ** 2) + 0.002, 0.009, (0, 0, -0.22), m=dark)
    torus(math.sqrt(R * R - 0.3 ** 2) + 0.002, 0.008, (0, 0, 0.3), m=dark)
    # top collar: brass ring, stepped dark rings, notched lip
    zt = R * 0.88
    torus(0.46, 0.022, (0, 0, zt - 0.03), m=P['brass'])
    cyl(0.44, 0.1, (0, 0, zt + 0.02), m=dark, bevel=0.02)
    cyl(0.38, 0.08, (0, 0, zt + 0.1), m=P['gun'], bevel=0.02)
    torus(0.36, 0.03, (0, 0, zt + 0.15), m=dark)
    for k in range(6):
        a = D(k * 60 + 15)
        box((0.1, 0.06, 0.06), (math.cos(a) * 0.36, math.sin(a) * 0.36, zt + 0.17), (0, 0, a), dark, bevel=0.012)
    cyl(0.27, 0.04, (0, 0, zt + 0.12), m=P['black'], bevel=0.01)
    # riveted hatch panel lower-right and a small vent plate upper-right
    sphere_patch(R + 0.005, 30, -30, 0.42, 0.22, 0.03, mat('svhatch', (0.4, 0.41, 0.42), metal=0.4, rough=0.35, wear=0.6, scratches=0.6), bevel=0.04)
    for k in range(6):
        sphere(0.012, on_sphere(R + 0.025, 20 + k * 4, -23.5), P['steel'])
        sphere(0.012, on_sphere(R + 0.025, 20 + k * 4, -36.5), P['steel'])
    sphere_patch(R + 0.003, 40, 32, 0.2, 0.12, 0.03, dark, bevel=0.015)
    for k in range(4):
        sphere_patch(R + 0.02, 40, 29 + k * 2.2, 0.15, 0.008, 0.01, P['black'], bevel=0)
    # brass binding wire with domed fittings
    W1 = [(-60, 50), (-38, 18), (-18, -10), (5, -32), (32, -40), (55, -20), (68, 10)]
    W2 = [(-90, -5), (-62, -28), (-30, -42), (5, -26), (28, 8), (40, 42)]
    wire = mat('svwire', (0.55, 0.42, 0.18), metal=1, rough=0.4, scratches=0.3)
    sphere_path(W1, R + 0.015, m=wire, r=0.011); sphere_path(W2, R + 0.015, m=wire, r=0.011)
    for a, e in (W1[1], W1[3], W1[-1], W2[1], W2[3], W2[-1]):
        x, y, z = on_sphere(R, a, e)
        sphere(0.06, (x, y, z), P['steel'], scale=(1, 1, 1))
        torus(0.06, 0.012, (x, y, z), (D(90 - e), 0, D(a)), P['gun'])


def oct_prism(r, length, loc, m, bevel=0.02, sz=1.0):
    p = prism(r, length, 8, loc, (0, D(90), 0), m, bevel=bevel, twist=D(22.5)); p.scale = (1, 1, sz)
    return p


# ------------------------------------------------------------------ Hornet Driver v2
@item('hornet-driver', azim=-40, elev=26)
def hornet_driver(P):
    body = mat('hdbody', (0.06, 0.065, 0.07), metal=0.55, rough=0.45, wear=0.7, scratches=0.65, dust=0.35, grime=0.7)
    bronze = mat('hdbronze', (0.27, 0.17, 0.08), metal=0.9, rough=0.45, wear=0.6, scratches=0.55, dust=0.3)
    bluec = mat('hdblue', (0.05, 0.26, 0.6), rough=0.45, wear=0, dust=0.15)
    yel = mat('hdyel', (0.6, 0.45, 0.12), metal=0.6, rough=0.4, wear=0)
    tape = mat('hdtape', (0.34, 0.35, 0.36), metal=0.25, rough=0.55, bump=0.4, noise_scale=35, scratches=0.3, wear=0, dust=0.2)
    o = []
    L = 2.0
    # open octagonal shell: build from 8 face plates, leave the two front-left faces off to expose the interior
    r = 0.4
    for k in range(8):
        if k in (3, 4): continue
        a = D(22.5 + 45 * k)
        o.append(box((L, 0.31, 0.05), (0, math.cos(a) * r * 0.93, math.sin(a) * r * 0.93), (a + D(90), 0, 0), body, bevel=0.012))
    # interior: blue ribbon cables and copper windings visible through the opening
    for k in range(5):
        tube([(-0.9, -0.2 - k * 0.02, -0.18 + k * 0.07), (-0.3, -0.3, -0.2 + k * 0.07), (0.3, -0.28, -0.14 + k * 0.06), (0.9, -0.2, -0.16 + k * 0.07)], 0.024, bluec)
    o.append(box((0.9, 0.3, 0.28), (-0.15, 0.02, -0.02), m=mat('hdcoil', (0.35, 0.16, 0.08), metal=0.85, rough=0.4, stripes=(300, (0.12, 0.05, 0.02), 'X')), bevel=0.04))
    # grey duct-tape wrap around the middle
    o.append(cyl(r + 0.025, 0.42, (-0.2, 0, 0), (0, D(90), 0), tape, verts=10, bevel=0.0))
    o.append(cyl(r + 0.03, 0.06, (-0.42, 0, 0), (0, D(90), D(4)), tape, verts=10, bevel=0.0))
    # bronze octagonal front collar and dark recessed face with a bundle of tube ends
    fx = L / 2 + 0.12
    o.append(oct_prism(r + 0.06, 0.28, (fx, 0, 0), bronze, bevel=0.03))
    o.append(cyl(0.28, 0.08, (fx + 0.15, 0, 0), (0, D(90), 0), P['steel'], bevel=0.02))
    o.append(cyl(0.24, 0.05, (fx + 0.18, 0, 0), (0, D(90), 0), P['black'], bevel=0.01))
    ends = [(0, 0)] + [(0.085 * math.cos(D(60 * k)), 0.085 * math.sin(D(60 * k))) for k in range(6)] + [(0.17 * math.cos(D(30 * k)), 0.17 * math.sin(D(30 * k))) for k in range(12)]
    for i, (py, pz) in enumerate(ends):
        mm = yel if i % 3 == 0 else bluec
        o.append(cyl(0.036, 0.12, (fx + 0.2, py, pz), (0, D(90), 0), mm, verts=20, bevel=0.006))
        o.append(cyl(0.02, 0.125, (fx + 0.205, py, pz), (0, D(90), 0), P['black'], verts=16, bevel=0))
    # rear cap
    o.append(oct_prism(r + 0.03, 0.12, (-L / 2 - 0.04, 0, 0), P['gun'], bevel=0.02))
    # long skid plate under the body
    o.append(box((L * 0.9, 0.36, 0.06), (-0.05, 0, -r - 0.12), m=P['gun'], bevel=0.015))
    for x in (-0.6, 0.0, 0.6):
        o.append(box((0.08, 0.2, 0.12), (x, 0, -r - 0.05), m=body, bevel=0.012))
    # top rail frame with a taped pipe and blue/yellow wires running to the front
    for y in (-0.12, 0.12):
        o.append(box((L * 0.8, 0.03, 0.03), (-0.1, y, r + 0.12), m=P['steel'], bevel=0.006))
        for x in (-0.8, 0.0, 0.7):
            o.append(box((0.03, 0.03, 0.12), (x, y, r + 0.06), m=P['steel'], bevel=0.005))
    o.append(cyl(0.035, L * 0.75, (-0.1, 0, r + 0.15), (0, D(90), 0), P['gun'], bevel=0.005))
    o.append(cyl(0.05, 0.3, (0.2, 0, r + 0.15), (0, D(90), 0), tape, verts=10, bevel=0))
    tube([(-0.9, -0.05, r + 0.1), (-0.2, -0.08, r + 0.2), (0.6, -0.06, r + 0.12), (fx + 0.1, -0.1, 0.25), (fx + 0.15, -0.08, 0.1)], 0.018, bluec)
    tube([(-0.85, 0.05, r + 0.08), (-0.1, 0.06, r + 0.22), (0.7, 0.02, r + 0.1), (fx + 0.12, 0.05, 0.22), (fx + 0.16, 0.03, 0.12)], 0.01, yel)


# ------------------------------------------------------------------ Spotter Relay v2
@item('spotter-relay', azim=-44, elev=28)
def spotter_relay(P):
    W = mat('srwhite', (0.55, 0.56, 0.55), metal=0, rough=0.48, coat=0.15, bump=0.08, wear=0.7, scratches=0.6, dust=0.35, grime=0.7)
    tanp = mat('srtan', (0.55, 0.36, 0.18), metal=0, rough=0.62, bump=0.2, noise_scale=30, wear=0.5, scratches=0.4, dust=0.3)
    pad = mat('srpad', (0.08, 0.085, 0.09), metal=0.1, rough=0.7, bump=0.25, wear=0.3, scratches=0.2, dust=0.4)
    o = []
    L = 1.9
    # flattened octagonal hull with chamfered ends
    o.append(oct_prism(0.42, L, (0, 0, 0), W, bevel=0.04, sz=0.78))
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.42, radius2=0.3, depth=0.3, location=(L / 2 + 0.15, 0, 0), rotation=(0, D(90), D(22.5)))
    nose = bpy.context.object; nose.scale = (0.78, 1, 1); nose.data.materials.append(P['gun'])
    bpy.ops.mesh.primitive_cone_add(vertices=8, radius1=0.42, radius2=0.25, depth=0.3, location=(-L / 2 - 0.15, 0, 0), rotation=(0, D(-90), D(22.5)))
    tail = bpy.context.object; tail.scale = (0.78, 1, 1); tail.data.materials.append(W)
    # white saddle band wrapping over the top in the middle
    sb = oct_prism(0.45, 0.42, (-0.1, 0, 0.0), W, bevel=0.05, sz=0.82)
    # tan armour panels along the lower flanks, with dark edging
    for side in (-1, 1):
        for x0, x1 in ((-L / 2 + 0.05, -0.33), (0.13, L / 2 - 0.05)):
            o.append(box((x1 - x0, 0.045, 0.34), ((x0 + x1) / 2, side * 0.39, -0.08), (D(-22 * side), 0, 0), tanp, bevel=0.012))
            o.append(box((x1 - x0, 0.05, 0.03), ((x0 + x1) / 2, side * 0.43, 0.09), (D(-22 * side), 0, 0), P['black'], bevel=0.006))
            o.append(box((x1 - x0, 0.05, 0.03), ((x0 + x1) / 2, side * 0.355, -0.25), (D(-22 * side), 0, 0), P['black'], bevel=0.006))
    # two dark rounded pads on top
    for x in (-0.55, 0.42):
        o.append(box((0.36, 0.52, 0.16), (x, 0, 0.33), m=pad, bevel=0.07, segs=5))
    # front hub: dark octagon ring, lens cap with a slot
    hx = L / 2 + 0.32
    o.append(oct_prism(0.31, 0.1, (hx, 0, 0), P['gun'], bevel=0.02, sz=0.95))
    o.append(cyl(0.25, 0.2, (hx + 0.1, 0, 0), (0, D(90), 0), P['rubber'], bevel=0.035))
    o.append(cyl(0.2, 0.03, (hx + 0.21, 0, 0), (0, D(90), 0), P['steel'], bevel=0.008))
    o.append(box((0.03, 0.24, 0.07), (hx + 0.235, 0, 0), m=P['black'], bevel=0.012))
    # dark wing fins at the front corners
    for a in (D(30), D(150)):
        o.append(box((0.22, 0.02, 0.14), (L / 2 + 0.12, math.cos(a) * 0.36, math.sin(a) * 0.26 + 0.04), (a - D(90), 0, D(-10)), P['gun'], bevel=0.005))
    # rear access hatch on the white tail
    o.append(box((0.22, 0.3, 0.02), (-L / 2 + 0.2, 0, 0.33), m=P['grey'], bevel=0.01))


# ------------------------------------------------------------------ Advanced Electrical Components v2 (ribbed tray of parts)
@item('advanced-electrical-components', azim=-30, elev=46)
def advanced_electrical_components(P):
    shell = mat('aectray', (0.3, 0.31, 0.31), metal=0.1, rough=0.55, bump=0.1, wear=0.6, scratches=0.55, dust=0.4, grime=0.8)
    floor = mat('aecfloor', (0.25, 0.3, 0.25), metal=0, rough=0.62, bump=0.08, wear=0.3, scratches=0.3, dust=0.35, grime=0.9)
    o = []
    X, Y, Hh = 1.7, 1.36, 0.3
    o.append(box((X, Y, 0.06), (0, 0, -Hh / 2 + 0.03), m=shell, bevel=0.02))
    for (sx, sy, x, y) in ((X, 0.07, 0, -Y / 2 + 0.035), (X, 0.07, 0, Y / 2 - 0.035), (0.07, Y, -X / 2 + 0.035, 0), (0.07, Y, X / 2 - 0.035, 0)):
        o.append(box((sx, sy, Hh), (x, y, 0), m=shell, bevel=0.02))
    # lip and outer vertical ribs
    for k in range(16):
        x = -X / 2 + 0.08 + k * (X - 0.16) / 15
        o.append(box((0.04, 0.05, Hh - 0.04), (x, -Y / 2 - 0.02, -0.01), m=shell, bevel=0.008))
    for k in range(13):
        y = -Y / 2 + 0.08 + k * (Y - 0.16) / 12
        o.append(box((0.05, 0.04, Hh - 0.04), (X / 2 + 0.02, y, -0.01), m=shell, bevel=0.008))
    # handles / latches on the sides
    for x in (-0.45, 0.45):
        o.append(box((0.24, 0.06, 0.07), (x, -Y / 2 - 0.06, Hh / 2 - 0.04), m=P['gun'], bevel=0.015))
        o.append(box((0.24, 0.06, 0.07), (x, Y / 2 + 0.05, Hh / 2 - 0.04), m=P['gun'], bevel=0.015))
    for y in (-0.35, 0.35):
        o.append(box((0.06, 0.2, 0.07), (-X / 2 - 0.05, y, Hh / 2 - 0.04), m=P['gun'], bevel=0.015))
    # green floor and compartment dividers
    fz = -Hh / 2 + 0.065
    o.append(box((X - 0.14, Y - 0.14, 0.01), (0, 0, fz), m=floor, bevel=0))
    div = [((0.02, Y - 0.14, 0.18), (-0.33, 0, fz + 0.09)), ((0.02, Y - 0.14, 0.18), (0.22, 0, fz + 0.09)),
           ((0.53, 0.02, 0.18), (-0.055, 0.12, fz + 0.09)), ((0.53, 0.02, 0.18), (-0.055, -0.22, fz + 0.09)),
           ((0.6, 0.02, 0.18), (0.53, 0.18, fz + 0.09)), ((0.6, 0.02, 0.18), (0.53, -0.25, fz + 0.09)), ((0.02, 0.43, 0.18), (0.53, -0.47, fz + 0.09))]
    for sz, loc in div:
        o.append(box(sz, loc, m=floor, bevel=0.004))
    # contents: wire bundle (long left bay), chips, brass connectors, blue PCB with a component grid
    for k, mm in enumerate((P['red'], P['blue'], P['red'], P['blue'], mat('aecwh', (0.6, 0.6, 0.58), rough=0.5, wear=0))):
        tube([(-0.7 + k * 0.02, -0.55, fz + 0.03 + k * 0.006), (-0.62 + k * 0.025, -0.1, fz + 0.04), (-0.52 + k * 0.025, 0.3, fz + 0.03), (-0.48 + k * 0.02, 0.58, fz + 0.035)], 0.012, mm)
    random.seed(11)
    for bay in ((-0.3, 0.2, 0.15, 0.6), (-0.3, 0.2, -0.2, 0.1)):
        for k in range(5):
            x = random.uniform(bay[0] + 0.05, bay[1] - 0.05); y = random.uniform(bay[2] + 0.05, bay[3] - 0.05)
            o.append(box((0.07, 0.07, 0.02), (x, y, fz + 0.015), (0, 0, random.uniform(0, 1.5)), P['black'], bevel=0.004))
            for j in range(3):
                o.append(box((0.006, 0.02, 0.004), (x - 0.02 + j * 0.02, y - 0.042, fz + 0.012), m=P['steel'], bevel=0))
    for k in range(4):
        x = random.uniform(-0.25, 0.15); y = random.uniform(-0.6, -0.3)
        o.append(cyl(0.03, 0.07, (x, y, fz + 0.03), (D(90), 0, random.uniform(0, 3)), P['brass'], verts=16, bevel=0.004))
    pcb = mat('aecpcb', (0.12, 0.25, 0.55), metal=0.1, rough=0.4, wear=0.3, scratches=0.3)
    o.append(box((0.48, 0.32, 0.012), (0.56, 0.42, fz + 0.03), (0, 0, D(-12)), pcb, bevel=0.003))
    for r in range(3):
        for c in range(6):
            x, y = 0.39 + c * 0.065, 0.34 + r * 0.075
            xr = 0.56 + (x - 0.56) * math.cos(D(-12)) - (y - 0.42) * math.sin(D(-12)); yr = 0.42 + (x - 0.56) * math.sin(D(-12)) + (y - 0.42) * math.cos(D(-12))
            o.append(box((0.04, 0.035, 0.018), (xr, yr, fz + 0.045), (0, 0, D(-12)), P['black'], bevel=0.003))
    for k in range(3):
        o.append(box((0.12, 0.05, 0.04), (0.45 + k * 0.15, -0.05, fz + 0.025), m=P['gun'], bevel=0.006))
    o.append(box((0.22, 0.14, 0.05), (0.5, -0.45, fz + 0.03), m=P['black'], bevel=0.008))


# ------------------------------------------------------------------ Comet Igniter v2
@item('comet-igniter', azim=-58, elev=14)
def comet_igniter(P):
    W = mat('cishell', (0.55, 0.55, 0.54), metal=0.1, rough=0.42, coat=0.25, bump=0.06, wear=0.6, scratches=0.55, dust=0.3, grime=0.7)
    seamm = mat('ciseam', (0.12, 0.12, 0.12), rough=0.6, wear=0)
    o = []
    R = 0.85
    # two shell halves (front half shortened) split by a deep dark ribbed band
    for side, cut_at in ((-1, -0.2), (1, 0.2)):
        sh = sphere(R, (0, 0, 0), W)
        c = box((3, 3, 3), (cut_at - side * 1.5, 0, 0), m=None, bevel=0)
        boolean(sh, c)
        o.append(sh)
        for t in (0.5,):                                                            # panel lines across the shell
            x = side * (0.2 + t * 0.55)
            rr = math.sqrt(max(R * R - x * x, 0.01))
            o.append(torus(rr + 0.003, 0.007, (x, 0, 0), (0, D(90), 0), seamm))
    o.append(cyl(0.76, 0.4, (0, 0, 0), (0, D(90), 0), P['black'], bevel=0.02))
    for k in range(13):
        o.append(torus(0.745, 0.012, (-0.18 + k * 0.03, 0, 0), (0, D(90), 0), P['gun']))
    for k in range(10):                                                                   # spokes visible in the band
        a = D(k * 36)
        o.append(box((0.36, 0.04, 0.12), (0, math.cos(a) * 0.76, math.sin(a) * 0.76), (a, 0, 0), P['gun'], bevel=0.01))
    # oval faceplate on the front half with a black capsule window and two stacked lenses
    fx = R * 0.9
    plate = cyl(0.5, 0.2, (fx, 0, 0), (0, D(90), 0), W, bevel=0.06); plate.scale = (1.15, 0.8, 1)
    o.append(torus(0.5, 0.014, (fx + 0.05, 0, 0), (D(90), D(90), 0), seamm)) if False else None
    ring = torus(0.5, 0.016, (fx + 0.07, 0, 0), (0, D(90), 0), seamm); ring.scale = (1.15, 0.8, 1)
    win = cyl(0.17, 0.12, (fx + 0.1, 0, 0), (0, D(90), 0), P['black'], bevel=0.05); win.scale = (2.0, 1, 1)
    for z in (0.15, -0.15):
        o.append(cyl(0.11, 0.06, (fx + 0.15, 0, z), (0, D(90), 0), P['glass'], bevel=0.01))
        o.append(torus(0.115, 0.016, (fx + 0.18, 0, z), (0, D(90), 0), P['gun']))
        o.append(cyl(0.05, 0.02, (fx + 0.185, 0, z), (0, D(90), 0), mat('cilens', (0.03, 0.05, 0.06), rough=0.03, coat=1, spec=1, wear=0)))
