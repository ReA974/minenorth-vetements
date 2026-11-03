package com.minenorth_vetements;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.event.RegisterCommandsEvent;
import net.minecraftforge.event.entity.living.LivingDropsEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.event.entity.player.PlayerInteractEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;
import net.minecraftforge.registries.ForgeRegistries;

import java.util.Arrays;

/**
 * Accessoires portés en plus des vêtements, un par emplacement ({@link AccSlot} : visage, cou, poignet, mains, dos). Stockés dans les données
 * persistantes du joueur (survivent à la déconnexion), synchronisés aux joueurs qui le voient. Le serveur décide de tout : le client ne fait qu'afficher.
 * Les chapeaux, casquettes, bonnets et bobs restent dans l'emplacement casque.
 */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID)
public final class Accessories {
    private Accessories() {}

    private static final String OLD_KEY = "mnv_accessory";   // ancienne version : un seul accessoire
    private static final String KEY = "mnv_acc";
    static final String TIME = "mnv_t";
    public static final int N = AccSlot.values().length;

    /** Objets qui se portent comme accessoire (et non dans l'emplacement casque). */
    public static boolean isAccessory(String outfitId) { return AccessoryData.BY_ID.containsKey(outfitId); }

    /**
     * Objets d'autres mods qui se portent dans un emplacement d'accessoire. Ils sont dessinés avec l'affichage « head » de leur modèle
     * d'item, centré sur le torse (voir client.ClothesExtrasLayer). Le mod d'origine lit l'emplacement dans les données du joueur.
     */
    public static final java.util.Map<String, AccSlot> EXTERNAL = java.util.Map.of(
            "minenorthsecours:bouteille_ari", AccSlot.DOS);   // bouteille d'air de l'ARI des pompiers

    /** Emplacement d'un objet accessoire, null si ce n'en est pas un. */
    public static AccSlot slotOf(ItemStack st) {
        if (st.isEmpty()) return null;
        ResourceLocation key = ForgeRegistries.ITEMS.getKey(st.getItem());
        if (key == null) return null;
        if (!key.getNamespace().equals(MineNorthVetements.MODID)) return EXTERNAL.get(key.toString());
        AccessoryData.Acc a = AccessoryData.BY_ID.get(key.getPath().replace("_helmet", ""));
        return a == null ? null : a.slot();
    }

    /** Stockage dans les données persistantes du joueur (lu et écrit par {@link AccContainer}). */
    static CompoundTag data(Player p) {
        CompoundTag root = p.getPersistentData();
        if (!root.contains(Player.PERSISTED_NBT_TAG)) root.put(Player.PERSISTED_NBT_TAG, new CompoundTag());
        CompoundTag d = root.getCompound(Player.PERSISTED_NBT_TAG);
        if (!d.contains(KEY)) d.put(KEY, new CompoundTag());
        if (d.contains(OLD_KEY)) {        // migration : l'ancien accessoire unique va dans son emplacement
            ItemStack old = ItemStack.of(d.getCompound(OLD_KEY));
            d.remove(OLD_KEY);
            AccSlot s = slotOf(old);
            if (s != null) d.getCompound(KEY).put(s.key, old.save(new CompoundTag()));
        }
        return d.getCompound(KEY);
    }

    public static ItemStack worn(Player p, AccSlot slot) {
        return AccContainer.of(p).getItem(slot.ordinal()).copy();
    }

    public static ItemStack[] wornAll(Player p) {
        ItemStack[] out = new ItemStack[N];
        for (AccSlot s : AccSlot.values()) out[s.ordinal()] = worn(p, s);
        return out;
    }

    static void sync(ServerPlayer p) {
        AccNet.CHANNEL.send(PacketDistributor.TRACKING_ENTITY_AND_SELF.with(() -> p), new AccNet.Sync(p.getId(), wornAll(p)));
        p.refreshDisplayName();   // cagoule mise / retirée : nom du chat recalculé (voir masked)
    }

    // ------------------------------------------------------------------ cagoule : identité masquée

    public static final String MASKED_NAME = "Individu masqué";

    /** Porte-t-il une cagoule (emplacement visage) ? Les bandanas et lunettes ne masquent pas. */
    public static boolean masked(Player p) {
        AccContainer c = AccContainer.peek(p);   // sans le créer : le nom peut être calculé avant le chargement des données du joueur
        if (c == null) return false;
        ItemStack st = c.getItem(AccSlot.VISAGE.ordinal());
        ResourceLocation key = st.isEmpty() ? null : ForgeRegistries.ITEMS.getKey(st.getItem());
        return key != null && key.getNamespace().equals(MineNorthVetements.MODID) && key.getPath().startsWith("cagoule_");
    }

    /**
     * Nom affiché (chat RP du mod identité, messages de mort, /msg...) : « Individu masqué » tant que la cagoule est portée. Fourni par l'API
     * ({@code MaskService}) et appliqué par le mod Identité, qui compose le nom : la cagoule passe après le mode staff et cache le préfixe VIP.
     * Le TAB (liste des joueurs) garde le vrai nom.
     */
    static void provideMask() {
        fr.minenorth.api.MineNorth.provide(fr.minenorth.api.MaskService.class, new fr.minenorth.api.MaskService() {
            @Override public boolean masked(ServerPlayer p) { return Accessories.masked(p); }
            @Override public Component maskedName() { return Component.literal(MASKED_NAME).withStyle(ChatFormatting.DARK_GRAY); }
        });
    }

    /** Pose (ou retire, avec EMPTY) l'accessoire de cet emplacement et prévient les clients qui voient le joueur. */
    public static void set(ServerPlayer p, AccSlot slot, ItemStack st) {
        AccContainer.of(p).setItem(slot.ordinal(), st);   // sauvegarde + synchronisation (rendu et emplacement d'inventaire)
    }

    /** Retire l'accessoire de cet emplacement et le rend au joueur (inventaire, sinon au sol). Renvoie false s'il n'y en avait pas. */
    public static boolean remove(ServerPlayer p, AccSlot slot) {
        ItemStack worn = worn(p, slot);
        if (worn.isEmpty()) return false;
        set(p, slot, ItemStack.EMPTY);
        if (!p.getInventory().add(worn)) p.drop(worn, false);
        p.displayClientMessage(Component.literal("§7" + worn.getHoverName().getString() + " retiré(e)."), true);
        p.level().playSound(null, p.blockPosition(), SoundEvents.ARMOR_EQUIP_GENERIC, SoundSource.PLAYERS, 0.6f, 1.1f);
        return true;
    }

    /** Retire le dernier accessoire porté. Renvoie false s'il n'en portait aucun. */
    public static boolean removeLast(ServerPlayer p) {
        AccContainer c = AccContainer.of(p);
        AccSlot last = null;
        long best = Long.MIN_VALUE;
        for (AccSlot s : AccSlot.values()) {
            if (c.getItem(s.ordinal()).isEmpty()) continue;
            long t = c.times[s.ordinal()];
            if (last == null || t >= best) { last = s; best = t; }
        }
        return last != null && remove(p, last);
    }

    // ------------------------------------------------------------------ synchronisation

    /**
     * Emplacements d'accessoires dans l'inventaire : ajoutés au menu du joueur des deux côtés (serveur : chaque joueur ; client : le joueur local),
     * à chaque nouveau joueur (connexion, réapparition, changement de dimension côté client).
     */
    @SubscribeEvent
    public static void joinLevel(net.minecraftforge.event.entity.EntityJoinLevelEvent e) {
        if (!(e.getEntity() instanceof Player p)) return;
        if (e.getLevel().isClientSide ? p.isLocalPlayer() : p instanceof ServerPlayer) AccessorySlot.install(p);
    }

    /** Un joueur arrive dans la zone de suivi d'un autre : il voit déjà ses accessoires. */
    @SubscribeEvent
    public static void startTracking(PlayerEvent.StartTracking e) {
        if (e.getTarget() instanceof ServerPlayer target && e.getEntity() instanceof ServerPlayer viewer) {
            // Toujours envoyé, même vide : sinon un joueur revu après avoir retiré sa cagoule hors de vue la garderait chez ce client.
            AccNet.CHANNEL.send(PacketDistributor.PLAYER.with(() -> viewer), new AccNet.Sync(target.getId(), wornAll(target)));
        }
    }

    @SubscribeEvent
    public static void login(PlayerEvent.PlayerLoggedInEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) sync(p);
    }

    /** Respawn / changement de dimension : on renvoie l'état (vide après une mort). */
    @SubscribeEvent
    public static void respawn(PlayerEvent.PlayerRespawnEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) sync(p);
    }

    @SubscribeEvent
    public static void dimension(PlayerEvent.PlayerChangedDimensionEvent e) {
        if (e.getEntity() instanceof ServerPlayer p) sync(p);
    }

    /** À la mort, les accessoires tombent avec le reste de l'équipement. */
    @SubscribeEvent
    public static void death(LivingDropsEvent e) {
        if (!(e.getEntity() instanceof ServerPlayer p)) return;
        if (p.level().getGameRules().getBoolean(net.minecraft.world.level.GameRules.RULE_KEEPINVENTORY)) return;   // gardés comme l'inventaire
        AccContainer c = AccContainer.of(p);
        for (AccSlot s : AccSlot.values()) {
            ItemStack st = c.removeItemNoUpdate(s.ordinal());
            if (st.isEmpty()) continue;
            e.getDrops().add(new net.minecraft.world.entity.item.ItemEntity(p.level(), p.getX(), p.getY() + 0.5, p.getZ(), st));
        }
    }

    /** Toutes les 5 s : un accessoire VIP porté sans le grade (grade expiré ou retiré) est enlevé et rendu au joueur. */
    @SubscribeEvent
    public static void vipCheck(net.minecraftforge.event.TickEvent.PlayerTickEvent e) {
        if (e.phase != net.minecraftforge.event.TickEvent.Phase.END || !(e.player instanceof ServerPlayer p) || p.tickCount % 100 != 0) return;
        for (AccSlot s : AccSlot.values()) {
            ItemStack st = AccContainer.of(p).getItem(s.ordinal());
            if (!st.isEmpty() && !VipItems.allowed(p, st) && remove(p, s))
                p.sendSystemMessage(Component.literal("§6" + st.getHoverName().getString() + " est réservé(e) aux " + VipItems.label(VipItems.level(st)) + " : il (elle) a été rangé(e) dans votre inventaire."));
        }
    }

    // ------------------------------------------------------------------ /accessoires : liste cliquable, retrait par emplacement

    @SubscribeEvent
    public static void commands(RegisterCommandsEvent e) {
        e.getDispatcher().register(Commands.literal("accessoires")
                .executes(c -> { AccMenu.open(c.getSource().getPlayerOrException()); return 1; })   // menu (marche aussi en créatif)
                .then(Commands.literal("liste").executes(c -> list(c.getSource().getPlayerOrException())))
                .then(Commands.literal("tout").executes(c -> {
                    ServerPlayer p = c.getSource().getPlayerOrException();
                    int n = 0;
                    for (AccSlot s : AccSlot.values()) if (remove(p, s)) n++;
                    p.sendSystemMessage(Component.literal(n == 0 ? "§7Tu ne portes aucun accessoire." : "§7" + n + " accessoire(s) retiré(s)."));
                    return n;
                }))
                .then(Commands.literal("retirer").then(Commands.argument("emplacement", StringArgumentType.word())
                        .suggests((c, b) -> SharedSuggestionProvider.suggest(Arrays.stream(AccSlot.values()).map(s -> s.key), b))
                        .executes(c -> {
                            ServerPlayer p = c.getSource().getPlayerOrException();
                            AccSlot s = AccSlot.byKey(StringArgumentType.getString(c, "emplacement"));
                            if (s == null) { p.sendSystemMessage(Component.literal("§cEmplacement inconnu.")); return 0; }
                            if (!remove(p, s)) p.sendSystemMessage(Component.literal("§7Rien à retirer (" + s.label + ")."));
                            return 1;
                        }))));
    }

    private static int list(ServerPlayer p) {
        p.sendSystemMessage(Component.literal("Accessoires portés :").withStyle(ChatFormatting.GOLD));
        for (AccSlot s : AccSlot.values()) {
            ItemStack st = worn(p, s);
            MutableComponent line = Component.literal(" " + s.label + " : ").withStyle(ChatFormatting.GRAY);
            if (st.isEmpty()) line.append(Component.literal("—").withStyle(ChatFormatting.DARK_GRAY));
            else line.append(st.getHoverName().copy().withStyle(ChatFormatting.WHITE)).append(Component.literal(" [retirer]").withStyle(sty -> sty
                    .withColor(ChatFormatting.RED)
                    .withClickEvent(new ClickEvent(ClickEvent.Action.RUN_COMMAND, "/accessoires retirer " + s.key))
                    .withHoverEvent(new HoverEvent(HoverEvent.Action.SHOW_TEXT, Component.literal("Retirer et remettre dans l'inventaire")))));
            p.sendSystemMessage(line);
        }
        p.sendSystemMessage(Component.literal(" Accroupi + clic droit main vide : retire le dernier accessoire porté.").withStyle(ChatFormatting.DARK_GRAY));
        return 1;
    }
}
