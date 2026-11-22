#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

One ripe strawberry, painted procedurally in pure-stdlib Python: a glossy
macro shot of a single berry on a warm cream background, water droplets,
seeds you can count, a green calyx on top. No network, no assets, no
third-party libraries -- the program draws every pixel itself and writes
/output/entry.png (1024x1024 PNG, under 1 MiB). Deterministic: same bytes
on every run.
"""
import math
import os
import random
import struct
import zlib

W = H = 1024
SEED = 20261122


def clamp(v, lo=0, hi=255):
    return lo if v < lo else hi if v > hi else int(v)


def main():
    rnd = random.Random(SEED)
    px = bytearray(W * H * 3)

    def blend(x, y, r, g, b, a):
        if x < 0 or x >= W or y < 0 or y >= H or a <= 0.0:
            return
        if a >= 1.0:
            i = (y * W + x) * 3
            px[i] = clamp(r)
            px[i + 1] = clamp(g)
            px[i + 2] = clamp(b)
            return
        i = (y * W + x) * 3
        ia = 1.0 - a
        px[i] = clamp(px[i] * ia + r * a)
        px[i + 1] = clamp(px[i + 1] * ia + g * a)
        px[i + 2] = clamp(px[i + 2] * ia + b * a)

    def soft_disc(cx, cy, rad, r, g, b, a0):
        """A disc with a soft radial falloff (for bokeh, gloss, shadow)."""
        x0 = max(0, int(cx - rad))
        x1 = min(W - 1, int(cx + rad))
        y0 = max(0, int(cy - rad))
        y1 = min(H - 1, int(cy + rad))
        for y in range(y0, y1 + 1):
            dy = (y - cy) / rad
            for x in range(x0, x1 + 1):
                dx = (x - cx) / rad
                d2 = dx * dx + dy * dy
                if d2 >= 1.0:
                    continue
                fall = 1.0 - d2
                blend(x, y, r, g, b, a0 * fall * fall)

    # ------------------------------------------------------------------
    # 1. Background: warm cream, lighter in the middle, soft bokeh dots.
    # ------------------------------------------------------------------
    for y in range(H):
        t = y / (H - 1)
        br = 252 - 22 * t
        bg = 240 - 30 * t
        bb = 218 - 42 * t
        row = y * W * 3
        for x in range(W):
            dx = (x - 512) / 700.0
            dy = (y - 430) / 700.0
            glow = max(0.0, 1.0 - (dx * dx + dy * dy)) * 14
            px[row] = clamp(br + glow)
            px[row + 1] = clamp(bg + glow)
            px[row + 2] = clamp(bb + glow)
            row += 3

    bokeh = [
        (150, 180, 70, 250, 225, 190, 0.10),
        (880, 150, 90, 245, 205, 160, 0.09),
        (920, 700, 60, 250, 220, 180, 0.10),
        (90, 820, 80, 240, 200, 150, 0.08),
        (300, 90, 45, 255, 235, 205, 0.10),
        (760, 880, 55, 245, 210, 165, 0.09),
        (60, 480, 50, 250, 225, 185, 0.07),
    ]
    for cx, cy, rad, r, g, b, a in bokeh:
        soft_disc(cx, cy, rad, r, g, b, a)

    # ------------------------------------------------------------------
    # 2. Berry body: broad shoulders tapering to a soft point.
    # ------------------------------------------------------------------
    TOP, BOT, CX = 185, 940, 512

    def half_width(y):
        if y < TOP or y > BOT:
            return 0.0
        t = (y - TOP) / (BOT - TOP)
        w = 305.0 * math.sin(math.pi * (0.10 + 0.90 * t)) ** 0.58
        # round the top corners in toward the calyx instead of a flat cut
        if t < 0.12:
            f = t / 0.12
            s = f * f * (3.0 - 2.0 * f)  # smoothstep, no kink where it joins
            w *= 0.55 + 0.45 * s
        # extra taper below the shoulders so the tip reads pointed, not round
        if t > 0.55:
            w *= 1.0 - 0.16 * ((t - 0.55) / 0.45) ** 1.5
        return w

    # soft contact shadow under the berry
    soft_disc(512, 905, 330, 120, 70, 40, 0.16)
    soft_disc(512, 900, 260, 110, 60, 35, 0.14)

    LX, LY = 400.0, 320.0  # light direction: upper left
    for y in range(TOP, BOT + 1):
        hw = half_width(y)
        if hw <= 0:
            continue
        t = (y - TOP) / (BOT - TOP)
        x0 = int(CX - hw)
        x1 = int(CX + hw)
        for x in range(x0, x1 + 1):
            dx = (x - CX) / hw
            if dx * dx > 1.0:
                continue
            edge = math.sqrt(max(0.0, 1.0 - dx * dx))
            # light falls off with distance from the light centre
            ddx = (x - LX) / 620.0
            ddy = (y - LY) / 620.0
            light = 1.18 - 0.62 * math.sqrt(ddx * ddx + ddy * ddy)
            light = max(0.25, min(1.25, light))
            # deep red at the rim, bright red in the light
            r = 150 + 105 * light
            g = 16 + 42 * light
            b = 20 + 30 * light
            # pinkish bloom where the light is strongest
            if light > 1.0:
                k = (light - 1.0) * 2.0
                r = r + (255 - r) * k * 0.6
                g = g + (120 - g) * k * 0.6
                b = b + (95 - b) * k * 0.6
            # darker toward the tip, and a rim darkening
            r *= 1.0 - 0.16 * t - 0.22 * (1.0 - edge)
            g *= 1.0 - 0.10 * t - 0.22 * (1.0 - edge)
            b *= 1.0 - 0.10 * t - 0.22 * (1.0 - edge)
            # fine speckle so the skin is not flat plastic
            n = ((x * 73 + y * 149) % 17 - 8)
            blend(x, y, r + n, g + n, b + n, 1.0)

    # ------------------------------------------------------------------
    # 3. Seeds (achenes): pale yellow, set in rows that follow the body.
    # ------------------------------------------------------------------
    def seed(cx, cy, rx, ry):
        # faint pit shadow, then the seed with a shaded rim
        soft_disc(cx + 2, cy + 3, rx + 2, 120, 20, 20, 0.30)
        for yy in range(int(cy - ry), int(cy + ry) + 1):
            for xx in range(int(cx - rx), int(cx + rx) + 1):
                ddx = (xx - cx) / rx
                ddy = (yy - cy) / ry
                d2 = ddx * ddx + ddy * ddy
                if d2 >= 1.0:
                    continue
                shade = 1.0 - 0.45 * math.sqrt(d2)
                blend(xx, yy, 252 * shade, 226 * shade, 152 * shade, 0.95)
        blend(int(cx - 2), int(cy - 3), 255, 245, 200, 0.9)

    row = 0
    y = 300
    while y < 870:
        hw = half_width(y)
        if hw > 60:
            spacing = 74
            off = (row % 2) * spacing // 2
            x = CX - hw + 42 + off
            while x < CX + hw - 40:
                # jitter so the rows read organic, not wallpaper
                jx = x + rnd.uniform(-9, 9)
                jy = y + rnd.uniform(-7, 7)
                js = rnd.uniform(0.85, 1.15)
                seed(jx, jy, 9 * js, 13 * js)
                x += spacing
        y += 62
        row += 1

    # ------------------------------------------------------------------
    # 4. Calyx: five green leaves fanning out of the top, plus a stem.
    # ------------------------------------------------------------------
    def leaf(bx, by, angle_deg, length, width, r0, g0, b0):
        ang = math.radians(angle_deg)
        dx = math.sin(ang)
        dy = -math.cos(ang)
        # sideways bend so the leaf curves a little
        bend = 0.25 if angle_deg > 0 else -0.25
        steps = int(length)
        for s in range(steps + 1):
            f = s / steps
            cx = bx + dx * s + bend * f * f * length * 0.5
            cy = by + dy * s
            w = width * math.sin(math.pi * (f ** 0.75)) * (1.0 - 0.25 * f)
            if w <= 0.5:
                continue
            shade = 0.85 + 0.30 * (1.0 - f)
            for xx in range(int(cx - w), int(cx + w) + 1):
                blend(xx, int(cy), r0 * shade, g0 * shade, b0 * shade, 0.98)
            # centre vein, lighter
            blend(int(cx), int(cy), 150, 200, 110, 0.5)

    # stem first (behind the leaves)
    for s in range(100):
        f = s / 99.0
        cx = 512 + 14 * math.sin(f * 1.2)
        cy = 210 - f * 95
        soft_disc(cx, cy, 10 - 4 * f, 96, 122, 58, 0.95)
    leaf(512, 215, -62, 140, 48, 34, 112, 46)
    leaf(512, 215, -32, 165, 52, 40, 128, 52)
    leaf(512, 215, 0, 180, 54, 46, 140, 56)
    leaf(512, 215, 32, 165, 52, 40, 128, 52)
    leaf(512, 215, 62, 140, 48, 34, 112, 46)

    # ------------------------------------------------------------------
    # 5. Gloss and water droplets: the "fresh, just picked" cues.
    # ------------------------------------------------------------------
    soft_disc(400, 350, 190, 255, 235, 225, 0.15)
    soft_disc(385, 330, 80, 255, 245, 235, 0.18)
    soft_disc(360, 300, 18, 255, 255, 255, 0.4)
    soft_disc(430, 470, 120, 255, 220, 210, 0.07)

    drops = []
    tries = 0
    while len(drops) < 14 and tries < 300:
        tries += 1
        x = rnd.uniform(260, 764)
        y = rnd.uniform(300, 880)
        hw = half_width(int(y))
        if hw <= 0 or abs(x - CX) > hw * 0.88:
            continue
        drops.append((x, y, rnd.uniform(8, 18)))
    for x, y, r in drops:
        soft_disc(x, y, r, 240, 105, 110, 0.55)
        soft_disc(x - r * 0.3, y - r * 0.35, r * 0.4, 255, 255, 255, 0.95)
        soft_disc(x + r * 0.45, y + r * 0.5, r * 0.55, 120, 15, 20, 0.3)

    # ------------------------------------------------------------------
    # 6. Vignette: darken the corners a touch so the eye stays on the berry.
    # ------------------------------------------------------------------
    for y in range(H):
        dy = (y - 512) / 512.0
        row = y * W * 3
        for x in range(W):
            dx = (x - 512) / 512.0
            d2 = dx * dx + dy * dy
            if d2 > 0.55:
                f = 1.0 - 0.10 * min(1.0, (d2 - 0.55) / 0.45)
                px[row] = clamp(px[row] * f)
                px[row + 1] = clamp(px[row + 1] * f)
                px[row + 2] = clamp(px[row + 2] * f)
            row += 3

    # ------------------------------------------------------------------
    # 7. Encode a plain PNG (filter 0) with zlib and write it out.
    # ------------------------------------------------------------------
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += px[y * W * 3:(y + 1) * W * 3]
    data = zlib.compress(bytes(raw), 9)

    def chunk(typ, payload):
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", data)
        + chunk(b"IEND", b"")
    )
    out_dir = os.environ.get("MAKEFUN_OUTPUT", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as fh:
        fh.write(png)
    print(f"wrote {path} ({len(png)} bytes)")


if __name__ == "__main__":
    main()
