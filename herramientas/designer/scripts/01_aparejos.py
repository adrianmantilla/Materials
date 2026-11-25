"""Designer: grafos de las estructuras de aparejo (ladrillo, bloque, sillería, baldosa, tablas).

Cada estructura es un grafo dentro de ``paquetes/aparejos_lote1.sbs`` con estas salidas
(escala de grises, 16 bits):

* ``piezas``: 1 en la pieza, 0 en la junta, con cantos irregulares según ``irregular``.
* ``gris``: un gris al azar por pieza (flood fill).
* ``incl``: un degradado por pieza en dirección al azar (piezas algo inclinadas).
* ``nubes``: variación grande (mortero, manchas).
* ``motas``: detalle fino de la cara.
* ``grunge``: desgaste y desconchones.

El bisel, la altura final, la máscara y el normal se componen después con medidas reales
(``componer.py``), para no depender de las unidades internas de cada nodo.
"""

import os
import sys
import traceback

import importlib

import fabrica_sd as fsd
import estructuras_def as ed

# Designer guarda los módulos entre ejecuciones: se recargan para leer la versión nueva.
importlib.reload(fsd)
importlib.reload(ed)

PAQUETE = os.path.join(CARPETA, "paquetes", "aparejos_lote1.sbs")  # noqa: F821
SOLO = None  # o una lista de ids para pruebas


def montar(paquete, d, detalle=False):
    tw, th = ed.tile_cm(d)
    nx, ny = d["piezas"]
    mx, my = d["pieza_cm"][0] + d["junta_cm"], d["pieza_cm"][1] + d["junta_cm"]
    g = fsd.Grafo(paquete, d["id"])
    ladrillos = g.bib("brick_generator", Bricks=(nx, ny), Keep_Ratio=False,
                      Gap=(d["junta_cm"] / mx, d["junta_cm"] / my),
                      Bevel=(0.0, 0.0, 0.0, 0.0), Offset=(d["desfase"], 0.0))
    nubes = g.bib("noise_clouds_2", "clouds_2", scale=max(1, int(round(tw / 60.0))))
    motas = g.bib("noise_bnw_spots_1", "bnw_spots_1", scale=max(1, int(round(tw / 12.0))))
    grunge = g.bib("noise_grunge_map_001", "grunge_map_001", balance=0.5, contrast=0.6)
    fino = g.bib("noise_perlin_noise", "perlin_noise", scale=max(8, int(round(tw / 1.5))))
    # Cantos irregulares: deformar con ruido fino + nubes y volver a umbralizar.
    deform = g.mezcla(nubes, fino, fsd.SUMA_RESTA, 0.5)
    warp = g.atomo("warp", intensity=0.6 * d["irregular"] * (d["junta_cm"] / mx) * 4.0)
    g.unir(ladrillos, warp, "input1")
    g.unir(deform, warp, "inputgradient", indice_entrada=1)
    piezas = g.bib("histogram_scan", Position=0.5, Contrast=1.0)
    g.unir(warp, piezas)
    relleno = g.bib("flood_fill", "flood_fill")
    g.unir(piezas, relleno)
    gris = g.bib("flood_fill", "flood_fill_to_random_grayscale")
    g.unir(relleno, gris)
    incl = g.bib("flood_fill", "flood_fill_to_gradient", angle=0.0, angle_variation=1.0)
    g.unir(relleno, incl)
    for nodo, nombre in ((piezas, "piezas"), (gris, "gris"), (incl, "incl"), (nubes, "nubes"),
                         (motas, "motas"), (grunge, "grunge"), (ladrillos, "forma")):
        g.salida(nodo, nombre)
    if detalle:
        for nodo in (ladrillos, warp, piezas, relleno, gris, incl, nubes, motas, grunge, fino, deform):
            print("  ", fsd.describir_nodo(nodo))
    return g


paquete = fsd.paquete_nuevo()
hechos = []
for i, d in enumerate(ed.LOTE_1):
    if SOLO and d["id"] not in SOLO:
        continue
    try:
        montar(paquete, d, detalle=(i == 0))
        hechos.append(d["id"])
        print("grafo", d["id"], "tile", ed.tile_cm(d))
    except Exception:
        print("ERROR en", d["id"])
        traceback.print_exc()
        if not hechos:
            break  # el primero falla: los demás fallarán igual
fsd.guardar(paquete, PAQUETE)
print("guardado", PAQUETE, "con", len(hechos), "grafos:", " ".join(hechos))
if not hechos:
    raise RuntimeError("no se ha montado ningún grafo")
