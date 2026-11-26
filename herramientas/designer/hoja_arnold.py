"""Hoja de contacto con Arnold de las estructuras de un catálogo (para aprobar lotes).

    mayapy herramientas/designer/hoja_arnold.py <catalogo> <salida> [--solo id,id] [--res 360] [--encuadre 150]

Por cada estructura: una pared de 2 × 2 m con la receta típica de su familia, el motivo en
proyección caja a tamaño real, luz rasante de sol y cielo. Deja ``<salida>/<id>.png`` y,
si hay Pillow en el Python de Maya, nada más; la hoja la monta ``fabricar.py --hoja``.
"""

import argparse
import glob
import os
import shutil
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

# Receta de muestra por familia de estructura: (color, rugosidad, metal).
MUESTRA = {
    "Ladrillo y bloque": ("#a5502f", 0.75, 0.0),
    "Piedra": ("#c4b49a", 0.7, 0.0),
    "Pavimento": ("#77726c", 0.7, 0.0),
    "Baldosa y azulejo": ("#e8e4dc", 0.2, 0.0),
    "Madera": ("#8a5a35", 0.5, 0.0),
    "Cubierta": ("#a8583a", 0.7, 0.0),
}
COLORES_PIEZA = {"bloque_hormigon": "#8e8b85", "baldosa_30": "#b9a58c", "baldosa_60": "#d8d3ca",
                 "azulejo_metro": "#f2f0ea", "azulejo_15": "#5f8fa3", "hexagono_terracota": "#b5653d",
                 "hexagono_baldosa": "#dcd6cc", "pizarra_cubierta": "#4a4d52", "terrazo_baldosa": "#d8d2c6",
                 "baldosa_hidraulica": "#e6dfd0", "damero_marmol": "#ece9e3", "adoquin_hormigon": "#9a968f",
                 "baldosa_barro": "#b5653d", "cantos_rodados": "#a49d92"}
# Estructuras con «color 2» (zona2): el segundo color de la muestra.
COLOR2 = {"baldosa_hidraulica": "#2d4a6b", "damero_marmol": "#2a2a2a"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("catalogo")
    p.add_argument("salida")
    p.add_argument("--solo", default="")
    p.add_argument("--res", type=int, default=360)
    p.add_argument("--encuadre", type=float, default=150.0, help="cm de pared que llenan la imagen")
    a = p.parse_args()
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    from materials import motivos as mv
    from materials import receta as rc
    from materials.escena_maya import ServiciosMaya

    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "materials_plugin.py"), quiet=True)
    cmds.loadPlugin("mtoa", quiet=True)
    import mtoa.core
    temporal = tempfile.mkdtemp(prefix="hoja_arnold_")
    os.environ["MATERIALS_CASA"] = os.path.join(temporal, "casa")
    os.makedirs(a.salida, exist_ok=True)
    cat = mv.Catalogo(a.catalogo)
    solo = [x for x in a.solo.split(",") if x]
    s = ServiciosMaya()
    hechos = []
    for est in sorted(cat.estructuras(), key=lambda e: (e.familia, e.id)):
        if solo and est.id not in solo:
            continue
        cmds.file(new=True, force=True)
        proyecto = os.path.join(temporal, "proyecto")
        os.makedirs(os.path.join(proyecto, "images"), exist_ok=True)
        cmds.workspace(proyecto, openWorkspace=True)
        pared = cmds.polyPlane(name="pared", width=200, height=200, subdivisionsX=1, subdivisionsY=1)[0]
        cmds.setAttr(pared + ".rotateX", 90)
        cmds.select(pared)
        color, rug, metal = MUESTRA.get(est.familia, ("#9a9a9a", 0.6, 0.0))
        color = COLORES_PIEZA.get(est.id, color)
        receta = rc.nueva(nombre=est.nombre, color=color, rugosidad=rug, metal=metal)
        material = s.crear_material(receta, "render")
        s.asignar(material)
        motivo = {"activo": True, "estructura": est.id, "proyeccion": "caja", "desgaste": 0.2,
                  "variacion": 0.5, "relieve": 0.8, "azar": False}
        if est.id in COLOR2:
            motivo["color2"] = COLOR2[est.id]
        plan = mv.plan(motivo, cat, receta)
        s.aplicar_motivo(material, plan, receta, "render")
        camara, forma = cmds.camera(name="cam")
        # Encuadre: a.encuadre cm de pared llenan la imagen (36 mm de película horizontal).
        cmds.setAttr(camara + ".translateZ", a.encuadre * 50.0 / 36.0)
        cmds.setAttr(forma + ".focalLength", 50)
        # Sol rasante desde arriba a la izquierda, para que se lean juntas y biseles.
        sol = cmds.listRelatives(cmds.directionalLight(name="sol", intensity=4.5), parent=True)[0]
        cmds.setAttr(sol + ".rotateX", -55)
        cmds.setAttr(sol + ".rotateY", -50)
        cielo = cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
        cmds.setAttr(cielo + ".intensity", 0.6)
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
        mtoa.core.createOptions()
        cmds.setAttr("defaultArnoldDriver.ai_translator", "png", type="string")
        cmds.setAttr("defaultArnoldRenderOptions.AASamples", 4)
        cmds.setAttr("defaultResolution.width", a.res)
        cmds.setAttr("defaultResolution.height", a.res)
        cmds.setAttr("defaultResolution.deviceAspectRatio", 1.0)
        prefijo = os.path.join(temporal, est.id)
        cmds.setAttr("defaultArnoldDriver.prefix", prefijo, type="string")
        try:
            cmds.arnoldRender(width=a.res, height=a.res, camera=camara, batch=True)
        except Exception as e:
            print("ERROR render", est.id, e)
            continue
        hechas = sorted(glob.glob(prefijo + "*.png"))
        if hechas:
            shutil.copy(hechas[-1], os.path.join(a.salida, est.id + ".png"))
            hechos.append(est.id)
            print("render", est.id)
    print("HECHOS", len(hechos), " ".join(hechos))
    shutil.rmtree(temporal, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
