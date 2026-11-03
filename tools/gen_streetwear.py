"""Streetwear : doudounes, gilets, sweats à capuche, bombers, perfectos, manteaux, trench, joggings, cargos, jeans,
casquettes, bonnets, bobs et accessoires (lunettes, chaînes, montres, gants, sacs).

Génère, depuis UNE seule définition :
  - textures d'armure 512 x 256 (art haute résolution sur l'UV 64 x 32 x 8 + pastilles de couleur pour le relief 3D) ;
  - icônes / modèles d'objet (2D pour les vêtements, 3D à éléments pour chapeaux et accessoires, tirés des cubes portés) ;
  - src/main/java/com/minenorth_vetements/client/Formes.java (cubes portés, par forme ; variante /slim pour les bras fins) ;
  - src/main/java/com/minenorth_vetements/AccessoryData.java (accessoires et leur emplacement) ;
  - lignes ajoutées à OutfitData.java, traductions fr_fr / en_us ;
  - tools/formes.json (pour tools/apercu.py).
Usage : python tools/gen_streetwear.py  (depuis la racine du mod). Idempotent."""
import json
import math
import random

import numpy as np
from PIL import Image, ImageDraw

R = 'src/main/resources/assets/minenorth_vetements/'
J = 'src/main/java/com/minenorth_vetements/'
ARMOR = R + 'textures/models/armor/'


# ---------------------------------------------------------------- couleurs

def rgb(c):
    return c if isinstance(c, tuple) else ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def sh(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in rgb(c))


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


WHITE, BLACK = 0xF2F2EE, 0x141416
GOLD, GOLD_D = 0xD9AE3E, 0x9C7424
SILVER, SILVER_D = 0xC4C8CE, 0x7E838B

# Pastilles : index -> nom (16 maxi, voir ClothesExtras.bake : 8 par ligne, 2 lignes)
SW = ['main', 'dark', 'light', 'accent', 'metal', 'metal_dark', 'second', 'strap', 'white', 'black', 'lens', 'lens_hi', 'main_hi', 'accent_dark', 'skin', 'extra']


def palette(p):
    m = p['main']
    d = dict(main=m, dark=sh(m, .72), light=sh(m, 1.3), accent=m, metal=GOLD, metal_dark=GOLD_D, second=p.get('accent', m), strap=0x1A1A1D,
             white=WHITE, black=BLACK, lens=0x15181C, lens_hi=0x7A8A9A, main_hi=sh(m, 1.12), skin=0xC69C7A, extra=m)
    d.update(p)
    d.setdefault('accent_dark', sh(d['accent'], .7))
    return [rgb(d[k]) for k in SW]


# ---------------------------------------------------------------- faces de l'UV (512 x 256)

BODY = dict(top=(160, 128, 224, 160), R=(128, 160, 160, 256), F=(160, 160, 224, 256), L=(224, 160, 256, 256), B=(256, 160, 320, 256))
ARM = dict(top=(352, 128, 384, 160), bot=(384, 128, 416, 160), O=(320, 160, 352, 256), F=(352, 160, 384, 256), I=(384, 160, 416, 256), B=(416, 160, 448, 256))
LEG = dict(top=(32, 128, 64, 160), O=(0, 160, 32, 256), F=(32, 160, 64, 256), I=(64, 160, 96, 256), B=(96, 160, 128, 256))


class Tex:
    def __init__(s, seed):
        s.a = np.zeros((256, 512, 4), np.float32)
        s.rnd = np.random.default_rng(seed)

    def fill(s, r, col, noise=.035, grad=(1.0, .9), heather=0.0, twill=0.0, sheen=0.0):
        x0, y0, x1, y1 = r
        h, w = y1 - y0, x1 - x0
        c = np.array(rgb(col), np.float32)
        f = 1 + s.rnd.uniform(-noise, noise, (h, w))
        if heather:   # gris chiné : fibres claires / sombres
            f += s.rnd.choice([-heather, 0, 0, heather * .7], (h, w))
        if twill:     # sergé : diagonales
            yy, xx = np.mgrid[0:h, 0:w]
            f += twill * np.where(((xx + yy) // 2) % 3 == 0, 1, -.4)
        g = np.linspace(grad[0], grad[1], h)[:, None]
        f = f * g
        if sheen:     # brillant (nylon, cuir) : reflet doux en haut de la pièce
            yy = np.linspace(0, 1, h)[:, None]
            f = f + sheen * np.exp(-((yy - .25) / .18) ** 2)
        s.a[y0:y1, x0:x1, :3] = np.clip(c[None, None, :] * f[:, :, None], 0, 255)
        s.a[y0:y1, x0:x1, 3] = 255

    def mul(s, r, f):
        x0, y0, x1, y1 = r
        s.a[y0:y1, x0:x1, :3] = np.clip(s.a[y0:y1, x0:x1, :3] * f, 0, 255)

    def rect(s, r, col):
        x0, y0, x1, y1 = r
        s.a[y0:y1, x0:x1, :3] = rgb(col)
        s.a[y0:y1, x0:x1, 3] = 255

    def clear(s, r):
        x0, y0, x1, y1 = r
        s.a[y0:y1, x0:x1] = 0

    def quilt(s, r, bands, shiny):
        """Doudoune : boudins horizontaux, clairs au centre, pincés aux coutures."""
        x0, y0, x1, y1 = r
        h = y1 - y0
        lum = s.a[y0:y1, x0:x1, :3].mean() / 255
        amp = 1.0 - .55 * max(0, lum - .45)                  # coloris clairs : relief plus doux (sinon rayures blanches)
        t = (np.arange(h) * bands / h) % 1.0
        f = 1 - amp * (.26 - .34 * np.sin(np.pi * t) ** .7)
        if shiny:
            f = f + .22 * np.exp(-((t - .34) / .1) ** 2)
        seam = (t < .045) | (t > .955)
        f = np.where(seam, 1 - amp * .45, f)
        s.mul(r, f[:, None, None])
        add = (1 - lum) * (26 * np.sin(np.pi * t) ** 2 + (30 * np.exp(-((t - .34) / .1) ** 2) if shiny else 0))   # reflet visible même sur le noir
        x0, y0, x1, y1 = r
        s.a[y0:y1, x0:x1, :3] = np.clip(s.a[y0:y1, x0:x1, :3] + np.where(seam, 0, add)[:, None, None], 0, 255)

    def ribs(s, r, f=.82, step=2):
        x0, y0, x1, y1 = r
        for x in range(x0, x1, step):
            s.mul((x, y0, x + 1, y1), f)

    def img(s):
        return Image.fromarray(s.a.astype(np.uint8), 'RGBA')


def draw_on(t, fn):
    """Dessin vectoriel (PIL) par-dessus le tableau."""
    im = t.img()
    fn(ImageDraw.Draw(im))
    t.a = np.array(im, np.float32)


def faces(d):
    return [d[k] for k in d]


# petite police 3 x 5 pour les logos brodés / imprimés
FONT = {'E': ["XXX", "X..", "XX.", "X..", "XXX"], 'S': [".XX", "X..", ".X.", "..X", "XX."], 'N': ["X.X", "XXX", "XXX", "X.X", "X.X"],
        'T': ["XXX", ".X.", ".X.", ".X.", ".X."], 'I': ["X", "X", "X", "X", "X"], 'L': ["X..", "X..", "X..", "X..", "XXX"],
        'A': [".X.", "X.X", "XXX", "X.X", "X.X"], 'P': ["XX.", "X.X", "XX.", "X..", "X.."], 'H': ["X.X", "X.X", "XXX", "X.X", "X.X"],
        'M': ["X...X", "XX.XX", "X.X.X", "X...X", "X...X"], 'O': [".X.", "X.X", "X.X", "X.X", ".X."], 'C': [".XX", "X..", "X..", "X..", ".XX"],
        'U': ["X.X", "X.X", "X.X", "X.X", "XXX"], 'R': ["XX.", "X.X", "XX.", "X.X", "X.X"], ' ': ["..", "..", "..", "..", ".."],
        'B': ["XX.", "X.X", "XX.", "X.X", "XX."], 'D': ["XX.", "X.X", "X.X", "X.X", "XX."]}


# lettrage serré (dos des tenues : les bras cachent ~4 px de chaque côté du dos) : M sur 4 colonnes
COMPACT = {'M': ["X..X", "XXXX", "XXXX", "X..X", "X..X"]}


def text(t, x, y, s, col, scale=1, sy=None, gap=None, glyphs=None):
    """sy : hauteur d'un point (lettres étirées en hauteur), par défaut = scale ; gap : espace entre lettres (défaut = scale)."""
    sy, gap = sy or scale, scale if gap is None else gap
    for ch in s:
        g = (glyphs or {}).get(ch) or FONT[ch]
        for j, row in enumerate(g):
            for i, c in enumerate(row):
                if c == 'X':
                    t.rect((x + i * scale, y + j * sy, x + (i + 1) * scale, y + (j + 1) * sy), col)
        x += len(g[0]) * scale + gap


def text_w(s, scale=1, gap=None, glyphs=None):
    gap = scale if gap is None else gap
    return sum(len(((glyphs or {}).get(c) or FONT[c])[0]) * scale + gap for c in s) - gap


# ---------------------------------------------------------------- vêtements (calque 1 : torse + bras)

def paint_puffer(o, t):
    m, shiny = o['main'], o.get('shiny', True)
    for r in faces(BODY):
        t.fill(r, m, noise=.015, grad=(1.02, .9))
    t.quilt(BODY['F'], 5, shiny); t.quilt(BODY['B'], 5, shiny); t.quilt(BODY['R'], 5, shiny); t.quilt(BODY['L'], 5, shiny)
    if not o.get('gilet'):
        for r in faces(ARM):
            t.fill(r, m, noise=.015, grad=(1.02, .92))
        for k in ('O', 'F', 'I', 'B'):
            t.quilt(ARM[k], 5, shiny)
            x0, y0, x1, y1 = ARM[k]
            t.fill((x0, 244, x1, 256), sh(m, .62), noise=.02); t.ribs((x0, 244, x1, 256), .8)   # poignets élastiques
    for k in ('F', 'B', 'R', 'L'):
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 248, x1, 256), sh(m, .62), noise=.02); t.ribs((x0, 248, x1, 256), .82)       # bas élastique
    # zip, rabat, tirette, badge
    t.mul((186, 160, 198, 256), .9)
    t.rect((191, 160, 193, 248), sh(o.get('zip', m), .5)); t.rect((192, 160, 193, 248), sh(o.get('zip', m), .8))
    t.rect((190, 166, 194, 178), SILVER); t.rect((191, 168, 193, 176), SILVER_D)
    def badge(d):
        d.ellipse((205, 176, 215, 186), fill=rgb(WHITE), outline=rgb(0x1B2A55))
        d.polygon([(207, 183), (210, 178), (213, 183)], fill=rgb(0x1B2A55))
        d.line([(208, 184), (212, 184)], fill=rgb(0xC8202A))
    draw_on(t, badge)
    if o.get('gilet'):
        for r in faces(ARM):
            t.clear(r)


def paint_hoodie(o, t):
    m = o['main']
    hz = o.get('heather', 0)
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.03, heather=hz, grad=(1.0, .9))
    for k in ('F', 'B', 'R', 'L'):
        x0, y0, x1, y1 = BODY[k]
        t.mul((x0, 244, x1, 256), .9); t.ribs((x0, 244, x1, 256), .82)      # bas côtelé
    for k in ('O', 'F', 'I', 'B'):
        x0, y0, x1, y1 = ARM[k]
        t.mul((x0, 242, x1, 256), .9); t.ribs((x0, 242, x1, 256), .82)      # poignets côtelés
        t.mul((x0, 160, x1, 166), .92)
    t.mul((256, 160, 320, 170), .82)                                        # ombre de la capuche dans le dos

    def det(d):
        d.ellipse((170, 146, 214, 170), fill=sh(m, .7))                     # encolure (ouverture de la capuche)
        d.ellipse((174, 144, 210, 166), fill=sh(m, .55))
        d.line([(172, 212), (212, 212)], fill=sh(m, .72), width=1)                                   # poche kangourou
        d.line([(164, 242), (220, 242)], fill=sh(m, .72), width=1)
        d.line([(172, 212), (166, 234)], fill=sh(m, .6), width=2)
        d.line([(212, 212), (218, 234)], fill=sh(m, .6), width=2)
        lc = rgb(o.get('cord', WHITE))
        for x in (184, 199):
            d.line([(x, 166), (x - 1 if x < 192 else x + 1, 196)], fill=lc, width=2)
            d.rectangle((x - 1, 196, x + 1, 202), fill=rgb(SILVER))
    draw_on(t, det)
    pocket = Image.new('L', (512, 256), 0)
    ImageDraw.Draw(pocket).polygon([(172, 213), (212, 213), (220, 241), (164, 241)], fill=255)
    t.a[..., :3] *= np.where(np.array(pocket)[..., None] > 0, .9, 1.0)                              # poche : même tissu, un ton plus sombre
    t.rect((160, 160, 224, 162), sh(m, .6))
    logo = o.get('logo', 'ESSENTIEL')
    w = text_w(logo)
    text(t, 192 - w // 2, 184, logo, o.get('logo_col', sh(m, .75)))


def paint_bomber(o, t):
    m, lin = o['main'], o.get('lining', 0xE8641E)
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.012, grad=(1.04, .88), sheen=.1)
    rib = sh(m, .7)
    for k in ('F', 'B', 'R', 'L'):
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 244, x1, 256), rib, noise=.02); t.ribs((x0, 244, x1, 256), .78)
        t.fill((x0, 160, x1, 166), rib, noise=.02); t.ribs((x0, 160, x1, 166), .78)
    for k in ('O', 'F', 'I', 'B'):
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 244, x1, 256), rib, noise=.02); t.ribs((x0, 244, x1, 256), .78)
    t.rect((189, 166, 195, 244), lin)                                       # doublure orange visible
    t.rect((191, 160, 193, 244), SILVER_D); t.rect((191, 160, 192, 244), SILVER)
    t.rect((190, 168, 194, 176), SILVER)

    def det(d):
        d.rectangle((326, 182, 346, 200), outline=sh(m, .6))               # poche de manche à stylos
        for x in (330, 335, 340):
            d.line([(x, 182), (x, 190)], fill=sh(m, .6))
        d.line([(328, 196), (344, 196)], fill=rgb(SILVER), width=1)
        d.line([(166, 214), (174, 232)], fill=sh(m, .55), width=2)          # poches passepoilées
        d.line([(218, 214), (210, 232)], fill=sh(m, .55), width=2)
        d.rectangle((202, 178, 214, 184), fill=rgb(o.get('patch', 0xEDE6D0)))
    draw_on(t, det)
    text(t, 203, 179, 'A', sh(m, .6))


def paint_perfecto(o, t):
    m = o['main']
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.03, grad=(1.1, .85), sheen=.2)
    rnd = random.Random(3)

    def det(d):
        for _ in range(140):                                                # plis du cuir
            x, y = rnd.randrange(128, 448), rnd.randrange(160, 256)
            d.line([(x, y), (x + rnd.randint(2, 6), y + rnd.randint(-1, 1))], fill=sh(m, 1.45))
        lap = sh(m, .82)
        d.polygon([(162, 160), (186, 160), (178, 190), (162, 184)], fill=lap, outline=sh(m, 1.6))     # revers
        d.polygon([(198, 160), (222, 160), (222, 190), (206, 184)], fill=lap, outline=sh(m, 1.6))
        for (x, y) in ((166, 168), (218, 168), (166, 180), (218, 180)):
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=rgb(SILVER), outline=rgb(SILVER_D))         # pressions
        d.line([(214, 162), (196, 202), (196, 256)], fill=rgb(SILVER), width=2)                    # zip asymétrique
        d.line([(204, 200), (218, 188)], fill=rgb(SILVER), width=2)                                # poche poitrine
        d.line([(166, 216), (182, 214)], fill=rgb(SILVER), width=2)
        d.line([(202, 216), (218, 214)], fill=rgb(SILVER), width=2)
        d.rectangle((160, 238, 224, 246), fill=sh(m, .7)); d.rectangle((256, 238, 320, 246), fill=sh(m, .7))
        d.rectangle((128, 238, 160, 246), fill=sh(m, .7)); d.rectangle((224, 238, 256, 246), fill=sh(m, .7))
        d.rectangle((164, 236, 174, 248), outline=rgb(SILVER), width=2)                            # boucle de ceinture
        d.line([(336, 226), (336, 256)], fill=rgb(SILVER), width=2)                                # zips de poignets
        d.rectangle((356, 130, 380, 138), fill=sh(m, .7)); d.ellipse((364, 131, 370, 137), fill=rgb(SILVER))   # épaulettes
        d.rectangle((168, 128, 176, 160), fill=sh(m, .7)); d.rectangle((208, 128, 216, 160), fill=sh(m, .7))
    draw_on(t, det)


def paint_coat(o, t):
    m, trench = o['main'], o.get('trench', False)
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.045 if not trench else .02, grad=(1.02, .9), twill=.025 if trench else .0)
    inner = rgb(o.get('inner', 0x1C1C20))

    def det(d):
        d.polygon([(178, 160), (206, 160), (192, 194)], fill=inner)                                 # col roulé dessous
        lap = sh(m, .86)
        d.polygon([(164, 160), (178, 160), (192, 194), (186, 204), (174, 182), (162, 176)], fill=lap, outline=sh(m, .62))
        d.polygon([(220, 160), (206, 160), (192, 194), (198, 204), (210, 182), (222, 176)], fill=lap, outline=sh(m, .62))
        d.line([(192, 196), (192, 256)], fill=sh(m, .6))
        btn = rgb(o.get('btn', 0x2A2420))
        for y in (208, 226) if not trench else (204, 216, 228):
            for x in (182, 202):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=btn, outline=sh(btn, 1.8))
        d.rectangle((166, 236, 182, 239), fill=sh(m, .7)); d.rectangle((202, 236, 218, 239), fill=sh(m, .7))   # rabats de poches
        d.line([(288, 236), (288, 256)], fill=sh(m, .6))                                            # fente dos
        for y in (236, 240, 244):
            d.ellipse((341, y, 344, y + 3), fill=btn)                                               # boutons de manche
        d.line([(320, 230), (352, 230)], fill=sh(m, .75))
        if trench:
            d.rectangle((164, 166, 184, 190), outline=sh(m, .7))                                    # rabat tempête
            for (x0, x1) in ((160, 224), (256, 320), (128, 160), (224, 256)):
                d.rectangle((x0, 230, x1, 240), fill=sh(m, .9), outline=sh(m, .7))                  # ceinture
            d.rectangle((188, 228, 196, 242), outline=rgb(o.get('metal', 0x8A7A5A)), width=2)
            d.rectangle((168, 128, 176, 160), fill=sh(m, .85)); d.rectangle((208, 128, 216, 160), fill=sh(m, .85))   # épaulettes
            d.rectangle((356, 130, 380, 138), fill=sh(m, .85))
            for k in ('O', 'F', 'I', 'B'):
                x0, y0, x1, y1 = ARM[k]
                d.rectangle((x0, 234, x1, 240), fill=sh(m, .85))                                    # pattes de poignet
    draw_on(t, det)


# ---------------------------------------------------------------- pantalons (calque 2 : jambes + bas du torse)

def paint_pants(o, t):
    m, kind = o['main'], o['pants']
    hz = o.get('heather', 0)
    tw = .05 if kind == 'jean' else .02 if kind == 'cargo' else 0
    for r in faces(LEG):
        t.fill(r, m, noise=.035, heather=hz, twill=tw, grad=(1.0, .9))
    for k in ('F', 'B', 'R', 'L'):                                           # hanches : bas du torse seulement (jamais près du cou)
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 232, x1, 256), m, noise=.035, heather=hz, twill=tw)
    st = rgb(o.get('stitch', sh(m, .7)))

    if kind == 'jogging':
        for k in ('F', 'B', 'R', 'L'):
            x0, y0, x1, y1 = BODY[k]
            t.mul((x0, 232, x1, 242), .86); t.ribs((x0, 232, x1, 242), .82)
        for k in ('O', 'F', 'I', 'B'):
            x0, y0, x1, y1 = LEG[k]
            t.mul((x0, 244, x1, 256), .86); t.ribs((x0, 244, x1, 256), .82)
            t.mul((x0, 236, x1, 244), .95)

        def det(d):
            d.line([(189, 242), (187, 254)], fill=rgb(WHITE), width=2); d.line([(195, 242), (197, 254)], fill=rgb(WHITE), width=2)
            d.line([(166, 244), (172, 256)], fill=sh(m, .7), width=2); d.line([(218, 244), (212, 256)], fill=sh(m, .7), width=2)
            d.line([(16, 160), (16, 244)], fill=sh(m, .8))
        draw_on(t, det)
    elif kind == 'cargo':
        def det(d):
            for (x0, x1) in ((160, 224), (256, 320), (128, 160), (224, 256)):
                d.rectangle((x0, 232, x1, 240), fill=sh(m, .85))
            for x in (166, 182, 202, 218, 262, 288, 314):
                d.rectangle((x - 1, 231, x + 1, 241), fill=sh(m, .7))                               # passants
            d.rectangle((188, 233, 196, 239), fill=rgb(o.get('belt', 0x1A1A1D)))
            d.line([(192, 240), (192, 256)], fill=sh(m, .65))
            d.rectangle((4, 192, 28, 222), outline=sh(m, .65), fill=sh(m, .95))                       # poche cargo (relief en plus)
            d.rectangle((4, 188, 28, 196), fill=sh(m, .82))
            for k in ('F',):
                x0, y0, x1, y1 = LEG[k]
                d.line([(x0, 206), (x1, 206)], fill=sh(m, .72))                                     # genou
                d.line([(x0, 212), (x1, 212)], fill=sh(m, .72))
            for x0 in (0, 32, 64, 96):
                d.rectangle((x0, 250, x0 + 32, 256), fill=sh(m, .85))
        draw_on(t, det)
    else:   # jean
        def det(d):
            for (x0, x1) in ((160, 224), (256, 320), (128, 160), (224, 256)):
                d.rectangle((x0, 232, x1, 240), fill=sh(m, .9))
                d.line([(x0, 233), (x1, 233)], fill=st); d.line([(x0, 239), (x1, 239)], fill=st)
            for x in (166, 182, 202, 218, 262, 288, 314):
                d.rectangle((x - 1, 231, x + 1, 242), fill=sh(m, .8))
            d.ellipse((189, 233, 195, 239), fill=rgb(0xB89A5A))                                     # bouton
            d.line([(196, 240), (196, 252), (192, 256)], fill=st)                                   # braguette en J
            d.arc((164, 236, 182, 254), 270, 360, fill=st); d.arc((202, 236, 220, 254), 180, 270, fill=st)
            for px in (262, 292):                                                                   # poches arrière
                d.polygon([(px, 242), (px + 22, 242), (px + 22, 256), (px, 256)], outline=st)
                d.line([(px + 4, 248), (px + 11, 252), (px + 18, 248)], fill=st)
            for x0 in (0, 32, 64, 96):
                d.rectangle((x0, 250, x0 + 32, 256), fill=sh(m, .85))
                d.line([(x0, 251), (x0 + 32, 251)], fill=st)
            d.line([(0, 160), (0, 250)], fill=st); d.line([(31, 160), (31, 250)], fill=st)            # coutures latérales
            for y in (166, 170, 174):                                                               # moustaches délavées
                d.line([(36, y), (46, y + 2)], fill=sh(m, 1.35)); d.line([(60, y), (50, y + 2)], fill=sh(m, 1.35))
        draw_on(t, det)
        t.mul((40, 160, 56, 200), 1.12)                                                             # usure sur le devant des cuisses


# ---------------------------------------------------------------- formes 3D portées

def arm_x(side, slim):
    if side == 'right':
        return (-2.0 if slim else -3.0), 1.0
    return -1.0, (2.0 if slim else 3.0)


def sym(boxes):
    """Ajoute le miroir (x -> -x) de chaque cube."""
    out = list(boxes)
    for (p, x0, y0, z0, x1, y1, z1, s) in boxes:
        q = {'right_leg': 'left_leg', 'left_leg': 'right_leg', 'right_arm': 'left_arm', 'left_arm': 'right_arm'}.get(p, p)
        out.append((q, -x1, y0, z0, -x0, y1, z1, s))
    return out


def shape_cap(slim):
    return [('head', -4.55, -8.6, -4.55, 4.55, -6.0, 4.55, 'main'), ('head', -4.05, -9.2, -4.05, 4.05, -8.6, 4.05, 'main'),
            ('head', -2.4, -9.6, -2.4, 2.4, -9.2, 2.4, 'main'), ('head', -0.5, -10.0, -0.5, 0.5, -9.6, 0.5, 'dark'),
            ('head', -4.62, -6.5, -4.62, 4.62, -5.9, 4.62, 'dark'), ('head', -3.6, -6.4, -7.0, 3.6, -5.9, -4.5, 'main'),
            ('head', -3.2, -6.1, -7.6, 3.2, -5.7, -7.0, 'main'), ('head', -3.5, -5.9, -6.9, 3.5, -5.8, -4.6, 'dark'),
            ('head', -1.3, -8.3, -4.7, 1.3, -6.7, -4.55, 'light'), ('head', -0.6, -7.9, -4.76, 0.6, -7.1, -4.7, 'accent'),
            ('head', -1.8, -6.6, 4.5, 1.8, -5.9, 5.0, 'strap'), ('head', -0.4, -6.7, 4.95, 0.4, -6.0, 5.1, 'metal')]


def shape_beanie(slim):
    return [('head', -4.5, -8.9, -4.5, 4.5, -5.6, 4.5, 'main'), ('head', -4.0, -9.5, -4.0, 4.0, -8.9, 4.0, 'main'),
            ('head', -2.8, -9.9, -2.8, 2.8, -9.5, 2.8, 'main_hi'), ('head', -4.72, -6.9, -4.72, 4.72, -5.2, 4.72, 'dark'),
            ('head', -1.1, -6.6, -4.86, 1.1, -5.5, -4.72, 'accent'), ('head', -0.6, -6.3, -4.9, 0.6, -5.8, -4.86, 'light')]


def shape_bucket(slim):
    return [('head', -4.45, -9.0, -4.45, 4.45, -6.2, 4.45, 'main'), ('head', -4.0, -9.4, -4.0, 4.0, -9.0, 4.0, 'main_hi'),
            ('head', -4.6, -6.9, -4.6, 4.6, -6.1, 4.6, 'dark'), ('head', -5.7, -6.3, -5.7, 5.7, -5.8, 5.7, 'main'),
            ('head', -6.4, -5.9, -6.4, 6.4, -5.4, 6.4, 'main_hi'), ('head', -1.0, -8.2, -4.56, 1.0, -7.4, -4.45, 'light')]


def shape_round(slim):
    b = []
    for s in (-1, 1):
        cx = 2.0 * s
        b += [('head', cx - 1.5, -4.5, -4.7, cx + 1.5, -2.9, -4.55, 'lens'), ('head', cx - 1.1, -4.9, -4.7, cx + 1.1, -2.5, -4.55, 'lens'),
              ('head', cx - 1.1, -5.15, -4.8, cx + 1.1, -4.9, -4.45, 'metal'), ('head', cx - 1.1, -2.5, -4.8, cx + 1.1, -2.25, -4.45, 'metal'),
              ('head', cx - 1.75, -4.5, -4.8, cx - 1.5, -2.9, -4.45, 'metal'), ('head', cx + 1.5, -4.5, -4.8, cx + 1.75, -2.9, -4.45, 'metal'),
              ('head', cx - 1.5, -4.9, -4.8, cx - 1.1, -4.5, -4.45, 'metal'), ('head', cx + 1.1, -4.9, -4.8, cx + 1.5, -4.5, -4.45, 'metal'),
              ('head', cx - 1.5, -2.9, -4.8, cx - 1.1, -2.5, -4.45, 'metal'), ('head', cx + 1.1, -2.9, -4.8, cx + 1.5, -2.5, -4.45, 'metal'),
              ('head', cx - 0.9, -4.6, -4.75, cx - 0.3, -4.3, -4.7, 'lens_hi')]
        xo0, xo1 = (cx + 1.75, 4.4) if s > 0 else (-4.4, cx - 1.75)
        b.append(('head', xo0, -4.5, -4.8, xo1, -4.2, -4.45, 'metal'))
        b.append(('head', 4.15 if s > 0 else -4.4, -4.5, -4.6, 4.4 if s > 0 else -4.15, -4.2, 2.5, 'metal'))   # branche
    b.append(('head', -0.5, -4.4, -4.8, 0.5, -4.1, -4.5, 'metal'))
    return b


def shape_shield(slim):
    return [('head', -4.3, -5.0, -4.8, 4.3, -2.8, -4.55, 'lens'), ('head', -4.4, -5.3, -4.85, 4.4, -5.0, -4.5, 'main'),
            ('head', -4.55, -5.0, -4.6, -4.3, -3.0, -3.0, 'lens'), ('head', 4.3, -5.0, -4.6, 4.55, -3.0, -3.0, 'lens'),
            ('head', -4.55, -4.9, -3.0, -4.3, -4.5, 2.5, 'main'), ('head', 4.3, -4.9, -3.0, 4.55, -4.5, 2.5, 'main'),
            ('head', -3.5, -4.7, -4.86, -1.5, -4.4, -4.8, 'lens_hi'), ('head', -0.6, -3.2, -4.86, 0.6, -2.8, -4.8, 'main')]


CHAIN_PATH = [(2.7, 0.3), (2.55, 1.0), (2.35, 1.7), (2.05, 2.4), (1.7, 3.05), (1.25, 3.6), (0.7, 4.0), (0.0, 4.15)]


def chain(path, size, depth, sws):
    b = []
    for i, (x, y) in enumerate(path):
        for s in ((1, -1) if x > 0 else (1,)):
            cx = x * s
            b.append(('body', cx - size / 2, y - size / 2, -2.3 - depth, cx + size / 2, y + size / 2, -2.3, sws[i % len(sws)]))
    return b


def shape_cuban(slim):
    b = chain(CHAIN_PATH, .8, .35, ['metal', 'metal_dark'])
    b.append(('body', -2.9, 0.0, 2.3, 2.9, 0.6, 2.65, 'metal'))
    return b


def shape_cross(slim):
    path = [(2.7, 0.3), (2.55, 1.1), (2.3, 1.9), (2.0, 2.7), (1.6, 3.4), (1.1, 4.1), (0.55, 4.6), (0.0, 4.8)]
    b = chain(path, .5, .25, ['metal'])
    b += [('body', -0.35, 5.3, -2.75, 0.35, 8.3, -2.3, 'metal'), ('body', -1.05, 6.0, -2.75, 1.05, 6.7, -2.3, 'metal'),
          ('body', -0.2, 4.9, -2.6, 0.2, 5.3, -2.35, 'metal_dark'), ('body', -2.9, 0.0, 2.3, 2.9, 0.4, 2.55, 'metal')]
    return b


def shape_pearls(slim):
    path = [(2.6, 0.3), (2.4, 0.95), (2.1, 1.6), (1.7, 2.2), (1.2, 2.7), (0.6, 3.0), (0.0, 3.1)]
    b = chain(path, .6, .5, ['white', 'second'])
    b.append(('body', -2.9, 0.0, 2.3, 2.9, 0.55, 2.7, 'white'))
    return b


def shape_scarf(slim):
    return [('body', -4.65, -1.6, -2.85, 4.65, 0.9, 2.85, 'main'), ('body', -4.85, 0.5, -3.05, 4.85, 2.0, 3.05, 'dark'),
            ('body', 0.8, 1.6, -3.45, 3.2, 8.6, -3.0, 'main'), ('body', 0.8, 8.6, -3.45, 3.2, 9.3, -3.0, 'light'),
            ('body', -3.0, 1.6, -3.4, -0.8, 6.0, -2.95, 'dark')]


def shape_watch(slim, sport=False):
    x0, x1 = arm_x('left', slim)
    big = .2 if sport else 0
    e = x1 + 0.52 + big                      # face du cadran (boîtier fin, pas une barre qui dépasse)
    return [('left_arm', x0 - 0.3, 7.15 - big, -2.3, x1 + 0.3, 7.95 + big, 2.3, 'strap'),
            ('left_arm', x1 + 0.3, 6.8 - big, -0.85 - big, e, 8.3 + big, 0.85 + big, 'metal'),
            ('left_arm', e, 7.0 - big, -0.65 - big, e + 0.04, 8.1 + big, 0.65 + big, 'second'),
            ('left_arm', x1 + 0.35, 7.4, 0.85 + big, x1 + 0.5, 7.7, 1.05 + big, 'metal'),
            ('left_arm', e + 0.04, 7.1, -0.06, e + 0.07, 7.6, 0.06, 'white'),
            ('left_arm', e + 0.04, 7.5, -0.06, e + 0.07, 7.62, 0.45, 'white')]


def shape_bracelet(slim):
    x0, x1 = arm_x('right', slim)
    return [('right_arm', x0 - 0.3, 7.6, -2.3, x1 + 0.3, 8.1, 2.3, 'metal'),
            ('right_arm', x0 - 0.45, 7.45, -0.8, x0 - 0.3, 8.25, 0.8, 'metal_dark')]


def shape_gloves(slim):
    b = []
    for side in ('right', 'left'):
        x0, x1 = arm_x(side, slim)
        p = side + '_arm'
        out = x0 - 0.3 if side == 'right' else x1 + 0.3
        b += [(p, x0 - 0.3, 6.9, -2.3, x1 + 0.3, 10.3, 2.3, 'main'), (p, x0 - 0.42, 6.5, -2.42, x1 + 0.42, 7.3, 2.42, 'dark')]
        for z in (-1.1, 0.0, 1.1):
            xa, xb = (out - 0.05, out) if side == 'right' else (out, out + 0.05)
            b.append((p, xa, 7.7, z - 0.07, xb, 9.7, z + 0.07, 'light'))
    return b


def strap_steps(x_a, y_a, x_b, y_b, n, z0, z1, sw='strap', w=1.05):
    b = []
    for i in range(n):
        t = i / (n - 1)
        x = x_a + (x_b - x_a) * t
        y = y_a + (y_b - y_a) * t
        b.append(('body', x - w / 2, y - w / 2, z0, x + w / 2, y + w / 2, z1, sw))
    return b


def shape_backpack(slim):
    b = [('body', -3.2, 0.9, 2.3, 3.2, 9.8, 5.1, 'main'), ('body', -2.8, 0.5, 2.5, 2.8, 0.9, 4.9, 'main'),
         ('body', -2.6, 5.0, 5.1, 2.6, 9.2, 5.8, 'dark'), ('body', -2.4, 5.0, 5.8, 2.4, 5.2, 5.9, 'metal'),
         ('body', 1.6, 5.2, 5.8, 1.9, 5.9, 5.95, 'metal'), ('body', -3.0, 1.6, 5.1, 3.0, 1.8, 5.2, 'metal'),
         ('body', -0.7, 6.4, 5.8, 0.7, 7.4, 5.9, 'light'), ('body', -3.25, 9.4, 2.25, 3.25, 10.0, 5.15, 'strap'),
         ('body', -0.8, 0.1, 3.4, 0.8, 0.5, 3.8, 'strap')]
    b += sym([('body', 1.3, 0.0, -2.6, 2.5, 7.6, -2.3, 'strap'), ('body', 1.4, 6.0, -2.7, 2.4, 6.5, -2.6, 'metal_dark'),
              ('body', 1.3, 0.0, 2.3, 2.5, 1.0, 2.6, 'strap')])
    return b


def shape_fanny(slim):
    b = [('body', -3.4, 4.0, -3.8, 1.2, 6.8, -2.3, 'main'), ('body', -3.1, 6.8, -3.6, 0.9, 7.2, -2.4, 'main'),
         ('body', -3.3, 4.3, -3.9, 1.1, 4.5, -3.8, 'metal'), ('body', 0.4, 4.4, -3.95, 0.7, 5.1, -3.85, 'metal'),
         ('body', -1.6, 5.3, -3.9, -0.6, 6.1, -3.8, 'light')]
    b += strap_steps(1.5, 4.0, 3.3, 0.4, 4, -2.6, -2.3)
    b += [('body', -4.0, 5.8, -2.6, -3.3, 7.2, -2.3, 'strap'), ('body', -4.35, 6.8, -2.3, -4.05, 7.6, 2.3, 'strap')]
    b += strap_steps(-4.0, 7.2, 3.4, 0.4, 8, 2.3, 2.6)
    return b


def shape_sacoche(slim):
    b = [('body', -3.8, 5.2, -3.4, -0.6, 9.4, -2.3, 'main'), ('body', -3.85, 5.1, -3.5, -0.55, 7.0, -3.4, 'dark'),
         ('body', -2.6, 6.2, -3.56, -1.8, 6.8, -3.5, 'metal'), ('body', -2.8, 7.9, -3.45, -1.6, 8.7, -3.4, 'light')]
    b += strap_steps(-0.8, 5.0, 3.3, 0.4, 6, -2.6, -2.3, w=.95)
    b += [('body', -4.35, 5.2, -2.3, -4.05, 6.0, 2.3, 'strap')]
    b += strap_steps(-4.0, 5.6, 3.4, 0.4, 7, 2.3, 2.6, w=.95)
    return b


def shape_duffel(slim):
    """Sac de sport porté dans le dos, à l'horizontale, bandoulière en travers du torse."""
    b = [('body', -4.8, 3.0, 2.3, 4.8, 7.4, 6.3, 'main'), ('body', -5.2, 3.3, 2.6, -4.8, 7.1, 6.0, 'dark'),
         ('body', 4.8, 3.3, 2.6, 5.2, 7.1, 6.0, 'dark'), ('body', -2.6, 4.2, 6.3, 2.6, 5.4, 6.4, 'light'),
         ('body', -4.4, 2.8, 3.6, 4.4, 3.0, 5.0, 'metal'), ('body', -4.8, 7.2, 2.25, 4.8, 7.6, 6.35, 'dark'),
         ('body', -2.0, 2.2, 4.0, -1.4, 3.0, 4.6, 'strap'), ('body', 1.4, 2.2, 4.0, 2.0, 3.0, 4.6, 'strap'),
         ('body', 2.6, 0.0, 2.3, 3.6, 3.0, 2.6, 'strap'), ('body', -4.35, 7.4, -2.3, -4.05, 9.4, 2.3, 'strap')]
    b += strap_steps(-3.6, 9.0, 3.3, 0.4, 7, -2.6, -2.3)
    return b


def shape_hiking(slim):
    """Gros sac de randonnée : rabat, poche frontale, poches latérales, tapis de sol roulé, sangle de poitrine."""
    b = [('body', -3.6, -1.5, 2.3, 3.6, 10.5, 6.6, 'main'), ('body', -3.8, -2.6, 2.4, 3.8, -0.9, 6.9, 'dark'),
         ('body', -2.6, 3.0, 6.6, 2.6, 8.0, 7.3, 'second'), ('body', -2.4, 3.0, 7.3, 2.4, 3.2, 7.4, 'metal'),
         ('body', -0.6, 5.0, 7.3, 0.6, 6.0, 7.4, 'light'),
         ('body', -4.6, 10.5, 3.2, 4.6, 12.5, 5.6, 'light'),
         ('body', -1.6, 3.0, -2.75, 1.6, 3.6, -2.6, 'strap'), ('body', -0.4, 2.9, -2.8, 0.4, 3.7, -2.7, 'metal')]
    b += sym([('body', 1.4, -1.2, 6.6, 1.9, 2.0, 6.9, 'strap'), ('body', 3.6, 5.0, 3.0, 4.3, 9.5, 6.0, 'dark'),
              ('body', 2.0, 10.3, 3.1, 2.5, 12.7, 5.7, 'strap'), ('body', 1.2, 0.0, -2.65, 2.4, 8.0, -2.3, 'strap'),
              ('body', 1.2, 0.0, 2.3, 2.4, 1.0, 2.6, 'strap')])
    return b


def ring(y0, y1, r, sw, part='body', hx=4.0, hz=2.0):
    return (part, -hx - r, y0, -hz - r, hx + r, y1, hz + r, sw)


def shape_puffer(slim, hood=True):
    b = [ring(-0.9, 0.9, .85, 'main_hi')]
    if hood:
        b += [('body', -3.3, -0.6, 2.55, 3.3, 2.4, 4.3, 'main'), ('body', -3.5, -0.9, 2.5, 3.5, 0.0, 4.5, 'dark')]
    return b


def shape_hoodie(slim):
    b = [('body', -3.4, -0.4, 2.3, 3.4, 3.0, 4.2, 'main'), ('body', -3.6, -0.8, 2.2, 3.6, 0.2, 4.4, 'dark')]
    b += sym([('body', 3.4, -0.6, 0.6, 4.4, 1.4, 3.8, 'main'), ('body', 0.9, 0.0, -2.6, 1.3, 4.4, -2.3, 'light'),
              ('body', 0.85, 4.4, -2.65, 1.35, 5.1, -2.25, 'metal')])
    return b


def shape_bomber(slim):
    return [ring(-0.5, 0.7, .48, 'dark')]


def shape_perfecto(slim):
    return [ring(-0.5, 0.6, .5, 'dark'), ring(10.4, 11.2, .42, 'dark'), ('body', -3.6, 10.25, -2.62, -2.6, 11.35, -2.5, 'metal')]


def shape_coat(slim, trench=False):
    b = [ring(-0.6, 0.8, .55, 'main_hi')]
    b += sym([('right_leg', -2.5, -0.4, -2.5, 2.5, 7.6, 2.5, 'main'), ('right_leg', -2.56, 7.2, -2.56, 2.56, 7.8, 2.56, 'dark')])
    if trench:
        b += [ring(9.4, 10.4, .45, 'main_hi'), ('body', -0.6, 9.3, -2.56, 0.6, 10.5, -2.45, 'metal'),
              ('body', 1.2, 10.4, -2.6, 1.7, 13.2, -2.45, 'main_hi')]
    return b


def shape_cargo(slim):
    return sym([('right_leg', -2.45, 4.0, -1.5, -2.1, 7.6, 1.5, 'main'), ('right_leg', -2.55, 3.7, -1.6, -2.1, 4.6, 1.6, 'dark'),
                ('right_leg', -2.6, 4.0, -0.2, -2.55, 4.3, 0.2, 'metal')])


SHAPES = {'CAP': shape_cap, 'BEANIE': shape_beanie, 'BUCKET': shape_bucket, 'ROUND': shape_round, 'SHIELD': shape_shield,
          'CUBAN': shape_cuban, 'CROSS': shape_cross, 'PEARLS': shape_pearls, 'SCARF2': shape_scarf,
          'WATCH': shape_watch, 'WATCH_SPORT': lambda s: shape_watch(s, True), 'BRACELET': shape_bracelet, 'GLOVES': shape_gloves,
          'BACKPACK': shape_backpack, 'FANNY': shape_fanny, 'SACOCHE': shape_sacoche, 'DUFFEL': shape_duffel, 'HIKING': shape_hiking,
          'PUFFER2': shape_puffer, 'GILET': lambda s: shape_puffer(s, False), 'HOODIE2': shape_hoodie, 'BOMBER': shape_bomber,
          'PERFECTO': shape_perfecto, 'COAT': shape_coat, 'TRENCH': lambda s: shape_coat(s, True), 'CARGO': shape_cargo}
PARTS = ['head', 'body', 'right_arm', 'left_arm', 'right_leg', 'left_leg']


# ---------------------------------------------------------------- catalogue

def C(id, fr, en, kind, shape=None, **p):
    return dict(id=id, fr=fr, en=en, kind=kind, shape=shape, **p)


CLOTHES = [
    # doudounes (modèle gonflé, voir SlimArmor)
    C('doudoune_noire', 'Doudoune Moncleur noire', 'Moncleur puffer jacket (black)', 'puffer', 'PUFFER2', main=0x18181C),
    C('doudoune_rouge', 'Doudoune Moncleur rouge', 'Moncleur puffer jacket (red)', 'puffer', 'PUFFER2', main=0xB01B24),
    C('doudoune_marine', 'Doudoune Moncleur bleu marine', 'Moncleur puffer jacket (navy)', 'puffer', 'PUFFER2', main=0x1A2A50),
    C('doudoune_creme', 'Doudoune Moncleur crème', 'Moncleur puffer jacket (cream)', 'puffer', 'PUFFER2', main=0xE6DCC6, zip=0x8A8070),
    C('doudoune_kaki', 'Doudoune Moncleur kaki', 'Moncleur puffer jacket (khaki)', 'puffer', 'PUFFER2', main=0x4B5636, shiny=False),
    C('gilet_noir', 'Gilet doudoune sans manches noir', 'Puffer vest (black)', 'puffer', 'GILET', main=0x18181C, gilet=True),
    C('gilet_bordeaux', 'Gilet doudoune sans manches bordeaux', 'Puffer vest (burgundy)', 'puffer', 'GILET', main=0x5E1622, gilet=True),
    # sweats à capuche
    C('sweat_gris', 'Sweat à capuche Essentiel gris chiné', 'Essentiel hoodie (heather grey)', 'hoodie', 'HOODIE2', main=0x9A9DA2, heather=.07, logo_col=0x5A5D62),
    C('sweat_noir', 'Sweat à capuche Essentiel noir', 'Essentiel hoodie (black)', 'hoodie', 'HOODIE2', main=0x1C1C20, logo_col=0x5A5A60, cord=0x2A2A2E),
    C('sweat_beige', 'Sweat à capuche Essentiel beige', 'Essentiel hoodie (beige)', 'hoodie', 'HOODIE2', main=0xC9B596, logo_col=0x8A7A60, cord=0xC9B596),
    C('sweat_bordeaux', 'Sweat à capuche Essentiel bordeaux', 'Essentiel hoodie (burgundy)', 'hoodie', 'HOODIE2', main=0x6A1A26, logo_col=0xE8DCD0),
    C('sweat_vert', 'Sweat à capuche Essentiel vert forêt', 'Essentiel hoodie (forest green)', 'hoodie', 'HOODIE2', main=0x23402F, logo_col=0xE8DCD0),
    # vestes
    C('bomber_kaki', 'Bomber Alpha kaki', 'Alpha bomber jacket (khaki)', 'bomber', 'BOMBER', main=0x4E5A3A),
    C('bomber_noir', 'Bomber Alpha noir', 'Alpha bomber jacket (black)', 'bomber', 'BOMBER', main=0x1A1A1E),
    C('bomber_marine', 'Bomber Alpha bleu marine', 'Alpha bomber jacket (navy)', 'bomber', 'BOMBER', main=0x1C2740),
    C('perfecto_noir', 'Perfecto en cuir noir', 'Leather biker jacket (black)', 'perfecto', 'PERFECTO', main=0x1E1E22, metal=SILVER),
    C('perfecto_marron', 'Perfecto en cuir marron', 'Leather biker jacket (brown)', 'perfecto', 'PERFECTO', main=0x5A3420, metal=SILVER),
    # manteaux
    C('manteau_camel', 'Manteau long en laine camel', 'Long wool coat (camel)', 'coat', 'COAT', main=0xB5875A),
    C('manteau_noir', 'Manteau long en laine noir', 'Long wool coat (black)', 'coat', 'COAT', main=0x222226, btn=0x0E0E10),
    C('manteau_gris', 'Manteau long en laine gris anthracite', 'Long wool coat (charcoal)', 'coat', 'COAT', main=0x46484E),
    C('trench_beige', 'Trench beige', 'Trench coat (beige)', 'coat', 'TRENCH', main=0xC8AE82, trench=True, metal=0x8A7A5A, btn=0x3A2E22),
    # pantalons
    C('jogging_gris', 'Jogging gris chiné', 'Joggers (heather grey)', 'pants', None, main=0x8E9196, heather=.07, pants='jogging'),
    C('jogging_noir', 'Jogging noir', 'Joggers (black)', 'pants', None, main=0x1E1E22, pants='jogging'),
    C('cargo_kaki', 'Pantalon cargo kaki', 'Cargo pants (khaki)', 'pants', 'CARGO', main=0x55603F, pants='cargo'),
    C('cargo_noir', 'Pantalon cargo noir', 'Cargo pants (black)', 'pants', 'CARGO', main=0x202024, pants='cargo'),
    C('cargo_beige', 'Pantalon cargo beige', 'Cargo pants (beige)', 'pants', 'CARGO', main=0xBFA982, pants='cargo'),
    C('jean_brut', 'Jean slim brut', 'Slim jeans (raw denim)', 'pants', None, main=0x23324F, pants='jean', stitch=0xC8873A),
    C('jean_noir', 'Jean slim noir', 'Slim jeans (black)', 'pants', None, main=0x24252A, pants='jean', stitch=0x55565C),
]

HATS = [
    C('casquette_noire', 'Casquette noire', 'Cap (black)', 'hat', 'CAP', main=0x18181B, light=WHITE, accent=0x18181B),
    C('casquette_blanche', 'Casquette blanche', 'Cap (white)', 'hat', 'CAP', main=0xEDEDE8, light=0x1B2A55, accent=WHITE),
    C('casquette_rouge', 'Casquette rouge', 'Cap (red)', 'hat', 'CAP', main=0xB01B24, light=WHITE, accent=0xB01B24),
    C('casquette_marine', 'Casquette bleu marine', 'Cap (navy)', 'hat', 'CAP', main=0x1A2A50, light=WHITE, accent=0x1A2A50),
    C('casquette_beige', 'Casquette beige', 'Cap (beige)', 'hat', 'CAP', main=0xCDB892, light=0x3A2E22, accent=0xCDB892),
    C('bonnet_noir', 'Bonnet noir', 'Beanie (black)', 'hat', 'BEANIE', main=0x1C1C20, accent=0xE07A1E, light=0x1C1C20),
    C('bonnet_gris', 'Bonnet gris chiné', 'Beanie (heather grey)', 'hat', 'BEANIE', main=0x8E9196, accent=0x1C1C20, light=WHITE),
    C('bonnet_rouge', 'Bonnet rouge', 'Beanie (red)', 'hat', 'BEANIE', main=0xA81C24, accent=0x1C1C20, light=WHITE),
    C('bonnet_moutarde', 'Bonnet moutarde', 'Beanie (mustard)', 'hat', 'BEANIE', main=0xC8962A, accent=0x1C1C20, light=WHITE),
    C('bonnet_marine', 'Bonnet bleu marine', 'Beanie (navy)', 'hat', 'BEANIE', main=0x1A2A50, accent=0xE07A1E, light=0x1A2A50),
    C('bob_noir', 'Bob noir', 'Bucket hat (black)', 'hat', 'BUCKET', main=0x1C1C20, light=WHITE),
    C('bob_beige', 'Bob beige', 'Bucket hat (beige)', 'hat', 'BUCKET', main=0xCDB892, light=0x3A2E22),
    C('bob_blanc', 'Bob blanc', 'Bucket hat (white)', 'hat', 'BUCKET', main=0xEDEDE8, light=0x1C1C20),
    C('bob_kaki', 'Bob kaki', 'Bucket hat (khaki)', 'hat', 'BUCKET', main=0x4E5A3A, light=0xE8DCC0),
]

# id, nom, emplacement, forme, palette
ACCS = [
    C('lunettes_rondes', 'Lunettes rondes dorées', 'Round gold sunglasses', 'VISAGE', 'ROUND', main=GOLD, metal=GOLD, lens=0x2C3A32, lens_hi=0x7A9A88),
    C('lunettes_masque', 'Lunettes masque Y2K', 'Y2K shield sunglasses', 'VISAGE', 'SHIELD', main=0x141416, lens=0x30204A, lens_hi=0x9A7AD0),
    C('chaine_or', 'Chaîne cubaine en or', 'Gold cuban chain', 'COU', 'CUBAN', main=GOLD),
    C('chaine_argent', 'Chaîne cubaine en argent', 'Silver cuban chain', 'COU', 'CUBAN', main=SILVER, metal=SILVER, metal_dark=SILVER_D),
    C('chaine_croix', 'Chaîne en or à croix', 'Gold cross chain', 'COU', 'CROSS', main=GOLD),
    C('collier_perles', 'Collier de perles', 'Pearl necklace', 'COU', 'PEARLS', main=0xF4F1EA, white=0xF6F3EC, second=0xE2DACB),
    C('echarpe_noire', 'Écharpe en laine noire', 'Black wool scarf', 'COU', 'SCARF2', main=0x1E1E22, light=0x5A5A60),
    C('montre_or', 'Montre Rolax or', 'Rolax gold watch', 'POIGNET', 'WATCH', main=GOLD, strap=GOLD_D, second=0x1E5A3A),
    C('montre_argent', 'Montre Rolax acier', 'Rolax steel watch', 'POIGNET', 'WATCH', main=SILVER, metal=SILVER, strap=SILVER_D, second=0x1E3A7A),
    C('montre_sport', 'Montre G-Chock noire', 'G-Chock black watch', 'POIGNET', 'WATCH_SPORT', main=0x1A1A1D, metal=0x26262A, strap=0x1A1A1D, second=0x8A9088),
    C('gourmette_or', 'Gourmette en or', 'Gold ID bracelet', 'POIGNET', 'BRACELET', main=GOLD),
    C('gants_cuir_noir', 'Gants en cuir noirs', 'Black leather gloves', 'MAINS', 'GLOVES', main=0x1A1A1D, light=0x3A3A40),
    C('gants_cuir_marron', 'Gants en cuir marron', 'Brown leather gloves', 'MAINS', 'GLOVES', main=0x5A3420, light=0x2E1A10),
    C('gants_laine', 'Gants en laine gris', 'Grey wool gloves', 'MAINS', 'GLOVES', main=0x7D8086, light=0x5A5D62),
    C('sac_dos_noir', 'Sac à dos noir', 'Black backpack', 'DOS', 'BACKPACK', main=0x1E1E22, light=0xC8202A),
    C('sac_dos_rouge', 'Sac à dos rouge', 'Red backpack', 'DOS', 'BACKPACK', main=0xA81C24, light=WHITE),
    C('sac_dos_kaki', 'Sac à dos kaki', 'Khaki backpack', 'DOS', 'BACKPACK', main=0x4E5A3A, light=0xE07A1E),
    C('banane_noire', 'Banane noire', 'Black crossbody bag', 'DOS', 'FANNY', main=0x1E1E22, light=WHITE, metal=SILVER),
    C('banane_guchi', 'Banane Guchi monogramme', 'Guchi monogram crossbody bag', 'DOS', 'FANNY', main=0xB89A6A, light=0x1E6B3A, strap=0x5A3A22),
    C('sacoche_noire', 'Sacoche noire', 'Black shoulder pouch', 'DOS', 'SACOCHE', main=0x1E1E22, light=0x1E6B3A, metal=SILVER),
    # Sacs de rangement (contenance : voir Bags.java)
    C('sacoche_lacroste', 'Sacoche Lacroste blanche', 'Sacoche Lacroste blanche', 'DOS', 'SACOCHE', main=0xEDEDE8, light=0x1E6B3A, metal=SILVER),
    C('banane_nayk', 'Banane Nayk grise', 'Banane Nayk grise', 'DOS', 'FANNY', main=0x8A8D92, light=0x141416, metal=SILVER),
    C('sac_sport_noir', 'Sac de sport Nayk noir', 'Sac de sport Nayk noir', 'DOS', 'DUFFEL', main=0x1E1E22, light=WHITE, metal=SILVER),
    C('sac_sport_bleu', 'Sac de sport bleu roi', 'Sac de sport bleu roi', 'DOS', 'DUFFEL', main=0x1F4FB0, light=WHITE, metal=SILVER),
    C('sac_rando_orange', 'Sac de randonnée orange', 'Sac de randonnée orange', 'DOS', 'HIKING', main=0xD2691E, second=0x3A3A40, light=0x7A9A5A, metal=SILVER),
    C('sac_rando_vert', 'Sac de randonnée vert forêt', 'Sac de randonnée vert forêt', 'DOS', 'HIKING', main=0x2F5A3A, second=0x6A6A70, light=0xC8A050, metal=SILVER),
    C('sac_luxe_vuiten', 'Sac à dos Louis Vuiten monogramme', 'Sac à dos Louis Vuiten monogramme', 'DOS', 'BACKPACK', main=0x6B4423, dark=0x4A2E18, light=0xC9A24A, metal=GOLD),
    # Réservés aux grades (avantage « vetementsVip » du mod VIP : 1 = VIP, 2 = VIP+), voir VipItems.java
    C('chaine_vip', 'Chaîne cubaine VIP violette', 'VIP purple cuban chain', 'COU', 'CUBAN', main=0xA048E0, metal=0xA048E0, metal_dark=0x5A2088),
    C('montre_vip', 'Montre Rolax VIP or et violet', 'VIP gold and purple Rolax watch', 'POIGNET', 'WATCH', main=GOLD, strap=0x5A2088, second=0xC83CF0),
    C('chaine_diamant', 'Chaîne en diamants VIP+', 'VIP+ diamond chain', 'COU', 'CUBAN', main=0xD8F4FF, metal=0xE8FAFF, metal_dark=0x7FB8D8),
    C('montre_diamant', 'Montre Rolax sertie VIP+', 'VIP+ iced-out Rolax watch', 'POIGNET', 'WATCH', main=0xE8FAFF, metal=0xE8FAFF, strap=0xB8D8EC, second=0x20AAEB),
    C('sac_vip', 'Sac à dos VIP violet', 'Sac à dos VIP violet', 'DOS', 'BACKPACK', main=0x6A28B0, light=0xC83CF0, metal=GOLD),
    C('lunettes_holo', 'Lunettes holographiques VIP+', 'VIP+ holographic shield sunglasses', 'VISAGE', 'SHIELD', main=0xE8FAFF, lens=0x20AAEB, lens_hi=0xC83CF0),
]
LEGACY = [('lunettes_aviator', 'VISAGE'), ('lunettes_wayfarer', 'VISAGE'), ('lunettes_sport', 'VISAGE'), ('lunettes_rose', 'VISAGE'),
          ('cagoule_noire', 'VISAGE'), ('cagoule_kaki', 'VISAGE'), ('cagoule_guchi', 'VISAGE'), ('cagoule_guchi_noire', 'VISAGE'),
          ('cagoule_vuiten', 'VISAGE'), ('cagoule_supreem', 'VISAGE'), ('cagoule_nayk', 'VISAGE'), ('bandana_rouge', 'VISAGE'),
          ('bandana_noir', 'VISAGE'), ('echarpe_grise', 'COU'), ('echarpe_rouge', 'COU')]
# ---------------------------------------------------------------- tenues de secours : pompiers et SAMU (02/11)
# Créations originales : aucun insigne ni logo officiel (pas de grenade, pas de croix), seulement des mots (POMPIERS, SAMU, AMBULANCE).

HIVIS, REFL = 0xD4E21E, 0xC6CBD0          # jaune fluo, bande grise réfléchissante
NAVY_SP, SABLE, NAVY_SAMU = 0x1B2436, 0xB59A66, 0x1B2A4E
SOLE = 0x101012


def band(t, keys, d, y, h, hivis=HIVIS, refl=REFL):
    """Bande des tenues d'intervention : jaune fluo avec, au milieu, une bande grise réfléchissante (refl=None : jaune seul)."""
    for k in keys:
        x0, _, x1, _ = d[k]
        if hivis is not None:
            t.fill((x0, y, x1, y + h), hivis, noise=.015, grad=(1.05, .95))
        if refl is not None:
            m = h // 3 if hivis is not None else 0
            t.fill((x0, y + m, x1, y + h - m), refl, noise=.01, sheen=.35)


TORSO, SLEEVES, LEGS4 = ('F', 'B', 'R', 'L'), ('O', 'F', 'I', 'B'), ('O', 'F', 'I', 'B')


def back_text(t, o, y, default_scale=2):
    s = o.get('dos')
    if not s:
        return
    sc, sy = o.get('dos_scale', default_scale), o.get('dos_sy')
    gap, gl = (1, COMPACT) if sc == 2 else (None, None)      # 2 : lettrage serré pour tenir dans la partie visible du dos (~52 px)
    w = text_w(s, sc, gap, gl)
    if o.get('dos_fond') is not None:        # bandeau sombre derrière le lettrage (tenue sable : argent peu lisible sur fond clair)
        t.fill((260, y - 3, 316, y + 5 * (sy or sc) + 3), o['dos_fond'], noise=.02)
    text(t, 288 - w // 2, y, s, o.get('dos_col', REFL), sc, sy, gap, gl)


def paint_feu(o, t):
    """Veste d'intervention (tenue de feu) : rabat tempête, deux bandes bicolores sur le torse et les manches, poche radio, poches à rabat."""
    m = o['main']
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.03, twill=.025, grad=(1.03, .88))
    t.fill(BODY['top'], m, noise=.03); t.fill(ARM['top'], m, noise=.03); t.fill(ARM['bot'], sh(m, .6))
    t.fill((183, 160, 201, 250), sh(m, .93), noise=.02, twill=.02)                     # rabat tempête
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 246, x1, 256), sh(m, .5), noise=.03); t.ribs((x0, 246, x1, 256), .78)   # manchettes en tricot
    band(t, TORSO, BODY, 194, 12); band(t, TORSO, BODY, 236, 12)
    band(t, SLEEVES, ARM, 180, 10); band(t, SLEEVES, ARM, 224, 10)

    def det(d):
        e = sh(m, .6)
        d.line([(183, 160), (183, 250)], fill=e); d.line([(200, 160), (200, 250)], fill=e)
        for y in (170, 186, 214, 228):
            d.rectangle((189, y - 2, 194, y + 2), fill=sh(m, .45))                     # pressions du rabat
        d.rectangle((204, 164, 220, 190), fill=sh(m, .96), outline=e)                  # poche radio (poitrine gauche)
        d.rectangle((204, 164, 220, 170), fill=sh(m, .8))
        d.rectangle((166, 176, 180, 185), fill=rgb(o.get('tape', 0x26262A)))          # bande nominative (velcro)
        d.line([(167, 180), (179, 180)], fill=rgb(REFL))
        for x0 in (164, 204):                                                         # poches basses à rabat
            d.rectangle((x0, 212, x0 + 16, 232), outline=e); d.rectangle((x0, 212, x0 + 16, 217), fill=sh(m, .8))
        d.line([(288, 160), (288, 194)], fill=sh(m, .8))                              # couture du dos
        for k in SLEEVES:
            x0, y0, x1, y1 = ARM[k]
            d.line([(x0, 168), (x1, 168)], fill=sh(m, .78))                           # couture d'épaule
    draw_on(t, det)
    back_text(t, o, 213)


def paint_parka(o, t):
    """Parka d'intervention : capuche roulée, passepoil rouge, bandes bicolores, poches manchon, lettrage dans le dos."""
    m = o['main']
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.025, grad=(1.04, .88), sheen=.06)
    t.fill(BODY['top'], m); t.fill(ARM['top'], m); t.fill(ARM['bot'], sh(m, .6))
    t.mul((256, 160, 320, 170), .78)                                                  # ombre de la capuche roulée
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 246, x1, 256), sh(m, .5), noise=.03); t.ribs((x0, 246, x1, 256), .78)
    hv = o.get('hivis', HIVIS)
    band(t, TORSO, BODY, 196, 10, hv); band(t, TORSO, BODY, 236, 10, hv); band(t, SLEEVES, ARM, 206, 10, hv)

    def det(d):
        e, red = sh(m, .58), rgb(o.get('second', 0xC62828))
        for (x0, x1) in ((128, 160), (160, 224), (224, 256), (256, 320), (320, 448)):
            d.line([(x0, 182), (x1, 182)], fill=red, width=2)                          # passepoil rouge de l'empiècement
        d.rectangle((186, 160, 198, 248), fill=sh(m, .9)); d.line([(186, 160), (186, 248)], fill=e)
        for y in (168, 186, 218, 230):
            d.ellipse((190, y - 2, 194, y + 2), fill=rgb(SILVER), outline=rgb(SILVER_D))   # pressions
        d.line([(166, 212), (174, 232)], fill=e, width=2); d.line([(218, 212), (210, 232)], fill=e, width=2)   # poches manchon
        d.rectangle((204, 166, 218, 178), outline=e)                                  # poche poitrine
    draw_on(t, det)
    back_text(t, o, 214)


def paint_polo(o, t):
    """Polo / t-shirt de caserne : manches courtes, col et patte de boutonnage (polo) ou col rond (t-shirt), empiècement, marquages."""
    m, c2, tee = o['main'], o.get('second', o['main']), o.get('tee', False)
    for r in faces(BODY):
        t.fill(r, m, noise=.04, grad=(1.02, .92))
    t.fill(BODY['top'], m, noise=.04)
    for k in SLEEVES:                                                                 # manches courtes : le reste du bras = peau du skin
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 160, x1, 196), m, noise=.04)
        t.fill((x0, 190, x1, 196), sh(m, .82) if tee else c2, noise=.02)
        if not tee:
            t.ribs((x0, 190, x1, 196), .85)
    t.fill(ARM['top'], m)
    if o.get('yoke') is not None:                                                     # empiècement d'épaules contrasté
        for k in TORSO:
            x0, y0, x1, y1 = BODY[k]
            t.fill((x0, 160, x1, 176), o['yoke'], noise=.03)
        for k in SLEEVES:
            x0, y0, x1, y1 = ARM[k]
            t.fill((x0, 160, x1, 182), o['yoke'], noise=.03)
        t.fill(BODY['top'], o['yoke']); t.fill(ARM['top'], o['yoke'])
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.mul((x0, 250, x1, 256), .88)
    if not tee:
        t.fill((185, 160, 199, 190), c2, noise=.02)                                   # patte de boutonnage
        t.fill((174, 134, 210, 160), c2, noise=.02); t.ribs((174, 134, 210, 160), .86)  # col (dessus des épaules)
    if o.get('liseré') is not None:
        for k in TORSO:
            x0, y0, x1, y1 = BODY[k]
            t.rect((x0, 176, x1, 178), o['liseré'])

    def det(d):
        if tee:
            d.ellipse((176, 150, 208, 170), fill=sh(m, .7)); d.ellipse((180, 148, 204, 166), fill=sh(m, .55))   # col rond côtelé
        else:
            for y in (168, 180):
                d.ellipse((190, y - 2, 194, y + 2), fill=rgb(WHITE), outline=sh(c2, .6))
        if o.get('emblème') == 'flamme':                                              # petite flamme brodée, poitrine gauche
            d.polygon([(212, 168), (216, 176), (215, 184), (209, 184), (207, 177)], fill=rgb(0xC62828))
            d.polygon([(212, 174), (214, 179), (213, 183), (210, 183), (210, 179)], fill=rgb(0xF2B21E))
    draw_on(t, det)
    if o.get('emblème') == 'texte':
        text(t, o.get('emblème_x', 204), 184, o['dos'], o.get('emblème_col', o.get('dos_col', WHITE)), 1)          # sous l'empiècement
    back_text(t, o, o.get('dos_y', 182))


def paint_hivis(o, t):
    """Veste haute visibilité SAMU : haut jaune fluo, bas bleu marine, bandes réfléchissantes, gros lettrage dans le dos."""
    hv, lo = o['accent'], o['main']
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 160, x1, 210), hv, noise=.015, grad=(1.04, .96), sheen=.05)
        t.fill((x0, 210, x1, 256), lo, noise=.03, twill=.02, grad=(1.0, .88))
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 160, x1, 214), hv, noise=.015, grad=(1.04, .96))
        t.fill((x0, 214, x1, 256), lo, noise=.03, twill=.02)
        t.fill((x0, 248, x1, 256), sh(lo, .7), noise=.03); t.ribs((x0, 248, x1, 256), .8)
    t.fill(BODY['top'], hv); t.fill(ARM['top'], hv); t.fill(ARM['bot'], lo)
    band(t, TORSO, BODY, 202, 8, hivis=None); band(t, TORSO, BODY, 240, 8, hivis=None)
    band(t, SLEEVES, ARM, 206, 8, hivis=None); band(t, SLEEVES, ARM, 232, 8, hivis=None)
    t.rect((191, 160, 193, 250), sh(lo, .7)); t.rect((190, 166, 194, 174), SILVER)   # fermeture éclair et tirette

    def det(d):
        d.rectangle((202, 175, 222, 186), fill=rgb(lo))                               # bande poitrine
        d.rectangle((166, 175, 180, 186), fill=rgb(lo))
        d.line([(166, 220), (180, 220)], fill=sh(lo, .6), width=2); d.line([(204, 220), (218, 220)], fill=sh(lo, .6), width=2)
        d.line([(288, 210), (288, 256)], fill=sh(lo, .8))
    draw_on(t, det)
    text(t, 203, 178, o.get('poitrine', 'SAMU'), WHITE, 1)
    back_text(t, o, 172, 3)


def paint_ambu(o, t):
    """Veste softshell d'ambulancier : bleu marine, empiècement jaune fluo, liserés réfléchissants, AMBULANCE dans le dos."""
    m, hv = o['main'], o['accent']
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.02, grad=(1.04, .88), sheen=.08)
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 160, x1, 184), hv, noise=.015, sheen=.05)
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 160, x1, 190), hv, noise=.015)
        t.fill((x0, 248, x1, 256), sh(m, .7)); t.ribs((x0, 248, x1, 256), .82)
    t.fill(BODY['top'], hv); t.fill(ARM['top'], hv); t.fill(ARM['bot'], m)
    band(t, TORSO, BODY, 184, 4, hivis=None); band(t, SLEEVES, ARM, 190, 4, hivis=None)
    band(t, TORSO, BODY, 238, 6, hivis=None); band(t, SLEEVES, ARM, 230, 6, hivis=None)
    t.rect((191, 160, 193, 250), sh(m, .55)); t.rect((190, 192, 194, 200), SILVER)

    def det(d):
        d.line([(166, 214), (176, 230)], fill=sh(m, .55), width=2); d.line([(218, 214), (208, 230)], fill=sh(m, .55), width=2)
        d.rectangle((204, 196, 220, 204), fill=rgb(WHITE)); d.rectangle((206, 198, 218, 202), fill=rgb(0x2B5FC8))   # badge
    draw_on(t, det)
    back_text(t, o, 202, 1)


def paint_overpants(o, t):
    """Surpantalon de feu : bande bicolore au-dessus des bottes, renforts aux genoux, poche cuisse, ceinture."""
    m = o['main']
    for r in faces(LEG):
        t.fill(r, m, noise=.03, twill=.025, grad=(1.0, .9))
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 232, x1, 256), m, noise=.03, twill=.025)
        t.fill((x0, 232, x1, 239), sh(m, .78), noise=.02)
    band(t, LEGS4, LEG, 202, 9)                                                         # juste au-dessus des bottes (212)

    def det(d):
        e = sh(m, .6)
        d.rectangle((34, 184, 62, 200), fill=sh(m, .84), outline=e)                     # renfort de genou (relief : SURPANT)
        for y in (188, 194):
            d.line([(36, y), (60, y)], fill=sh(m, .74))
        d.rectangle((4, 166, 28, 186), outline=e, fill=sh(m, .95)); d.rectangle((4, 164, 28, 170), fill=sh(m, .8))   # poche cuisse
        d.line([(192, 239), (192, 256)], fill=e)                                      # braguette sous rabat
        d.line([(196, 239), (196, 256)], fill=sh(m, .8))
        for x in (166, 182, 202, 218, 262, 288, 314):
            d.rectangle((x - 1, 231, x + 1, 240), fill=sh(m, .65))                     # passants
        d.rectangle((188, 233, 196, 238), fill=rgb(SILVER_D))                         # boucle
    draw_on(t, det)


def paint_caserne_pants(o, t):
    """Pantalon de caserne : cargo, liserés réfléchissants en bas de jambe."""
    paint_pants(o, t)
    for y in o.get('liserés', (226,)):
        band(t, LEGS4, LEG, y, 4, hivis=None)


def paint_boots(o, t):
    """Bottes de feu (hautes, bande réfléchissante) ou chaussures d'intervention (basses, lacets) : calque 1, bas des jambes."""
    m, low = o['main'], o.get('basses', False)
    top = 228 if low else 212
    for k in LEGS4:
        x0, y0, x1, y1 = LEG[k]
        t.fill((x0, top, x1, 256), m, noise=.03, grad=(1.12, .85), sheen=.15)
        t.fill((x0, top, x1, top + 4), sh(m, .55), noise=.02)                          # rebord
        t.fill((x0, 248, x1, 256), SOLE, noise=.05)                                    # semelle crantée
        t.ribs((x0, 250, x1, 256), .7, 3)
    t.fill((64, 128, 96, 160), SOLE, noise=.05)                                       # dessous du pied
    t.mul((32, 238, 64, 248), 1.18)                                                   # coque de protection
    if not low:
        band(t, LEGS4, LEG, top + 8, 6)

    def det(d):
        if low:
            for y in (232, 236, 240, 244):
                d.line([(40, y), (56, y + 2)], fill=rgb(0x3A3A40)); d.line([(56, y), (40, y + 2)], fill=rgb(0x3A3A40))   # lacets
        else:
            d.rectangle((44, top + 2, 52, top + 6), fill=rgb(0x2A2A2E))                # tirant
            d.line([(16, top + 4), (16, 248)], fill=sh(m, 1.4))                       # reflet du cuir
    draw_on(t, det)


# ---- formes 3D

def shape_veste_feu(slim):
    b = [ring(-1.3, 0.8, .62, 'main_hi'), ring(-1.3, -0.9, .66, 'dark'),               # col haut
         ring(11.0, 13.2, .42, 'main'), ring(11.45, 12.35, .47, 'accent'), ring(11.75, 12.05, .5, 'light'),   # bas de veste + bande
         ('body', -1.0, 0.8, -2.45, 1.0, 11.0, -2.3, 'dark'),                            # rabat tempête
         ('body', 1.5, 1.7, -3.05, 3.0, 4.6, -2.3, 'black'), ('body', 1.7, 2.3, -3.12, 2.8, 3.2, -3.05, 'metal_dark'),   # radio
         ('body', 2.45, -1.3, -2.85, 2.75, 1.7, -2.55, 'strap'), ('body', 2.1, 4.0, -3.12, 2.4, 4.3, -3.05, 'second')]   # antenne, voyant
    b += sym([('body', 1.6, -0.4, -1.1, 3.9, 0.0, 1.1, 'dark')])                        # pattes d'épaules
    for side in ('right', 'left'):
        x0, x1 = arm_x(side, slim)
        b.append((side + '_arm', x0 - 0.42, 8.6, -2.42, x1 + 0.42, 10.1, 2.42, 'dark'))    # serrage de poignet
    return b


def shape_parka(slim):
    b = [ring(-1.2, 1.0, .72, 'main_hi'), ('body', -3.3, -0.8, 2.45, 3.3, 2.3, 4.4, 'main'), ('body', -3.5, -1.0, 2.4, 3.5, -0.2, 4.6, 'dark'),
         ('body', -0.8, 0.8, -2.42, 0.8, 11.6, -2.3, 'main_hi')]
    b += sym([('right_leg', -2.5, -0.4, -2.5, 2.5, 3.4, 2.5, 'main'), ('right_leg', -2.56, 2.0, -2.56, 2.56, 2.8, 2.56, 'accent'),
              ('right_leg', -2.58, 2.25, -2.58, 2.58, 2.55, 2.58, 'light')])
    return b


def shape_polo(slim):
    return [('body', -3.0, -0.6, 1.5, 3.0, 0.4, 2.62, 'second')] + sym([('body', 0.25, -0.3, -2.62, 2.2, 1.3, -2.3, 'second'),
                                                                         ('body', 2.2, -0.6, -2.4, 3.0, 0.4, 1.5, 'second')])


def shape_hivis(slim):
    b = [ring(-0.9, 0.7, .55, 'main'), ring(11.2, 12.8, .4, 'main'), ring(11.65, 12.25, .45, 'light'),
         ('body', 1.6, 1.9, -2.95, 3.0, 4.4, -2.3, 'black'), ('body', 2.45, -0.9, -2.8, 2.7, 1.9, -2.55, 'strap')]
    b += sym([('body', 1.6, -0.35, -1.0, 3.9, 0.0, 1.0, 'main')])
    return b


def shape_surpantalon(slim):
    return sym([('right_leg', -1.7, 3.0, -2.62, 1.7, 5.0, -2.25, 'dark'), ('right_leg', -2.5, 0.6, -1.5, -2.2, 3.2, 1.5, 'main'),
                ('right_leg', -2.6, 0.4, -1.6, -2.2, 1.1, 1.6, 'dark')])


def shape_bottes(slim, low=False):
    top = 9.2 if low else 6.4
    return sym([('right_leg', -2.42, 11.6, -2.95, 2.42, 12.4, 2.42, 'black'), ('right_leg', -2.38, 9.9, -2.8, 2.38, 11.6, -2.3, 'main_hi'),
                ('right_leg', -2.46, top, -2.46, 2.46, top + 0.6, 2.46, 'dark')])


def shape_f1(slim):
    """Casque de pompier type F1 : calotte bombée, crête, jonc, visière dorée relevée, couvre-nuque, lampe sur le côté, jugulaire."""
    b = [('head', -4.7, -8.2, -4.7, 4.7, -4.7, 4.7, 'main'), ('head', -4.3, -9.0, -4.3, 4.3, -8.2, 4.3, 'main'),
         ('head', -3.4, -9.5, -3.4, 3.4, -9.0, 3.4, 'main_hi'), ('head', -2.0, -9.8, -2.0, 2.0, -9.5, 2.0, 'main_hi'),
         ('head', -0.45, -10.1, -2.4, 0.45, -9.5, 2.6, 'light'), ('head', -0.45, -9.7, -3.9, 0.45, -9.0, -2.4, 'light'),   # crête
         ('head', -0.45, -9.7, 2.6, 0.45, -9.0, 4.0, 'light'), ('head', -0.45, -9.0, -4.95, 0.45, -7.6, -4.3, 'light'),
         ('head', -0.45, -9.0, 4.3, 0.45, -6.8, 4.95, 'light'),
         ('head', -4.78, -6.6, -4.78, 4.78, -6.0, 4.78, 'accent'),                       # bande rétroréfléchissante
         ('head', -4.88, -4.95, -4.88, 4.88, -4.5, 4.88, 'dark'),                        # jonc
         ('head', -4.7, -4.6, 0.9, 4.7, -2.6, 4.7, 'main'),                              # nuque
         ('head', -4.6, -2.6, 2.2, 4.6, 0.6, 4.95, 'second'), ('head', -4.65, 0.2, 2.1, 4.65, 0.6, 5.0, 'dark'),   # couvre-nuque
         ('head', -3.9, -5.15, -5.18, 3.9, -4.4, -4.88, 'lens'), ('head', -2.8, -5.05, -5.22, -0.9, -4.85, -5.18, 'lens_hi'),   # visière relevée
         ('head', 4.7, -7.2, -1.8, 5.3, -5.4, 0.4, 'black'), ('head', 4.8, -7.0, -3.0, 5.7, -5.6, -1.8, 'strap'),   # support + lampe
         ('head', 4.85, -6.8, -3.08, 5.65, -5.8, -3.0, 'white')]
    b += sym([('head', -4.72, -4.5, -0.6, -4.52, -0.2, 0.4, 'strap')])                    # jugulaire
    b.append(('head', -4.72, -0.2, -2.6, 4.72, 0.15, -1.8, 'strap'))
    return b


SHAPES.update({'VESTE_FEU': shape_veste_feu, 'PARKA': shape_parka, 'POLO2': shape_polo, 'HIVIS': shape_hivis, 'SURPANT': shape_surpantalon,
               'BOTTES': shape_bottes, 'CHAUSSURES': lambda s: shape_bottes(s, True), 'F1': shape_f1})


# ---- icônes 16 x 16

SIL = {
    'veste': ["................", "...XXXXXXXXXX...", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.",
              ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.",
              ".XXX.XXXXXX.XXX.", "....XXXXXXXX....", "................", "................"],
    'polo': ["................", "....XX....XX....", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", "..XXXXXXXXXXXX..",
             "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
             "...XXXXXXXXXX...", "................", "................", "................"],
    'pants': ["................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXX.XXXX...", "...XXXX..XXXX...",
              "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...",
              "...XXXX..XXXX...", "...XXXX..XXXX...", "................", "................"],
    'bottes': ["................", "................", "...XXXX.........", "...XXXX.........", "...XXXX.........", "...XXXX.........",
               "...XXXX.........", "...XXXX.........", "...XXXXX........", "...XXXXXX.......", "...XXXXXXXX.....", "..XXXXXXXXXX....",
               "..XXXXXXXXXXX...", "..XXXXXXXXXXX...", "................", "................"],
    'chaussures': ["................", "................", "................", "................", "................", "................",
                   "...XXXX.........", "...XXXXX........", "...XXXXXX.......", "..XXXXXXXXX.....", "..XXXXXXXXXXX...", "..XXXXXXXXXXX...",
                   "..XXXXXXXXXXX...", "................", "................", "................"],
}


def icon_secours(o):
    sil, m = SIL[o['sil']], o['main']
    bands = o.get('icon_bandes', ())
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(sil):
        for x, ch in enumerate(row):
            if ch != 'X':
                continue
            c = sh(m, 1.0 + (0.12 if x < 8 else -0.05) - y * 0.012)
            if o['sil'] in ('veste', 'polo') and o.get('icon_haut') is not None and y < o.get('icon_coupe', 8):
                c = sh(o['icon_haut'], 1.05 if x < 8 else .95)
            if y in bands:
                c = rgb(o.get('icon_bande', HIVIS))
            if o['sil'] == 'veste' and x in (7, 8) and 2 <= y <= 12:
                c = sh(m, .6) if o.get('icon_haut') is None else rgb(0x2A2A2E)
            if o['sil'] == 'polo' and o.get('second') is not None and (y <= 2 or (x in (7, 8) and y <= 4)):
                c = rgb(o['second'])
            if o.get('icon_galon') is not None and y == 2 and x in (3, 4, 11, 12):
                c = rgb(o['icon_galon'])
            if o['sil'] in ('bottes', 'chaussures') and y >= 12:
                c = rgb(0x2E2E32)
            im.putpixel((x, y), c + (255,))
    out = im.copy()
    for y in range(16):
        for x in range(16):
            if im.getpixel((x, y))[3] == 0 and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and im.getpixel((x + dx, y + dy))[3]
                                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), (16, 16, 16, 255))
    return out


def S(id, fr, piece, shape, paint, sil, **p):
    return C(id, fr, fr, 'secours', shape, piece=piece, paint=paint, sil=sil, icon=icon_secours, **p)


SECOURS = [
    # pompiers : tenue de feu
    S('veste_feu_marine', 'Veste de feu bleu marine', 'chestplate', 'VESTE_FEU', paint_feu, 'veste', main=NAVY_SP, accent=HIVIS, light=REFL,
      second=0x2EC46A, dos='POMPIERS', icon_bandes=(6, 11)),
    S('veste_feu_sable', 'Veste de feu sable', 'chestplate', 'VESTE_FEU', paint_feu, 'veste', main=SABLE, accent=HIVIS, light=REFL,
      second=0x2EC46A, dos='POMPIERS', dos_fond=0x2A2620, icon_bandes=(6, 11)),
    S('surpantalon_feu_marine', 'Surpantalon de feu bleu marine', 'leggings', 'SURPANT', paint_overpants, 'pants', main=NAVY_SP, icon_bandes=(10,)),
    S('surpantalon_feu_sable', 'Surpantalon de feu sable', 'leggings', 'SURPANT', paint_overpants, 'pants', main=SABLE, icon_bandes=(10,)),
    S('bottes_feu', 'Bottes de feu', 'boots', 'BOTTES', paint_boots, 'bottes', main=0x1C1C20, icon_bandes=(5,)),
    S('parka_pompier', 'Parka pompier', 'chestplate', 'PARKA', paint_parka, 'veste', main=NAVY_SP, accent=HIVIS, light=REFL, second=0xC62828,
      dos='POMPIERS', icon_bandes=(6, 10)),
    # pompiers : tenue de caserne
    S('polo_pompier', 'Polo de caserne pompier', 'chestplate', 'POLO2', paint_polo, 'polo', main=NAVY_SP, second=0xC62828, dos='POMPIERS',
      dos_col=WHITE, emblème='flamme'),
    S('tshirt_pompier', 'T-shirt de caserne pompier', 'chestplate', None, paint_polo, 'polo', main=NAVY_SP, tee=True, dos='POMPIERS',
      dos_col=WHITE, emblème='flamme'),
    S('pantalon_pompier', 'Pantalon de caserne pompier', 'leggings', 'CARGO', paint_caserne_pants, 'pants', main=NAVY_SP, pants='cargo',
      icon_bandes=(11,), icon_bande=REFL),
    # SAMU / ambulanciers
    S('veste_samu', 'Veste SAMU haute visibilité', 'chestplate', 'HIVIS', paint_hivis, 'veste', main=NAVY_SAMU, accent=HIVIS, light=REFL,
      dos='SAMU', dos_col=NAVY_SAMU, icon_haut=HIVIS, icon_coupe=7, icon_bandes=(7, 11), icon_bande=REFL),
    S('veste_ambulancier', 'Veste ambulancier', 'chestplate', 'HIVIS', paint_ambu, 'veste', main=NAVY_SAMU, accent=HIVIS, light=REFL,
      dos='AMBULANCE', dos_sy=2, icon_haut=HIVIS, icon_coupe=4, icon_bandes=(4, 12), icon_bande=REFL),
    S('polo_samu', 'Polo SAMU', 'chestplate', 'POLO2', paint_polo, 'polo', main=0xF2F2EE, second=NAVY_SAMU, yoke=NAVY_SAMU,
      liseré=0xC62828, dos='SAMU', dos_scale=3, dos_col=NAVY_SAMU, dos_y=184, emblème='texte'),
    S('pantalon_samu', 'Pantalon de secours SAMU', 'leggings', 'CARGO', paint_caserne_pants, 'pants', main=NAVY_SAMU, pants='cargo',
      liserés=(220, 230), icon_bandes=(10, 12), icon_bande=REFL),
    S('chaussures_intervention', "Chaussures d'intervention", 'boots', 'CHAUSSURES', paint_boots, 'chaussures', main=0x1C1C20, basses=True),
]
CLOTHES += SECOURS
HATS += [
    C('casque_f1', 'Casque F1 chromé', 'F1 firefighter helmet (chrome)', 'hat', 'F1', main=0xC9CFD6, main_hi=0xE6EAEE, light=0xA8AEB6,
      dark=0x1A1A1D, accent=HIVIS, second=0xA9AEB4, lens=0xC9A23A, lens_hi=0xF2DE9A, strap=0x1A1A1D, black=0x141416, white=0xFFF6D0),
    C('casque_f1_blanc', 'Casque F1 blanc', 'F1 firefighter helmet (white)', 'hat', 'F1', main=0xEEEEEA, main_hi=0xFAFAF7, light=0xD2D2CC,
      dark=0x1A1A1D, accent=HIVIS, second=0x2A2A2E, lens=0xC9A23A, lens_hi=0xF2DE9A, strap=0x1A1A1D, black=0x141416, white=0xFFF6D0),
    C('casquette_pompier', 'Casquette pompier', 'Firefighter cap', 'hat', 'CAP', main=NAVY_SP, light=0xC62828, accent=0xF2B21E),
    C('casquette_samu', 'Casquette SAMU', 'SAMU cap', 'hat', 'CAP', main=NAVY_SAMU, light=WHITE, accent=0x2B5FC8),
]
ACCS += [
    C('gants_pompier', "Gants d'intervention", "Gants d'intervention", 'MAINS', 'GLOVES', main=0x232326, dark=0x3A3A3E, light=HIVIS),
]

# ---------------------------------------------------------------- tenues de Police Nationale (03/11)
# Grades du mod minenorth-police : Sous-officier, Officier, Commissaire. Le grade se lit sur la patte de poitrine et les épaulettes (galons en relief) :
# sous-officier 1 galon argent, officier 2 galons argent, commissaire 3 galons or. Le brassard orange POLICE (BAC, en civil) est dans ZeroContact.
# Créations originales : aucun insigne officiel, seulement le mot POLICE.

NAVY_PN, RAID_NOIR = 0x1A1F3C, 0x1C1C1F
GRADES_PN = [('sous_officier', 'Sous-officier', 1, SILVER), ('officier', 'Officier', 2, SILVER), ('commissaire', 'Commissaire', 3, GOLD)]


def epaulettes(n, base=None):
    """Pattes d'épaules + n galons (pastille metal) ; base : forme à compléter (col, capuche...)."""
    b = list(base or [])
    b += sym([('body', 1.6, -0.36, -1.0, 3.9, 0.0, 1.0, 'dark'), ('body', 3.55, -0.42, -0.35, 3.9, -0.33, 0.35, 'metal_dark')])   # patte + bouton
    for k in range(n):
        x = 2.0 + k * 0.48
        b += sym([('body', x, -0.44, -1.04, x + 0.28, -0.34, 1.04, 'metal')])
    b.append(('body', -0.75, 1.5, -2.45, 0.75, 3.9, -2.3, 'dark'))                     # patte de poitrine (grade visible de face)
    for k in range(n):
        y = 2.0 + k * 0.55
        b.append(('body', -0.6, y, -2.52, 0.6, y + 0.28, -2.45, 'metal'))
    return b


def paint_blouson_police(o, t):
    """Blouson d'intervention : softshell bleu nuit, épaules renforcées, fermeture, POLICE poitrine et dos, liserés réfléchissants aux manches."""
    m = o['main']
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, noise=.02, grad=(1.04, .86), sheen=.09)
    t.fill(BODY['top'], sh(m, .85)); t.fill(ARM['top'], sh(m, .85)); t.fill(ARM['bot'], sh(m, .6))
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 160, x1, 176), sh(m, .82), noise=.02, sheen=.06)               # empiècement d'épaules
        t.fill((x0, 248, x1, 256), sh(m, .7)); t.ribs((x0, 248, x1, 256), .84)      # bas élastiqué
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 160, x1, 180), sh(m, .82), noise=.02)
        t.fill((x0, 248, x1, 256), sh(m, .6)); t.ribs((x0, 248, x1, 256), .8)
    band(t, SLEEVES, ARM, 232, 4, hivis=None)
    t.rect((191, 160, 193, 248), sh(m, .5)); t.rect((190, 182, 194, 190), SILVER)   # fermeture éclair et tirette

    def det(d):
        e = sh(m, .55)
        for (x0, x1) in ((128, 160), (160, 224), (224, 256), (256, 320)):
            d.line([(x0, 176), (x1, 176)], fill=e)
        d.line([(166, 214), (176, 232)], fill=e, width=2); d.line([(218, 214), (208, 232)], fill=e, width=2)   # poches zippées
        d.rounded_rectangle((165, 190, 183, 197), radius=3, fill=rgb(0x26262A))                             # bande nominative
        d.line([(167, 193), (181, 193)], fill=rgb(REFL))
    draw_on(t, det)
    back_text(t, o, 196, 2)



def detoure(lg):
    """Logo PN sans son fond blanc : blanc -> transparent, lettrage noir -> blanc brodé (lisible sur le bleu nuit), bleu éclairci, rouge gardé."""
    import colorsys
    out = Image.new('RGBA', lg.size)
    for y in range(lg.height):
        for x in range(lg.width):
            r, g, b, a = lg.getpixel((x, y))
            hh, ll, ss = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
            if ss > .35 and .15 < ll < .9:                         # bleu / rouge du ruban tricolore
                if .5 < hh < .75:
                    r, g, b = [int(v * 255) for v in colorsys.hls_to_rgb(hh, max(ll, .55), ss)]
                out.putpixel((x, y), (r, g, b, a))
            else:                                                   # gris / noir = lettrage, blanc = fond
                k = 1 - ll
                if k > .12:
                    out.putpixel((x, y), (240, 240, 236, int(a * min(1, k * 1.6))))
    return out

def logo_pn(t, x, y, w):
    """Logo POLICE NATIONALE détouré (repris de la texture du gilet PN de ZeroContact, tools/logo_pn.png), w pixels de large."""
    lg = detoure(Image.open('tools/logo_pn.png').convert('RGBA'))
    lg = lg.resize((w, round(lg.height * w / lg.width)), Image.LANCZOS)
    lg.putalpha(lg.getchannel('A').point(lambda a: 255 if a > 60 else 0))       # bords francs (broderie), pas de voile gris
    im = t.img()
    im.alpha_composite(lg, (x, y))
    t.a = np.array(im, np.float32)


def paint_pn(paint):
    """Tenue police : la peinture de base, plus l'écusson PN sur la poitrine (côté cœur) et sur les deux manches."""
    def f(o, t):
        paint(o, t)
        logo_pn(t, 197, 177 if o['sil'] == 'polo' else 181, 26)
        logo_pn(t, 322, 166, 28)
    return f


def P(id, fr, piece, shape, paint, sil, **p):
    return S(id, fr, piece, shape, paint, sil, main=NAVY_PN, **p)


POLICE = []
for g, gfr, n, col in GRADES_PN:
    POLICE += [
        P('polo_police_' + g, 'Polo Police - ' + gfr, 'chestplate', 'POLO_PN_' + g.upper(), paint_pn(paint_polo), 'polo', second=sh(NAVY_PN, .75),
          dos='POLICE', dos_col=WHITE, metal=col, metal_dark=sh(col, .6), dark=sh(NAVY_PN, .8),
          icon_galon=col),
        P('blouson_police_' + g, "Blouson d'intervention Police - " + gfr, 'chestplate', 'BLOUSON_PN_' + g.upper(), paint_pn(paint_blouson_police), 'veste',
          dos='POLICE', dos_col=WHITE, metal=col, metal_dark=sh(col, .6), dark=sh(NAVY_PN, .78), main_hi=sh(NAVY_PN, 1.15),
          icon_galon=col, icon_bandes=(10,), icon_bande=REFL),
    ]
    SHAPES['POLO_PN_' + g.upper()] = (lambda n: lambda slim: epaulettes(n, shape_polo(slim)))(n)
    SHAPES['BLOUSON_PN_' + g.upper()] = (lambda n: lambda slim: epaulettes(n, [ring(-0.9, 0.6, .5, 'main_hi')]))(n)
POLICE += [
    P('parka_police', 'Parka Police', 'chestplate', 'PARKA', paint_pn(paint_parka), 'veste', accent=REFL, light=REFL, second=0x2B5FC8, hivis=None,
      dos='POLICE', icon_bandes=(6, 10), icon_bande=REFL),
    P('pantalon_police', 'Pantalon Police', 'leggings', 'CARGO', paint_caserne_pants, 'pants', pants='cargo', liserés=()),
    # RAID (unité d'intervention) : tenue noire, logo PN, RAID dans le dos ; casque et gilet RAID dans ZeroContact
    S('blouson_raid', "Blouson d'intervention RAID", 'chestplate', 'BLOUSON_RAID', paint_pn(paint_blouson_police), 'veste', main=RAID_NOIR,
      dos='RAID', dos_scale=3, dos_col=WHITE, dark=sh(RAID_NOIR, .7), main_hi=sh(RAID_NOIR, 1.25), metal=SILVER_D, metal_dark=SILVER_D,
      icon_bandes=(10,), icon_bande=REFL),
    S('pantalon_raid', 'Pantalon RAID', 'leggings', 'CARGO', paint_caserne_pants, 'pants', main=RAID_NOIR, pants='cargo', liserés=()),
]
SHAPES['BLOUSON_RAID'] = lambda slim: [ring(-0.9, 0.6, .5, 'main_hi')] + sym([('body', 1.6, -0.36, -1.0, 3.9, 0.0, 1.0, 'dark')])
CLOTHES += POLICE
HATS += [
    C('casquette_police', 'Casquette Police', 'Casquette Police', 'hat', 'CAP', main=NAVY_PN, light=WHITE, accent=0x2B5FC8),
]

PUFFY = [o['id'] for o in CLOTHES if o['kind'] == 'puffer']


# ---------------------------------------------------------------- écriture

def armor_png(o, l1, l2):
    pal = palette(o)
    for lay, t in ((1, l1), (2, l2)):
        im = t.img() if t else Image.new('RGBA', (512, 256), (0, 0, 0, 0))
        for k, col in enumerate(pal):
            cx, cy = 256 + 32 * (k % 8), 32 * (k // 8)
            im.paste(col + (255,), (cx, cy, cx + 32, cy + 32))
        im.save(ARMOR + '%s_layer_%d.png' % (o['id'], lay))


def cells_texture(o, name):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for k, col in enumerate(palette(o)):
        im.paste(col + (255,), ((k % 4) * 4, (k // 4) * 4, (k % 4) * 4 + 4, (k // 4) * 4 + 4))
    im.save(R + 'textures/item/%s.png' % name)


PIVOT = {'head': (0, 0, 0), 'body': (0, 0, 0), 'right_arm': (-5, 2, 0), 'left_arm': (5, 2, 0), 'right_leg': (-1.9, 12, 0), 'left_leg': (1.9, 12, 0)}


def item_boxes(shape, boxes):
    """Cubes montrés dans l'inventaire : sans les parties cachées dans le dos (chaînes, bandoulières), gants côte à côte."""
    if shape in ('CUBAN', 'CROSS', 'PEARLS', 'FANNY', 'SACOCHE'):
        boxes = [b for b in boxes if b[6] <= 0.5]
    elif shape in ('DUFFEL', 'HIKING'):          # le sac seul, sans la bandoulière / les bretelles du devant
        boxes = [b for b in boxes if b[3] >= 2.2]
    piv = dict(PIVOT)
    if shape == 'GLOVES':
        piv.update(right_arm=(-2.2, 0, 0), left_arm=(2.2, 0, 0))
    return boxes, piv


def item_model_3d(o, name, boxes, tex):
    """Modèle d'objet 3D : les cubes portés, recentrés et mis à l'échelle dans le cube 16 x 16 x 16."""
    boxes, piv = item_boxes(o['shape'], boxes)
    pts = []
    for (p, x0, y0, z0, x1, y1, z1, s) in boxes:
        px, py, pz = piv[p]
        pts.append((x0 + px, y0 + py, z0 + pz, x1 + px, y1 + py, z1 + pz, s))
    mn = [min(b[i] for b in pts) for i in range(3)]
    mx = [max(b[i + 3] for b in pts) for i in range(3)]
    ext = max(mx[i] - mn[i] for i in range(3))
    k = 14.0 / ext
    c = [(mn[i] + mx[i]) / 2 for i in range(3)]
    E = []
    for (x0, y0, z0, x1, y1, z1, s) in pts:
        i = SW.index(s)
        u, v = (i % 4) * 4, (i // 4) * 4
        f = [round(8 - (x1 - c[0]) * k, 3), round(8 - (y1 - c[1]) * k, 3), round(8 + (z0 - c[2]) * k, 3)]
        t = [round(8 - (x0 - c[0]) * k, 3), round(8 - (y0 - c[1]) * k, 3), round(8 + (z1 - c[2]) * k, 3)]
        for a in range(3):
            if t[a] - f[a] < .05:
                t[a] = round(f[a] + .05, 3)
        E.append({'from': f, 'to': t, 'faces': {d: {'uv': [u + .5, v + .5, u + 3.5, v + 3.5], 'texture': '#0'} for d in ('north', 'south', 'east', 'west', 'up', 'down')}})
    json.dump({'textures': {'0': 'minenorth_vetements:item/' + tex, 'particle': 'minenorth_vetements:item/' + tex}, 'elements': E,
               'display': {'gui': {'rotation': [25, 200, 0], 'scale': [0.95, 0.95, 0.95]},
                           'ground': {'translation': [0, 2, 0], 'scale': [0.5, 0.5, 0.5]},
                           'fixed': {'rotation': [0, 180, 0], 'scale': [0.9, 0.9, 0.9]},
                           'thirdperson_righthand': {'rotation': [0, 180, 0], 'translation': [0, 2.5, 2], 'scale': [0.5, 0.5, 0.5]},
                           'firstperson_righthand': {'rotation': [0, 160, 0], 'translation': [1, 3, 0], 'scale': [0.55, 0.55, 0.55]}}},
              open(R + 'models/item/%s.json' % name, 'w'), indent=1)


def icon(o):
    """Icône 2D 16 x 16 des vêtements."""
    sil = {
        'puffer': ["................", "....XXXXXXXX....", "..XXXXXXXXXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", "XXXXXXXXXXXXXXXX",
                   "XXXXXXXXXXXXXXXX", "XXXXXXXXXXXXXXXX", "XXXXXXXXXXXXXXXX", "XXXX.XXXXXX.XXXX", "XXXX.XXXXXX.XXXX", "XXXX.XXXXXX.XXXX",
                   "XXX..XXXXXX..XXX", ".....XXXXXX.....", "................", "................"],
        'gilet': ["................", ".....XX..XX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
                  "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
                  "...XXXXXXXXXX...", "................", "................", "................"],
        'hoodie': ["......XXXX......", ".....XXXXXX.....", "...XXXX..XXXX...", ".XXXXXX..XXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.",
                   ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.",
                   ".XXX.XXXXXX.XXX.", "................", "................", "................"],
        'jacket': ["................", "...XXXXXXXXXX...", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.",
                   ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.",
                   ".XXX.XXXXXX.XXX.", "................", "................", "................"],
        'coat': ["....XXX..XXX....", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXX.XXXXXX.XXX.",
                 ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", "....XXXXXXXX....",
                 "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "................"],
        'pants': ["................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXX.XXXX...", "...XXXX..XXXX...",
                  "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...",
                  "...XXXX..XXXX...", "...XXXX..XXXX...", "................", "................"],
    }
    k = o['kind']
    key = 'gilet' if o.get('gilet') else 'jacket' if k in ('bomber', 'perfecto') else k
    sh_ = sil[key]
    m = o['main']
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(sh_):
        for x, ch in enumerate(row):
            if ch != 'X':
                continue
            c = sh(m, 1.0 + (0.12 if x < 8 else -0.05) - y * 0.012)
            if k == 'puffer' and y % 3 == 0:
                c = sh(m, .7)
            if k == 'hoodie' and (y >= 12 or (y <= 2 and 6 <= x <= 9)):
                c = sh(m, .78)
            if k in ('bomber', 'puffer', 'perfecto') and x in (7, 8) and 1 <= y <= 12 and not o.get('gilet'):
                c = rgb(SILVER) if k != 'bomber' else rgb(0xE8641E)
            if k == 'coat' and x in (6, 9) and y in (6, 9):
                c = sh(m, .5)
            if k == 'coat' and o.get('trench') and y == 9:
                c = sh(m, .78)
            if k == 'pants':
                if y == 1:
                    c = sh(m, .75)
                if o['pants'] == 'jogging' and y == 13:
                    c = sh(m, .75)
                if o['pants'] == 'cargo' and x in (3, 12) and 6 <= y <= 8:
                    c = sh(m, .78)
                if o['pants'] == 'jean' and (x in (3, 12)):
                    c = rgb(o['stitch'])
            im.putpixel((x, y), c + (255,))
    out = im.copy()
    for y in range(16):
        for x in range(16):
            if im.getpixel((x, y))[3] == 0 and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and im.getpixel((x + dx, y + dy))[3]
                                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), (16, 16, 16, 255))
    return out


def jfloat(v):
    s = ('%.3f' % v).rstrip('0').rstrip('.')
    return (s if s not in ('-0', '') else '0') + 'f'


def main():
    lang_fr, lang_en, formes = {}, {}, {}
    seed = 11
    piece = {'puffer': 'chestplate', 'hoodie': 'chestplate', 'bomber': 'chestplate', 'perfecto': 'chestplate', 'coat': 'chestplate', 'pants': 'leggings'}
    paint = {'puffer': paint_puffer, 'hoodie': paint_hoodie, 'bomber': paint_bomber, 'perfecto': paint_perfecto, 'coat': paint_coat}
    outfit_lines = []
    for o in CLOTHES:
        seed += 1
        pc = o.get('piece') or piece[o['kind']]          # tenues de secours : pièce, peinture et icône propres (voir SECOURS)
        if pc == 'leggings':
            l2 = Tex(seed); (o.get('paint') or paint_pants)(o, l2); armor_png(o, None, l2)
        else:                                             # hauts (torse + bras) et chaussures (jambes du calque 1)
            l1 = Tex(seed); (o.get('paint') or paint.get(o['kind']))(o, l1); armor_png(o, l1, None)
        n = o['id'] + '_' + pc
        (o.get('icon') or icon)(o).save(R + 'textures/item/%s.png' % n)
        json.dump({'parent': 'item/generated', 'textures': {'layer0': 'minenorth_vetements:item/' + n}}, open(R + 'models/item/%s.json' % n, 'w'), indent=1)
        lang_fr['item.minenorth_vetements.' + n] = o['fr']
        lang_en['item.minenorth_vetements.' + n] = o['fr']   # noms FR aussi pour un client en anglais
        outfit_lines.append((o['id'], o['fr'], False, pc == 'chestplate', pc == 'leggings', pc == 'boots'))
    for o in HATS:
        armor_png(o, None, None)
        n = o['id'] + '_helmet'
        cells_texture(o, o['id'] + '_acc')
        item_model_3d(o, n, SHAPES[o['shape']](False), o['id'] + '_acc')
        lang_fr['item.minenorth_vetements.' + n] = o['fr']
        lang_en['item.minenorth_vetements.' + n] = o['fr']   # noms FR aussi pour un client en anglais
        outfit_lines.append((o['id'], o['fr'], True, False, False, False))
    for o in ACCS:
        armor_png(o, None, None)
        cells_texture(o, o['id'] + '_acc')
        item_model_3d(o, o['id'], SHAPES[o['shape']](False), o['id'] + '_acc')
        lang_fr['item.minenorth_vetements.' + o['id']] = o['fr']
        lang_en['item.minenorth_vetements.' + o['id']] = o['fr']

    # ---- Formes.java
    shape_of = {o['id']: o['shape'] for o in CLOTHES + HATS + ACCS if o['shape']}
    used = sorted(set(shape_of.values()))
    L = ['package com.minenorth_vetements.client;', '', 'import java.util.HashMap;', 'import java.util.Map;', 'import java.util.Set;', '',
         '/** Généré par tools/gen_streetwear.py - ne pas éditer. Cubes portés : {partie, x0, y0, z0, x1, y1, z1, pastille} ; parties : '
         + ', '.join('%d %s' % (i, p) for i, p in enumerate(PARTS)) + '. */',
         'final class Formes {', '    private Formes() {}', '',
         '    /** id de tenue / accessoire -> forme. */', '    static final Map<String, String> SHAPE_OF = new HashMap<>();',
         '    /** forme (ou forme + "/slim" pour les bras fins) -> cubes. */', '    static final Map<String, float[][]> SHAPES = new HashMap<>();',
         '    /** Hauts gonflés (doudounes) : modèle d\'armure plus épais. */',
         '    static final Set<String> PUFFY = Set.of(' + ', '.join('"%s"' % i for i in PUFFY) + ');', '', '    static {']
    for i, s in sorted(shape_of.items()):
        L.append('        SHAPE_OF.put("%s", "%s");' % (i, s))
    for s in used:
        for slim in (False, True):
            boxes = SHAPES[s](slim)
            if slim and boxes == SHAPES[s](False):
                continue
            key = s + ('/slim' if slim else '')
            formes[key] = boxes
            rows = ['{%d, %s, %d}' % (PARTS.index(b[0]), ', '.join(jfloat(v) for v in b[1:7]), SW.index(b[7])) for b in boxes]
            L.append('        SHAPES.put("%s", new float[][]{' % key)
            for r in rows:
                L.append('            ' + r + ',')
            L.append('        });')
    L += ['    }', '}', '']
    open(J + 'client/Formes.java', 'w', encoding='utf-8').write('\n'.join(L))
    json.dump({'formes': formes, 'shape_of': shape_of, 'puffy': PUFFY, 'sw': SW}, open('tools/formes.json', 'w'), indent=0)

    # ---- AccessoryData.java
    A = ['package com.minenorth_vetements;', '', 'import java.util.HashMap;', 'import java.util.Map;', '',
         '/** Généré par tools/gen_streetwear.py - ne pas éditer. Accessoires portés en plus des vêtements, par emplacement. */',
         'final class AccessoryData {', '    private AccessoryData() {}', '',
         '    /** legacy : ancien objet enregistré par OutfitData sous le nom id + "_helmet". */',
         '    record Acc(String id, AccSlot slot, boolean legacy) {}', '',
         '    static final Map<String, Acc> BY_ID = new HashMap<>();', '',
         '    static {']
    for (i, s) in LEGACY:
        A.append('        put("%s", AccSlot.%s, true);' % (i, s))
    for o in ACCS:
        A.append('        put("%s", AccSlot.%s, false);' % (o['id'], o['kind']))
    A += ['    }', '', '    private static void put(String id, AccSlot slot, boolean legacy) { BY_ID.put(id, new Acc(id, slot, legacy)); }',
          '', '    /** Nouveaux accessoires (enregistrés sous leur id), dans l\'ordre du catalogue. */',
          '    static final String[] NEW = {' + ', '.join('"%s"' % o['id'] for o in ACCS) + '};', '}', '']
    open(J + 'AccessoryData.java', 'w', encoding='utf-8').write('\n'.join(A))

    # ---- OutfitData.java
    src = open(J + 'OutfitData.java', encoding='utf-8').read()
    for (i, fr, cap, chest, legs, boots) in outfit_lines:
        if '"%s"' % i in src:
            continue
        line = '        new Outfit("%s", "%s", %s, %s, %s, %s),\n' % (i, fr.replace('"', '\\"'), *(str(v).lower() for v in (cap, chest, legs, boots)))
        src = src.replace('    };\n', line + '    };\n', 1)
    open(J + 'OutfitData.java', 'w', encoding='utf-8').write(src)

    # ---- langues
    for lg, extra in (('fr_fr', lang_fr), ('en_us', lang_en)):
        p = R + 'lang/%s.json' % lg
        d = json.load(open(p, encoding='utf-8-sig'))
        d.update(extra)
        json.dump(d, open(p, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('ok : %d vêtements, %d chapeaux, %d accessoires, %d formes' % (len(CLOTHES), len(HATS), len(ACCS), len(formes)))


if __name__ == '__main__':
    main()
