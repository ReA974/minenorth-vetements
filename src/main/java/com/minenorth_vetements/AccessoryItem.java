package com.minenorth_vetements;

import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResultHolder;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.level.Level;

import javax.annotation.Nullable;
import java.util.List;

/**
 * Accessoire de visage (lunettes, cagoule, bandana, écharpe) : clic droit = le porter (en plus du chapeau), accroupi + clic droit = retirer
 * l'accessoire porté. Un seul accessoire à la fois : en porter un autre rend le précédent.
 */
public class AccessoryItem extends Item {
    public AccessoryItem(Properties props) { super(props); }

    @Override
    public InteractionResultHolder<ItemStack> use(Level level, Player player, InteractionHand hand) {
        ItemStack held = player.getItemInHand(hand);
        if (level.isClientSide || !(player instanceof ServerPlayer p)) return InteractionResultHolder.sidedSuccess(held, level.isClientSide);
        ItemStack worn = Accessories.worn(p);
        if (p.isShiftKeyDown()) {
            if (worn.isEmpty()) {
                p.displayClientMessage(Component.literal("§7Tu ne portes aucun accessoire."), true);
            } else {
                Accessories.set(p, ItemStack.EMPTY);
                if (!p.getInventory().add(worn)) p.drop(worn, false);
                p.displayClientMessage(Component.literal("§7Accessoire retiré."), true);
                level.playSound(null, p.blockPosition(), SoundEvents.ARMOR_EQUIP_GENERIC, SoundSource.PLAYERS, 0.6f, 1.1f);
            }
            return InteractionResultHolder.success(held);
        }
        ItemStack one = held.copy();
        one.setCount(1);
        held.shrink(1);
        Accessories.set(p, one);
        if (!worn.isEmpty() && !p.getInventory().add(worn)) p.drop(worn, false);
        p.displayClientMessage(Component.literal("§aAccessoire porté."), true);
        level.playSound(null, p.blockPosition(), SoundEvents.ARMOR_EQUIP_LEATHER, SoundSource.PLAYERS, 0.7f, 1.2f);
        return InteractionResultHolder.success(held);
    }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tip, TooltipFlag flag) {
        tip.add(Component.literal("§7Clic droit : le porter (en plus du chapeau)."));
        tip.add(Component.literal("§7Accroupi + clic droit (même main vide) : retirer l'accessoire porté."));
    }
}
