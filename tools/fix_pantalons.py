"""Correction des pantalons (calque jambes, *_layer_2.png, 512 x 256 = UV 64 x 32 x 8).

Le calque jambes est rendu sur le torse et les jambes. Deux défauts faisaient apparaître du tissu au niveau du cou :
  - pantalons de marque : la ceinture (passants, boucle) était peinte en HAUT du torse (lignes UV 20-23, donc aux épaules)
    au lieu du bas (lignes 28-31, à la taille) -> on la redescend ;
  - costards / robes / smoking : le DESSUS du torse (UV 20,16 8x4 = plaque sur les épaules autour du cou) était peint -> vidé.
On vide aussi le dessous du torse et les bras (jamais utiles sur ce calque).
Usage : python tools/fix_pantalons.py  (depuis la racine du mod). Idempotent."""
import glob
import os
from PIL import Image

A = 'src/main/resources/assets/minenorth_vetements/textures/models/armor/'
S = 8
CLEAR = [
    (20, 16, 16, 4),     # dessus + dessous du torse
    (40, 16, 16, 16),    # bras (non rendus par le calque jambes)
    (0, 0, 32, 16),      # tête
]


def clear(im, x, y, w, h):
    im.paste((0, 0, 0, 0), (x * S, y * S, (x + w) * S, (y + h) * S))


def main():
    n = 0
    for f in sorted(glob.glob(A + '*_layer_2.png')):
        im = Image.open(f).convert('RGBA')
        before = im.tobytes()
        torso = im.crop((16 * S, 20 * S, 40 * S, 32 * S))
        bb = torso.getbbox()
        if bb and bb[1] < 4 * S and bb[3] <= 4 * S:          # tout le tissu est en haut du torse : c'est une ceinture mal placée
            band = torso.crop((0, 0, torso.width, bb[3]))
            empty = Image.new('RGBA', torso.size, (0, 0, 0, 0))
            empty.paste(band, (0, torso.height - bb[3]))
            im.paste(empty, (16 * S, 20 * S))
        for r in CLEAR:
            clear(im, *r)
        if im.tobytes() != before:
            im.save(f)
            n += 1
            print('corrigé', os.path.basename(f))
    print(n, 'textures corrigées')


main()
