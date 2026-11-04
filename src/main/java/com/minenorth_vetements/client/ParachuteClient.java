package com.minenorth_vetements.client;

import com.minenorth_vetements.AccNet;
import com.minenorth_vetements.MineNorthVetements;
import com.minenorth_vetements.Parachute;
import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.blaze3d.vertex.VertexConsumer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.client.renderer.MultiBufferSource;
import net.minecraft.client.renderer.RenderType;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RenderLevelStageEvent;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import org.joml.Matrix4f;

import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Parachute côté joueur : Espace en chute libre (avec le parachute dans l'emplacement Dos) ouvre la voile. La descente est freinée et on plane
 * vers où l'on regarde (le joueur gère son propre mouvement) ; le serveur confirme et annule les dégâts de chute. La voile (caissons orange
 * et blancs, suspentes) est dessinée au-dessus de chaque joueur dont la voile est ouverte, y compris soi-même (visible en levant les yeux).
 */
@Mod.EventBusSubscriber(modid = MineNorthVetements.MODID, value = Dist.CLIENT)
public final class ParachuteClient {
    private ParachuteClient() {}

    private static final Set<Integer> OPEN = ConcurrentHashMap.newKeySet();
    private static boolean jumpWasDown;
    /** Ouverture demandée, en attente de la réponse du serveur (le mouvement est freiné tout de suite). */
    private static boolean predicted;
    private static final float FALL_SPEED = 0.11f, GLIDE = 0.24f;

    public static void state(int entityId, boolean open) {
        if (open) OPEN.add(entityId); else OPEN.remove(entityId);
        Minecraft mc = Minecraft.getInstance();
        if (mc.player != null && mc.player.getId() == entityId) predicted = false;
    }

    private static boolean mine(LocalPlayer p) { return predicted || OPEN.contains(p.getId()); }

    @SubscribeEvent
    public static void logout(ClientPlayerNetworkEvent.LoggingOut e) { OPEN.clear(); predicted = false; }

    @SubscribeEvent
    public static void tick(TickEvent.ClientTickEvent e) {
        if (e.phase != TickEvent.Phase.START) return;
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer p = mc.player;
        if (p == null || mc.level == null) { OPEN.clear(); predicted = false; return; }
        boolean down = mc.options.keyJump.isDown();
        boolean pressed = down && !jumpWasDown && mc.screen == null;
        jumpWasDown = down;
        if (!mine(p)) {
            if (pressed && Parachute.canOpen(p) && Parachute.wears(p, AccessoryClient.get(p.getId()))) {
                predicted = true;
                AccNet.CHANNEL.sendToServer(new Parachute.Request(true));
            }
            return;
        }
        if (p.onGround() || p.isInWater() || p.isPassenger()) { predicted = false; OPEN.remove(p.getId()); return; }
        // voile ouverte : chute lente, on plane dans la direction du regard (un peu plus vite en avançant)
        Vec3 v = p.getDeltaMovement();
        double vy = Math.max(v.y, -FALL_SPEED);
        if (v.y < -FALL_SPEED) vy = Mth.lerp(0.35, v.y, -FALL_SPEED);   // la voile s'ouvre : freinage progressif
        Vec3 look = Vec3.directionFromRotation(0, p.getYRot());
        double push = p.input.forwardImpulse > 0 ? GLIDE : GLIDE * 0.45;
        double vx = Mth.lerp(0.08, v.x, look.x * push), vz = Mth.lerp(0.08, v.z, look.z * push);
        p.setDeltaMovement(vx, vy, vz);
        p.fallDistance = 0;
    }

    // ------------------------------------------------------------------ rendu de la voile

    @SubscribeEvent
    public static void render(RenderLevelStageEvent e) {
        if (e.getStage() != RenderLevelStageEvent.Stage.AFTER_TRANSLUCENT_BLOCKS) return;
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || (OPEN.isEmpty() && !predicted)) return;
        Vec3 cam = e.getCamera().getPosition();
        PoseStack ps = e.getPoseStack();
        MultiBufferSource.BufferSource buf = mc.renderBuffers().bufferSource();
        VertexConsumer vc = buf.getBuffer(RenderType.debugQuads());
        float pt = e.getPartialTick();
        for (Player pl : mc.level.players()) {
            boolean open = OPEN.contains(pl.getId()) || (pl == mc.player && predicted);
            if (!open || pl.isRemoved()) continue;
            double x = Mth.lerp(pt, pl.xo, pl.getX()) - cam.x, y = Mth.lerp(pt, pl.yo, pl.getY()) - cam.y, z = Mth.lerp(pt, pl.zo, pl.getZ()) - cam.z;
            ps.pushPose();
            ps.translate(x, y, z);
            ps.mulPose(com.mojang.math.Axis.YP.rotationDegrees(-Mth.rotLerp(pt, pl.yBodyRotO, pl.yBodyRot)));
            drawCanopy(vc, ps.last().pose(), pl.tickCount + pt);
            ps.popPose();
        }
        buf.endBatch(RenderType.debugQuads());
    }

    private static final int CELLS = 9;
    private static final float SPAN = 5.2f, CHORD = 1.6f, TOP = 4.6f, ARCH = 1.1f;

    private static float[] point(int i, float sway) {
        float t = (float) i / CELLS * 2 - 1;   // -1 .. 1 sur l'envergure
        float x = t * SPAN / 2 + sway * 0.05f;
        float y = TOP - ARCH * t * t;
        return new float[]{x, y};
    }

    private static void drawCanopy(VertexConsumer vc, Matrix4f m, float time) {
        float sway = Mth.sin(time * 0.08f);
        float zf = -CHORD / 2 + 0.25f, zb = CHORD / 2 + 0.25f;   // un peu en avant du joueur, comme une aile qui tire
        for (int i = 0; i < CELLS; i++) {
            float[] a = point(i, sway), b = point(i + 1, sway);
            int c = i % 2 == 0 ? 0xFFE8601C : 0xFFF2F0EA;
            int d = shade(c, 0.78f);
            // extrados (dessus), intrados (dessous, plus sombre), bord d'attaque
            quad(vc, m, a[0], a[1], zf, b[0], b[1], zf, b[0], b[1], zb, a[0], a[1], zb, c);
            quad(vc, m, a[0], a[1] - 0.22f, zf, a[0], a[1] - 0.22f, zb, b[0], b[1] - 0.22f, zb, b[0], b[1] - 0.22f, zf, d);
            quad(vc, m, a[0], a[1], zf, a[0], a[1] - 0.22f, zf, b[0], b[1] - 0.22f, zf, b[0], b[1], zf, shade(c, 0.6f));
        }
        // suspentes : des épaules du joueur vers le dessous de la voile
        int line = 0xFF2A2A2E;
        for (int i = 0; i <= CELLS; i += 3) {
            float[] a = point(i, sway);
            float sx = a[0] < 0 ? -0.3f : 0.3f;
            cord(vc, m, sx, 1.45f, 0.1f, a[0], a[1] - 0.22f, zf + 0.2f, line);
            cord(vc, m, sx, 1.45f, 0.1f, a[0], a[1] - 0.22f, zb - 0.2f, line);
        }
    }

    private static int shade(int c, float k) {
        int r = (int) (((c >> 16) & 255) * k), g = (int) (((c >> 8) & 255) * k), b = (int) ((c & 255) * k);
        return 0xFF000000 | (r << 16) | (g << 8) | b;
    }

    /** Suspente : fine bande verticale (deux faces croisées pour rester visible sous tous les angles). */
    private static void cord(VertexConsumer vc, Matrix4f m, float x0, float y0, float z0, float x1, float y1, float z1, int c) {
        float w = 0.015f;
        quad(vc, m, x0 - w, y0, z0, x0 + w, y0, z0, x1 + w, y1, z1, x1 - w, y1, z1, c);
        quad(vc, m, x0, y0, z0 - w, x0, y0, z0 + w, x1, y1, z1 + w, x1, y1, z1 - w, c);
    }

    private static void quad(VertexConsumer vc, Matrix4f m, float ax, float ay, float az, float bx, float by, float bz,
                             float cx, float cy, float cz, float dx, float dy, float dz, int c) {
        vertex(vc, m, ax, ay, az, c); vertex(vc, m, bx, by, bz, c); vertex(vc, m, cx, cy, cz, c); vertex(vc, m, dx, dy, dz, c);
        vertex(vc, m, dx, dy, dz, c); vertex(vc, m, cx, cy, cz, c); vertex(vc, m, bx, by, bz, c); vertex(vc, m, ax, ay, az, c);
    }

    private static void vertex(VertexConsumer vc, Matrix4f m, float x, float y, float z, int c) {
        vc.vertex(m, x, y, z).color((c >> 16) & 255, (c >> 8) & 255, c & 255, 255).endVertex();
    }

    /** Joueur parti : on oublie sa voile. */
    public static void forget(Entity e) { OPEN.remove(e.getId()); }
}
