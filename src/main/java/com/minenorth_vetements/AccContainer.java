package com.minenorth_vetements;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;

import java.util.Arrays;
import java.util.Map;
import java.util.WeakHashMap;

/**
 * Les 5 accessoires portés par un joueur (un par {@link AccSlot}). Côté serveur, c'est la seule source de vérité : chaque changement
 * (emplacement de l'inventaire, clic droit avec l'objet, /accessoires, mort) passe ici, est écrit dans les données persistantes du joueur et
 * envoyé aux joueurs qui le voient. Côté client, simple copie remplie par la synchronisation du menu d'inventaire.
 */
public final class AccContainer implements Container {
    private static final Map<Player, AccContainer> BY_PLAYER = new WeakHashMap<>();

    private final Player player;
    private final ItemStack[] items = new ItemStack[Accessories.N];
    final long[] times = new long[Accessories.N];   // moment où chaque accessoire a été mis (pour « retirer le dernier porté »)
    private boolean loading;

    /** Conteneur déjà créé pour ce joueur, ou null (ne charge rien). */
    public static AccContainer peek(Player p) {
        synchronized (BY_PLAYER) {
            return BY_PLAYER.get(p);
        }
    }

    public static AccContainer of(Player p) {
        synchronized (BY_PLAYER) {
            return BY_PLAYER.computeIfAbsent(p, AccContainer::new);
        }
    }

    private AccContainer(Player p) {
        player = p;
        Arrays.fill(items, ItemStack.EMPTY);
        if (!p.level().isClientSide) load();
    }

    private void load() {
        loading = true;
        CompoundTag d = Accessories.data(player);
        for (AccSlot s : AccSlot.values()) {
            if (!d.contains(s.key)) continue;
            CompoundTag t = d.getCompound(s.key);
            items[s.ordinal()] = ItemStack.of(t);
            times[s.ordinal()] = t.getLong(Accessories.TIME);
        }
        loading = false;
    }

    /** Réécrit les données du joueur sans prévenir les autres clients (contenu d'un sac modifié : rien ne change à l'affichage). */
    void persist() {
        if (!player.level().isClientSide) save();
    }

    private void save() {
        CompoundTag d = Accessories.data(player);
        for (AccSlot s : AccSlot.values()) {
            ItemStack st = items[s.ordinal()];
            if (st.isEmpty()) { d.remove(s.key); continue; }
            CompoundTag t = st.save(new CompoundTag());
            t.putLong(Accessories.TIME, times[s.ordinal()]);
            d.put(s.key, t);
        }
    }

    @Override public int getContainerSize() { return items.length; }
    @Override public boolean isEmpty() { return Arrays.stream(items).allMatch(ItemStack::isEmpty); }
    @Override public ItemStack getItem(int i) { return i >= 0 && i < items.length ? items[i] : ItemStack.EMPTY; }

    @Override
    public ItemStack removeItem(int i, int n) {
        if (getItem(i).isEmpty() || n <= 0) return ItemStack.EMPTY;
        ItemStack out = items[i].split(n);
        if (items[i].isEmpty()) items[i] = ItemStack.EMPTY;
        setChanged();
        return out;
    }

    @Override
    public ItemStack removeItemNoUpdate(int i) {
        ItemStack out = getItem(i);
        if (i >= 0 && i < items.length) items[i] = ItemStack.EMPTY;
        setChanged();
        return out;
    }

    @Override
    public void setItem(int i, ItemStack st) {
        if (i < 0 || i >= items.length) return;
        boolean changed = !ItemStack.matches(items[i], st);
        items[i] = st;
        if (changed && !st.isEmpty() && !player.level().isClientSide) times[i] = player.level().getGameTime();
        setChanged();
    }

    /** Côté serveur : sauvegarde et prévient les joueurs qui voient le porteur (pour le rendu 3D). */
    @Override
    public void setChanged() {
        if (loading || player.level().isClientSide) return;
        save();
        if (player instanceof ServerPlayer sp && sp.connection != null) Accessories.sync(sp);
    }

    @Override public int getMaxStackSize() { return 1; }
    @Override public boolean stillValid(Player p) { return true; }

    @Override
    public boolean canPlaceItem(int i, ItemStack st) {
        return i >= 0 && i < items.length && Accessories.slotOf(st) == AccSlot.values()[i] && VipItems.allowed(player, st);   // accessoires VIP : grade requis
    }

    @Override
    public void clearContent() {
        Arrays.fill(items, ItemStack.EMPTY);
        setChanged();
    }
}
