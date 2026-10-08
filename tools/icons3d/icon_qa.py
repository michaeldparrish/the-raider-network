"""Raider Network icon QA + normaliser for AI-generated candidates.

    python3 icon_qa.py <item-id> <candidate.png> [--ref in-game.png] [--out qa/]

Checks (all automatic; a human still approves the final look):
  1  transparency   real alpha channel, empty corners, little soft fringe (no leftover background/halo)
  2  framing        normalised to the house layout: centred, longest side = 84% of a 512x512 canvas
  3  shape          silhouette IoU vs our guide mask (same camera) — proves it is the right object/pose
  4  originality    must NOT be a near-copy of the in-game icon (dHash distance + silhouette IoU vs reference)
  5  thumbnail      readable at 64 px and 48 px on the site's card colour (contrast + separation)
  6  lighting       key light reads from upper-left like every other Raider Network icon
  7  weight         512 WebP <= 60 KB
Writes qa/<id>.webp (normalised), qa/<id>-qa.json and qa/<id>-qa.png (review sheet)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
CARD_BG = (10, 22, 27)           # site card background #0a161b
CANVAS, FILL = 512, 0.84


def normalise(img):
    img = img.convert('RGBA'); a = np.asarray(img)[..., 3]
    ys, xs = np.where(a > 128)   # frame on the solid object, not on any soft shadow
    if not len(xs): raise SystemExit('empty image')
    crop = img.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    s = CANVAS * FILL / max(crop.size); crop = crop.resize((max(1, round(crop.width * s)), max(1, round(crop.height * s))), Image.LANCZOS)
    out = Image.new('RGBA', (CANVAS, CANVAS), (0, 0, 0, 0)); out.alpha_composite(crop, ((CANVAS - crop.width) // 2, (CANVAS - crop.height) // 2))
    return out


def mask(img, t=128): return np.asarray(img.convert('RGBA'))[..., 3] > t
def iou(a, b): return float((a & b).sum() / max(1, (a | b).sum()))


def dhash(img, n=16):
    g = Image.new('RGB', img.size, (128, 128, 128)); g.paste(img, mask=img.split()[3])
    g = np.asarray(g.convert('L').resize((n + 1, n), Image.LANCZOS)).astype(int)
    return (g[:, 1:] > g[:, :-1]).flatten()


def on_bg(img, size):
    t = img.resize((size, size), Image.LANCZOS); bg = Image.new('RGBA', t.size, CARD_BG + (255,)); bg.alpha_composite(t); return bg


def lum(rgb): return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]


def qa(item_id, cand_path, ref_path=None, out_dir=None):
    out_dir = out_dir or os.path.join(HERE, 'qa'); os.makedirs(out_dir, exist_ok=True)
    raw = Image.open(cand_path)
    R = {'item': item_id, 'candidate': os.path.basename(cand_path), 'checks': {}}
    C = R['checks']
    # 1 transparency
    has_alpha = raw.mode in ('RGBA', 'LA') or 'transparency' in raw.info
    rgba = raw.convert('RGBA'); A = np.asarray(rgba)[..., 3].astype(float)
    h, w = A.shape; k = max(4, int(min(h, w) * 0.04))
    corners = np.concatenate([A[:k, :k].ravel(), A[:k, -k:].ravel(), A[-k:, :k].ravel(), A[-k:, -k:].ravel()])
    soft = float(((A > 10) & (A < 245)).sum() / max(1, (A > 10).sum()))
    C['transparency'] = {'pass': bool(has_alpha and corners.max() < 10 and soft < 0.06), 'alpha_channel': bool(has_alpha),
                         'corner_alpha_max': int(corners.max()), 'soft_fringe_ratio': round(soft, 4)}
    # 2 framing
    norm = normalise(rgba)
    ys, xs = np.where(A > 8); fill0 = max(np.ptp(xs), np.ptp(ys)) / max(w, h) if len(xs) else 0
    C['framing'] = {'pass': True, 'source_size': [w, h], 'source_fill': round(float(fill0), 3), 'note': 'normalised to 512px, 84% fill, centred'}
    # 3 shape vs our guide mask
    gpath = os.path.join(HERE, 'guides', f'{item_id}-mask.png')
    if os.path.exists(gpath):
        gm = Image.open(gpath).convert('L'); g_rgba = Image.new('RGBA', gm.size, (255, 255, 255, 0)); g_rgba.putalpha(gm)
        g_norm = normalise(g_rgba); s_iou = iou(mask(norm), mask(g_norm))
        C['shape'] = {'pass': s_iou >= 0.80, 'review': 0.70 <= s_iou < 0.80, 'iou_vs_guide': round(s_iou, 3)}
    else:
        C['shape'] = {'pass': None, 'note': 'no guide mask for this item'}
    # 4 originality vs in-game icon (never a near-copy)
    if ref_path and os.path.exists(ref_path):
        ref = normalise(Image.open(ref_path)); r_iou = iou(mask(norm), mask(ref))
        hd = int((dhash(norm) != dhash(ref)).sum()); hd_frac = hd / 256
        # calibrated: upscaled/recoloured/blurred/rotated copies of the in-game icon score <= 0.12; independent work >= 0.28
        C['originality'] = {'pass': bool(hd_frac > 0.25), 'review': bool(0.18 <= hd_frac <= 0.25), 'dhash_distance': round(hd_frac, 3),
                            'iou_vs_ingame': round(r_iou, 3), 'note': '<0.18 = too close to the in-game artwork (copy/trace risk): reject'}
    # 5 thumbnail legibility
    th = {}
    for sz in (64, 48):
        t = np.asarray(on_bg(norm, sz).convert('RGB')).astype(float) / 255; m = mask(norm.resize((sz, sz), Image.LANCZOS))
        L = lum(t); obj = L[m]; bg = L[~m]
        th[sz] = {'contrast': round(float(obj.std()), 3), 'separation': round(float(abs(obj.mean() - bg.mean())), 3)}
    C['thumbnail'] = {'pass': all(v['contrast'] >= 0.08 and v['separation'] >= 0.10 for v in th.values()), **{f'{k}px': v for k, v in th.items()}}
    # 6 lighting direction (upper-left key)
    rgb = np.asarray(norm.convert('RGB')).astype(float) / 255; m = mask(norm); L = lum(rgb)
    yy, xx = np.mgrid[:CANVAS, :CANVAS]; cy, cx = yy[m].mean(), xx[m].mean()
    tl = L[m & (yy < cy) & (xx < cx)].mean(); br = L[m & (yy > cy) & (xx > cx)].mean()
    C['lighting'] = {'pass': bool(tl >= br * 0.95), 'upper_left_mean': round(float(tl), 3), 'lower_right_mean': round(float(br), 3)}
    # 7 weight
    wp = os.path.join(out_dir, f'{item_id}.webp'); norm.save(wp, 'WEBP', quality=86, method=6)
    kb = os.path.getsize(wp) / 1024
    C['weight'] = {'pass': kb <= 60, 'webp_kb': round(kb, 1)}
    fails = [k for k, v in C.items() if v.get('pass') is False and not v.get('review')]
    R['result'] = 'PASS' if all(v.get('pass') in (True, None) for v in C.values()) else ('FAIL' if fails else 'REVIEW')
    R['failed_checks'] = fails
    json.dump(R, open(os.path.join(out_dir, f'{item_id}-qa.json'), 'w'), indent=1)
    # review sheet: normalised | 64 | 48 | silhouette overlay
    sheet = Image.new('RGB', (512 + 300, 512), (12, 22, 27)); sheet.paste(on_bg(norm, 512).convert('RGB'), (0, 0))
    sheet.paste(on_bg(norm, 64).convert('RGB'), (540, 20)); sheet.paste(on_bg(norm, 48).convert('RGB'), (620, 28))
    if os.path.exists(gpath):
        ov = Image.new('RGB', (256, 256)); a1 = mask(norm.resize((256, 256))); a2 = mask(g_norm.resize((256, 256)))
        arr = np.zeros((256, 256, 3), np.uint8); arr[a1 & a2] = (200, 200, 200); arr[a1 & ~a2] = (255, 106, 26); arr[~a1 & a2] = (25, 211, 197)
        sheet.paste(Image.fromarray(arr), (530, 110))
    d = ImageDraw.Draw(sheet); y = 380
    for name, v in C.items():
        d.text((530, y), f"{name:13} {'PASS' if v.get('pass') else ('n/a' if v.get('pass') is None else 'CHECK')}", fill=(150, 230, 225) if v.get('pass') else (255, 160, 120)); y += 16
    d.text((530, 92), 'silhouette: grey=match orange=extra teal=missing', fill=(150, 160, 165))
    sheet.save(os.path.join(out_dir, f'{item_id}-qa.png'))
    return R


if __name__ == '__main__':
    args = sys.argv[1:]
    ref = args[args.index('--ref') + 1] if '--ref' in args else None
    out = args[args.index('--out') + 1] if '--out' in args else None
    print(json.dumps(qa(args[0], args[1], ref, out), indent=1))
