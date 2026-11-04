"""Planche des tenues de motard : une ligne par tenue (face, trois-quarts avant, dos, trois-quarts arrière), puis les casques en gros plan.
Même rendu que tools/apercu.py.  Usage : python tools/apercu_motards.py <skin.png> <sortie.png>"""
import math
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, 'tools')
import apercu  # noqa: E402

TENUES = [
    ('Cuir racing Dayneze + intégral Araï', 'casque_integral_arai', 'blouson_moto_dayneze', 'pantalon_moto_cuir', 'bottes_moto_racing', 'gants_moto_racing'),
    ('Cuir Alpinestarz + intégral AGVE Rossy', 'casque_integral_agve', 'blouson_moto_alpinestarz', 'pantalon_moto_cuir', 'bottes_moto_racing', 'gants_moto_racing'),
    ('Café racer + jet Belle crème', 'casque_jet_belle_creme', 'blouson_moto_cafe', 'jean_moto', 'bottes_moto_vintage', 'gants_moto_cuir'),
    ('Textile Revite + intégral Shoey noir mat', 'casque_integral_shoey_noir', 'blouson_moto_revite', 'pantalon_moto_textile', 'bottes_moto_touring', 'gants_moto_hiver'),
    ('Textile Furygane + jet Belle rouge', 'casque_jet_rouge', 'blouson_moto_furygane', 'jean_moto', 'bottes_moto_touring', 'gants_moto_hiver'),
    ('Haute visibilité + intégral blanc police', 'casque_integral_police', 'blouson_moto_police', 'pantalon_moto_textile', 'bottes_moto_touring', 'gants_moto_racing'),
]
CASQUES = ['casque_integral_arai', 'casque_integral_agve', 'casque_integral_shoey_noir', 'casque_integral_chrome', 'casque_integral_police',
           'casque_jet_belle_creme', 'casque_jet_noir', 'casque_jet_rouge']
NOMS = {'casque_integral_arai': 'Intégral Araï racing', 'casque_integral_agve': 'Intégral AGVE Rossy', 'casque_integral_shoey_noir': 'Intégral Shoey noir mat',
        'casque_integral_chrome': 'Intégral Shoey chromé iridium', 'casque_integral_police': 'Intégral motard police',
        'casque_jet_belle_creme': 'Jet Belle crème', 'casque_jet_noir': 'Jet Shoey noir', 'casque_jet_rouge': 'Jet Belle rouge'}
VUES = (0, -0.7, math.pi, math.pi - 0.7)


def ligne(skin, ids, accs, w=170, h=400, oy=150):
    sc = apercu.Scene(4 * w, h)
    parts = apercu.build(skin, False, *ids, accs)
    for i, yaw in enumerate(VUES):
        apercu.render(sc, parts, yaw, w // 2 + i * w, oy)
    return Image.fromarray(sc.img.clip(0, 255).astype(np.uint8))


def main(a):
    skin = apercu.load(a[0])
    rows = []
    for (titre, casque, haut, bas, pieds, gants) in TENUES:
        rows.append((titre, ligne(skin, [casque, haut, bas, pieds], [gants])))
    for c in CASQUES:   # gros plan : tête seule, zoomée
        im = ligne(skin, [c, None, None, None], [], h=200, oy=150).crop((0, 20, 680, 170))
        rows.append((NOMS.get(c, c), im.resize((im.width * 2 // 1, im.height * 2 // 1), Image.NEAREST).crop((0, 0, 1360, 300))))
    W = max(r[1].width for r in rows)
    H = sum(r[1].height + 22 for r in rows)
    out = Image.new('RGB', (W, H), (40, 44, 52))
    d = ImageDraw.Draw(out)
    try:
        police = ImageFont.truetype('arial.ttf', 15)
    except OSError:
        police = ImageFont.load_default()
    y = 0
    for titre, im in rows:
        d.text((8, y + 3), titre, fill=(230, 230, 230), font=police)
        out.paste(im, (0, y + 22))
        y += im.height + 22
    out.save(a[1])


if __name__ == '__main__':
    main(sys.argv[1:])
