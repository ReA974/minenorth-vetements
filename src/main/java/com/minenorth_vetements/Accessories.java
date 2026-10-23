package com.minenorth_vetements;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.entity.living.LivingDropsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

import java.util.Set;

/**
 * Emplacement « accessoire de visage » : lunettes, cagoules, bandanas et écharpes se portent en plus du chapeau / de la casquette (qui reste dans
 * l'emplacement casque). Un seul accessoire à la fois, stocké dans les données persistantes du joueur (survit à la déconnexion), synchronisé aux
 * joueurs qui le voient. Le serveur décide de tout : le client ne fait qu'afficher.
 */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID)
public final class Accessories {
    private Accessories() {}

    private static final String KEY = "mnv_accessory";

    /** Objets qui se portent comme accessoire (et non dans l'emplacement casque). */
    public static final Set<String> IDS = Set.of(
            "lunettes_aviator", "lunettes_wayfarer", "lunettes_sport", "lunettes_rose",
            "cagoule_noire", "cagoule_kaki", "cagoule_guchi", "cagoule_guchi_noire", "cagoule_vuiten", "cagoule_supreem", "cagoule_nayk",
            "bandana_rouge", "bandana_noir", "echarpe_grise", "echarpe_rouge");

    public static boolean isAccessory(String outfitId) { return IDS.contains(outfitId); }

    private static CompoundTag data(Player p) {
        CompoundTag root = p.getPersistentData();
        if (!root.contains(Player.PERSISTED_NBT_TAG)) root.put(Player.PERSISTED_NBT_TAG, new CompoundTag());
        return root.getCompound(Player.PERSISTED_NBT_TAG);
    }

    public static ItemStack worn(Player p) {
        CompoundTag d = data(p);
        return d.contains(KEY) ? ItemStack.of(d.getCompound(KEY)) : ItemStack.EMPTY;
    }

    /** Pose (ou retire, avec EMPTY) l'accessoire et prévient les clients qui voient le joueur. */
    public static void set(ServerPlayer p, ItemStack st) {
        CompoundTag d = data(p);
        if (st.isEmpty()) d.remove(KEY); else d.put(KEY, st.save(new CompoundTag()));
        AccNet.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), new AccNet.Sync(p.getId(), st));
    }

    /** Un joueur arrive dans la zone de suivi d'un autre : il voit déjà son accessoire. */
    @SubscribeEvent
    public static void startTracking(PlayerEvent.StartTracking e) {
        if (e.getTarget() instanceof ServerPlayer target && e.getEntity() instanceof ServerPlayer viewer) {
            ItemStack st = worn(target);
            if (!st.isEmpty()) AccNet.CHANNEL.send(PacketDistributor.PLAYER.with(() -> viewer), new AccNet.Sync(target.getId(), st));
        }
    }

    @SubscribeEvent
    public static void login(PlayerEvent.PlayerLoggedInEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) {
            ItemStack st = worn(p);
            if (!st.isEmpty()) AccNet.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), new AccNet.Sync(p.getId(), st));
        }
    }

    /** Retire l'accessoire porté et le rend au joueur (inventaire, sinon au sol). Renvoie false s'il n'en portait pas. */
    public static boolean remove(ServerPlayer p) {
        ItemStack worn = worn(p);
        if (worn.isEmpty()) return false;
        set(p, ItemStack.EMPTY);
        if (!p.getInventory().add(worn)) p.drop(worn, false);
        p.displayClientMessage(net.minecraft.network.chat.Component.literal("§7Accessoire retiré."), true);
        p.level().playSound(null, p.blockPosition(), net.minecraft.sounds.SoundEvents.ARMOR_EQUIP_GENERIC, net.minecraft.sounds.SoundSource.PLAYERS, 0.6f, 1.1f);
        return true;
    }

    /** Accroupi + clic droit à mains nues : retire l'accessoire sans rien avoir en main (le serveur décide, jamais le client). */
    @SubscribeEvent
    public static void rightClickEmpty(net.minecraftforge.event.entity.player.PlayerInteractEvent.RightClickItem e) {
        if (!(e.getEntity() instanceof ServerPlayer p) || !p.isShiftKeyDown() || !e.getItemStack().isEmpty()) return;
        if (e.getHand() != net.minecraft.world.InteractionHand.MAIN_HAND) return;
        if (remove(p)) { e.setCanceled(true); e.setCancellationResult(net.minecraft.world.InteractionResult.SUCCESS); }
    }

    /** Même geste quand on vise un bloc (le clic « dans le vide » ne se déclenche pas alors). */
    @SubscribeEvent
    public static void rightClickBlock(net.minecraftforge.event.entity.player.PlayerInteractEvent.RightClickBlock e) {
        if (!(e.getEntity() instanceof ServerPlayer p) || !p.isShiftKeyDown() || !e.getItemStack().isEmpty()) return;
        if (e.getHand() != net.minecraft.world.InteractionHand.MAIN_HAND) return;
        if (remove(p)) { e.setCanceled(true); e.setCancellationResult(net.minecraft.world.InteractionResult.SUCCESS); }
    }

    /** Même geste quand on vise une entité ou un joueur. */
    @SubscribeEvent
    public static void rightClickEntity(net.minecraftforge.event.entity.player.PlayerInteractEvent.EntityInteract e) {
        if (!(e.getEntity() instanceof ServerPlayer p) || !p.isShiftKeyDown() || !e.getItemStack().isEmpty()) return;
        if (e.getHand() != net.minecraft.world.InteractionHand.MAIN_HAND) return;
        if (remove(p)) { e.setCanceled(true); e.setCancellationResult(net.minecraft.world.InteractionResult.SUCCESS); }
    }

    /** À la mort, l'accessoire tombe avec le reste de l'équipement. */
    @SubscribeEvent
    public static void death(LivingDropsEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer p)) return;
        ItemStack st = worn(p);
        if (st.isEmpty()) return;
        data(p).remove(KEY);
        e.getDrops().add(new net.minecraft.world.entity.item.ItemEntity(p.level(), p.getX(), p.getY() + 0.5, p.getZ(), st));
    }

    /** Respawn / changement de dimension : on renvoie l'état (vide après une mort). */
    @SubscribeEvent
    public static void respawn(PlayerEvent.PlayerRespawnEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) AccNet.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), new AccNet.Sync(p.getId(), worn(p)));
    }
}
