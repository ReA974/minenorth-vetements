package com.minenorth_vetements.client;

import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.world.entity.EquipmentSlot;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Reliefs 3D générés ({@link Formes}) : casquettes, bonnets, bobs, capuches, cols, pans de manteau, chaînes, montres, gants, sacs...
 * Les cubes du torse et des bras sont dessinés pour un haut de 0,3 d'épaisseur ; {@code delta} les pousse vers l'extérieur (doudoune)
 * ou les laisse en place, pour qu'une chaîne ou une bretelle reste toujours posée sur le vêtement.
 */
final class Reliefs {
    private Reliefs() {}

    private static final String[] PARTS = {"head", "body", "right_arm", "left_arm", "right_leg", "left_leg"};
    private static final Map<String, Map<String, ModelPart>> CACHE = new HashMap<>();

    /** Pièces 3D de cette tenue / cet accessoire, ou null s'il n'a pas de forme générée. */
    static Map<String, ModelPart> parts(String id, boolean slim, float delta) { return parts(id, slim, delta, 0); }

    /** {@code headDelta} : chapeaux relevés au-dessus d'une cagoule (voir {@link SlimArmor#HAT_LIFT}). */
    static Map<String, ModelPart> parts(String id, boolean slim, float delta, float headDelta) {
        String shape = Formes.SHAPE_OF.get(id);
        if (shape == null) return null;
        float[][] rows = slim && Formes.SHAPES.containsKey(shape + "/slim") ? Formes.SHAPES.get(shape + "/slim") : Formes.SHAPES.get(shape);
        float d = Math.round(delta * 100) / 100f, h = Math.round(headDelta * 100) / 100f;
        return CACHE.computeIfAbsent(shape + "/" + slim + "/" + d + "/" + h, k -> {
            List<ClothesExtras.Box> l = new ArrayList<>();
            for (float[] r : rows) {
                String part = PARTS[(int) r[0]];
                l.add(expand(new ClothesExtras.Box(part, r[1], r[2], r[3], r[4], r[5], r[6], (int) r[7]), slim, d, h));
            }
            return ClothesExtras.bake(l);
        });
    }

    /** Anciens chapeaux / casquettes (relief {@link ClothesExtras}) relevés au-dessus d'une cagoule. */
    static Map<String, ModelPart> legacyHat(ClothesExtras.Style style, boolean beanie, float headDelta) {
        return CACHE.computeIfAbsent("legacyhat/" + style + "/" + beanie + "/" + headDelta, k -> {
            List<ClothesExtras.Box> l = new ArrayList<>();
            for (ClothesExtras.Box b : ClothesExtras.boxes(EquipmentSlot.HEAD, style, beanie))
                l.add(b.part().equals("head") ? expand(b, false, 0, headDelta) : b);
            return ClothesExtras.bake(l);
        });
    }

    /**
     * Cagoules : leur texture de tête est bien au-dessus de la couche cheveux du skin ({@link SlimArmor#BALACLAVA} au lieu de 0,25), on
     * écarte d'autant les ourlets, le col roulé et le sommet pour qu'ils restent visibles ; l'encolure posée sur les épaules suit
     * l'épaisseur du haut porté ({@code bodyDelta}, comme les autres accessoires).
     */
    static Map<String, ModelPart> legacyBalaclava(ClothesExtras.Style style, float bodyDelta) {
        float d = Math.round(bodyDelta * 100) / 100f;
        return CACHE.computeIfAbsent("legacy/" + style + "/" + d, k -> {
            List<ClothesExtras.Box> l = new ArrayList<>();
            for (ClothesExtras.Box b : ClothesExtras.boxes(EquipmentSlot.HEAD, style, false))
                l.add(expand(b, false, d, SlimArmor.BALACLAVA - 0.25f));
            return ClothesExtras.bake(l);
        });
    }

    /** Écarte de {@code d} (tête : {@code dHead}) les faces d'un cube situées hors du membre (torse, bras, tête), sans toucher aux jambes. */
    private static ClothesExtras.Box expand(ClothesExtras.Box b, boolean slim, float d, float dHead) {
        float[] c;   // xmin, xmax, ymin, ymax, zmin, zmax du membre nu
        float k = d;
        switch (b.part()) {
            case "head" -> { c = new float[]{-4, 4, -8, 0, -4, 4}; k = dHead; }
            case "body" -> c = new float[]{-4, 4, 0, 12, -2, 2};
            case "right_arm" -> c = new float[]{slim ? -2 : -3, 1, -2, 10, -2, 2};
            case "left_arm" -> c = new float[]{-1, slim ? 2 : 3, -2, 10, -2, 2};
            default -> { return b; }
        }
        if (k == 0) return b;
        return new ClothesExtras.Box(b.part(), out(b.x0(), c[0], c[1], k), out(b.y0(), c[2], c[3], k), out(b.z0(), c[4], c[5], k),
                out(b.x1(), c[0], c[1], k), out(b.y1(), c[2], c[3], k), out(b.z1(), c[4], c[5], k), b.swatch());
    }

    private static float out(float v, float lo, float hi, float d) {
        return v <= lo ? v - d : v >= hi ? v + d : v;
    }
}
