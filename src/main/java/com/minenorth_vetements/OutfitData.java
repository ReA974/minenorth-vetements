package com.minenorth_vetements;

/** Genere par tools/Gen.java - ne pas editer. */
final class OutfitData {
    record Outfit(String id, String name, boolean cap, boolean chest, boolean legs, boolean boots) {}

    static final Outfit[] ALL = {
        new Outfit("nayk_noir", "Nayk Noir", true, true, true, true),
        new Outfit("nayk_gris", "Nayk Gris", false, true, true, true),
        new Outfit("nayk_rouge", "Nayk Rouge", true, true, true, true),
        new Outfit("abidas_bleu", "Abidas Bleu", false, true, true, true),
        new Outfit("abidas_noir", "Abidas Noir", false, true, true, true),
        new Outfit("pumba_rouge", "Pumba Rouge", false, true, true, true),
        new Outfit("pumba_blanc", "Pumba Blanc", false, true, true, true),
        new Outfit("supreem_rouge", "Supreem Box Logo", true, true, false, false),
        new Outfit("supreem_noir", "Supreem Hoodie Noir", true, true, false, false),
        new Outfit("lacroste_vert", "Lacroste Polo Vert", false, true, true, false),
        new Outfit("lacroste_blanc", "Lacroste Polo Blanc", false, true, true, false),
        new Outfit("nord_fasse", "Nord Fasse Doudoune", true, true, true, false),
        new Outfit("champyon_gris", "Champyon Sweat", false, true, true, false),
        new Outfit("guchi_vert", "Guchi Polo", true, true, false, true),
        new Outfit("louis_vuiten", "Louis Vuiten Monogram", false, true, true, true),
        new Outfit("jordane_rouge", "Jordane Retro", false, true, true, true),
        new Outfit("levys_jean", "Levys Jean", false, true, true, true),
        new Outfit("costard_noir", "Costard noir", false, true, true, true),
        new Outfit("costard_marine", "Costard bleu nuit", false, true, true, true),
        new Outfit("costard_blanc", "Costard blanc", false, true, true, true),
        new Outfit("costard_gris", "Costard gris anthracite", false, true, true, true),
        new Outfit("smoking", "Smoking", false, true, true, true),
        new Outfit("robe_soiree_rouge", "Robe de soirée rouge", false, true, true, true),
        new Outfit("robe_soiree_noire", "Robe de soirée noire", false, true, true, true),
        new Outfit("robe_cocktail", "Robe cocktail bleu roi", false, true, true, true),
        new Outfit("robe_ete", "Robe d'été fleurie", false, true, true, false),
        new Outfit("bikini_rouge", "Bikini rouge", false, true, true, false),
        new Outfit("bikini_turquoise", "Bikini turquoise", false, true, true, false),
        new Outfit("bikini_noir", "Bikini noir et or", false, true, true, false),
        new Outfit("maillot_bleu", "Short de bain bleu", false, false, true, false),
        new Outfit("maillot_tropical", "Short de bain tropical", false, false, true, false),
    };

    private OutfitData() {}
}
