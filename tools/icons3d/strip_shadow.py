import sys, numpy as np
from PIL import Image
from scipy import ndimage as ndi
for iid in sys.argv[1:]:
    im = Image.open(f'/home/claude/v62/r3d/final/{iid}.png').convert('RGBA'); a = np.asarray(im).astype(float)
    A = a[..., 3] / 255
    solid = A > 0.97
    lab, n = ndi.label(solid); sz = ndi.sum(solid, lab, range(1, n + 1))
    solid = np.isin(lab, [i + 1 for i, s in enumerate(sz) if s > 200])
    keep = ndi.binary_dilation(solid, iterations=1)
    a[..., 3] = np.where(keep, a[..., 3], 0)
    Image.fromarray(a.astype(np.uint8)).save(f'/home/claude/v62/r3d/final/{iid}-clean.png')
