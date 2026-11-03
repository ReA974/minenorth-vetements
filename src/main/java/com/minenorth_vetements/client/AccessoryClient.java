package com.minenorth_vetements.client;

import com.minenorth_vetements.Accessories;
import net.minecraft.client.Minecraft;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/** Accessoires portés par les joueurs visibles (reçus du serveur, un par emplacement), lus par la couche de rendu. */
@Mod.EventBusSubscriber(modid = com.minenorth_vetements.MineNorthVetements.MODID, value = Dist.CLIENT)
public final class AccessoryClient {
    private AccessoryClient() {}

    private static final Map<Integer, ItemStack[]> WORN = new HashMap<>();
    private static final ItemStack[] NONE = new ItemStack[0];

    public static void set(int entityId, ItemStack[] st) {
        if (Arrays.stream(st).allMatch(ItemStack::isEmpty)) WORN.remove(entityId); else WORN.put(entityId, st);
    }

    public static ItemStack[] get(int entityId) { return WORN.getOrDefault(entityId, NONE); }

    /** Un joueur sort du monde du client (hors de vue, mort, changement de dimension) : on oublie ses accessoires, le serveur les renverra. */
    @SubscribeEvent
    public static void leaveLevel(net.minecraftforge.event.entity.EntityLeaveLevelEvent e) {
        if (e.getLevel().isClientSide() && e.getEntity() instanceof net.minecraft.world.entity.player.Player p && !p.isLocalPlayer()) WORN.remove(p.getId());
    }

    /** Cagoule : plus de nom au-dessus de la tête (les autres joueurs ne voient plus qui c'est). */
    @SubscribeEvent
    public static void hideNameTag(net.minecraftforge.client.event.RenderNameTagEvent e) {
        if (!(e.getEntity() instanceof net.minecraft.world.entity.player.Player p)) return;
        ItemStack[] worn = get(p.getId());
        int i = com.minenorth_vetements.AccSlot.VISAGE.ordinal();
        if (worn.length <= i || worn[i] == null || worn[i].isEmpty()) return;
        net.minecraft.resources.ResourceLocation key = net.minecraftforge.registries.ForgeRegistries.ITEMS.getKey(worn[i].getItem());
        if (key != null && key.getNamespace().equals(com.minenorth_vetements.MineNorthVetements.MODID) && key.getPath().startsWith("cagoule_"))
            e.setResult(net.minecraftforge.eventbus.api.Event.Result.DENY);
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
