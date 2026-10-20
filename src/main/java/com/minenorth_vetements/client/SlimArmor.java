package com.minenorth_vetements.client;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.world.entity.EquipmentSlot;

import java.util.EnumMap;
import java.util.Map;

/**
 * Modèle d'armure « près du corps » : l'armure vanilla gonfle le corps de 1,0 (couche 1) ou 0,5 (jambes), ce qui fait des vêtements
 * énormes. Ici le gonflement est de 0,25 / 0,1 : les textures (mêmes UV que l'armure vanilla, 64 x 32) ne changent pas.
 */
public final class SlimArmor {
    private SlimArmor() {}

    private static final float OUTER = 0.25f, INNER = 0.1f;
    private static final Map<EquipmentSlot, HumanoidModel<?>> CACHE = new EnumMap<>(EquipmentSlot.class);

    public static HumanoidModel<?> model(EquipmentSlot slot, HumanoidModel<?> original) {
        return CACHE.computeIfAbsent(slot, s -> {
            float d = s == EquipmentSlot.LEGS ? INNER : OUTER;
            var mesh = HumanoidModel.createMesh(new CubeDeformation(d), 0.0f);
            // La couche « chapeau » (texOffs 32,0) tomberait sur la palette de pastilles de la texture : on la vide.
            mesh.getRoot().addOrReplaceChild("hat", net.minecraft.client.model.geom.builders.CubeListBuilder.create(), net.minecraft.client.model.geom.PartPose.ZERO);
            LayerDefinition def = LayerDefinition.create(mesh, 64, 32);
            return new HumanoidModel<>(def.bakeRoot());
        });
    }
}
