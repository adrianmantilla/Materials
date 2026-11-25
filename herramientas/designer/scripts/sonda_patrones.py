"""Sonda: cómo se ven los tipos de patrón de tile_generator y tile_random, y los nodos de
formas que usará el lote 2 (espiga, hexágono, piedra irregular). Calcula cada grafo dentro
de Designer y guarda PNG pequeños en CARPETA/sonda/patrones/.
"""

import importlib
import os
import traceback

import fabrica_sd as fsd

importlib.reload(fsd)
from sd.api.sdproperty import SDPropertyCategory  # noqa: E402
from sd.api.sdbasetypes import int2  # noqa: E402
from sd.api.sdvalueint2 import SDValueInt2  # noqa: E402

SALIDA = os.path.join(CARPETA, "sonda", "patrones")  # noqa: F821
os.makedirs(SALIDA, exist_ok=True)
paquete = fsd.paquete_nuevo()


def calcular(g, nodo, nombre, salida=None):
    out = g.salida(nodo, nombre, salida=salida)
    g.g.setPropertyValue(g.g.getPropertyFromId("$outputsize", SDPropertyCategory.Input), SDValueInt2.sNew(int2(8, 8)))
    g.g.compute()
    props = out.getProperties(SDPropertyCategory.Output)
    tex = out.getPropertyValue(props[0]).get()
    tex.save(os.path.join(SALIDA, nombre + ".png"))


casos = []
for t in range(0, 17):
    casos.append(("tg_tipo_{:02d}".format(t), "tile_generator", None, dict(Pattern_Type=t, Nb_X=4, Nb_Y=4)))
for t in range(0, 12):
    casos.append(("tr_tipo_{:02d}".format(t), "tile_random", None, dict(pattern=t)))
for t in range(0, 12):
    casos.append(("ts_tipo_{:02d}".format(t), "tile_sampler", None, dict(pattern=t, x_amount=4, y_amount=4)))
casos += [
    ("tr_split", "tile_random", None, dict(pattern=1, split_mode=1, split_threshold=0.5, x_amount=6, y_amount=6)),
    ("cells1", "noise_cells_1", "cells_1", dict(scale=8)),
    ("crystal1", "noise_crystal_1", "crystal_1", dict(scale=8)),
    ("weave", "pattern_weave_generator", "weave_generator", dict(tile_x=4, tile_y=4)),
    ("brick2", "pattern_brick_generator", "brick_generator", dict(Bricks=(4, 8))),
]
for nombre, paquete_bib, grafo, params in casos:
    try:
        g = fsd.Grafo(paquete, nombre)
        nodo = g.bib(paquete_bib, grafo, **params)
        calcular(g, nodo, nombre)
        print("ok", nombre)
    except BaseException as e:  # la API de Designer lanza excepciones que no heredan de Exception
        print("ERROR", nombre, type(e).__mro__, e)
        traceback.print_exc()

for paquete_bib in ("pattern_polygon_1", "pattern_polygon_2", "pattern_alveolus", "pattern_arc_pavement",
                    "pattern_tile_random", "pattern_tile_generator", "shape_splatter_v2"):
    try:
        grafo = fsd.grafo_biblioteca(paquete_bib)
        params = [p.getId() for p in grafo.getProperties(SDPropertyCategory.Input) if not p.getId().startswith("$")]
        print("PARAMS", paquete_bib, grafo.getIdentifier(), params)
        g = fsd.Grafo(paquete, "x_" + paquete_bib)
        nodo = g.bib(paquete_bib)
        print("  ", fsd.describir_nodo(nodo))
        calcular(g, nodo, "x_" + paquete_bib)
    except BaseException as e:
        print("ERROR", paquete_bib, type(e).__mro__, e)
        traceback.print_exc()
