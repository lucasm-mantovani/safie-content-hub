"""
rasterizar_capa.py — Rasteriza a capa SVG de um artigo em JPG 1200x630.

Motivo: og:image / twitter:image / JSON-LD image não renderizam SVG em preview
social (Facebook, LinkedIn, WhatsApp, X). O SVG continua sendo a arte-fonte e a
imagem visível na página; o JPG é derivado só para as tags sociais.

Rasterizador: Chromium headless (alta fidelidade de fontes/gradientes). Presente
no ambiente via cache do Playwright. Conversão PNG->JPG via ImageMagick.

Fonte única usada por:
  - scripts/publicar.py                (artigos futuros nascem com o JPG)
  - scripts/backfill_ogimage_raster.py (backfill dos artigos já publicados)

FALHA ALTO (RuntimeError com mensagem clara) se o binário do Chromium ou o
ImageMagick não forem encontrados — mitigação do risco de o cache do Playwright
mudar de caminho e quebrar a geração diária silenciosamente.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

LARGURA, ALTURA = 1200, 630
QUALIDADE_JPG_PADRAO = int(os.environ.get("CAPA_JPG_QUALITY", "85"))


def _achar_chromium() -> str:
    """Localiza o binário do Chromium headless. Override por CHROME_HEADLESS_BIN."""
    env = os.environ.get("CHROME_HEADLESS_BIN")
    if env and Path(env).is_file() and os.access(env, os.X_OK):
        return env

    cache = Path.home() / "Library" / "Caches" / "ms-playwright"
    candidatos = []
    # 1. headless shell (preferido — leve, é o que testamos)
    candidatos += sorted(
        cache.glob("chromium_headless_shell-*/chrome-headless-shell-*/chrome-headless-shell"),
        reverse=True,
    )
    # 2. Chromium/Chrome for Testing completo (fallback)
    candidatos += sorted(cache.glob("chromium-*/chrome-mac*/**/MacOS/*"), reverse=True)

    for c in candidatos:
        if c.is_file() and os.access(c, os.X_OK):
            return str(c)

    raise RuntimeError(
        "FALHA CRÍTICA (rasterizar_capa): binário do Chromium headless NÃO encontrado. "
        "Procurei em $CHROME_HEADLESS_BIN e em "
        "~/Library/Caches/ms-playwright/chromium_headless_shell-*/. "
        "A rasterização da capa (og:image) NÃO pode prosseguir. "
        "Corrija com 'npx playwright install chromium' ou defina CHROME_HEADLESS_BIN "
        "apontando para um chrome-headless-shell executável."
    )


def _achar_magick() -> list:
    """Retorna o comando base do ImageMagick ('magick' ou 'convert')."""
    magick = shutil.which("magick")
    if magick:
        return [magick]
    convert = shutil.which("convert")
    if convert:
        return [convert]
    raise RuntimeError(
        "FALHA CRÍTICA (rasterizar_capa): ImageMagick (magick/convert) NÃO encontrado "
        "para converter PNG->JPG. Instale com 'brew install imagemagick'."
    )


def rasterizar(svg_path, jpg_path, qualidade: int = QUALIDADE_JPG_PADRAO) -> Path:
    """Rasteriza svg_path -> jpg_path (JPG 1200x630). Retorna o Path do JPG.
    Levanta RuntimeError em qualquer falha (fail loud)."""
    svg_path = Path(svg_path)
    jpg_path = Path(jpg_path)
    if not svg_path.is_file():
        raise RuntimeError(f"FALHA (rasterizar_capa): SVG de origem não existe: {svg_path}")

    chrome = _achar_chromium()
    magick = _achar_magick()

    with tempfile.TemporaryDirectory(prefix="capa_raster_") as td:
        td = Path(td)
        # SVG local + wrapper HTML 1200x630 sem margens (screenshot fiel, pixel-perfect)
        (td / "capa.svg").write_text(svg_path.read_text(encoding="utf-8"), encoding="utf-8")
        (td / "wrap.html").write_text(
            "<!doctype html><html><head><style>*{margin:0;padding:0}"
            f"html,body{{width:{LARGURA}px;height:{ALTURA}px;overflow:hidden}}"
            f"img{{display:block;width:{LARGURA}px;height:{ALTURA}px}}</style></head>"
            '<body><img src="capa.svg"></body></html>',
            encoding="utf-8",
        )
        png = td / "capa.png"
        cmd = [
            chrome, "--headless", "--disable-gpu", "--hide-scrollbars",
            "--force-device-scale-factor=1", f"--window-size={LARGURA},{ALTURA}",
            f"--user-data-dir={td / 'profile'}",
            f"--screenshot={png}", str(td / "wrap.html"),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FALHA (rasterizar_capa): Chromium travou (timeout) em {svg_path.name}")
        if not png.is_file():
            raise RuntimeError(
                f"FALHA (rasterizar_capa): Chromium não gerou PNG para {svg_path.name}. "
                f"stderr: {(r.stderr or '')[-500:]}"
            )

        # PNG -> JPG (strip de metadados; qualidade parametrizável)
        jpg_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_conv = magick + [str(png), "-strip", "-quality", str(qualidade), str(jpg_path)]
        try:
            r2 = subprocess.run(cmd_conv, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FALHA (rasterizar_capa): ImageMagick travou (timeout) em {svg_path.name}")
        if not jpg_path.is_file():
            raise RuntimeError(
                f"FALHA (rasterizar_capa): conversão PNG->JPG falhou para {svg_path.name}. "
                f"stderr: {(r2.stderr or '')[-500:]}"
            )

    # Verificação de dimensão (fail loud) — Pillow já está no ambiente
    try:
        from PIL import Image
        with Image.open(jpg_path) as im:
            if im.size != (LARGURA, ALTURA):
                raise RuntimeError(
                    f"FALHA (rasterizar_capa): dimensão inesperada {im.size} "
                    f"(esperado {LARGURA}x{ALTURA}) em {jpg_path.name}"
                )
    except ImportError:
        pass  # sem Pillow: pula a checagem (não deveria acontecer neste ambiente)

    return jpg_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        sys.exit("uso: python3 scripts/rasterizar_capa.py <origem.svg> <destino.jpg> [qualidade]")
    q = int(sys.argv[3]) if len(sys.argv) > 3 else QUALIDADE_JPG_PADRAO
    out = rasterizar(sys.argv[1], sys.argv[2], q)
    print(f"OK: {out} (q={q})")
