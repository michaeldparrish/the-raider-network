"""Trace per-weapon side-profile outlines (vector) from the RaidTheory reference icons.
Reference used for shape only: rotated from the in-game 40-degree icon angle to level, mirrored (muzzle right),
outline smoothed and simplified. No pixels of the reference are kept."""
import json, sys, os
import numpy as np, cv2
from PIL import Image
from scipy import ndimage as ndi
REF = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('RAIDTHEORY_DIR', '../arcraiders-data')).rstrip('/') + '/images/items/'
ANGLE, UP = 40.0, 4

def level_angle(ref):
    """Correct the 40-degree icon angle so the weapon's longest straight edge (barrel, slide or receiver line) is level."""
    m = mask(ref, ANGLE).astype(np.uint8) * 255
    e = cv2.Canny(m, 50, 150)
    seg = cv2.HoughLinesP(e, 1, np.pi / 720, 60, minLineLength=int(m.shape[1] * 0.18), maxLineGap=3)
    if seg is None: return ANGLE, 0.0
    best = None
    for x1, y1, x2, y2 in np.asarray(seg).reshape(-1, 4):
        ln = np.hypot(x2 - x1, y2 - y1); ang = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if ang > 90: ang -= 180
        if ang < -90: ang += 180
        if abs(ang) < 8 and (best is None or ln > best[0]): best = (ln, ang)
    if best is None: return ANGLE, 0.0
    corr = float(np.clip(best[1], -5, 5))
    # mask is mirrored after rotation: a line sloping down to the right needs the rotation increased
    return ANGLE - corr, best[0] / m.shape[1]

def mask(ref, angle=ANGLE, crop=True):
    im = Image.open(ref).convert('RGBA'); im = im.resize((im.width * UP, im.height * UP), Image.BICUBIC)
    pad = Image.new('RGBA', (im.width * 2, im.height * 2)); pad.alpha_composite(im, (im.width // 2, im.height // 2))
    a = np.asarray(pad.rotate(angle, resample=Image.BICUBIC).transpose(Image.FLIP_LEFT_RIGHT))[..., 3].astype(float) / 255
    m = ndi.gaussian_filter(a, 2.0) > 0.5
    lab, n = ndi.label(m); sz = ndi.sum(m, lab, range(1, n + 1)); m = np.isin(lab, [i + 1 for i, s in enumerate(sz) if s > 600])
    ys, xs = np.nonzero(m); return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def trace(m, box=(400, 150), eps=1.6, min_hole=900):
    cs, hier = cv2.findContours(m.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    H, W = m.shape; s = min(box[0] / W, box[1] / H); ox, oy = 0.0, 0.0
    parts = []
    for c, h in zip(cs, hier[0]):
        if cv2.contourArea(c) < (min_hole if h[3] >= 0 else 400): continue
        a = cv2.approxPolyDP(c, eps * UP / 2, True)[:, 0]
        if len(a) < 3: continue
        parts.append('M' + ' L'.join(f'{x * s + ox:.1f} {y * s + oy:.1f}' for x, y in a) + ' Z')
    return ' '.join(parts), (round(W * s, 1), round(H * s, 1))

WEAPONS = ['anvil_i', 'aphelion', 'arpeggio_i', 'bettina_i', 'bobcat_i', 'burletta_i', 'canto_i', 'dolabra', 'equalizer', 'ferro_i',
           'hairpin_i', 'hullcracker_i', 'il_toro_i', 'jupiter', 'kettle_i', 'osprey_i', 'rattler_i', 'renegade_i', 'stitcher_i',
           'tempest_i', 'torrente_i', 'venator_i', 'vulcano_i']

if __name__ == '__main__':
    # usage: python3 tools/trace_weapon_silhouettes.py /path/to/arcraiders-data   -> tools/source-data/weapon-silhouettes.json
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source-data', 'weapon-silhouettes.json')
    out = {'_readme': json.load(open(dst))['_readme']} if os.path.exists(dst) else {}
    for k in WEAPONS:
        ang, _ = level_angle(REF + k + '.png'); d, size = trace(mask(REF + k + '.png', ang))
        out[k[:-2] if k.endswith('_i') else k] = {'d': d, 'size': size, 'angle': round(float(ang), 2), 'ref': f'images/items/{k}.png'}
        print(k, round(ang, 2), size)
    json.dump(out, open(dst, 'w'), indent=1)
