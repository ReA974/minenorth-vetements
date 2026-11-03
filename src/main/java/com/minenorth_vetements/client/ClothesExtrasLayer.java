package com.minenorth_vetements.client;

import com.minenorth_vetements.ClothesItem;
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
import net.minecraftforge.registries.ForgeRegistries;

import java.util.Map;

/** Ajoute le relief 3D des tenues (voir {@link ClothesExtras} et {@link Reliefs}) et les accessoires portés, par-dessus la couche d'armure vanilla. */
public class ClothesExtrasLayer extends RenderLayer<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> {
    private static final EquipmentSlot[] SLOTS = {EquipmentSlot.HEAD, EquipmentSlot.CHEST, EquipmentSlot.LEGS, EquipmentSlot.FEET};

    public ClothesExtrasLayer(RenderLayerParent<AbstractClientPlayer, PlayerModel<AbstractClientPlayer>> parent) {
        super(parent);
    }

    private static String outfitId(ItemStack stack, EquipmentSlot slot) {
        if (!(stack.getItem() instanceof ArmorItem armor) || armor.getType().getSlot() != slot) return null;
        String name = armor.getMaterial().getName();
        return name.startsWith(MineNorthVetements.MODID + ":") ? name.substring(name.indexOf(':') + 1) : null;
    }

    @Override
    public void render(PoseStack ps, MultiBufferSource buffers, int light, AbstractClientPlayer player,
                       float limbSwing, float limbSwingAmount, float partialTick, float ageInTicks, float netHeadYaw, float headPitch) {
        if (player.isInvisible()) return;
        PlayerModel<AbstractClientPlayer> model = getParentModel();
        boolean slim = SlimArmor.slim(player);
        boolean bala = wearsBalaclava(player);
        for (EquipmentSlot slot : SLOTS) {
            String id = outfitId(player.getItemBySlot(slot), slot);
            if (id == null) continue;
            ResourceLocation tex = new ResourceLocation(MineNorthVetements.MODID,
                    "textures/models/armor/" + id + "_layer_" + (slot == EquipmentSlot.LEGS ? 2 : 1) + ".png");
            float lift = bala && slot == EquipmentSlot.HEAD ? SlimArmor.HAT_LIFT : 0;   // chapeau par-dessus la cagoule, pas dedans
            Map<String, ModelPart> gen = Reliefs.parts(id, slim, 0, lift);
            if (gen != null) {
                draw(ps, buffers.getBuffer(RenderType.armorCutoutNoCull(tex)), light, model, gen);
                continue;
            }
            ClothesExtras.Style style = ClothesExtras.styleOf(id);
            if (!ClothesExtras.hasRelief(slot, style)) continue;
            Map<String, ModelPart> parts = lift > 0 ? Reliefs.legacyHat(style, ClothesExtras.beanie(id), lift) : ClothesExtras.parts(slot, style, ClothesExtras.beanie(id));
            draw(ps, buffers.getBuffer(RenderType.armorCutoutNoCull(tex)), light, model, parts);
        }
        renderAccessories(ps, buffers, light, player, model, slim);
        if (player.tickCount % 400 == 0) AccessoryClient.prune();
    }

    private static String accessoryId(ItemStack st) {
        if (st == null || st.isEmpty()) return null;
        ResourceLocation key = ForgeRegistries.ITEMS.getKey(st.getItem());
        return key == null || !key.getNamespace().equals(MineNorthVetements.MODID) ? null : key.getPath().replace("_helmet", "");
    }

    /** Porte-t-il une cagoule (emplacement visage) ? */
    private static boolean wearsBalaclava(AbstractClientPlayer player) {
        ItemStack[] worn = AccessoryClient.get(player.getId());
        int i = com.minenorth_vetements.AccSlot.VISAGE.ordinal();
        String id = worn.length > i ? accessoryId(worn[i]) : null;
        return id != null && Formes.SHAPE_OF.get(id) == null && ClothesExtras.styleOf(id) == ClothesExtras.Style.BALA;
    }

    /** Épaisseur du haut porté : les chaînes, bretelles, montres et gants se posent par-dessus (jamais dedans, jamais sous le skin). */
    private static float chestInflation(AbstractClientPlayer player) {
        ItemStack chest = player.getItemBySlot(EquipmentSlot.CHEST);
        String id = outfitId(chest, EquipmentSlot.CHEST);
        if (id != null && chest.getItem() instanceof ClothesItem) return SlimArmor.chestInflation(id);
        return chest.getItem() instanceof ArmorItem ? 1.0f : 0f;   // armure d'un autre mod / vanilla : bien plus épaisse
    }

    /** Accessoires portés (visage, cou, poignet, mains, dos), en plus du chapeau et des vêtements. */
    private void renderAccessories(PoseStack ps, MultiBufferSource buffers, int light, AbstractClientPlayer player, PlayerModel<AbstractClientPlayer> model, boolean slim) {
        ItemStack[] worn = AccessoryClient.get(player.getId());
        if (worn.length == 0) return;
        float delta = Math.max(chestInflation(player), 0.25f) + 0.05f - SlimArmor.CHEST;   // 0,25 = couche veste / manches du skin
        for (ItemStack st : worn) {
            String id = accessoryId(st);
            if (id == null) continue;
            ResourceLocation tex = new ResourceLocation(MineNorthVetements.MODID, "textures/models/armor/" + id + "_layer_1.png");
            VertexConsumer vc = buffers.getBuffer(RenderType.armorCutoutNoCull(tex));
            Map<String, ModelPart> gen = Reliefs.parts(id, slim, delta);
            if (gen != null) {
                draw(ps, vc, light, model, gen);
                continue;
            }
            ClothesExtras.Style style = ClothesExtras.styleOf(id);
            if (style == ClothesExtras.Style.BALA) {      // la cagoule a une vraie texture de tête (maille, fente des yeux)
                ModelPart head = SlimArmor.balaclavaHead();   // modèle à part : plus de clignotement avec les cheveux du skin ni la casquette
                head.copyFrom(model.head);
                head.render(ps, vc, light, OverlayTexture.NO_OVERLAY);
                draw(ps, vc, light, model, Reliefs.legacyBalaclava(style, delta));
            } else {
                draw(ps, vc, light, model, ClothesExtras.parts(EquipmentSlot.HEAD, style, false));
            }
        }
    }

    private static void draw(PoseStack ps, VertexConsumer vc, int light, PlayerModel<AbstractClientPlayer> model, Map<String, ModelPart> parts) {
        for (Map.Entry<String, ModelPart> e : parts.entrySet()) {
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
