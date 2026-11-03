package com.minenorth_vetements;

import net.minecraft.core.NonNullList;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.ContainerHelper;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.registries.ForgeRegistries;

/**
 * Sacs de rangement (emplacement dos des accessoires). Le contenu est enregistré DANS l'objet sac (tag {@link #TAG}) : il suit le sac quand
 * on le retire, le pose, le donne, ou qu'il tombe à la mort, sans jamais exister en double. Seul le sac porté s'ouvre (voir {@link BagMenu}).
 */
public final class Bags {
    private Bags() {}

    public static final String TAG = "mnv_sac";

    /** Nombre de cases (multiple de 9), 0 si ce n'est pas un sac. */
    public static int capacity(ItemStack st) {
        if (st.isEmpty()) return 0;
        ResourceLocation key = ForgeRegistries.ITEMS.getKey(st.getItem());
        if (key == null || !key.getNamespace().equals(MineNorthVetements.MODID)) return 0;
        return capacity(key.getPath());
    }

    public static int capacity(String id) {
        if (id.startsWith("banane_") || id.startsWith("sacoche_")) return 9;     // petits sacs
        if (id.startsWith("sac_dos_") || id.startsWith("sac_luxe_")) return 18;  // sacs à dos
        if (id.startsWith("sac_sport_") || id.equals("sac_vip")) return 27;      // sac de sport, sac VIP
        if (id.startsWith("sac_rando_")) return 36;                              // gros sac de randonnée
        return 0;
    }

    /** Peut-on ranger cet objet dans un sac ? Ni sac (même vide), ni boîte de Shulker ou autre objet-conteneur. */
    public static boolean allowedInside(ItemStack st) {
        return st.isEmpty() || (capacity(st) == 0 && st.getItem().canFitInsideContainerItems());
    }

    public static NonNullList<ItemStack> load(ItemStack bag) {
        NonNullList<ItemStack> items = NonNullList.withSize(capacity(bag), ItemStack.EMPTY);
        CompoundTag tag = bag.getTag();
        if (tag != null && tag.contains(TAG)) ContainerHelper.loadAllItems(tag.getCompound(TAG), items);
        return items;
    }

    public static void save(ItemStack bag, NonNullList<ItemStack> items) {
        if (items.stream().allMatch(ItemStack::isEmpty)) {
            bag.removeTagKey(TAG);
            if (bag.getTag() != null && bag.getTag().isEmpty()) bag.setTag(null);   // un sac vide redevient empilable / comparable avec un neuf
            return;
        }
        bag.getOrCreateTag().put(TAG, ContainerHelper.saveAllItems(new CompoundTag(), items, false));
    }

    /** Nombre d'objets (piles) rangés, pour l'infobulle. */
    public static int count(ItemStack bag) {
        CompoundTag tag = bag.getTag();
        return tag != null && tag.contains(TAG) ? tag.getCompound(TAG).getList("Items", 10).size() : 0;
    }

    /** Copie à envoyer aux autres joueurs pour le rendu : sans le contenu (inutile, et ce serait de l'espionnage gratuit). */
    public static ItemStack withoutContents(ItemStack st) {
        if (st.isEmpty() || st.getTag() == null || !st.getTag().contains(TAG)) return st;
        ItemStack c = st.copy();
        c.removeTagKey(TAG);
        return c;
    }
}
