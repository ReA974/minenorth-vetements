package com.minenorth_vetements;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ArmorMaterial;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.client.extensions.common.IClientItemExtensions;

import java.util.function.Consumer;

/** Vêtement : une pièce d'armure sans protection, rendue avec un modèle près du corps (voir {@link com.minenorth_vetements.client.SlimArmor}). */
public class ClothesItem extends ArmorItem {
    public ClothesItem(ArmorMaterial material, Type type, Properties props) { super(material, type, props); }

    @Override
    public void initializeClient(Consumer<IClientItemExtensions> consumer) {
        consumer.accept(new IClientItemExtensions() {
            @Override
            public HumanoidModel<?> getHumanoidArmorModel(LivingEntity entity, ItemStack stack, EquipmentSlot slot, HumanoidModel<?> original) {
                return com.minenorth_vetements.client.SlimArmor.model(slot, original);
            }
        });
    }
}
