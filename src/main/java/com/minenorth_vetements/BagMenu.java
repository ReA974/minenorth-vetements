package com.minenorth_vetements;

import net.minecraft.core.NonNullList;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.Container;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.network.NetworkHooks;

/**
 * Contenu du sac PORTÉ (emplacement dos). Le serveur lit le contenu dans l'objet sac à l'ouverture et l'y réécrit à chaque changement :
 * il n'existe qu'à un seul endroit. Le sac lui-même n'est pas dans l'inventaire affiché (il est sur le dos), donc impossible de le jeter, de
 * le déplacer ou de le ranger dans lui-même pendant qu'il est ouvert ; s'il quitte le dos (mort, commande), le menu se ferme.
 */
public class BagMenu extends AbstractContainerMenu {
    public final int rows;
    private final Container bag;
    private final Player player;
    private final ItemStack bagStack;   // côté serveur : l'objet porté lui-même (null côté client)

    /** Côté client : seulement la taille, le contenu arrive par la synchronisation du menu. */
    public BagMenu(int id, Inventory inv, FriendlyByteBuf buf) {
        this(id, inv, new SimpleContainer(buf.readVarInt()), null);
    }

    private BagMenu(int id, Inventory inv, Container bag, ItemStack bagStack) {
        super(MineNorthVetements.BAG_MENU.get(), id);
        this.bag = bag;
        this.player = inv.player;
        this.bagStack = bagStack;
        this.rows = bag.getContainerSize() / 9;
        for (int r = 0; r < rows; r++)
            for (int c = 0; c < 9; c++) addSlot(new BagSlot(bag, c + r * 9, 8 + c * 18, 18 + r * 18));
        int invY = invY(rows);
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 9; c++) addSlot(new Slot(inv, c + r * 9 + 9, 8 + c * 18, invY + r * 18));
        for (int c = 0; c < 9; c++) addSlot(new Slot(inv, c, 8 + c * 18, invY + 58));
    }

    public static int invY(int rows) { return 18 + rows * 18 + 14; }

    /** Ouvre le sac porté, s'il y en a un. */
    public static void open(ServerPlayer p) {
        ItemStack worn = AccContainer.of(p).getItem(AccSlot.DOS.ordinal());
        int cap = Bags.capacity(worn);
        if (cap <= 0) {
            p.displayClientMessage(Component.literal("§7Tu ne portes pas de sac (emplacement Dos des accessoires)."), true);
            return;
        }
        SimpleContainer c = new SimpleContainer(cap);
        NonNullList<ItemStack> items = Bags.load(worn);
        for (int i = 0; i < cap; i++) c.setItem(i, items.get(i));
        c.addListener(x -> write(p, worn, x));
        NetworkHooks.openScreen(p, new SimpleMenuProvider((id, inv, pl) -> new BagMenu(id, inv, c, worn), worn.getHoverName()), buf -> buf.writeVarInt(cap));
    }

    private static void write(Player p, ItemStack worn, Container c) {
        NonNullList<ItemStack> items = NonNullList.withSize(c.getContainerSize(), ItemStack.EMPTY);
        for (int i = 0; i < items.size(); i++) items.set(i, c.getItem(i));
        Bags.save(worn, items);
        AccContainer.of(p).persist();
    }

    @Override
    public boolean stillValid(Player p) {
        if (bagStack == null) return true;   // client
        return p.isAlive() && AccContainer.of(p).getItem(AccSlot.DOS.ordinal()) == bagStack;   // toujours le même sac sur le dos
    }

    @Override
    public ItemStack quickMoveStack(Player p, int index) {
        Slot slot = slots.get(index);
        if (!slot.hasItem()) return ItemStack.EMPTY;
        ItemStack st = slot.getItem();
        ItemStack copy = st.copy();
        int n = rows * 9;
        if (index < n) {
            if (!moveItemStackTo(st, n, n + 36, true)) return ItemStack.EMPTY;
        } else {
            if (!Bags.allowedInside(st) || !moveItemStackTo(st, 0, n, false)) return ItemStack.EMPTY;
        }
        if (st.isEmpty()) slot.setByPlayer(ItemStack.EMPTY); else slot.setChanged();
        return copy;
    }

    @Override
    public void removed(Player p) {
        super.removed(p);
        if (bagStack != null && !p.level().isClientSide) write(p, bagStack, bag);
    }

    /** Case du sac : ni sac, ni boîte de Shulker. */
    static final class BagSlot extends Slot {
        BagSlot(Container c, int i, int x, int y) { super(c, i, x, y); }

        @Override public boolean mayPlace(ItemStack st) { return Bags.allowedInside(st); }
    }
}
