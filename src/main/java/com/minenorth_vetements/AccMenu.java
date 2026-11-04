package com.minenorth_vetements;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;

/**
 * Menu « Accessoires » : les 5 emplacements + l'inventaire du joueur. Ouvert par le serveur (bouton de l'inventaire créatif, /accessoires),
 * c'est un conteneur ordinaire : il se synchronise normalement, y compris en mode créatif où les cases ajoutées à l'inventaire survie
 * n'apparaissent pas. Partage le même {@link AccContainer} que ces cases. En dessous : gilet, cagoule et brassard de ZeroContact ({@link ZcSlots}).
 */
public class AccMenu extends AbstractContainerMenu {
    public static final int SLOT_X = 80, SLOT_Y = 26;
    private static final int N = Accessories.N;

    public AccMenu(int id, Inventory inv) {
        super(MineNorthVetements.ACC_MENU.get(), id);
        AccContainer c = AccContainer.of(inv.player);
        for (AccSlot s : AccSlot.values()) addSlot(new AccessorySlot(c, s, SLOT_X + s.ordinal() * 18, SLOT_Y));
        for (int row = 0; row < 3; row++)
            for (int col = 0; col < 9; col++) addSlot(new Slot(inv, col + row * 9 + 9, 8 + col * 18, 84 + row * 18));
        for (int col = 0; col < 9; col++) addSlot(new Slot(inv, col, 8 + col * 18, 142));
        ZcSlots.create(inv.player, SLOT_X, SLOT_Y + 20, 18).forEach(this::addSlot);   // après l'inventaire : indices inchangés
    }

    public static void open(ServerPlayer p) {
        p.openMenu(new SimpleMenuProvider((id, inv, pl) -> new AccMenu(id, inv), Component.translatable("container.minenorth_vetements.accessoires")));
    }

    /** Maj + clic : un accessoire va dans sa case, une case renvoie vers l'inventaire. */
    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        Slot slot = slots.get(index);
        if (!slot.hasItem()) return ItemStack.EMPTY;
        ItemStack st = slot.getItem();
        ItemStack copy = st.copy();
        if (index >= N + 36) {   // case ZeroContact -> inventaire
            if (!moveItemStackTo(st, N, N + 36, true)) return ItemStack.EMPTY;
        } else if (index < N) {
            if (!moveItemStackTo(st, N, N + 36, true)) return ItemStack.EMPTY;
        } else {
            AccSlot t = Accessories.slotOf(st);
            if (t != null && !slots.get(t.ordinal()).hasItem()) {
                if (!moveItemStackTo(st, t.ordinal(), t.ordinal() + 1, false)) return ItemStack.EMPTY;
            } else if (index < N + 27) {
                if (!moveItemStackTo(st, N + 27, N + 36, false)) return ItemStack.EMPTY;
            } else if (!moveItemStackTo(st, N, N + 27, false)) return ItemStack.EMPTY;
        }
        if (st.isEmpty()) slot.setByPlayer(ItemStack.EMPTY); else slot.setChanged();
        if (st.getCount() == copy.getCount()) return ItemStack.EMPTY;
        slot.onTake(player, st);
        return copy;
    }

    @Override
    public boolean stillValid(Player player) { return player.isAlive(); }
}
