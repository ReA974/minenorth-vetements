package com.minenorth_vetements.client;

import com.minenorth_vetements.AccMenu;
import com.minenorth_vetements.AccessorySlot;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;

import java.util.List;

/** Écran du menu Accessoires : aperçu du joueur, les 5 cases (avec icônes fantômes) et l'inventaire, dans le style des fenêtres vanilla. */
public class AccScreen extends AbstractContainerScreen<AccMenu> {
    public AccScreen(AccMenu menu, Inventory inv, Component title) {
        super(menu, inv, title);
        imageWidth = 176;
        imageHeight = 166;
        inventoryLabelY = imageHeight - 94;
    }

    private net.minecraft.client.gui.components.Button bagButton;

    @Override
    protected void init() {
        super.init();
        bagButton = addRenderableWidget(BagClient.button(leftPos + AccMenu.SLOT_X, topPos + AccMenu.SLOT_Y + 40, 5 * 18 - 2));
    }

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partial) {
        if (bagButton != null) bagButton.visible = BagClient.wearsBag();   // seulement avec un sac sur le dos
        renderBackground(g);
        super.render(g, mouseX, mouseY, partial);
        if (hoveredSlot instanceof AccessorySlot a && !a.hasItem() && menu.getCarried().isEmpty()) {
            g.renderComponentTooltip(font, List.of(
                    Component.literal("Accessoire · " + a.type.label).withStyle(ChatFormatting.GOLD),
                    Component.literal(InventoryPanel.HINT[a.type.ordinal()]).withStyle(ChatFormatting.GRAY)), mouseX, mouseY);
        } else if (hoveredSlot != null && !hoveredSlot.hasItem() && menu.getCarried().isEmpty() && com.minenorth_vetements.ZcSlots.label(hoveredSlot) != null) {
            g.renderTooltip(font, Component.literal(com.minenorth_vetements.ZcSlots.label(hoveredSlot)).withStyle(ChatFormatting.GOLD), mouseX, mouseY);
        } else {
            renderTooltip(g, mouseX, mouseY);
        }
    }

    @Override
    protected void renderBg(GuiGraphics g, float partial, int mouseX, int mouseY) {
        int x = leftPos, y = topPos, w = imageWidth, h = imageHeight;
        // fenêtre vanilla : bord noir aux coins arrondis, reflet blanc, ombre grise
        g.fill(x + 2, y, x + w - 2, y + 1, 0xFF000000);
        g.fill(x + 2, y + h - 1, x + w - 2, y + h, 0xFF000000);
        g.fill(x, y + 2, x + 1, y + h - 2, 0xFF000000);
        g.fill(x + w - 1, y + 2, x + w, y + h - 2, 0xFF000000);
        g.fill(x + 1, y + 1, x + 2, y + 2, 0xFF000000); g.fill(x + w - 2, y + 1, x + w - 1, y + 2, 0xFF000000);
        g.fill(x + 1, y + h - 2, x + 2, y + h - 1, 0xFF000000); g.fill(x + w - 2, y + h - 2, x + w - 1, y + h - 1, 0xFF000000);
        g.fill(x + 1, y + 1, x + w - 1, y + h - 1, 0xFFC6C6C6);
        g.fill(x + 1, y + 2, x + 3, y + h - 3, 0xFFFFFFFF);
        g.fill(x + 2, y + 1, x + w - 3, y + 3, 0xFFFFFFFF);
        g.fill(x + w - 3, y + 3, x + w - 1, y + h - 2, 0xFF555555);
        g.fill(x + 3, y + h - 3, x + w - 1, y + h - 1, 0xFF555555);
        // aperçu du joueur
        g.fill(x + 7, y + 17, x + 70, y + 70, 0xFF373737);
        g.fill(x + 8, y + 18, x + 70, y + 70, 0xFFFFFFFF);
        g.fill(x + 8, y + 18, x + 69, y + 69, 0xFF000000);
        if (minecraft != null && minecraft.player != null)
            InventoryScreen.renderEntityInInventoryFollowsMouse(g, x + 38, y + 66, 23, (float) (x + 38) - mouseX, (float) (y + 66 - 38) - mouseY, minecraft.player);
        // cases
        for (Slot s : menu.slots) {
            int sx = x + s.x - 1, sy = y + s.y - 1;
            g.fill(sx, sy, sx + 18, sy + 18, 0xFF373737);
            g.fill(sx + 1, sy + 1, sx + 18, sy + 18, 0xFFFFFFFF);
            g.fill(sx + 1, sy + 1, sx + 17, sy + 17, 0xFF8B8B8B);
        }
    }

    @Override
    protected void renderLabels(GuiGraphics g, int mouseX, int mouseY) {
        g.drawString(font, title, titleLabelX, titleLabelY, 0x404040, false);
        g.drawString(font, "Inventaire", inventoryLabelX, inventoryLabelY, 0x404040, false);   // en français même si le jeu est en anglais
        if (!com.minenorth_vetements.ZcSlots.enabled()) g.drawString(font, "Survole une case", AccMenu.SLOT_X, AccMenu.SLOT_Y + 22, 0x6A6A6A, false);
    }
}
