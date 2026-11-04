package com.minenorth_vetements;

import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkEvent;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

import java.util.Optional;
import java.util.function.Supplier;

/** Réseau des accessoires : le serveur dit aux clients quel accessoire porte quel joueur (serveur vers client uniquement). */
public final class AccNet {
    private AccNet() {}

    private static final String PROTOCOL = "6";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(MineNorthVetements.MODID, "acc"), () -> PROTOCOL, PROTOCOL::equals, PROTOCOL::equals);

    public static void register() {
        CHANNEL.registerMessage(0, Sync.class, Sync::encode, Sync::decode, Sync::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
        CHANNEL.registerMessage(1, Remove.class, (m, b) -> {}, b -> new Remove(), Remove::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(2, OpenMenu.class, (m, b) -> {}, b -> new OpenMenu(), OpenMenu::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(3, OpenBag.class, (m, b) -> {}, b -> new OpenBag(), OpenBag::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(4, Parachute.Request.class, Parachute.Request::encode, Parachute.Request::decode, Parachute.Request::handle, Optional.of(NetworkDirection.PLAY_TO_SERVER));
        CHANNEL.registerMessage(5, Parachute.State.class, Parachute.State::encode, Parachute.State::decode, Parachute.State::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
    }

    /** Demande de retrait du dernier accessoire porté (clic droit dans le vide, accroupi, main vide) : le serveur revérifie tout. */
    public record Remove() {
        static void handle(Remove m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> {
                net.minecraft.server.level.ServerPlayer p = c.get().getSender();
                if (p != null && p.isShiftKeyDown() && p.getMainHandItem().isEmpty()) Accessories.removeLast(p);
            });
            c.get().setPacketHandled(true);
        }
    }

    /** Demande d'ouverture du menu Accessoires (bouton de l'inventaire créatif). */
    /** Demande d'ouverture du sac porté (touche, bouton de l'inventaire ou du menu Accessoires) : le serveur vérifie qu'il y a bien un sac. */
    public record OpenBag() {
        static void handle(OpenBag m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> {
                net.minecraft.server.level.ServerPlayer p = c.get().getSender();
                if (p != null && p.isAlive() && !p.isSpectator()) BagMenu.open(p);
            });
            c.get().setPacketHandled(true);
        }
    }

    public record OpenMenu() {
        static void handle(OpenMenu m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> {
                net.minecraft.server.level.ServerPlayer p = c.get().getSender();
                if (p != null && p.isAlive()) AccMenu.open(p);
            });
            c.get().setPacketHandled(true);
        }
    }

    /** entityId du joueur et accessoires portés, un par emplacement (EMPTY = aucun). */
    public record Sync(int entityId, ItemStack[] stacks) {
        static void encode(Sync m, FriendlyByteBuf b) {
            b.writeVarInt(m.entityId);
            for (int i = 0; i < Accessories.N; i++) b.writeItem(i < m.stacks.length ? Bags.withoutContents(m.stacks[i]) : ItemStack.EMPTY);   // jamais le contenu des sacs
        }
        static Sync decode(FriendlyByteBuf b) {
            int id = b.readVarInt();
            ItemStack[] st = new ItemStack[Accessories.N];
            for (int i = 0; i < st.length; i++) st[i] = b.readItem();
            return new Sync(id, st);
        }
        static void handle(Sync m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> com.minenorth_vetements.client.AccessoryClient.set(m.entityId, m.stacks)));
            c.get().setPacketHandled(true);
        }
    }
}
