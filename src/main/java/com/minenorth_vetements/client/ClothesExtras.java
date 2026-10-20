package com.minenorth_vetements.client;

import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.world.entity.EquipmentSlot;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Relief des tenues : capuches, cols, poches, ourlets, pantalons amples, semelles... Chaque pièce est un cube dépassant de la
 * couche d'armure vanilla, coloré avec une « pastille » de la texture de la tenue (zone libre x 32-64 / y 0-16 des layers).
 */
final class ClothesExtras {
    private ClothesExtras() {}

    enum Style { TEE, HOODIE, JACKET, POLO, PUFFER, DENIM, SUIT, GOWN, MINI, SWIM, AVIATOR, WAYFARER, SPORT, BALA, BANDANA, SCARF }

    // Pastilles (voir tools : 4x4 px chacune, ligne 0 puis ligne 1)
    static final int M = 0, A = 1, L = 2, P = 3, S = 4, O = 5, C = 6, D = 7, H = 8, PD = 9, SD = 10, AD = 11;

    /** Taille virtuelle de la texture : les cubes n'échantillonnent qu'un point de la pastille choisie. */
    private static final int VIRT_W = 1024, VIRT_H = 512, SCALE = 16;

    record Box(String part, float x0, float y0, float z0, float x1, float y1, float z1, int swatch) {}

    static Style styleOf(String id) {
        return switch (id) {
            case "lunettes_aviator", "lunettes_rose" -> Style.AVIATOR;
            case "lunettes_wayfarer" -> Style.WAYFARER;
            case "lunettes_sport" -> Style.SPORT;
            case "cagoule_noire", "cagoule_kaki" -> Style.BALA;
            case "bandana_rouge", "bandana_noir" -> Style.BANDANA;
            case "echarpe_grise", "echarpe_rouge" -> Style.SCARF;
            case "costard_noir", "costard_marine", "costard_blanc", "costard_gris", "smoking" -> Style.SUIT;
            case "robe_soiree_rouge", "robe_soiree_noire" -> Style.GOWN;
            case "robe_cocktail", "robe_ete" -> Style.MINI;
            case "bikini_rouge", "bikini_turquoise", "bikini_noir", "maillot_bleu", "maillot_tropical" -> Style.SWIM;
            case "nayk_noir", "nayk_gris", "supreem_noir", "champyon_gris" -> Style.HOODIE;
            case "abidas_bleu", "abidas_noir", "louis_vuiten" -> Style.JACKET;
            case "lacroste_vert", "lacroste_blanc", "guchi_vert" -> Style.POLO;
            case "nord_fasse" -> Style.PUFFER;
            case "levys_jean" -> Style.DENIM;
            default -> Style.TEE;
        };
    }

    /** Tenues dont le relief 3D est dessiné : casquettes (tête), costards, robes, accessoires. Les anciens hauts / pantalons restent à plat (textures seules). */
    static boolean hasRelief(EquipmentSlot slot, Style style) {
        return slot == EquipmentSlot.HEAD || switch (style) {
            case SUIT, GOWN, MINI, SCARF -> true;
            default -> false;
        };
    }

    static boolean beanie(String id) {
        return false;   // plus de bonnets : tout le monde porte des casquettes (les bonnets tombaient devant les yeux)
    }

    private static final Map<String, Map<String, ModelPart>> CACHE = new HashMap<>();

    /** Pièces (par partie du corps) à dessiner pour cette tenue et cet emplacement. */
    static Map<String, ModelPart> parts(EquipmentSlot slot, Style style, boolean beanie) {
        String key = slot + "/" + style + "/" + beanie;
        return CACHE.computeIfAbsent(key, k -> bake(boxes(slot, style, beanie)));
    }

    private static Map<String, ModelPart> bake(List<Box> boxes) {
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();
        Map<String, CubeListBuilder> builders = new HashMap<>();
        for (Box b : boxes) {
            int u = 32 * SCALE + 4 * (b.swatch() % 8) * SCALE + 8;
            int v = 4 * (b.swatch() / 8) * SCALE + 8;
            builders.computeIfAbsent(b.part(), n -> CubeListBuilder.create())
                    .texOffs(u, v).addBox(b.x0(), b.y0(), b.z0(), b.x1() - b.x0(), b.y1() - b.y0(), b.z1() - b.z0());
        }
        builders.forEach((name, cubes) -> root.addOrReplaceChild(name, cubes, PartPose.ZERO));
        ModelPart baked = LayerDefinition.create(mesh, VIRT_W, VIRT_H).bakeRoot();
        Map<String, ModelPart> out = new HashMap<>();
        for (String name : builders.keySet()) out.put(name, baked.getChild(name));
        return out;
    }

    private static void both(List<Box> l, String part, float x0, float y0, float z0, float x1, float y1, float z1, int sw) {
        l.add(new Box(part, x0, y0, z0, x1, y1, z1, sw));
    }

    /** Pièce symétrique sur les deux côtés (x miroir), sur deux parties du corps (right_ / left_). */
    private static void pair(List<Box> l, String right, String left, float x0, float y0, float z0, float x1, float y1, float z1, int sw) {
        l.add(new Box(right, x0, y0, z0, x1, y1, z1, sw));
        l.add(new Box(left, -x1, y0, z0, -x0, y1, z1, sw));
    }

    static List<Box> boxes(EquipmentSlot slot, Style style, boolean beanie) {
        List<Box> l = new ArrayList<>();
        switch (slot) {
            case HEAD -> {
                switch (style) {
                    case AVIATOR, WAYFARER -> {
                        boolean w = style == Style.WAYFARER;
                        both(l, "head", -4.3f, -5.4f, -4.7f, -0.2f, w ? -2.2f : -1.8f, -4.45f, M);     // monture gauche
                        both(l, "head", 0.2f, -5.4f, -4.7f, 4.3f, w ? -2.2f : -1.8f, -4.45f, M);       // monture droite
                        both(l, "head", -3.9f, w ? -4.8f : -5.0f, -4.9f, -0.6f, w ? -2.6f : -2.2f, -4.7f, A);   // verre gauche
                        both(l, "head", 0.6f, w ? -4.8f : -5.0f, -4.9f, 3.9f, w ? -2.6f : -2.2f, -4.7f, A);     // verre droit
                        if (!w) { both(l, "head", -3.2f, -2.2f, -4.9f, -1.3f, -1.6f, -4.7f, A); both(l, "head", 1.3f, -2.2f, -4.9f, 3.2f, -1.6f, -4.7f, A); }
                        if (w) both(l, "head", -4.4f, -5.7f, -4.8f, 4.4f, -4.9f, -4.4f, M);            // arcade épaisse
                        both(l, "head", -0.3f, -4.8f, -4.85f, 0.3f, -4.2f, -4.45f, M);                 // pont
                        both(l, "head", -4.6f, -5.0f, -4.6f, -4.3f, -4.3f, 4.0f, M);                   // branches
                        both(l, "head", 4.3f, -5.0f, -4.6f, 4.6f, -4.3f, 4.0f, M);
                        both(l, "head", -3.6f, -4.9f, -4.95f, -2.6f, -4.4f, -4.85f, L);                // reflet
                    }
                    case SPORT -> {
                        both(l, "head", -4.4f, -5.2f, -4.9f, 4.4f, -2.8f, -4.5f, A);                   // verre miroir enveloppant
                        both(l, "head", -4.6f, -5.7f, -4.95f, 4.6f, -5.2f, -4.4f, M);                  // arcade
                        both(l, "head", -4.7f, -5.2f, -4.7f, -4.3f, -3.0f, 3.6f, M);                   // branches enveloppantes
                        both(l, "head", 4.3f, -5.2f, -4.7f, 4.7f, -3.0f, 3.6f, M);
                        both(l, "head", -0.7f, -4.6f, -5.0f, 0.7f, -3.6f, -4.85f, L);                  // nez
                    }
                    case BALA -> {
                        both(l, "head", -4.6f, -1.4f, -4.6f, 4.6f, 0.6f, 4.6f, D);                     // col roulé
                        both(l, "head", -3.6f, -5.2f, -4.6f, 3.6f, -4.7f, -4.35f, H);                  // ourlet au-dessus des yeux
                        both(l, "head", -3.6f, -3.3f, -4.6f, 3.6f, -2.8f, -4.35f, H);                  // ourlet sous les yeux
                        both(l, "head", -4.5f, -8.5f, -4.5f, 4.5f, -8.0f, 4.5f, D);                    // sommet côtelé
                    }
                    case BANDANA -> {
                        both(l, "head", -4.5f, -3.3f, -4.5f, 4.5f, 0.4f, 4.5f, M);                     // tissu sur le bas du visage
                        both(l, "head", -2.8f, -2.3f, -4.65f, -1.6f, -1.3f, -4.45f, L);                // motifs
                        both(l, "head", 1.6f, -2.8f, -4.65f, 2.8f, -1.8f, -4.45f, L);
                        both(l, "head", -0.6f, -1.2f, -4.65f, 0.6f, -0.3f, -4.45f, L);
                        both(l, "head", -2.5f, 0.2f, -4.2f, 2.5f, 1.7f, -3.5f, M);                     // pointe sous le menton
                        both(l, "head", -1.3f, -3.0f, 4.5f, 1.3f, -0.8f, 5.4f, D);                     // nœud
                        both(l, "head", -2.3f, -0.8f, 4.8f, -1.0f, 2.0f, 5.3f, D);                     // pans
                        both(l, "head", 1.0f, -0.8f, 4.8f, 2.3f, 2.0f, 5.3f, D);
                    }
                    case SCARF -> {
                        both(l, "body", -4.7f, -2.4f, -2.9f, 4.7f, 0.8f, 2.9f, M);                     // tour de cou
                        both(l, "body", -4.9f, 0.4f, -3.1f, 4.9f, 2.0f, 3.1f, D);                      // second tour
                        both(l, "body", 0.8f, 1.4f, -3.5f, 3.4f, 8.2f, -3.0f, M);                      // pan long
                        both(l, "body", 0.8f, 8.2f, -3.5f, 3.4f, 9.0f, -3.0f, L);                      // frange
                        both(l, "body", -3.2f, 1.4f, -3.4f, -0.8f, 5.6f, -2.95f, D);                   // pan court
                    }
                    default -> { }
                }
                if (style == Style.AVIATOR || style == Style.WAYFARER || style == Style.SPORT || style == Style.BALA || style == Style.BANDANA || style == Style.SCARF) break;
                // casquette : calotte haute, visière courbe, œillets, patte arrière. Tout reste au-dessus des yeux (y < -5,6).
                both(l, "head", -5.4f, -10.2f, -5.4f, 5.4f, -6.6f, 5.4f, C);            // calotte
                both(l, "head", -5.5f, -7.0f, -5.5f, 5.5f, -6.5f, 5.5f, D);             // bandeau
                both(l, "head", -4.9f, -6.8f, -8.3f, 4.9f, -5.9f, -5.0f, C);            // visière (base)
                both(l, "head", -4.4f, -7.2f, -10.6f, 4.4f, -6.3f, -8.3f, C);           // visière (bout relevé)
                both(l, "head", -4.9f, -6.2f, -8.3f, 4.9f, -5.9f, -5.0f, D);            // dessous ombré
                both(l, "head", -0.5f, -10.5f, -0.5f, 0.5f, -10.2f, 0.5f, D);           // bouton du dessus
                both(l, "head", -1.0f, -9.6f, -5.8f, 1.0f, -7.6f, -5.4f, L);            // écusson
                both(l, "head", -2.4f, -7.4f, 5.3f, 2.4f, -6.6f, 5.9f, A);              // patte de réglage
            }
            case CHEST -> {
                switch (style) {
                    case SUIT -> {
                        both(l, "body", -3.6f, -2.0f, 2.9f, 3.6f, 0.2f, 3.9f, M);      // col de la veste
                        both(l, "body", -4.4f, -0.2f, -3.9f, -1.0f, 6.0f, -3.4f, D);   // revers gauche
                        both(l, "body", 1.0f, -0.2f, -3.9f, 4.4f, 6.0f, -3.4f, D);     // revers droit
                        both(l, "body", -4.7f, 10.2f, -3.2f, 4.7f, 14.0f, 3.4f, M);    // basques de la veste
                        both(l, "body", -3.8f, 9.0f, -3.9f, -1.4f, 9.5f, -3.4f, D);    // rabats de poches
                        both(l, "body", 1.4f, 9.0f, -3.9f, 3.8f, 9.5f, -3.4f, D);
                        pair(l, "right_arm", "left_arm", -4.6f, -2.0f, -3.4f, 2.6f, 1.0f, 3.4f, M);   // épaulettes
                        pair(l, "right_arm", "left_arm", -4.4f, 10.3f, -3.3f, 2.4f, 11.1f, 3.3f, L);   // poignets de chemise
                    }
                    case GOWN, MINI -> {
                        both(l, "body", -4.4f, 5.2f, -3.3f, 4.4f, 6.4f, 3.3f, D);      // ceinture marquée
                        both(l, "body", -4.2f, -0.6f, -3.3f, -0.8f, 0.8f, -2.8f, M);    // bonnets du décolleté
                        both(l, "body", 0.8f, -0.6f, -3.3f, 4.2f, 0.8f, -2.8f, M);
                    }
                    case SWIM -> { }
                    case TEE -> {
                        both(l, "body", -3.4f, -1.5f, -3.5f, 3.4f, 0.2f, 3.5f, A);   // col rond
                        pair(l, "right_arm", "left_arm", -4.6f, 1.8f, -3.6f, 2.6f, 3.0f, 3.6f, A);
                    }
                    case POLO -> {
                        both(l, "body", -4.4f, -2.4f, -3.9f, -0.1f, 0.8f, -2.7f, H);  // col gauche
                        both(l, "body", 0.1f, -2.4f, -3.9f, 4.4f, 0.8f, -2.7f, H);    // col droit
                        both(l, "body", -3.4f, -1.6f, 2.8f, 3.4f, 0.4f, 3.6f, H);     // col arrière
                        both(l, "body", -0.8f, 0.4f, -3.6f, 0.8f, 5.2f, -3.1f, D);    // patte de boutonnage
                        pair(l, "right_arm", "left_arm", -4.6f, 1.8f, -3.6f, 2.6f, 3.0f, 3.6f, D);
                    }
                    case HOODIE -> {
                        both(l, "body", -4.8f, -3.2f, 2.8f, 4.8f, 3.0f, 5.4f, M);     // capuche dans le dos
                        both(l, "body", -5.8f, -2.4f, -1.6f, -4.4f, 1.6f, 3.6f, H);   // côtés de la capuche
                        both(l, "body", 4.4f, -2.4f, -1.6f, 5.8f, 1.6f, 3.6f, H);
                        both(l, "body", -2.0f, 0.4f, -3.8f, -1.3f, 4.6f, -3.3f, L);   // cordons
                        both(l, "body", 1.3f, 0.4f, -3.8f, 2.0f, 4.6f, -3.3f, L);
                        both(l, "body", -3.8f, 8.2f, -3.7f, 3.8f, 11.6f, -3.1f, D);   // poche kangourou
                        both(l, "body", -5.5f, 10.6f, -3.6f, 5.5f, 13.4f, 3.6f, D);   // bas côtelé
                        pair(l, "right_arm", "left_arm", -4.6f, 7.8f, -3.6f, 2.6f, 11.0f, 3.6f, D);
                    }
                    case JACKET -> {
                        both(l, "body", -3.8f, -2.8f, -3.8f, 3.8f, 0.4f, 3.8f, D);    // col montant
                        both(l, "body", -0.4f, -1.0f, -3.7f, 0.4f, 13.1f, -3.2f, A);  // zip
                        both(l, "body", -5.5f, 11.0f, -3.6f, 5.5f, 13.4f, 3.6f, D);   // bas
                        pair(l, "right_arm", "left_arm", -4.6f, 8.4f, -3.6f, 2.6f, 11.2f, 3.6f, D);
                    }
                    case PUFFER -> {
                        both(l, "body", -4.0f, -3.6f, -4.0f, 4.0f, 0.4f, 4.0f, A);    // col haut
                        for (float y : new float[]{0.2f, 4.2f, 8.2f}) both(l, "body", -5.7f, y, -3.8f, 5.7f, y + 3.5f, 3.8f, M);
                        for (float y : new float[]{-0.8f, 4.6f}) pair(l, "right_arm", "left_arm", -4.8f, y, -3.8f, 2.8f, y + 4.4f, 3.8f, M);
                    }
                    case DENIM -> {
                        both(l, "body", -3.6f, -2.0f, -3.7f, 3.6f, 0.2f, 3.7f, D);    // col
                        both(l, "body", -4.2f, 2.4f, -3.7f, -1.4f, 5.2f, -3.2f, D);   // poches poitrine
                        both(l, "body", 1.4f, 2.4f, -3.7f, 4.2f, 5.2f, -3.2f, D);
                        both(l, "body", -4.2f, 2.4f, -3.9f, -1.4f, 3.4f, -3.5f, A);   // rabats
                        both(l, "body", 1.4f, 2.4f, -3.9f, 4.2f, 3.4f, -3.5f, A);
                        both(l, "body", -5.5f, 11.0f, -3.6f, 5.5f, 13.4f, 3.6f, D);
                        pair(l, "right_arm", "left_arm", -4.6f, 8.4f, -3.6f, 2.6f, 11.2f, 3.6f, D);
                    }
                }
            }
            case LEGS -> {
                if (style == Style.SWIM) break;
                if (style == Style.SUIT) {
                    both(l, "body", -4.7f, 10.2f, -2.9f, 4.7f, 11.4f, 2.9f, PD);   // ceinture
                    both(l, "body", -1.0f, 10.2f, -3.3f, 1.0f, 11.4f, -2.8f, O);   // boucle
                    break;
                }
                if (style == Style.GOWN || style == Style.MINI) {
                    boolean gown = style == Style.GOWN;
                    both(l, "body", -4.6f, 10.0f, -3.2f, 4.6f, 14.0f, 3.2f, P);                       // hanches
                    both(l, "body", -5.4f, 14.0f, -3.9f, 5.4f, gown ? 19.0f : 17.0f, 3.9f, P);       // évasement
                    both(l, "body", -6.2f, gown ? 19.0f : 17.0f, -4.6f, 6.2f, gown ? 23.4f : 18.4f, 4.6f, PD);   // bas de la robe
                    break;
                }
                pair(l, "right_leg", "left_leg", -2.9f, 0.6f, -2.9f, 2.9f, 9.8f, 2.9f, P);     // jambes amples
                pair(l, "right_leg", "left_leg", -3.1f, 9.6f, -3.1f, 3.1f, 12.2f, 3.1f, PD);   // revers
                both(l, "body", -4.9f, 10.2f, -2.9f, 4.9f, 11.8f, 2.9f, PD);                   // ceinture
                both(l, "body", -1.0f, 10.2f, -3.3f, 1.0f, 11.8f, -2.8f, O);                   // boucle
                both(l, "body", -4.9f, 6.5f, -3.1f, -2.6f, 9.0f, -2.7f, PD);                   // poches avant
                both(l, "body", 2.6f, 6.5f, -3.1f, 4.9f, 9.0f, -2.7f, PD);
            }
            case FEET -> {
                if (style == Style.SUIT) {
                    pair(l, "right_leg", "left_leg", -3.1f, 11.7f, -3.7f, 3.1f, 12.5f, 3.2f, O);   // semelle fine
                    pair(l, "right_leg", "left_leg", -3.0f, 10.2f, -3.8f, 3.0f, 11.8f, -1.5f, S);   // bout verni
                    break;
                }
                if (style == Style.GOWN || style == Style.MINI) {
                    pair(l, "right_leg", "left_leg", -1.4f, 10.6f, 1.6f, 1.4f, 13.4f, 3.0f, S);     // talon aiguille
                    pair(l, "right_leg", "left_leg", -3.0f, 11.7f, -3.5f, 3.0f, 12.3f, 1.2f, O);    // semelle
                    break;
                }
                pair(l, "right_leg", "left_leg", -3.4f, 11.6f, -3.9f, 3.4f, 13.2f, 3.5f, O);   // semelle épaisse
                pair(l, "right_leg", "left_leg", -3.2f, 9.4f, -4.3f, 3.2f, 11.8f, -1.0f, S);   // bout de la chaussure
                pair(l, "right_leg", "left_leg", -3.2f, 8.6f, 2.4f, 3.2f, 12.0f, 3.7f, S);     // talon
                pair(l, "right_leg", "left_leg", -1.6f, 8.2f, -3.5f, 1.6f, 10.2f, -2.6f, O);   // languette / lacets
                pair(l, "right_leg", "left_leg", -3.4f, 7.6f, -3.4f, 3.4f, 8.9f, 3.4f, SD);    // col de la chaussure
            }
            default -> { }
        }
        return l;
    }
}
