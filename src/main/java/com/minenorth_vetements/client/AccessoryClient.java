package com.minenorth_vetements.client;

import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.HashMap;
import java.util.Map;

/** Accessoires portés par les joueurs visibles (reçus du serveur), lus par la couche de rendu. */
@Mod.EventBusSubscriber(modid = com.minenorth_vetements.MineNorthVetements.MODID, value = Dist.CLIENT)
public final class AccessoryClient {
    private AccessoryClient() {}

    private static final Map<Integer, ItemStack> WORN = new HashMap<>();

    public static void set(int entityId, ItemStack st) {
        if (st.isEmpty()) WORN.remove(entityId); else WORN.put(entityId, st);
    }

    public static ItemStack get(int entityId) { return WORN.getOrDefault(entityId, ItemStack.EMPTY); }

    /** Accroupi + clic droit dans le vide, main vide : on demande au serveur de retirer l'accessoire. */
    @SubscribeEvent
    public static void rightClickEmpty(net.minecraftforge.event.entity.player.PlayerInteractEvent.RightClickEmpty e) {
        if (e.getEntity().isShiftKeyDown() && e.getItemStack().isEmpty() && e.getHand() == net.minecraft.world.InteractionHand.MAIN_HAND
                && !get(e.getEntity().getId()).isEmpty())
            com.minenorth_vetements.AccNet.CHANNEL.sendToServer(new com.minenorth_vetements.AccNet.Remove());
    }

    @SubscribeEvent
    public static void logout(ClientPlayerNetworkEvent.LoggingOut e) { WORN.clear(); }

    /** Nettoie les joueurs qui ne sont plus dans le monde. */
    public static void prune() {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) { WORN.clear(); return; }
        WORN.keySet().removeIf(id -> mc.level.getEntity(id) == null);
    }
}
