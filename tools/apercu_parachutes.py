"""Aperçus hors jeu des parachutes : planche « fermés » (sac sur le dos) et planche « ouverts » (voile déployée au-dessus du joueur).
Même rendu que tools/apercu.py ; la voile reprend la géométrie de client/ParachuteClient (caissons, intrados, bord d'attaque, suspentes).

  python tools/apercu_parachutes.py <skin.png> <dossier de sortie>   (depuis la racine du mod)
  -> apercu-parachutes-fermes.png, apercu-parachutes-ouverts.png"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import apercu  # noqa: E402

MODELES = [('parachute', 'Parachute', [0xE8601C, 0xF2F0EA]),
           ('parachute_noir', 'Tactique noir', [0x1C1C1F, 0x4A4E54]),
           ('parachute_rouge', 'Rouge et blanc', [0xC8202E, 0xF2F2EE]),
           ('parachute_bleu', 'Bleu ciel', [0x2A8FE0, 0xF2F2EE]),
           ('parachute_vip', 'VIP violet et or', [0x7A30C8, 0xE0B040]),
           ('parachute_prestige', 'VIP+ Prestige', [0x141416, 0xE0B040, 0x141416, 0x2FD4E0])]
TENUE = (None, 'blouson_police_sous_officier', 'pantalon_police', None)   # une tenue sombre fait ressortir le sac
CELLS, SPAN, CHORD, TOP, ARCH = 9, 5.2, 1.6, 4.6, 1.1   # mêmes valeurs que ParachuteClient


def rgb(c):
    return ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def tex(c):
    t = np.zeros((1, 1, 4), np.float32)
    t[0, 0, :3] = rgb(c)
    t[0, 0, 3] = 255
    return t


def shade(c, k):
    r, g, b = rgb(c)
    return (int(r * k) << 16) | (int(g * k) << 8) | int(b * k)


def canopy_quads(pal):
    """Quadrilatères (4 sommets en blocs : x vers la droite, y vers le haut depuis les pieds, z vers l'avant) et couleur."""
    out = []
    pts = [((i / CELLS * 2 - 1) * SPAN / 2, TOP - ARCH * (i / CELLS * 2 - 1) ** 2) for i in range(CELLS + 1)]
    zf, zb = -CHORD / 2 + 0.25, CHORD / 2 + 0.25
    for i in range(CELLS):
        (ax, ay), (bx, by) = pts[i], pts[i + 1]
        c = pal[i % len(pal)]
        out.append((((ax, ay, zf), (bx, by, zf), (bx, by, zb), (ax, ay, zb)), c))                                       # dessus
        out.append((((ax, ay - .22, zf), (ax, ay - .22, zb), (bx, by - .22, zb), (bx, by - .22, zf)), shade(c, .78)))  # dessous
        out.append((((ax, ay, zf), (ax, ay - .22, zf), (bx, by - .22, zf), (bx, by, zf)), shade(c, .6)))               # bord d'attaque
    for i in range(0, CELLS + 1, 3):
        ax, ay = pts[i]
        sx = -.3 if ax < 0 else .3
        for z in (zf + .2, zb - .2):
            w = .02
            out.append((((sx - w, 1.45, .1), (sx + w, 1.45, .1), (ax + w, ay - .22, z), (ax - w, ay - .22, z)), 0x2A2A2E))
    return out


def draw_canopy(scene, pal, yaw, ox, oy):
    """Projette la voile comme apercu.render : unités du modèle (16 par bloc, y vers le bas, pieds à y = 24, avant = -z)."""
    for quad, c in canopy_quads(pal):
        q = []
        for (x, y, z) in quad:
            w = apercu.rot((-x * 16, 24 - y * 16, -z * 16), 0, yaw, 0)
            q.append((ox + w[0] * apercu.SC, oy + w[1] * apercu.SC, w[2]))
        t = tex(c)
        # deux triangles du quadrilatère : apercu.Scene.quad dessine des parallélogrammes (P0, P1, P2)
        scene.quad([q[1], q[0], q[3]], (0, 0, 1, 1), t, 1, 1, 1.0)
        scene.quad([q[3], q[2], q[1]], (0, 0, 1, 1), t, 1, 1, 1.0)


def label(img, items, w):
    d = ImageDraw.Draw(img)
    for i, txt in enumerate(items):
        d.text((i * w + 8, 6), txt, fill=(235, 235, 235))
    return img


def main(skin_path, out_dir):
    skin = apercu.load(skin_path)
    # planche 1 : fermés (dos et trois-quarts arrière)
    W, H = 170, 300
    sc = apercu.Scene(W * len(MODELES), H)
    for i, (pid, _, _) in enumerate(MODELES):
        parts = apercu.build(skin, False, *TENUE, [pid])
        apercu.render(sc, parts, math.pi - 0.55, W * i + W // 2, 80)
    img = Image.fromarray(sc.img.clip(0, 255).astype(np.uint8))
    head = Image.new('RGB', (img.width, 24), (40, 44, 52))
    board = Image.new('RGB', (img.width, img.height + 24))
    board.paste(label(head, [m[1] for m in MODELES], W), (0, 0))
    board.paste(img, (0, 24))
    board.save(os.path.join(out_dir, 'apercu-parachutes-fermes.png'))

    # planche 2 : ouverts (voile au-dessus, vue de trois-quarts arrière, plus petite échelle)
    old = apercu.SC
    apercu.SC = 3.4
    W2, H2 = 400, 420
    sc = apercu.Scene(W2 * 3, H2 * 2)
    for i, (pid, _, pal) in enumerate(MODELES):
        parts = apercu.build(skin, False, *TENUE, [pid])
        ox, oy = W2 * (i % 3) + W2 // 2, H2 * (i // 3) + 300
        yaw = math.pi - 0.6
        draw_canopy(sc, pal, yaw, ox, oy)
        apercu.render(sc, parts, yaw, ox, oy)
    apercu.SC = old
    img = Image.fromarray(sc.img.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for i, (_, name, _) in enumerate(MODELES):
        d.text((W2 * (i % 3) + 8, H2 * (i // 3) + 6), name, fill=(235, 235, 235))
    img.save(os.path.join(out_dir, 'apercu-parachutes-ouverts.png'))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '.')
