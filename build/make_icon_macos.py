"""Genera assets/icon.icns para el bundle .app de macOS.

Reusa la misma identidad visual que build/make_icon.py (fondo #1e1e2e +
tres barras con gradiente azul #3b82f6 -> #60a5fa), pero exportando a .icns
(formato que requiere PyInstaller/macOS para el ícono del .app), en vez de
.ico (Windows). No modifica ni reemplaza make_icon.py: son artefactos
distintos para pipelines distintos.

Requiere Pillow (ya en requirements.txt). Uso:
    python3 build/make_icon_macos.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

S = 1024  # lienzo base de alta resolucion (icns pide hasta 1024x1024)
BG = (30, 30, 46, 255)        # #1e1e2e
C_BOTTOM = (59, 130, 246)     # #3b82f6
C_TOP = (96, 165, 250)        # #60a5fa
OUT = Path(__file__).parent.parent / "assets" / "icon.icns"

# Misma grilla/proporciones que make_icon.py (barras en grilla de 64).
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
    # Pillow soporta exportar ICNS directamente si corre en cualquier
    # plataforma (no requiere iconutil), incluyendo el set de tamaños
    # estandar que macOS espera para Finder/Dock/Launchpad.
    sizes = [(s, s) for s in (16, 32, 64, 128, 256, 512, 1024)]
    img.save(OUT, format="ICNS", sizes=sizes)
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
