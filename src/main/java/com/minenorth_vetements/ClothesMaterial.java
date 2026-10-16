package com.minenorth_vetements;

import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.crafting.Ingredient;

/** Materiau "vetement": aucune protection, texture propre a la tenue. */
final class ClothesMaterial implements ArmorMaterial {
    private final String name;

    ClothesMaterial(String id) { this.name = MineNorthVetements.MODID + ":" + id; }

    @Override public int getDurabilityForType(ArmorItem.Type type) { return 2000; }
    @Override public int getDefenseForType(ArmorItem.Type type) { return 0; }
    @Override public int getEnchantmentValue() { return 0; }
    @Override public SoundEvent getEquipSound() { return SoundEvents.ARMOR_EQUIP_LEATHER; }
    @Override public Ingredient getRepairIngredient() { return Ingredient.EMPTY; }
    @Override public String getName() { return name; }
    @Override public float getToughness() { return 0; }
    @Override public float getKnockbackResistance() { return 0; }
}
