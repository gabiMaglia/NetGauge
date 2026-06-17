"""Genera assets/icon.ico replicando el icono de la app (_make_icon de qt/app.py).

Fondo oscuro #1e1e2e + tres barras redondeadas con gradiente azul vertical
(#3b82f6 abajo -> #60a5fa arriba). Multi-size para que Windows lo use bien en
exe, accesos directos e instalador.

Uso:  python build/make_icon.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 256  # lienzo base de alta resolucion
BG = (30, 30, 46, 255)        # #1e1e2e
C_BOTTOM = (59, 130, 246)     # #3b82f6
C_TOP = (96, 165, 250)        # #60a5fa
OUT = Path(__file__).parent.parent / "assets" / "icon.ico"

# Barras (x, top) en grilla de 64, escaladas a S; ancho 10, hasta y=52.
BARS = [(12, 38), (27, 24), (42, 12)]
BAR_W, BASE = 10, 52
GRID = 64
k = S / GRID


def _vertical_gradient(w: int, h: int) -> Image.Image:
    grad = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)  # 0 arriba, 1 abajo
        r = round(C_TOP[0] + (C_BOTTOM[0] - C_TOP[0]) * t)
        g = round(C_TOP[1] + (C_BOTTOM[1] - C_TOP[1]) * t)
        b = round(C_TOP[2] + (C_BOTTOM[2] - C_TOP[2]) * t)
        grad.putpixel((0, y), (r, g, b))
    return grad.resize((w, h))


def main() -> None:
    img = Image.new("RGBA", (S, S), BG)
    # mascara de barras redondeadas
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    radius = round(2 * k)
    for x, top in BARS:
        x0, y0 = round(x * k), round(top * k)
        x1, y1 = round((x + BAR_W) * k), round(BASE * k)
        md.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=255)
    grad = _vertical_gradient(S, S).convert("RGBA")
    img.paste(grad, (0, 0), mask)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    img.save(OUT, format="ICO", sizes=sizes)
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
