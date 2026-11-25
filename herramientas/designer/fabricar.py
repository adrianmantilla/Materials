"""Fábrica de motivos (Mac): .sbs de Designer → .sbsar → PNG → mapas finales del catálogo.

    venv/bin/python herramientas/designer/fabricar.py <paquete.sbs> <catalogo> [--res 1024] [--solo id,id]

1. ``sbscooker`` cocina el paquete en .sbsar.
2. ``sbsrender`` saca, por cada grafo, las salidas en bruto (piezas, gris, incl, nubes,
   motas, grunge) a ``<catalogo>/_bruto/<id>/``.
3. ``componer`` las convierte en los mapas que lee Materials a tamaño real:
   ``estructuras/<id>/<res>/altura.png`` (16 bits), ``mascara.png`` (RGB sin alfa:
   R junta, G gris por pieza, B desgaste), ``normal.png`` (OpenGL), ``miniatura.png`` y
   ``motivo.json``. Además deja ``<catalogo>/_hoja_<paquete>.jpg`` con todas las miniaturas
   y ``_informe_<paquete>.json`` con medidas de control (costuras, proporción de junta...).

Necesita numpy y Pillow (el venv de la fábrica).
"""

import argparse
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "lib"))
import estructuras_def as ed  # noqa: E402

DESIGNER = "/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS"
BRUTOS = ("piezas", "gris", "incl", "nubes", "motas", "grunge")
CARPETA_RES = {256: "1k", 512: "1k", 1024: "1k", 2048: "2k", 4096: "4k"}


def ejecutar(orden):
    print("$", " ".join(orden))
    r = subprocess.run(orden, capture_output=True, text=True)
    salida = (r.stdout + r.stderr).strip()
    if salida:
        print("\n".join(salida.splitlines()[-15:]))
    if r.returncode:
        raise RuntimeError("falló ({}): {}".format(r.returncode, orden[0]))
    return salida


def cocinar(sbs):
    carpeta = os.path.dirname(os.path.abspath(sbs))
    ejecutar([os.path.join(DESIGNER, "sbscooker"), "--inputs", sbs, "--output-path", carpeta])
    return os.path.splitext(os.path.abspath(sbs))[0] + ".sbsar"


def renderizar(sbsar, ident, destino, res, semilla=1):
    os.makedirs(destino, exist_ok=True)
    for viejo in glob.glob(os.path.join(destino, "*.png")):
        os.remove(viejo)
    log2 = int(round(np.log2(res)))
    ejecutar([os.path.join(DESIGNER, "sbsrender"), "render", "--input", sbsar, "--input-graph", "pkg://" + ident,
              "--output-path", destino, "--output-name", "{outputNodeName}", "--output-format", "png",
              "--set-value", "$outputsize@{},{}".format(log2, log2), "--set-value", "$randomseed@{}".format(semilla)])


# --- Composición (numpy) -------------------------------------------------------------------------

def leer(ruta):
    im = Image.open(ruta)
    a = np.asarray(im)
    if a.ndim == 3:
        a = a[..., :3].mean(axis=2)
    escala = 65535.0 if a.dtype == np.uint16 or a.max() > 255 else 255.0
    return a.astype(np.float64) / escala


def suave(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def distancia_interior(mascara, px_x, px_y, maximo_cm):
    """Distancia aproximada (cm) de cada píxel de pieza al borde, hasta ``maximo_cm``. Repite sin costuras."""
    paso = min(px_x, px_y)
    d = np.where(mascara, maximo_cm, 0.0)
    vecinos = [((0, 1), px_x), ((0, -1), px_x), ((1, 0), px_y), ((-1, 0), px_y),
               ((1, 1), np.hypot(px_x, px_y)), ((1, -1), np.hypot(px_x, px_y)),
               ((-1, 1), np.hypot(px_x, px_y)), ((-1, -1), np.hypot(px_x, px_y))]
    for _ in range(int(np.ceil(maximo_cm / paso)) + 2):
        nuevo = d
        for (dy, dx), coste in vecinos:
            nuevo = np.minimum(nuevo, np.roll(d, (dy, dx), axis=(0, 1)) + coste)
        nuevo = np.where(mascara, nuevo, 0.0)
        if np.array_equal(nuevo, d):
            break
        d = nuevo
    return np.minimum(d, maximo_cm)


def normal_opengl(altura, relieve_cm, cm_px_x, cm_px_y):
    h = altura * relieve_cm
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * cm_px_x)
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) / (2 * cm_px_y)
    # Imagen con y hacia abajo; OpenGL (Maya) tiene el verde hacia arriba.
    n = np.dstack([-dx, dy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def hex_a_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def vista(altura, normal, mascara_rgb, junta_hex, lado=256):
    """Miniatura sombreada: pieza gris cálido con variación, junta de su color, luz rasante."""
    n = normal * 2 - 1
    luz = np.array([-0.55, 0.45, 0.70])
    luz /= np.linalg.norm(luz)
    lambert = np.clip((n * luz).sum(axis=2), 0, 1)
    pieza = np.array([0.62, 0.42, 0.33]) * (0.8 + 0.4 * mascara_rgb[..., 1:2])
    pieza = pieza * (1 - 0.35 * mascara_rgb[..., 2:3]) + 0.35 * mascara_rgb[..., 2:3] * np.array([0.75, 0.7, 0.62])
    base = pieza * (1 - mascara_rgb[..., 0:1]) + hex_a_rgb(junta_hex) * mascara_rgb[..., 0:1]
    color = base * (0.25 + 0.9 * lambert[..., None])
    im = Image.fromarray((np.clip(color, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8), "RGB")
    return im.resize((lado, lado), Image.LANCZOS)


def costura(a):
    """Salto en el borde de la imagen dividido por el mayor salto entre columnas (o filas) interiores.

    Hasta ~1 no hay costura (el borde no salta más que una junta normal); bastante más de 1 la delata.
    """
    peor = 0.0
    for eje in (0, 1):
        b = np.moveaxis(a, eje, 0)
        interior = np.abs(np.diff(b, axis=0)).mean(axis=1).max() + 1e-9
        borde = np.abs(b[0] - b[-1]).mean()
        peor = max(peor, borde / interior)
    return round(float(peor), 2)


def componer(d, bruto, destino_raiz, res):
    b = {n: leer(os.path.join(bruto, n + ".png")) for n in BRUTOS}
    n = b["piezas"].shape[0]
    tw, th = ed.tile_cm(d)
    cm_px_x, cm_px_y = tw / b["piezas"].shape[1], th / n
    mascara = b["piezas"] > 0.5
    bisel = max(d["bisel_cm"], 0.6 * max(cm_px_x, cm_px_y))
    dist = distancia_interior(mascara, cm_px_x, cm_px_y, bisel * 3.0)
    perfil = suave(dist, 0.0, bisel)  # 0 en el canto, 1 en la cara
    av, ru, ir = d["altura_var"], d["rugoso"], d["irregular"]
    cara = (0.70 + 0.10 * av * (b["gris"] - 0.5) + 0.08 * av * (b["incl"] - 0.5)
            + 0.06 * ru * (b["motas"] - 0.5) + 0.04 * ru * (b["nubes"] - 0.5))
    # Desconchones cerca del canto en piezas hechas a mano.
    cerca = 1.0 - suave(dist, bisel, bisel * 3.0)
    mancha = 1.0 - b["grunge"]  # grunge_map_001 es casi blanco con manchas oscuras
    desconchon = suave(mancha, 0.45 - 0.15 * ir, 0.6 - 0.15 * ir) * cerca * ir
    cara = cara - 0.25 * desconchon
    junta = 0.12 + 0.10 * b["nubes"] + 0.04 * b["motas"]
    altura = junta + (np.maximum(cara, junta) - junta) * perfil
    altura = np.clip(altura, 0.0, 1.0)
    desgaste = np.clip(1.6 * mancha * (1.0 - 0.5 * perfil) - 0.15 + 0.5 * desconchon, 0.0, 1.0) * mascara
    gris = np.where(mascara, b["gris"], 0.5)
    en_junta = 1.0 - suave(dist, 0.0, 1.5 * max(cm_px_x, cm_px_y))  # canto suavizado un píxel
    mascara_rgb = np.dstack([en_junta, gris, desgaste])
    normal = normal_opengl(altura, d["relieve_cm"], cm_px_x, cm_px_y)

    carpeta = os.path.join(destino_raiz, "estructuras", d["id"])
    sub = os.path.join(carpeta, CARPETA_RES.get(res, "1k"))
    os.makedirs(sub, exist_ok=True)
    Image.fromarray((altura * 65535).round().astype(np.uint16)).save(os.path.join(sub, "altura.png"))
    Image.fromarray((mascara_rgb * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "mascara.png"))
    Image.fromarray((normal * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "normal.png"))
    mini = vista(altura, normal, mascara_rgb, d["junta"])
    mini.save(os.path.join(carpeta, "miniatura.png"))
    datos = {k: d[k] for k in ("id", "nombre", "familia", "junta", "recomendado_para", "etiquetas", "relieve_cm")}
    datos.update(tile_cm=[round(tw, 3), round(th, 3)], pieza_cm=d["pieza_cm"][0], color2=False, licencia="CC0",
                 fabrica="designer", version=1)
    with open(os.path.join(carpeta, "motivo.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    junta_real = 1.0 - (d["pieza_cm"][0] * d["pieza_cm"][1]) / ((d["pieza_cm"][0] + d["junta_cm"]) *
                                                              (d["pieza_cm"][1] + d["junta_cm"]))
    informe = {"id": d["id"], "res": [int(x) for x in b["piezas"].shape],
               "junta_px": round(float(1.0 - mascara.mean()), 4), "junta_esperada": round(junta_real, 4),
               "grises_distintos": int(len(np.unique(np.round(gris[dist > 3 * max(cm_px_x, cm_px_y)], 2)))),
               # Píxeles de pieza (lejos del canto) cuyo gris cambia con el vecino: el flood fill ha fallado.
               "gris_ruidoso": round(float((np.abs(gris - np.roll(gris, 2, axis=1))[dist > 3 * max(cm_px_x, cm_px_y)]
                                            > 0.02).mean()), 4),
               "piezas_esperadas": d["piezas"][0] * d["piezas"][1],
               "costura_altura": costura(altura), "costura_mascara": costura(mascara_rgb[..., 0]),
               "altura_min_max": [round(float(altura.min()), 3), round(float(altura.max()), 3)],
               "desgaste_medio": round(float(desgaste.mean()), 3)}
    return mini, informe


def hoja(minis, ruta, columnas=6):
    lado = 256
    filas = (len(minis) + columnas - 1) // columnas
    lienzo = Image.new("RGB", (columnas * lado, filas * (lado + 18)), (24, 24, 24))
    dibujo = ImageDraw.Draw(lienzo)
    for i, (nombre, im) in enumerate(minis):
        x, y = (i % columnas) * lado, (i // columnas) * (lado + 18)
        lienzo.paste(im, (x, y))
        dibujo.text((x + 4, y + lado + 3), nombre, fill=(220, 220, 220))
    lienzo.save(ruta, quality=88)
    return ruta


def hoja_renders(carpeta, ruta, lado=360, columnas=4):
    """Junta los PNG de hoja_arnold.py en una hoja con el nombre debajo de cada uno."""
    minis = []
    for f in sorted(os.listdir(carpeta)):
        if f.endswith(".png"):
            im = Image.open(os.path.join(carpeta, f)).convert("RGB").resize((lado, lado), Image.LANCZOS)
            minis.append((os.path.splitext(f)[0], im))
    filas = (len(minis) + columnas - 1) // columnas
    lienzo = Image.new("RGB", (columnas * lado, filas * (lado + 20)), (24, 24, 24))
    dibujo = ImageDraw.Draw(lienzo)
    for i, (nombre, im) in enumerate(minis):
        x, y = (i % columnas) * lado, (i // columnas) * (lado + 20)
        lienzo.paste(im, (x, y))
        dibujo.text((x + 5, y + lado + 4), nombre, fill=(225, 225, 225))
    lienzo.save(ruta, quality=90)
    print("hoja:", ruta, len(minis), "renders")
    return ruta


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--hoja-renders":
        hoja_renders(sys.argv[2], sys.argv[3])
        return
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("sbs")
    p.add_argument("catalogo")
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--solo", default="")
    p.add_argument("--sin-render", action="store_true", help="solo componer desde _bruto")
    a = p.parse_args()
    solo = [x for x in a.solo.split(",") if x]
    sbsar = os.path.splitext(os.path.abspath(a.sbs))[0] + ".sbsar"
    if not a.sin_render:
        sbsar = cocinar(a.sbs)
        print(ejecutar([os.path.join(DESIGNER, "sbsrender"), "info", "--input", sbsar])[:3000])
    minis, informes = [], []
    for d in ed.LOTE_1:
        if solo and d["id"] not in solo:
            continue
        bruto = os.path.join(a.catalogo, "_bruto", d["id"])
        try:
            if not a.sin_render:
                renderizar(sbsar, d["id"], bruto, a.res)
            faltan = [n for n in BRUTOS if not os.path.isfile(os.path.join(bruto, n + ".png"))]
            if faltan:
                print("FALTAN", d["id"], faltan, os.listdir(bruto) if os.path.isdir(bruto) else "-")
                continue
            mini, informe = componer(d, bruto, a.catalogo, a.res)
            minis.append((d["id"], mini))
            informes.append(informe)
            print("OK", json.dumps(informe, ensure_ascii=False))
        except Exception as e:  # sigue con las demás
            print("ERROR", d["id"], e)
    nombre = os.path.splitext(os.path.basename(a.sbs))[0]
    if minis:
        print("hoja:", hoja(minis, os.path.join(a.catalogo, "_hoja_{}.jpg".format(nombre))))
    with open(os.path.join(a.catalogo, "_informe_{}.json".format(nombre)), "w", encoding="utf-8") as f:
        json.dump(informes, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
