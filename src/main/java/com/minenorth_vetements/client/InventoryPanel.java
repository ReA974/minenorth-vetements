package com.minenorth_vetements.client;

import com.minenorth_vetements.AccContainer;
import com.minenorth_vetements.AccSlot;
import com.minenorth_vetements.AccessorySlot;
import com.minenorth_vetements.MineNorthVetements;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.inventory.Slot;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ContainerScreenEvent;
import net.minecraftforge.client.event.ScreenEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

import java.util.List;

/**
 * Panneau des accessoires dans l'inventaire du joueur : une colonne de 5 emplacements collée à gauche de la fenêtre, à côté de l'armure, dans
 * le style des panneaux vanilla. Masqué quand le livre de recettes est ouvert (il occupe cette place).
 * Inventaire créatif : les emplacements en sont retirés (le créatif ne synchronise que les emplacements vanilla avec le serveur ; sinon ils
 * s'afficheraient par-dessus la barre d'action) ; un bouton « Accessoires » sur l'onglet inventaire ouvre à la place le menu dédié ({@code AccMenu}).
 */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID, value = Dist.CLIENT)
public final class InventoryPanel {
    private InventoryPanel() {}

    private static final int HIDDEN = -10000;
    static final String[] HINT = {
            "Lunettes, cagoule, bandana", "Chaîne, collier, écharpe", "Montre, gourmette", "Gants", "Sac à dos, banane, sacoche"};

    private static boolean visible(InventoryScreen s) { return !s.getRecipeBookComponent().isVisible(); }

    /** Place (ou cache) les emplacements avant chaque image : ils suivent l'ouverture / fermeture du livre de recettes. */
    private static void layout(InventoryScreen s) {
        boolean show = visible(s);
        for (Slot slot : s.getMenu().slots) {
            if (!(slot instanceof AccessorySlot a)) continue;
            slot.x = show ? AccessorySlot.X : HIDDEN;
            slot.y = show ? AccessorySlot.Y0 + a.type.ordinal() * 18 : HIDDEN;
        }
    }

    private static void stripCreative(CreativeModeInventoryScreen s) {
        s.getMenu().slots.removeIf(slot -> slot.container instanceof AccContainer);
    }

    /** Bouton « Sac » sous le panneau des accessoires (inventaire survie), visible avec un sac sur le dos. */
    private static net.minecraft.client.gui.components.Button invBagButton;

    private static void placeBagButton(InventoryScreen s) {
        if (invBagButton == null) return;
        invBagButton.visible = visible(s) && BagClient.wearsBag();
        invBagButton.setX(s.getGuiLeft() + AccessorySlot.X - 7);
        invBagButton.setY(s.getGuiTop() + AccessorySlot.Y0 + AccSlot.values().length * 18 + 8);
    }

    /** Bouton de l'onglet inventaire du créatif : ouvre le menu Accessoires (conteneur synchronisé par le serveur). */
    private static net.minecraft.client.gui.components.Button creativeButton;

    @SubscribeEvent
    public static void init(ScreenEvent.Init.Post e) {
        if (e.getScreen() instanceof InventoryScreen s) {
            layout(s);
            invBagButton = BagClient.button(0, 0, 28);
            placeBagButton(s);
            e.addListener(invBagButton);
        } else if (e.getScreen() instanceof CreativeModeInventoryScreen c) {
            stripCreative(c);
            creativeButton = net.minecraft.client.gui.components.Button.builder(Component.literal("Accessoires"),
                            b -> com.minenorth_vetements.AccNet.CHANNEL.sendToServer(new com.minenorth_vetements.AccNet.OpenMenu()))
                    .bounds(c.getGuiLeft() + 126, c.getGuiTop() + 20, 64, 16)
                    .tooltip(net.minecraft.client.gui.components.Tooltip.create(Component.literal("Lunettes, chaînes, montres, gants, sacs…")))
                    .build();
            creativeButton.visible = c.isInventoryOpen();
            e.addListener(creativeButton);
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void renderPre(ScreenEvent.Render.Pre e) {
        if (e.getScreen() instanceof InventoryScreen s) { layout(s); placeBagButton(s); }
        else if (e.getScreen() instanceof CreativeModeInventoryScreen c) {
            stripCreative(c);
            if (creativeButton != null) creativeButton.visible = c.isInventoryOpen();   // seulement sur l'onglet inventaire
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void clickPre(ScreenEvent.MouseButtonPressed.Pre e) {
        if (e.getScreen() instanceof InventoryScreen s) layout(s);
        else if (e.getScreen() instanceof CreativeModeInventoryScreen c) stripCreative(c);
    }

    /** Fond du panneau et des cases, dessinés après le fond de l'inventaire et avant les objets. */
    @SubscribeEvent
    public static void background(ContainerScreenEvent.Render.Background e) {
        if (!(e.getContainerScreen() instanceof InventoryScreen s) || !visible(s)) return;
        GuiGraphics g = e.getGuiGraphics();
        int x0 = s.getGuiLeft() + AccessorySlot.X - 7, y0 = s.getGuiTop() + AccessorySlot.Y0 - 7;
        int x1 = s.getGuiLeft() + 3, y1 = y0 + 7 + AccSlot.values().length * 18 + 6;
        // panneau vanilla (bord noir arrondi, reflet blanc, ombre grise) qui se fond dans le bord gauche de l'inventaire
        g.fill(x0 + 2, y0, x1, y0 + 1, 0xFF000000);
        g.fill(x0 + 2, y1 - 1, x1, y1, 0xFF000000);
        g.fill(x0, y0 + 2, x0 + 1, y1 - 2, 0xFF000000);
        g.fill(x0 + 1, y0 + 1, x0 + 2, y0 + 2, 0xFF000000);
        g.fill(x0 + 1, y1 - 2, x0 + 2, y1 - 1, 0xFF000000);
        g.fill(x0 + 1, y0 + 2, x1, y1 - 2, 0xFFC6C6C6);
        g.fill(x0 + 2, y0 + 1, x1, y1 - 1, 0xFFC6C6C6);
        g.fill(x0 + 1, y0 + 2, x0 + 3, y1 - 3, 0xFFFFFFFF);   // reflet à gauche
        g.fill(x0 + 2, y0 + 1, x1, y0 + 3, 0xFFFFFFFF);       // reflet en haut
        g.fill(x0 + 3, y1 - 3, x1, y1 - 1, 0xFF555555);       // ombre en bas
        for (AccSlot t : AccSlot.values()) {
            int sx = s.getGuiLeft() + AccessorySlot.X - 1, sy = s.getGuiTop() + AccessorySlot.Y0 + t.ordinal() * 18 - 1;
            g.fill(sx, sy, sx + 18, sy + 18, 0xFF373737);
            g.fill(sx + 1, sy + 1, sx + 18, sy + 18, 0xFFFFFFFF);
            g.fill(sx + 1, sy + 1, sx + 17, sy + 17, 0xFF8B8B8B);
        }
    }

    /** Infobulle sur un emplacement vide : à quoi il sert. */
    @SubscribeEvent
    public static void tooltip(ScreenEvent.Render.Post e) {
        if (!(e.getScreen() instanceof InventoryScreen s) || !visible(s)) return;
        if (!(s.getSlotUnderMouse() instanceof AccessorySlot a) || a.hasItem() || !s.getMenu().getCarried().isEmpty()) return;
        e.getGuiGraphics().renderComponentTooltip(net.minecraft.client.Minecraft.getInstance().font, List.of(
                Component.literal("Accessoire · " + a.type.label).withStyle(ChatFormatting.GOLD),
                Component.literal(HINT[a.type.ordinal()]).withStyle(ChatFormatting.GRAY),
                Component.literal("En plus du chapeau et des vêtements").withStyle(ChatFormatting.DARK_GRAY)), e.getMouseX(), e.getMouseY());
    }
}
