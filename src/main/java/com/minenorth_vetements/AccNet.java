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

    private static final String PROTOCOL = "1";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(MineNorthVetements.MODID, "acc"), () -> PROTOCOL, PROTOCOL::equals, PROTOCOL::equals);

    public static void register() {
        CHANNEL.registerMessage(0, Sync.class, Sync::encode, Sync::decode, Sync::handle, Optional.of(NetworkDirection.PLAY_TO_CLIENT));
    }

    /** entityId du joueur et accessoire porté (EMPTY = aucun). */
    public record Sync(int entityId, ItemStack stack) {
        static void encode(Sync m, FriendlyByteBuf b) { b.writeVarInt(m.entityId); b.writeItem(m.stack); }
        static Sync decode(FriendlyByteBuf b) { return new Sync(b.readVarInt(), b.readItem()); }
        static void handle(Sync m, Supplier<NetworkEvent.Context> c) {
            c.get().enqueueWork(() -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> com.minenorth_vetements.client.AccessoryClient.set(m.entityId, m.stack)));
            c.get().setPacketHandled(true);
        }
    }
}
