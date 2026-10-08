"""The Raider Network — modernized item icon renderer (Blender/bpy, Cycles).

Every icon is modelled procedurally from scratch (geometry + PBR materials) using the RaidTheory in-game icon only
as a visual reference for shape, proportions, colours and identifying features. No reference pixels are copied,
traced or filtered into the output. All items share one studio: camera angle, lights, shadow and framing.

    blendenv/bin/python trn3d.py leaper-pulse-unit bastion-cell ...   (no args = all registered items)
Outputs: renders/<id>.png (1024 RGBA master)  ->  web/<id>.webp (512, transparent)"""
import bpy, bmesh, math, os, sys, time
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PNG = os.path.join(HERE, 'renders'); OUT_WEB = os.path.join(HERE, 'web')
RES = int(os.environ.get("TRN_RES", 1024)); SAMPLES = int(os.environ.get("TRN_SAMPLES", 96))
D = math.radians

# ------------------------------------------------------------------ scene
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = SAMPLES
    s.cycles.use_denoising = True; s.cycles.max_bounces = 8
    s.render.film_transparent = True; s.render.resolution_x = s.render.resolution_y = RES
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Punchy'; s.view_settings.exposure = -0.7
    s.render.image_settings.file_format = 'PNG'; s.render.image_settings.color_mode = 'RGBA'
    w = bpy.data.worlds.new('studio'); s.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    # soft studio gradient for reflections: brighter overhead, dark floor
    tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); nt.links.new(sep.outputs['Z'], ramp.inputs[0])
    ramp.color_ramp.elements[0].position = 0.45; ramp.color_ramp.elements[0].color = (0.015, 0.02, 0.024, 1)
    ramp.color_ramp.elements[1].position = 0.75; ramp.color_ramp.elements[1].color = (0.42, 0.46, 0.5, 1)
    nt.links.new(ramp.outputs[0], bg.inputs['Color']); bg.inputs['Strength'].default_value = 0.35
    return s

def lights(target_r=1.0):
    def area(name, loc, energy, size, color):
        bpy.ops.object.light_add(type='AREA', location=loc); L = bpy.context.object; L.name = name
        L.data.energy = energy * target_r ** 2; L.data.size = size * target_r; L.data.color = color
        L.rotation_euler = (Vector((0, 0, 0)) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
        return L
    r = target_r * 3.2
    area('key', (-r * 0.55, -r * 0.9, r * 1.05), 600, 2.0, (1.0, 0.95, 0.88))       # warm key, front-left high
    area('fill', (r * 1.1, -r * 0.55, r * 0.35), 70, 3.2, (0.85, 0.92, 1.0))       # cool soft fill, right
    area('rim', (r * 0.4, r * 1.15, r * 0.9), 420, 1.6, (0.55, 0.95, 1.0))          # teal-cyan rim (brand accent)
    area('top', (0, 0, r * 1.5), 90, 4.0, (1, 1, 1))

def shadow_catcher(z, size=30):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, z)); p = bpy.context.object
    p.is_shadow_catcher = True; p.name = 'shadow'
    return p

def frame_camera(objs, azim=-38, elev=24, lens=70, pad=1.12):
    """3/4 view from front-right, auto-fit to the objects' projected bounds."""
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (lo + hi) / 2
    d = Vector((math.cos(D(elev)) * math.sin(D(azim)) * -1, -math.cos(D(elev)) * math.cos(D(azim)), math.sin(D(elev))))
    bpy.ops.object.camera_add(); cam = bpy.context.object; cam.data.lens = lens; cam.data.sensor_width = 36
    bpy.context.scene.camera = cam
    fov = 2 * math.atan(18 / lens)
    rot = (-d).to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    # iterative fit: place camera, measure projected extent, adjust distance
    dist = (hi - lo).length * 1.5
    from bpy_extras.object_utils import world_to_camera_view
    sc = bpy.context.scene
    for _ in range(6):
        cam.location = ctr + d * dist; bpy.context.view_layer.update()
        uv = [world_to_camera_view(sc, cam, p) for p in pts]
        xs = [u.x for u in uv]; ys = [u.y for u in uv]
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        dist *= span * pad
    # centre the projected box
    bpy.context.view_layer.update()
    uv = [world_to_camera_view(sc, cam, p) for p in pts]
    cx = (max(u.x for u in uv) + min(u.x for u in uv)) / 2 - 0.5; cy = (max(u.y for u in uv) + min(u.y for u in uv)) / 2 - 0.5
    cam.data.shift_x = cx; cam.data.shift_y = cy
    return cam, (hi - lo).length / 2, lo.z

# ------------------------------------------------------------------ materials
_mats = {}
def mat(name, color, metal=0.0, rough=0.4, coat=0.0, bump=0.0, wear=0.35, stripes=None, emission=None, noise_scale=60, tint_var=0.06, spec=0.5,
        scratches=0.0, scratch_scale=9.0, dust=0.0, grime=0.55):
    """Physically based material with subtle grime/roughness breakup, optional bevelled edges and stripes."""
    key = name
    if key in _mats: return _mats[key]
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
    b = N['Principled BSDF']
    b.inputs['Metallic'].default_value = metal; b.inputs['Coat Weight'].default_value = coat
    b.inputs['Specular IOR Level'].default_value = spec
    tc = N.new('ShaderNodeTexCoord')
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = noise_scale; nz.inputs['Detail'].default_value = 8
    Lk(tc.outputs['Object'], nz.inputs['Vector'])
    # roughness breakup
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = max(0.02, rough - 0.1); mr.inputs['To Max'].default_value = min(1, rough + 0.12)
    Lk(nz.outputs['Fac'], mr.inputs['Value']); Lk(mr.outputs['Result'], b.inputs['Roughness'])
    # colour variation (grime)
    big = N.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 6; big.inputs['Detail'].default_value = 4
    Lk(tc.outputs['Object'], big.inputs['Vector'])
    c2 = tuple(max(0, x * (1 - tint_var * 2.2)) for x in color[:3]) + (1,)
    mix = N.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['A'].default_value = tuple(color[:3]) + (1,); mix.inputs['B'].default_value = c2
    Lk(big.outputs['Fac'], mix.inputs['Factor'])
    col_out = mix.outputs['Result']
    if stripes:  # (scale, dark colour, axis) — e.g. copper coil windings or grille slats
        sc, dark, axis = stripes
        wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = axis; wv.inputs['Scale'].default_value = sc
        wv.inputs['Distortion'].default_value = 0.0; wv.inputs['Detail'].default_value = 0
        Lk(tc.outputs['Object'], wv.inputs['Vector'])
        ramp = N.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.6
        Lk(wv.outputs['Fac'], ramp.inputs[0])
        m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.inputs['B'].default_value = tuple(dark) + (1,)
        Lk(col_out, m2.inputs['A']); Lk(ramp.outputs[0], m2.inputs['Factor']); col_out = m2.outputs['Result']
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.004
        Lk(wv.outputs['Fac'], bp.inputs['Height'])
        bump_node = bp
    else:
        bump_node = None
    # cavity grime (ambient occlusion) and worn/highlighted edges (bevel normal vs true normal)
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = 0.09; ao.only_local = True
    dirt = N.new('ShaderNodeMix'); dirt.data_type = 'RGBA'; dirt.blend_type = 'MULTIPLY'
    aor = N.new('ShaderNodeMapRange'); aor.inputs['To Min'].default_value = 0.0; aor.inputs['To Max'].default_value = 1.0
    Lk(ao.outputs['AO'], aor.inputs['Value'])
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; Lk(aor.outputs['Result'], inv.inputs[1])
    dirt.inputs['B'].default_value = (0.2, 0.17, 0.13, 1); Lk(col_out, dirt.inputs['A'])
    gm = N.new('ShaderNodeMath'); gm.operation = 'MULTIPLY'; gm.use_clamp = True; Lk(inv.outputs[0], gm.inputs[0]); gm.inputs[1].default_value = grime * 1.8
    Lk(gm.outputs[0], dirt.inputs['Factor'])
    col_out = dirt.outputs['Result']
    if wear:
        ebev = N.new('ShaderNodeBevel'); ebev.inputs['Radius'].default_value = 0.02; ebev.samples = 8
        geo = N.new('ShaderNodeNewGeometry')
        dot = N.new('ShaderNodeVectorMath'); dot.operation = 'DOT_PRODUCT'
        Lk(ebev.outputs['Normal'], dot.inputs[0]); Lk(geo.outputs['Normal'], dot.inputs[1])
        em = N.new('ShaderNodeMapRange'); em.inputs['From Min'].default_value = 0.93; em.inputs['From Max'].default_value = 0.995
        em.inputs['To Min'].default_value = 1.0; em.inputs['To Max'].default_value = 0.0
        Lk(dot.outputs['Value'], em.inputs['Value'])
        ns = N.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 25; ns.inputs['Detail'].default_value = 6
        Lk(tc.outputs['Object'], ns.inputs['Vector'])
        msk = N.new('ShaderNodeMath'); msk.operation = 'MULTIPLY'; Lk(em.outputs['Result'], msk.inputs[0]); Lk(ns.outputs['Fac'], msk.inputs[1])
        msk2 = N.new('ShaderNodeMath'); msk2.operation = 'MULTIPLY'; msk2.use_clamp = True; Lk(msk.outputs[0], msk2.inputs[0]); msk2.inputs[1].default_value = wear * 3.0
        edge_col = (0.62, 0.63, 0.64, 1) if metal < 0.5 else tuple(min(1, x * 1.6 + 0.08) for x in color[:3]) + (1,)
        ew = N.new('ShaderNodeMix'); ew.data_type = 'RGBA'; ew.inputs['B'].default_value = edge_col
        Lk(col_out, ew.inputs['A']); Lk(msk2.outputs[0], ew.inputs['Factor']); col_out = ew.outputs['Result']
        if metal < 0.5:   # chipped paint reveals metal
            mm = N.new('ShaderNodeMath'); mm.operation = 'MAXIMUM'; mm.inputs[0].default_value = metal; Lk(msk2.outputs[0], mm.inputs[1])
            Lk(mm.outputs[0], b.inputs['Metallic'])
    # v6.2 realism: fine scratches (thin voronoi edges, stretched), dust on up-facing surfaces, stronger cavity grime
    if scratches:
        mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 7.0, 1.0)
        Lk(tc.outputs['Object'], mp.inputs['Vector'])
        vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'DISTANCE_TO_EDGE'; vo.inputs['Scale'].default_value = scratch_scale
        Lk(mp.outputs['Vector'], vo.inputs['Vector'])
        sr = N.new('ShaderNodeMapRange'); sr.inputs['From Min'].default_value = 0.0; sr.inputs['From Max'].default_value = 0.012
        sr.inputs['To Min'].default_value = 1.0; sr.inputs['To Max'].default_value = 0.0
        Lk(vo.outputs['Distance'], sr.inputs['Value'])
        gate = N.new('ShaderNodeTexNoise'); gate.inputs['Scale'].default_value = 3.5; Lk(tc.outputs['Object'], gate.inputs['Vector'])
        gr = N.new('ShaderNodeMapRange'); gr.inputs['From Min'].default_value = 0.5; gr.inputs['From Max'].default_value = 0.62; Lk(gate.outputs['Fac'], gr.inputs['Value'])
        sm = N.new('ShaderNodeMath'); sm.operation = 'MULTIPLY'; sm.use_clamp = True; Lk(sr.outputs['Result'], sm.inputs[0]); Lk(gr.outputs['Result'], sm.inputs[1])
        sm2 = N.new('ShaderNodeMath'); sm2.operation = 'MULTIPLY'; sm2.use_clamp = True; Lk(sm.outputs[0], sm2.inputs[0]); sm2.inputs[1].default_value = scratches
        scol = (0.55, 0.56, 0.57, 1) if metal < 0.5 else tuple(min(1, x * 1.35 + 0.1) for x in color[:3]) + (1,)
        sx = N.new('ShaderNodeMix'); sx.data_type = 'RGBA'; sx.inputs['B'].default_value = scol
        Lk(col_out, sx.inputs['A']); Lk(sm2.outputs[0], sx.inputs['Factor']); col_out = sx.outputs['Result']
    if dust:
        geo2 = N.new('ShaderNodeNewGeometry'); sz = N.new('ShaderNodeSeparateXYZ'); Lk(geo2.outputs['Normal'], sz.inputs[0])
        dr = N.new('ShaderNodeMapRange'); dr.inputs['From Min'].default_value = 0.55; dr.inputs['From Max'].default_value = 0.95; dr.inputs['To Max'].default_value = dust
        Lk(sz.outputs['Z'], dr.inputs['Value'])
        dn = N.new('ShaderNodeTexNoise'); dn.inputs['Scale'].default_value = 14; dn.inputs['Detail'].default_value = 6; Lk(tc.outputs['Object'], dn.inputs['Vector'])
        dm = N.new('ShaderNodeMath'); dm.operation = 'MULTIPLY'; dm.use_clamp = True; Lk(dr.outputs['Result'], dm.inputs[0]); Lk(dn.outputs['Fac'], dm.inputs[1])
        dx = N.new('ShaderNodeMix'); dx.data_type = 'RGBA'; dx.inputs['B'].default_value = (0.42, 0.4, 0.36, 1)
        Lk(col_out, dx.inputs['A']); Lk(dm.outputs[0], dx.inputs['Factor']); col_out = dx.outputs['Result']
    Lk(col_out, b.inputs['Base Color'])
    # bevelled edge highlight (rounds hard edges in shading, like a real machined part)
    bev = N.new('ShaderNodeBevel'); bev.inputs['Radius'].default_value = 0.012; bev.samples = 6
    if bump or bump_node:
        nb = bump_node or N.new('ShaderNodeBump')
        if not bump_node:
            nb.inputs['Strength'].default_value = bump; nb.inputs['Distance'].default_value = 0.002; Lk(nz.outputs['Fac'], nb.inputs['Height'])
        Lk(bev.outputs['Normal'], nb.inputs['Normal']); Lk(nb.outputs['Normal'], b.inputs['Normal'])
    else:
        Lk(bev.outputs['Normal'], b.inputs['Normal'])
    if emission:
        b.inputs['Emission Color'].default_value = tuple(emission[:3]) + (1,); b.inputs['Emission Strength'].default_value = emission[3]
    _mats[key] = m
    return m

def M():  # shared palette (v6.2: muted, weathered, with scratches and dust)
    return dict(
        gun=mat('gunmetal', (0.05, 0.053, 0.056), metal=0.85, rough=0.42, bump=0.1, scratches=0.55, dust=0.25),
        black=mat('black', (0.022, 0.023, 0.025), metal=0.25, rough=0.55, scratches=0.35, dust=0.3),
        rubber=mat('rubber', (0.024, 0.024, 0.026), metal=0, rough=0.78, bump=0.18, noise_scale=180, dust=0.35),
        steel=mat('steel', (0.5, 0.52, 0.54), metal=1, rough=0.3, scratches=0.6, scratch_scale=14),
        chrome=mat('chrome', (0.72, 0.74, 0.76), metal=1, rough=0.14, scratches=0.4, scratch_scale=16),
        brass=mat('brass', (0.6, 0.42, 0.16), metal=1, rough=0.36, scratches=0.5, dust=0.2),
        copper=mat('copper', (0.6, 0.32, 0.18), metal=1, rough=0.36, scratches=0.4),
        coil=mat('coil', (0.34, 0.2, 0.11), metal=0.85, rough=0.42, stripes=(160, (0.12, 0.07, 0.04), 'X'), dust=0.2),
        coilY=mat('coilY', (0.34, 0.2, 0.11), metal=0.85, rough=0.42, stripes=(160, (0.12, 0.07, 0.04), 'Y'), dust=0.2),
        white=mat('whitepaint', (0.56, 0.56, 0.54), metal=0, rough=0.48, coat=0.15, bump=0.08, wear=0.5, scratches=0.45, dust=0.3),
        offwhite=mat('offwhite', (0.55, 0.53, 0.49), metal=0, rough=0.5, coat=0.1, bump=0.08, wear=0.5, scratches=0.4, dust=0.3),
        tan=mat('tan', (0.5, 0.33, 0.17), metal=0, rough=0.62, bump=0.12, scratches=0.3, dust=0.25),
        yellow=mat('yellowpaint', (0.55, 0.36, 0.05), metal=0, rough=0.5, coat=0.2, bump=0.08, wear=0.55, scratches=0.5, dust=0.25),
        green=mat('armygreen', (0.17, 0.22, 0.13), metal=0, rough=0.65, bump=0.12, scratches=0.3, dust=0.3),
        blue=mat('blueins', (0.06, 0.24, 0.55), metal=0, rough=0.4, coat=0.3, scratches=0.15),
        red=mat('redins', (0.5, 0.06, 0.04), metal=0, rough=0.4, coat=0.3, scratches=0.15),
        orange=mat('orange', (0.85, 0.36, 0.06), metal=0, rough=0.4, coat=0.2),
        glass=mat('glassdark', (0.02, 0.025, 0.03), metal=0, rough=0.05, coat=1.0, spec=1.0, wear=0),
        grey=mat('greyplastic', (0.27, 0.28, 0.29), metal=0, rough=0.58, bump=0.08, scratches=0.35, dust=0.3),
        tape=mat('ducttape', (0.3, 0.31, 0.32), metal=0.2, rough=0.55, bump=0.3, noise_scale=40, scratches=0.2),
        pcb=mat('pcb', (0.05, 0.2, 0.45), metal=0.1, rough=0.38, stripes=(220, (0.55, 0.57, 0.6), 'X')),
        trayg=mat('traygreen', (0.26, 0.31, 0.26), metal=0, rough=0.62, bump=0.08, scratches=0.3, dust=0.3),
    )

# ------------------------------------------------------------------ geometry helpers
def _apply(o, mtl, bevel=0.0, segs=3, smooth=True):
    if mtl: o.data.materials.append(mtl)
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = segs; md.limit_method = 'ANGLE'; md.harden_normals = False
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
        try: o.data.set_sharp_from_angle(angle=D(35))
        except Exception: pass
    return o

def box(size, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bevel=0.01, segs=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot); o = bpy.context.object
    o.scale = size; bpy.ops.object.transform_apply(scale=True)
    return _apply(o, m, bevel, segs)

def cyl(r, depth, loc=(0, 0, 0), rot=(0, 0, 0), m=None, verts=64, bevel=0.006, segs=2):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot); o = bpy.context.object
    return _apply(o, m, bevel, segs)

def prism(r, depth, n, loc=(0, 0, 0), rot=(0, 0, 0), m=None, bevel=0.01, twist=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=n, radius=r, depth=depth, location=loc, rotation=rot); o = bpy.context.object
    if twist: o.rotation_euler.rotate_axis('Z', twist)
    return _apply(o, m, bevel, 3, smooth=False)

def sphere(r, loc=(0, 0, 0), m=None, scale=(1, 1, 1), rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=r, location=loc, rotation=rot); o = bpy.context.object
    o.scale = scale
    return _apply(o, m, 0)

def torus(R, r, loc=(0, 0, 0), rot=(0, 0, 0), m=None):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=96, minor_segments=16, location=loc, rotation=rot)
    return _apply(bpy.context.object, m, 0)

def tube(points, r, m=None, res=12):
    """Cable / wire along a smooth path of 3D points."""
    cu = bpy.data.curves.new('cable', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1)
    for p, c in zip(sp.points, points): p.co = (*c, 1)
    sp.order_u = min(4, len(points)); sp.use_endpoint_u = True; sp.resolution_u = res
    o = bpy.data.objects.new('cable', cu); bpy.context.collection.objects.link(o)
    if m: o.data.materials.append(m)
    return o

def helix(start, axis_len, R, r_wire, turns, m=None, axis='X', drop=(0, 0, 0)):
    pts = []
    n = int(turns * 24)
    for i in range(n + 1):
        t = i / n; a = t * turns * 2 * math.pi
        if axis == 'X': p = (start[0] + t * axis_len + drop[0] * t, start[1] + R * math.cos(a) + drop[1] * t, start[2] + R * math.sin(a) + drop[2] * t)
        else: p = (start[0] + R * math.cos(a) + drop[0] * t, start[1] + R * math.sin(a) + drop[1] * t, start[2] + t * axis_len + drop[2] * t)
        pts.append(p)
    return tube(pts, r_wire, m, res=4)

def sphere_path(waypoints_deg, R, steps=10, m=None, r=0.012):
    """Wire lying on a sphere: great-circle interpolation between (azimuth, elevation) waypoints."""
    from mathutils import Vector as V
    def P(a, e): return V((math.cos(D(e)) * math.sin(D(a)), -math.cos(D(e)) * math.cos(D(a)), math.sin(D(e))))
    pts = []
    for (a1, e1), (a2, e2) in zip(waypoints_deg, waypoints_deg[1:]):
        p1, p2 = P(a1, e1), P(a2, e2)
        for i in range(steps):
            t = i / steps; q = p1.slerp(p2, t) if hasattr(p1, 'slerp') else (p1 * (1 - t) + p2 * t).normalized()
            pts.append(tuple(q.normalized() * R))
    pts.append(tuple(P(*waypoints_deg[-1]) * R))
    return tube(pts, r, m, res=2)

def boolean(target, cutter, op='DIFFERENCE', bevel_first=False):
    md = target.modifiers.new('bool', 'BOOLEAN'); md.operation = op; md.object = cutter; md.solver = 'EXACT'
    bpy.context.view_layer.objects.active = target
    # keep bevel after boolean
    if 'bev' in target.modifiers and not bevel_first:
        bpy.ops.object.modifier_move_to_index(modifier='bool', index=0)
    cutter.hide_render = True; cutter.display_type = 'WIRE'   # must stay evaluated for the boolean
    bpy.context.view_layer.update()
    cutter.parent = target; cutter.matrix_parent_inverse = target.matrix_world.inverted()   # follows any later group transform
    return target

def group(objs, loc=(0, 0, 0), rot=(0, 0, 0), scale=1.0):
    e = bpy.data.objects.new('grp', None); bpy.context.collection.objects.link(e)
    for o in objs: o.parent = e
    e.location = loc; e.rotation_euler = rot; e.scale = (scale,) * 3
    return e

def meshes():
    return [o for o in bpy.context.scene.objects if o.type in ('MESH', 'CURVE') and not o.hide_render and o.name != 'shadow']

# ------------------------------------------------------------------ render driver
REGISTRY = {}
def item(item_id, azim=-38, elev=24):
    def deco(fn):
        REGISTRY[item_id] = (fn, azim, elev); return fn
    return deco

def render(item_id):
    fn, azim, elev = REGISTRY[item_id]
    reset(); _mats.clear(); pal = M()
    fn(pal)
    bpy.context.view_layer.update()
    # curves -> meshes for bounds
    objs = meshes()
    for o in objs:
        if o.type == 'CURVE':
            bpy.context.view_layer.objects.active = o
    cam, r, zmin = frame_camera([o for o in objs if o.type == 'MESH'], azim, elev)
    lights(r)
    shadow_catcher(zmin - 0.001)
    os.makedirs(OUT_PNG, exist_ok=True)
    bpy.context.scene.render.filepath = os.path.join(OUT_PNG, item_id + '.png')
    t = time.time(); bpy.ops.render.render(write_still=True)
    print(f'rendered {item_id} in {time.time() - t:.1f}s')


if __name__ == '__main__':
    sys.path.insert(0, HERE)
    import trn3d as T, items_models, items_v2  # noqa: later modules override earlier @T.item registrations
    args = [a for a in sys.argv[1:] if not a.startswith('-')]
    for iid in (args or list(T.REGISTRY)):
        T.render(iid)
