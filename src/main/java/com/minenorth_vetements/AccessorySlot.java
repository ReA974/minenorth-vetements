package com.minenorth_vetements;

import com.mojang.datafixers.util.Pair;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/**
 * Emplacement d'accessoire ajouté au menu d'inventaire du joueur (après la seconde main), des deux côtés : le serveur le synchronise comme
 * les emplacements d'armure. N'accepte que les accessoires de son type ; icône fantôme quand il est vide. Position : voir client.InventoryPanel.
 */
public class AccessorySlot extends Slot {
    public static final int X = -19, Y0 = 8;   // colonne à gauche de l'inventaire, à côté de l'armure

    public final AccSlot type;

    public AccessorySlot(AccContainer c, AccSlot type) {
        this(c, type, X, Y0 + type.ordinal() * 18);
    }

    public AccessorySlot(AccContainer c, AccSlot type, int x, int y) {
        super(c, type.ordinal(), x, y);
        this.type = type;
    }

    @Override public boolean mayPlace(ItemStack st) { return container.canPlaceItem(getContainerSlot(), st); }   // type d'emplacement + grade (VipItems)
    @Override public int getMaxStackSize() { return 1; }
    @Override public boolean mayPickup(Player p) { return true; }

    @Override
    public Pair<ResourceLocation, ResourceLocation> getNoItemIcon() {
        return Pair.of(InventoryMenu.BLOCK_ATLAS, new ResourceLocation(MineNorthVetements.MODID, "item/empty_acc_" + type.key));
    }

    /** Ajoute les 5 emplacements au menu d'inventaire du joueur, une seule fois par menu. */
    public static void install(Player p) {
        if (p.inventoryMenu.slots.stream().anyMatch(s -> s instanceof AccessorySlot)) return;
        AccContainer c = AccContainer.of(p);
        for (AccSlot s : AccSlot.values()) p.inventoryMenu.addSlot(new AccessorySlot(c, s));
    }
}
