package com.minenorth_vetements.client;

import com.minenorth_vetements.AccContainer;
import com.minenorth_vetements.AccNet;
import com.minenorth_vetements.AccSlot;
import com.minenorth_vetements.Bags;
import com.minenorth_vetements.MineNorthVetements;
import com.mojang.blaze3d.platform.InputConstants;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.network.chat.Component;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.lwjgl.glfw.GLFW;

/** Ouverture du sac porté : touche « Sac » (B par défaut, modifiable dans Options > Commandes) et boutons « Sac » des écrans. */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID, value = Dist.CLIENT)
public final class BagClient {
    private BagClient() {}

    public static final KeyMapping KEY = new KeyMapping("key.minenorth_vetements.sac", InputConstants.Type.KEYSYM, GLFW.GLFW_KEY_B,
            "key.categories.minenorth_vetements");

    /** Le joueur local porte-t-il un sac (copie client de l'emplacement Dos) ? */
    static boolean wearsBag() {
        Minecraft mc = Minecraft.getInstance();
        return mc.player != null && Bags.capacity(AccContainer.of(mc.player).getItem(AccSlot.DOS.ordinal())) > 0;
    }

    static void open() { AccNet.CHANNEL.sendToServer(new AccNet.OpenBag()); }

    static Button button(int x, int y, int w) {
        return Button.builder(Component.literal("Sac"), b -> open()).bounds(x, y, w, 14)
                .tooltip(Tooltip.create(Component.literal("Ouvrir le sac porté (touche B par défaut)"))).build();
    }

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.END) return;
        Minecraft mc = Minecraft.getInstance();
        while (KEY.consumeClick()) {
            if (mc.player == null || mc.screen != null) continue;
            if (wearsBag()) open();
            else mc.player.displayClientMessage(Component.literal("§7Tu ne portes pas de sac (emplacement Dos des accessoires)."), true);
        }
    }
}
