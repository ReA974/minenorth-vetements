package com.minenorth_vetements;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.entity.living.LivingFallEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.registries.ForgeRegistries;

import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

/**
 * Parachute : accessoire de l'emplacement « Dos / sac ». En chute libre (au moins {@value #MIN_FALL} blocs, ni à cheval, ni dans l'eau, ni en
 * élytres), Espace ouvre la voile : la descente ralentit fortement, on plane dans la direction du regard, et on se pose sans dégât.
 * Le mouvement est appliqué chez le joueur (Minecraft lui laisse son mouvement) ; le serveur valide l'ouverture (parachute porté, vraie chute),
 * annule les dégâts de chute et dit à tous les joueurs proches d'afficher la voile. Après l'atterrissage il faut {@value #REPACK_SECONDS} s
 * pour replier la voile avant un nouveau saut. Plusieurs modèles (voile de couleur différente) : parachute, _noir, _rouge, _bleu ; _vip (VIP) et
 * _prestige (VIP+) sont réservés au grade comme les autres accessoires VIP (VipItems).
 */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID)
public final class Parachute {
    private Parachute() {}

    public static final String ID = "parachute";
    public static final float MIN_FALL = 3f;
    public static final int REPACK_SECONDS = 4;

    /** Voiles ouvertes (serveur). */
    private static final Map<UUID, Long> OPEN = new ConcurrentHashMap<>();
    private static final Map<UUID, Long> LANDED = new ConcurrentHashMap<>();

    public static boolean wears(Player p, ItemStack[] worn) {
        ItemStack back = worn != null && worn.length > AccSlot.DOS.ordinal() ? worn[AccSlot.DOS.ordinal()] : ItemStack.EMPTY;
        ResourceLocation k = back.isEmpty() ? null : ForgeRegistries.ITEMS.getKey(back.getItem());
        return k != null && k.getNamespace().equals(MineNorthVetements.MODID) && (k.getPath().equals(ID) || k.getPath().startsWith(ID + "_"));
    }

    /** Peut-on ouvrir la voile maintenant ? (mêmes règles côté joueur et côté serveur) */
    /** Modèle de parachute porté (« parachute », « parachute_vip »…), ou "". */
    public static String model(ItemStack[] worn) {
        ItemStack back = worn != null && worn.length > AccSlot.DOS.ordinal() ? worn[AccSlot.DOS.ordinal()] : ItemStack.EMPTY;
        ResourceLocation k = back.isEmpty() ? null : ForgeRegistries.ITEMS.getKey(back.getItem());
        return k == null ? "" : k.getPath();
    }

    public static boolean canOpen(Player p) {
        return !p.onGround() && !p.isInWater() && !p.isInLava() && !p.isPassenger() && !p.isFallFlying() && !p.getAbilities().flying
                && p.fallDistance >= MIN_FALL && p.getDeltaMovement().y < -0.25;
    }

    // ------------------------------------------------------------------ serveur

    static void request(ServerPlayer p, boolean open) {
        if (!open) { close(p, false); return; }
        if (OPEN.containsKey(p.getUUID())) return;
        Long landed = LANDED.get(p.getUUID());
        if (landed != null && System.currentTimeMillis() - landed < REPACK_SECONDS * 1000L) {
            p.displayClientMessage(Component.literal("§7La voile n'est pas encore repliée."), true);
            sync(p, false);
            return;
        }
        if (!wears(p, Accessories.wornAll(p)) || !canOpen(p)) { sync(p, false); return; }
        OPEN.put(p.getUUID(), System.currentTimeMillis());
        p.fallDistance = 0;
        p.level().playSound(null, p.blockPosition(), SoundEvents.ARMOR_EQUIP_ELYTRA, SoundSource.PLAYERS, 1.2f, 0.7f);
        sync(p, true);
    }

    private static void close(ServerPlayer p, boolean landed) {
        if (OPEN.remove(p.getUUID()) == null) return;
        if (landed) LANDED.put(p.getUUID(), System.currentTimeMillis());
        p.fallDistance = 0;
        sync(p, false);
    }

    private static void sync(ServerPlayer p, boolean open) {
        AccNet.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), new State(p.getId(), open));
    }

    public static boolean isOpen(Player p) { return OPEN.containsKey(p.getUUID()); }

    @SubscribeEvent
    public static void tick(TickEvent.PlayerTickEvent e) {
        if (e.phase != TickEvent.Phase.END || !(e.player instanceof ServerPlayer p) || !OPEN.containsKey(p.getUUID())) return;
        p.fallDistance = 0;
        if (p.onGround() || p.isInWater() || p.isPassenger() || !p.isAlive()) close(p, true);
        else if (!wears(p, Accessories.wornAll(p))) close(p, false);
    }

    /** Voile ouverte (ou posé dans la seconde) : pas de dégâts de chute. */
    @SubscribeEvent
    public static void fall(LivingFallEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer p)) return;
        Long landed = LANDED.get(p.getUUID());
        if (OPEN.containsKey(p.getUUID()) || (landed != null && System.currentTimeMillis() - landed < 1500)) {
            e.setDistance(0);
            e.setDamageMultiplier(0);
        }
    }

    @SubscribeEvent
    public static void logout(PlayerEvent.PlayerLoggedOutEvent e) {
        OPEN.remove(e.getEntity().getUUID());
        LANDED.remove(e.getEntity().getUUID());
    }

    // ------------------------------------------------------------------ réseau

    /** Joueur -> serveur : ouvrir (true) ou couper (false) la voile. */
    public record Request(boolean open) {
        static void encode(Request m, FriendlyByteBuf b) { b.writeBoolean(m.open); }
        static Request decode(FriendlyByteBuf b) { return new Request(b.readBoolean()); }
        static void handle(Request m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> { ServerPlayer p = c.get().getSender(); if (p != null) request(p, m.open); });
            c.get().setPacketHandled(true);
        }
    }

    /** Serveur -> joueurs proches : voile ouverte ou fermée pour ce joueur. */
    public record State(int entityId, boolean open) {
        static void encode(State m, FriendlyByteBuf b) { b.writeVarInt(m.entityId); b.writeBoolean(m.open); }
        static State decode(FriendlyByteBuf b) { return new State(b.readVarInt(), b.readBoolean()); }
        static void handle(State m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> com.minenorth_vetements.client.ParachuteClient.state(m.entityId, m.open)));
            c.get().setPacketHandled(true);
        }
    }
}
