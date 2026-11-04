package com.minenorth_vetements;

import java.util.HashMap;
import java.util.Map;

/** Généré par tools/gen_streetwear.py - ne pas éditer. Accessoires portés en plus des vêtements, par emplacement. */
final class AccessoryData {
    private AccessoryData() {}

    /** legacy : ancien objet enregistré par OutfitData sous le nom id + "_helmet". */
    record Acc(String id, AccSlot slot, boolean legacy) {}

    static final Map<String, Acc> BY_ID = new HashMap<>();

    static {
        put("lunettes_aviator", AccSlot.VISAGE, true);
        put("lunettes_wayfarer", AccSlot.VISAGE, true);
        put("lunettes_sport", AccSlot.VISAGE, true);
        put("lunettes_rose", AccSlot.VISAGE, true);
        put("cagoule_noire", AccSlot.VISAGE, true);
        put("cagoule_kaki", AccSlot.VISAGE, true);
        put("cagoule_guchi", AccSlot.VISAGE, true);
        put("cagoule_guchi_noire", AccSlot.VISAGE, true);
        put("cagoule_vuiten", AccSlot.VISAGE, true);
        put("cagoule_supreem", AccSlot.VISAGE, true);
        put("cagoule_nayk", AccSlot.VISAGE, true);
        put("bandana_rouge", AccSlot.VISAGE, true);
        put("bandana_noir", AccSlot.VISAGE, true);
        put("echarpe_grise", AccSlot.COU, true);
        put("echarpe_rouge", AccSlot.COU, true);
        put("lunettes_rondes", AccSlot.VISAGE, false);
        put("lunettes_masque", AccSlot.VISAGE, false);
        put("chaine_or", AccSlot.COU, false);
        put("chaine_argent", AccSlot.COU, false);
        put("chaine_croix", AccSlot.COU, false);
        put("collier_perles", AccSlot.COU, false);
        put("echarpe_noire", AccSlot.COU, false);
        put("montre_or", AccSlot.POIGNET, false);
        put("montre_argent", AccSlot.POIGNET, false);
        put("montre_sport", AccSlot.POIGNET, false);
        put("gourmette_or", AccSlot.POIGNET, false);
        put("gants_cuir_noir", AccSlot.MAINS, false);
        put("gants_cuir_marron", AccSlot.MAINS, false);
        put("gants_laine", AccSlot.MAINS, false);
        put("sac_dos_noir", AccSlot.DOS, false);
        put("sac_dos_rouge", AccSlot.DOS, false);
        put("sac_dos_kaki", AccSlot.DOS, false);
        put("banane_noire", AccSlot.DOS, false);
        put("banane_guchi", AccSlot.DOS, false);
        put("sacoche_noire", AccSlot.DOS, false);
        put("sacoche_lacroste", AccSlot.DOS, false);
        put("banane_nayk", AccSlot.DOS, false);
        put("sac_sport_noir", AccSlot.DOS, false);
        put("sac_sport_bleu", AccSlot.DOS, false);
        put("sac_rando_orange", AccSlot.DOS, false);
        put("sac_rando_vert", AccSlot.DOS, false);
        put("parachute", AccSlot.DOS, false);
        put("parachute_noir", AccSlot.DOS, false);
        put("parachute_rouge", AccSlot.DOS, false);
        put("parachute_bleu", AccSlot.DOS, false);
        put("parachute_vip", AccSlot.DOS, false);
        put("parachute_prestige", AccSlot.DOS, false);
        put("sac_luxe_vuiten", AccSlot.DOS, false);
        put("chaine_vip", AccSlot.COU, false);
        put("montre_vip", AccSlot.POIGNET, false);
        put("chaine_diamant", AccSlot.COU, false);
        put("montre_diamant", AccSlot.POIGNET, false);
        put("sac_vip", AccSlot.DOS, false);
        put("lunettes_holo", AccSlot.VISAGE, false);
        put("gants_pompier", AccSlot.MAINS, false);
        put("gants_moto_racing", AccSlot.MAINS, false);
        put("gants_moto_cuir", AccSlot.MAINS, false);
        put("gants_moto_hiver", AccSlot.MAINS, false);
    }

    private static void put(String id, AccSlot slot, boolean legacy) { BY_ID.put(id, new Acc(id, slot, legacy)); }

    /** Nouveaux accessoires (enregistrés sous leur id), dans l'ordre du catalogue. */
    static final String[] NEW = {"lunettes_rondes", "lunettes_masque", "chaine_or", "chaine_argent", "chaine_croix", "collier_perles", "echarpe_noire", "montre_or", "montre_argent", "montre_sport", "gourmette_or", "gants_cuir_noir", "gants_cuir_marron", "gants_laine", "sac_dos_noir", "sac_dos_rouge", "sac_dos_kaki", "banane_noire", "banane_guchi", "sacoche_noire", "sacoche_lacroste", "banane_nayk", "sac_sport_noir", "sac_sport_bleu", "sac_rando_orange", "sac_rando_vert", "parachute", "parachute_noir", "parachute_rouge", "parachute_bleu", "parachute_vip", "parachute_prestige", "sac_luxe_vuiten", "chaine_vip", "montre_vip", "chaine_diamant", "montre_diamant", "sac_vip", "lunettes_holo", "gants_pompier", "gants_moto_racing", "gants_moto_cuir", "gants_moto_hiver"};
}
