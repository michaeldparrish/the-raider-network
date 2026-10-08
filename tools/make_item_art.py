"""DATABASE ITEM ART v2 (v5.2) — clean, centred, recognisable silhouettes rendered as SVG.

Two image modes on the site:
  FEATURE ART  = cinematic concept renders in assets/images/items/*.webp  (homepage / features; item.heroImage)
  DATABASE ART = this generator's SVGs in assets/images/items/db/          (Loot Intel, item pages, trade + hunt cards; item.image)

Shape references (visual only — no text, values or pixels copied): the community ARC Raiders cheat sheet (v5.1)
and The Raider Network cheat sheet (v5.2). Polished dedicated renders are KEPT as database art when they already read well
(see KEEP_RENDER); everything else gets a class-consistent render:
  keys / keycards / codes / fobs · HUD blueprint cards · specific ARC & tech parts · category fallbacks
  (ARC component, crafting component, salvage, project item badge, consumable, trinket, nature, weapon, mod, augment, shield, ammo)

Run:  python3 tools/make_item_art.py   -> assets/images/items/db/*.svg + tools/source-data/db-art.json
"""
import json, os, re, html, math, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets', 'images', 'items', 'db')
SNAP = json.load(open(os.path.join(ROOT, 'tools', 'source-data', 'raidtheory-snapshot.json')))
PROJ_PATH = os.path.join(ROOT, 'data', 'projects.json')
WSIL = {k: v for k, v in json.load(open(os.path.join(ROOT, 'tools', 'source-data', 'weapon-silhouettes.json'))).items() if not k.startswith('_')}
RARITY = {'Common': '#a7b3b8', 'Uncommon': '#3fd07a', 'Rare': '#3aa2ff', 'Epic': '#b45cff', 'Legendary': '#ffb020'}
FONT = "'Barlow Condensed','Arial Narrow','Helvetica Neue',Arial,sans-serif"
E = html.escape
# Dedicated cinematic renders that already read well as database art — kept, not replaced.
KEEP_RENDER = {'rotary_encoder', 'magnetron', 'queen_reactor', 'matriarch_reactor', 'vaporizer_regulator', 'headphones',
               'industrial_battery', 'advanced_mechanical_components', 'electrical_components', 'processor', 'voltage_converter',
               'sensors', 'exodus_modules', 'breathtaking_snow_globe', 'mechanical_components', 'wires', 'battery', 'arc_powercell'}

DEFS = '''
<radialGradient id="bg" cx="50%" cy="45%" r="75%"><stop offset="0" stop-color="#15303a"/><stop offset=".55" stop-color="#0a181e"/><stop offset="1" stop-color="#050b0e"/></radialGradient>
<pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#19d3c5" stroke-opacity=".05"/></pattern>
<linearGradient id="steelV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5b666c"/><stop offset=".18" stop-color="#e8eef0"/><stop offset=".32" stop-color="#b9c3c7"/><stop offset=".62" stop-color="#6b767c"/><stop offset=".85" stop-color="#3a4348"/><stop offset="1" stop-color="#252b2f"/></linearGradient>
<linearGradient id="darkV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3e484d"/><stop offset=".2" stop-color="#7d888d"/><stop offset=".35" stop-color="#4a5459"/><stop offset=".75" stop-color="#1f2528"/><stop offset="1" stop-color="#121618"/></linearGradient>
<linearGradient id="brassV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6b3f17"/><stop offset=".2" stop-color="#ffd38f"/><stop offset=".4" stop-color="#d1913f"/><stop offset=".75" stop-color="#7a4718"/><stop offset="1" stop-color="#3d220b"/></linearGradient>
<linearGradient id="copperV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5a2a12"/><stop offset=".22" stop-color="#ffb07a"/><stop offset=".45" stop-color="#c8642c"/><stop offset="1" stop-color="#3a1607"/></linearGradient>
<linearGradient id="whiteV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#dfe5e7"/><stop offset="1" stop-color="#9aa5aa"/></linearGradient>
<linearGradient id="faceL" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfd7da"/><stop offset="1" stop-color="#6d787d"/></linearGradient>
<linearGradient id="faceR" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8b969b"/><stop offset="1" stop-color="#3a4348"/></linearGradient>
<linearGradient id="faceT" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#eef3f4"/><stop offset="1" stop-color="#aab4b8"/></linearGradient>
<linearGradient id="dfaceL" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#4f5a5f"/><stop offset="1" stop-color="#22282b"/></linearGradient>
<linearGradient id="dfaceR" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#343c40"/><stop offset="1" stop-color="#14181a"/></linearGradient>
<linearGradient id="dfaceT" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#6c777c"/><stop offset="1" stop-color="#3f484c"/></linearGradient>
<radialGradient id="capFace" cx="40%" cy="38%" r="70%"><stop offset="0" stop-color="#cfd7da"/><stop offset=".6" stop-color="#5d686e"/><stop offset="1" stop-color="#20262a"/></radialGradient>
<radialGradient id="specular" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<filter id="sh" x="-30%" y="-30%" width="160%" height="170%"><feDropShadow dx="0" dy="14" stdDeviation="12" flood-color="#000" flood-opacity=".6"/></filter>
<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="softglow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
'''


def lens_grad(gid, color):
    return f'<radialGradient id="{gid}" cx="42%" cy="40%" r="62%"><stop offset="0" stop-color="#ffffff"/><stop offset=".25" stop-color="{color}"/><stop offset=".7" stop-color="{color}" stop-opacity=".55"/><stop offset="1" stop-color="#05090b"/></radialGradient>'


def frame(body, tag, rarity='Common', extra_defs='', badge=None, title=None):
    c = RARITY.get(rarity, '#a7b3b8')
    b = ''
    if badge:
        b = f'<g transform="translate(470 18)"><rect width="150" height="30" rx="3" fill="#0b1418" stroke="{badge[1]}" stroke-width="1.5"/><circle cx="16" cy="15" r="6" fill="{badge[1]}"/><text x="30" y="21" font-family="{FONT}" font-size="15" font-weight="800" letter-spacing="2" fill="{badge[1]}">{E(badge[0])}</text></g>'
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" width="640" height="400"><defs>{DEFS}{extra_defs}</defs>
<rect width="640" height="400" fill="url(#bg)"/><rect width="640" height="400" fill="url(#grid)"/>
<ellipse cx="320" cy="300" rx="250" ry="60" fill="{c}" opacity=".07"/>
<ellipse cx="320" cy="318" rx="200" ry="20" fill="#000" opacity=".55" filter="url(#softglow)"/>
<g filter="url(#sh)">{body}</g>
<path d="M0 0H640V3H0Z" fill="{c}"/><path d="M0 397H640V400H0Z" fill="{c}" opacity=".35"/>
<text x="22" y="380" font-family="{FONT}" font-size="16" font-weight="700" letter-spacing="3" fill="{c}">{E(tag)}</text>{b}{f'<text x="22" y="356" font-family="{FONT}" font-size="{30 if len(title) < 24 else 24}" font-weight="800" fill="#eef4f5">{E(title.upper())}</text>' if title else ''}
</svg>'''


# ---------------------------------------------------------------- 3D-ish primitives
def hcyl(x0, x1, cy, r, body='steelV', rings=(), left='dark', right=None, lens='#19d3c5', gid='l1', bolts=False):
    """Horizontal cylinder in 3/4 view. rings: list of (pos 0..1, width px, gradient). right: 'lens' | 'cap' | 'none'."""
    ex = r * .34
    s = [f'<ellipse cx="{x0}" cy="{cy}" rx="{ex}" ry="{r}" fill="#1a1f22"/>',
         f'<rect x="{x0}" y="{cy - r}" width="{x1 - x0}" height="{2 * r}" fill="url(#{body})"/>']
    for pos, w, g in rings:
        x = x0 + (x1 - x0) * pos - w / 2
        s.append(f'<rect x="{x}" y="{cy - r - 3}" width="{w}" height="{2 * r + 6}" rx="2" fill="url(#{g})"/>')
        s.append(f'<path d="M{x + w} {cy - r - 3} q{ex * .5} {r + 3} 0 {2 * r + 6}" fill="none" stroke="#000" stroke-opacity=".35" stroke-width="2"/>')
        s.append(f'<line x1="{x + 2}" y1="{cy - r * .55}" x2="{x + w - 2}" y2="{cy - r * .55}" stroke="#fff" stroke-opacity=".45" stroke-width="2"/>')
    s.append(f'<rect x="{x0}" y="{cy - r * .62}" width="{x1 - x0}" height="{r * .14}" fill="#fff" opacity=".22"/>')
    if right == 'lens':
        s += [f'<ellipse cx="{x1}" cy="{cy}" rx="{ex}" ry="{r}" fill="url(#capFace)" stroke="#20262a" stroke-width="2"/>',
              f'<ellipse cx="{x1}" cy="{cy}" rx="{ex * .78}" ry="{r * .78}" fill="#0b1012"/>',
              f'<ellipse cx="{x1}" cy="{cy}" rx="{ex * .62}" ry="{r * .62}" fill="url(#{gid})" filter="url(#glow)"/>',
              f'<ellipse cx="{x1 - ex * .2}" cy="{cy - r * .25}" rx="{ex * .18}" ry="{r * .16}" fill="#fff" opacity=".8"/>']
    elif right == 'cap':
        s += [f'<ellipse cx="{x1}" cy="{cy}" rx="{ex}" ry="{r}" fill="url(#capFace)" stroke="#20262a" stroke-width="2"/>',
              f'<ellipse cx="{x1}" cy="{cy}" rx="{ex * .45}" ry="{r * .45}" fill="#2a3135" stroke="#7d888d" stroke-width="2"/>']
    if bolts:
        for i in range(5):
            x = x0 + 14 + i * (x1 - x0 - 28) / 4
            s.append(f'<circle cx="{x}" cy="{cy - r + 7}" r="3" fill="#cfd7da" stroke="#30373b"/>')
    return ''.join(s)


class Box:
    """Isometric box. F = bottom-front corner. Left face runs F→L (up-left), right face F→R (up-right), height h.
    face('L'|'R'|'T', u, v) maps unit coords on a face to screen: L/R: u along face (0 at F), v up (0..1); T: u→R, v→L."""
    C, S = math.cos(math.radians(30)), math.sin(math.radians(30))

    def __init__(self, fx, fy, w, d, h):
        self.F = (fx, fy); self.L = (fx - w * self.C, fy - w * self.S); self.R = (fx + d * self.C, fy - d * self.S); self.h = h
        self.B = (self.L[0] + self.R[0] - fx, self.L[1] + self.R[1] - fy)

    def face(self, f, u, v):
        F, L, R, h = self.F, self.L, self.R, self.h
        if f == 'L': return (F[0] + (L[0] - F[0]) * u, F[1] + (L[1] - F[1]) * u - h * v)
        if f == 'R': return (F[0] + (R[0] - F[0]) * u, F[1] + (R[1] - F[1]) * u - h * v)
        return (F[0] + (R[0] - F[0]) * u + (L[0] - F[0]) * v, F[1] + (R[1] - F[1]) * u + (L[1] - F[1]) * v - h)

    def poly(self, f, pts, **attrs):
        a = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
        return f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in (self.face(f, u, v) for u, v in pts))}" {a}/>'

    def svg(self, dark=False, stroke='#141a1d', grads=None):
        L, R, T = grads or (('dfaceL', 'dfaceR', 'dfaceT') if dark else ('faceL', 'faceR', 'faceT'))
        q = [(0, 0), (1, 0), (1, 1), (0, 1)]
        return (self.poly('L', q, fill=f'url(#{L})', stroke=stroke, stroke_width=2, stroke_linejoin='round')
                + self.poly('R', q, fill=f'url(#{R})', stroke=stroke, stroke_width=2, stroke_linejoin='round')
                + self.poly('T', q, fill=f'url(#{T})', stroke=stroke, stroke_width=2, stroke_linejoin='round'))


# ---------------------------------------------------------------- specific items (DB art)
def kinetic_converter(it):
    body = (f'<rect x="250" y="112" width="140" height="38" rx="6" fill="url(#darkV)" stroke="#111" stroke-width="2"/>'
            + ''.join(f'<circle cx="{268 + i * 34}" cy="131" r="5" fill="#cfd7da" stroke="#222"/>' for i in range(4))
            + hcyl(150, 470, 210, 66, 'steelV', [(.18, 26, 'brassV'), (.42, 18, 'copperV'), (.62, 18, 'copperV'), (.86, 26, 'brassV')], right='lens', lens='#4fc3ff', gid='lk', bolts=True)
            + '<path d="M170 262 q-40 30 -10 60" fill="none" stroke="#1a1f22" stroke-width="9"/><path d="M170 262 q-40 30 -10 60" fill="none" stroke="#ffb020" stroke-width="3"/>'
            + ''.join(f'<rect x="{290 + i * 22}" y="266" width="12" height="22" rx="2" fill="url(#darkV)"/>' for i in range(4)))
    return frame(body, 'MODIFICATION · KINETIC CONVERTER', it['rarity'], lens_grad('lk', '#4fc3ff'))


def sentinel_firing_core(it):
    body = (hcyl(140, 440, 205, 78, 'darkV', [(.12, 20, 'brassV'), (.3, 12, 'steelV'), (.48, 12, 'steelV'), (.66, 12, 'steelV'), (.85, 22, 'brassV')], right='lens', lens='#ff7a2a', gid='ls')
            + '<rect x="200" y="120" width="160" height="20" rx="4" fill="url(#steelV)" stroke="#222" stroke-width="2"/>'
            + '<path d="M150 260 q-30 36 30 58" fill="none" stroke="#ff6a1a" stroke-width="5"/>')
    return frame(body, 'ARC PART · SENTINEL FIRING CORE', it['rarity'], lens_grad('ls', '#ff7a2a'))


def driver(tag, lens, ring='brassV', small=False):
    def f(it):
        r = 52 if small else 60
        body = (hcyl(170, 450, 210, r, 'darkV', [(.1, 16, ring), (.32, 26, ring), (.68, 26, ring), (.9, 16, ring)], right='lens', lens=lens, gid='ld')
                + ''.join(f'<rect x="{230 + i * 40}" y="{210 - r - 16}" width="8" height="16" fill="url(#steelV)"/>' for i in range(5)))
        return frame(body, tag, it['rarity'], lens_grad('ld', lens))
    return f


def bastion_cell(it):
    bx = Box(320, 300, 120, 120, 140)
    g = bx.svg()
    g += bx.poly('L', [(.12, .12), (.88, .12), (.88, .88), (.12, .88)], fill='#2a1a10', stroke='#ffb020', stroke_width=3)
    g += bx.poly('L', [(.3, .25), (.7, .25), (.7, .75), (.3, .75)], fill='#ff7a2a', filter='url(#glow)')
    g += bx.poly('R', [(.12, .12), (.88, .12), (.88, .88), (.12, .88)], fill='#0b1012', opacity='.55', stroke='#ffb020', stroke_width=2)
    g += bx.poly('T', [(.2, .2), (.8, .2), (.8, .8), (.2, .8)], fill='#cfd7da', stroke='#7d888d', stroke_width=2)
    return frame(g, 'ARC PART · BASTION CELL', it['rarity'])

def bombardier_cell(it):
    cx, top, bot, r = 320, 120, 290, 78
    body = (f'<ellipse cx="{cx}" cy="{bot}" rx="{r}" ry="{r * .3}" fill="#1a1f22"/>'
            f'<rect x="{cx - r}" y="{top}" width="{2 * r}" height="{bot - top}" fill="url(#steelH2)"/>'
            + ''.join(f'<rect x="{cx - r - 2}" y="{y}" width="{2 * r + 4}" height="14" fill="url(#brassH)"/>' for y in (top + 18, bot - 36))
            + f'<ellipse cx="{cx}" cy="{top}" rx="{r}" ry="{r * .3}" fill="url(#capFace)" stroke="#20262a" stroke-width="2"/>'
            f'<ellipse cx="{cx}" cy="{top}" rx="{r * .55}" ry="{r * .16}" fill="#ffb020" opacity=".9" filter="url(#glow)"/>'
            f'<rect x="{cx - r + 16}" y="{top + 40}" width="14" height="{bot - top - 80}" fill="#fff" opacity=".35"/>')
    d = ('<linearGradient id="steelH2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2a3135"/><stop offset=".25" stop-color="#e6ecee"/><stop offset=".5" stop-color="#9aa5aa"/><stop offset="1" stop-color="#1f2528"/></linearGradient>'
         '<linearGradient id="brassH" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#5a3412"/><stop offset=".3" stop-color="#ffd38f"/><stop offset="1" stop-color="#3d220b"/></linearGradient>')
    return frame(body, 'ARC PART · BOMBARDIER CELL', it['rarity'], d)


def leaper_pulse_unit(it):
    # Rectangular housing (in-game silhouette) — long box with end caps, cyan pulse window and orange vents.
    bx = Box(390, 300, 300, 80, 82)
    g = bx.svg(dark=True)
    g += bx.poly('L', [(.12, .3), (.62, .3), (.62, .7), (.12, .7)], fill='#062a2a', stroke='#1b5a55', stroke_width=2)
    g += bx.poly('L', [(.15, .42), (.59, .42), (.59, .58), (.15, .58)], fill='#5ff7ee', filter='url(#glow)')
    for i in range(4):
        u = .7 + i * .06
        g += bx.poly('L', [(u, .2), (u + .03, .2), (u + .03, .8), (u, .8)], fill='#ff6a1a')
    g += bx.poly('T', [(.15, .1), (.85, .1), (.85, .9), (.15, .9)], fill='none', stroke='#7d888d', stroke_width=2)
    g += bx.poly('R', [(.15, .15), (.85, .15), (.85, .85), (.15, .85)], fill='url(#steelV)', stroke='#20262a', stroke_width=2)
    g += bx.poly('R', [(.35, .3), (.65, .3), (.65, .7), (.35, .7)], fill='#19d3c5', opacity='.8')
    return frame(g, 'ARC PART · LEAPER PULSE UNIT', it['rarity'])

def surveyor_vault(it):
    body = ('<circle cx="320" cy="200" r="112" fill="url(#sph)" stroke="#5d686e" stroke-width="2"/>'
            '<path d="M212 176 Q320 132 428 176" fill="none" stroke="#7d898e" stroke-width="5"/><path d="M216 236 Q320 270 424 236" fill="none" stroke="#7d898e" stroke-width="5"/>'
            '<path d="M320 88 Q290 200 320 312" fill="none" stroke="#7d898e" stroke-width="3" opacity=".6"/>'
            '<rect x="294" y="184" width="54" height="40" rx="7" fill="#1b2226" stroke="#5d686e" stroke-width="2"/><rect x="302" y="192" width="38" height="24" rx="4" fill="#19d3c5" filter="url(#glow)"/>'
            '<ellipse cx="270" cy="140" rx="34" ry="20" fill="url(#specular)" opacity=".7"/>')
    d = '<radialGradient id="sph" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#d4dbde"/><stop offset=".85" stop-color="#7d888d"/><stop offset="1" stop-color="#4a5459"/></radialGradient>'
    return frame(body, 'ARC PART · SURVEYOR VAULT', it['rarity'], d)


def ion_sputter(it):
    # Boxy white lab instrument as seen in-game (the cinematic cylinder render stays the feature art).
    bx = Box(330, 300, 190, 130, 125)
    g = bx.svg()
    g += bx.poly('L', [(.1, .4), (.75, .4), (.75, .78), (.1, .78)], fill='#1b2226', stroke='#59656a', stroke_width=2)
    g += bx.poly('L', [(.15, .52), (.7, .52), (.7, .68), (.15, .68)], fill='#19d3c5', filter='url(#glow)')
    for i, col in enumerate(['#ff6a1a', '#5d686e', '#5d686e']):
        x, y = bx.face('L', .18 + i * .12, .2); g += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{col}"/>'
    for i in range(7):
        u = .2 + i * .1; g += bx.poly('R', [(u, .2), (u + .03, .2), (u + .03, .8), (u, .8)], fill='#7d888d')
    cx, cy = bx.face('T', .5, .5)
    g += f'<rect x="{cx - 24:.1f}" y="{cy - 46:.1f}" width="48" height="40" fill="url(#steelV)"/><ellipse cx="{cx:.1f}" cy="{cy - 6:.1f}" rx="24" ry="9" fill="#9aa5aa"/><ellipse cx="{cx:.1f}" cy="{cy - 46:.1f}" rx="24" ry="9" fill="#eef3f4" stroke="#7d888d"/>'
    return frame(g, 'EXODUS · ION SPUTTER', it['rarity'])

def magnetic_accelerator(it):
    bx = Box(320, 300, 170, 170, 42)
    g = bx.svg(grads=('brL', 'brR', 'brT'), stroke='#3d220b')
    g += bx.poly('T', [(.28, .28), (.72, .28), (.72, .72), (.28, .72)], fill='#0b1012', stroke='#4a2a10', stroke_width=3)
    cx, cy = bx.face('T', .5, .5)
    g += f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="34" ry="18" fill="#19d3c5" filter="url(#glow)" opacity=".9"/>'
    for i in range(9):
        u = .1 + i * .09; g += bx.poly('L', [(u, .15), (u + .035, .15), (u + .035, .85), (u, .85)], fill='#ffd38f')
        g += bx.poly('R', [(u, .15), (u + .035, .15), (u + .035, .85), (u, .85)], fill='#c88a45')
    d = ('<linearGradient id="brL" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#d79b55"/><stop offset="1" stop-color="#6b3f17"/></linearGradient>'
         '<linearGradient id="brR" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9a5e28"/><stop offset="1" stop-color="#3d220b"/></linearGradient>'
         '<linearGradient id="brT" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ffd38f"/><stop offset="1" stop-color="#b9762f"/></linearGradient>')
    return frame(g, 'REFINED · MAGNETIC ACCELERATOR', it['rarity'], d)

def snap_hook(it):
    body = (hcyl(190, 420, 170, 40, 'darkV', [(.2, 14, 'brassV'), (.8, 14, 'brassV')], right='cap')
            + '<path d="M250 205 l-24 110 h60 l18 -110 z" fill="url(#darkV)" stroke="#111" stroke-width="2"/><rect x="262" y="220" width="12" height="40" rx="3" fill="#ff6a1a"/>'
            + '<path d="M432 170 h38 M470 170 l34 -34 M470 170 l34 34 M470 170 h44" stroke="url(#steelV)" stroke-width="12" stroke-linecap="round"/>'
            + '<path d="M470 170 l34 -34 M470 170 l34 34 M470 170 h44" stroke="#30373b" stroke-width="2" fill="none"/>'
            + '<circle cx="230" cy="170" r="18" fill="#1b2226" stroke="#7d888d" stroke-width="3"/><circle cx="230" cy="170" r="7" fill="#ffb020" filter="url(#glow)"/>'
            + '<path d="M190 200 q-70 40 -30 90 q20 26 -18 50" fill="none" stroke="#c9b48a" stroke-width="5"/>')
    return frame(body, 'QUICK USE · SNAP HOOK', it['rarity'])


def tick_pod(it):
    bx = Box(320, 300, 110, 110, 120)
    g = bx.svg(dark=True)
    x, y = bx.face('L', .5, .55)
    g += f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="32" ry="36" fill="url(#steelV)" stroke="#222" stroke-width="2"/><ellipse cx="{x:.1f}" cy="{y:.1f}" rx="19" ry="22" fill="url(#lt)" filter="url(#glow)"/>'
    for u in (.2, .8):
        a, b2 = bx.face('R', u, 0); g += f'<rect x="{a - 6:.1f}" y="{b2:.1f}" width="12" height="22" fill="#3a4348"/>'
    return frame(g, 'ARC PART · TICK POD', it['rarity'], lens_grad('lt', '#ff5149'))

def pop_trigger(it):
    body = (hcyl(240, 400, 205, 70, 'darkV', [(.5, 30, 'brassV')], right='lens', lens='#ff6a1a', gid='lp')
            + '<g stroke="url(#steelV)" stroke-width="10" stroke-linecap="round"><path d="M270 135 v-22"/><path d="M320 135 v-22"/><path d="M370 135 v-22"/></g>')
    return frame(body, 'ARC PART · POP TRIGGER', it['rarity'], lens_grad('lp', '#ff6a1a'))


def hatch_key(it):
    body = ('<path d="M250 110 C150 80 120 220 230 250" fill="none" stroke="#1d2428" stroke-width="8"/><path d="M250 110 C150 80 120 220 230 250" fill="none" stroke="#7d888d" stroke-width="3"/>'
            '<circle cx="350" cy="210" r="92" fill="url(#sph2)" stroke="#2a3135" stroke-width="4"/><circle cx="350" cy="210" r="62" fill="url(#darkV)" stroke="#7d888d" stroke-width="3"/>'
            '<circle cx="350" cy="210" r="26" fill="url(#lh)" filter="url(#glow)"/><rect x="336" y="104" width="28" height="24" rx="5" fill="url(#steelV)" stroke="#2a3135" stroke-width="2"/>'
            '<path d="M296 156 l-14 -14 M404 156 l14 -14 M296 264 l-14 14 M404 264 l14 14" stroke="#ff6a1a" stroke-width="6" stroke-linecap="round"/>')
    d = lens_grad('lh', '#19d3c5') + '<radialGradient id="sph2" cx="38%" cy="32%" r="75%"><stop offset="0" stop-color="#eef3f4"/><stop offset=".6" stop-color="#8b969b"/><stop offset="1" stop-color="#2a3135"/></radialGradient>'
    return frame(body, 'ACCESS · RAIDER HATCH KEY', it['rarity'], d)


SPECIFIC = {'kinetic_converter': kinetic_converter, 'sentinel_firing_core': sentinel_firing_core, 'leaper_pulse_unit': leaper_pulse_unit,
            'bastion_cell': bastion_cell, 'bombardier_cell': bombardier_cell, 'surveyor_vault': surveyor_vault,
            'rocketeer_driver': driver('ARC PART · ROCKETEER DRIVER', '#ff6a1a'), 'hornet_driver': driver('ARC PART · HORNET DRIVER', '#ffb020', 'steelV', True),
            'wasp_driver': driver('ARC PART · WASP DRIVER', '#19d3c5', 'steelV', True), 'fireball_burner': driver('ARC PART · FIREBALL BURNER', '#ff5149', 'copperV'),
            'ion_sputter': ion_sputter, 'magnetic_accelerator': magnetic_accelerator, 'snap_hook': snap_hook, 'tick_pod': tick_pod,
            'pop_trigger': pop_trigger, 'raider_hatch_key': hatch_key}


# ---------------------------------------------------------------- keys / access
def place_from(name):
    n = re.sub(r'\b(Key|Keycard|Access Card|Security Code)\b', '', name).strip()
    return re.sub(r'\bNo\.?\s*', '#', n).upper()


def two_lines(s, n=16):
    w = s.split(); a = ''
    while w and len(a + ' ' + w[0]) <= n: a = (a + ' ' + w.pop(0)).strip()
    return a or s, ' '.join(w)


def key_svg(it):
    l1, l2 = two_lines(place_from(it['name']), 14)
    c = RARITY.get(it['rarity'])
    body = f'''<g transform="translate(110 160) rotate(-10)">
  <circle cx="70" cy="60" r="60" fill="url(#steelV)" stroke="#2a3135" stroke-width="3"/><circle cx="70" cy="60" r="22" fill="#0b1a20" stroke="#2a3135" stroke-width="3"/>
  <rect x="122" y="42" width="232" height="36" rx="5" fill="url(#steelV)" stroke="#2a3135" stroke-width="3"/>
  <path d="M252 78 v26 h18 v-14 h16 v20 h18 v-18 h16 v28 h16 v-42 z" fill="url(#steelV)" stroke="#2a3135" stroke-width="3"/>
  <line x1="132" y1="58" x2="344" y2="58" stroke="#2a3135" stroke-width="3"/><rect x="40" y="20" width="22" height="80" rx="4" fill="{c}" opacity=".35"/></g>
<g transform="translate(372 88) rotate(8)"><path d="M-30 30 Q-60 10 -88 44" fill="none" stroke="#c9b48a" stroke-width="3"/>
  <rect width="200" height="120" rx="10" fill="#efe6cf" stroke="#9a8964" stroke-width="3"/><circle cx="18" cy="22" r="8" fill="#0b1a20"/>
  <rect y="40" width="200" height="12" fill="{c}"/>
  <text x="100" y="80" text-anchor="middle" font-family="{FONT}" font-size="24" font-weight="800" fill="#1b2328">{E(l1)}</text>
  <text x="100" y="104" text-anchor="middle" font-family="{FONT}" font-size="19" font-weight="700" fill="#3b464b">{E(l2)}</text></g>'''
    return frame(body, 'ACCESS · KEY', it['rarity'])


def keycard_svg(it):
    l1, l2 = two_lines(place_from(it['name']), 18)
    c = RARITY.get(it['rarity'])
    body = f'''<g transform="translate(166 70) rotate(-7)">
  <rect width="310" height="196" rx="16" fill="url(#whiteV)" stroke="#59656a" stroke-width="3"/>
  <path d="M0 16 a16 16 0 0 1 16 -16 h278 a16 16 0 0 1 16 16 v34 h-310 z" fill="{c}"/>
  <path d="M200 0 h110 v50 h-170 z" fill="#fff" opacity=".18"/>
  <rect x="240" y="14" width="50" height="10" rx="5" fill="#0b1a20" opacity=".6"/>
  <rect x="24" y="70" width="60" height="46" rx="6" fill="#d8b25a" stroke="#8a6a26" stroke-width="2"/><path d="M24 93 h60 M54 70 v46 M39 70 v46 M69 70 v46" stroke="#8a6a26" stroke-width="2"/>
  <text x="102" y="92" font-family="{FONT}" font-size="23" font-weight="800" fill="#1b2328">{E(l1)}</text>
  <text x="102" y="115" font-family="{FONT}" font-size="18" font-weight="700" fill="#4a565b">{E(l2)}</text>
  <rect y="142" width="310" height="22" fill="#20292d"/><path d="M250 172 q20 -12 40 0" fill="none" stroke="#19d3c5" stroke-width="3"/>
  <text x="24" y="186" font-family="{FONT}" font-size="14" font-weight="700" letter-spacing="2" fill="#4a565b">ACCESS · AUTHORISED</text></g>'''
    return frame(body, 'ACCESS · KEYCARD', it['rarity'])


def code_svg(it):
    place = place_from(it['name'])
    body = f'''<g transform="translate(186 88) rotate(4)"><path d="M0 0 h268 v176 h-268 z" fill="#efe6cf" stroke="#9a8964" stroke-width="3"/>
  <rect width="268" height="38" fill="#20292d"/><text x="134" y="27" text-anchor="middle" font-family="{FONT}" font-size="21" font-weight="800" letter-spacing="3" fill="#ff8a43">SECURITY CODE</text>
  <text x="134" y="74" text-anchor="middle" font-family="{FONT}" font-size="23" font-weight="800" fill="#1b2328">{E(place)}</text>
  {''.join(f'<rect x="{40 + i * 50}" y="94" width="36" height="48" rx="4" fill="#d9cfb5" stroke="#9a8964" stroke-width="2"/><circle cx="{58 + i * 50}" cy="118" r="5" fill="#1b2328"/>' for i in range(4))}
  <path d="M0 176 {' '.join(f'l12 -8 12 8' for _ in range(11))}" fill="none" stroke="#9a8964" stroke-width="2"/></g>'''
    return frame(body, 'ACCESS · SECURITY CODE', it['rarity'])


# ---------------------------------------------------------------- silhouettes (400x150 box) — shared by blueprints + weapons
SIL = {
    'rifle': 'M0 72 L52 60 L60 48 L120 46 L124 34 L196 34 L200 46 L262 46 L270 38 L300 38 L300 48 L396 48 L396 58 L300 58 L292 66 L214 66 L206 70 L198 108 L178 108 L184 68 L132 68 L122 116 L90 122 L82 78 L0 84 Z M210 66 l6 22 h18 l-4 -22',
    'smg': 'M24 72 L66 62 L76 50 L136 50 L140 40 L196 40 L200 50 L250 50 L256 42 L300 42 L300 64 L246 64 L232 74 L210 74 L204 136 L180 136 L186 74 L146 74 L134 112 L106 116 L98 82 L24 88 Z',
    'pistol': 'M100 46 L304 46 L310 52 L310 72 L220 72 L214 86 L188 86 L172 142 L126 142 L142 76 L100 76 Z M168 86 q8 24 32 16 M120 46 v-8 h20 v8',
    'shotgun': 'M0 76 L58 64 L70 52 L330 52 L338 58 L338 68 L256 68 L256 80 L176 80 L168 72 L132 72 L120 112 L88 120 L80 82 L0 88 Z M178 80 h72 v14 h-72 z',
    'sniper': 'M0 76 L50 64 L62 54 L296 54 L296 48 L398 48 L398 58 L296 62 L206 66 L196 100 L174 100 L180 66 L128 66 L116 110 L82 118 L74 82 L0 88 Z M112 18 h120 v20 h-120 z M136 38 v16 M206 38 v16',
    'lmg': 'M0 72 L56 60 L68 46 L284 46 L296 36 L334 36 L334 50 L398 50 L398 60 L334 60 L322 68 L256 68 L256 114 L192 114 L192 68 L132 68 L120 112 L88 120 L80 78 L0 84 Z M150 112 l-12 34 M226 112 l12 34',
    'launcher': 'M30 42 h320 a26 26 0 0 1 0 52 h-320 z M136 94 v40 h28 v-40 M218 94 v30 h22 v-30 M350 42 l30 -12 v76 l-30 -12 M60 30 h60 v12 h-60 z',
    'grenade': 'M172 40 a62 62 0 1 0 1 0 Z M196 28 h42 v22 h-42 z M238 32 q42 0 42 52 M140 100 h66 M140 120 h66',
    'mine': 'M96 92 a104 34 0 1 0 208 0 a104 34 0 1 0 -208 0 Z M96 92 v22 a104 34 0 0 0 208 0 v-22 M178 64 h44 v-20 h-44 z',
    'barrel': 'M30 58 h300 v38 h-300 z M64 58 v38 M104 58 v38 M144 58 v38 M184 58 v38 M330 50 h40 v54 h-40 z M10 66 h20 v22 h-20 z',
    'mag': 'M150 18 h96 l22 124 h-96 z M160 40 h86 M166 70 h86 M172 100 h86',
    'grip': 'M110 40 h190 v28 h-190 z M166 68 l-12 82 h48 l12 -82',
    'stock': 'M30 52 h210 l126 -24 v86 l-126 -22 h-210 z M240 52 v40',
    'parts': 'M80 52 h240 v84 h-240 z M80 52 l30 -22 h240 l-30 22 M320 52 l30 -22 v84 l-30 22 M118 74 h64 v42 h-64 z M200 74 h100 v12 h-100 z M200 96 h100 v12 h-100 z',
    'augment': 'M120 22 h160 a20 20 0 0 1 20 20 v90 a20 20 0 0 1 -20 20 h-160 a20 20 0 0 1 -20 -20 v-90 a20 20 0 0 1 20 -20 z M140 52 h120 v34 h-120 z M200 100 v30 M170 115 h60',
    'shield': 'M200 14 l100 30 v40 c0 40 -50 60 -100 74 c-50 -14 -100 -34 -100 -74 v-40 z M200 40 v94',
    'med': 'M60 66 h200 v32 h-200 z M260 72 h40 v20 h-40 z M300 82 h70 M20 68 h40 v28 h-40 z M100 66 v32 M140 66 v32 M180 66 v32',
    'grapple': 'M100 48 h200 v52 h-200 z M150 100 l-10 52 h32 l10 -52 M300 60 h28 v28 h-28 z M328 74 h30 l24 -24 M358 74 l24 24 M358 74 h30',
    'stick': 'M120 104 l164 -52 l10 18 l-164 52 z M284 52 l18 -6 l10 18 l-18 6',
    'tool': 'M60 80 h220 l40 -30 v60 l-40 -30 M100 80 v40 h40 v-40 M330 50 q40 30 0 60',
    'ammo': 'M120 40 h40 v90 h-40 z M120 40 q20 -30 40 0 M180 40 h40 v90 h-40 z M180 40 q20 -30 40 0 M240 40 h40 v90 h-40 z M240 40 q20 -30 40 0',
    'unknown': 'M120 30 h160 v100 h-160 z M200 56 q30 0 30 22 q0 16 -24 22 v12 M206 122 v4',
}
WEAPON_SIL = {'Assault Rifle': 'rifle', 'Battle Rifle': 'rifle', 'SMG': 'smg', 'Pistol': 'pistol', 'Hand Cannon': 'pistol',
              'Shotgun': 'shotgun', 'Sniper Rifle': 'sniper', 'LMG': 'lmg', 'Special': 'launcher'}


def silhouette_for(target, name=''):
    if not target:
        n = name.lower()
        return 'barrel' if any(k in n for k in ('silencer', 'barrel', 'muzzle', 'choke', 'compensator')) else 'unknown'
    t, n, d = target['type'], target['name'].lower(), (target.get('description') or '').lower()
    if t in WEAPON_SIL: return WEAPON_SIL[t]
    if t == 'Modification':
        for k, s in (('silencer', 'barrel'), ('barrel', 'barrel'), ('compensator', 'barrel'), ('muzzle', 'barrel'), ('choke', 'barrel'), ('mag', 'mag'), ('grip', 'grip'), ('stock', 'stock')):
            if k in n: return s
        return 'barrel'
    if 'snap hook' in n: return 'grapple'
    if 'light stick' in n: return 'stick'
    if 'grenade' in n or 'grenade' in d or 'blaze' in n: return 'grenade'
    if 'mine' in n or d.startswith('a mine') or 'mine that' in d: return 'mine'
    if any(k in d for k in ('injection', 'medical', 'health')): return 'med'
    if 'gun parts' in n: return 'parts'
    if t == 'Augment': return 'augment'
    if t == 'Shield': return 'shield'
    if t == 'Ammunition': return 'ammo'
    if t == 'Quick Use': return 'tool'
    return 'parts'


# ---------------------------------------------------------------- HUD blueprint card (v5.2)
def blueprint_svg(it, target, unlisted=False):
    s = silhouette_for(target, it['name'])
    name = it['name'].replace(' Blueprint', '').upper()
    size = 34 if len(name) < 20 else 28 if len(name) < 28 else 22
    c = RARITY.get(it['rarity'], '#a7b3b8')
    klass = 'UNLISTED · NOT IN DATABASE' if unlisted else (target or {}).get('type', 'ITEM').upper()
    h = int(hashlib.md5(it['name'].encode()).hexdigest()[:6], 16)
    code = f'TRN-BP-{h % 9000 + 1000}'
    ticks = ''.join(f'<rect x="{470 + i * 4}" y="356" width="{1 + (h >> i) % 3}" height="14" fill="#7ff3ff" opacity=".6"/>' for i in range(22))
    callouts = ''.join(
        f'<circle cx="{cx}" cy="{cy}" r="4" fill="none" stroke="#ff8a43" stroke-width="2"/><path d="M{cx} {cy} L{lx} {ly} h{dx}" fill="none" stroke="#ff8a43" stroke-width="1.5" opacity=".9"/>'
        f'<text x="{lx + dx + (6 if dx > 0 else -6)}" y="{ly + 4}" text-anchor="{"start" if dx > 0 else "end"}" font-family="{FONT}" font-size="12" font-weight="700" letter-spacing="1.5" fill="#ffb38a">{t}</text>'
        for cx, cy, lx, ly, dx, t in [(190, 236, 150, 300, -40, 'A-01'), (330, 196, 380, 140, 40, 'B-02'), (440, 250, 486, 300, 40, 'C-03')])
    d = (f'<linearGradient id="bpbg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d3346"/><stop offset=".55" stop-color="#082232"/><stop offset="1" stop-color="#04121b"/></linearGradient>'
         '<pattern id="bpg1" width="16" height="16" patternUnits="userSpaceOnUse"><path d="M16 0H0V16" fill="none" stroke="#7ff3ff" stroke-opacity=".07"/></pattern>'
         '<pattern id="bpg2" width="80" height="80" patternUnits="userSpaceOnUse"><path d="M80 0H0V80" fill="none" stroke="#7ff3ff" stroke-opacity=".16"/></pattern>'
         '<radialGradient id="bphalo" cx="50%" cy="55%" r="55%"><stop offset="0" stop-color="#19d3c5" stop-opacity=".22"/><stop offset="1" stop-color="#19d3c5" stop-opacity="0"/></radialGradient>'
         '<filter id="bpglow" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    sil = SIL[s]
    fam = weapon_family(target['id']) if target and target.get('type') in WEAPON_SIL else None
    if fam:   # v6.1: the weapon's own traced side profile, centred in the same 400x150 schematic box
        sil, (w, hh) = WSIL[fam]['d'], WSIL[fam]['size']; ox, oy = 90 + (400 - w) / 2 * 1.15, 138 + (150 - hh) / 2 * 1.15
        silg = (f'<g transform="translate({ox:.1f} {oy:.1f}) scale(1.15)" filter="url(#bpglow)"><path d="{sil}" fill="#7ff3ff" fill-opacity=".1" fill-rule="evenodd" stroke="#a8f7ff" stroke-width="2" stroke-linejoin="round"/></g>\n'
                f'<g transform="translate({ox:.1f} {oy:.1f}) scale(1.15)"><path d="{sil}" fill="none" stroke="#ffffff" stroke-width=".8" stroke-opacity=".75" stroke-dasharray="3 5" transform="translate(5 5)"/></g>')
    else:
        silg = (f'<g transform="translate(90 138) scale(1.15)" filter="url(#bpglow)"><path d="{sil}" fill="#7ff3ff" fill-opacity=".1" stroke="#a8f7ff" stroke-width="2.4" stroke-linejoin="round"/></g>\n'
                f'<g transform="translate(90 138) scale(1.15)"><path d="{sil}" fill="none" stroke="#ffffff" stroke-width=".8" stroke-opacity=".75" stroke-dasharray="3 5" transform="translate(5 5)"/></g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 400" width="640" height="400"><defs>{d}</defs>
<rect width="640" height="400" fill="#050d12"/>
<path d="M18 14 H600 L624 38 V386 H42 L18 362 Z" fill="url(#bpbg)" stroke="#2f8fb0" stroke-width="2"/>
<path d="M18 14 H600 L624 38 V386 H42 L18 362 Z" fill="url(#bpg1)"/><path d="M18 14 H600 L624 38 V386 H42 L18 362 Z" fill="url(#bpg2)"/>
<ellipse cx="320" cy="230" rx="260" ry="110" fill="url(#bphalo)"/>
<path d="M30 26 h40 M30 26 v40 M612 374 h-40 M612 374 v-40" stroke="#7ff3ff" stroke-width="3"/>
<g><rect x="34" y="30" width="150" height="30" fill="#ff6a1a"/><path d="M184 30 h16 l-16 30 z" fill="#ff6a1a"/>
<text x="44" y="52" font-family="{FONT}" font-size="19" font-weight="800" letter-spacing="3" fill="#0a1216">BLUEPRINT</text></g>
<text x="604" y="52" text-anchor="end" font-family="{FONT}" font-size="14" font-weight="700" letter-spacing="2.5" fill="#7ff3ff">{E(klass)}</text>
<text x="38" y="{86 + size * .2:.0f}" font-family="{FONT}" font-size="{size}" font-weight="800" letter-spacing=".5" fill="#ffffff">{E(name)}</text>
<rect x="38" y="{98 + size * .2:.0f}" width="120" height="3" fill="{c}"/>
{silg}
<path d="M120 330 h400 M120 324 v12 M520 324 v12 M320 326 v8" stroke="#7ff3ff" stroke-opacity=".7"/>
<text x="320" y="350" text-anchor="middle" font-family="{FONT}" font-size="11" letter-spacing="3" fill="#7ff3ff" fill-opacity=".8">SCHEMATIC · NOT THE FINISHED ITEM</text>
<path d="M560 130 v170 M554 130 h12 M554 300 h12" stroke="#7ff3ff" stroke-opacity=".5"/>
{callouts}
<text x="44" y="370" font-family="{FONT}" font-size="12" font-weight="700" letter-spacing="2" fill="#7ff3ff" fill-opacity=".75">{code} · {E(it['rarity'].upper())}</text>{ticks}
</svg>'''


# ---------------------------------------------------------------- category fallbacks (consistent, never random imagery)
def glyph(kind):
    if kind == 'arc':
        return hcyl(220, 420, 200, 58, 'darkV', [(.2, 18, 'steelV'), (.8, 18, 'steelV')], right='lens', lens='#ff5149', gid='lg'), lens_grad('lg', '#ff5149')
    if kind == 'craft':
        bx = Box(320, 290, 150, 150, 46)
        g = bx.svg(dark=True) + bx.poly('T', [(.25, .25), (.75, .25), (.75, .75), (.25, .75)], fill='#0e3b3a', stroke='#19d3c5', stroke_width=2)
        g += bx.poly('T', [(.38, .38), (.62, .38), (.62, .62), (.38, .62)], fill='#19d3c5', filter='url(#glow)')
        for i in range(6):
            u = .12 + i * .14; g += bx.poly('L', [(u, .3), (u + .05, .3), (u + .05, .7), (u, .7)], fill='#d8b25a')
        return g, ''
    if kind == 'salvage':
        bx = Box(320, 300, 140, 120, 100)
        g = bx.svg()
        for u in (.25, .75):
            g += bx.poly('L', [(u, 0), (u + .07, 0), (u + .07, 1), (u, 1)], fill='#ff6a1a')
        g += bx.poly('T', [(.1, .4), (.9, .4), (.9, .6), (.1, .6)], fill='#ff6a1a')
        g += bx.poly('R', [(.2, .3), (.8, .3), (.8, .7), (.2, .7)], fill='none', stroke='#59656a', stroke_width=2)
        return g, ''
    if kind == 'consumable':
        return ('<rect x="250" y="120" width="140" height="170" rx="18" fill="url(#whiteV)" stroke="#59656a" stroke-width="3"/><rect x="250" y="120" width="140" height="40" rx="18" fill="#ff5149"/>'
                '<path d="M320 190 v60 M290 220 h60" stroke="#ff5149" stroke-width="16" stroke-linecap="round"/>'), ''
    if kind == 'trinket':
        return ('<polygon points="320,110 390,170 360,280 280,280 250,170" fill="url(#brassV)" stroke="#3d220b" stroke-width="3"/>'
                '<polygon points="320,140 360,180 342,250 298,250 280,180" fill="#b45cff" opacity=".75" filter="url(#glow)"/><ellipse cx="305" cy="170" rx="12" ry="8" fill="#fff" opacity=".7"/>'), ''
    if kind == 'nature':
        return ('<path d="M320 300 C300 230 230 220 220 150 C290 150 320 200 320 260 C320 190 360 130 430 120 C430 200 360 230 320 300 Z" fill="#3fd07a" stroke="#1c6a3d" stroke-width="3"/>'
                '<path d="M320 300 V200" stroke="#1c6a3d" stroke-width="4"/>'), ''
    if kind == 'shield':
        return ('<path d="M320 100 l110 34 v60 c0 60 -60 90 -110 106 c-50 -16 -110 -46 -110 -106 v-60 z" fill="url(#steelV)" stroke="#2a3135" stroke-width="3"/>'
                '<path d="M320 130 l80 24 v44 c0 44 -44 66 -80 78 z" fill="#19d3c5" opacity=".35"/>'), ''
    if kind == 'augment':
        bx = Box(320, 300, 130, 70, 150)
        g = bx.svg(dark=True) + bx.poly('L', [(.2, .45), (.8, .45), (.8, .7), (.2, .7)], fill='#19d3c5', opacity='.7', filter='url(#glow)')
        g += bx.poly('L', [(.1, .85), (.9, .85), (.9, .92), (.1, .92)], fill='#ffb020')
        return g, ''
    if kind == 'ammo':
        return ''.join(hcyl(220, 420, y, 14, 'brassV', right='cap') for y in (170, 210, 250)), ''
    if kind == 'mod':
        return hcyl(190, 450, 205, 30, 'darkV', [(.25, 12, 'steelV'), (.5, 12, 'steelV'), (.75, 12, 'steelV')], right='cap'), ''
    return glyph('salvage')


def weapon_family(rid):
    """'il_toro_ii' -> 'il_toro'; 'aphelion' -> 'aphelion'. Only families with a traced outline are returned."""
    f = re.sub(r'_(i|ii|iii|iv)$', '', rid.replace('-', '_'))
    return f if f in WSIL else None


WDEFS = '''<linearGradient id="gunV" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#8e999e"/><stop offset=".12" stop-color="#5d686d"/><stop offset=".45" stop-color="#363e42"/><stop offset=".8" stop-color="#1c2124"/><stop offset="1" stop-color="#121517"/></linearGradient>
<filter id="metal" x="-5%" y="-10%" width="110%" height="130%" color-interpolation-filters="sRGB"><feGaussianBlur in="SourceAlpha" stdDeviation="1.6" result="bump"/><feSpecularLighting in="bump" surfaceScale="3.2" specularConstant=".95" specularExponent="22" lighting-color="#fff4e6" result="spec"><feDistantLight azimuth="235" elevation="38"/></feSpecularLighting><feComposite in="spec" in2="SourceAlpha" operator="in" result="specIn"/><feDiffuseLighting in="bump" surfaceScale="3.2" diffuseConstant="1.05" lighting-color="#ffffff" result="diff"><feDistantLight azimuth="235" elevation="50"/></feDiffuseLighting><feComposite in="SourceGraphic" in2="diff" operator="arithmetic" k1="1.15" k2="0" k3="0" k4="0" result="lit"/><feComposite in="lit" in2="SourceAlpha" operator="in" result="litIn"/><feComposite in="litIn" in2="specIn" operator="arithmetic" k1="0" k2="1" k3=".55" k4="0"/></filter>
<filter id="inset" x="-5%" y="-10%" width="110%" height="130%"><feMorphology in="SourceAlpha" operator="erode" radius="5" result="e"/><feMorphology in="e" operator="erode" radius="1" result="e2"/><feComposite in="e" in2="e2" operator="out" result="ln"/><feOffset in="ln" dy="1.2" result="lo"/><feComposite in="lo" in2="ln" operator="out" result="hl"/><feFlood flood-color="#05080a" flood-opacity=".55"/><feComposite in2="ln" operator="in" result="dk"/><feFlood flood-color="#cfe3e6" flood-opacity=".22"/><feComposite in2="hl" operator="in" result="lt"/><feMerge><feMergeNode in="dk"/><feMergeNode in="lt"/></feMerge></filter>
<filter id="rim" x="-5%" y="-15%" width="110%" height="130%"><feOffset in="SourceAlpha" dx="1.1" dy="-1.0" result="o"/><feComposite in="o" in2="SourceAlpha" operator="out" result="r"/><feGaussianBlur in="r" stdDeviation=".45" result="rb"/><feFlood flood-color="#19d3c5" flood-opacity=".85"/><feComposite in2="rb" operator="in"/></filter>'''


def traced_weapon_svg(it, fam):
    """v6.1: the weapon's own side profile (traced outline, see weapon-silhouettes.json) as a lit gunmetal render."""
    d, (w, h) = WSIL[fam]['d'], WSIL[fam]['size']
    s = min(540 / w, 230 / h); tx, ty = 320 - w * s / 2, 175 - h * s / 2
    g = f'<g transform="translate({tx:.1f} {ty:.1f}) scale({s:.3f})">'
    body = (f'{g}<path d="{d}" fill="#000" fill-rule="evenodd" filter="url(#rim)"/></g>'
            f'{g}<path d="{d}" fill="url(#gunV)" fill-rule="evenodd" filter="url(#metal)"/>'
            f'<path d="{d}" fill="#000" fill-rule="evenodd" filter="url(#inset)"/>'
            f'<path d="{d}" fill="none" stroke="#0a0d0f" stroke-width="{1.4 / s:.2f}" stroke-linejoin="round"/></g>')
    return frame(body, f'WEAPON · {it["type"].upper()}', it['rarity'], WDEFS, title=it['name'])


def weapon_svg(it):
    fam = weapon_family(it['id'])
    if fam: return traced_weapon_svg(it, fam)
    s = WEAPON_SIL.get(it['type'], 'rifle')
    body = f'<g transform="translate(120 130)"><path d="{SIL[s]}" fill="url(#darkV)" stroke="#9aa5aa" stroke-width="2" stroke-linejoin="round"/><path d="{SIL[s]}" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="1" transform="translate(0 -2)"/></g>'
    return frame(body, f'WEAPON · {it["type"].upper()}', it['rarity'], title=it['name'])


def fallback_svg(it, kind, project):
    g, d = glyph(kind)
    label = {'arc': 'ARC COMPONENT', 'craft': 'CRAFTING COMPONENT', 'salvage': 'SALVAGE', 'consumable': 'CONSUMABLE', 'trinket': 'TRINKET',
             'nature': 'NATURE / RESOURCE', 'shield': 'SHIELD', 'augment': 'AUGMENT', 'ammo': 'AMMUNITION', 'mod': 'MODIFICATION'}[kind]
    return frame(g, label, it['rarity'], d, badge=('PROJECT', '#ffb020') if project else None, title=it['name'])


def kind_for(it):
    t, found = it['type'], it.get('foundIn') or ''
    if t in ('Recyclable', 'Topside Material') and 'ARC' in found: return 'arc'
    if t in ('Basic Material', 'Refined Material', 'Topside Material'): return 'craft'
    if t == 'Quick Use': return 'consumable'
    if t == 'Trinket': return 'trinket'
    if t == 'Nature': return 'nature'
    if t == 'Shield': return 'shield'
    if t == 'Augment': return 'augment'
    if t == 'Ammunition': return 'ammo'
    if t == 'Modification': return 'mod'
    return 'salvage'


def main():
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT): os.remove(os.path.join(OUT, f))
    raw = {i['id']: i for i in SNAP['items']}
    proj_items = set()
    if os.path.exists(PROJ_PATH):
        for p in json.load(open(PROJ_PATH))['projects']:
            for st in p['stages']:
                for r in st['requiredItems']: proj_items.add(r['itemId'].replace('-', '_'))
    made = {}
    for it in SNAP['items']:
        rid = it['id']
        if rid in KEEP_RENDER: continue
        if rid in SPECIFIC: svg, kind = SPECIFIC[rid](it), 'specific'
        elif it['type'] == 'Key':
            n = it['name']
            svg = code_svg(it) if 'Security Code' in n else keycard_svg(it) if ('Keycard' in n or 'Access Card' in n) else key_svg(it)
            kind = 'key'
        elif it['type'] == 'Blueprint':
            target = raw.get(rid.replace('_blueprint', '')) or raw.get(rid.replace('_blueprint', '_i'))
            svg, kind = blueprint_svg(it, target), 'blueprint'
        elif it['type'] in WEAPON_SIL and it['type'] != 'Special' or it.get('isWeapon'):
            svg, kind = weapon_svg(it), 'weapon'
        else:
            svg, kind = fallback_svg(it, kind_for(it), rid in proj_items), 'fallback'
        fn = rid.replace('_', '-') + '.svg'
        open(os.path.join(OUT, fn), 'w').write(svg)
        made[rid.replace('_', '-')] = {'file': 'items/db/' + fn, 'kind': kind}
    # Unlisted blueprints referenced by real trade data (not in the item snapshot) — consistent placeholders, no invented IDs.
    for name in ('Patina Blueprint', 'Silencer III Blueprint', 'Blueprint'):
        fn = 'unlisted-' + re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-') + '.svg'
        open(os.path.join(OUT, fn), 'w').write(blueprint_svg({'name': name, 'rarity': 'Common'}, None, unlisted=True))
    json.dump(made, open(os.path.join(ROOT, 'tools', 'source-data', 'db-art.json'), 'w'), indent=1)
    from collections import Counter
    print(len(made), Counter(v['kind'] for v in made.values()))


if __name__ == '__main__':
    main()
