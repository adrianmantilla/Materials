"""Sonda del puente de Designer: versión, rutas, entradas de los nodos de biblioteca
que usará la fábrica y una prueba de punta a punta (grafo → PNG + .sbs).

Se ejecuta dentro de Designer a través de materials_puente. Solo escribe en
CARPETA/sonda.
"""

import os
import traceback

import sd
from sd.api.sdproperty import SDPropertyCategory

SALIDA = os.path.join(CARPETA, "sonda")  # noqa: F821  (lo pone el puente)
os.makedirs(SALIDA, exist_ok=True)

ctx = sd.getContext()
app = ctx.getSDApplication()
pm = app.getPackageMgr()

print("sd:", getattr(sd, "__version__", "?"))
try:
    from sd.api.sdapplication import SDApplicationPath
    for nombre in dir(SDApplicationPath):
        if not nombre.startswith("_"):
            try:
                print("ruta", nombre, app.getPath(getattr(SDApplicationPath, nombre)))
            except Exception as e:
                print("ruta", nombre, "->", e)
    RECURSOS = app.getPath(SDApplicationPath.DefaultResourcesDir)
except Exception:
    traceback.print_exc()
    RECURSOS = "/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/Resources"
PAQUETES = os.path.join(RECURSOS, "packages")
print("paquetes:", PAQUETES, os.path.isdir(PAQUETES))


def valor(v):
    try:
        x = v.get()
        for f in ("x", "y", "z", "w"):
            if not hasattr(x, f):
                break
        else:
            return (x.x, x.y, x.z, x.w)
        if hasattr(x, "x") and hasattr(x, "y"):
            return tuple(getattr(x, f) for f in ("x", "y", "z", "w") if hasattr(x, f))
        return x
    except Exception:
        return "?"


def describir(grafo):
    print("  GRAFO", grafo.getIdentifier(), "url:", grafo.getUrl())
    for cat, rotulo in ((SDPropertyCategory.Input, "in"), (SDPropertyCategory.Output, "out")):
        for p in grafo.getProperties(cat):
            if p.getId().startswith("$"):
                continue
            try:
                v = valor(grafo.getPropertyValue(p)) if rotulo == "in" else ""
            except Exception:
                v = "?"
            etiqueta = ""
            try:
                etiqueta = p.getLabel()
            except Exception:
                pass
            print("    {} {:<28} {:<22} {!r:<30} {}".format(rotulo, p.getId(), p.getType().getId(), v, etiqueta))


QUIERO = ["tile_generator", "tile_sampler", "tile_random", "brick_generator", "pattern_brick_generator",
          "flood_fill", "flood_fill_2", "bevel", "bevel_smooth", "height_blend", "shape", "edge_detect",
          "slope_blur", "slope_blur_grayscale", "non_uniform_blur", "noise_clouds_2", "noise_bnw_spots_1",
          "noise_grunge_map_001", "noise_perlin_noise", "noise_cells_1", "noise_directional_noise_1",
          "noise_fractal_sum_base", "histogram_scan", "histogram_range", "levels", "normal",
          "height_to_normal_world_units", "warp", "directional_warp", "make_it_tile_patch_grayscale",
          "dirt_gradient", "curvature_smooth", "ambient_occlusion_hbao", "pattern_weave_generator",
          "pattern_fibers_1", "noise_crystal_1", "noise_moisture_noise_v2", "noise_dirt_1"]
todos = sorted(os.listdir(PAQUETES)) if os.path.isdir(PAQUETES) else []
print("total .sbs:", sum(1 for f in todos if f.endswith(".sbs")))
with open(os.path.join(SALIDA, "paquetes.txt"), "w") as f:
    f.write("\n".join(todos))

cargados = {}
for nombre in QUIERO:
    ruta = os.path.join(PAQUETES, nombre + ".sbs")
    if not os.path.isfile(ruta):
        parecidos = [x for x in todos if nombre.split("_")[0] in x and nombre.split("_")[-1] in x][:6]
        print("FALTA", nombre, "parecidos:", parecidos)
        continue
    try:
        paquete = pm.getUserPackageFromFilePath(ruta) or pm.loadUserPackage(ruta)
        cargados[nombre] = paquete
        print("PAQUETE", nombre)
        for r in paquete.getChildrenResources(True):
            tipo = type(r).__name__
            if tipo == "SDSBSCompGraph":
                describir(r)
            else:
                print("  recurso", tipo, r.getIdentifier())
    except Exception:
        print("ERROR al cargar", nombre)
        traceback.print_exc()

# Prueba de punta a punta: tile_generator → salida; calcular, guardar PNG y .sbs.
try:
    from sd.api.sbs.sdsbscompgraph import SDSBSCompGraph
    paquete_tg = cargados["tile_generator"]
    tg = [r for r in paquete_tg.getChildrenResources(True) if type(r).__name__ == "SDSBSCompGraph"][0]
    nuevo = pm.newUserPackage()
    g = SDSBSCompGraph.sNew(nuevo)
    g.setIdentifier("sonda")
    nodo = g.newInstanceNode(tg)
    salidas = [p.getId() for p in nodo.getProperties(SDPropertyCategory.Output)]
    print("salidas del nodo:", salidas)
    out = g.newNode("sbs::compositing::output")
    print("entradas del nodo output:", [p.getId() for p in out.getProperties(SDPropertyCategory.Input)])
    nodo.newPropertyConnectionFromId(salidas[0], out, "inputNodeOutput")
    print("propiedades del grafo:", [p.getId() for p in g.getProperties(SDPropertyCategory.Input)])
    g.compute()
    pout = out.getProperties(SDPropertyCategory.Output)
    print("salidas del output:", [p.getId() for p in pout])
    textura = out.getPropertyValue(pout[0]).get()
    print("textura:", type(textura).__name__, textura.getSize() if hasattr(textura, "getSize") else "")
    textura.save(os.path.join(SALIDA, "sonda_tile.png"))
    pm.savePackageAs(nuevo, os.path.join(SALIDA, "sonda.sbs"))
    print("guardado sonda_tile.png y sonda.sbs")
except Exception:
    print("ERROR en la prueba de punta a punta")
    traceback.print_exc()
