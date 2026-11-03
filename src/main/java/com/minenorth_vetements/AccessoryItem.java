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
 * Accessoire (lunettes, cagoule, chaîne, montre, gants, sac...) : clic droit = le porter dans son emplacement (en plus des vêtements),
 * accroupi + clic droit = retirer l'accessoire porté dans cet emplacement. En porter un autre au même endroit rend le précédent.
 */
public class AccessoryItem extends Item {
    private final AccSlot slot;

    public AccessoryItem(AccSlot slot, Properties props) {
        super(props);
        this.slot = slot;
    }

    public AccSlot slot() { return slot; }

    /** Un sac ne se range ni dans une boîte de Shulker ni dans un autre sac (pas de rangement emboîté, pas de duplication). */
    @Override
    public boolean canFitInsideContainerItems() { return Bags.capacity(new ItemStack(this)) == 0; }

    @Override
    public void appendHoverText(ItemStack stack, @Nullable Level level, List<Component> tip, TooltipFlag flag) {
        tip.add(Component.literal("§6Accessoire · " + slot.label));
        int cap = Bags.capacity(stack);
        if (cap > 0) {
            int n = Bags.count(stack);
            tip.add(Component.literal("§bSac de rangement · " + cap + " cases" + (n > 0 ? " §7(" + n + " rangé" + (n > 1 ? "s" : "") + ")" : " §8(vide)")));
            tip.add(Component.literal("§7Porté sur le dos, il s'ouvre avec la touche Sac (B par défaut) ou le bouton « Sac »."));
        }
        net.minecraft.resources.ResourceLocation key = net.minecraftforge.registries.ForgeRegistries.ITEMS.getKey(stack.getItem());
        if (key != null && key.getPath().startsWith("cagoule_")) tip.add(Component.literal("§8Masque ton identité : pas de nom au-dessus de la tête, « " + Accessories.MASKED_NAME + " » dans le chat."));
        int vip = VipItems.level(stack);
        if (vip > 0) tip.add(Component.literal((vip >= 2 ? "§b" : "§d") + "Réservé aux " + (vip >= 2 ? "VIP+" : "VIP et VIP+")));
        tip.add(Component.literal("§7Se porte depuis le menu des accessoires (inventaire, ou /accessoires)."));
    }
}
