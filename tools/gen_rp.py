"""Tenues RP (costards, smoking, robes, bikinis, maillots) : textures d'armure 512x256 (art 64x32 x8 + pastilles), icones, modeles, lang, OutfitData.
Usage : python tools/gen_rp.py   (depuis la racine du mod). Ajoute les tenues a OutfitData.java et aux fichiers de langue sans toucher aux autres."""
import json
from PIL import Image

R = 'src/main/resources/assets/minenorth_vetements/'
J = 'src/main/java/com/minenorth_vetements/OutfitData.java'
BLACK = 0x15151A
WHITE = 0xF2F2EE
GOLD = 0xC9A24A


def sh(c, f):
    if isinstance(c, tuple):
        c = (c[0] << 16) | (c[1] << 8) | c[2]
    return tuple(max(0, min(255, int(((c >> s) & 255) * f))) for s in (16, 8, 0))


def rgb(c):
    return c if isinstance(c, tuple) else ((c >> 16) & 255, (c >> 8) & 255, c & 255)


class Img:
    def __init__(s, w, h):
        s.im = Image.new('RGBA', (w, h), (0, 0, 0, 0))

    def px(s, x, y, c):
        if 0 <= x < s.im.width and 0 <= y < s.im.height:
            s.im.putpixel((x, y), rgb(c) + (255,))

    def rect(s, x, y, w, h, c):
        for i in range(w):
            for j in range(h):
                s.px(x + i, y + j, c)


def torso(im, fn):
    for face, ox, w in (('front', 20, 8), ('back', 32, 8), ('sideR', 16, 4), ('sideL', 28, 4)):
        for y in range(12):
            for x in range(w):
                c = fn(face, x, y)
                if c is not None:
                    im.px(ox + x, 20 + y, c)


def arms(im, fn, length=12):
    for face, ox in (('out', 40), ('front', 44), ('in', 48), ('back', 52)):
        for y in range(length):
            for x in range(4):
                c = fn(face, x, y)
                if c is not None:
                    im.px(ox + x, 20 + y, c)


def legs(im, fn, y0=0, y1=12):
    for face, ox in (('out', 0), ('front', 4), ('in', 8), ('back', 12)):
        for y in range(y0, y1):
            for x in range(4):
                c = fn(face, x, y)
                if c is not None:
                    im.px(ox + x, 20 + y, c)


def tops(im, c):
    im.rect(20, 16, 8, 4, c)
    im.rect(28, 16, 8, 4, sh(c, .8) if isinstance(c, int) else c)
    im.rect(44, 16, 4, 4, c)
    im.rect(48, 16, 4, 4, c)
    im.rect(4, 16, 4, 4, c)
    im.rect(8, 16, 4, 4, c)


def paint_suit(o):
    j, shirt, tie, lap = o['main'], o['shirt'], o['tie'], o['lapel']
    l1, l2 = Img(64, 32), Img(64, 32)

    def t(face, x, y):
        if face == 'front':
            if y >= 11:
                return sh(j, .72)
            if y == 10 and x in (0, 7):
                return sh(j, .85)
            if x in (2, 5) and y < 7:                      # revers crantes
                return lap if not (y == 3 and x in (2, 5)) else sh(lap, .7)
            if x in (3, 4) and y < 7:                      # chemise + cravate
                if y == 0:
                    return shirt
                if o.get('tiekind') == 'bow':
                    return shirt
                return tie if (y >= 1 and not (y == 1 and False)) else shirt
            if x in (3, 4):                                # veste croisee en bas
                return sh(j, 1.08) if y != 8 else 0x222226
            if x == 1 and y == 6 and o.get('pocket', True):
                return shirt                               # pochette
            if y == 8 and x in (2, 5):
                return 0x2A2A2E                            # boutons
            return j if (x + y) % 5 else sh(j, 1.05)
        if face == 'back':
            return sh(j, .75) if y >= 11 else (sh(j, .88) if x in (3, 4) else j)
        return sh(j, .75) if y >= 11 else j

    torso(l1, t)
    if o.get('tiekind') == 'bow':
        for x in (22, 23, 24, 25):
            l1.px(x, 21, tie)
    arms(l1, lambda f, x, y: shirt if y == 11 and f != 'back' else (sh(j, .78) if y == 10 else j))
    tops(l1, j)
    if o.get('boots'):
        legs(l1, lambda f, x, y: (0x0C0C0E if y == 11 else 0x1B1B1F), 8, 12)
        l1.px(5, 29, 0x6A6A72)
        l1.px(6, 29, 0x4A4A52)
    p = o['pants']
    legs(l2, lambda f, x, y: sh(p, 1.12) if f == 'front' and x == 1 and y > 1 else p)
    tops(l2, p)

    def b(face, x, y):
        if y < 9:
            return None
        if y == 9:
            return 0x1A1A1A
        return GOLD if (face == 'front' and x in (3, 4) and y == 10) else sh(p, .8)

    torso(l2, b)
    if o.get('stripe'):
        legs(l2, lambda f, x, y: lap if f in ('out', 'in') and x == 1 else (sh(p, 1.12) if f == 'front' and x == 1 and y > 1 else p))
    return l1, l2


def paint_dress(o):
    c, a, ac = o['main'], o['accent'], o['hem']
    l1, l2 = Img(64, 32), Img(64, 32)

    def t(face, x, y):
        if face == 'front':
            if y <= 1 and 2 <= x <= 5:
                return None if (y == 0 or x in (3, 4)) else c
            if y == 5:
                return sh(c, .8)
            return sh(c, .85) if y >= 10 else c
        if face == 'back':
            return None if (y <= 1 and 2 <= x <= 5) else (sh(c, .85) if y >= 10 else c)
        return None if y <= 2 else c

    torso(l1, t)
    l1.rect(20, 16, 8, 4, c)
    l1.rect(28, 16, 8, 4, sh(c, .8))
    if o.get('flower'):
        for (fx, fy) in ((2, 4), (5, 7), (1, 9), (6, 2)):
            l1.px(20 + fx, 20 + fy, a)
    if o.get('boots'):
        legs(l1, lambda f, x, y: o['shoe'], 10, 12)
    legs(l2, lambda f, x, y: c if y < o.get('skirt', 12) else None)
    tops(l2, c)
    torso(l2, lambda f, x, y: (ac if y == 9 else c) if y >= 9 else None)
    if o.get('flower'):
        for (fx, fy) in ((1, 1), (2, 2)):
            l2.px(4 + fx, 20 + fy, a)
            l2.px(12 + fx, 20 + fy, a)
    return l1, l2


def paint_bikini(o):
    c, a = o['main'], o['accent']
    l1, l2 = Img(64, 32), Img(64, 32)

    def top(face, x, y):
        if face == 'front':
            if y == 0 and x in (1, 6):
                return a
            if y in (1, 3):
                return c if x in (1, 2, 5, 6) else None
            if y == 2:
                return a if x in (3, 4) else c
            return None
        if face == 'back':
            return a if (y == 0 and x in (1, 6)) or y == 2 else None
        return a if y == 2 else None

    torso(l1, top)

    def bottom(face, x, y):
        if face == 'front':
            if y == 8:
                return a if x in (0, 7) else None
            if y == 9:
                return a if x in (0, 1, 6, 7) else c
            if y == 10:
                return c if 2 <= x <= 5 else None
            return c if (y == 11 and x in (3, 4)) else None
        if face == 'back':
            if y == 8:
                return a
            if y in (9, 10):
                return c if 1 <= x <= 6 else a
            return c if (y == 11 and 2 <= x <= 5) else None
        return a if y == 8 else None

    torso(l2, bottom)
    return l1, l2


def paint_trunks(o):
    c, a = o['main'], o['accent']
    l1, l2 = Img(64, 32), Img(64, 32)
    legs(l2, lambda f, x, y: (a if y == 5 else c) if y < 6 else None)
    torso(l2, lambda f, x, y: (sh(c, .7) if y == 9 else (a if (y == 10 or x in (0, 7)) else c)) if y >= 9 else None)
    if o.get('palms'):
        for (x, y) in ((1, 2), (2, 3), (1, 4), (2, 1), (0, 3)):
            l2.px(4 + x, 20 + y, a)
            l2.px(12 + x, 20 + y, a)
    return l1, l2


def enhance(big, base):
    """Detail de tissu : leger grain, degrade vertical et fines lignes sombres a la frontiere des couleurs (hors palette de pastilles)."""
    import random
    rnd = random.Random(7)
    src = base.im
    for X in range(512):
        for Y in range(256):
            if X >= 256 and Y < 64:
                continue
            px = big.getpixel((X, Y))
            if px[3] == 0:
                continue
            f = 1.0 + rnd.uniform(-.035, .035) * (1 if (X // 2 + Y // 2) % 2 else -1)
            f *= 1.0 - 0.10 * ((Y % 64) / 64.0) if Y >= 128 else 1.0
            gx, gy = X // 8, Y // 8
            c = src.getpixel((gx, gy))
            for dx, dy, edge in ((1, 0, X % 8 == 7), (-1, 0, X % 8 == 0), (0, 1, Y % 8 == 7), (0, -1, Y % 8 == 0)):
                if edge and 0 <= gx + dx < 64 and 0 <= gy + dy < 32:
                    n = src.getpixel((gx + dx, gy + dy))
                    if n[3] and n != c and sum(n[:3]) > sum(c[:3]) + 30:
                        f *= 0.78
            big.putpixel((X, Y), tuple(max(0, min(255, int(v * f))) for v in px[:3]) + (px[3],))
    return big


def finish(l1, l2, pal, name):
    out = []
    for im in (l1, l2):
        big = enhance(im.im.resize((512, 256), Image.NEAREST), im)
        for k, col in enumerate(pal):
            cx, cy = 256 + 32 * (k % 8), 32 * (k // 8)
            for x in range(32):
                for y in range(32):
                    big.putpixel((cx + x, cy + y), rgb(col) + (255,))
        out.append(big)
    p = R + 'textures/models/armor/'
    out[0].save(p + name + '_layer_1.png')
    out[1].save(p + name + '_layer_2.png')


SHIRT = ["................", "...XXXXXXXXXX...", "..XXXXX..XXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", ".XXX.XXXXXX.XXX.", "................", "................", "................"]
PANTS = ["................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "................", "................", "................"]
SHOES = ["................", "................", "................", "................", "...XXXX.........", "...XXXX.........", "...XXXXX........", "...XXXXXX.......", "..XXXXXXXXX.....", ".XXXXXXXXXXXX...", ".XXXXXXXXXXXX...", "................", "................", "................", "................", "................"]
HEELS = ["................", "................", "................", "................", "....XXX.........", "....XXX.........", "....XXXX........", "....XXXXX.......", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXX.......X..", "...XX.........X.", "................", "................", "................", "................"]
LONGDRESS = ["................", "....X.XXXX.X....", "....XXXXXXXX....", "....XXXXXXXX....", ".....XXXXXX.....", ".....XXXXXX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", ".XXXXXXXXXXXXXX.", "................", "................"]
SHORTDRESS = ["................", "....X.XXXX.X....", "....XXXXXXXX....", "....XXXXXXXX....", ".....XXXXXX.....", ".....XXXXXX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", "................", "................", "................", "................", "................", "................"]
BIKTOP = ["................", "................", "..X..........X..", "...X........X...", "...XX......XX...", "..XXXX....XXXX..", "..XXXX....XXXX..", "...XX......XX...", "................", "................", "................", "................", "................", "................", "................", "................"]
BIKBOT = ["................", "................", "................", "................", "...X........X...", "....XXXXXXXX....", ".....XXXXXX.....", "......XXXX......", ".......XX.......", "................", "................", "................", "................", "................", "................", "................"]
TRUNKS = ["................", "................", "................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXX....XXX...", "................", "................", "................", "................", "................", "................", "................"]


def icon(shape, base, fn=None):
    im = Img(16, 16)
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch == 'X':
                im.px(x, y, fn(x, y) if fn else base)
    o = Img(16, 16)
    o.im = im.im.copy()
    for y in range(16):
        for x in range(16):
            if im.im.getpixel((x, y))[3] == 0 and any(0 <= x + dx < 16 and 0 <= y + dy < 16 and im.im.getpixel((x + dx, y + dy))[3] for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                o.px(x, y, 0x101010)
    return o


def icon_suit(o):
    j, shirt, tie = o['main'], o['shirt'], o['tie']

    def f(x, y):
        if 6 <= x <= 9 and 2 <= y <= 12:
            return tie if (x in (7, 8) and 3 <= y <= 9 and o.get('tiekind') != 'bow') else shirt
        if x in (5, 10) and 2 <= y <= 6:
            return o['lapel']
        return j if y < 12 else sh(j, .75)
    return icon(SHIRT, j, f)


def icon_dress(o, shape):
    c = o['main']

    def f(x, y):
        if y >= 12:
            return o['hem']
        if o.get('flower') and (x * 3 + y * 5) % 11 == 0:
            return o['accent']
        return c
    return icon(shape, c, f)


OUT = [
    dict(id='costard_noir', fr='Costard noir', kind='suit', parts='clb', main=BLACK, shirt=WHITE, tie=0x8B1A1E, lapel=sh(BLACK, 2.6), pants=BLACK, boots=True),
    dict(id='costard_marine', fr='Costard bleu nuit', kind='suit', parts='clb', main=0x1B2A4A, shirt=WHITE, tie=GOLD, lapel=sh(0x1B2A4A, 2.0), pants=0x1B2A4A, boots=True),
    dict(id='costard_blanc', fr='Costard blanc', kind='suit', parts='clb', main=0xEDEDE6, shirt=0x1E1E22, tie=GOLD, lapel=sh(0xEDEDE6, .72), pants=0xEDEDE6, boots=True),
    dict(id='costard_gris', fr='Costard gris anthracite', kind='suit', parts='clb', main=0x4A4D52, shirt=WHITE, tie=0xB02030, lapel=sh(0x4A4D52, 1.7), pants=0x4A4D52, boots=True),
    dict(id='smoking', fr='Smoking', kind='suit', parts='clb', main=BLACK, shirt=WHITE, tie=0xB01E26, tiekind='bow', lapel=0x3C3C46, pants=BLACK, stripe=True, boots=True),
    dict(id='robe_soiree_rouge', fr='Robe de soirée rouge', kind='dress', parts='clb', main=0xB0121E, accent=0xB0121E, hem=sh(0xB0121E, .75), skirt=12, boots=True, shoe=0x1A1A1A, pants=0xB0121E),
    dict(id='robe_soiree_noire', fr='Robe de soirée noire', kind='dress', parts='clb', main=0x141418, accent=GOLD, hem=GOLD, skirt=12, boots=True, shoe=GOLD, pants=0x141418),
    dict(id='robe_cocktail', fr='Robe cocktail bleu roi', kind='dress', parts='clb', main=0x2447B0, accent=0x2447B0, hem=sh(0x2447B0, .75), skirt=3, boots=True, shoe=0xE8E8E8, pants=0x2447B0),
    dict(id='robe_ete', fr="Robe d'été fleurie", kind='dress', parts='cl', main=0xF4F1EA, accent=0xE86FA0, hem=0xF4F1EA, flower=True, skirt=3, pants=0xF4F1EA),
    dict(id='bikini_rouge', fr='Bikini rouge', kind='bikini', parts='cl', main=0xD01F2E, accent=0xF2F2EE, pants=0xD01F2E),
    dict(id='bikini_turquoise', fr='Bikini turquoise', kind='bikini', parts='cl', main=0x21B7C4, accent=0xF2C230, pants=0x21B7C4),
    dict(id='bikini_noir', fr='Bikini noir et or', kind='bikini', parts='cl', main=0x141418, accent=GOLD, pants=0x141418),
    dict(id='maillot_bleu', fr='Short de bain bleu', kind='trunks', parts='l', main=0x1F5FB0, accent=0xF2F2EE, pants=0x1F5FB0),
    dict(id='maillot_tropical', fr='Short de bain tropical', kind='trunks', parts='l', main=0x12806A, accent=0xF2C230, palms=True, pants=0x12806A),
]
PIECE = {'c': 'chestplate', 'l': 'leggings', 'b': 'boots'}
LABEL = {'suit': {'c': 'Veste', 'l': 'Pantalon', 'b': 'Chaussures'}, 'dress': {'c': 'Corsage', 'l': 'Jupe', 'b': 'Talons'},
         'bikini': {'c': 'Haut', 'l': 'Bas'}, 'trunks': {'l': 'Short'}}


def palette(o):
    m = o['main']
    a = o.get('accent', o.get('lapel', m))
    p = o.get('pants', m)
    s = o.get('shoe', 0x141416)
    return [m, a, o.get('shirt', WHITE), p, s, 0x2A2A2E, m, sh(m, .75), sh(m, 1.1), sh(p, .8), sh(s, .7), sh(a, .75)]


def main():
    lang = {}
    for o in OUT:
        k = o['kind']
        l1, l2 = {'suit': paint_suit, 'dress': paint_dress, 'bikini': paint_bikini, 'trunks': paint_trunks}[k](o)
        finish(l1, l2, palette(o), o['id'])
        for ch in o['parts']:
            n = o['id'] + '_' + PIECE[ch]
            if k == 'suit':
                ic = icon_suit(o) if ch == 'c' else icon(PANTS, o['pants']) if ch == 'l' else icon(SHOES, 0x141416, lambda x, y: 0x141416 if y < 10 else 0x35353A)
            elif k == 'dress':
                shape = LONGDRESS if o['skirt'] >= 12 else SHORTDRESS
                ic = icon_dress(o, shape) if ch == 'c' else icon(shape, o['main']) if ch == 'l' else icon(HEELS, o.get('shoe', 0x141416))
            elif k == 'bikini':
                ic = icon(BIKTOP if ch == 'c' else BIKBOT, o['main'], lambda x, y, o=o: o['accent'] if y in (2, 3) and x in (2, 3, 12, 13) else o['main'])
            else:
                ic = icon(TRUNKS, o['main'], lambda x, y, o=o: o['accent'] if y == 3 else o['main'])
            ic.im.save(R + 'textures/item/' + n + '.png')
            json.dump({'parent': 'item/generated', 'textures': {'layer0': 'minenorth_vetements:item/' + n}}, open(R + 'models/item/' + n + '.json', 'w'), indent=1)
            lang['item.minenorth_vetements.' + n] = o['fr'] + ' - ' + LABEL[k][ch]
    for lg in ('fr_fr', 'en_us'):
        p = R + 'lang/' + lg + '.json'
        d = json.load(open(p, encoding='utf-8-sig'))
        d.update(lang)
        json.dump(d, open(p, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    src = open(J, encoding='utf-8').read()
    for o in OUT:
        if '"' + o['id'] + '"' in src:
            continue
        line = '        new Outfit("%s", "%s", false, %s, %s, %s),\n' % (o['id'], o['fr'], 'true' if 'c' in o['parts'] else 'false', 'true' if 'l' in o['parts'] else 'false', 'true' if 'b' in o['parts'] else 'false')
        src = src.replace('    };\n', line + '    };\n', 1)
    open(J, 'w', encoding='utf-8').write(src)
    print('ok', len(OUT))


main()
