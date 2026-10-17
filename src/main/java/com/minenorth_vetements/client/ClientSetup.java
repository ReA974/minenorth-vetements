package com.minenorth_vetements.client;

import com.minenorth_vetements.MineNorthVetements;
import net.minecraft.client.renderer.entity.player.PlayerRenderer;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Branche la couche de relief sur les deux modèles de joueur (bras classiques et fins). */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class ClientSetup {
    private ClientSetup() {}

    /** Reliefs 3D (ourlets, poignets, semelles) : coupés, ils ne collaient plus aux textures actuelles (512 x 256) et faisaient des blocs qui dépassent. */
    private static final boolean RELIEF = false;

    @SubscribeEvent
    public static void addLayers(EntityRenderersEvent.AddLayers event) {
        for (String skin : new String[]{"default", "slim"}) {
            PlayerRenderer renderer = event.getSkin(skin);
            if (renderer != null && RELIEF) renderer.addLayer(new ClothesExtrasLayer(renderer));
        }
    }
}
