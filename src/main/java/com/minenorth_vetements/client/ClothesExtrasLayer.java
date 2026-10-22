package com.minenorth_vetements.client;

import com.minenorth_vetements.MineNorthVetements;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.model.PlayerModel;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.ItemStack;

import java.util.Map;

/** Ajoute le relief 3D des tenues (voir {@link ClothesExtras}) sur le joueur, par-dessus la couche d'armure vanilla. */
public class ClothesExtrasLayer extends RenderLayer<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> {
    private static final EquipmentSlot[] SLOTS = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};

    public ClothesExtrasLayer(RenderLayerParent<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> parent) {
        super(parent);
    }

    @Override
    public void render(PoseStack ps, MultiBufferSource buffers, int light, AbstractClientPlayer player,
                       float limbSwing, float limbSwingAmount, float partialTick, float ageInTicks, float netHeadYaw, float headPitch) {
        if (player.isInvisible()) return;
        PlayerModel<AbstractClientPlayer> model = getParentModel();
        for (EquipmentSlot slot : SLOTS) {
            ItemStack stack = player.getItemBySlot(slot);
            if (!(stack.getItem() instanceof ArmorItem armor) || armor.getType().getSlot() != slot) continue;
            String name = armor.getMaterial().getName();
            if (!name.startsWith(MineNorthVetements.MODID + ":")) continue;
            String id = name.substring(name.indexOf(':') + 1);

            ResourceLocation tex = new ResourceLocation(MineNorthVetements.MODID,
                    "textures/models/armor/" + id + "_layer_" + (slot == EquipmentSlot.LEGS ? 2 : 1) + ".png");
            VertexConsumer vc = buffers.getBuffer(RenderType.armorCutoutNoCull(tex));
            ClothesExtras.Style style = ClothesExtras.styleOf(id);
            if (!ClothesExtras.hasRelief(slot, style)) continue;
            Map<String, ModelPart> parts = ClothesExtras.parts(slot, style, ClothesExtras.beanie(id));
            for (Map.Entry<String, ModelPart> e : parts.entrySet()) {
                ModelPart parent = parentPart(model, e.getKey());
                if (parent == null) continue;
                ModelPart extra = e.getValue();
                extra.copyFrom(parent);
                extra.render(ps, vc, light, OverlayTexture.NO_OVERLAY);
            }
        }
        renderAccessory(ps, buffers, light, player, model);
        if (player.tickCount % 400 == 0) AccessoryClient.prune();
    }

    /** Accessoire de visage (lunettes, cagoule, bandana, écharpe) porté en plus du chapeau : texture de tête (cagoule) puis relief. */
    private void renderAccessory(PoseStack ps, MultiBufferSource buffers, int light, AbstractClientPlayer player, PlayerModel<AbstractClientPlayer> model) {
        ItemStack st = AccessoryClient.get(player.getId());
        if (st.isEmpty()) return;
        net.minecraft.resources.ResourceLocation key = net.minecraftforge.registries.ForgeRegistries.ITEMS.getKey(st.getItem());
        if (key == null || !key.getNamespace().equals(MineNorthVetements.MODID)) return;
        String id = key.getPath().replace("_helmet", "");
        ResourceLocation tex = new ResourceLocation(MineNorthVetements.MODID, "textures/models/armor/" + id + "_layer_1.png");
        VertexConsumer vc = buffers.getBuffer(RenderType.armorCutoutNoCull(tex));
        ClothesExtras.Style style = ClothesExtras.styleOf(id);
        if (style == ClothesExtras.Style.BALA) {      // la cagoule a une vraie texture de tête (maille, fente des yeux)
            ModelPart head = SlimArmor.model(EquipmentSlot.HEAD, null).head;
            head.copyFrom(model.head);
            head.render(ps, vc, light, OverlayTexture.NO_OVERLAY);
        }
        for (Map.Entry<String, ModelPart> e : ClothesExtras.parts(EquipmentSlot.HEAD, style, false).entrySet()) {
            ModelPart parent = parentPart(model, e.getKey());
            if (parent == null) continue;
            ModelPart extra = e.getValue();
            extra.copyFrom(parent);
            extra.render(ps, vc, light, OverlayTexture.NO_OVERLAY);
        }
    }

    private static ModelPart parentPart(PlayerModel<AbstractClientPlayer> m, String name) {
        return switch (name) {
            case "head" -> m.head;
            case "body" -> m.body;
            case "right_arm" -> m.rightArm;
            case "left_arm" -> m.leftArm;
            case "right_leg" -> m.rightLeg;
            case "left_leg" -> m.leftLeg;
            default -> null;
        };
    }
}
