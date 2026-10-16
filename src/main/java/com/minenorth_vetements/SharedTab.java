package com.minenorth_vetements;

import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.event.BuildCreativeModeTabContentsEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;

/**
 * Les vêtements vont dans l'onglet « Animaux & Vêtements » (fourni par le mod minenorth-pets). Sans ce mod, ils restent dans l'onglet
 * commun « MineNorth » (fourni par minenorth_api).
 */
@Mod.EventBusSubscriber(modid = "minenorth_vetements", bus = Mod.EventBusSubscriber.Bus.MOD)
public final class SharedTab {
    private SharedTab() {}

    @SubscribeEvent
    public static void fill(BuildCreativeModeTabContentsEvent e) {
        ResourceLocation key = e.getTabKey().location();
        ResourceLocation target = ModList.get().isLoaded("minenorthpets")
                ? new ResourceLocation("minenorthpets", "animaux_vetements")
                : new ResourceLocation("minenorthapi", "minenorth");
        if (!key.equals(target)) return;
        MineNorthVetements.TAB_ITEMS.accept(e.getParameters(), e);
    }
}
