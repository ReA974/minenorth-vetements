package com.minenorth_vetements;

import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ArmorItem;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.eventbus.api.IEventBus;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.ForgeRegistries;
import net.minecraftforge.registries.RegistryObject;

import java.util.ArrayList;
import java.util.List;

@Mod(MineNorthVetements.MODID)
public class MineNorthVetements {
    public static final String MODID = "minenorth_vetements";

    private static final DeferredRegister<Item> ITEMS = DeferredRegister.create(ForgeRegistries.ITEMS, MODID);
    private static final DeferredRegister<CreativeModeTab> TABS = DeferredRegister.create(Registries.CREATIVE_MODE_TAB, MODID);
    private static final List<RegistryObject<Item>> ALL = new ArrayList<>();
    /** Objets affichés dans l'onglet créatif commun « MineNorth ». */
    public static final CreativeModeTab.DisplayItemsGenerator TAB_ITEMS = (params, out) -> ALL.forEach(r -> out.accept(r.get()));

    public MineNorthVetements() {
        IEventBus bus = FMLJavaModLoadingContext.get().getModEventBus();
        for (OutfitData.Outfit o : OutfitData.ALL) {
            ClothesMaterial mat = new ClothesMaterial(o.id());
            if (o.cap() && Accessories.isAccessory(o.id())) addAccessory(o.id() + "_helmet");     // lunettes, cagoules, bandanas, écharpes : emplacement accessoire
            else if (o.cap()) add(o.id() + "_helmet", mat, ArmorItem.Type.HELMET);
            if (o.chest()) add(o.id() + "_chestplate", mat, ArmorItem.Type.CHESTPLATE);
            if (o.legs()) add(o.id() + "_leggings", mat, ArmorItem.Type.LEGGINGS);
            if (o.boots()) add(o.id() + "_boots", mat, ArmorItem.Type.BOOTS);
        }
        ITEMS.register(bus);
        AccNet.register();
    }

    private static void addAccessory(String name) {
        ALL.add(ITEMS.register(name, () -> new AccessoryItem(new Item.Properties().stacksTo(1))));
    }

    private static void add(String name, ClothesMaterial mat, ArmorItem.Type type) {
        ALL.add(ITEMS.register(name, () -> new ClothesItem(mat, type, new Item.Properties().stacksTo(1))));
    }
}
