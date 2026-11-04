package com.minenorth_vetements;

import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.registries.ForgeRegistries;

import java.util.Map;
import java.util.UUID;

/**
 * Accessoires réservés aux grades : avantage « vetementsVip » du mod VIP (1 = accessoires VIP, 2 = VIP et VIP+), lu via l'API MineNorth
 * ({@code GradeService.perk}, par réflexion : aucune dépendance dure). Vérifié côté serveur à la pose (clic droit, emplacements, menu
 * /accessoires) ; un accessoire porté sans le grade (grade expiré) est retiré et rendu. Les opérateurs peuvent tout porter (tests).
 */
public final class VipItems {
    private VipItems() {}

    private static final Map<String, Integer> LEVEL = Map.of(
            "chaine_vip", 1, "montre_vip", 1, "sac_vip", 1,
            "chaine_diamant", 2, "montre_diamant", 2, "lunettes_holo", 2, "parachute_vip", 1, "parachute_prestige", 2);

    /** Niveau requis (0 = libre, 1 = VIP, 2 = VIP+). */
    public static int level(ItemStack st) {
        if (st.isEmpty()) return 0;
        ResourceLocation key = ForgeRegistries.ITEMS.getKey(st.getItem());
        if (key == null || !key.getNamespace().equals(MineNorthVetements.MODID)) return 0;
        return LEVEL.getOrDefault(key.getPath(), 0);
    }

    public static String label(int level) { return level >= 2 ? "VIP+" : "VIP"; }

    /** Le joueur peut-il porter cet objet ? Côté client : toujours oui (le serveur décide). */
    public static boolean allowed(Player p, ItemStack st) {
        int need = level(st);
        if (need == 0 || !(p instanceof ServerPlayer sp) || sp.hasPermissions(2)) return true;
        return perk(sp.server, sp.getUUID()) >= need;
    }

    private static double perk(MinecraftServer s, UUID id) {
        try {
            if (!ModList.get().isLoaded("minenorthapi")) return 0;
            Object svc = Class.forName("fr.minenorth.api.MineNorth").getMethod("grades").invoke(null);
            return (double) Class.forName("fr.minenorth.api.GradeService").getMethod("perk", MinecraftServer.class, UUID.class, String.class, double.class)
                    .invoke(svc, s, id, "vetementsVip", 0.0);
        } catch (Throwable t) {
            return 0;
        }
    }
}
