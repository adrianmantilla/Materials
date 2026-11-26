"""Designer: grafos de las estructuras de aparejo (ladrillo, bloque, sillería, baldosa, tablas).

Cada estructura es un grafo dentro de ``paquetes/aparejos_lote1.sbs`` con estas salidas
(escala de grises, 16 bits):

* ``forma``: 1 en la pieza, 0 en la junta (aparejo exacto, sin deformar).
* ``nubes``: variación grande (mortero, manchas).
* ``motas``: detalle fino de la cara.
* ``grunge``: desgaste y desconchones.

Los cantos irregulares, la numeración de piezas (gris e inclinación de cada una), el grano
fino, los poros, el bisel, la altura, la máscara y el normal se componen después en numpy
con medidas reales (``fabricar.py``): así no dependen de las unidades internas de cada nodo
y no se usan ruidos FX-map a escala alta, que hacen eterno el render.
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

LOTE = globals().get("LOTE", "lote1")  # fabricar_lote.py lo pasa
PAQUETE = os.path.join(CARPETA, "paquetes", "aparejos_{}.sbs".format(LOTE))  # noqa: F821
SOLO = None  # o una lista de ids para pruebas


def montar(paquete, d, detalle=False):
    tw, th = ed.tile_cm(d)
    g = fsd.Grafo(paquete, d["id"])
    nubes = g.bib("noise_clouds_2", "clouds_2", scale=max(1, int(round(tw / 60.0))))
    motas = g.bib("noise_bnw_spots_1", "bnw_spots_1", scale=max(1, int(round(tw / 12.0))))
    grunge = g.bib("noise_grunge_map_001", "grunge_map_001", balance=0.5, contrast=0.6)
    salidas = [(nubes, "nubes"), (motas, "motas"), (grunge, "grunge")]
    if "patron" in d:  # la forma la dibuja fabricar.py (lib/patrones.py)
        for nodo, nombre in salidas:
            g.salida(nodo, nombre)
        return g
    nx, ny = d["piezas"]
    mx, my = d["pieza_cm"][0] + d["junta_cm"], d["pieza_cm"][1] + d["junta_cm"]
    ladrillos = g.bib("brick_generator", Bricks=(nx, ny), Keep_Ratio=False,
                      Gap=(d["junta_cm"] / mx, d["junta_cm"] / my),
                      Bevel=(0.0, 0.0, 0.0, 0.0), Offset=(d["desfase"], 0.0))
    for nodo, nombre in [(ladrillos, "forma")] + salidas:
        g.salida(nodo, nombre)
    if detalle:
        for nodo in (ladrillos, nubes, motas, grunge):
            print("  ", fsd.describir_nodo(nodo))
    return g


paquete = fsd.paquete_nuevo()
hechos = []
for i, d in enumerate(ed.LOTES[LOTE]):
    if SOLO and d["id"] not in SOLO:
        continue
    try:
        montar(paquete, d, detalle=(i == 0))
        hechos.append(d["id"])
        print("grafo", d["id"], "tile", ed.tile_cm(d))
    except BaseException:  # la API de Designer lanza excepciones que no heredan de Exception
        print("ERROR en", d["id"])
        traceback.print_exc()
        if not hechos:
            break  # el primero falla: los demás fallarán igual
fsd.guardar(paquete, PAQUETE)
print("guardado", PAQUETE, "con", len(hechos), "grafos:", " ".join(hechos))
if not hechos:
    raise RuntimeError("no se ha montado ningún grafo")
