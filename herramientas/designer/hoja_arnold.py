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
    "Revestimiento": ("#9a968f", 0.7, 0.0),
}
COLORES_PIEZA = {"bloque_hormigon": "#8e8b85", "baldosa_30": "#b9a58c", "baldosa_60": "#d8d3ca",
                 "azulejo_metro": "#f2f0ea", "azulejo_15": "#5f8fa3", "hexagono_terracota": "#b5653d",
                 "hexagono_baldosa": "#dcd6cc", "pizarra_cubierta": "#62666d", "terrazo_baldosa": "#d8d2c6",
                 "baldosa_hidraulica": "#e6dfd0", "damero_marmol": "#ece9e3", "adoquin_hormigon": "#9a968f",
                 "baldosa_barro": "#b5653d", "cantos_rodados": "#a49d92",
                 "mosaico_gresite": "#3f8fa8", "mosaico_hexagonal": "#eeece7", "octogono_taco": "#e9e4da",
                 "adoquin_granito": "#8d8880", "muro_piedra_seca": "#a89c88", "teja_plana": "#a4502f",
                 "chapa_ondulada": "#b4b9be", "chapa_grecada": "#7f8a8f"}
# Rugosidad y metal propios (chapas).
RUG_METAL = {"chapa_ondulada": (0.35, 1.0), "chapa_grecada": (0.45, 0.6)}
# Estructuras con «color 2» (zona2): el segundo color de la muestra.
COLOR2 = {"baldosa_hidraulica": "#2d4a6b", "damero_marmol": "#2a2a2a", "octogono_taco": "#1e1e1e"}


def _aclarar(hex_color, minimo=0.42):
    """En la hoja, un acabado casi negro no deja ver nada: se aclara hasta un gris oscuro legible."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    m = max(rgb)
    if m >= minimo:
        return hex_color
    k = minimo / max(m, 1e-3)
    rgb = [min(1.0, c * k) if m > 0.02 else minimo for c in rgb]
    return "#" + "".join("{:02x}".format(int(round(c * 255))) for c in rgb)


def _exposicion(hex_color):
    """Factor de luz para la hoja de acabados: los blancos no se queman y los oscuros se leen."""
    h = hex_color.lstrip("#")
    r, g, b = [(int(h[i:i + 2], 16) / 255.0) ** 2.2 for i in (0, 2, 4)]
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return max(0.5, min(2.2, (0.32 / max(lum, 1e-3)) ** 0.5))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("catalogo")
    p.add_argument("salida")
    p.add_argument("--solo", default="")
    p.add_argument("--res", type=int, default=360)
    p.add_argument("--encuadre", type=float, default=150.0, help="cm de pared que llenan la imagen")
    p.add_argument("--relieve-x", type=float, default=1.0, help="multiplica relieveCm (pruebas de bump)")
    p.add_argument("--sufijo", default="", help="se añade al nombre del render")
    p.add_argument("--acabados", action="store_true", help="renderiza acabados (sin estructura)")
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
    lista = cat.acabados() if a.acabados else cat.estructuras()
    for est in sorted(lista, key=lambda e: (e.familia, e.id)):
        if solo and est.id not in solo:
            continue
        cmds.file(new=True, force=True)
        proyecto = os.path.join(temporal, "proyecto")
        os.makedirs(os.path.join(proyecto, "images"), exist_ok=True)
        cmds.workspace(proyecto, openWorkspace=True)
        # Un metal o un acabado brillante en una pared plana solo refleja el horizonte: en esfera
        # (con cielo) se leen sus reflejos y su relieve fino.
        es_metal = a.acabados and (float(est.datos.get("muestra_metal", 0.0)) > 0.5
                                   or float(est.datos.get("muestra_rug", 0.5)) < 0.35)
        if es_metal:
            pared = cmds.polySphere(name="pared", radius=a.encuadre * 0.45, subdivisionsX=96,
                                    subdivisionsY=64)[0]
        else:
            pared = cmds.polyPlane(name="pared", width=200, height=200, subdivisionsX=1, subdivisionsY=1)[0]
            cmds.setAttr(pared + ".rotateX", 90)
        cmds.select(pared)
        color, rug, metal = MUESTRA.get(est.familia, ("#9a9a9a", 0.6, 0.0))
        color = COLORES_PIEZA.get(est.id, color)
        rug, metal = RUG_METAL.get(est.id, (rug, metal))
        if a.acabados:
            color = _aclarar(est.datos.get("muestra", color))
            rug = float(est.datos.get("muestra_rug", 0.5))
            metal = float(est.datos.get("muestra_metal", 0.0))
        receta = rc.nueva(nombre=est.nombre, color=color, rugosidad=rug, metal=metal)
        material = s.crear_material(receta, "render")
        s.asignar(material)
        motivo = {"activo": True, "estructura": est.id, "proyeccion": "caja", "desgaste": 0.2,
                  "variacion": 0.5, "relieve": 0.8, "azar": False}
        if a.acabados:
            motivo.update(estructura="", acabado=est.id, relieve=1.0)
        if est.id in COLOR2:
            motivo["color2"] = COLOR2[est.id]
        plan = mv.plan(motivo, cat, receta)
        s.aplicar_motivo(material, plan, receta, "render")
        if a.relieve_x != 1.0:
            for ctrl in cmds.ls(type="network") or []:
                if cmds.attributeQuery("relieveCm", node=ctrl, exists=True):
                    cmds.setAttr(ctrl + ".relieveCm", cmds.getAttr(ctrl + ".relieveCm") * a.relieve_x)
        camara, forma = cmds.camera(name="cam")
        # Encuadre: a.encuadre cm de pared llenan la imagen (36 mm de película horizontal).
        encuadre = a.encuadre
        if a.acabados and not es_metal:
            # Un acabado se juzga de cerca: algo más de una repetición llena la imagen.
            encuadre = max(2.0, min(a.encuadre, 1.2 * est.tile_cm[0]))
        cmds.setAttr(camara + ".translateZ", encuadre * 50.0 / 36.0)
        cmds.setAttr(forma + ".focalLength", 50)
        # Sol rasante desde arriba a la izquierda, para que se lean juntas y biseles.
        sol = cmds.listRelatives(cmds.directionalLight(name="sol", intensity=4.5), parent=True)[0]
        cmds.setAttr(sol + ".rotateX", -70 if a.acabados and not es_metal else -55)  # más rasante: relieve fino
        cmds.setAttr(sol + ".rotateY", -50)
        cielo = cmds.shadingNode("aiSkyDomeLight", asLight=True, name="cielo")
        cmds.setAttr(cielo + ".intensity", 0.6)
        if a.acabados and not es_metal:
            # Luz rasante: el sol llega más débil a la pared; se compensa para que la hoja no salga oscura.
            k = _exposicion(color)
            cmds.setAttr(sol + ".intensity", 9.0 * k)
            cmds.setAttr(cielo + ".intensity", 1.0 * k)
        if es_metal:
            fisico = cmds.shadingNode("aiPhysicalSky", asTexture=True)
            cmds.setAttr(fisico + ".elevation", 35)
            cmds.connectAttr(fisico + ".outColor", cielo + ".color", force=True)
            cmds.setAttr(cielo + ".intensity", 4.0 * (_exposicion(color) if a.acabados else 1.0))
            if cmds.attributeQuery("enableSun", node=fisico, exists=True):
                cmds.setAttr(fisico + ".enableSun", False)  # el brillo ya lo da el sol direccional
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
            shutil.copy(hechas[-1], os.path.join(a.salida, est.id + a.sufijo + ".png"))
            hechos.append(est.id)
            print("render", est.id)
    print("HECHOS", len(hechos), " ".join(hechos))
    shutil.rmtree(temporal, ignore_errors=True)
    sys.stdout.flush()
    os._exit(0)


if __name__ == "__main__":
    main()
