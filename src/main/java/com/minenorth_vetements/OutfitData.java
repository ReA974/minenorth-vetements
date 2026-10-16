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
    };

    private OutfitData() {}
}
