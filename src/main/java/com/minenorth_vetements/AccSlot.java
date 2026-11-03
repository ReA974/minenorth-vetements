package com.minenorth_vetements;

/** Emplacements d'accessoires, portés en plus des vêtements (un accessoire par emplacement). */
public enum AccSlot {
    VISAGE("visage", "Visage"),
    COU("cou", "Cou"),
    POIGNET("poignet", "Poignet"),
    MAINS("mains", "Mains"),
    DOS("dos", "Dos / sac");

    public final String key, label;

    AccSlot(String key, String label) { this.key = key; this.label = label; }

    public static AccSlot byKey(String key) {
        for (AccSlot s : values()) if (s.key.equals(key)) return s;
        return null;
    }
}
