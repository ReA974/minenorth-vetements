package com.minenorth_vetements.client;

import net.minecraft.client.model.HumanoidModel;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeDeformation;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;

import java.util.HashMap;
import java.util.Map;

/**
 * Modèle d'armure « près du corps » : l'armure vanilla gonfle le corps de 1,0 (couche 1) ou 0,5 (jambes), ce qui fait des vêtements énormes.
 * Les textures gardent les UV de l'armure vanilla (64 x 32). Épaisseurs, de l'intérieur vers l'extérieur :
 * calques du skin (0,25) &lt; pantalon (0,27) &lt; haut (0,3) &lt; chaussures (0,32) ; tête 0,52 (au-dessus de la couche cheveux du skin, 0,5), cagoule 0,62 ;
 * doudounes 0,6 (modèle gonflé). Skins fins : manches de 3 de large, comme les bras du joueur.
 */
public final class SlimArmor {
    private SlimArmor() {}

    static final float HEAD = 0.52f, CHEST = 0.3f, PUFFY = 0.6f, LEGS = 0.27f, FEET = 0.32f;
    /**
     * Cagoules (texture de tête) : bien au-dessus des cheveux du skin (0,5) et de la texture des casquettes (0,52). À 0,52 elles se
     * superposaient exactement aux casquettes et presque aux cheveux : clignotement. Les chapeaux sont alors relevés de {@link #HAT_LIFT}.
     */
    static final float BALACLAVA = 0.62f, HAT_LIFT = 0.22f;
    private static final Map<String, HumanoidModel<?>> CACHE = new HashMap<>();

    public static boolean slim(LivingEntity e) {
        if (!(e instanceof AbstractClientPlayer p)) return false;
        Boolean drawn = identitySlim(p);   // le corps est dessiné par le mod Identité : manches et accessoires suivent le même bras
        return drawn != null ? drawn : "slim".equals(p.getModelName());
    }

    private static java.lang.reflect.Method identity;
    private static boolean identityTried;

    private static Boolean identitySlim(AbstractClientPlayer p) {
        if (!identityTried) {
            identityTried = true;
            try {
                if (net.minecraftforge.fml.ModList.get().isLoaded("minenorthidentite"))
                    identity = Class.forName("fr.minenorth.identite.client.skin.PlayerSkinEvents").getMethod("slimArms", java.util.UUID.class);
            } catch (ReflectiveOperationException | LinkageError ex) {
                identity = null;
            }
        }
        if (identity == null) return null;
        try {
            return (Boolean) identity.invoke(null, p.getUUID());
        } catch (ReflectiveOperationException ex) {
            return null;
        }
    }

    /** Épaisseur du haut porté (0 si aucun vêtement du mod), pour poser les accessoires par-dessus. */
    static float chestInflation(String outfitId) { return Formes.PUFFY.contains(outfitId) ? PUFFY : CHEST; }

    public static HumanoidModel<?> model(EquipmentSlot slot, LivingEntity entity, String outfitId) {
        boolean slim = slim(entity);
        float d = switch (slot) {
            case HEAD -> HEAD;
            case LEGS -> LEGS;
            case FEET -> FEET;
            default -> outfitId != null && Formes.PUFFY.contains(outfitId) ? PUFFY : CHEST;
        };
        return build(slot + "/" + d + "/" + slim, d, slim);
    }

    /** Tête de cagoule, sur son propre modèle (toujours visible, quelle que soit la dernière utilisation du modèle d'armure). */
    static net.minecraft.client.model.geom.ModelPart balaclavaHead() {
        net.minecraft.client.model.geom.ModelPart head = build("balaclava", BALACLAVA, false).head;
        head.visible = true;
        return head;
    }

    private static HumanoidModel<?> build(String key, float d, boolean slim) {
        return CACHE.computeIfAbsent(key, k -> {
            MeshDefinition mesh = HumanoidModel.createMesh(new CubeDeformation(d), 0.0f);
            PartDefinition root = mesh.getRoot();
            // La couche « chapeau » (texOffs 32,0) tomberait sur la palette de pastilles de la texture : on la vide.
            root.addOrReplaceChild("hat", CubeListBuilder.create(), PartPose.ZERO);
            if (slim) {
                CubeDeformation def = new CubeDeformation(d);
                root.addOrReplaceChild("right_arm", CubeListBuilder.create().texOffs(40, 16).addBox(-2.0f, -2.0f, -2.0f, 3.0f, 12.0f, 4.0f, def), PartPose.offset(-5.0f, 2.5f, 0.0f));
                root.addOrReplaceChild("left_arm", CubeListBuilder.create().texOffs(40, 16).mirror().addBox(-1.0f, -2.0f, -2.0f, 3.0f, 12.0f, 4.0f, def), PartPose.offset(5.0f, 2.5f, 0.0f));
            }
            return new HumanoidModel<>(LayerDefinition.create(mesh, 64, 32).bakeRoot());
        });
    }
}
