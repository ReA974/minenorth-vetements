"""Accessoires RP en 3D (lunettes de marque, cagoules, bandanas, echarpes) : objets 3D a elements + textures d'armure pour le rendu porte.
Usage : python tools/gen_acc.py  (depuis la racine du mod). Ajoute les objets a OutfitData.java et aux fichiers de langue."""
import json
from PIL import Image

R = 'src/main/resources/assets/minenorth_vetements/'
J = 'src/main/java/com/minenorth_vetements/OutfitData.java'


def rgb(c):
    return c if isinstance(c, tuple) else ((c >> 16) & 255, (c >> 8) & 255, c & 255)


def sh(c, f):
    r = rgb(c)
    return tuple(max(0, min(255, int(v * f))) for v in r)


# id, nom, style, couleur principale, verres/accent, clair
ITEMS = [
    ('lunettes_aviator', 'Lunettes aviator dorées', 'AVIATOR', 0xD4AF37, 0x2C3A32, 0xF2F2EE),
    ('lunettes_wayfarer', 'Lunettes noires Ray-Band', 'WAYFARER', 0x111114, 0x0A0A0C, 0x55555C),
    ('lunettes_sport', 'Lunettes sport miroir', 'SPORT', 0xF2F2EE, 0x2E6FD0, 0xC8202A),
    ('lunettes_rose', 'Lunettes de star roses', 'AVIATOR', 0xF2F2EE, 0xE86FA0, 0xD4AF37),
    ('cagoule_noire', 'Cagoule noire', 'BALA', 0x1A1A1D, 0x0A0A0C, 0x3A3A40),
    ('cagoule_kaki', 'Cagoule kaki', 'BALA', 0x4B5A3A, 0x0A0A0C, 0x6B7B54),
    ('bandana_rouge', 'Bandana rouge', 'BANDANA', 0xB3202A, 0x7A1219, 0xF2F2EE),
    ('bandana_noir', 'Bandana noir', 'BANDANA', 0x1A1A1D, 0x0A0A0C, 0xC8C8C8),
    ('echarpe_grise', 'Écharpe en laine grise', 'SCARF', 0x7D8086, 0x5A5D62, 0xE0E0E0),
    ('echarpe_rouge', 'Foulard en soie rouge', 'SCARF', 0xB3202A, 0x7A1219, 0xD4AF37),
]


def palette(main, lens, light):
    return [main, lens, light, main, 0x202024, 0x303034, main, sh(main, .75), sh(main, 1.15), sh(main, .7), 0x181818, sh(lens, .7)]


def finish(img1, name, pal):
    for lay in (1, 2):
        big = (img1 if lay == 1 else Image.new('RGBA', (64, 32), (0, 0, 0, 0))).resize((512, 256), Image.NEAREST)
        for k, col in enumerate(pal):
            cx, cy = 256 + 32 * (k % 8), 32 * (k // 8)
            for x in range(32):
                for y in range(32):
                    big.putpixel((cx + x, cy + y), rgb(col) + (255,))
        big.save(R + 'textures/models/armor/%s_layer_%d.png' % (name, lay))


def head_art(style, main):
    im = Image.new('RGBA', (64, 32), (0, 0, 0, 0))
    if style != 'BALA':
        return im
    for (ox, oy, w, h) in ((8, 0, 8, 8), (0, 8, 8, 8), (8, 8, 8, 8), (16, 8, 8, 8), (24, 8, 8, 8)):
        for x in range(w):
            for y in range(h):
                f = 1.0 if (x + y) % 2 else .92
                im.putpixel((ox + x, oy + y), sh(main, f) + (255,))
    for x in range(9, 15):          # fente des yeux (la peau et les yeux du joueur restent visibles)
        for y in (11, 12):
            im.putpixel((x, y), (0, 0, 0, 0))
    return im


def icon_cell(img, cx, cy, col):
    for x in range(4):
        for y in range(4):
            img.putpixel((cx * 4 + x, cy * 4 + y), rgb(col) + (255,))


def item_model(name, style, main, lens, light):
    tex = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    icon_cell(tex, 0, 0, main)
    icon_cell(tex, 1, 0, sh(main, .7))
    icon_cell(tex, 2, 0, lens)
    icon_cell(tex, 3, 0, light)
    icon_cell(tex, 0, 1, 0xDDA37C)
    tex.save(R + 'textures/item/%s_acc.png' % name)
    C = {'main': (0, 0), 'dark': (4, 0), 'lens': (8, 0), 'light': (12, 0), 'skin': (0, 4)}

    def box(n, f, t, c, top=None):
        u, v = C[c]
        faces = {d: {'uv': [u, v, u + 4, v + 4], 'texture': '#0'} for d in ('north', 'south', 'east', 'west', 'up', 'down')}
        if top:
            u, v = C[top]
            faces['up'] = {'uv': [u, v, u + 4, v + 4], 'texture': '#0'}
        return {'name': n, 'from': f, 'to': t, 'faces': faces}
    E = []
    if style in ('AVIATOR', 'WAYFARER'):
        w = style == 'WAYFARER'
        for s, (x0, x1) in (('g', (1.2, 7.4)), ('d', (8.6, 14.8))):
            E.append(box('monture_' + s, [x0 - .5, 4.2, 5.6], [x1 + .5, 10.2 if not w else 9.4, 6.4], 'main'))
            E.append(box('verre_' + s, [x0, 4.8 if w else 4.4, 5.2], [x1, 9.4 if w else 9.6, 5.7], 'lens'))
            if not w:
                E.append(box('pointe_' + s, [x0 + 1.2, 3.6, 5.2], [x1 - 1.2, 4.4, 5.7], 'lens'))
        E.append(box('pont', [7.2, 8.0, 5.3], [8.8, 8.8, 6.0], 'main'))
        if w:
            E.append(box('barre', [0.6, 9.4, 5.4], [15.4, 10.6, 6.4], 'main'))
        E.append(box('branche_g', [0.6, 8.4, 6.4], [1.4, 9.4, 14.5], 'main'))
        E.append(box('branche_d', [14.6, 8.4, 6.4], [15.4, 9.4, 14.5], 'main'))
        E.append(box('reflet', [2.0, 8.6, 5.1], [3.2, 9.0, 5.3], 'light'))
    elif style == 'SPORT':
        E.append(box('verre', [0.8, 4.6, 5.0], [15.2, 9.6, 5.6], 'lens'))
        E.append(box('arcade', [0.6, 9.6, 4.8], [15.4, 10.6, 6.2], 'main'))
        E.append(box('branche_g', [0.4, 5.4, 5.6], [1.2, 9.4, 14.5], 'main'))
        E.append(box('branche_d', [14.8, 5.4, 5.6], [15.6, 9.4, 14.5], 'main'))
        E.append(box('pont', [7.0, 5.0, 4.8], [9.0, 8.0, 5.2], 'light'))
        E.append(box('logo', [11.6, 9.6, 4.6], [14.0, 10.6, 4.8], 'light'))
    elif style == 'BALA':
        E.append(box('tete', [3.6, 1.4, 3.6], [12.4, 12.0, 12.4], 'main', top='dark'))
        E.append(box('sommet', [4.4, 12.0, 4.4], [11.6, 12.8, 11.6], 'dark'))
        E.append(box('col', [3.2, 0, 3.2], [12.8, 2.0, 12.8], 'dark'))
        E.append(box('fente', [4.2, 6.0, 3.2], [11.8, 8.4, 3.7], 'skin'))
        E.append(box('yeux_g', [5.0, 6.7, 3.0], [6.8, 7.7, 3.4], 'lens'))
        E.append(box('yeux_d', [9.2, 6.7, 3.0], [11.0, 7.7, 3.4], 'lens'))
        E.append(box('bord_haut', [4.0, 8.4, 3.4], [12.0, 9.0, 3.8], 'light'))
        E.append(box('bord_bas', [4.0, 5.4, 3.4], [12.0, 6.0, 3.8], 'light'))
    elif style == 'BANDANA':
        E.append(box('tissu', [2, 0, 3], [14, 0.8, 9], 'main', top='main'))
        E.append(box('tissu_2', [4, 0, 9], [12, 0.8, 12], 'main'))
        E.append(box('pointe', [6.5, 0, 12], [9.5, 0.8, 14.5], 'main'))
        E.append(box('noeud', [6.4, 0.8, 2.0], [9.6, 2.4, 4.2], 'dark'))
        E.append(box('bout_g', [4.5, 0.8, 1.0], [6.5, 1.6, 3.2], 'dark'))
        E.append(box('bout_d', [9.5, 0.8, 1.0], [11.5, 1.6, 3.2], 'dark'))
        for i, (x, z) in enumerate(((4, 5), (8, 4.6), (11.5, 5.6), (6, 7.6), (10, 8))):
            E.append(box('motif%d' % i, [x, 0.8, z], [x + 1.2, 1.0, z + 1.2], 'light'))
    else:   # SCARF
        E.append(box('tour', [1, 0, 3], [15, 2.4, 9], 'main'))
        E.append(box('rayure_1', [1, 0, 5.2], [15, 2.5, 5.8], 'light'))
        E.append(box('rayure_2', [1, 0, 6.8], [15, 2.5, 7.4], 'light'))
        E.append(box('pan', [10.4, 0, 9], [14.0, 2.0, 15.5], 'main'))
        E.append(box('frange', [10.4, 0, 15.5], [14.0, 2.1, 16.3], 'light'))
        E.append(box('pan_2', [6.8, 0, 9], [10.2, 2.0, 13.5], 'dark'))
    json.dump({'textures': {'0': 'minenorth_vetements:item/%s_acc' % name, 'particle': 'minenorth_vetements:item/%s_acc' % name}, 'elements': E,
               'display': {'gui': {'rotation': [28, 205, 0], 'translation': [0, -1, 0], 'scale': [0.95, 0.95, 0.95]},
                           'ground': {'translation': [0, 2, 0], 'scale': [0.5, 0.5, 0.5]},
                           'fixed': {'rotation': [0, 180, 0], 'scale': [0.9, 0.9, 0.9]},
                           'head': {'translation': [0, 4, 0], 'scale': [1.0, 1.0, 1.0]},
                           'thirdperson_righthand': {'translation': [0, 3, 2], 'scale': [0.55, 0.55, 0.55]},
                           'firstperson_righthand': {'rotation': [0, 200, 0], 'translation': [1, 4, 0], 'scale': [0.55, 0.55, 0.55]}}},
              open(R + 'models/item/%s_helmet.json' % name, 'w'), indent=1)


def main():
    lang = {}
    src = open(J, encoding='utf-8').read()
    for (i, fr, style, main_c, lens, light) in ITEMS:
        finish(head_art(style, main_c), i, palette(main_c, lens, light))
        item_model(i, style, main_c, lens, light)
        lang['item.minenorth_vetements.%s_helmet' % i] = fr
        if '"%s"' % i not in src:
            src = src.replace('    };\n', '        new Outfit("%s", "%s", true, false, false, false),\n    };\n' % (i, fr), 1)
    open(J, 'w', encoding='utf-8').write(src)
    for lg in ('fr_fr', 'en_us'):
        p = R + 'lang/%s.json' % lg
        d = json.load(open(p, encoding='utf-8-sig'))
        d.update(lang)
        json.dump(d, open(p, 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
    print('ok', len(ITEMS))


main()
