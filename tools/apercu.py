"""Aperçu hors jeu : rend un joueur (skin classique ou fin) habillé, comme en jeu (même géométrie que PlayerModel / SlimArmor / Formes).

  python tools/apercu.py <skin.png> <slim 0|1> <sortie.png> [tête] [haut] [jambes] [pieds] [acc1,acc2,...]
  (ids de tenue, "-" = rien). Vues : face, trois-quarts avant, dos, trois-quarts arrière. Lit tools/formes.json."""
import json
import math
import sys

import numpy as np
from PIL import Image

R = 'src/main/resources/assets/minenorth_vetements/textures/models/armor/'
F = json.load(open('tools/formes.json'))
SC = 9          # pixels par unité de modèle


def cube_quads(x, y, z, dx, dy, dz, u, v, g=0.0, mirror=False):
    """Faces d'un ModelPart.Cube : (4 sommets, uv (u1, v1, u2, v2), normale). Même ordre que Minecraft."""
    f0, f1, f2 = x - g, y - g, z - g
    f3, f4, f5 = x + dx + g, y + dy + g, z + dz + g
    if mirror:
        f0, f3 = f3, f0
    v7, v0, v1, v2 = (f0, f1, f2), (f3, f1, f2), (f3, f4, f2), (f0, f4, f2)
    v3, v4, v5, v6 = (f0, f1, f5), (f3, f1, f5), (f3, f4, f5), (f0, f4, f5)
    a, b, c, d, e = u, u + dz, u + dz + dx, u + dz + dx + dx, u + dz + dx + dz
    ff = u + dz + dx + dz + dx
    vv0, vv1, vv2 = v, v + dz, v + dz + dy
    q = [((v4, v3, v7, v0), (b, vv0, c, vv1), (0, -1, 0)),       # dessus (y- modèle)
         ((v1, v2, v6, v5), (c, vv1, d, vv0), (0, 1, 0)),        # dessous
         ((v7, v3, v6, v2), (a, vv1, b, vv2), (-1, 0, 0)),       # côté x-
         ((v0, v7, v2, v1), (b, vv1, c, vv2), (0, 0, -1)),       # avant (z-)
         ((v4, v0, v1, v5), (c, vv1, e, vv2), (1, 0, 0)),        # côté x+
         ((v3, v4, v5, v6), (e, vv1, ff, vv2), (0, 0, 1))]       # arrière
    if mirror:
        q = [(p, uv, (-n[0], n[1], n[2])) for (p, uv, n) in q]
    return q


def rot(p, ax, ay, az):
    x, y, z = p
    if az:
        x, y = x * math.cos(az) - y * math.sin(az), x * math.sin(az) + y * math.cos(az)
    if ay:
        x, z = x * math.cos(ay) + z * math.sin(ay), -x * math.sin(ay) + z * math.cos(ay)
    if ax:
        y, z = y * math.cos(ax) - z * math.sin(ax), y * math.sin(ax) + z * math.cos(ax)
    return x, y, z


class Scene:
    def __init__(s, w, h):
        s.img = np.zeros((h, w, 3), np.float32) + np.array([58, 62, 70], np.float32)
        s.z = np.full((h, w), 1e9, np.float32)
        s.w, s.h = w, h

    def quad(s, pts, uvs, tex, tw, th, light):
        """pts : 3 sommets projetés (écran x, y, profondeur) P0 (u2,v1), P1 (u1,v1), P2 (u1,v2)."""
        (p0, p1, p2) = pts
        e1 = np.array([p0[0] - p1[0], p0[1] - p1[1]])
        e2 = np.array([p2[0] - p1[0], p2[1] - p1[1]])
        det = e1[0] * e2[1] - e1[1] * e2[0]
        if abs(det) < 1e-6:
            return
        xs = [p0[0], p1[0], p2[0], p0[0] + e2[0]]
        ys = [p0[1], p1[1], p2[1], p0[1] + e2[1]]
        x0, x1 = max(0, int(min(xs))), min(s.w, int(max(xs)) + 1)
        y0, y1 = max(0, int(min(ys))), min(s.h, int(max(ys)) + 1)
        if x0 >= x1 or y0 >= y1:
            return
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) + .5
        dx, dy = xx - p1[0], yy - p1[1]
        a = (dx * e2[1] - dy * e2[0]) / det
        b = (e1[0] * dy - e1[1] * dx) / det
        m = (a >= 0) & (a < 1) & (b >= 0) & (b < 1)
        if not m.any():
            return
        u1, v1, u2, v2 = uvs
        tu = ((u1 + a * (u2 - u1)) / tw * tex.shape[1]).astype(int).clip(0, tex.shape[1] - 1)
        tv = ((v1 + b * (v2 - v1)) / th * tex.shape[0]).astype(int).clip(0, tex.shape[0] - 1)
        col = tex[tv, tu]
        m &= col[..., 3] > 8
        depth = p1[2] + a * (p0[2] - p1[2]) + b * (p2[2] - p1[2])
        zb = s.z[y0:y1, x0:x1]
        m &= depth <= zb + 1e-4   # comme le jeu (GL_LEQUAL) : la couche dessinée après gagne
        zb[m] = depth[m]
        s.img[y0:y1, x0:x1][m] = col[..., :3][m] * light


LIGHT = {(0, -1, 0): 1.0, (0, 1, 0): .5, (0, 0, -1): .92, (0, 0, 1): .78, (-1, 0, 0): .7, (1, 0, 0): .7}


def render(scene, parts, yaw, ox, oy):
    for (pivot, cubes) in parts:
        for (geo, tex, tw, th) in cubes:
            for (pts, uv, n) in cube_quads(*geo):
                q = []
                for p in (pts[0], pts[1], pts[2]):
                    w = (p[0] + pivot[0], p[1] + pivot[1], p[2] + pivot[2])
                    w = rot(w, 0, yaw, 0)
                    q.append((ox + w[0] * SC, oy + w[1] * SC, w[2]))
                nn = rot(n, 0, yaw, 0)
                if nn[2] > 0.01:     # face qui tourne le dos (culling simple)
                    continue
                l = LIGHT.get(tuple(n), .8) * (0.85 + 0.15 * max(0, -nn[2]))
                scene.quad(q, uv, tex, tw, th, l)


def load(p):
    try:
        return np.array(Image.open(p).convert('RGBA'), np.float32)
    except FileNotFoundError:
        return None


def build(skin, slim, head, chest, legs, feet, accs):
    aw = 3 if slim else 4
    PIV = {'head': (0, 0, 0), 'body': (0, 0, 0), 'right_arm': (-5, 2.5 if slim else 2, 0), 'left_arm': (5, 2.5 if slim else 2, 0),
           'right_leg': (-1.9, 12, 0), 'left_leg': (1.9, 12, 0)}
    P = {k: [] for k in PIV}
    S = (skin, 64, 64)
    P['head'] += [((-4, -8, -4, 8, 8, 8, 0, 0), *S), ((-4, -8, -4, 8, 8, 8, 32, 0, .5), *S)]
    P['body'] += [((-4, 0, -2, 8, 12, 4, 16, 16), *S), ((-4, 0, -2, 8, 12, 4, 16, 32, .25), *S)]
    P['right_arm'] += [((-3 if not slim else -2, -2, -2, aw, 12, 4, 40, 16), *S), ((-3 if not slim else -2, -2, -2, aw, 12, 4, 40, 32, .25), *S)]
    P['left_arm'] += [((-1, -2, -2, aw, 12, 4, 32, 48), *S), ((-1, -2, -2, aw, 12, 4, 48, 48, .25), *S)]
    P['right_leg'] += [((-2, 0, -2, 4, 12, 4, 0, 16), *S), ((-2, 0, -2, 4, 12, 4, 0, 32, .25), *S)]
    P['left_leg'] += [((-2, 0, -2, 4, 12, 4, 16, 48), *S), ((-2, 0, -2, 4, 12, 4, 0, 48, .25), *S)]

    def armor(id, layer, g, parts):
        t = load(R + '%s_layer_%d.png' % (id, layer))
        if t is None:
            return
        A = (t, 64, 32)
        if 'head' in parts:
            P['head'].append(((-4, -8, -4, 8, 8, 8, 0, 0, g), *A))
        if 'body' in parts:
            P['body'].append(((-4, 0, -2, 8, 12, 4, 16, 16, g), *A))
        if 'arms' in parts:
            P['right_arm'].append(((-3 if not slim else -2, -2, -2, aw, 12, 4, 40, 16, g), *A))
            P['left_arm'].append(((-1, -2, -2, aw, 12, 4, 40, 16, g, True), *A))
        if 'legs' in parts:
            P['right_leg'].append(((-2, 0, -2, 4, 12, 4, 0, 16, g), *A))
            P['left_leg'].append(((-2, 0, -2, 4, 12, 4, 0, 16, g, True), *A))

    def relief(id, delta, hdelta=0):
        sh = F['shape_of'].get(id)
        if not sh:
            return
        boxes = F['formes'].get(sh + '/slim') if slim and (sh + '/slim') in F['formes'] else F['formes'][sh]
        t = load(R + '%s_layer_%d.png' % (id, 2 if id == legs else 1))
        for b in boxes:
            p, x0, y0, z0, x1, y1, z1, s = b
            dd = hdelta if p == 'head' else delta
            if p in ('head', 'body', 'right_arm', 'left_arm') and dd:
                delta_ = dd
                core = {'head': ((-4, 4), (-8, 0), (-4, 4)), 'body': ((-4, 4), (0, 12), (-2, 2)), 'right_arm': ((-2 if slim else -3, 1), (-2, 10), (-2, 2)),
                        'left_arm': ((-1, 2 if slim else 3), (-2, 10), (-2, 2))}[p]
                def ex(v, lo, hi):
                    return v - delta_ if v <= lo else v + delta_ if v >= hi else v
                x0, x1 = ex(x0, *core[0]), ex(x1, *core[0])
                y0, y1 = ex(y0, *core[1]), ex(y1, *core[1])
                z0, z1 = ex(z0, *core[2]), ex(z1, *core[2])
            k = F['sw'].index(s)
            u = 32 * 16 + 4 * (k % 8) * 16 + 8
            v = 4 * (k // 8) * 16 + 8
            P[p].append(((x0, y0, z0, x1 - x0, y1 - y0, z1 - z0, u, v), t, 1024, 512))

    puffy = chest in F['puffy']
    bala = any(a.startswith('cagoule') for a in accs)   # cagoule : texture de tête à 0,62, chapeau relevé de 0,22 (comme SlimArmor)
    if head:
        armor(head, 1, .52, ['head']); relief(head, 0, .22 if bala else 0)
    if chest:
        armor(chest, 1, .6 if puffy else .3, ['body', 'arms']); relief(chest, 0)
    if legs:
        armor(legs, 2, .27, ['body', 'legs']); relief(legs, 0)
    if feet:
        armor(feet, 1, .32, ['legs']); relief(feet, 0)
    infl = (.6 if puffy else .3) if chest else 0
    for a in accs:
        if a.startswith('cagoule'):
            armor(a, 1, .62, ['head'])
        relief(a, max(infl, .25) + .05 - .3)
    out = []
    for k in PIV:
        cubes = []
        for c in P[k]:
            geo = c[0]
            x, y, z, dx, dy, dz, u, v = geo[:8]
            g = geo[8] if len(geo) > 8 else 0
            mi = geo[9] if len(geo) > 9 else False
            cubes.append(((x, y, z, dx, dy, dz, u, v, g, mi), c[1], c[2], c[3]))
        out.append((PIV[k], cubes))
    return out


def main(a):
    skin = load(a[0])
    slim = a[1] == '1'
    ids = [None if x in ('-', '') else x for x in (a[3:7] + ['-'] * 4)[:4]]
    accs = [x for x in (a[7].split(',') if len(a) > 7 else []) if x and x != '-']
    parts = build(skin, slim, *ids, accs)
    W = 4 * 170
    sc = Scene(W, 330)
    for i, yaw in enumerate((0, -0.7, math.pi, math.pi - 0.7)):
        render(sc, parts, yaw, 85 + i * 170, 92)
    Image.fromarray(sc.img.clip(0, 255).astype(np.uint8)).save(a[2])


if __name__ == '__main__':
    main(sys.argv[1:])
