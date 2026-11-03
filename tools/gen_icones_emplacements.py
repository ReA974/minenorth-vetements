"""Icônes fantômes des emplacements d'accessoires (gris vanilla 85,85,85, comme empty_armor_slot_*).
Usage : python tools/gen_icones_emplacements.py  (depuis la racine du mod)."""
from PIL import Image

G = (85, 85, 85, 255)
ICONS = {
    'visage': ["................", "................", "................", "................", "................",
               "X..............X", "XXXXXXX..XXXXXXX", "XXXXXXXXXXXXXXXX", ".XXXXXX..XXXXXX.", ".XXXXXX..XXXXXX.",
               "..XXXX....XXXX..", "................", "................", "................", "................", "................"],
    'cou': ["................", "..XX........XX..", "..XX........XX..", "...XX......XX...", "...XX......XX...",
            "....XX....XX....", ".....XX..XX.....", "......XXXX......", ".......XX.......", "......XXXX......",
            ".....XXXXXX.....", ".....XXXXXX.....", "......XXXX......", ".......XX.......", "................", "................"],
    'poignet': ["................", ".....XXXXXX.....", ".....XXXXXX.....", ".....XXXXXX.....", "....XXXXXXXX....",
                "...XX......XX...", "...X..X.....X...", "...X..X.....XX..", "...X..XXX...XX..", "...X.........X..",
                "...XX......XX...", "....XXXXXXXX....", ".....XXXXXX.....", ".....XXXXXX.....", ".....XXXXXX.....", "................"],
    'mains': ["................", ".....X..X.......", ".....X..X..X....", "..X..X..X..X....", "..X..X..X..X....",
              "..X..X..X..X....", "..XXXXXXXXXX.XX.", "..XXXXXXXXXXXXX.", "..XXXXXXXXXXXX..", "..XXXXXXXXXXX...",
              "...XXXXXXXXX....", "...XXXXXXXXX....", "....XXXXXXX.....", "....XXXXXXX.....", "....XXXXXXX.....", "................"],
    'dos': ["................", "......XXXX......", ".....X....X.....", "...XXXXXXXXXX...", "..XXXXXXXXXXXX..",
            "..XXXXXXXXXXXX..", "..XXXXXXXXXXXX..", "..XX........XX..", "..XX.XXXXXX.XX..", "..XX.X....X.XX..",
            "..XX.XXXXXX.XX..", "..XX........XX..", "..XXXXXXXXXXXX..", "...XXXXXXXXXX...", "................", "................"],
}
for k, rows in ICONS.items():
    im = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c == 'X':
                im.putpixel((x, y), G)
    im.save('src/main/resources/assets/minenorth_vetements/textures/item/empty_acc_%s.png' % k)
print('ok', len(ICONS))
