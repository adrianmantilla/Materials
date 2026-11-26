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
                 "chapa_ondulada": "#b4b9be", "chapa_grecada": "#7f8a8f",
                 "azulejo_metro_vertical": "#f2f0ea", "azulejo_espiga": "#2f5f6f", "azulejo_10": "#e6c64a",
                 "baldosa_gran_formato": "#cfcac2", "baldosa_diagonal": "#c9b89c", "opus_romano": "#d6c4a4",
                 "losas_rectangulares": "#5f6166", "adoquin_espiga": "#8f8a82", "adoquin_madera": "#7a5a3c",
                 "tarima_exterior": "#8a6a48", "bloque_split": "#9a968f", "bloque_vidrio": "#b8ccd0",
                 "parquet_espiga_doble": "#a87a4e", "parquet_bastones": "#c29a68", "tablas_diagonal": "#7d5a3c",
                 "hexagono_alargado": "#5d7f73", "mosaico_penny": "#e9e4da", "zellige": "#2f6f6a",
                 "azulejo_biselado": "#efeee8", "trencadis": "#3f74a8", "mosaico_teselas": "#c9a24a",
                 "adoquin_cesta": "#8f5f45", "adoquin_hexagonal": "#7c7a75", "losa_hormigon": "#a19d96",
                 "panel_composite": "#4a4e53", "panel_ranurado": "#b08a60", "cubos_3d": "#d9d4c8",
                 "rombos": "#b65a3c", "azulejo_escama": "#4f8f9a",
                 "ladrillo_holandes": "#9a4e36", "ladrillo_americano": "#a35a40", "ladrillo_monje": "#8e4a34",
                 "celosia_ladrillo": "#b0603e", "bloque_apilado": "#8e8b85", "opus_modular": "#d8c8aa",
                 "baldosa_tercios": "#bdb8ae", "tablas_irregulares": "#9a7450", "ripias": "#8a7258",
                 "sillar_almohadillado": "#c8b48e", "listones_horizontales": "#a87e56", "loseta_caucho": "#5e6064",
                 "losas_jardin": "#b8b4aa",
                 "mosaico_listelo": "#5f8f88", "mosaico_listelo_espiga": "#e8e4dc", "espiga_ancha": "#a07a52",
                 "punta_hungria_ancha": "#b08a60", "pizarra_rombo": "#4a4e52", "damero_ceramico": "#ecebe6",
                 "azulejo_20": "#d8d2c4", "azulejo_vertical_apilado": "#7a9a8a", "ladrillo_tercios": "#9a5038",
                 "losas_soga": "#cfc6b4", "bloque_termoarcilla": "#b8704e", "baldosa_rustica": "#b8704a",
                 "lajas_apiladas": "#6a6660", "opus_incertum": "#bfb39c", "hexagono_grande": "#c8c4bc",
                 "estrella_cruz": "#e6e2d8", "triangulos": "#c8a070", "baldosa_ondulada": "#5a8ab0",
                 "arlequin": "#d8d0c0", "parquet_cesta_diagonal": "#a87e56", "ladrillo_espiga_doble": "#9a4e36",
                 "adoquin_espiga_recta": "#8e8a84", "adoquin_cesped": "#a8a49c", "listones_diagonales": "#a07a52",
                 "teja_mixta": "#b0603e", "panel_sandwich": "#c8ccd0", "parquet_hexagonal": "#a87e56",
                 "molinete": "#c9b89c", "porcelanico_madera": "#9c7650", "cubierta_barco": "#b08a5e",
                 "azulejo_ondas_3d": "#e8e6e0", "azulejo_abombado": "#3e7a6a", "pasaderas": "#a8a49c",
                 "traviesas": "#6e5640", "ladrillo_vidriado": "#2e6a8e", "bloque_split_apilado": "#9a958c",
                 "adoquin_irregular": "#8a8680", "ladrillo_vertical_trabado": "#9a5038", "baldosa_120": "#bdb8b0",
                 "mosaico_rombo": "#5a8ab0", "mosaico_triangulos": "#c8b090", "mosaico_estrella_cruz": "#e6e2d8",
                 "adoquin_ondulado": "#9a958e", "pizarra_hexagonal": "#4a4d52", "baldosa_con_listelo": "#d8d0c0",
                 "azulejo_diagonal_15": "#d8d2c4", "ladrillo_cesta": "#9a4e36", "parquet_trabado": "#a87e56",
                 "tatami": "#b8b080", "azulejo_metro_apilado": "#e8e6e0", "baldosa_60x30_apilada": "#9a958e",
                 "hexagono_cesped": "#b0aca4", "losas_cesped": "#b0aca4", "baldosa_triangular": "#c8a070",
                 "mosaico_damero": "#e6e2d8", "tejuela_madera": "#8a6a4a", "ladrillo_soldado": "#9a5038",
                 "sillar_apilado": "#c8bca4", "baldosa_trabada": "#cfc6b4", "hexagono_triangulo": "#e6e2d8",
                 "baldosa_rayuela": "#c8a888", "losas_rayuela": "#b8ae9c", "parquet_escalonado": "#a87e56",
                 "parquet_ladrillo_doble": "#9c7650", "troncos_cabana": "#8a6440", "bambu": "#c8b078",
                 "panel_listones_acustico": "#b08a5e", "mosaico_molinete": "#e6e2d8", "mosaico_dedos": "#6a9a8a",
                 "azulejo_diamante": "#e8e6e0", "punta_diamante": "#c8bca4", "bloque_celosia": "#c8c4bc",
                 "damero_piedra": "#d8d0bc", "baldosa_rombo_hexagonal": "#b8704a"}
# Rugosidad y metal propios (chapas).
RUG_METAL = {"chapa_ondulada": (0.35, 1.0), "chapa_grecada": (0.45, 0.6), "bloque_vidrio": (0.05, 0.0), "panel_composite": (0.3, 0.0)}
# Estructuras con «color 2» (zona2): el segundo color de la muestra.
COLOR2 = {"baldosa_hidraulica": "#2d4a6b", "damero_marmol": "#2a2a2a", "octogono_taco": "#1e1e1e", "cubos_3d": "#3a3a3a", "damero_ceramico": "#1e1e1e", "estrella_cruz": "#2f5f8f", "arlequin": "#3a3a3a", "mosaico_estrella_cruz": "#2f5f8f",
          "mosaico_damero": "#1e1e1e", "hexagono_triangulo": "#2f5f8f", "baldosa_rayuela": "#5a3a2a",
          "mosaico_molinete": "#2a2a2a", "damero_piedra": "#3a3c40"}


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
