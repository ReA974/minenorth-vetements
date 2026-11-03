package com.minenorth_vetements.client;

import com.minenorth_vetements.BagMenu;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;

/** Écran du sac porté, aux couleurs MineNorth (bleu nuit, liserés cyan et rose, coins arrondis), comme la banque et les permis. */
public class BagScreen extends AbstractContainerScreen<BagMenu> {
    static final int FRAME = 0xFF0E0E10, PANEL = 0xFF161048, LIST = 0xFF0E0A34, HOVER = 0xFF2E2480, CYAN = 0xFF20AAEB, PINK = 0xFFC83CF0,
            TEXT = 0xFFFFFFFF, MUTED = 0xFF8FA8E0;

    public BagScreen(BagMenu menu, Inventory inv, Component title) {
        super(menu, inv, title);
        imageWidth = 176;
        imageHeight = BagMenu.invY(menu.rows) + 83;
        inventoryLabelY = BagMenu.invY(menu.rows) - 11;
    }

    @Override
    public void render(GuiGraphics g, int mouseX, int mouseY, float partial) {
        renderBackground(g);
        super.render(g, mouseX, mouseY, partial);
        renderTooltip(g, mouseX, mouseY);
    }

    /** Rectangle aux coins arrondis (rayon r, en escalier). */
    static void round(GuiGraphics g, int x0, int y0, int x1, int y1, int r, int color) {
        for (int i = 0; i < r; i++) {
            int cut = r - (int) Math.round(Math.sqrt(r * r - (r - i - 0.5) * (r - i - 0.5)));
            g.fill(x0 + cut, y0 + i, x1 - cut, y0 + i + 1, color);
            g.fill(x0 + cut, y1 - i - 1, x1 - cut, y1 - i, color);
        }
        g.fill(x0, y0 + r, x1, y1 - r, color);
    }

    @Override
    protected void renderBg(GuiGraphics g, float partial, int mouseX, int mouseY) {
        int x = leftPos, y = topPos;
        round(g, x - 2, y - 2, x + imageWidth + 2, y + imageHeight + 2, 7, FRAME);
        round(g, x, y, x + imageWidth, y + imageHeight, 6, PANEL);
        g.fill(x + 8, y + 15, x + imageWidth - 8, y + 16, HOVER);                               // filet sous le titre
        int bagBottom = y + 18 + menu.rows * 18;
        round(g, x + 5, y + 16, x + imageWidth - 5, bagBottom + 3, 4, LIST);                  // zone du sac
        g.fill(x + 10, bagBottom + 2, x + imageWidth - 10, bagBottom + 3, PINK);               // liseré rose
        for (Slot s : menu.slots) {
            int sx = x + s.x - 1, sy = y + s.y - 1;
            boolean bag = s.index < menu.rows * 9;
            round(g, sx, sy, sx + 18, sy + 18, 2, bag ? HOVER : LIST);
            round(g, sx + 1, sy + 1, sx + 17, sy + 17, 2, bag ? 0xFF1C1658 : 0xFF130E40);
        }
    }

    @Override
    protected void renderLabels(GuiGraphics g, int mouseX, int mouseY) {
        g.drawString(font, title, titleLabelX, titleLabelY, TEXT, false);
        String cap = menu.rows * 9 + " cases";
        g.drawString(font, cap, imageWidth - 8 - font.width(cap), titleLabelY, CYAN, false);
        g.drawString(font, "Inventaire", inventoryLabelX, inventoryLabelY, MUTED, false);   // en français même si le jeu est en anglais
    }
}
