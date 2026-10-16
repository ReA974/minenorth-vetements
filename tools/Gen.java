import java.awt.image.BufferedImage;
import java.io.File;
import java.nio.file.*;
import java.util.*;
import javax.imageio.ImageIO;

/** Genere textures d'armure (layer_1/2), icones, modeles et lang. Usage: java tools/Gen.java <racine projet> */
public class Gen {
    enum Style { TEE, HOODIE, JACKET, POLO, PUFFER, DENIM }
    enum Logo { SWOOSH, STRIPES, BOX, CROC, CAT, MONO, CHAMP, NORD, GG, JUMP, DENIMTAG }

    static class Outfit {
        String id, fr, en; Logo logo; Style style;
        int main, accent, logoC, pants, shoe, sole, cap;
        boolean hasCap, hasChest = true, hasLegs, hasBoots, beanie;
        Outfit(String id, String name, Logo l, Style s, int main, int accent, int logoC) {
            this.id = id; this.fr = name; this.en = name; logo = l; style = s; this.main = main; this.accent = accent; this.logoC = logoC;
            pants = main; shoe = 0xFFFFFF; sole = 0xDDDDDD; cap = main;
        }
        Outfit cap() { hasCap = true; return this; }
        Outfit beanie() { hasCap = true; beanie = true; return this; }
        Outfit pants(int c) { hasLegs = true; pants = c; return this; }
        Outfit shoes(int c, int sole) { hasBoots = true; shoe = c; this.sole = sole; return this; }
        Outfit noChest() { hasChest = false; return this; }
    }

    static final int BLACK = 0x1A1A1A, WHITE = 0xF2F2F2, GREY = 0x8A8D91, RED = 0xC8202A, BLUE = 0x1F3F9E, NAVY = 0x14213D,
            GREEN = 0x1E7A3C, YELLOW = 0xF2C230, BROWN = 0x5A3A22, TAN = 0xB88B4A, DENIM = 0x3F5F94, DKDENIM = 0x2B4470, PINK = 0xE86FA0;

    static List<Outfit> outfits = new ArrayList<>();

    static void define() {
        outfits.add(new Outfit("nayk_noir", "Nayk Noir", Logo.SWOOSH, Style.HOODIE, BLACK, GREY, WHITE).cap().pants(BLACK).shoes(WHITE, GREY));
        outfits.add(new Outfit("nayk_gris", "Nayk Gris", Logo.SWOOSH, Style.HOODIE, GREY, BLACK, BLACK).pants(GREY).shoes(BLACK, WHITE));
        outfits.add(new Outfit("nayk_rouge", "Nayk Rouge", Logo.SWOOSH, Style.TEE, RED, BLACK, WHITE).cap().pants(BLACK).shoes(RED, WHITE));
        outfits.add(new Outfit("abidas_bleu", "Abidas Bleu", Logo.STRIPES, Style.JACKET, BLUE, WHITE, WHITE).pants(BLUE).shoes(WHITE, BLUE));
        outfits.add(new Outfit("abidas_noir", "Abidas Noir", Logo.STRIPES, Style.JACKET, BLACK, WHITE, WHITE).pants(BLACK).shoes(BLACK, WHITE));
        outfits.add(new Outfit("pumba_rouge", "Pumba Rouge", Logo.CAT, Style.TEE, RED, WHITE, WHITE).pants(BLACK).shoes(RED, WHITE));
        outfits.add(new Outfit("pumba_blanc", "Pumba Blanc", Logo.CAT, Style.TEE, WHITE, BLACK, BLACK).pants(NAVY).shoes(WHITE, BLACK));
        outfits.add(new Outfit("supreem_rouge", "Supreem Box Logo", Logo.BOX, Style.TEE, RED, WHITE, WHITE).cap());
        outfits.add(new Outfit("supreem_noir", "Supreem Hoodie Noir", Logo.BOX, Style.HOODIE, BLACK, RED, WHITE).beanie());
        outfits.add(new Outfit("lacroste_vert", "Lacroste Polo Vert", Logo.CROC, Style.POLO, GREEN, WHITE, WHITE).pants(0xD9C9A0));
        outfits.add(new Outfit("lacroste_blanc", "Lacroste Polo Blanc", Logo.CROC, Style.POLO, WHITE, GREEN, GREEN).pants(NAVY));
        outfits.add(new Outfit("nord_fasse", "Nord Fasse Doudoune", Logo.NORD, Style.PUFFER, BLACK, YELLOW, WHITE).beanie().pants(BLACK));
        outfits.add(new Outfit("champyon_gris", "Champyon Sweat", Logo.CHAMP, Style.HOODIE, GREY, NAVY, NAVY).pants(GREY));
        outfits.add(new Outfit("guchi_vert", "Guchi Polo", Logo.GG, Style.POLO, GREEN, RED, YELLOW).cap().shoes(WHITE, GREEN));
        outfits.add(new Outfit("louis_vuiten", "Louis Vuiten Monogram", Logo.MONO, Style.JACKET, BROWN, TAN, TAN).pants(BROWN).shoes(BROWN, TAN));
        outfits.add(new Outfit("jordane_rouge", "Jordane Retro", Logo.JUMP, Style.TEE, BLACK, RED, RED).pants(BLACK).shoes(RED, BLACK));
        outfits.add(new Outfit("levys_jean", "Levys Jean", Logo.DENIMTAG, Style.DENIM, DENIM, YELLOW, RED).pants(DKDENIM).shoes(WHITE, GREY));
    }

    // ---------- helpers ----------
    static BufferedImage newImg(int w, int h) { return new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB); }
    static void px(BufferedImage im, int x, int y, int rgb) {
        if (x < 0 || y < 0 || x >= im.getWidth() || y >= im.getHeight()) return;
        im.setRGB(x, y, 0xFF000000 | rgb);
    }
    static void rect(BufferedImage im, int x, int y, int w, int h, int rgb) {
        for (int i = 0; i < w; i++) for (int j = 0; j < h; j++) px(im, x + i, y + j, rgb);
    }
    static int shade(int c, double f) {
        int r = (int) Math.min(255, ((c >> 16) & 255) * f), g = (int) Math.min(255, ((c >> 8) & 255) * f), b = (int) Math.min(255, (c & 255) * f);
        return (r << 16) | (g << 8) | b;
    }

    /** bitmap de logo; 'X' = pixel logo */
    static String[] bitmap(Logo l) {
        switch (l) {
            case SWOOSH: return new String[]{"....XX", ".XXXXX", "XXX..."};
            case STRIPES: return new String[]{"..X.X.X", ".X.X.X.", "X.X.X.."};
            case BOX: return new String[]{"XXXXXXX", "XX.X.XX", "XXXXXXX"};
            case CROC: return new String[]{".XXXX.", "XX.XXX", ".XXX.."};
            case CAT: return new String[]{"X.XXX.X", "XXXXXXX", ".XX.XX."};
            case MONO: return new String[]{"X.X", ".X.", "X.X"};
            case CHAMP: return new String[]{"XXXX", "X...", "XXXX"};
            case NORD: return new String[]{"X.X.X", "XXXXX", ".XXX."};
            case GG: return new String[]{"XX.XX", "X..X.", "XX.XX"};
            case JUMP: return new String[]{"..X..", "XXXXX", ".X.X."};
            default: return new String[]{"XXX", "X.X", "XXX"};
        }
    }
    static void drawBitmap(BufferedImage im, int x, int y, String[] bm, int rgb) {
        for (int j = 0; j < bm.length; j++) for (int i = 0; i < bm[j].length(); i++) if (bm[j].charAt(i) == 'X') px(im, x + i, y + j, rgb);
    }

    // ---------- armor layers ----------
    static void paintHead(BufferedImage im, Outfit o) {
        int c = o.cap;
        int hx = o.beanie ? 4 : 4; // rows de bonnet/casquette
        rect(im, 8, 0, 8, 8, c);              // top
        for (int[] f : new int[][]{{0, 8}, {8, 8}, {16, 8}, {24, 8}}) {
            rect(im, f[0], f[1], 8, o.beanie ? 4 : 3, c);
        }
        if (o.beanie) { for (int[] f : new int[][]{{0, 8}, {8, 8}, {16, 8}, {24, 8}}) rect(im, f[0], f[1] + 3, 8, 1, o.accent); }
        else rect(im, 8, 11, 8, 1, shade(c, 0.7)); // visiere (ombre) sur la face
        rect(im, 8, 8, 8, 1, c);
        // logo face avant
        if (!o.beanie) drawBitmap(im, 10, 9, bitmap(o.logo).length > 0 ? small(o.logo) : bitmap(o.logo), o.logoC);
    }
    static String[] small(Logo l) { // version 3 colonnes pour casquette
        switch (l) {
            case SWOOSH: return new String[]{"..X", "XX."};
            case BOX: return new String[]{"XXX", "XXX"};
            case STRIPES: return new String[]{"X.X", ".X."};
            default: return new String[]{"XXX", ".X."};
        }
    }

    static void paintChest(BufferedImage im, Outfit o) {
        int m = o.main;
        // torse
        rect(im, 16, 20, 4, 12, m); rect(im, 20, 20, 8, 12, m); rect(im, 28, 20, 4, 12, m); rect(im, 32, 20, 8, 12, m);
        rect(im, 20, 16, 8, 4, m); rect(im, 28, 16, 8, 4, shade(m, 0.8));
        // bras
        int armLen = (o.style == Style.TEE || o.style == Style.POLO) ? 4 : 12;
        for (int x : new int[]{40, 44, 48, 52}) rect(im, x, 20, 4, armLen, m);
        rect(im, 44, 16, 4, 4, m); rect(im, 48, 16, 4, 4, shade(m, 0.8));
        if (armLen == 4) for (int x : new int[]{40, 44, 48, 52}) rect(im, x, 23, 4, 1, o.accent == WHITE || o.accent == BLACK ? shade(m, 0.85) : o.accent);
        // poignets / bas
        if (o.style == Style.HOODIE || o.style == Style.JACKET || o.style == Style.PUFFER) {
            for (int x : new int[]{40, 44, 48, 52}) rect(im, x, 30, 4, 2, o.accent == m ? shade(m, 0.7) : o.style == Style.HOODIE ? shade(m, 0.75) : o.accent);
            for (int x : new int[]{16, 20, 28, 32}) rect(im, x, 30, x == 20 || x == 32 ? 8 : 4, 2, shade(m, 0.75));
        }
        switch (o.style) {
            case HOODIE:
                rect(im, 24, 20, 2, 3, shade(m, 0.75)); rect(im, 22, 20, 1, 3, o.accent); rect(im, 25, 20, 1, 3, o.accent); // cordons
                rect(im, 22, 27, 4, 3, shade(m, 0.85)); // poche kangourou
                break;
            case JACKET:
                rect(im, 23, 20, 2, 12, o.accent); rect(im, 23, 20, 1, 12, shade(o.accent, 0.8)); // zip centre
                rect(im, 20, 20, 8, 1, shade(m, 0.7)); // col
                if (o.logo == Logo.STRIPES) { // 3 bandes sur manches
                    for (int x : new int[]{40, 52}) { rect(im, x + 0, 20, 1, 10, o.accent); rect(im, x + 2, 20, 1, 10, o.accent); }
                    for (int x : new int[]{44, 48}) { rect(im, x + (x == 44 ? 0 : 3), 20, 1, 10, o.accent); }
                    rect(im, 41, 20, 1, 10, o.accent); rect(im, 43, 20, 1, 10, 0xFF000000 | m);
                    rect(im, 41, 20, 1, 10, o.accent); rect(im, 53, 20, 1, 10, o.accent);
                }
                break;
            case PUFFER:
                for (int y = 23; y < 32; y += 3) { for (int x : new int[]{16, 28}) rect(im, x, y, 4, 1, shade(m, 0.6)); rect(im, 20, y, 8, 1, shade(m, 0.6)); rect(im, 32, y, 8, 1, shade(m, 0.6)); }
                for (int y = 23; y < 32; y += 3) for (int x : new int[]{40, 44, 48, 52}) rect(im, x, y, 4, 1, shade(m, 0.6));
                rect(im, 23, 20, 2, 12, o.accent);
                rect(im, 20, 20, 8, 2, shade(m, 0.65));
                rect(im, 44, 20, 4, 2, o.accent); rect(im, 40, 20, 4, 1, o.accent);
                break;
            case POLO:
                rect(im, 21, 20, 6, 1, WHITE == o.accent ? WHITE : o.accent); rect(im, 23, 21, 2, 3, shade(m, 0.8)); // col + patte
                px(im, 23, 22, o.logoC); px(im, 24, 22, o.logoC);
                break;
            case DENIM:
                rect(im, 23, 20, 2, 12, shade(m, 0.7)); // boutonnage
                for (int y = 22; y < 32; y += 3) px(im, 24, y, o.accent);
                rect(im, 21, 23, 2, 2, shade(m, 0.8)); rect(im, 26, 23, 2, 2, shade(m, 0.8)); // poches poitrine
                break;
            default: break;
        }
        // logo
        String[] bm = bitmap(o.logo);
        if (o.logo == Logo.MONO) {
            for (int y = 22; y < 32; y += 4) for (int x = 20; x < 28; x += 4) drawBitmap(im, x, y, bm, o.logoC);
            for (int y = 24; y < 32; y += 4) for (int x = 18; x < 40; x += 4) if (x >= 32 && x < 40) drawBitmap(im, x, y, bm, o.logoC);
        } else if (o.logo == Logo.BOX) {
            rect(im, 21, 24, 6, 4, o.logoC == WHITE ? RED : o.logoC);
            rect(im, 22, 25, 4, 2, WHITE);
        } else if (o.style == Style.POLO) {
            drawBitmap(im, 21, 25, small(o.logo), o.logoC);
        } else if (o.logo == Logo.STRIPES) {
            drawBitmap(im, 21, 25, small(o.logo), o.logoC);
        } else {
            drawBitmap(im, 20 + 1, 23, bm, o.logoC);
        }
        // dos : petit logo
        if (o.logo != Logo.MONO) drawBitmap(im, 34, 22, small(o.logo), shade(o.logoC, 0.9));
    }

    static void paintBoots(BufferedImage im, Outfit o) {
        // jambe layer_1 : y 20..31, on remplit les 5 derniers pixels
        for (int x : new int[]{0, 4, 8, 12}) {
            rect(im, x, 27, 4, 5, o.shoe);
            rect(im, x, 31, 4, 1, o.sole);
            rect(im, x, 30, 4, 1, shade(o.shoe, 0.9));
        }
        drawBitmap(im, 0, 28, new String[]{"..XX", "XXX."}, o.logo == Logo.STRIPES ? o.sole : o.sole == o.shoe ? BLACK : o.sole);
        rect(im, 4, 27, 4, 1, shade(o.shoe, 0.8)); // lacets
    }

    static void paintLegs(BufferedImage im, Outfit o) {
        int p = o.pants;
        for (int x : new int[]{0, 4, 8, 12}) rect(im, x, 20, 4, 12, p);
        rect(im, 4, 16, 4, 4, p); rect(im, 8, 16, 4, 4, shade(p, 0.8));
        // ceinture sur le torse (layer_2 body)
        rect(im, 16, 29, 4, 3, shade(p, 0.8)); rect(im, 20, 29, 8, 3, shade(p, 0.8)); rect(im, 28, 29, 4, 3, shade(p, 0.8)); rect(im, 32, 29, 8, 3, shade(p, 0.8));
        rect(im, 20, 29, 8, 1, o.accent == p ? shade(p, 0.6) : o.accent);
        if (o.logo == Logo.STRIPES) { rect(im, 0, 20, 1, 12, o.accent); rect(im, 2, 20, 1, 12, o.accent); rect(im, 8 + 3, 20, 1, 12, o.accent); }
        else if (o.style == Style.DENIM) { rect(im, 4, 20, 1, 2, shade(p, 0.7)); px(im, 5, 22, o.accent); }
        else if (o.logo == Logo.SWOOSH) drawBitmap(im, 0, 22, new String[]{"..X", "XX."}, o.logoC);
        else if (o.logo == Logo.MONO) { for (int x : new int[]{0, 4, 8, 12}) for (int y = 22; y < 32; y += 4) px(im, x + 1, y, o.logoC); }
        for (int x : new int[]{0, 8}) rect(im, x + 3, 20, 1, 12, shade(p, 0.9));
    }

    // ---------- icones ----------
    static String[] shirtShape(Style s) {
        boolean longSleeve = s != Style.TEE && s != Style.POLO;
        String[] a = {
                "................",
                "...XXXXXXXXXX...",
                "..XXXXX..XXXXX..",
                ".XXXXXXXXXXXXXX.",
                ".XXXXXXXXXXXXXX.",
                longSleeve ? ".XXXXXXXXXXXXXX." : "..XXXXXXXXXXXX..",
                longSleeve ? ".XXXXXXXXXXXXXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXXXXXXXXXXXXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXX.XXXXXX.XXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXX.XXXXXX.XXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXX.XXXXXX.XXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXX.XXXXXX.XXX." : "...XXXXXXXXXX...",
                longSleeve ? ".XXX.XXXXXX.XXX." : "...XXXXXXXXXX...",
                "................", "................", "................"};
        return a;
    }
    static void shape(BufferedImage im, String[] sh, int rgb, java.util.function.BiFunction<Integer, Integer, Integer> fn) {
        for (int y = 0; y < sh.length; y++) for (int x = 0; x < 16; x++) if (sh[y].charAt(x) == 'X') {
            int c = fn == null ? rgb : fn.apply(x, y); px(im, x, y, c);
        }
        // contour
        for (int y = 0; y < 16; y++) for (int x = 0; x < 16; x++) {
            if ((im.getRGB(x, y) >>> 24) != 0) continue;
            boolean n = false;
            for (int[] d : new int[][]{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}) {
                int nx = x + d[0], ny = y + d[1];
                if (nx >= 0 && ny >= 0 && nx < 16 && ny < 16 && (im.getRGB(nx, ny) >>> 24) != 0 && (im.getRGB(nx, ny) & 0xFFFFFF) != 0x101010) n = true;
            }
            if (n) im.setRGB(x, y, 0xFF101010);
        }
    }

    static BufferedImage iconChest(Outfit o) {
        BufferedImage im = newImg(16, 16);
        String[] sh = shirtShape(o.style);
        shape(im, sh, o.main, (x, y) -> y == 1 || y == 2 ? shade(o.main, 0.85) : o.main);
        if (o.style == Style.JACKET || o.style == Style.PUFFER || o.style == Style.DENIM) rect(im, 7, 3, 2, 10, o.style == Style.DENIM ? shade(o.main, 0.7) : o.accent);
        if (o.style == Style.POLO) { rect(im, 6, 1, 4, 1, o.accent); rect(im, 7, 3, 2, 3, shade(o.main, 0.8)); }
        if (o.style == Style.HOODIE) { rect(im, 5, 2, 6, 1, shade(o.main, 0.7)); rect(im, 5, 9, 6, 3, shade(o.main, 0.85)); }
        if (o.style == Style.PUFFER) for (int y = 5; y < 13; y += 3) rect(im, 2, y, 12, 1, shade(o.main, 0.65));
        drawBitmap(im, 9, 5, o.logo == Logo.BOX ? new String[]{"XX", "XX"} : small(o.logo), o.logoC);
        return im;
    }
    static BufferedImage iconLegs(Outfit o) {
        BufferedImage im = newImg(16, 16);
        String[] sh = {"................", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "...XXXX..XXXX...", "................", "................", "................"};
        shape(im, sh, o.pants, null);
        rect(im, 4, 1, 8, 1, o.accent == o.pants ? shade(o.pants, 0.7) : o.accent);
        if (o.logo == Logo.STRIPES) { rect(im, 4, 3, 1, 10, o.accent); }
        return im;
    }
    static BufferedImage iconBoots(Outfit o) {
        BufferedImage im = newImg(16, 16);
        String[] sh = {"................", "................", "................", "................", "...XXXX.........", "...XXXX.........", "...XXXXX........", "...XXXXXX.......", "..XXXXXXXXX.....", ".XXXXXXXXXXXX...", ".XXXXXXXXXXXX...", ".XXXXXXXXXXXX...", "................", "................", "................", "................"};
        shape(im, sh, o.shoe, (x, y) -> y >= 11 ? o.sole : o.shoe);
        drawBitmap(im, 5, 8, new String[]{"XX", "X."}, o.sole == o.shoe ? BLACK : o.sole);
        rect(im, 4, 4, 4, 1, shade(o.shoe, 0.75));
        return im;
    }
    static BufferedImage iconCap(Outfit o) {
        BufferedImage im = newImg(16, 16);
        String[] capS = {"................", "................", "................", "......XXXX......", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXXXX.", "...XXXXXXXXXXXX.", "................", "................", "................", "................", "................", "................", "................"};
        String[] beaS = {"................", "................", ".....XXXXXX.....", "....XXXXXXXX....", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "...XXXXXXXXXX...", "................", "................", "................", "................", "................", "................"};
        shape(im, o.beanie ? beaS : capS, o.cap, (x, y) -> o.beanie && y >= 8 ? o.accent : (!o.beanie && y >= 7 && x >= 11) ? shade(o.cap, 0.7) : o.cap);
        if (!o.beanie) drawBitmap(im, 6, 5, new String[]{"..X", "XX."}, o.logoC);
        return im;
    }

    // ---------- main ----------
    public static void main(String[] a) throws Exception {
        Path root = Paths.get(a[0]);
        Path res = root.resolve("src/main/resources/assets/minenorth_vetements");
        Path armor = res.resolve("textures/models/armor"), icons = res.resolve("textures/item"), models = res.resolve("models/item");
        Files.createDirectories(armor); Files.createDirectories(icons); Files.createDirectories(models);
        define();
        StringBuilder lang = new StringBuilder("{\n  \"itemGroup.minenorth_vetements\": \"Vetements de marque\"");
        StringBuilder java = new StringBuilder("package com.minenorth_vetements;\n\n/** Genere par tools/Gen.java - ne pas editer. */\nfinal class OutfitData {\n    record Outfit(String id, String name, boolean cap, boolean chest, boolean legs, boolean boots) {}\n\n    static final Outfit[] ALL = {\n");
        for (Outfit o : outfits) {
            BufferedImage l1 = newImg(64, 32), l2 = newImg(64, 32);
            if (o.hasCap) paintHead(l1, o);
            if (o.hasChest) paintChest(l1, o);
            if (o.hasBoots) paintBoots(l1, o);
            if (o.hasLegs) paintLegs(l2, o);
            ImageIO.write(l1, "png", armor.resolve(o.id + "_layer_1.png").toFile());
            ImageIO.write(l2, "png", armor.resolve(o.id + "_layer_2.png").toFile());
            java.append(String.format("        new Outfit(\"%s\", \"%s\", %b, %b, %b, %b),\n", o.id, o.fr, o.hasCap, o.hasChest, o.hasLegs, o.hasBoots));
            String[][] pieces = {{"helmet", "cap"}, {"chestplate", "chest"}, {"leggings", "legs"}, {"boots", "boots"}};
            boolean[] has = {o.hasCap, o.hasChest, o.hasLegs, o.hasBoots};
            String[] suffix = {o.beanie ? "Bonnet" : "Casquette", "Haut", "Pantalon", "Chaussures"};
            for (int i = 0; i < 4; i++) {
                if (!has[i]) continue;
                String n = o.id + "_" + pieces[i][0];
                BufferedImage ic = i == 0 ? iconCap(o) : i == 1 ? iconChest(o) : i == 2 ? iconLegs(o) : iconBoots(o);
                ImageIO.write(ic, "png", icons.resolve(n + ".png").toFile());
                Files.writeString(models.resolve(n + ".json"), "{\n  \"parent\": \"item/generated\",\n  \"textures\": {\"layer0\": \"minenorth_vetements:item/" + n + "\"}\n}\n");
                lang.append(",\n  \"item.minenorth_vetements.").append(n).append("\": \"").append(o.fr).append(" - ").append(suffix[i]).append("\"");
            }
        }
        lang.append("\n}\n");
        java.append("    };\n\n    private OutfitData() {}\n}\n");
        Files.writeString(res.resolve("lang/fr_fr.json"), lang.toString());
        Files.writeString(res.resolve("lang/en_us.json"), lang.toString());
        Files.writeString(root.resolve("src/main/java/com/minenorth_vetements/OutfitData.java"), java.toString());
        System.out.println("OK " + outfits.size() + " tenues");
    }
}
