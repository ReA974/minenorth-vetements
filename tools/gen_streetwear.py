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
    if 'shoe' in p:                                       # chaussures : pastilles 16 à 31
        d.update(shoe_palette(p['shoe']))
    return [rgb(d[k]) for k in (SW if 'shoe' in p else SW[:16])]


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


def cap_boxes(inverse=False):
    """Casquette à 6 pans, d'après la « boss cap » de ZeroContact : calotte bombée à plateau, panneau avant structuré, coutures et œillets,
    visière incurvée (bords plus bas que le milieu) et inclinée vers le bas, bouton, ouverture et sangle à pression derrière.
    inverse : portée à l'envers (visière dans la nuque, panneau avant derrière) ; l'écusson reste devant, comme avant."""
    b = [('head', -4.62, -8.3, -4.62, 4.62, -5.45, 4.62, 'main'),                        # calotte
         ('head', -4.3, -8.75, -4.3, 4.3, -8.3, 4.3, 'main'),                            # arrondi
         ('head', -3.4, -9.05, -3.4, 3.4, -8.75, 3.4, 'main'),                           # plateau
         ('head', -0.45, -9.35, -0.45, 0.45, -9.05, 0.45, 'dark'),                       # bouton
         ('head', -4.68, -5.75, -4.68, 4.68, -5.3, 4.68, 'dark'),                        # bandeau
         ('head', -2.6, -8.1, -4.92, 2.6, -5.35, -4.62, 'main'),                         # panneau avant structuré
         ('head', -3.5, -7.7, -4.8, 3.5, -5.35, -4.62, 'main'),
         ('head', -1.9, -8.45, -4.48, 1.9, -8.3, -4.3, 'main')]
    for z in (-1.55, 1.55):                                                           # coutures des pans (côtés)
        b += [('head', -4.66, -8.3, z - .07, -4.62, -5.75, z + .07, 'dark'), ('head', 4.62, -8.3, z - .07, 4.66, -5.75, z + .07, 'dark')]
    for x in (-1.55, 1.55):                                                           # coutures du dessus
        b.append(('head', x - .07, -8.79, -4.3, x + .07, -8.75, 4.3, 'dark'))
    for (x, z) in ((-4.68, -2.8), (4.62, -2.8), (-4.68, 2.8), (4.62, 2.8)):           # œillets d'aération
        b.append(('head', x, -7.7, z - .2, x + .06, -7.3, z + .2, 'dark'))
    # visière : milieu, côtés plus bas (courbure), bouts plus bas encore (inclinaison)
    b += [('head', -1.7, -5.55, -6.4, 1.7, -5.1, -4.7, 'main'), ('head', -1.6, -5.3, -8.1, 1.6, -4.85, -6.4, 'main'),
          ('head', -3.2, -5.45, -6.4, -1.7, -5.0, -4.7, 'main'), ('head', 1.7, -5.45, -6.4, 3.2, -5.0, -4.7, 'main'),
          ('head', -3.0, -5.2, -7.7, -1.6, -4.75, -6.4, 'main'), ('head', 1.6, -5.2, -7.7, 3.0, -4.75, -6.4, 'main'),
          ('head', -4.25, -5.3, -6.5, -3.2, -4.85, -4.7, 'main'), ('head', 3.2, -5.3, -6.5, 4.25, -4.85, -4.7, 'main'),
          ('head', -3.8, -5.05, -7.1, -3.0, -4.65, -6.5, 'main'), ('head', 3.0, -5.05, -7.1, 3.8, -4.65, -6.5, 'main'),
          ('head', -1.5, -4.85, -7.9, 1.5, -4.78, -4.75, 'dark'),                        # dessous de visière
          ('head', -1.5, -5.37, -8.0, 1.5, -5.3, -6.45, 'dark')]                         # piqûres du dessus
    if not inverse:                                                                   # ouverture et sangle à pression (arrière)
        b += [('head', -1.7, -6.5, 4.62, 1.7, -5.75, 4.7, 'black'), ('head', -1.9, -5.75, 4.6, 1.9, -5.3, 4.85, 'strap'),
              ('head', -0.35, -5.85, 4.85, 0.35, -5.25, 4.95, 'metal')]
    else:
        b = [(p, x0, y0, -z1, x1, y1, -z0, sw) for (p, x0, y0, z0, x1, y1, z1, sw) in b]
    lz = -4.62 if inverse else -4.92                                                  # écusson brodé (devant)
    b += [('head', -1.3, -7.6, lz - .06, 1.3, -6.0, lz, 'light'), ('head', -0.6, -7.15, lz - .1, 0.6, -6.45, lz - .06, 'accent')]
    return b


def shape_cap(slim):
    return cap_boxes()


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


SHAPES = {'CAP': shape_cap, 'CAP_INV': lambda s: cap_boxes(True), 'BEANIE': shape_beanie, 'BUCKET': shape_bucket, 'ROUND': shape_round, 'SHIELD': shape_shield,
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
    # à l'envers (anciennement dans gen_acc.py) : même casquette, visière dans la nuque ; écusson clair à logo coloré
    C('casquette_inverse_noire', "Casquette à l'envers noire", "Casquette à l'envers noire", 'hat', 'CAP_INV', main=0x141416, light=0xEDEDE6, accent=0xC8202A),
    C('casquette_inverse_rouge', "Casquette à l'envers rouge", "Casquette à l'envers rouge", 'hat', 'CAP_INV', main=0xB3202A, light=0xEDEDE6, accent=0x141416),
    C('casquette_inverse_marine', "Casquette à l'envers bleu marine", "Casquette à l'envers bleu marine", 'hat', 'CAP_INV', main=0x1B2A55, light=0xEDEDE6, accent=0xD4AF37),
    C('casquette_inverse_blanche', "Casquette à l'envers blanche", "Casquette à l'envers blanche", 'hat', 'CAP_INV', main=0xEDEDE6, light=0x141416, accent=0x2E6FD0),
    C('casquette_inverse_kaki', "Casquette à l'envers kaki", "Casquette à l'envers kaki", 'hat', 'CAP_INV', main=0x4B5A3A, light=0xC9A24A, accent=0x141416),
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
    # Parachute : se porte dans l'emplacement Dos, se déploie avec Espace en chute (voir Parachute.java)
    C('parachute', 'Parachute', 'Parachute', 'DOS', 'HIKING', main=0x3E4A2C, second=0x1E1E22, light=0xE8601C, metal=SILVER),
    C('parachute_noir', 'Parachute tactique noir', 'Parachute tactique noir', 'DOS', 'HIKING', main=0x1C1C1F, second=0x2C2C30, light=0x8A8F96, metal=SILVER_D),
    C('parachute_rouge', 'Parachute rouge et blanc', 'Parachute rouge et blanc', 'DOS', 'HIKING', main=0xB01B24, second=0x1E1E22, light=WHITE, metal=SILVER),
    C('parachute_bleu', 'Parachute bleu ciel', 'Parachute bleu ciel', 'DOS', 'HIKING', main=0x2A6FC0, second=0x1E1E22, light=0xF2F2EE, metal=SILVER),
    # parachutes VIP (voile violet et or) et VIP+ (voile noir et or à liseré cyan) : réservés au grade (VipItems)
    C('parachute_vip', 'Parachute VIP violet et or', 'Parachute VIP violet et or', 'DOS', 'HIKING', main=0x6A28B0, second=0x2A1440, light=0xE0B040, metal=GOLD),
    C('parachute_prestige', 'Parachute VIP+ Prestige', 'Parachute VIP+ Prestige', 'DOS', 'HIKING', main=0x141416, second=0x2A2A2E, light=0x2FD4E0, metal=GOLD),
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
    s2 = o.get('dos2')                        # seconde ligne (SAPEURS / POMPIERS, comme sur les vraies tenues)
    h = 5 * (sy or sc) + (5 * (sy or sc) + 3 if s2 else 0)
    if o.get('dos_fond') is not None:        # bandeau sombre derrière le lettrage (tenue sable : argent peu lisible sur fond clair)
        t.fill((260, y - 3, 316, y + h + 3), o['dos_fond'], noise=.02)
    text(t, 288 - w // 2, y, s, o.get('dos_col', REFL), sc, sy, gap, gl)
    if s2:
        text(t, 288 - text_w(s2, sc, gap, gl) // 2, y + 5 * (sy or sc) + 3, s2, o.get('dos_col', REFL), sc, sy, gap, gl)


def radio(t, x, y):
    """Radio portative clipsée sur la poitrine : boîtier noir, écran, antenne courte, cordon spiralé du micro vers l'épaule."""
    def det(d):
        d.rounded_rectangle((x, y, x + 10, y + 20), radius=2, fill=rgb(0x141416), outline=rgb(0x2C2C30))
        d.rectangle((x + 2, y + 3, x + 8, y + 7), fill=rgb(0x3A6A5A))                   # écran
        for k in range(3):
            d.line([(x + 2, y + 10 + k * 3), (x + 8, y + 10 + k * 3)], fill=rgb(0x2C2C30))   # grille du haut-parleur
        d.line([(x + 8, y), (x + 8, y - 7)], fill=rgb(0x0E0E10), width=2)              # antenne
        for k in range(4):
            d.arc((x - 2 - k * 3, y - 6 + k * 2, x + 2 - k * 3, y - 2 + k * 2), 0, 360, fill=rgb(0x141416))   # cordon spiralé
    draw_on(t, det)


def drapeau(t, keys=('O',), y=166):
    """Écusson tricolore sur le haut des manches (bleu, blanc, rouge)."""
    for k in keys:
        x0, _, x1, _ = ARM[k]
        cx = (x0 + x1) // 2 - 7
        t.rect((cx - 1, y - 1, cx + 15, y + 9), 0x0E0E12)
        t.rect((cx, y, cx + 5, y + 8), 0x1F3E9A); t.rect((cx + 5, y, cx + 10, y + 8), 0xF2F2EE); t.rect((cx + 10, y, cx + 14, y + 8), 0xC8202E)


def ceinturon(t, metal=None, y=232):
    """Ceinturon d'intervention noir : boucle, porte-menottes, étui d'arme sur la hanche, porte-chargeur, bâton, gants.
    y = haut de la ceinture (232 sur le pantalon ; 242 sur le polo, qui recouvre les hanches du pantalon)."""
    noir, e = 0x141416, 0x2C2C30
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, y, x1, y + 9), noir, noise=.02, sheen=.12)
    dy = y - 232
    def det(d0):
        class D:   # décale tout le dessin de dy pixels vers le bas
            def rectangle(self, b, **k): d0.rectangle((b[0], b[1] + dy, b[2], min(256, b[3] + dy)), **k)
            def ellipse(self, b, **k): d0.ellipse((b[0], b[1] + dy, b[2], b[3] + dy), **k)
            def line(self, pts, **k): d0.line([(x, min(255, yy + dy)) for x, yy in pts], **k)
        d = D()
        d.rectangle((186, 232, 198, 241), fill=rgb(metal or 0x2A2A2E), outline=rgb(0x0E0E10))   # boucle
        d.rectangle((200, 238, 214, 250), fill=rgb(noir), outline=rgb(e))                         # porte-chargeur
        d.line([(207, 238), (207, 250)], fill=rgb(e))
        d.rectangle((166, 238, 178, 248), fill=rgb(noir), outline=rgb(e))                         # porte-menottes
        d.ellipse((169, 241, 175, 247), outline=rgb(SILVER_D))
        d.rectangle((132, 236, 156, 256), fill=rgb(noir), outline=rgb(e))                         # étui d'arme (hanche droite)
        d.rectangle((136, 236, 152, 242), fill=rgb(0x222226))                                     # crosse
        d.rectangle((134, 244, 154, 248), fill=rgb(0x2C2C30))                                     # sangle de maintien
        d.rectangle((228, 236, 236, 256), fill=rgb(0x1E1E22))                                     # bâton télescopique (hanche gauche)
        d.rectangle((240, 238, 252, 250), fill=rgb(noir), outline=rgb(e))                         # pochette gants
        d.rectangle((300, 238, 314, 250), fill=rgb(noir), outline=rgb(e))                         # porte-radio / lampe (dos)
    draw_on(t, det)


def paint_police_pants(o, t):
    """Pantalon d'intervention police : cargo bleu nuit (ou noir RAID) avec le ceinturon complet porté par-dessus."""
    paint_caserne_pants(o, t)
    ceinturon(t, o.get('boucle'))


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
    radio(t, 207, 167)
    back_text(t, o, 210)


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
    if o.get('drapeau'):
        drapeau(t, ('O',), 168)
    if o.get('emblème') == 'texte':
        text(t, o.get('emblème_x', 204), 184, o.get('emblème_txt', o['dos']), o.get('emblème_col', o.get('dos_col', WHITE)), 1)          # sous l'empiècement
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
               'F1': shape_f1})


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


# ---------------------------------------------------------------- chaussures (03/11) : toutes les paires *_boots
# Tige peinte sur le bas des jambes (calque 1, art 512 x 256) ; semelle, bout arrondi, talon, languette, lacets, œillets et col en relief
# (forme « <id>_boots », cherchée par ClothesExtrasLayer pour l'emplacement pieds). Les pastilles des chaussures sont à part
# (index 16 à 31 : lignes 2 et 3 de la palette) pour ne pas toucher à celles du haut ou de la casquette de la même tenue.

SW += ['sole', 'sole_dark', 'upper', 'upper_dark', 'upper_hi', 'toe', 'lace', 'heel', 'eyelet', 'collar', 'logo', 'trim', 'tread', 'lining',
       'strap2', 'gloss']
SHOE0 = 16


def shoe_palette(s):
    u = s['upper']
    d = dict(sole=s.get('sole', WHITE), upper=u, upper_dark=s.get('overlay', sh(u, .72)), upper_hi=sh(u, 1.18), toe=s.get('toe', u),
             lace=s.get('lace', WHITE), heel=s.get('heel', s.get('overlay', u)), eyelet=s.get('eyelet', SILVER_D), collar=s.get('collar', sh(u, .8)),
             logo=s.get('logo_col', WHITE), trim=s.get('trim', sh(u, .8)), lining=s.get('lining', sh(u, 1.1)), strap2=s.get('strap', u),
             gloss=s.get('gloss', mix(u, 0xFFFFFF, .5)))
    d['sole_dark'] = s.get('sole_dark', sh(d['sole'], .75))
    d['tread'] = s.get('tread', sh(d['sole'], .62))
    return d


# Haut de la tige sur les côtés, du talon (0) au bout (1), en unités du membre (0 = hanche, 12 = sol) ; puis haut de la face avant.
PROFIL = {
    'basket': ([(0, 8.4), (.35, 9.1), (1, 9.5)], 8.0), 'runner': ([(0, 8.6), (.4, 9.3), (1, 9.6)], 8.2),
    'montante': ([(0, 5.0), (.5, 5.4), (1, 5.6)], 4.8), 'toile': ([(0, 8.8), (.5, 9.4), (1, 9.6)], 8.4),
    'chunky': ([(0, 8.2), (.4, 8.9), (1, 9.3)], 7.8), 'securite': ([(0, 7.4), (.5, 8.0), (1, 8.4)], 7.2),
    'derby': ([(0, 9.3), (.45, 9.9), (1, 10.1)], 8.8), 'mocassin': ([(0, 9.5), (.5, 10.2), (1, 9.9)], 9.6),
    'escarpin': ([(0, 9.9), (.4, 10.9), (.8, 10.9), (1, 10.6)], 10.6), 'sandale': ([(0, 10.6), (1, 10.6)], 10.6),
    'tong': ([(0, 12), (1, 12)], 12), 'claquette': ([(0, 12), (.55, 12), (.6, 10.4), (1, 10.4)], 10.4),
    'sabot': ([(0, 10.6), (.55, 10.6), (.6, 9.9), (1, 9.9)], 9.7),
    'botte': ([(0, 2.4), (1, 2.4)], 2.4), 'rangers': ([(0, 5.2), (1, 5.6)], 5.0), 'chantier': ([(0, 5.8), (1, 6.2)], 5.6),
    'chelsea': ([(0, 6.2), (.5, 6.8), (1, 6.4)], 6.4), 'santiag': ([(0, 3.0), (.5, 4.2), (1, 3.0)], 3.0),
    'apres_ski': ([(0, 4.6), (1, 4.6)], 4.6), 'fourree': ([(0, 4.4), (1, 4.4)], 4.4),
}
BASKETS = ('basket', 'runner', 'montante', 'toile', 'chunky', 'securite')
LACEES = BASKETS + ('derby', 'rangers', 'chantier')
SEMELLE = {'chunky': 10.5, 'runner': 10.9, 'securite': 10.9, 'derby': 11.6, 'mocassin': 11.6, 'chelsea': 11.4, 'santiag': 11.5,
           'escarpin': 11.9, 'sandale': 11.9, 'tong': 11.9, 'claquette': 11.6, 'sabot': 11.5, 'apres_ski': 10.6, 'fourree': 11.4}
MATIERE = {'cuir': dict(noise=.03, sheen=.14), 'vernis': dict(noise=.01, sheen=.55, grad=(1.18, .8)), 'daim': dict(noise=.08, heather=.06),
           'toile': dict(noise=.03, twill=.06), 'maille': dict(noise=.04, heather=.07), 'nubuck': dict(noise=.07, heather=.05),
           'caoutchouc': dict(noise=.015, sheen=.3), 'nylon': dict(noise=.02, twill=.02, sheen=.12), 'monogramme': dict(noise=.03, twill=.03)}


def shoe_top(kind, s):
    pts = PROFIL[kind][0]
    for (s0, y0), (s1, y1) in zip(pts, pts[1:]):
        if s <= s1:
            return y0 + (y1 - y0) * (s - s0) / max(1e-6, s1 - s0)
    return pts[-1][1]


def Y(u):
    return int(round(160 + 8 * u))


def side_x(k, s):
    """Côtés du pied : s = 0 au talon, 1 au bout (face extérieure O : le bout touche la face avant, à droite ; intérieure I : à gauche)."""
    x0 = LEG[k][0]
    return x0 + s * 32 if k == 'O' else x0 + (1 - s) * 32


def side_poly(d, pts, fill=None, outline=None, faces_=('O', 'I')):
    """Polygone en coordonnées du pied (s, unité) sur les deux côtés."""
    for k in faces_:
        d.polygon([(side_x(k, s), Y(u)) for (s, u) in pts], fill=fill, outline=outline)


def side_line(d, pts, fill, width=1, dots=False, faces_=('O', 'I')):
    for k in faces_:
        p = [(side_x(k, s), Y(u)) for (s, u) in pts]
        if dots:                                                              # piqûres : points espacés
            for (xa, ya), (xb, yb) in zip(p, p[1:]):
                n = max(1, int(max(abs(xb - xa), abs(yb - ya)) / 3))
                for i in range(n + 1):
                    d.point((xa + (xb - xa) * i / n, ya + (yb - ya) * i / n), fill=fill)
        else:
            d.line(p, fill=fill, width=width)


def mat_fill(t, r, c, mat):
    p = dict(grad=(1.08, .9))
    p.update(MATIERE[mat])
    t.fill(r, c, **p)
    x0, y0, x1, y1 = r
    if mat == 'maille':                                                       # mailles : rangs horizontaux
        for y in range(y0, y1, 3):
            t.mul((x0, y, x1, y + 1), .86)


def paint_shoe_tex(t, s):
    kind, m, mat = s['kind'], s['upper'], s.get('matiere', 'cuir')
    P = shoe_palette(s)
    ftop = PROFIL[kind][1]
    semelle = SEMELLE.get(kind, 11.2)
    t.clear((0, 128, 128, 256))
    # ---- tige : matière, découpée selon le profil
    for k in LEGS4:
        x0, _, x1, _ = LEG[k]
        if k in ('O', 'I'):
            tops = [shoe_top(kind, ((x - x0) + .5) / 32 if k == 'O' else 1 - ((x - x0) + .5) / 32) for x in range(x0, x1)]
        else:
            tops = [ftop if k == 'F' else shoe_top(kind, 0)] * 32
        y_min = Y(min(tops))
        if y_min >= 256:
            continue
        mat_fill(t, (x0, y_min, x1, 256), m, mat)
        for i, x in enumerate(range(x0, x1)):
            t.clear((x, y_min, x + 1, Y(tops[i])))
            if kind not in ('tong', 'claquette', 'sandale', 'sabot'):
                t.mul((x, Y(tops[i]), x + 1, Y(tops[i]) + 3), .74)             # bord du col (rembourrage / tranche)
    t.fill((64, 128, 96, 160), P['tread'], noise=.05)                          # dessous du pied : semelle crantée
    for y in range(130, 160, 4):
        t.mul((64, y, 96, y + 2), .72)
    if kind == 'monogramme' or mat == 'monogramme':
        mono = rgb(s.get('logo_col', 0xC9A24A))
        for k in LEGS4:
            x0 = LEG[k][0]
            for yy in range(Y(ftop) + 4, 256, 9):
                for xx in range(x0 + 2 + (yy // 9 % 2) * 4, x0 + 32, 8):
                    t.rect((xx, yy, xx + 1, yy + 3), mono); t.rect((xx - 1, yy + 1, xx + 2, yy + 2), mono)

    up, dk, hi, sole = rgb(m), rgb(P['upper_dark']), rgb(P['upper_hi']), rgb(P['sole'])
    lace, eye, logo, trim, lin = rgb(P['lace']), rgb(P['eyelet']), rgb(P['logo']), rgb(P['trim']), rgb(P['lining'])
    thread = rgb(s.get('fil', sh(m, 1.45) if sum(rgb(m)) < 330 else sh(m, .7)))

    def det(d):
        # ---- baskets : empiècements, piqûres, languette, lacets croisés, logo, semelle intermédiaire
        if kind in BASKETS:
            ov = rgb(P['upper_dark'])
            t0 = shoe_top(kind, .72)
            side_poly(d, [(.68, t0 + .5), (1, t0 + .4), (1, semelle), (.62, semelle)], fill=ov)                  # bout rapporté
            side_line(d, [(.68, t0 + .7), (.64, semelle - .2)], thread, dots=True)
            h0 = shoe_top(kind, 0)
            side_poly(d, [(0, h0 + .4), (.26, h0 + 1.2), (.32, semelle), (0, semelle)], fill=rgb(P['heel']))     # contrefort
            side_line(d, [(.27, h0 + 1.4), (.31, semelle - .2)], thread, dots=True)
            side_line(d, [(0, h0 + .45), (.5, shoe_top(kind, .5) + .45), (1, shoe_top(kind, 1) + .45)], thread, dots=True)
            if kind == 'montante':
                side_poly(d, [(0, 5.3), (.4, 5.7), (.45, 7.6), (0, 7.4)], fill=rgb(P['collar']))                # col contrasté
            for (x, w) in ((32, 8), (56, 8)):                                                                   # passants d'œillets
                d.rectangle((x, Y(ftop), x + w - 1, Y(9.8)), fill=ov)
            d.rectangle((40, Y(ftop) - 2, 55, Y(9.8)), fill=lin)                                               # languette
            y, n = Y(ftop) + 3, 0
            while y < Y(9.6):
                d.ellipse((35, y - 1, 37, y + 1), fill=eye); d.ellipse((58, y - 1, 60, y + 1), fill=eye)
                d.line([(37, y), (58, y + 4)], fill=lace, width=2); d.line([(58, y), (37, y + 4)], fill=sh(lace, .82), width=2)
                y += 6; n += 1
            if kind == 'toile':
                for k in LEGS4:
                    x0 = LEG[k][0]
                    d.rectangle((x0, Y(semelle) + 3, x0 + 31, Y(semelle) + 4), fill=rgb(s.get('liseré', 0x1A1A1D)))
            if kind == 'securite':
                side_line(d, [(0, 8.3), (1, 9.1)], rgb(HIVIS), width=3)
            logo_kind = s.get('logo')
            if logo_kind == 'swoosh':
                side_poly(d, [(.9, 10.1), (.78, 10.75), (.5, 10.55), (.12, 9.0), (.45, 10.0), (.72, 10.3)], fill=logo)
            elif logo_kind == 'bandes':
                for i in range(3):
                    a = .36 + i * .11
                    side_poly(d, [(a, shoe_top(kind, a) + .5), (a + .06, shoe_top(kind, a) + .5), (a + .13, semelle), (a + .07, semelle)], fill=logo)
            elif logo_kind == 'formstrip':
                side_poly(d, [(.82, 10.6), (.62, 10.7), (.12, 9.2), (.12, 9.7), (.6, 10.3), (.82, 10.2)], fill=logo)
            elif logo_kind == 'web':
                side_poly(d, [(.15, 9.7), (.78, 9.9), (.78, 10.8), (.15, 10.6)], fill=rgb(0x1E6B3A))
                side_poly(d, [(.15, 9.95), (.78, 10.15), (.78, 10.5), (.15, 10.35)], fill=rgb(0xB01B24))
            elif logo_kind == 'jump':
                side_poly(d, [(.42, 5.9), (.62, 5.6), (.6, 6.6), (.44, 6.7)], fill=logo)
                side_poly(d, [(.88, 10.0), (.75, 10.6), (.5, 10.4), (.15, 8.5), (.47, 9.8), (.7, 10.2)], fill=rgb(0x141416))
            elif logo_kind == 'tab':
                d.rectangle((100, Y(semelle) - 9, 104, Y(semelle) - 3), fill=rgb(0xC8202A))
            elif logo_kind == 'n':
                side_poly(d, [(.35, 9.4), (.42, 9.4), (.55, 10.3), (.55, 9.4), (.62, 9.4), (.62, 10.9), (.55, 10.9), (.42, 10.0), (.42, 10.9), (.35, 10.9)], fill=logo)
            d.rectangle((108, Y(shoe_top(kind, 0)) - 2, 115, Y(shoe_top(kind, 0)) + 9), fill=trim)          # tirant de talon
            for k in LEGS4:                                                                                       # semelle intermédiaire
                x0 = LEG[k][0]
                d.rectangle((x0, Y(semelle), x0 + 31, 255), fill=sole)
                d.line([(x0, Y(semelle) + 1), (x0 + 31, Y(semelle) + 1)], fill=sh(sole, .82))
            if kind == 'chunky':
                side_poly(d, [(0, semelle), (.5, semelle + .25), (1, semelle), (1, semelle + .6), (0, semelle + .7)], fill=rgb(s.get('second', 0xB01B24)))
        # ---- chaussures de ville : piqûre de trépointe, bout rapporté, lacets ou mors, reflet du cuir
        if kind in ('derby', 'mocassin', 'chelsea', 'santiag', 'escarpin'):
            for k in LEGS4:
                x0 = LEG[k][0]
                d.rectangle((x0, Y(semelle), x0 + 31, 255), fill=sole)
                if kind != 'escarpin':
                    for x in range(x0, x0 + 32, 3):
                        d.point((x + 1, Y(semelle) - 2), fill=thread)
            if kind != 'escarpin':
                side_line(d, [(.55, shoe_top(kind, .55) + .3), (.6, semelle - .2)], dk)                        # couture du quartier
            if s.get('richelieu'):
                side_line(d, [(.8, shoe_top(kind, .8) + .2), (.76, semelle - .1)], dk, width=2)
                d.line([(32, Y(10.6)), (63, Y(10.6))], fill=dk, width=2)
                if s.get('fleuri'):                                                                               # perforations (brogue)
                    for k in ('O', 'I'):
                        for i in range(6):
                            d.point((side_x(k, .73 - i * .002) + (1 if k == 'O' else -1) * 0, Y(10.0 + i * .26)), fill=sh(m, .45))
                    for x in range(34, 63, 3):
                        d.point((x, Y(10.4)), fill=sh(m, .45))
            if kind == 'derby':
                d.rectangle((38, Y(ftop), 57, Y(10.0)), fill=dk)
                for y in (Y(9.0), Y(9.45), Y(9.9)):
                    d.line([(39, y), (56, y)], fill=lace, width=2)
                    d.point((38, y), fill=eye); d.point((57, y), fill=eye)
            if kind == 'mocassin':
                d.arc((36, Y(9.7), 59, Y(11.6)), 180, 360, fill=thread)                                           # plateau cousu
                d.line([(36, Y(10.65)), (36, Y(11.6))], fill=thread); d.line([(59, Y(10.65)), (59, Y(11.6))], fill=thread)
                if s.get('mors', True):
                    d.rectangle((38, Y(9.75), 57, Y(9.75) + 2), fill=rgb(s.get('metal', GOLD)))
            if kind == 'chelsea':
                for k in ('O', 'I'):                                                                              # élastique latéral
                    xs = sorted([side_x(k, .32), side_x(k, .52)])
                    d.polygon([(xs[0], Y(6.4)), (xs[1], Y(6.5)), ((xs[0] + xs[1]) / 2, Y(9.4))], fill=sh(m, .45))
                d.rectangle((108, Y(6.2) - 8, 115, Y(6.2) + 2), fill=sh(m, .6))                                  # tirette
            if kind == 'santiag':
                for (a, b) in ((3.6, 5.2), (4.4, 6.2), (5.2, 7.2)):                                               # surpiqûres décoratives
                    side_line(d, [(.2, a), (.5, b), (.8, a)], thread)
                side_poly(d, [(0, 7.0), (.25, 7.6), (.3, semelle), (0, semelle)], fill=dk)
            if kind == 'escarpin' and s.get('bride'):
                for k in LEGS4:
                    x0 = LEG[k][0]
                    d.rectangle((x0, Y(9.3), x0 + 31, Y(9.7)), fill=rgb(P['strap2']))
            for k in ('O', 'I'):                                                                                  # reflet
                x = side_x(k, .72)
                d.line([(x, Y(shoe_top(kind, .72)) + 4), (x, Y(semelle) - 4)], fill=rgb(P['gloss']))
        # ---- bottes, rangers, boots
        if kind in ('botte', 'rangers', 'chantier', 'apres_ski', 'fourree'):
            top = shoe_top(kind, 0)
            for k in LEGS4:
                x0 = LEG[k][0]
                d.rectangle((x0, Y(semelle), x0 + 31, 255), fill=sole)
            if kind in ('botte', 'rangers', 'chantier'):
                side_poly(d, [(.66, 9.2), (1, 9.0), (1, semelle), (.6, semelle)], fill=rgb(P['toe']))             # coque du bout
                side_poly(d, [(0, 8.6), (.24, 9.0), (.3, semelle), (0, semelle)], fill=rgb(P['heel']))
                d.line([(112, Y(top) + 2), (112, Y(semelle))], fill=dk)                                          # couture arrière
            if kind in ('rangers', 'chantier'):
                d.rectangle((38, Y(top) - 2, 57, Y(9.4)), fill=lin)
                y = Y(top) + 3
                while y < Y(9.4):
                    hook = y < Y(top + 1.6)
                    for x in (36, 59):
                        if hook:
                            d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=eye)
                        else:
                            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=eye)
                    d.line([(37, y), (58, y + 5)], fill=lace, width=2); d.line([(58, y), (37, y + 5)], fill=sh(lace, .8), width=2)
                    y += 6
            if kind == 'chantier':
                for k in LEGS4:
                    x0 = LEG[k][0]
                    d.rectangle((x0, Y(top), x0 + 31, Y(top) + 7), fill=rgb(P['collar']))                         # col rembourré
                side_line(d, [(.6, 9.3), (1, 9.1)], thread, dots=True); side_line(d, [(0, 8.7), (.25, 9.1)], thread, dots=True)
                for k in ('O',):
                    x, y = side_x(k, .4), Y(7.2)
                    d.polygon([(x, y - 6), (x - 4, y + 2), (x + 4, y + 2)], fill=sh(m, .55)); d.line([(x, y + 2), (x, y + 5)], fill=sh(m, .55))
            if kind == 'botte' and s.get('bande'):
                band(t, LEGS4, LEG, Y(top) + 14, 6)
            if kind == 'botte':
                for k in ('O', 'I'):
                    x = side_x(k, .5)
                    d.rectangle((x - 3, Y(top), x + 3, Y(top) + 8), fill=sh(m, .6))                                # tirants
            if kind == 'apres_ski':
                for y in range(Y(top) + 8, Y(semelle), 7):
                    d.line([(0, y), (127, y)], fill=sh(m, .78))                                                  # matelassage
                for k in ('O', 'I'):
                    x = side_x(k, .5)
                    tw = text_w('MOUN')
                    text(t, int(x - tw / 2), Y(7.0), 'MOUN', rgb(s.get('logo_col', 0x1A1A1D)))
            if kind == 'fourree':
                for k in LEGS4:
                    x0 = LEG[k][0]
                    d.line([(x0 + 16, Y(top) + 8), (x0 + 16, Y(semelle))], fill=sh(m, .78))
        if kind == 'claquette':
            d.rectangle((32, Y(10.4), 63, Y(11.6)), fill=up)
            if s.get('logo') == 'swoosh':
                d.polygon([(54, Y(10.7)), (50, Y(11.2)), (38, Y(11.3)), (46, Y(11.0))], fill=logo)
            elif s.get('logo') == 'web':
                d.rectangle((32, Y(10.75), 63, Y(11.25)), fill=rgb(0x1E6B3A)); d.rectangle((32, Y(10.9), 63, Y(11.1)), fill=rgb(0xB01B24))
            for k in LEGS4:
                x0 = LEG[k][0]
                d.rectangle((x0, Y(11.6), x0 + 31, 255), fill=sole)
        if kind == 'sabot':
            for k in ('F', 'O', 'I'):
                x0 = LEG[k][0]
                for yy in (Y(10.3), Y(10.9)):
                    for xx in range(x0 + 4 + (yy % 2) * 3, x0 + 30, 6):
                        if k == 'F' or (k == 'O' and xx > x0 + 18) or (k == 'I' and xx < x0 + 14):
                            d.ellipse((xx - 1, yy - 1, xx + 1, yy + 1), fill=sh(m, .55))                         # aérations
        if kind in ('tong', 'sandale'):
            for k in LEGS4:
                x0 = LEG[k][0]
                d.rectangle((x0, Y(11.9), x0 + 31, 255), fill=sole)
            if kind == 'sandale':
                for k in LEGS4:
                    x0 = LEG[k][0]
                    d.rectangle((x0, Y(9.3), x0 + 31, Y(9.7)), fill=rgb(P['strap2']))                             # bride de cheville
                d.rectangle((32, Y(11.0), 63, Y(11.4)), fill=rgb(P['strap2']))
    draw_on(t, det)
    if kind == 'sandale':                                                                                         # entre les brides : la peau du skin
        for k in LEGS4:
            x0 = LEG[k][0]
            t.clear((x0, Y(9.7), x0 + 32, Y(11.0) if k == 'F' else Y(11.9)))
        t.clear((32, Y(11.4), 64, Y(11.9)))
    if kind == 'tong':
        t.clear((0, Y(0), 128, Y(11.9)))
    if kind == 'claquette':
        t.clear((96, Y(0), 128, Y(11.6)))


# ---- volumes : pied droit, le gauche en miroir (sym)

def shoe_boxes(s):
    kind, L = s['kind'], 'right_leg'
    semelle = SEMELLE.get(kind, 11.2)
    b = []
    if kind in BASKETS:
        hi = shoe_top(kind, 0)
        st = semelle
        b += [(L, -2.52, st, -3.4, 2.52, 12.3, 2.62, 'sole'),                     # semelle intermédiaire
              (L, -2.2, st + .15, -3.72, 2.2, 12.25, -3.4, 'sole'), (L, -1.5, st + .3, -3.9, 1.5, 12.2, -3.72, 'sole'),   # arrondi avant
              (L, -2.44, 12.3, -3.6, 2.44, 12.6, 2.55, 'tread'),                   # semelle d'usure
              (L, -2.36, 9.8, -3.25, 2.36, st, -2.2, 'toe' if kind in ('toile', 'securite') or s.get('coquille') else 'upper_dark'),   # bout
              (L, -1.85, 10.1, -3.62, 1.85, st, -3.25, 'toe' if kind in ('toile', 'securite') or s.get('coquille') else 'upper_dark'),
              (L, -2.15, 9.3, -2.85, 2.15, 9.8, -2.2, 'upper'),                   # cou-de-pied
              (L, -1.2, hi - .7, -2.6, 1.2, 9.4, -2.3, 'lining'),                 # languette, qui dépasse du col
              (L, -2.1, 9.2, 2.3, 2.1, st, 2.66, 'heel'),                        # contrefort
              (L, -0.45, hi - .9, 2.3, 0.45, hi + .3, 2.56, 'trim'),             # tirant
              (L, -2.46, hi, -1.9, 2.46, hi + .6, 2.5, 'collar')]                # col rembourré
        y = hi + .35
        while y < 9.2:                                                          # lacets
            b.append((L, -1.1, y, -2.74, 1.1, y + .26, -2.6, 'lace'))
            y += .55 if kind != 'montante' else .6
        b += [(L, -1.55, hi + .1, -2.52, -1.15, 9.5, -2.3, 'upper_dark'), (L, 1.15, hi + .1, -2.52, 1.55, 9.5, -2.3, 'upper_dark')]   # passants
        if kind == 'toile' or s.get('coquille'):
            b.append((L, -1.7, 10.6, -3.66, 1.7, 10.75, -3.6, 'sole_dark'))        # bout caoutchouc strié
        if kind == 'chunky':
            b += [(L, -2.62, st + .3, -3.0, 2.62, st + .9, 2.4, 'trim')]          # couche de semelle contrastée
        logo = s.get('logo')
        if logo == 'swoosh':
            b += [(L, -2.47, 10.3, -1.9, -2.34, 10.65, -0.9, 'logo'), (L, -2.47, 9.95, -0.9, -2.34, 10.4, 0.6, 'logo'),
                  (L, -2.47, 9.4, 0.6, -2.34, 10.0, 1.7, 'logo'), (L, -2.47, 9.9, -2.25, -2.34, 10.3, -1.9, 'logo')]
        elif logo == 'bandes':
            for i in range(3):
                z = -0.9 + i * .55
                b.append((L, -2.47, 9.3 - i * .1, z, -2.34, st, z + .28, 'logo'))
        elif logo == 'formstrip':
            b += [(L, -2.47, 10.1, -1.7, -2.34, 10.5, 0.0, 'logo'), (L, -2.47, 9.5, 0.0, -2.34, 9.95, 1.8, 'logo')]
        elif logo == 'web':
            b += [(L, -2.48, 9.75, -1.3, -2.34, 10.6, 1.9, 'trim'), (L, -2.52, 10.0, -1.3, -2.48, 10.35, 1.9, 'logo')]
        elif logo == 'jump':
            b += [(L, -2.5, 5.9, -0.3, -2.44, 6.7, 1.3, 'logo'), (L, -2.47, 9.4, -1.6, -2.34, 9.9, 1.4, 'upper_dark')]
        elif logo == 'n':
            b += [(L, -2.47, 9.5, -0.4, -2.34, 10.9, 0.6, 'logo')]
        if s.get('liseré_relief'):
            b.append((L, -2.56, st + .25, -3.45, 2.56, st + .45, 2.65, 'trim'))
    elif kind in ('derby', 'mocassin', 'chelsea', 'santiag'):
        st = semelle
        pointe = -4.35 if kind == 'santiag' else -4.0
        b += [(L, -2.42, st + .1, -3.65, 2.42, 12.35, 2.5, 'sole'), (L, -1.75, st + .15, pointe, 1.75, 12.3, -3.65, 'sole'),
              (L, -2.48, st - .12, -3.72, 2.48, st + .12, 2.56, 'sole_dark'), (L, -1.8, st - .12, pointe - .05, 1.8, st + .12, -3.65, 'sole_dark'),   # trépointe
              (L, -2.2, 12.35, 0.6, 2.2, 12.7, 2.45, 'heel'),                                                     # talon
              (L, -2.3, 10.3, -3.5, 2.3, st, -2.2, 'upper'), (L, -1.65, 10.6, pointe + .08, 1.65, st, -3.5, 'upper'),   # bout effilé
              (L, -2.1, 9.7, -2.9, 2.1, 10.3, -2.2, 'upper'), (L, -2.05, 9.6, 2.3, 2.05, st, 2.5, 'upper'),
              (L, -1.0, 10.22, -3.3, 0.2, 10.3, -2.6, 'gloss')]                                                  # reflet sur le bout
        if s.get('richelieu'):
            b.append((L, -2.33, 10.28, -3.02, 2.33, st + .02, -2.92, 'upper_dark'))
        if kind == 'derby':
            b += [(L, -0.95, 8.6, -2.44, 0.95, 9.8, -2.3, 'upper_dark')]
            for y in (8.95, 9.4):
                b.append((L, -0.9, y, -2.54, 0.9, y + .2, -2.42, 'lace'))
        if kind == 'mocassin':
            b += [(L, -1.6, 9.62, -2.98, 1.6, 9.72, -2.2, 'upper_dark')]
            if s.get('mors', True):
                b += [(L, -1.25, 9.45, -2.72, 1.25, 9.7, -2.45, 'trim'), (L, -1.4, 9.4, -2.75, -1.1, 9.75, -2.42, 'trim'),
                      (L, 1.1, 9.4, -2.75, 1.4, 9.75, -2.42, 'trim')]
        if kind == 'chelsea':
            b += [(L, -0.5, 5.4, 2.3, 0.5, 6.9, 2.55, 'trim'), (L, -2.42, 6.2, -2.42, 2.42, 6.6, 2.42, 'collar')]
        if kind == 'santiag':
            b += [(L, -2.0, 12.35, 0.9, 2.0, 13.0, 2.45, 'heel'), (L, -1.2, 2.2, -2.5, 1.2, 3.0, -2.32, 'upper'),
                  (L, -1.2, 2.2, 2.32, 1.2, 3.0, 2.5, 'upper'), (L, -2.44, 2.9, -2.44, 2.44, 3.3, 2.44, 'collar')]
    elif kind in ('escarpin', 'sandale'):
        b += [(L, -2.1, 12.0, -3.8, 2.1, 12.5, -0.6, 'sole'), (L, -1.2, 12.0, -4.3, 1.2, 12.45, -3.8, 'sole'),       # semelle avant
              (L, -1.9, 11.85, -0.6, 1.9, 12.2, 1.6, 'sole'),                                                       # cambrure
              (L, -0.75, 11.6, 1.5, 0.75, 12.15, 2.55, 'heel'), (L, -0.45, 12.15, 1.85, 0.45, 12.65, 2.4, 'heel'),  # talon aiguille
              (L, -0.42, 12.65, 1.9, 0.42, 12.78, 2.35, 'sole_dark')]
        if kind == 'escarpin':
            b += [(L, -2.25, 10.9, -3.5, 2.25, 12.0, -2.2, 'upper'), (L, -1.5, 11.1, -4.05, 1.5, 12.0, -3.5, 'upper'),
                  (L, -0.7, 11.3, -4.35, 0.7, 12.0, -4.05, 'upper'), (L, -2.1, 10.2, 2.3, 2.1, 11.6, 2.55, 'upper'),
                  (L, -0.9, 10.82, -3.3, 0.0, 10.9, -2.6, 'gloss')]
            if s.get('bride'):
                b.append((L, -2.4, 9.25, -2.4, 2.4, 9.7, 2.4, 'strap2'))
        else:
            b += [(L, -2.4, 9.25, -2.4, 2.4, 9.7, 2.4, 'strap2'), (L, -2.3, 10.95, -3.3, 2.3, 11.45, -2.25, 'strap2'),
                  (L, -2.1, 10.2, 2.3, 2.1, 11.6, 2.5, 'strap2'), (L, -0.3, 9.7, 2.32, 0.3, 10.2, 2.48, 'strap2'),
                  (L, -0.4, 9.3, -2.55, 0.4, 9.75, -2.38, 'trim')]                                                   # boucle
    elif kind in ('tong', 'claquette'):
        ep = 11.95 if kind == 'tong' else 11.6
        b += [(L, -2.25, ep, -3.55, 2.25, 12.55, 2.45, 'sole'), (L, -1.6, ep + .05, -3.85, 1.6, 12.5, -3.55, 'sole'),
              (L, -2.2, ep - .1, -3.5, 2.2, ep, 2.4, 'upper' if kind == 'tong' else 'lining')]                       # semelle de propreté
        if kind == 'tong':
            b += [(L, -0.2, 11.2, -3.1, 0.2, 11.85, -2.85, 'strap2'), (L, -1.2, 11.3, -2.62, 1.2, 11.55, -2.32, 'strap2'),
                  (L, -2.4, 11.4, -2.32, -2.32, 11.65, -0.8, 'strap2'), (L, 2.32, 11.4, -2.32, 2.4, 11.65, -0.8, 'strap2')]
        else:
            b += [(L, -2.45, 10.4, -3.0, 2.45, 11.6, -0.4, 'upper'), (L, -1.0, 10.32, -2.4, 1.0, 10.4, -1.2, 'logo')]
    elif kind == 'sabot':
        b += [(L, -2.6, 11.5, -3.6, 2.6, 12.55, 2.6, 'sole'), (L, -2.55, 9.6, -3.5, 2.55, 11.5, -0.9, 'upper'),
              (L, -2.0, 9.9, -3.85, 2.0, 11.5, -3.5, 'upper'), (L, -2.42, 9.6, 0.9, 2.42, 10.2, 2.45, 'strap2'),
              (L, -2.5, 9.5, 0.6, -2.42, 10.3, 1.4, 'trim'), (L, 2.42, 9.5, 0.6, 2.5, 10.3, 1.4, 'trim')]
        for (x, z) in ((-1.4, -3.0), (0.0, -3.0), (1.4, -3.0), (-0.7, -2.0), (0.7, -2.0), (-1.4, -1.2), (1.4, -1.2)):
            b.append((L, x - .25, 9.52, z - .25, x + .25, 9.6, z + .25, 'upper_dark'))                               # aérations
    else:   # bottes, rangers, boots, après-ski, fourrées
        top = shoe_top(kind, 0)
        st = semelle
        puffy = kind == 'apres_ski'
        w = 2.85 if puffy else 2.56
        b += [(L, -w, st, -3.35, w, 12.35, w + .1, 'sole'), (L, -w + .08, 12.35, -3.25, w - .08, 12.65, w, 'tread'),
              (L, -1.9, st + .1, -3.62, 1.9, 12.3, -3.35, 'sole'),
              (L, -2.42, 9.7, -3.15, 2.42, st, -2.2, 'toe'), (L, -1.85, 10.0, -3.45, 1.85, st, -3.15, 'toe'),
              (L, -2.3, 9.1, -2.75, 2.3, 9.7, -2.2, 'upper'), (L, -2.25, 10.0, 2.3, 2.25, st, 2.62, 'heel')]
        if kind in ('botte', 'rangers', 'chantier'):
            b += [(L, -2.46, top, -2.46, 2.46, top + .55, 2.46, 'collar')]
        if kind == 'botte':
            b += [(L, -2.52, top - .2, -0.35, -2.4, top + 1.0, 0.35, 'trim'), (L, 2.4, top - .2, -0.35, 2.52, top + 1.0, 0.35, 'trim')]
            if s.get('bande'):
                b.append((L, -2.4, top + 1.75, -2.4, 2.4, top + 2.5, 2.4, 'logo'))
            if s.get('moto'):                                                     # botte de moto : coques rapportées
                b += [(L, -1.7, 4.6, -2.72, 1.7, 8.9, -2.48, 'toe'), (L, -1.2, 5.0, -2.86, 1.2, 8.5, -2.72, 'toe'),               # protège-tibia
                      (L, -2.6, 8.5, -0.7, -2.44, 9.7, 0.7, 'trim'), (L, -2.66, 8.8, -0.4, -2.6, 9.4, 0.4, 'logo'),             # puck de cheville
                      (L, -2.58, 10.0, -3.2, -2.4, 11.0, -1.4, 'toe'),                                                          # slider de pointe
                      (L, -2.52, top + 3.4, -2.52, 2.52, top + 3.95, 2.52, 'collar'),                                           # sangle à scratch
                      (L, -2.52, 9.6, 2.4, 2.52, 11.0, 2.75, 'heel')]                                                          # coque de talon
        if kind in ('rangers', 'chantier'):
            b.append((L, -1.15, top - .3, -2.5, 1.15, 9.5, -2.3, 'lining'))
            y = top + .35
            while y < 9.2:
                b += [(L, -1.1, y, -2.7, 1.1, y + .24, -2.56, 'lace'), (L, -1.5, y - .05, -2.6, -1.15, y + .32, -2.36, 'eyelet'),
                      (L, 1.15, y - .05, -2.6, 1.5, y + .32, -2.36, 'eyelet')]
                y += .62
        if kind == 'chantier':
            b.append((L, -2.56, top, -2.1, 2.56, top + .9, 2.56, 'collar'))
        if puffy:
            b += [(L, -2.95, top - .3, -2.95, 2.95, top + .7, 2.95, 'collar'), (L, -2.7, 9.0, -2.7, 2.7, st, 2.7, 'upper'),
                  (L, -0.25, top + .6, -2.98, 0.25, 9.0, -2.82, 'lace'), (L, -0.4, top + .2, -3.05, 0.4, top + .8, -2.85, 'trim')]
        if kind == 'fourree':
            b += [(L, -2.62, top - .3, -2.62, 2.62, top + .8, 2.62, 'lining')]
    return sym(b)


def shoe_item_boxes(s):
    """Inventaire : la paire, avec la tige (peinte sur le membre en jeu) ajoutée en volume."""
    b = shoe_boxes(s)
    kind = s['kind']
    if kind not in ('tong', 'claquette', 'sandale', 'sabot'):
        top = PROFIL[kind][1]
        b += sym([('right_leg', -2.32, top, -2.32, 2.32, SEMELLE.get(kind, 11.2), 2.32, 'upper')])
    return b


def shoe_cells(s, name):
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    d = shoe_palette(s)
    for k, key in enumerate(SW[SHOE0:]):
        im.paste(rgb(d[key]) + (255,), ((k % 4) * 4, (k // 4) * 4, (k % 4) * 4 + 4, (k // 4) * 4 + 4))
    im.save(R + 'textures/item/%s.png' % name)


def paint_shoe(o, t):
    """Peinture des chaussures vendues seules (calque 1, bas des jambes)."""
    paint_shoe_tex(t, o['shoe'])


def shoe_shape_name(o):
    return 'SHOE_' + o['id'].upper()


# Chaussures des anciennes tenues (Gen.java, gen_rp.py) : seul le bas des jambes de leur calque 1 est repeint.
def SP(id, kind, upper, **p):
    return dict(id=id, shoe=dict(kind=kind, upper=upper, **p))


SHOES_TENUES = [
    SP('nayk_noir', 'basket', 0xF2F2EE, sole=0xF6F6F2, logo='swoosh', logo_col=0x9A9DA2, lace=0xF2F2EE, overlay=0xE6E6E2),
    SP('nayk_gris', 'basket', 0x1C1C20, sole=0xF2F2EE, logo='swoosh', logo_col=0xF2F2EE, lace=0x1C1C20, overlay=0x26262A),
    SP('nayk_rouge', 'basket', 0xB01B24, sole=0xF2F2EE, logo='swoosh', logo_col=0xF2F2EE, lace=0xF2F2EE, overlay=0x9A1820),
    SP('abidas_bleu', 'basket', 0xF2F2EE, sole=0xF2F2EE, logo='bandes', logo_col=0x1F3F9E, toe=0xF2F2EE, coquille=True, trim=0x1F3F9E,
       overlay=0xF2F2EE, lace=0xF2F2EE),
    SP('abidas_noir', 'basket', 0x1A1A1D, sole=0xF2F2EE, logo='bandes', logo_col=0xF2F2EE, toe=0xF2F2EE, coquille=True, trim=0xF2F2EE,
       overlay=0x1A1A1D, lace=0xF2F2EE),
    SP('pumba_rouge', 'basket', 0xA81C24, matiere='daim', sole=0xF2F2EE, logo='formstrip', logo_col=0xF2F2EE, overlay=0x98181F, lace=0xA81C24),
    SP('pumba_blanc', 'basket', 0xF2F2EE, sole=0x1C1C20, tread=0x101012, logo='formstrip', logo_col=0x1C1C20, overlay=0xE8E8E4, lace=0xF2F2EE),
    SP('guchi_vert', 'basket', 0xF4F2EC, sole=0xF4F2EC, logo='web', logo_col=0xB01B24, trim=0x1E6B3A, overlay=0xEDEBE4, lace=0xF4F2EC,
       heel=0x1E6B3A),
    SP('louis_vuiten', 'basket', 0x6B4423, matiere='monogramme', sole=0xE8DCC0, logo_col=0xC9A24A, overlay=0x4A2E18, lace=0xE8DCC0,
       collar=0x4A2E18, trim=0xC9A24A),
    SP('jordane_rouge', 'montante', 0xF2F2EE, sole=0xF2F2EE, tread=0xB01B24, overlay=0xB01B24, heel=0xB01B24, collar=0x141416,
       logo='jump', logo_col=0x141416, lace=0xF2F2EE, trim=0x141416),
    SP('levys_jean', 'toile', 0xF2F2EE, matiere='toile', sole=0xF2F2EE, toe=0xF2F2EE, logo='tab', lace=0xF2F2EE, liseré=0x2B4470,
       overlay=0xF2F2EE),
    SP('costard_noir', 'derby', 0x161618, sole=0x101012, richelieu=True, lace=0x101012, overlay=0x0C0C0E, gloss=0x8A8A92),
    SP('costard_marine', 'derby', 0x7A4524, sole=0x2A1A10, richelieu=True, fleuri=True, lace=0x3A2414, overlay=0x5E3418, gloss=0xC89A6A),
    SP('costard_blanc', 'mocassin', 0xF0EEE8, sole=0xC9B48A, metal=GOLD, trim=GOLD, overlay=0xD8D4CA, gloss=0xFFFFFF),
    SP('costard_gris', 'derby', 0x1A1A1C, sole=0x101012, lace=0x101012, overlay=0x111113, gloss=0x8A8A92),
    SP('smoking', 'derby', 0x0E0E10, matiere='vernis', sole=0x0A0A0C, richelieu=True, lace=0x0A0A0C, overlay=0x070708, gloss=0xD8D8E0),
    SP('robe_soiree_rouge', 'escarpin', 0x141416, matiere='vernis', sole=0xC8101E, heel=0x141416, gloss=0xC8C8D0),
    SP('robe_soiree_noire', 'sandale', 0xD9AE3E, matiere='vernis', sole=0x2A2420, heel=0xD9AE3E, strap=0xD9AE3E, trim=0xF2DE9A),
    SP('robe_cocktail', 'escarpin', 0xC4C8CE, matiere='vernis', sole=0x2A2A2E, heel=0xC4C8CE, gloss=0xFFFFFF, bride=True, strap=0xC4C8CE),
]


def S(id, fr, piece, shape, paint, sil, **p):
    return C(id, fr, fr, 'secours', shape, piece=piece, paint=paint, sil=sil, icon=icon_secours, **p)


SECOURS = [
    # pompiers : tenue de feu
    S('veste_feu_marine', 'Veste de feu bleu marine', 'chestplate', 'VESTE_FEU', paint_feu, 'veste', main=NAVY_SP, accent=HIVIS, light=REFL,
      second=0x2EC46A, dos='SAPEURS', dos2='POMPIERS', dos_fond=sh(NAVY_SP, .7), icon_bandes=(6, 11)),
    S('veste_feu_sable', 'Veste de feu sable', 'chestplate', 'VESTE_FEU', paint_feu, 'veste', main=SABLE, accent=HIVIS, light=REFL,
      second=0x2EC46A, dos='SAPEURS', dos2='POMPIERS', dos_fond=0x2A2620, icon_bandes=(6, 11)),
    S('surpantalon_feu_marine', 'Surpantalon de feu bleu marine', 'leggings', 'SURPANT', paint_overpants, 'pants', main=NAVY_SP, icon_bandes=(10,)),
    S('surpantalon_feu_sable', 'Surpantalon de feu sable', 'leggings', 'SURPANT', paint_overpants, 'pants', main=SABLE, icon_bandes=(10,)),
    S('bottes_feu', 'Bottes de feu', 'boots', 'SHOE_BOTTES_FEU', paint_shoe, 'bottes', main=0x1C1C20,
      shoe=dict(kind='botte', upper=0x1C1C20, matiere='caoutchouc', sole=0x101012, toe=0x2A2A2E, heel=0x2A2A2E, bande=True, logo_col=HIVIS,
                collar=0x141416, trim=0x2A2A2E)),
    S('parka_pompier', 'Parka pompier', 'chestplate', 'PARKA', paint_parka, 'veste', main=NAVY_SP, accent=HIVIS, light=REFL, second=sh(NAVY_SP, .7),
      dos='SAPEURS', dos2='POMPIERS', icon_bandes=(6, 10)),
    # pompiers : tenue de caserne
    S('polo_pompier', 'Polo de caserne pompier', 'chestplate', 'POLO2', paint_polo, 'polo', main=NAVY_SP, second=sh(NAVY_SP, .72), dos='SAPEURS',
      dos2='POMPIERS', dos_col=WHITE, emblème='texte', emblème_txt='SP', emblème_x=207, emblème_col=WHITE, drapeau=True),
    S('tshirt_pompier', 'T-shirt de caserne pompier', 'chestplate', None, paint_polo, 'polo', main=NAVY_SP, tee=True, dos='SAPEURS',
      dos2='POMPIERS', dos_col=WHITE, emblème='texte', emblème_txt='SP', emblème_x=207, emblème_col=WHITE, drapeau=True),
    S('pantalon_pompier', 'Pantalon de caserne pompier', 'leggings', 'CARGO', paint_caserne_pants, 'pants', main=NAVY_SP, pants='cargo',
      liserés=(218, 226), icon_bandes=(11,), icon_bande=REFL),
    # SAMU / ambulanciers
    S('veste_samu', 'Veste SAMU haute visibilité', 'chestplate', 'HIVIS', paint_hivis, 'veste', main=NAVY_SAMU, accent=HIVIS, light=REFL,
      dos='SAMU', dos_col=NAVY_SAMU, icon_haut=HIVIS, icon_coupe=7, icon_bandes=(7, 11), icon_bande=REFL),
    S('veste_ambulancier', 'Veste ambulancier', 'chestplate', 'HIVIS', paint_ambu, 'veste', main=NAVY_SAMU, accent=HIVIS, light=REFL,
      dos='AMBULANCE', dos_sy=2, icon_haut=HIVIS, icon_coupe=4, icon_bandes=(4, 12), icon_bande=REFL),
    S('polo_samu', 'Polo SAMU', 'chestplate', 'POLO2', paint_polo, 'polo', main=0xF2F2EE, second=NAVY_SAMU, yoke=NAVY_SAMU,
      liseré=0xC62828, dos='SAMU', dos_scale=3, dos_col=NAVY_SAMU, dos_y=184, emblème='texte'),
    S('pantalon_samu', 'Pantalon de secours SAMU', 'leggings', 'CARGO', paint_caserne_pants, 'pants', main=NAVY_SAMU, pants='cargo',
      liserés=(220, 230), icon_bandes=(10, 12), icon_bande=REFL),
    S('chaussures_intervention', "Chaussures d'intervention", 'boots', 'SHOE_CHAUSSURES_INTERVENTION', paint_shoe, 'chaussures', main=0x1C1C20,
      shoe=dict(kind='rangers', upper=0x161618, sole=0x101012, lace=0x1A1A1D, eyelet=0x4A4A50, toe=0x1E1E22, heel=0x1E1E22, lining=0x202024,
                collar=0x0E0E10)),
]
CLOTHES += SECOURS
HATS += [
    C('casque_f1', 'Casque F1 chromé', 'F1 firefighter helmet (chrome)', 'hat', 'F1', main=0xC9CFD6, main_hi=0xE6EAEE, light=0xA8AEB6,
      dark=0x1A1A1D, accent=HIVIS, second=0xA9AEB4, lens=0xC9A23A, lens_hi=0xF2DE9A, strap=0x1A1A1D, black=0x141416, white=0xFFF6D0),
    C('casque_f1_blanc', 'Casque F1 blanc', 'F1 firefighter helmet (white)', 'hat', 'F1', main=0xEEEEEA, main_hi=0xFAFAF7, light=0xD2D2CC,
      dark=0x1A1A1D, accent=HIVIS, second=0x2A2A2E, lens=0xC9A23A, lens_hi=0xF2DE9A, strap=0x1A1A1D, black=0x141416, white=0xFFF6D0),
    C('casquette_pompier', 'Casquette pompier', 'Firefighter cap', 'hat', 'CAP', main=NAVY_SP, light=WHITE, accent=0xC8202E),
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
        if o.get('radio', True):
            radio(t, 167, 168)                      # radio côté droit de la poitrine, micro vers l'épaule
        if o['sil'] == 'polo':
            ceinturon(t, o.get('metal_dark'), 244)  # le polo est rentré : le ceinturon se voit par-dessus
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
    P('pantalon_police', 'Pantalon Police', 'leggings', 'CARGO', paint_police_pants, 'pants', pants='cargo', liserés=()),
    # RAID (unité d'intervention) : tenue noire, logo PN, RAID dans le dos ; casque et gilet RAID dans ZeroContact
    S('blouson_raid', "Blouson d'intervention RAID", 'chestplate', 'BLOUSON_RAID', paint_pn(paint_blouson_police), 'veste', main=RAID_NOIR,
      dos='RAID', dos_scale=3, dos_col=WHITE, dark=sh(RAID_NOIR, .7), main_hi=sh(RAID_NOIR, 1.25), metal=SILVER_D, metal_dark=SILVER_D,
      icon_bandes=(10,), icon_bande=REFL),
    S('pantalon_raid', 'Pantalon RAID', 'leggings', 'CARGO', paint_police_pants, 'pants', main=RAID_NOIR, pants='cargo', liserés=()),
]
SHAPES['BLOUSON_RAID'] = lambda slim: [ring(-0.9, 0.6, .5, 'main_hi')] + sym([('body', 1.6, -0.36, -1.0, 3.9, 0.0, 1.0, 'dark')])
CLOTHES += POLICE
HATS += [
    C('casquette_police', 'Casquette Police', 'Casquette Police', 'hat', 'CAP', main=NAVY_PN, light=WHITE, accent=0x2B5FC8),
]

# ---------------------------------------------------------------- garde-robe RP (03/11) : travail, sport, soirée, bain, hiver, femme, basiques

FONT.update({'F': ["XXX", "X..", "XX.", "X..", "X.."], 'G': [".XX", "X..", "X.X", "X.X", ".XX"], 'V': ["X.X", "X.X", "X.X", "X.X", ".X."],
             'K': ["X.X", "X.X", "XX.", "X.X", "X.X"], 'Y': ["X.X", "X.X", ".X.", ".X.", ".X."], 'X': ["X.X", "X.X", ".X.", "X.X", "X.X"],
             '0': ["XXX", "X.X", "X.X", "X.X", "XXX"], '1': [".X.", "XX.", ".X.", ".X.", "XXX"], '2': ["XX.", "..X", ".X.", "X..", "XXX"],
             '3': ["XX.", "..X", ".X.", "..X", "XX."], '4': ["X.X", "X.X", "XXX", "..X", "..X"], '5': ["XXX", "X..", "XX.", "..X", "XX."],
             '6': [".XX", "X..", "XXX", "X.X", "XXX"], '7': ["XXX", "..X", ".X.", ".X.", ".X."], '8': ["XXX", "X.X", "XXX", "X.X", "XXX"],
             '9': ["XXX", "X.X", "XXX", "..X", "XX."]})
TISSU = {'coton': dict(noise=.04, grad=(1.02, .92)), 'chine': dict(noise=.03, heather=.07), 'satin': dict(noise=.01, sheen=.3),
         'jean': dict(noise=.04, twill=.05), 'laine': dict(noise=.06), 'nylon': dict(noise=.015, sheen=.14, grad=(1.04, .9)),
         'cuir': dict(noise=.03, sheen=.25, grad=(1.1, .85)), 'lin': dict(noise=.05, twill=.02), 'toile': dict(noise=.03, twill=.04),
         'lycra': dict(noise=.015, sheen=.22, grad=(1.06, .88))}
ORANGE_HV = 0xF06A1A


def U(u):
    """Unité du membre (0 en haut, 12 en bas) -> ligne de la texture 512 x 256 (faces latérales du torse, des bras et des jambes)."""
    return int(round(160 + 8 * u))


def tissu(o):
    return dict(TISSU[o.get('tissu', 'coton')], heather=o.get('heather', TISSU[o.get('tissu', 'coton')].get('heather', 0)))


def cut(t, poly):
    """Découpe (transparent : la peau ou le skin dessous se voit)."""
    mk = Image.new('L', (512, 256), 0)
    ImageDraw.Draw(mk).polygon(poly, fill=255)
    t.a[np.array(mk) > 0] = 0


def fill_top(t, m, sleeve=12, crop=12, **kw):
    """Torse (jusqu'à crop unités) et manches (longueur sleeve, 0 = sans manches)."""
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 160, x1, U(crop)), m, **kw)
    t.fill(BODY['top'], m, **kw)
    if sleeve:
        for k in SLEEVES:
            x0, _, x1, _ = ARM[k]
            t.fill((x0, 160, x1, U(sleeve)), m, **kw)
        t.fill(ARM['top'], m, **kw)
        if sleeve >= 12:
            t.fill(ARM['bot'], sh(m, .7))


def hem(t, keys, d, y, f=.84, h=4, rib=False):
    for k in keys:
        x0, _, x1, _ = d[k]
        t.mul((x0, y - h, x1, y), f)
        if rib:
            t.ribs((x0, y - h, x1, y), .85)


def flowers(t, rnd, cols, leaf, n, area=(128, 160, 448, 256), size=3):
    """Motif hawaïen : fleurs à 5 pétales et feuilles, seulement sur le tissu déjà peint."""
    im = t.img()
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = area
    for i in range(n):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        if i % 3 == 0:
            a = rnd.uniform(0, math.pi)
            dx, dy = math.cos(a) * size * 2.2, math.sin(a) * size * 2.2
            d.polygon([(x - dx, y - dy), (x - dy * .35, y + dx * .35), (x + dx, y + dy), (x + dy * .35, y - dx * .35)], fill=rgb(leaf))
        else:
            c = rgb(cols[i % len(cols)])
            for p in range(5):
                a = p * 2 * math.pi / 5
                px_, py_ = x + math.cos(a) * size * .8, y + math.sin(a) * size * .8
                d.ellipse((px_ - size * .6, py_ - size * .6, px_ + size * .6, py_ + size * .6), fill=c)
            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=rgb(0xF2C230))
    arr = np.array(im, np.float32)
    keep = t.a[..., 3] > 0
    t.a[keep] = arr[keep]


def plaid(t, area, c1, c2, step=16):
    """Chemise à carreaux (flanelle) : bandes sombres croisées et fins filets clairs."""
    x0, y0, x1, y1 = area
    for x in range(x0, x1, step):
        t.mul((x, y0, x + 5, y1), .62)
        t.a[y0:y1, x + 9:x + 10, :3] = np.clip(t.a[y0:y1, x + 9:x + 10, :3] * .4 + np.array(rgb(c2), np.float32) * .6, 0, 255)
    for y in range(y0, y1, step):
        t.mul((x0, y, x1, y + 5), .66)
        t.a[y + 9:y + 10, x0:x1, :3] = np.clip(t.a[y + 9:y + 10, x0:x1, :3] * .4 + np.array(rgb(c1), np.float32) * .6, 0, 255)
    t.a[t.a[..., 3] == 0] = 0


def sparkles(t, area, rnd, col, n):
    """Paillettes : points brillants et sombres."""
    x0, y0, x1, y1 = area
    hi, lo = np.array(rgb(mix(col, 0xFFFFFF, .7)), np.float32), np.array(rgb(sh(col, .5)), np.float32)
    for _ in range(n):
        x, y = rnd.randrange(x0, x1 - 1), rnd.randrange(y0, y1 - 1)
        if t.a[y, x, 3] > 0:
            t.a[y, x, :3] = hi if rnd.random() < .55 else lo
            if rnd.random() < .2:
                t.a[y, x + 1, :3] = hi


def number(t, x, y, s, col, scale, outline=None):
    w = text_w(s, scale)
    if outline is not None:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            text(t, x - w // 2 + dx, y + dy, s, outline, scale)
    text(t, x - w // 2, y, s, col, scale)


# ---- hauts (calque 1)

def paint_tee(o, t):
    """T-shirts, débardeurs, crop tops, tops à bretelles, brassière, maillots de sport, maillot de bain une pièce."""
    m, kw = o['main'], tissu(o)
    sleeve, crop, col = o.get('manches', 3.5), o.get('court', 12), o.get('col', 'rond')
    fill_top(t, m, sleeve, crop, **kw)
    if o.get('côtes'):
        for k in TORSO:
            t.ribs(BODY[k], .9)
    if o.get('rayures') is not None:
        for y in range(166, U(crop), 12):
            for k in TORSO:
                x0, _, x1, _ = BODY[k]
                t.fill((x0, y, x1, y + 4), o['rayures'], **kw)
    if o.get('empiècement') is not None:            # épaules / manches contrastées (maillots)
        for k in TORSO:
            x0, _, x1, _ = BODY[k]
            t.fill((x0, 160, x1, 172), o['empiècement'], **kw)
        if sleeve:
            for k in SLEEVES:
                x0, _, x1, _ = ARM[k]
                t.fill((x0, 160, x1, U(sleeve)), o['empiècement'], **kw)
            t.fill(ARM['top'], o['empiècement'])
    hem(t, TORSO, BODY, U(crop), .86, 4, rib=crop < 12)
    if sleeve:
        hem(t, SLEEVES, ARM, U(sleeve), .82, 4, rib=sleeve >= 12)
    tr = o.get('liseré')
    if tr is not None and sleeve:
        for k in SLEEVES:
            x0, _, x1, _ = ARM[k]
            t.rect((x0, U(sleeve) - 5, x1, U(sleeve) - 3), tr)
    if tr is not None and o.get('bandes_côtés'):
        for k in ('R', 'L'):
            x0, _, x1, _ = BODY[k]
            t.rect((x0 + 12, 160, x0 + 20, U(crop)), tr)
    nk = rgb(o.get('col_col', sh(m, .7)))

    def det(d):
        if col == 'rond':
            d.ellipse((176, 150, 208, 170), fill=nk); d.ellipse((180, 148, 204, 166), fill=sh(nk, .8))
        elif col == 'v':
            d.polygon([(178, 160), (206, 160), (192, 182)], fill=nk); d.polygon([(182, 160), (202, 160), (192, 176)], fill=sh(m, .55))
        elif col == 'polo':
            d.rectangle((186, 160, 198, 188), fill=nk)
            for y in (168, 180):
                d.ellipse((190, y - 2, 194, y + 2), fill=rgb(WHITE))
        if o.get('logo') == 'swoosh':
            d.polygon([(214, 172), (211, 177), (203, 178), (209, 175)], fill=rgb(o.get('logo_col', WHITE)))
        if o.get('poche'):
            d.rectangle((203, 172, 215, 186), outline=sh(m, .72))
    draw_on(t, det)
    if o.get('devant'):
        s, sc = o['devant'], o.get('devant_scale', 1)
        text(t, 192 - text_w(s, sc) // 2, o.get('devant_y', 178), s, o.get('devant_col', WHITE), sc)
    if o.get('numero'):
        oc = o.get('numero_contour')
        number(t, 288, 176, o['numero'], o.get('numero_col', WHITE), 4, oc)
        number(t, 192, 196 if o.get('devant') else 182, o['numero'], o.get('numero_col', WHITE), 2, oc)
    back_text(t, o, o.get('dos_y', 166))
    # découpes : encolures profondes, emmanchures, bretelles, échancrures
    if col in ('debardeur', 'bretelles', 'bustier', 'brassiere', 'une_piece'):
        if col == 'debardeur':
            cut(t, [(174, 160), (210, 160), (204, 176), (192, 182), (180, 176)])
            cut(t, [(270, 160), (306, 160), (300, 170), (276, 170)])
        if col in ('bretelles', 'une_piece', 'brassiere'):
            for (x0, x1, a, b) in ((160, 224, 168, 214), (256, 320, 264, 310)):
                cut(t, [(x0, 160), (a, 160), (a, U(1.6)), (x0, U(1.6))]); cut(t, [(a + 4, 160), (b, 160), (b, U(1.6)), (a + 4, U(1.6))])
                cut(t, [(b + 4, 160), (x1, 160), (x1, U(1.6)), (b + 4, U(1.6))])
            cut(t, [(178, U(1.6)), (206, U(1.6)), (192, U(3.2))])
            if col == 'brassiere':
                cut(t, [(268, U(1.6)), (308, U(1.6)), (300, U(5)), (276, U(5))])        # dos nageur
        if col == 'bustier':
            for k in TORSO:
                x0, _, x1, _ = BODY[k]
                cut(t, [(x0, 160), (x1, 160), (x1, U(2.2)), (x0, U(2.2))])
        for k in ('R', 'L'):
            x0, _, x1, _ = BODY[k]
            cut(t, [(x0, 160), (x1, 160), (x1, U(2.6)), (x0, U(2.6))])
        cut(t, [(160, 128), (224, 128), (224, 160), (160, 160)])
        if col == 'une_piece':                                            # échancrure haute sur les hanches
            for (x0, x1) in ((160, 224), (256, 320)):
                cut(t, [(x0, 256), (x0 + 22, 256), (x0, U(9.2))]); cut(t, [(x1, 256), (x1 - 22, 256), (x1, U(9.2))])
            for k in ('R', 'L'):
                x0, _, x1, _ = BODY[k]
                cut(t, [(x0, U(9.4)), (x1, U(9.4)), (x1, 256), (x0, 256)])


def paint_chemise(o, t):
    """Chemises : blanche, hawaïenne (col ouvert), à carreaux ; manches longues, courtes ou retroussées."""
    m, kw = o['main'], tissu(o)
    sleeve = o.get('manches', 12)
    fill_top(t, m, sleeve, 12, **kw)
    rnd = random.Random(hash(o['id']) % 1000)
    if o.get('motif') == 'hawaii':
        flowers(t, rnd, o['fleurs'], o['feuille'], 95)
    elif o.get('motif') == 'carreaux':
        plaid(t, (128, 128, 448, 256), o['filet1'], o['filet2'])
    if sleeve >= 12:
        for k in SLEEVES:
            x0, _, x1, _ = ARM[k]
            t.fill((x0, 244, x1, 256), sh(m, .95), noise=.02)                          # poignets
            t.rect((x0, 244, x1, 245), sh(m, .7))
    elif sleeve > 4:
        hem(t, SLEEVES, ARM, U(sleeve), .82, 7)                                       # manches retroussées
    else:
        hem(t, SLEEVES, ARM, U(sleeve), .86, 3)
    hem(t, TORSO, BODY, 256, .9, 2)
    sc = rgb(o.get('col_col', sh(m, .86)))

    def det(d):
        d.line([(192, 160), (192, 256)], fill=sh(m, .7))                             # patte de boutonnage
        for y in range(170, 252, 14):
            d.ellipse((193, y - 2, 197, y + 2), fill=rgb(o.get('bouton', 0xE8E4DA)), outline=sh(m, .6))
        if not o.get('ouverte'):
            d.polygon([(176, 160), (191, 160), (186, 172)], fill=sc, outline=sh(sc, .7))   # pointes de col
            d.polygon([(208, 160), (193, 160), (198, 172)], fill=sc, outline=sh(sc, .7))
        else:
            d.polygon([(172, 160), (184, 160), (192, 186), (184, 182)], fill=sc, outline=sh(sc, .7))   # col camp, revers
            d.polygon([(212, 160), (200, 160), (192, 186), (200, 182)], fill=sc, outline=sh(sc, .7))
        if o.get('poche', True):
            d.rectangle((202, 176, 214, 190), outline=sh(m, .68))
        if sleeve >= 12:
            for k in ('O',):
                x0 = ARM[k][0]
                d.ellipse((x0 + 14, 248, x0 + 17, 251), fill=rgb(o.get('bouton', 0xE8E4DA)))
    draw_on(t, det)
    if o.get('ouverte'):
        cut(t, [(184, 160), (200, 160), (192, 184)])                                  # col ouvert : la peau se voit


def paint_btp(o, t):
    """Gilet de chantier haute visibilité sur un t-shirt : bandes réfléchissantes, bretelles, poches, BTP dans le dos."""
    m, tee = o['main'], o.get('tee', 0x2A2A2E)
    fill_top(t, tee, 3.5, 12, noise=.04)
    hem(t, SLEEVES, ARM, U(3.5), .84, 3)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 160, x1, 256), m, noise=.02, grad=(1.06, .94))
    t.fill(BODY['top'], m)
    for y in (U(6.2), U(9.6)):
        band(t, TORSO, BODY, y, 8, hivis=None)
    for x in (166, 210, 262, 306):
        t.fill((x, 160, x + 8, U(6.2)), REFL, noise=.01, sheen=.35)                    # bretelles réfléchissantes

    def det(d):
        d.line([(192, 160), (192, 256)], fill=sh(m, .6), width=2)
        d.polygon([(180, 160), (204, 160), (192, 174)], fill=rgb(tee))
        for x in (164, 204):
            d.rectangle((x, 220, x + 16, 240), outline=sh(m, .6))
            d.line([(x, 224), (x + 16, 224)], fill=sh(m, .6))
        d.rectangle((166, 182, 176, 192), outline=sh(m, .6))                          # porte-badge
    draw_on(t, det)
    back_text(t, o, 214, 3)


def paint_mecano(o, t):
    """Veste de bleu de travail : empiècement contrasté, poches à rabat, écusson, GARAGE dans le dos."""
    m, c2 = o['main'], o.get('second', 0x5A5E66)
    fill_top(t, m, 12, 12, noise=.03, twill=.03)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 160, x1, 180), c2, noise=.03, twill=.03)
    for k in SLEEVES:
        x0, _, x1, _ = ARM[k]
        t.fill((x0, 160, x1, 184), c2, noise=.03, twill=.03)
    t.fill(ARM['top'], c2)
    hem(t, SLEEVES, ARM, 256, .8, 6, rib=True)
    hem(t, TORSO, BODY, 256, .85, 6)
    rnd = random.Random(5)
    for _ in range(40):                                                            # taches de cambouis
        x, y = rnd.randrange(130, 446), rnd.randrange(186, 252)
        if t.a[y, x, 3] > 0:
            t.mul((x, y, x + rnd.randint(1, 3), y + rnd.randint(1, 2)), .55)

    def det(d):
        d.line([(180, 180), (320, 180)], fill=rgb(o.get('passepoil', 0xE07A1E)), width=1)
        d.line([(192, 160), (192, 256)], fill=rgb(SILVER_D), width=2)
        for x in (166, 200):
            d.rectangle((x, 188, x + 18, 208), outline=sh(m, .62)); d.rectangle((x, 188, x + 18, 194), fill=sh(m, .82))
        d.ellipse((166, 166, 186, 176), fill=rgb(WHITE), outline=rgb(0xC8202A))           # écusson nominatif
        d.line([(170, 171), (182, 171)], fill=rgb(0x1A2A50))
    draw_on(t, det)
    back_text(t, o, 192, 2)


def paint_chef(o, t):
    """Veste de cuisinier : croisée, deux rangs de boutons boules, col officier à liseré tricolore, manches retroussées."""
    m = o['main']
    fill_top(t, m, 12, 12, noise=.03, twill=.02)
    for k in SLEEVES:
        x0, _, x1, _ = ARM[k]
        t.fill((x0, 236, x1, 248), sh(m, .94), noise=.02)                              # revers de manche
        t.rect((x0, 236, x1, 237), sh(m, .75))
    hem(t, TORSO, BODY, 256, .9, 3)

    def det(d):
        d.polygon([(172, 160), (224, 160), (224, 256), (172, 256)], fill=sh(m, .97))
        d.line([(172, 166), (172, 256)], fill=sh(m, .78))                            # bord du croisé
        for y in (176, 194, 212, 230):
            for x in (180, 212):
                d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=rgb(0x1A1A1D), outline=rgb(0x3A3A40))
        for i, c in enumerate((0x1F3F9E, WHITE, 0xC8202A)):
            d.line([(160, 161 + i), (224, 161 + i)], fill=rgb(c))
        d.line([(256, 161), (320, 161)], fill=rgb(0x1F3F9E)); d.line([(256, 162), (320, 162)], fill=rgb(WHITE)); d.line([(256, 163), (320, 163)], fill=rgb(0xC8202A))
    draw_on(t, det)
    text(t, 198, 184, 'CHEF', rgb(0x1F3F9E), 1)


def paint_serveur(o, t):
    """Tenue de serveur : chemise blanche, gilet noir boutonné (dos en satin à patte de serrage), nœud papillon."""
    shirt, vest = o.get('chemise', 0xF2F2EE), o['main']
    fill_top(t, shirt, 12, 12, noise=.03)
    hem(t, SLEEVES, ARM, 256, .9, 6)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, U(1.0), x1, 256), vest, noise=.03, twill=.03)
    t.fill((256, U(1.0), 320, 256), sh(vest, 1.2), noise=.01, sheen=.3)                 # dos satiné
    cut_v = [(176, U(1.0)), (208, U(1.0)), (192, U(6.5))]

    def det(d):
        d.polygon(cut_v, fill=rgb(shirt))
        d.line([(192, U(6.5)), (192, 256)], fill=sh(vest, .6))
        for y in (U(7), U(8.4), U(9.8)):
            d.ellipse((194, y - 2, 198, y + 2), fill=rgb(0x3A3A40))
        d.line([(166, U(8.6)), (178, U(8.6))], fill=sh(vest, .55)); d.line([(206, U(8.6)), (218, U(8.6))], fill=sh(vest, .55))
        d.line([(192, U(1)), (192, U(6))], fill=sh(shirt, .8))
        d.rectangle((272, U(8.5), 304, U(9.2)), fill=sh(vest, .9)); d.rectangle((286, U(8.4), 290, U(9.3)), fill=rgb(SILVER))
        d.polygon([(184, 160), (190, 164), (184, 168)], fill=rgb(o.get('noeud', 0x141416)))
        d.polygon([(200, 160), (194, 164), (200, 168)], fill=rgb(o.get('noeud', 0x141416)))
    draw_on(t, det)


def paint_livreur(o, t):
    """Veste de livreur : orange et noir, matelassage léger, passepoils réfléchissants, LIVRAISON dans le dos."""
    m, c2 = o['main'], o.get('second', 0x1C1C20)
    fill_top(t, m, 12, 12, noise=.015, sheen=.1)
    for k in SLEEVES:
        x0, _, x1, _ = ARM[k]
        t.fill((x0, U(6), x1, 256), c2, noise=.015, sheen=.1)
    for k in ('R', 'L'):
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 160, x1, 256), c2, noise=.015, sheen=.1)
    for y in range(176, 250, 12):
        for k in TORSO:
            x0, _, x1, _ = BODY[k]
            t.mul((x0, y, x1, y + 1), .8)
    hem(t, SLEEVES, ARM, 256, .8, 6, rib=True)
    hem(t, TORSO, BODY, 256, .8, 6, rib=True)

    def det(d):
        for (x0, x1) in ((160, 224), (256, 320)):
            d.line([(x0, U(6)), (x1, U(6))], fill=rgb(REFL), width=2)
        for k in SLEEVES:
            x0 = ARM[k][0]
            d.line([(x0, U(6)), (x0 + 32, U(6))], fill=rgb(REFL), width=2)
        d.line([(192, 160), (192, 256)], fill=rgb(SILVER_D), width=2)
        d.rectangle((190, 166, 194, 174), fill=rgb(SILVER))
    draw_on(t, det)
    back_text(t, o, 196, 1)
    text(t, 202, 172, 'MN', o.get('dos_col', WHITE), 1, glyphs=COMPACT)


def paint_miami(o, t):
    """Costume Miami pastel : veste ouverte sur un t-shirt, manches retroussées, revers, pochette."""
    m, tee = o['main'], o.get('tee', 0xF2F2EE)
    fill_top(t, m, 9.5, 12, noise=.04, twill=.02)
    for k in SLEEVES:
        x0, _, x1, _ = ARM[k]
        t.fill((x0, U(8.6), x1, U(9.5)), sh(m, .9), noise=.02)                        # manche retroussée
        t.rect((x0, U(8.6), x1, U(8.6) + 1), sh(m, .7))
    hem(t, TORSO, BODY, 256, .9, 3)

    def det(d):
        d.polygon([(180, 160), (204, 160), (198, 256), (186, 256)], fill=rgb(tee))       # t-shirt dessous
        d.ellipse((182, 154, 202, 166), fill=sh(tee, .8))
        lap = sh(m, .9)
        d.polygon([(170, 160), (180, 160), (188, 214), (184, 214), (172, 180)], fill=lap, outline=sh(m, .65))
        d.polygon([(214, 160), (204, 160), (196, 214), (200, 214), (212, 180)], fill=lap, outline=sh(m, .65))
        d.ellipse((199, 216, 203, 220), fill=sh(m, .55))
        d.line([(166, 230), (180, 230)], fill=sh(m, .7)); d.line([(204, 230), (218, 230)], fill=sh(m, .7))
        d.polygon([(206, 180), (216, 180), (214, 176), (210, 178), (207, 176)], fill=rgb(o.get('pochette', WHITE)))
        d.line([(288, 236), (288, 256)], fill=sh(m, .7))
    draw_on(t, det)


def paint_robe_haut(o, t):
    """Haut de robe : paillettes (bustier) ou moulante à bretelles, fronces."""
    m = o['main']
    fill_top(t, m, 0, 12, **tissu(o))
    rnd = random.Random(9)
    if o.get('paillettes'):
        sparkles(t, (128, 160, 320, 256), rnd, m, 2600)

    def det(d):
        if o.get('fronces'):
            for i in range(7):
                d.line([(162, 176 + i * 11), (222, 168 + i * 11)], fill=sh(m, .78))
    draw_on(t, det)
    for (x0, x1) in ((160, 224), (256, 320)):
        if o.get('bustier'):                                                     # bustier : décolleté en cœur devant
            d0 = U(2.0)
            cut(t, [(x0, 160), (x1, 160), (x1, d0), (x0 + (x1 - x0) // 2, d0 + (6 if x0 == 160 else 0)), (x0, d0)])
        else:
            cut(t, [(x0, 160), (x0 + 8, 160), (x0 + 8, U(1.5)), (x0, U(1.5))]); cut(t, [(x1 - 8, 160), (x1, 160), (x1, U(1.5)), (x1 - 8, U(1.5))])
            cut(t, [(x0 + 12, 160), (x1 - 12, 160), (x1 - 12, U(1.5)), (x0 + 12, U(1.5))])
            cut(t, [(x0 + 16, U(1.5)), (x1 - 16, U(1.5)), (x0 + 32, U(3.4))])
    for k in ('R', 'L'):
        x0, _, x1, _ = BODY[k]
        cut(t, [(x0, 160), (x1, 160), (x1, U(2.4)), (x0, U(2.4))])
    cut(t, [(160, 128), (224, 128), (224, 160), (160, 160)])


def paint_parka_fourrure(o, t):
    """Parka d'hiver : capuche bordée de fausse fourrure (relief), poches à rabat, cordon de serrage, boutons-pressions."""
    m = o['main']
    fill_top(t, m, 12, 12, noise=.025, twill=.03)
    hem(t, SLEEVES, ARM, 256, .78, 6, rib=True)

    def det(d):
        e = sh(m, .6)
        d.line([(192, 160), (192, 256)], fill=e, width=2)
        for y in (172, 196, 220, 244):
            d.ellipse((188, y - 2, 192, y + 2), fill=rgb(SILVER_D))
        for x in (164, 202):
            d.rectangle((x, 222, x + 18, 246), outline=e); d.rectangle((x, 222, x + 18, 228), fill=sh(m, .85))
            d.rectangle((x, 182, x + 16, 198), outline=e)
        for (x0, x1) in ((128, 160), (160, 224), (224, 256), (256, 320)):
            d.line([(x0, 212), (x1, 212)], fill=e)
        d.line([(182, 212), (180, 220)], fill=rgb(0xE8DCC0)); d.line([(202, 212), (204, 220)], fill=rgb(0xE8DCC0))
        d.rectangle((328, 180, 344, 190), fill=sh(m, .8))
    draw_on(t, det)


# ---- bas (calque 2)

def legs_fill(t, m, L=12, **kw):
    for k in LEGS4:
        x0, _, x1, _ = LEG[k]
        t.fill((x0, 160, x1, U(L)), m, **kw)
    t.fill(LEG['top'], m, **kw)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 232, x1, 256), m, **kw)


def paint_short(o, t):
    """Shorts et bermudas : jean effiloché, sport à bandes, cargo, bain à motif."""
    m, L, kind = o['main'], o.get('long', 5), o.get('short', 'sport')
    if kind in ('jean', 'cargo'):
        paint_pants(dict(o, pants=kind), t)
        for k in LEGS4:
            x0, _, x1, _ = LEG[k]
            t.clear((x0, U(L), x1, 256))
        if kind == 'jean':
            rnd = random.Random(2)
            for k in LEGS4:
                x0, _, x1, _ = LEG[k]
                for x in range(x0, x1):
                    for y in range(U(L) - 3, U(L) + rnd.randint(0, 3)):
                        t.a[y, x] = (*rgb(0xE8E4DA), 255) if y >= U(L) - 1 else t.a[y, x]
        else:
            hem(t, LEGS4, LEG, U(L), .82, 4)
        return
    legs_fill(t, m, L, **tissu(o))
    if o.get('motif') == 'flamants':
        flowers(t, random.Random(4), [0xF29AB8, 0xE86FA0], 0x1E7A3C, 70, (0, 160, 128, U(L)), 3)
        flowers(t, random.Random(5), [0xF29AB8], 0x1E7A3C, 30, (128, 232, 320, 256), 3)
    hem(t, LEGS4, LEG, U(L), .84, 3)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.mul((x0, 232, x1, 240), .82); t.ribs((x0, 232, x1, 240), .85)              # taille élastique
    if o.get('bandes') is not None:
        for k in ('O', 'I'):
            x0 = LEG[k][0]
            t.rect((x0 + 12, 160, x0 + 15, U(L)), o['bandes']); t.rect((x0 + 17, 160, x0 + 20, U(L)), o['bandes'])

    def det(d):
        d.line([(189, 240), (187, 250)], fill=rgb(WHITE), width=2); d.line([(195, 240), (197, 250)], fill=rgb(WHITE), width=2)
    draw_on(t, det)
    if o.get('numero'):
        text(t, 8, 168, o['numero'], o.get('numero_col', WHITE), 2)


def paint_jupe(o, t):
    """Jupes : plissée, mini en cuir, longue à paillettes, moulante."""
    m, L = o['main'], o.get('long', 4)
    legs_fill(t, m, L, **tissu(o))
    if o.get('plis'):
        for k in LEGS4:
            x0, _, x1, _ = LEG[k]
            for x in range(x0, x1, 6):
                t.mul((x, 160, x + 3, U(L)), .82); t.mul((x + 3, 160, x + 4, U(L)), 1.12)
        for k in TORSO:
            x0, _, x1, _ = BODY[k]
            for x in range(x0, x1, 6):
                t.mul((x, 240, x + 3, 256), .82)
    if o.get('paillettes'):
        sparkles(t, (0, 160, 128, U(L)), random.Random(3), m, 2600)
        sparkles(t, (128, 232, 320, 256), random.Random(4), m, 600)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.mul((x0, 232, x1, 238), .8)                                                 # ceinture
    hem(t, LEGS4, LEG, U(L), .8, 2)
    if o.get('zip'):
        t.rect((287, 236, 289, 256), SILVER)
    if o.get('fente'):
        for (x0, x1) in ((0, 32),):
            cut(t, [(x0 + 22, U(L)), (x0 + 30, U(L)), (x0 + 26, U(L) - 22)])


def paint_pantalon_costume(o, t):
    """Pantalon de costume : pli marqué devant, ceinture à passants, poches italiennes, ourlet."""
    m = o['main']
    legs_fill(t, m, 12, noise=.035, twill=.02)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 232, x1, 240), sh(m, .9), noise=.02)
    t.rect((47, 160, 49, 256), sh(m, 1.15)); t.rect((49, 160, 50, 256), sh(m, .82))     # pli
    t.rect((111, 160, 113, 256), sh(m, 1.1))
    hem(t, LEGS4, LEG, 256, .86, 3)

    def det(d):
        for x in (166, 182, 202, 218, 262, 288, 314):
            d.rectangle((x - 1, 231, x + 1, 241), fill=sh(m, .8))
        d.line([(192, 240), (192, 252)], fill=sh(m, .72))
        d.line([(162, 240), (170, 256)], fill=sh(m, .72)); d.line([(222, 240), (214, 256)], fill=sh(m, .72))
        d.line([(266, 246), (282, 246)], fill=sh(m, .7)); d.line([(294, 246), (310, 246)], fill=sh(m, .7))
    draw_on(t, det)


def paint_legging(o, t):
    m = o['main']
    legs_fill(t, m, 12, noise=.015, sheen=.22, grad=(1.06, .88))
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 228, x1, 256), m, noise=.015, sheen=.22)
        t.mul((x0, 228, x1, 236), .78)                                               # taille haute
    if o.get('bandes') is not None:
        for k in ('O', 'I'):
            x0 = LEG[k][0]
            t.rect((x0 + 14, 160, x0 + 18, 256), o['bandes'])


def paint_travail(o, t):
    """Pantalon de travail : cargo, genouillères, bandes haute visibilité, marteau à la ceinture (passant)."""
    paint_pants(dict(o, pants='cargo'), t)
    for k in ('F',):
        x0, _, x1, _ = LEG[k]
        t.fill((x0 + 4, U(5.2), x1 - 4, U(7.4)), sh(o['main'], .7), noise=.03)
    if o.get('bandes', True):
        band(t, LEGS4, LEG, U(9.6), 8, hivis=o.get('hivis', ORANGE_HV))
    if o.get('bretelles'):
        for x in (168, 210, 264, 304):
            t.fill((x, 232, x + 6, 256), sh(o['main'], .8))


def paint_pied_de_poule(o, t):
    """Pantalon de cuisinier : pied-de-poule noir et blanc, taille élastique, coupe ample."""
    legs_fill(t, o.get('fond', WHITE), 12, noise=.02)
    yy, xx = np.mgrid[0:256, 0:512]
    dent = ((xx // 4 + yy // 4) % 2 == 0) | (((xx // 4) % 2 == 1) & ((yy // 4) % 2 == 0) & (xx % 4 == 3 - yy % 4))   # carreau + dent
    zone = np.zeros((256, 512), bool)
    zone[160:256, 0:128] = True
    zone[232:256, 128:320] = True
    t.a[dent & zone & (t.a[..., 3] > 0), :3] = rgb(o['main'])
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 232, x1, 240), o['main'], noise=.02); t.ribs((x0, 232, x1, 240), .8)
    hem(t, LEGS4, LEG, 256, .85, 4)


def paint_tablier(o, t):
    """Tablier de serveur, long, sur un pantalon noir à pli : liens à la taille, poche à stylos."""
    m, apron = o['main'], o.get('tablier', 0x1C1C20)
    legs_fill(t, m, 12, noise=.03, twill=.03)
    for k in LEGS4:
        x0 = LEG[k][0]
        if k == 'F':
            t.rect((x0 + 15, 160, x0 + 17, 256), sh(m, 1.25))                            # pli du pantalon
    for k in ('F',):
        x0, _, x1, _ = LEG[k]
        t.fill((x0, 160, x1, U(9)), apron, noise=.025, twill=.04)
    for k in ('O', 'I'):
        x0, _, x1, _ = LEG[k]
        if k == 'O':
            t.fill((x0 + 18, 160, x1, U(9)), apron, noise=.025, twill=.04)
        else:
            t.fill((x0, 160, x0 + 14, U(9)), apron, noise=.025, twill=.04)
    t.fill((160, 232, 224, 256), apron, noise=.025, twill=.04)
    for k in TORSO:
        x0, _, x1, _ = BODY[k]
        t.fill((x0, 232, x1, 236), sh(apron, 1.4), noise=.02)                          # liens
    hem(t, ('F',), LEG, U(9), .7, 2)

    def det(d):
        d.rectangle((196, 240, 214, 252), outline=sh(apron, 1.6))
        d.line([(205, 240), (205, 252)], fill=sh(apron, 1.6))
    draw_on(t, det)


# ---- icônes 16 x 16

SIL.update({
    'tee': ["................", "....XX....XX....", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", "..XXXXXXXXXXXX..",
            "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
            "...XXXXXXXXXX...", "................", "................", "................"],
    'tank': ["................", "....XX....XX....", "....XX....XX....", "....XXX..XXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
             "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
             "...XXXXXXXXXX...", "................", "................", "................"],
    'crop': ["................", "................", "....XX....XX....", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", "..XXXXXXXXXXXX..",
             "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "................", "................", "................",
             "................", "................", "................", "................"],
    'brassiere': ["................", "................", "....X......X....", "....X......X....", "...XXX....XXX...", "...XXXXXXXXXX...",
                  "...XXXXXXXXXX...", "...XXXXXXXXXX...", "................", "................", "................", "................",
                  "................", "................", "................", "................"],
    'une_piece': ["................", "....X......X....", "....X......X....", "...XXX....XXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
                  "....XXXXXXXX....", "....XXXXXXXX....", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXX....XXX...", "....XX....XX....",
                  "................", "................", "................", "................"],
    'robe_haut': ["................", "................", "................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
                  "....XXXXXXXX....", "....XXXXXXXX....", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
                  "................", "................", "................", "................"],
    'jupe': ["................", "................", "................", "....XXXXXXXX....", "....XXXXXXXX....", "....XXXXXXXX....",
             "...XXXXXXXXXX...", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", "................", "................",
             "................", "................", "................", "................"],
    'jupe_longue': ["................", "....XXXXXXXX....", "....XXXXXXXX....", "....XXXXXXXX....", "....XXXXXXXX....", "...XXXXXXXXXX...",
                    "...XXXXXXXXXX...", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", ".XXXXXXXXXXXXXX.",
                    ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", "................", "................"],
    'short': ["................", "................", "................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...",
              "...XXXXX.XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "................", "................",
              "................", "................", "................", "................"],
    'veste_ouverte': ["................", "...XXXXXXXXXX...", "..XXXX....XXXX..", ".XXXXX....XXXXX.", ".XXXXXX..XXXXXX.", ".XXXXXX..XXXXXX.",
                      ".XXXXXX..XXXXXX.", ".XXXXXX..XXXXXX.", ".XXX.XX..XX.XXX.", ".XXX.XX..XX.XXX.", ".XXX.XXXXXX.XXX.", "....XXXXXXXX....",
                      "....XXXXXXXX....", "................", "................", "................"],
})


def icon_mode(o):
    """Icône 2D des nouveaux vêtements : silhouette ombrée + détails (bandes, col, motif)."""
    sil, m = SIL[o['sil']], o['main']
    rnd = random.Random(len(o['id']))
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(sil):
        for x, ch in enumerate(row):
            if ch != 'X':
                continue
            c = sh(m, 1.0 + (0.12 if x < 8 else -0.05) - y * 0.012)
            if o.get('icon_haut') is not None and y < o.get('icon_coupe', 4):
                c = rgb(o['icon_haut'])
            if y in o.get('icon_bandes', ()):
                c = rgb(o.get('icon_bande', REFL))
            if o.get('icon_centre') is not None and x in (7, 8) and 1 <= y <= 12:
                c = rgb(o['icon_centre'])
            if o.get('icon_motif') and rnd.random() < .3:
                c = rgb(rnd.choice(o['icon_motif']))
            if o.get('icon_rayures') is not None and y % 3 == 1:
                c = rgb(o['icon_rayures'])
            im.putpixel((x, y), c + (255,))
    out = im.copy()
    for y in range(16):
        for x in range(16):
            if im.getpixel((x, y))[3] == 0 and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and im.getpixel((x + dx, y + dy))[3]
                                                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out.putpixel((x, y), (16, 16, 16, 255))
    return out


# ---- formes 3D

def shape_chef(slim):
    b = [ring(-0.7, 0.6, .42, 'main_hi')]
    for y in (2.0, 4.25, 6.5, 8.75):
        for x in (-1.5, 2.5):
            b.append(('body', x - .3, y - .3, -2.45, x + .3, y + .3, -2.3, 'black'))
    return b


def shape_serveur(slim):
    return [('body', -1.25, 0.15, -2.68, -0.25, 1.15, -2.32, 'accent'), ('body', 0.25, 0.15, -2.68, 1.25, 1.15, -2.32, 'accent'),
            ('body', -0.3, 0.35, -2.76, 0.3, 0.95, -2.32, 'accent_dark')] + shape_polo(slim)


def shape_btp(slim):
    return sym([('body', 0.4, 7.4, -2.55, 3.3, 9.8, -2.3, 'main'), ('body', 0.4, 7.1, -2.6, 3.3, 7.6, -2.3, 'dark')]) + [ring(-0.4, 0.4, .4, 'main')]


def shape_livreur(slim):
    return [ring(-0.9, 0.7, .55, 'main_hi'), ('body', -3.3, -0.8, 2.45, 3.3, 2.3, 4.4, 'second'), ('body', -3.5, -1.0, 2.4, 3.5, -0.2, 4.6, 'dark')]


def shape_miami(slim):
    return sym([('body', 1.0, -0.2, -2.55, 2.7, 2.4, -2.3, 'main_hi'), ('body', 0.5, 2.4, -2.5, 1.7, 6.6, -2.3, 'main_hi')]) + \
        [('body', 1.9, 2.6, -2.62, 3.0, 3.2, -2.3, 'second')]


def shape_fourrure(slim):
    b = [ring(-1.0, 0.8, .6, 'main_hi'), ('body', -3.4, -0.7, 2.35, 3.4, 3.0, 4.5, 'main'),
         ('body', -3.9, -1.4, 2.1, 3.9, 0.3, 4.95, 'light'), ('body', -3.9, 0.3, 4.3, 3.9, 3.5, 4.95, 'light'),
         ('body', -3.9, 0.3, 2.1, -3.4, 3.5, 4.3, 'light'), ('body', 3.4, 0.3, 2.1, 3.9, 3.5, 4.3, 'light')]
    b += sym([('right_leg', -2.5, -0.4, -2.5, 2.5, 3.6, 2.5, 'main'), ('right_leg', -2.56, 3.2, -2.56, 2.56, 3.7, 2.56, 'dark')])
    return b


def shape_hardhat(slim):
    return [('head', -4.6, -8.6, -4.6, 4.6, -6.0, 4.6, 'main'), ('head', -4.1, -9.3, -4.1, 4.1, -8.6, 4.1, 'main'),
            ('head', -3.0, -9.7, -3.0, 3.0, -9.3, 3.0, 'main_hi'), ('head', -0.55, -9.95, -4.3, 0.55, -9.3, 4.3, 'light'),
            ('head', -5.0, -6.35, -5.4, 5.0, -5.9, 5.0, 'main'), ('head', -3.5, -6.45, -6.6, 3.5, -6.0, -5.4, 'main'),
            ('head', -4.65, -6.1, -4.65, 4.65, -5.6, 4.65, 'dark'), ('head', -1.2, -8.2, -4.68, 1.2, -7.0, -4.6, 'accent')]


def shape_toque(slim):
    b = [('head', -4.6, -8.6, -4.6, 4.6, -6.0, 4.6, 'main'), ('head', -4.65, -6.75, -4.65, 4.65, -6.35, 4.65, 'accent'),
         ('head', -5.2, -12.6, -5.2, 5.2, -8.6, 5.2, 'main_hi'), ('head', -4.6, -13.2, -4.6, 4.6, -12.6, 4.6, 'main')]
    for x in (-3.4, -1.15, 1.15, 3.4):
        b += [('head', x - .2, -12.5, -5.28, x + .2, -8.7, -5.2, 'light'), ('head', x - .2, -12.5, 5.2, x + .2, -8.7, 5.28, 'light')]
    return b


def shape_chapka(slim):
    return [('head', -4.7, -9.3, -4.7, 4.7, -7.2, 4.7, 'main'), ('head', -4.3, -9.7, -4.3, 4.3, -9.3, 4.3, 'main'),
            ('head', -4.95, -7.6, -5.05, 4.95, -5.6, -4.6, 'light'), ('head', -4.95, -7.6, 4.6, 4.95, -4.4, 5.0, 'light'),
            ('head', -5.0, -7.4, -3.0, -4.6, -2.4, 3.0, 'light'), ('head', 4.6, -7.4, -3.0, 5.0, -2.4, 3.0, 'light'),
            ('head', -4.98, -7.25, -4.6, 4.98, -6.9, 4.6, 'light')]


SHAPES.update({'CHEF': shape_chef, 'SERVEUR': shape_serveur, 'GILET_BTP': shape_btp, 'LIVREUR': shape_livreur, 'MIAMI': shape_miami,
               'FOURRURE': shape_fourrure, 'CASQUE_CHANTIER': shape_hardhat, 'TOQUE': shape_toque, 'CHAPKA': shape_chapka,
               'GENOUILLERES': lambda slim: shape_cargo(slim) + sym([('right_leg', -1.6, 5.2, -2.55, 1.6, 7.4, -2.25, 'dark'),
                                                                    ('right_leg', -1.7, 5.6, -2.6, 1.7, 6.0, -2.5, 'strap')]),
               'PLISSEE': lambda slim: sym([('right_leg', -2.45, 3.4, -2.45, 2.45, 4.0, 2.45, 'main')])})


def M(id, fr, piece, shape, paint, sil, **p):
    return C(id, fr, fr, 'mode', shape, piece=piece, paint=paint, sil=sil, icon=icon_mode, **p)


GARDEROBE = [
    # ---- travail
    M('gilet_chantier', 'Gilet de chantier haute visibilité', 'chestplate', 'GILET_BTP', paint_btp, 'tank', main=ORANGE_HV, tee=0x2A2A2E,
      dos='BTP', dos_col=0x1A1A1D, dark=sh(ORANGE_HV, .75), icon_bandes=(6, 9)),
    M('pantalon_travail', 'Pantalon de travail à genouillères', 'leggings', 'GENOUILLERES', paint_travail, 'pants', main=0x3A3D44,
      strap=0x1A1A1D, icon_bandes=(11,), icon_bande=ORANGE_HV),
    M('veste_mecano', 'Veste de mécanicien', 'chestplate', 'POLO2', paint_mecano, 'veste', main=0x1E2A4A, second=0x5A5E66, dos='GARAGE',
      dos_col=WHITE, icon_haut=0x5A5E66, icon_coupe=3),
    M('pantalon_mecano', 'Pantalon de mécanicien', 'leggings', 'CARGO', paint_travail, 'pants', main=0x1E2A4A, bandes=False, bretelles=True),
    M('veste_cuisinier', 'Veste de cuisinier', 'chestplate', 'CHEF', paint_chef, 'veste', main=0xF4F4F0, black=0x1A1A1D, icon_centre=0xE0E0DA),
    M('pantalon_cuisinier', 'Pantalon de cuisinier pied-de-poule', 'leggings', None, paint_pied_de_poule, 'pants', main=0x1A1A1D,
      icon_rayures=0xF2F2EE),
    M('tenue_serveur', 'Chemise et gilet de serveur', 'chestplate', 'SERVEUR', paint_serveur, 'veste', main=0x1C1C20, second=0xF2F2EE,
      accent=0x141416, icon_centre=0xF2F2EE),
    M('tablier_serveur', 'Pantalon et tablier de serveur', 'leggings', None, paint_tablier, 'pants', main=0x1E1E22),
    M('veste_livreur', 'Veste de livreur', 'chestplate', 'LIVREUR', paint_livreur, 'veste', main=0xF07A1A, second=0x1C1C20, dos='LIVRAISON',
      dos_col=WHITE, icon_bandes=(7,), icon_bande=REFL),
    # ---- sport
    M('maillot_foot', 'Maillot de foot MineNorth FC', 'chestplate', 'POLO2', paint_tee, 'tee', main=0x1F4FB0, col='v', col_col=WHITE,
      liseré=WHITE, bandes_côtés=True, numero='10', devant='MN', devant_y=176, second=WHITE, tissu='lycra', icon_haut=WHITE, icon_coupe=2),
    M('maillot_basket', 'Maillot de basket', 'chestplate', None, paint_tee, 'tank', main=0xC8202A, manches=0, col='debardeur', numero='23',
      numero_col=WHITE, numero_contour=0x141416, tissu='lycra', icon_bandes=(6,), icon_bande=WHITE),
    M('short_sport', 'Short de sport noir', 'leggings', None, paint_short, 'short', main=0x1C1C20, long=4.5, bandes=WHITE, tissu='lycra'),
    M('short_basket', 'Short de basket rouge', 'leggings', None, paint_short, 'short', main=0xC8202A, long=6, bandes=WHITE, tissu='lycra',
      numero='23'),
    M('brassiere_sport', 'Brassière de sport rose', 'chestplate', None, paint_tee, 'brassiere', main=0xE86FA0, manches=0, court=6,
      col='brassiere', tissu='lycra', logo='swoosh'),
    M('legging_sport', 'Legging de sport noir', 'leggings', None, paint_legging, 'pants', main=0x1A1A1E, bandes=0xE86FA0),
    # ---- soirée / cérémonie
    M('costume_miami_rose', 'Veste de costume Miami rose', 'chestplate', 'MIAMI', paint_miami, 'veste_ouverte', main=0xF2A6B8, tee=0xF2F2EE,
      pochette=0x2EC4C4, second=0x2EC4C4, icon_centre=0xF2F2EE),
    M('pantalon_miami_rose', 'Pantalon de costume Miami rose', 'leggings', None, paint_pantalon_costume, 'pants', main=0xF2A6B8),
    M('costume_miami_ciel', 'Veste de costume Miami bleu ciel', 'chestplate', 'MIAMI', paint_miami, 'veste_ouverte', main=0x9AD0EC,
      tee=0xF2F2EE, pochette=0xF2A6B8, second=0xF2A6B8, icon_centre=0xF2F2EE),
    M('pantalon_miami_ciel', 'Pantalon de costume Miami bleu ciel', 'leggings', None, paint_pantalon_costume, 'pants', main=0x9AD0EC),
    M('chemise_hawaienne', 'Chemise hawaïenne', 'chestplate', 'POLO2', paint_chemise, 'tee', main=0x1C8EA8, manches=3.5, ouverte=True,
      motif='hawaii', fleurs=[0xF26A8A, 0xF2F2EE, 0xF2C230], feuille=0x1E7A3C, col_col=0x1C8EA8, second=0x1C8EA8,
      icon_motif=[0xF26A8A, 0xF2F2EE, 0x1E7A3C]),
    M('chemise_hawaienne_rouge', 'Chemise hawaïenne rouge', 'chestplate', 'POLO2', paint_chemise, 'tee', main=0xB01B24, manches=3.5,
      ouverte=True, motif='hawaii', fleurs=[0xF2F2EE, 0xF2C230], feuille=0x1E5A3A, col_col=0xB01B24, second=0xB01B24,
      icon_motif=[0xF2F2EE, 0xF2C230]),
    M('chemise_blanche', 'Chemise blanche', 'chestplate', 'POLO2', paint_chemise, 'veste', main=0xF4F4F0, second=0xF4F4F0, poche=False),
    M('robe_paillettes', 'Robe bustier à paillettes argentée', 'chestplate', None, paint_robe_haut, 'robe_haut', main=0xB8BEC8, paillettes=True,
      bustier=True, tissu='satin'),
    M('jupe_paillettes', 'Jupe longue à paillettes argentée', 'leggings', None, paint_jupe, 'jupe_longue', main=0xB8BEC8, long=11.6,
      paillettes=True, tissu='satin', fente=True),
    M('robe_moulante', 'Robe moulante noire', 'chestplate', None, paint_robe_haut, 'robe_haut', main=0x141418, fronces=True, tissu='lycra'),
    M('jupe_moulante', 'Jupe moulante noire', 'leggings', None, paint_jupe, 'jupe', main=0x141418, long=4.5, tissu='lycra', zip=True),
    # ---- bain
    M('maillot_une_piece', 'Maillot de bain une pièce rouge', 'chestplate', None, paint_tee, 'une_piece', main=0xD01F2E, manches=0,
      col='une_piece', tissu='lycra'),
    M('short_bain_flamants', 'Short de bain flamants roses', 'leggings', None, paint_short, 'short', main=0x2EC4C4, long=5, motif='flamants',
      icon_motif=[0xF29AB8, 0x1E7A3C]),
    # ---- hiver
    M('parka_fourrure_kaki', 'Parka à capuche fourrée kaki', 'chestplate', 'FOURRURE', paint_parka_fourrure, 'veste', main=0x4E5636,
      light=0xD8CCB4, icon_haut=0xD8CCB4, icon_coupe=2),
    M('parka_fourrure_noire', 'Parka à capuche fourrée noire', 'chestplate', 'FOURRURE', paint_parka_fourrure, 'veste', main=0x1C1C20,
      light=0xC8C0B4, icon_haut=0xC8C0B4, icon_coupe=2),
    # ---- femme
    M('crop_top_blanc', 'Crop top blanc', 'chestplate', None, paint_tee, 'crop', main=0xF4F4F0, court=7, col='rond'),
    M('crop_top_noir', 'Crop top noir', 'chestplate', None, paint_tee, 'crop', main=0x1C1C20, court=7, col='rond'),
    M('top_bretelles', 'Top à bretelles satiné émeraude', 'chestplate', None, paint_tee, 'tank', main=0x1E6A4E, manches=0, col='bretelles', tissu='satin'),
    M('jupe_plissee', 'Jupe plissée écossaise', 'leggings', 'PLISSEE', paint_jupe, 'jupe', main=0x8A1E2A, long=4.2, plis=True,
      icon_rayures=0x1A2A50),
    M('mini_jupe_cuir', 'Mini-jupe en cuir noir', 'leggings', None, paint_jupe, 'jupe', main=0x1A1A1D, long=3.6, tissu='cuir', zip=True),
    M('jean_mom', 'Jean mom taille haute', 'leggings', None, paint_pants, 'pants', main=0x7A9AC8, pants='jean', stitch=0xC8873A),
    M('short_jean', 'Short en jean effiloché', 'leggings', None, paint_short, 'short', main=0x6A8AB8, long=3.6, short='jean', stitch=0xC8873A),
    # ---- basiques
    M('tshirt_blanc', 'T-shirt blanc', 'chestplate', None, paint_tee, 'tee', main=0xF4F4F0),
    M('tshirt_noir', 'T-shirt noir', 'chestplate', None, paint_tee, 'tee', main=0x1C1C20),
    M('tshirt_marine_raye', 'Marinière', 'chestplate', None, paint_tee, 'tee', main=0xF4F4F0, rayures=0x1A2A50, manches=12, icon_rayures=0x1A2A50),
    M('debardeur_blanc', 'Débardeur blanc côtelé', 'chestplate', None, paint_tee, 'tank', main=0xF2F2EE, manches=0, col='debardeur', côtes=True),
    M('chemise_carreaux', 'Chemise à carreaux en flanelle', 'chestplate', 'POLO2', paint_chemise, 'veste', main=0xA8202A, motif='carreaux',
      filet1=0xE8C040, filet2=0x1A1A1D, second=0x8A1A22, col_col=0x8A1A22, icon_rayures=0x3A1A1A),
    M('bermuda_cargo', 'Bermuda cargo beige', 'leggings', 'CARGO', paint_short, 'short', main=0xBFA982, long=7, short='cargo'),
]
CLOTHES += GARDEROBE
HATS += [
    C('casque_chantier', 'Casque de chantier jaune', 'Casque de chantier jaune', 'hat', 'CASQUE_CHANTIER', main=0xF2C230, light=0xF6D860,
      dark=0x2A2A2E, accent=ORANGE_HV),
    C('casque_chantier_blanc', 'Casque de chantier blanc', 'Casque de chantier blanc', 'hat', 'CASQUE_CHANTIER', main=0xEEEEEA,
      light=0xFAFAF7, dark=0x2A2A2E, accent=0x1F4FB0),
    C('toque_cuisinier', 'Toque de cuisinier', 'Toque de cuisinier', 'hat', 'TOQUE', main=0xF4F4F0, main_hi=0xFAFAF8, light=0xDCDCD6,
      accent=0x1F3F9E),
    C('chapka', 'Chapka en fausse fourrure', 'Chapka en fausse fourrure', 'hat', 'CHAPKA', main=0x2A2420, light=0x8A7A66),
    C('casquette_livreur', 'Casquette de livreur', 'Casquette de livreur', 'hat', 'CAP', main=0xF07A1A, light=0x1C1C20, accent=0x1C1C20),
]


# ---------------------------------------------------------------- chaussures vendues seules (03/11)

def CH(id, fr, kind, upper, **p):
    return C(id, fr, fr, 'chaussures', 'SHOE_' + id.upper(), piece='boots', paint=paint_shoe, main=upper, shoe=dict(kind=kind, upper=upper, **p))


CHAUSSURES = [
    # baskets
    CH('baskets_running_blanches', 'Baskets de running Nayk Air blanches', 'runner', 0xEEEEEC, matiere='maille', sole=0xF6F6F2,
       logo='swoosh', logo_col=0xE8641E, overlay=0xDCDCDA, lace=0xF2F2EE, heel=0xE8641E, liseré_relief=True, trim=0xE8641E),
    CH('baskets_running_noires', 'Baskets de running Nayk Air noires', 'runner', 0x1C1C20, matiere='maille', sole=0x1C1C20, tread=0x0E0E10,
       logo='swoosh', logo_col=0xF2F2EE, overlay=0x26262A, lace=0x1C1C20, trim=0x3A3A40),
    CH('baskets_new_grises', 'Baskets New Ballance grises', 'basket', 0x9A9DA2, matiere='daim', sole=0xEDEDE8, logo='n', logo_col=0xF2F2EE,
       overlay=0x7E8186, lace=0xC8CACE, heel=0x6E7176),
    CH('baskets_montantes_panda', 'Baskets montantes Jordane noir et blanc', 'montante', 0xF2F2EE, sole=0xF2F2EE, tread=0x141416, overlay=0x141416,
       heel=0x141416, collar=0x141416, logo='jump', logo_col=0x141416, lace=0xF2F2EE, trim=0x141416),
    CH('baskets_toile_noires', 'Baskets en toile Converso noires', 'toile', 0x1C1C20, matiere='toile', sole=0xF2F2EE, toe=0xF2F2EE,
       lace=0xF2F2EE, liseré=0x1C1C20, overlay=0x1C1C20, heel=0x1C1C20, logo='tab'),
    CH('baskets_chunky', 'Baskets chunky Balencio', 'chunky', 0xE8E2D4, matiere='nubuck', sole=0xF2EEE4, overlay=0x9A9DA2, heel=0xB01B24,
       second=0x7A7E86, trim=0x7A7E86, lace=0x9A9DA2, logo='n', logo_col=0x1A1A1D),
    CH('baskets_luxe_blanches', 'Baskets Guchi Ace blanches', 'basket', 0xF6F4EE, sole=0xF6F4EE, logo='web', logo_col=0xB01B24, trim=0x1E6B3A,
       overlay=0xF0EEE8, lace=0xF6F4EE, heel=0xD9AE3E),
    # chaussures de ville
    CH('mocassins_cognac', 'Mocassins à mors cognac', 'mocassin', 0x8A4E26, sole=0x3A2414, metal=GOLD, trim=GOLD, overlay=0x6A3A1C, gloss=0xD8A878),
    CH('mocassins_noirs', 'Mocassins à mors noirs', 'mocassin', 0x161618, sole=0x101012, metal=SILVER, trim=SILVER, overlay=0x0E0E10, gloss=0x8A8A92),
    CH('derbies_marron', 'Derbies en cuir marron', 'derby', 0x5A3420, sole=0x2A1A10, lace=0x2A1A10, overlay=0x46281A, gloss=0xB0805A),
    # talons
    CH('escarpins_noirs', 'Escarpins Loubouton noirs', 'escarpin', 0x141416, matiere='vernis', sole=0xC8101E, heel=0x141416, gloss=0xC8C8D0),
    CH('escarpins_rouges', 'Escarpins vernis rouges', 'escarpin', 0xB0121E, matiere='vernis', sole=0x1A1A1D, heel=0xB0121E, gloss=0xF2A0A8),
    CH('escarpins_nude', 'Escarpins nude à bride', 'escarpin', 0xD8B49A, sole=0x2A2420, heel=0xD8B49A, gloss=0xF4E2D4, bride=True, strap=0xD8B49A),
    CH('sandales_talons_argent', 'Sandales à talons argentées', 'sandale', 0xC4C8CE, matiere='vernis', sole=0x2A2A2E, heel=0xC4C8CE,
       strap=0xC4C8CE, trim=0xE8ECF0),
    # été
    CH('tongs_havaianna', 'Tongs Havaianna jaunes', 'tong', 0x1E8A4A, sole=0xF2C230, sole_dark=0x1E8A4A, strap=0x1E8A4A),
    CH('tongs_noires', 'Tongs noires', 'tong', 0x1C1C20, sole=0x1C1C20, sole_dark=0x3A3A40, strap=0x2A2A2E),
    CH('claquettes_nayk', 'Claquettes Nayk noires', 'claquette', 0x1C1C20, sole=0xF2F2EE, lining=0x1C1C20, logo='swoosh', logo_col=0xF2F2EE),
    CH('claquettes_guchi', 'Claquettes Guchi', 'claquette', 0xF0E8D8, sole=0x1C1C20, lining=0x1C1C20, logo='web', logo_col=0xB01B24),
    # bottes et boots
    CH('rangers_noires', 'Rangers en cuir noir', 'rangers', 0x161618, sole=0x101012, lace=0x1A1A1D, eyelet=0x4A4A50, toe=0x1E1E22,
       heel=0x1E1E22, lining=0x202024, collar=0x0E0E10),
    CH('boots_timberlande', 'Boots Timberlande', 'chantier', 0xC08A3E, matiere='nubuck', sole=0x5A3A22, tread=0x3A2414, lace=0x8A5A2A,
       eyelet=0xC9A24A, collar=0x4A2E18, toe=0xC08A3E, heel=0xC08A3E, lining=0xB07E36, fil=0xE0A040),
    CH('chelsea_noires', 'Bottines Chelsea noires', 'chelsea', 0x161618, sole=0x101012, trim=0x2A2A2E, collar=0x161618, gloss=0x8A8A92),
    CH('chelsea_daim', 'Bottines Chelsea en daim taupe', 'chelsea', 0x7A6A5A, matiere='daim', sole=0x2A1A10, trim=0x4A3A2A, collar=0x7A6A5A,
       gloss=0x9A8A7A),
    CH('santiags', 'Santiags en cuir', 'santiag', 0x6A3A1E, sole=0x2A1A10, heel=0x3A2414, collar=0x4A2814, overlay=0x4A2814, fil=0xE8D8B0,
       gloss=0xC08A5A),
    # hiver
    CH('apres_ski', 'Après-ski Moun Boot argentés', 'apres_ski', 0xBEC2C8, matiere='nylon', sole=0x2A2A2E, collar=0xA8ACB2, lace=0x1A1A1D,
       trim=0xB01B24, toe=0xBEC2C8, heel=0xBEC2C8, logo_col=0x1A1A1D),
    CH('bottes_fourrees', 'Bottes fourrées Ougg camel', 'fourree', 0xB88A5A, matiere='daim', sole=0xE8DCC8, lining=0xEDE4D2, toe=0xB88A5A,
       heel=0xB88A5A),
    # travail
    CH('chaussures_securite', 'Chaussures de sécurité', 'securite', 0x1C1C20, matiere='nubuck', sole=0x2A2A2E, tread=0x101012, toe=0x3A3A40,
       overlay=0x26262A, lace=0x1A1A1D, trim=HIVIS, heel=0x26262A),
    CH('sabots_cuisine', 'Sabots de cuisine Krocs blancs', 'sabot', 0xF2F2EE, matiere='caoutchouc', sole=0xF2F2EE, strap=0xF2F2EE, trim=0x9A9DA2),
    CH('sabots_noirs', 'Sabots de cuisine Krocs noirs', 'sabot', 0x1C1C20, matiere='caoutchouc', sole=0x1C1C20, strap=0x1C1C20, trim=0x5A5A60),
]
CLOTHES += CHAUSSURES


# ---------------------------------------------------------------- tenues de motard (04/11) : blousons, pantalons, gants, bottes, casques
# Marques parodiées façon GTA VI : Dayneze, Alpinestarz, Revite, Furygane (vêtements) ; Shoey, Araï, AGVE, Belle (casques).

FONT.update({'Z': ["XXX", "..X", ".X.", "X..", "XXX"], 'W': ["X...X", "X...X", "X.X.X", "XX.XX", "X...X"], 'J': ["..X", "..X", "..X", "X.X", ".X."]})


def paint_moto(o, t):
    """Blouson de moto (cuir ou textile) : empiècements contrastés, bandes de course, protections d'épaules et de coudes cousues, dorsale,
    soufflets d'aisance, col officier, fermeture, poignets à scratch, marque sur la poitrine et dans le dos."""
    m, c2, ac = o['main'], o.get('second', o['main']), o.get('accent', o['main'])
    cuir = o.get('tissu') == 'cuir'
    base = dict(noise=.03, grad=(1.08, .86), sheen=.22) if cuir else dict(noise=.03, twill=.03, grad=(1.04, .88), sheen=.05)
    for r in faces(BODY) + faces(ARM):
        t.fill(r, m, **base)
    t.fill(BODY['top'], sh(m, .85)); t.fill(ARM['top'], sh(c2, .9)); t.fill(ARM['bot'], sh(m, .6))
    for k in TORSO:                                                                 # empiècement d'épaules contrasté
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 160, x1, 178), c2, **base)
        t.fill((x0, 246, x1, 256), sh(m, .7)); t.ribs((x0, 246, x1, 256), .8)       # bas de blouson resserré
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        t.fill((x0, 160, x1, 184), c2, **base)                                      # épaule (coque de protection)
        t.ribs((x0, 162, x1, 182), .88, 4)
        t.fill((x0, 200, x1, 222), sh(c2, .9), **base); t.ribs((x0, 202, x1, 220), .86, 3)   # coude protégé
        t.fill((x0, 244, x1, 256), sh(m, .55)); t.rect((x0, 248, x1, 250), sh(m, .4))  # poignet à scratch
    # bandes de course : diagonale sur la poitrine, bande sur toute la longueur des manches
    for k in SLEEVES:
        x0, y0, x1, y1 = ARM[k]
        if k in ('O', 'B'):
            t.fill((x0 + 10, 184, x0 + 16, 244), ac, noise=.02)
    t.fill((256, 186, 320, 238), sh(m, .9), **base); t.ribs((258, 188, 318, 236), .84, 6)   # dorsale (coque dans le dos)

    def det(d):
        e = sh(m, .55)
        d.polygon([(160, 196), (176, 178), (184, 178), (168, 196)], fill=rgb(ac))   # diagonale gauche
        d.polygon([(224, 196), (208, 178), (200, 178), (216, 196)], fill=rgb(ac))   # diagonale droite
        d.line([(192, 160), (192, 246)], fill=rgb(SILVER_D if cuir else 0x2A2A2E), width=2)   # fermeture
        d.rectangle((189, 166, 195, 172), fill=rgb(SILVER))
        for (x0, x1) in ((128, 160), (160, 224), (224, 256), (256, 320)):
            d.line([(x0, 178), (x1, 178)], fill=e)                                  # couture de l'empiècement
        for x in (262, 314):                                                        # soufflets d'aisance (accordéon)
            for y in range(166, 184, 3):
                d.line([(x - 3, y), (x + 3, y)], fill=sh(c2, .7))
        d.rounded_rectangle((166, 214, 182, 232), radius=2, outline=e)               # poches à rabat
        d.rounded_rectangle((202, 214, 218, 232), radius=2, outline=e)
        for x in (176, 208):                                                        # surpiqûres des panneaux de poitrine
            for y in range(198, 244, 4):
                d.line([(x, y), (x, y + 2)], fill=sh(m, .62))
        for x in (324, 380):                                                        # surpiqûres des manches (extérieur, avant)
            for y in range(186, 244, 4):
                d.line([(x, y), (x, y + 2)], fill=sh(m, .62))
        if cuir:                                                                    # perforations d'aération
            for y in range(186, 210, 4):
                for x in range(166, 184, 4):
                    d.point((x, y), fill=sh(m, .45))
    draw_on(t, det)
    if o.get('poitrine'):
        text(t, 168, 200, o['poitrine'], o.get('marque_col', WHITE), 1)
    back_text(t, o, o.get('dos_y', 194), 2)


def paint_moto_pants(o, t):
    """Pantalon de moto : genouillères cousues, soufflets d'aisance au-dessus des genoux, renforts de hanches, bande latérale, ceinture à zip."""
    m, c2, ac = o['main'], o.get('second', o['main']), o.get('accent', o['main'])
    cuir = o.get('tissu') == 'cuir'
    base = dict(noise=.03, grad=(1.05, .88), sheen=.2) if cuir else dict(noise=.03, twill=.03, grad=(1.02, .9), sheen=.04)
    for r in faces(LEG):
        t.fill(r, m, **base)
    for k in TORSO:
        x0, y0, x1, y1 = BODY[k]
        t.fill((x0, 232, x1, 256), m, **base)
        t.fill((x0, 232, x1, 240), sh(m, .7))
    x0, _, x1, _ = LEG['F']
    t.fill((x0, 196, x1, 218), c2, **base); t.ribs((x0, 198, x1, 216), .86, 4)    # genou protégé
    t.ribs((x0, 184, x1, 194), .82, 2)                                              # soufflet au-dessus du genou
    x0, _, x1, _ = LEG['O']
    t.fill((x0 + 12, 160, x0 + 18, 250), ac, noise=.02)                             # bande latérale

    def det(d):
        e = sh(m, .55)
        d.rounded_rectangle((4, 164, 28, 182), radius=3, fill=sh(c2, .9), outline=e)  # renfort de hanche
        d.line([(192, 240), (192, 256)], fill=e)
        d.rectangle((188, 233, 196, 239), fill=rgb(SILVER_D))
        for x0 in (0, 32, 64, 96):
            d.rectangle((x0, 246, x0 + 32, 256), fill=sh(m, .7))                     # bas de jambe à zip
        d.line([(16, 244), (16, 256)], fill=rgb(SILVER))
    draw_on(t, det)


def shape_moto(slim, bosse=False):
    """Blouson de moto : col officier, coques d'épaule étagées et arrondies (3 plaques, slider côté extérieur), soufflets d'aisance,
    coques de coude en coupe, poignets à scratch ; cuir racing : bosse dorsale arrondie (au-dessus du lettrage du dos)."""
    b = [ring(-1.0, 0.5, .5, 'dark'), ring(-1.1, -0.85, .55, 'second')]                 # col officier, liseré
    for side in ('right', 'left'):
        x0, x1 = arm_x(side, slim)
        p = side + '_arm'
        ox = (x0 - 0.62, x0 - 0.42) if side == 'right' else (x1 + 0.42, x1 + 0.62)    # face extérieure du bras
        oo = (x0 - 0.68, x0 - 0.62) if side == 'right' else (x1 + 0.62, x1 + 0.68)
        ow = (x0 - 0.48, x0 - 0.38) if side == 'right' else (x1 + 0.38, x1 + 0.48)
        b += [(p, x0 - 0.2, -2.5, -2.2, x1 + 0.2, -2.25, 2.2, 'second'),              # dessus d'épaule (arrondi)
              (p, x0 - 0.42, -2.25, -2.42, x1 + 0.42, -0.6, 2.42, 'second'),          # coque principale
              (p, x0 - 0.36, -0.6, -2.3, x1 + 0.36, -0.45, 2.3, 'dark'),              # soufflet
              (p, x0 - 0.36, -0.45, -2.3, x1 + 0.36, 0.7, 2.3, 'second'),             # 2e plaque
              (p, x0 - 0.3, 0.7, -2.2, x1 + 0.3, 0.85, 2.2, 'dark'),
              (p, x0 - 0.3, 0.85, -2.2, x1 + 0.3, 1.7, 2.2, 'second'),                # 3e plaque
              (p, ox[0], -1.6, -1.0, ox[1], 0.2, 1.0, 'metal'),                       # slider d'épaule
              (p, oo[0], -1.2, -0.6, oo[1], -0.2, 0.6, 'metal_dark'),
              (p, x0 - 0.32, 4.2, 0.9, x1 + 0.32, 7.2, 2.38, 'second'),               # coque de coude (coupe)
              (p, x0 - 0.2, 4.6, 2.38, x1 + 0.2, 6.8, 2.55, 'second'),
              (p, x0 - 0.1, 5.1, 2.55, x1 + 0.1, 6.3, 2.62, 'metal'),                 # puck de coude
              (p, x0 - 0.38, 8.4, -2.38, x1 + 0.38, 9.85, 2.38, 'dark'),              # poignet à scratch
              (p, ow[0], 8.6, -0.9, ow[1], 9.6, 0.9, 'strap')]
    if bosse:                                                                         # bosse aérodynamique arrondie (cuir racing)
        b += [('body', -2.6, 0.1, 2.3, 2.6, 4.6, 3.2, 'second'), ('body', -2.1, -0.4, 2.6, 2.1, 3.9, 3.7, 'second'),
              ('body', -1.4, -0.7, 3.0, 1.4, 3.1, 4.05, 'second'), ('body', -0.9, -0.9, 3.4, 0.9, 2.2, 4.25, 'main'),
              ('body', -0.25, 0.4, 3.62, 0.25, 4.0, 3.75, 'accent')]
    return b


def shape_moto_pants(slim):
    """Pantalon de moto : genouillère étagée et arrondie, slider de genou côté extérieur, renfort de hanche, soufflet au-dessus du genou."""
    return sym([('right_leg', -2.42, 4.0, -2.62, 2.42, 7.6, -2.3, 'second'), ('right_leg', -2.0, 4.4, -2.85, 2.0, 7.2, -2.62, 'second'),
                ('right_leg', -1.3, 4.9, -2.98, 1.3, 6.7, -2.85, 'second'),
                ('right_leg', -2.36, 3.4, -2.55, 2.36, 3.65, -2.3, 'dark'), ('right_leg', -2.36, 3.0, -2.5, 2.36, 3.25, -2.3, 'dark'),   # soufflet
                ('right_leg', -2.66, 4.6, -1.9, -2.3, 7.0, 0.6, 'metal'), ('right_leg', -2.76, 5.0, -1.5, -2.66, 6.6, 0.2, 'metal_dark'),   # slider
                ('right_leg', -2.6, 0.3, -1.6, -2.3, 3.2, 1.6, 'second')])                                             # hanche


def shape_gloves_moto(slim):
    b = shape_gloves(slim)
    for side in ('right', 'left'):
        x0, x1 = arm_x(side, slim)
        p = side + '_arm'
        out = (x0 - 0.62, x0 - 0.3) if side == 'right' else (x1 + 0.3, x1 + 0.62)
        far = (x0 - 0.74, x0 - 0.62) if side == 'right' else (x1 + 0.62, x1 + 0.74)
        b += [(p, x0 - 0.62, 5.9, -2.62, x1 + 0.62, 7.4, 2.62, 'dark'),                # manchette longue
              (p, x0 - 0.5, 6.3, -2.74, x1 + 0.5, 7.0, -2.62, 'second'),               # sangle de manchette
              (p, out[0], 8.1, -1.7, out[1], 9.7, 1.7, 'metal'),                     # coque de phalanges
              (p, far[0], 8.4, -1.2, far[1], 9.4, 1.2, 'metal_dark'),
              (p, out[0], 6.1, -0.9, out[1], 7.2, 0.9, 'second')]                    # coque de poignet
    return b


def rrect(y0, y1, ax, zf, zb, r, sw, part='head'):
    """Rectangle arrondi (vu de dessus) en 3 cubes : coins coupés en deux marches. x ±ax, z de zf (avant) à zb (arrière)."""
    k = .3 * r
    return [(part, -ax, y0, zf + r, ax, y1, zb - r, sw), (part, -ax + r, y0, zf, ax - r, y1, zb, sw),
            (part, -ax + k, y0, zf + k, ax - k, y1, zb - k, sw)]


def shape_integral(slim):
    """Casque intégral façon Scorpion Exo-R1 : coque arrondie en couches, grand écran iridium qui épouse les coins, mentonnière en pointe
    (grille, lamelles, prises d'air, déflecteur), écopes sur le dessus, aération frontale à curseur, becquet arrière relevé à ailettes et
    extracteurs, platines de pivot, nervures et déco racing, écusson arrière."""
    b = []
    # coque : du sommet au tour de cou
    for (y0, y1, ax, zf, zb, r) in ((-10.1, -9.7, 2.7, -2.7, 3.1, .9), (-9.7, -9.1, 3.9, -3.9, 4.3, 1.3), (-9.1, -8.6, 4.6, -4.6, 4.95, 1.5),
                                    (-8.6, -2.6, 5.0, -5.0, 5.25, 1.4), (-2.6, -0.6, 4.95, -5.2, 5.05, 1.3), (-0.6, 0.7, 4.8, -5.0, 4.85, .9)):
        # rayons choisis pour que les coins arrondis couvrent encore le casque d'armure (±4,52) : ax - 0,3 r >= 4,52
        b += rrect(y0, y1, ax, zf, zb, r, 'main')
    b += rrect(-10.18, -10.1, 1.9, -1.9, 2.3, .6, 'main_hi')                          # reflet du sommet
    b += rrect(0.7, 1.1, 4.4, -4.7, 4.35, 1.2, 'dark')                                # tour de cou (mousse)
    # grand écran : face, pans d'angle, fenêtres latérales, reflets iridium
    b += [('head', -3.4, -6.6, -5.25, 3.4, -3.1, -4.98, 'lens'),
          ('head', -4.62, -6.4, -4.75, -3.4, -3.3, -4.4, 'lens'), ('head', 3.4, -6.4, -4.75, 4.62, -3.3, -4.4, 'lens'),
          ('head', -5.08, -6.2, -3.6, -4.98, -3.6, -2.1, 'lens'), ('head', 4.98, -6.2, -3.6, 5.08, -3.6, -2.1, 'lens'),
          ('head', -3.0, -6.4, -5.3, -0.8, -5.9, -5.25, 'lens_hi'), ('head', -2.4, -5.9, -5.3, -1.4, -5.4, -5.25, 'lens_hi'),
          ('head', 1.6, -4.0, -5.3, 3.0, -3.5, -5.25, 'lens_hi'), ('head', -4.5, -6.1, -4.8, -3.7, -5.5, -4.75, 'lens_hi')]
    b += [('head', -3.9, -6.98, -5.42, 3.9, -6.6, -4.95, 'main_hi'),                  # casquette de visière (lèvre)
          ('head', -3.6, -3.1, -5.32, 3.6, -2.8, -4.98, 'dark'),                      # joint sous l'écran
          ('head', -3.5, -3.45, -5.42, -2.6, -2.85, -5.25, 'dark')]                   # languette d'ouverture
    # mentonnière en pointe
    b += [('head', -3.4, -2.8, -5.55, 3.4, -0.9, -5.0, 'main'), ('head', -2.2, -2.3, -6.0, 2.2, -0.3, -5.5, 'main'),
          ('head', -1.1, -1.7, -6.35, 1.1, 0.25, -5.95, 'main_hi'),
          ('head', -0.8, -1.55, -6.42, 0.8, -0.1, -6.33, 'dark'),                     # grille d'aération
          ('head', -0.85, -1.2, -6.46, 0.85, -1.05, -6.4, 'metal'), ('head', -0.85, -0.7, -6.46, 0.85, -0.55, -6.4, 'metal'),
          ('head', -2.4, 0.2, -5.7, 2.4, 0.7, -4.8, 'dark')]                          # déflecteur de menton
    # aération frontale à curseur
    b += [('head', -1.1, -8.2, -5.12, 1.1, -7.2, -4.98, 'dark'), ('head', -0.7, -8.1, -5.18, 0.7, -7.75, -5.1, 'metal')]
    # becquet arrière relevé, extracteurs, écusson
    b += [('head', -3.4, -8.0, 5.2, 3.4, -6.6, 5.85, 'main'), ('head', -2.6, -8.5, 5.55, 2.6, -7.6, 6.4, 'second'),
          ('head', -1.9, -8.25, 6.38, -0.6, -7.85, 6.45, 'dark'), ('head', 0.6, -8.25, 6.38, 1.9, -7.85, 6.45, 'dark'),
          ('head', -1.2, -4.4, 5.22, 1.2, -3.6, 5.3, 'light')]
    b += [('head', -0.45, -10.2, -2.5, 0.45, -10.12, 2.9, 'accent'), ('head', -0.45, -8.3, 5.24, 0.45, -2.8, 5.32, 'accent')]   # bande centrale
    b += sym([
        ('head', -2.1, -10.4, -2.4, -0.9, -10.05, -0.5, 'second'), ('head', -1.95, -10.46, -2.3, -1.05, -10.38, -1.8, 'dark'),   # écopes
        ('head', -5.18, -5.6, -2.0, -4.98, -3.8, -0.4, 'second'), ('head', -5.26, -5.0, -1.5, -5.16, -4.4, -0.9, 'metal'),   # pivots
        ('head', -3.4, -2.4, -5.62, -2.25, -1.4, -5.5, 'dark'),                        # prises d'air latérales
        ('head', -3.4, -8.6, 5.3, -2.6, -7.6, 6.3, 'second'),                          # ailettes du becquet
        ('head', -3.0, -3.2, 5.03, -1.6, -2.65, 5.1, 'dark'),                          # extracteurs bas
        ('head', -5.14, -8.0, -3.0, -4.98, -7.55, 4.2, 'second'),                      # nervure haute
        ('head', -5.1, -7.3, 0.4, -4.98, -6.6, 4.6, 'accent'), ('head', -5.1, -6.6, 2.0, -4.98, -6.0, 4.9, 'accent'),   # déco
        ('head', -5.0, -2.4, -3.8, -4.9, -2.0, 4.0, 'accent_dark')])                   # filet bas
    return b


def shape_jet(slim):
    """Casque jet : coque arrondie en couches, nuque et oreillettes enveloppantes, rebord cuir, écran bulle teinté relevé, pressions,
    jugulaire, bande centrale."""
    b = []
    for (y0, y1, ax, zf, zb, r) in ((-10.0, -9.6, 2.6, -2.6, 2.9, .9), (-9.6, -9.0, 3.8, -3.8, 4.1, 1.3), (-9.0, -8.6, 4.55, -4.55, 4.8, 1.5),
                                    (-8.6, -5.6, 4.95, -4.95, 5.1, 1.4)):
        b += rrect(y0, y1, ax, zf, zb, r, 'main')
    b += rrect(-10.08, -10.0, 1.8, -1.8, 2.1, .6, 'main_hi')
    b += rrect(-5.6, 0.3, 4.95, -1.6, 5.1, 1.4, 'main')                               # nuque et côtés enveloppants
    b += [('head', -4.7, -5.6, -4.0, 4.7, -4.6, -1.6, 'main'),
          ('head', -4.75, 0.3, -1.5, 4.75, 0.75, 4.75, 'dark'),                         # rebord bas (cuir)
          ('head', -4.75, -5.75, -5.1, 4.75, -5.3, -4.6, 'dark'),                       # rebord de front
          ('head', -3.9, -8.4, -5.45, 3.9, -5.95, -5.05, 'lens'), ('head', -3.3, -8.2, -5.5, -1.3, -7.6, -5.45, 'lens_hi'),   # écran relevé
          ('head', -0.6, -10.08, -2.4, 0.6, -10.02, 2.6, 'accent'), ('head', -0.6, -8.3, 5.08, 0.6, -0.2, 5.16, 'accent'),
          ('head', -4.6, 1.3, -1.8, 4.6, 1.6, -0.6, 'strap')]
    b += sym([('head', -5.1, -5.0, -1.4, -4.95, 0.1, 1.6, 'dark'),                      # oreillettes
              ('head', -5.2, -7.4, -4.4, -4.9, -6.6, -3.6, 'metal'),                    # pressions d'écran
              ('head', -4.6, 0.4, -1.6, -4.3, 1.6, -0.6, 'strap')])                     # jugulaire
    return b


SHAPES.update({'MOTO': lambda s: shape_moto(s), 'MOTO_RACING': lambda s: shape_moto(s, True), 'MOTO_PANTS': shape_moto_pants,
               'GLOVES_MOTO': shape_gloves_moto, 'INTEGRAL': shape_integral, 'JET': shape_jet})

MOTO = [
    M('blouson_moto_dayneze', 'Blouson cuir racing Dayneze noir et rouge', 'chestplate', 'MOTO_RACING', paint_moto, 'veste', main=0x161618,
      second=0xB01B24, accent=0xF2F2EE, tissu='cuir', dos='DAYNEZE', dos_y=214, dos_col=WHITE, poitrine='DAYNEZE', metal=SILVER, dark=0x0E0E10,
      icon_haut=0xB01B24, icon_coupe=4, icon_bandes=(8,), icon_bande=0xF2F2EE),
    M('blouson_moto_alpinestarz', 'Blouson cuir Alpinestarz noir et blanc', 'chestplate', 'MOTO_RACING', paint_moto, 'veste', main=0x1A1A1D,
      second=0xEDEDE8, accent=0x2A6FC0, tissu='cuir', dos='ASTARZ', dos_y=214, dos_col=WHITE, poitrine='ASTARZ', metal=SILVER, dark=0x0E0E10,
      icon_haut=0xEDEDE8, icon_coupe=4, icon_bandes=(8,), icon_bande=0x2A6FC0),
    M('blouson_moto_cafe', 'Blouson cuir café racer marron', 'chestplate', 'MOTO', paint_moto, 'veste', main=0x5A3420, second=0x4A2814,
      accent=0xC9A24A, tissu='cuir', poitrine='CAFE', marque_col=0xC9A24A, metal=SILVER, dark=0x2E1A10),
    M('blouson_moto_revite', 'Blouson textile Revite gris et jaune fluo', 'chestplate', 'MOTO', paint_moto, 'veste', main=0x4A4D54,
      second=0x26282C, accent=0xD4E21E, tissu='textile', dos='REVITE', dos_col=0xD4E21E, poitrine='REVITE', metal=0x8A8F96, dark=0x1C1C1F,
      icon_bandes=(8,), icon_bande=0xD4E21E),
    M('blouson_moto_furygane', 'Blouson textile Furygane noir et bleu', 'chestplate', 'MOTO', paint_moto, 'veste', main=0x1C1C20,
      second=0x1F3F9E, accent=0xF2F2EE, tissu='textile', dos='FURYGANE', dos_col=WHITE, poitrine='FURYGANE', metal=0x8A8F96, dark=0x0E0E10,
      icon_haut=0x1F3F9E, icon_coupe=4),
    M('blouson_moto_police', 'Blouson moto haute visibilité', 'chestplate', 'MOTO', paint_moto, 'veste', main=0xD4E21E, second=0x1C1C20,
      accent=REFL, tissu='textile', dos='MOTO', dos_col=0x1C1C20, metal=0x8A8F96, dark=0x1C1C20, icon_haut=0x1C1C20, icon_coupe=4),
    M('pantalon_moto_cuir', 'Pantalon cuir racing Dayneze', 'leggings', 'MOTO_PANTS', paint_moto_pants, 'pants', main=0x161618, second=0xB01B24,
      accent=0xF2F2EE, tissu='cuir', metal=SILVER),
    M('pantalon_moto_textile', 'Pantalon textile Revite gris', 'leggings', 'MOTO_PANTS', paint_moto_pants, 'pants', main=0x3A3D44, second=0x1C1C20,
      accent=0xD4E21E, tissu='textile', metal=0x8A8F96),
    M('jean_moto', 'Jean de moto renforcé Furygane', 'leggings', 'MOTO_PANTS', paint_moto_pants, 'pants', main=0x2A3A5A, second=0x22304A,
      accent=0x2A3A5A, tissu='textile', metal=0x6A6E76),
]
for o in MOTO:                                                                    # pucks et sliders : métal assorti (pas l'or par défaut)
    o.setdefault('metal_dark', sh(o.get('metal', SILVER), .62))
CLOTHES += MOTO
ACCS += [
    C('gants_moto_racing', 'Gants de moto racing Dayneze', 'Gants de moto racing Dayneze', 'MAINS', 'GLOVES_MOTO', main=0x161618,
      dark=0x0E0E10, light=0xB01B24, second=0xB01B24, metal=0xC6CBD0, metal_dark=0x7A7E86),
    C('gants_moto_cuir', 'Gants de moto en cuir marron', 'Gants de moto en cuir marron', 'MAINS', 'GLOVES_MOTO', main=0x5A3420,
      dark=0x3A2414, light=0x7A4A2C, second=0x4A2814, metal=0x2A2A2E, metal_dark=0x141416),
    C('gants_moto_hiver', 'Gants de moto hiver Revite', 'Gants de moto hiver Revite', 'MAINS', 'GLOVES_MOTO', main=0x2A2C30,
      dark=0x1A1A1D, light=0xD4E21E, second=0x4A4D54, metal=0x8A8F96, metal_dark=0x55595F),
]
CLOTHES += [
    CH('bottes_moto_racing', 'Bottes de moto racing Alpinestarz', 'botte', 0x161618, matiere='cuir', sole=0x0E0E10, toe=0xC6CBD0,
       heel=0xB01B24, bande=True, logo_col=0xB01B24, collar=0xB01B24, trim=0xC6CBD0, moto=True),
    CH('bottes_moto_touring', 'Bottes de moto touring noires', 'botte', 0x1C1C20, matiere='cuir', sole=0x101012, toe=0x2A2A2E,
       heel=0x2A2A2E, bande=False, logo_col=0x3A3A40, collar=0x141416, trim=0x6A6E76, moto=True),
    CH('bottes_moto_vintage', 'Bottes de moto vintage en cuir marron', 'botte', 0x5A3420, matiere='cuir', sole=0x2A1A10, toe=0x4A2814,
       heel=0x3A2414, bande=False, logo_col=0x4A2814, collar=0x3A2414, trim=0xC9A24A, moto=True),
]
HATS += [
    C('casque_integral_shoey_noir', 'Casque intégral Shoey noir mat', 'Casque intégral Shoey noir mat', 'hat', 'INTEGRAL', main=0x1C1C1F,
      main_hi=0x2E2E33, dark=0x0E0E10, second=0x2A2A2F, accent=0x4A4A52, lens=0x22303C, lens_hi=0x8AAAC0, metal=0x6A6E76),
    C('casque_integral_arai', 'Casque intégral Araï racing rouge et blanc', 'Casque intégral Araï racing rouge et blanc', 'hat', 'INTEGRAL',
      main=0xEDEDE8, main_hi=0xFFFFFF, dark=0x1A1A1D, second=0xC8202E, accent=0xC8202E, lens=0x2A3A6A, lens_hi=0x8AA0E0, metal=0xC6CBD0),
    C('casque_integral_agve', 'Casque intégral AGVE Rossy jaune fluo', 'Casque intégral AGVE Rossy jaune fluo', 'hat', 'INTEGRAL',
      main=0xE8E01E, main_hi=0xF6F04A, dark=0x1A1A1D, second=0x1F3F9E, accent=0x1F3F9E, lens=0x5A3A1A, lens_hi=0xE0A050, metal=0xC6CBD0),
    C('casque_integral_chrome', 'Casque intégral Shoey chromé iridium', 'Casque intégral Shoey chromé iridium', 'hat', 'INTEGRAL',
      main=0xC9CFD6, main_hi=0xEEF2F6, dark=0x1A1A1D, second=0x8A8F96, accent=0x2FD4E0, lens=0x3A2A6A, lens_hi=0x2FD4E0, metal=0x8A8F96),
    C('casque_integral_police', 'Casque intégral blanc motard police', 'Casque intégral blanc motard police', 'hat', 'INTEGRAL',
      main=0xF2F2EE, main_hi=0xFFFFFF, dark=0x1A1A1D, second=0x1F3F9E, accent=0x1F3F9E, lens=0x15181C, lens_hi=0x7A8A9A, metal=0xC6CBD0),
    C('casque_jet_belle_creme', 'Casque jet Belle vintage crème', 'Casque jet Belle vintage crème', 'hat', 'JET', main=0xE8DCC0,
      main_hi=0xF4ECD8, dark=0x5A3420, second=0x5A3420, accent=0x8A2A1E, lens=0x4A3A1A, lens_hi=0xC8A060, metal=0xC9A24A, strap=0x5A3420),
    C('casque_jet_noir', 'Casque jet Shoey noir brillant', 'Casque jet Shoey noir brillant', 'hat', 'JET', main=0x141416,
      main_hi=0x3A3A40, dark=0x2A2A2E, second=0x141416, accent=0x3A3A40, lens=0x15181C, lens_hi=0x7A8A9A, metal=0xC6CBD0, strap=0x1A1A1D),
    C('casque_jet_rouge', 'Casque jet Belle rouge vintage', 'Casque jet Belle rouge vintage', 'hat', 'JET', main=0xA81C24,
      main_hi=0xC83A40, dark=0x2A1A10, second=0xA81C24, accent=0xF2F2EE, lens=0x15181C, lens_hi=0x7A8A9A, metal=0xC9A24A, strap=0x2A1A10),
]
for o in SHOES_TENUES + [o for o in CLOTHES if o.get('shoe')]:
    SHAPES[shoe_shape_name(o)] = (lambda s: lambda slim: shoe_boxes(s))(o['shoe'])

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


def item_model_3d(o, name, boxes, tex, base=0):
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
        i = SW.index(s) - base
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
        if pc == 'boots':                                 # chaussures : la paire en 3D dans l'inventaire
            shoe_cells(o['shoe'], n + '_acc')
            item_model_3d(o, n, shoe_item_boxes(o['shoe']), n + '_acc', SHOE0)
        else:
            (o.get('icon') or icon)(o).save(R + 'textures/item/%s.png' % n)
            json.dump({'parent': 'item/generated', 'textures': {'layer0': 'minenorth_vetements:item/' + n}}, open(R + 'models/item/%s.json' % n, 'w'), indent=1)
        lang_fr['item.minenorth_vetements.' + n] = o['fr']
        lang_en['item.minenorth_vetements.' + n] = o['fr']   # noms FR aussi pour un client en anglais
        outfit_lines.append((o['id'], o['fr'], False, pc == 'chestplate', pc == 'leggings', pc == 'boots'))
    for o in SHOES_TENUES:                                # anciennes tenues : on ne repeint que les chaussures de leur calque 1
        p = ARMOR + '%s_layer_1.png' % o['id']
        t = Tex(0)
        t.a = np.array(Image.open(p).convert('RGBA'), np.float32)
        t.clear((256, 64, 512, 128))
        paint_shoe_tex(t, o['shoe'])
        im = t.img()
        d = shoe_palette(o['shoe'])
        for k, key in enumerate(SW[SHOE0:], SHOE0):
            cx, cy = 256 + 32 * (k % 8), 32 * (k // 8)
            im.paste(rgb(d[key]) + (255,), (cx, cy, cx + 32, cy + 32))
        im.save(p)
        n = o['id'] + '_boots'
        shoe_cells(o['shoe'], n + '_acc')
        item_model_3d(dict(shape=None), n, shoe_item_boxes(o['shoe']), n + '_acc', SHOE0)
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
    # chaussures : forme « <id>_boots » (une tenue peut aussi avoir un haut ou une casquette en relief)
    shape_of = {o['id'] + ('_boots' if o.get('piece') == 'boots' else ''): o['shape'] for o in CLOTHES + HATS + ACCS if o['shape']}
    shape_of.update({o['id'] + '_boots': shoe_shape_name(o) for o in SHOES_TENUES})
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
    # une méthode par groupe de 12 formes : un seul bloc statique dépasserait la limite de 64 Ko de code d'une méthode Java
    groups = [used[i:i + 12] for i in range(0, len(used), 12)]
    L += ['        shapes%d();' % g for g in range(len(groups))]
    L.append('    }')
    for g, grp in enumerate(groups):
        L += ['', '    private static void shapes%d() {' % g]
        for s in grp:
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
        L.append('    }')
    L += ['}', '']
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
