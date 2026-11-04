package com.minenorth_vetements;

import net.minecraft.world.SimpleContainer;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.fml.ModList;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Cases ZeroContact dans le menu Accessoires : gilet pare-balles, cagoule / masque, brassard. Ce sont les vraies cases Curios (CurioSlot) de
 * ZeroContact : l'objet reste là où ZeroContact le lit, on n'a plus besoin de son menu. Toujours 3 cases quand Curios et ZeroContact sont
 * installés (même nombre côté serveur et client) ; une case pas encore synchronisée par Curios est inerte. Par réflexion, sans dépendance.
 */
public final class ZcSlots {
    private ZcSlots() {}

    public static final Map<String, String> SLOTS = new LinkedHashMap<>();

    static {
        SLOTS.put("zc_plate_carrier", "Gilet pare-balles (ZeroContact)");
        SLOTS.put("zc_mask", "Cagoule / masque (ZeroContact)");
        SLOTS.put("zc_armband", "Brassard (ZeroContact)");
    }

    public static boolean enabled() { return ModList.get().isLoaded("curios") && ModList.get().isLoaded("zerocontact"); }

    public static List<Slot> create(Player p, int x, int y, int pitch) {
        List<Slot> out = new ArrayList<>();
        if (!enabled()) return out;
        int i = 0;
        for (String id : SLOTS.keySet()) {
            Slot s = null;
            try {
                Object lazy = Class.forName("top.theillusivec4.curios.api.CuriosApi").getMethod("getCuriosInventory", LivingEntity.class).invoke(null, p);
                Object inv = ((Optional<?>) lazy.getClass().getMethod("resolve").invoke(lazy)).orElse(null);
                Class<?> api = Class.forName("top.theillusivec4.curios.api.type.capability.ICuriosItemHandler");
                Object h = inv == null ? null : ((Optional<?>) api.getMethod("getStacksHandler", String.class).invoke(inv, id)).orElse(null);
                if (h != null) {
                    Class<?> sh = Class.forName("top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler");
                    Class<?> dyn = Class.forName("top.theillusivec4.curios.api.type.inventory.IDynamicStackHandler");
                    s = (Slot) Class.forName("top.theillusivec4.curios.common.inventory.CurioSlot").getConstructor(Player.class, dyn, int.class, String.class,
                                    int.class, int.class, net.minecraft.core.NonNullList.class, boolean.class)
                            .newInstance(p, sh.getMethod("getStacks").invoke(h), 0, id, x + i * pitch, y, sh.getMethod("getRenders").invoke(h),
                                    (boolean) sh.getMethod("canToggleRendering").invoke(h));
                }
            } catch (ReflectiveOperationException | RuntimeException | LinkageError e) {
                com.mojang.logging.LogUtils.getLogger().warn("[Vetements] Case ZeroContact {} indisponible : {}", id, e.toString());
            }
            if (s == null) s = new Slot(new SimpleContainer(1), 0, x + i * pitch, y) {
                @Override public boolean mayPlace(ItemStack st) { return false; }
                @Override public boolean mayPickup(Player pl) { return false; }
            };
            out.add(s);
            i++;
        }
        return out;
    }

    public static String label(Slot slot) {
        if (!slot.getClass().getName().equals("top.theillusivec4.curios.common.inventory.CurioSlot")) return null;
        try {
            return SLOTS.get((String) slot.getClass().getMethod("getIdentifier").invoke(slot));
        } catch (ReflectiveOperationException e) {
            return null;
        }
    }
}
