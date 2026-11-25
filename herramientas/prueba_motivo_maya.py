"""Prueba de los motivos dentro de Maya, sin interfaz (herramienta de desarrollo).

    /Applications/Autodesk/maya2027/Maya.app/Contents/bin/mayapy herramientas/prueba_motivo_maya.py [carpeta_renders]

Si mayapy no tiene numpy y Pillow: ``python3 herramientas/generar_motivos_prueba.py /tmp/mot --res 256`` y
``MATERIALS_MOTIVOS_PRUEBA=/tmp/mot mayapy herramientas/prueba_motivo_maya.py``.

Genera los motivos de prueba en una carpeta temporal y comprueba: montar la red,
cambios en vivo desde el nodo de control, leer la receta con su motivo, proyecciones
caja / planar / cilíndrica / esférica / uv a tamaño real, triplanar, quitar el motivo
(vuelve lo que había), asignar a otro objeto (se proyecta solo) y deshacer.
Con Arnold (mtoa) además renderiza unas imágenes pequeñas y comprueba que la red se
evalúa en el render (nodo de control, uvChooser, aiTriplanar). Si se pasa
``carpeta_renders``, deja allí los PNG para mirarlos.
Termina con «RESULTADO: OK» o con la lista de fallos.
"""

import glob
import math
import os
import shutil
import sys
import tempfile
import traceback

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))

fallos = []
avisos = []


def comprobar(condicion, texto):
    print(("  ok    " if condicion else "  FALLO ") + texto, flush=True)
    if not condicion:
        fallos.append(texto)


def avisar(texto):
    print("  aviso " + texto, flush=True)
    avisos.append(texto)


def cerca(a, b, tolerancia=0.02):
    return abs(a - b) <= tolerancia


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds
    print("Maya", cmds.about(version=True), "-", cmds.about(operatingSystem=True))
    temporal = tempfile.mkdtemp(prefix="materials_motivo_")
    os.environ["MATERIALS_CASA"] = os.path.join(temporal, "casa")
    renders = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        _pruebas(cmds, temporal, renders)
    except Exception:
        sys.stdout.flush()
        traceback.print_exc()
        fallos.append("excepción inesperada")
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
    print()
    if avisos:
        print("AVISOS:\n - " + "\n - ".join(avisos))
    print("RESULTADO: OK" if not fallos else "RESULTADO: {} FALLOS\n - ".format(len(fallos)) + "\n - ".join(fallos))
    try:
        maya.standalone.uninitialize()
    except Exception:
        pass
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if not fallos else 1)


def rango_uv(cmds, caras, conjunto="tt_motivo"):
    forma = cmds.listRelatives(caras.split(".")[0], shapes=True, fullPath=True)[0]
    actual = cmds.polyUVSet(forma, query=True, currentUVSet=True)[0]
    cmds.polyUVSet(forma, currentUVSet=True, uvSet=conjunto)
    try:
        (u0, u1), (v0, v1) = cmds.polyEvaluate(caras, boundingBoxComponent2d=True)
    finally:
        cmds.polyUVSet(forma, currentUVSet=True, uvSet=actual)
    return u1 - u0, v1 - v0


def entrada(cmds, nodo, atributo):
    origen = cmds.listConnections("{}.{}".format(nodo, atributo), source=True, destination=False) or []
    return origen[0] if origen else None


def _pruebas(cmds, temporal, renders):
    from materials import motivo_maya as mm
    from materials import motivos as mv
    from materials import receta as rc
    from materials.escena_maya import ServiciosMaya

    # Los motivos de prueba necesitan numpy y Pillow; si mayapy no los tiene, se generan antes
    # con otro Python y se pasa la carpeta en MATERIALS_MOTIVOS_PRUEBA.
    carpeta = os.environ.get("MATERIALS_MOTIVOS_PRUEBA")
    if not carpeta:
        import generar_motivos_prueba as gen
        carpeta = os.path.join(temporal, "motivos")
        gen.generar(carpeta, 256)
    cat = mv.Catalogo(carpeta)
    comprobar(len(cat) == 6, "catálogo de prueba con 6 motivos")
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "materials_plugin.py"), quiet=True)
    arnold = False
    try:
        cmds.loadPlugin("mtoa", quiet=True)
        arnold = cmds.pluginInfo("mtoa", query=True, loaded=True)
    except RuntimeError:
        pass
    print("   Arnold:", "sí" if arnold else "no")
    s = ServiciosMaya()
    proyecto = os.path.join(temporal, "proyecto")
    os.makedirs(os.path.join(proyecto, "images"))
    cmds.workspace(proyecto, openWorkspace=True)
    cmds.file(new=True, force=True)
    cmds.undoInfo(state=True, infinity=True)
    print("   unidades:", cmds.currentUnit(query=True, linear=True))

    receta = rc.nueva(nombre="Muro de oro", color="#e5b85a", rugosidad=0.3, metal=1.0, familia="metales")
    muro = cmds.polyCube(name="muro", width=100, height=100, depth=100)[0]
    cmds.select(muro)
    material = s.crear_material(receta, "render")
    s.asignar(material)

    # Antes del motivo, una textura conectada al color: al quitar el motivo tiene que volver.
    archivo = cmds.shadingNode("file", asTexture=True, name="textura_previa")
    cmds.connectAttr(archivo + ".outColor", material + ".baseColor", force=True)

    # --- Montar ---------------------------------------------------------------------------
    motivo = {"activo": True, "estructura": "ladrillo_soga", "proyeccion": "caja"}
    plan = mv.plan(motivo, cat, receta)
    comprobar(plan["motivo"]["acabado"] == "cepillado", "acabado propuesto para oro: cepillado (sin restricción)")
    ctrl = s.aplicar_motivo(material, plan, receta, "render")
    comprobar(bool(ctrl) and cmds.objExists(ctrl), "existe el nodo de control")
    comprobar(mm.control_de(material) == ctrl, "el material encuentra su control")
    comprobar(cmds.nodeType(entrada(cmds, material, "baseColor")) == "blendColors", "baseColor viene de la red")
    comprobar(entrada(cmds, material, "normalCamera") is not None, "relieve conectado")
    comprobar(cerca(cmds.getAttr(ctrl + ".pieza"), 24.0), "pieza = 24 cm")
    places = mm.places_de(ctrl)
    comprobar(len(places) == 2, "dos place2dTexture (estructura y acabado)")
    pe = [p for p in places if "uvEstructura" in p][0]
    comprobar(cerca(cmds.getAttr(pe + ".repeatU"), 2.0) and cerca(cmds.getAttr(pe + ".repeatV"), 8.0),
              "repetición del ladrillo: 2 × 8 por metro ({:.3f}, {:.3f})".format(cmds.getAttr(pe + ".repeatU"),
                                                                                 cmds.getAttr(pe + ".repeatV")))
    forma = cmds.listRelatives(muro, shapes=True, fullPath=True)[0]
    comprobar("tt_motivo" in (cmds.polyUVSet(forma, query=True, allUVSets=True) or []), "conjunto de UV tt_motivo")
    comprobar(bool(mm.nodos_de(material, ["uvChooser"])), "uvChooser creado")
    for cara in range(6):
        du, dv = rango_uv(cmds, "{}.f[{}]".format(muro, cara))
        comprobar(cerca(du, 1.0) and cerca(dv, 1.0), "caja: cara {} de 1 m mide 1 UV ({:.3f} × {:.3f})".format(
            cara, du, dv))

    # --- En vivo ----------------------------------------------------------------------------
    cmds.setAttr(ctrl + ".pieza", 48.0)
    comprobar(cerca(cmds.getAttr(pe + ".repeatU"), 1.0), "pieza 48 cm desde el Channel Box: repetición 1")
    s.ajustar_motivo(material, dict(plan["motivo"], pieza_cm=85.0, desgaste=0.6, color_junta="#ff0000"))
    comprobar(cerca(cmds.getAttr(pe + ".repeatU"), 100.0 * 24.0 / 50.0 / 85.0), "pieza 85 cm desde la pestaña")
    leida = s.leer_receta(material)
    comprobar(leida.get("motivo", {}).get("estructura") == "ladrillo_soga", "leer_receta trae el motivo")
    comprobar(cerca(leida["motivo"]["pieza_cm"], 85.0) and cerca(leida["motivo"]["desgaste"], 0.6),
              "el motivo leído tiene los valores vivos")
    comprobar(leida["motivo"]["color_junta"] == "#ff0000", "color de junta leído")
    comprobar(leida["color"] == receta["color"], "el color de la receta se lee del control ({})".format(leida["color"]))
    s.actualizar_material(material, dict(receta, color="#3366aa", rugosidad=0.7), "render")
    comprobar(cerca(cmds.getAttr(ctrl + ".rugosidad"), 0.7), "la rugosidad de la receta va al control")
    comprobar(s.leer_receta(material)["color"] == "#3366aa", "el color nuevo va al control")
    comprobar(cmds.nodeType(entrada(cmds, material, "baseColor")) == "blendColors", "la red sigue conectada")

    # --- Otras proyecciones ------------------------------------------------------------------
    columna = cmds.polyCylinder(name="columna", radius=50, height=200, subdivisionsAxis=48)[0]
    cmds.select(columna)
    m_col = s.crear_material(receta, "render", nombre="Columna")
    s.asignar(m_col)
    plan_c = mv.plan({"activo": True, "estructura": "ladrillo_soga", "proyeccion": "cilindrica"}, cat, receta)
    s.aplicar_motivo(m_col, plan_c, receta, "render")
    lados = "{}.f[0:47]".format(columna)
    du, dv = rango_uv(cmds, lados)
    esperado = mv.vuelta_cerrada(2 * math.pi * 50.0 * math.cos(math.pi / 48), 50.0)
    comprobar(cerca(du, esperado, 0.1), "cilíndrica: la vuelta cierra con piezas enteras ({:.3f} / {:.3f})".format(
        du, esperado))
    comprobar(cerca(dv, 2.0, 0.05), "cilíndrica: 2 m de alto = 2 UV ({:.3f})".format(dv))

    suelo = cmds.polyPlane(name="suelo", width=200, height=200, subdivisionsX=2, subdivisionsY=2)[0]
    cmds.select(suelo)
    m_suelo = s.crear_material(receta, "render", nombre="Suelo")
    s.asignar(m_suelo)
    plan_p = mv.plan({"activo": True, "estructura": "baldosa_cuadrada", "proyeccion": "planar", "eje": "y"}, cat,
                     receta)
    s.aplicar_motivo(m_suelo, plan_p, receta, "render")
    du, dv = rango_uv(cmds, suelo + ".f[*]")
    comprobar(cerca(du, 2.0) and cerca(dv, 2.0), "planar: suelo de 2 m = 2 UV ({:.3f} × {:.3f})".format(du, dv))
    plan_uv = mv.plan(dict(plan_p["motivo"], proyeccion="uv"), cat, receta)
    s.aplicar_motivo(m_suelo, plan_uv, receta, "render")
    ctrl_s = mm.control_de(m_suelo)
    comprobar(ctrl_s is not None, "rehacer la red (planar → uv) conserva el control")
    if mm.RECREADOS:
        print("   info: Maya borró el control al rehacer la red y se ha vuelto a crear: {} al borrar {}".format(
            mm.RECREADOS, mm.RECREADOS_POR))
    pe_s = [p for p in mm.places_de(ctrl_s) if "uvEstructura" in p][0]
    # UV 0-1 sobre 2 m: una imagen de baldosa (60,8 cm) cabe 200 / 60,8 veces.
    comprobar(cerca(cmds.getAttr(pe_s + ".repeatU"), 200.0 / 60.8, 0.05),
              "uv: tamaño real por densidad de UV ({:.3f})".format(cmds.getAttr(pe_s + ".repeatU")))
    comprobar("tt_motivo" not in (cmds.polyUVSet(cmds.listRelatives(suelo, shapes=True, fullPath=True)[0],
                                                 query=True, allUVSets=True) or []),
              "uv: se borra el conjunto tt_motivo que ya no se usa")

    bola = cmds.polySphere(name="naranja", radius=4)[0]
    cmds.select(bola)
    naranja = rc.nueva(nombre="Naranja", color="#f08a1c", familia="comida")
    m_bola = s.crear_material(naranja, "render")
    s.asignar(m_bola)
    plan_e = mv.plan({"activo": True, "proyeccion": "esferica"}, cat, naranja)
    comprobar(plan_e["motivo"]["acabado"] == "piel_naranja", "naranja: acabado propuesto piel de naranja")
    s.aplicar_motivo(m_bola, plan_e, naranja, "render")
    du, dv = rango_uv(cmds, bola + ".f[*]")
    comprobar(du > 0.1, "esférica: escribe UV ({:.3f} × {:.3f})".format(du, dv))

    if arnold:
        plan_t = mv.plan({"activo": True, "estructura": "ladrillo_soga", "proyeccion": "triplanar"}, cat, receta)
        s.aplicar_motivo(m_col, plan_t, receta, "render")
        comprobar(len(mm.nodos_de(m_col, ["aiTriplanar"])) == 2, "triplanar: dos aiTriplanar (color y datos)")
        comprobar(not mm.nodos_de(m_col, ["polyCylProj", "polyPlanarProj"]), "triplanar: sin nodos de proyección")
        s.aplicar_motivo(m_col, plan_c, receta, "render")

    # --- Asignar a otro objeto: se proyecta solo ------------------------------------------------
    otro = cmds.polyCube(name="otro_muro", width=300, height=100, depth=20)[0]
    cmds.select(otro)
    s.asignar(material)
    du, dv = rango_uv(cmds, otro + ".f[0]")
    comprobar(cerca(du, 3.0) and cerca(dv, 1.0), "asignar a otro objeto lo proyecta ({:.3f} × {:.3f})".format(du, dv))

    # --- Quitar y deshacer -------------------------------------------------------------------------
    s.quitar_motivo(material, receta, "render")
    comprobar(mm.control_de(material) is None, "quitar: sin control")
    comprobar(not mm.nodos_de(material), "quitar: sin nodos del motivo")
    comprobar(entrada(cmds, material, "baseColor") == archivo, "quitar: vuelve la textura que había")
    comprobar("tt_motivo" not in (cmds.polyUVSet(forma, query=True, allUVSets=True) or []),
              "quitar: se borra tt_motivo")
    cmds.undo()
    comprobar(mm.control_de(material) is not None, "deshacer devuelve el motivo")
    cmds.redo()
    comprobar(mm.control_de(material) is None, "rehacer lo vuelve a quitar")

    n = s.borrar_sin_usar()
    comprobar(n == 0, "borrar sin usar no toca materiales usados")

    if arnold:
        _render(cmds, s, mv, cat, receta, temporal, renders)


def _pixeles(ruta):
    """Canal rojo de un PNG de 8 bits (RGB o RGBA), sin Pillow: (valores, ancho, alto)."""
    import struct
    import zlib
    with open(ruta, "rb") as f:
        datos = f.read()
    pos, idat, ancho, alto, canales = 8, b"", 0, 0, 4
    while pos < len(datos):
        largo, tipo = struct.unpack(">I4s", datos[pos:pos + 8])
        cuerpo = datos[pos + 8:pos + 8 + largo]
        if tipo == b"IHDR":
            ancho, alto, bits, color = struct.unpack(">IIBB", cuerpo[:10])
            if bits != 8:
                raise ValueError("PNG de {} bits".format(bits))
            canales = {0: 1, 2: 3, 4: 2, 6: 4}[color]
        elif tipo == b"IDAT":
            idat += cuerpo
        pos += 12 + largo
    crudo = zlib.decompress(idat)
    fila = ancho * canales
    anterior = bytearray(fila)
    rojos = []
    for y in range(alto):
        filtro = crudo[y * (fila + 1)]
        linea = bytearray(crudo[y * (fila + 1) + 1:(y + 1) * (fila + 1)])
        for x in range(fila):
            a = linea[x - canales] if x >= canales else 0
            b = anterior[x]
            c = anterior[x - canales] if x >= canales else 0
            if filtro == 1:
                linea[x] = (linea[x] + a) & 255
            elif filtro == 2:
                linea[x] = (linea[x] + b) & 255
            elif filtro == 3:
                linea[x] = (linea[x] + (a + b) // 2) & 255
            elif filtro == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                linea[x] = (linea[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        rojos.extend(linea[0::canales])
        anterior = linea
    return rojos, ancho, alto


def _desviacion(valores):
    media = sum(valores) / float(len(valores))
    return math.sqrt(sum((v - media) ** 2 for v in valores) / len(valores)), media


def _render(cmds, s, mv, cat, receta, temporal, renders):
    """Render pequeño con Arnold: la red tiene que verse (no un color plano)."""
    from materials import receta as rc
    cmds.file(new=True, force=True)
    plano = cmds.polyPlane(name="pared", width=200, height=200, subdivisionsX=1, subdivisionsY=1)[0]
    cmds.setAttr(plano + ".rotateX", 90)
    # UV de map1 aplastadas: si Arnold no leyera tt_motivo, la pared saldría lisa.
    cmds.polyEditUV(plano + ".map[*]", scaleU=0.0, scaleV=0.0, pivotU=0.5, pivotV=0.5)
    cmds.select(plano)
    receta = rc.nueva(nombre="Pared", color="#b04a2c", rugosidad=0.6)
    material = s.crear_material(receta, "render")
    s.asignar(material)
    camara, camara_forma = cmds.camera(name="cam_prueba")
    cmds.setAttr(camara + ".translateZ", 600)
    cmds.setAttr(camara_forma + ".focalLength", 35)
    luz = cmds.directionalLight(name="sol")
    sol = cmds.listRelatives(luz, parent=True)[0]
    cmds.setAttr(sol + ".rotateX", -15)
    cmds.setAttr(sol + ".rotateY", 20)
    cmds.setAttr(luz + ".intensity", 3.0)
    cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")
    try:
        import mtoa.core
        mtoa.core.createOptions()   # en mayapy defaultArnoldDriver no existe hasta aquí
    except Exception as error:
        avisar("no se pudieron crear las opciones de Arnold: {}".format(error))
    cmds.setAttr("defaultArnoldDriver.ai_translator", "png", type="string")
    cmds.setAttr("defaultArnoldRenderOptions.AASamples", 2)
    cmds.setAttr("defaultResolution.width", 240)
    cmds.setAttr("defaultResolution.height", 240)
    cmds.setAttr("defaultResolution.deviceAspectRatio", 1.0)
    salida = renders or os.path.join(temporal, "renders")
    os.makedirs(salida, exist_ok=True)

    def render(nombre):
        prefijo = os.path.join(salida, nombre)
        for viejo in glob.glob(prefijo + "*.png"):
            os.remove(viejo)
        cmds.setAttr("defaultArnoldDriver.prefix", prefijo, type="string")
        cmds.arnoldRender(width=160, height=160, camera=camara, batch=True)
        hechos = sorted(glob.glob(prefijo + "*.png"))
        return hechos[-1] if hechos else None

    plan = mv.plan({"activo": True, "estructura": "ladrillo_soga", "proyeccion": "caja", "desgaste": 0.0}, cat, receta)
    s.aplicar_motivo(material, plan, receta, "render")
    rutas = {}
    rutas["caja_24cm"] = render("motivo_caja_24cm")
    ctrl = mm_control(s, material)
    junta = cmds.getAttr(ctrl + ".colorJunta")[0]
    cmds.setAttr(ctrl + ".colorJunta", 1, 1, 1, type="double3")
    rutas["junta_blanca"] = render("motivo_junta_blanca")
    cmds.setAttr(ctrl + ".colorJunta", *junta, type="double3")
    cmds.setAttr(ctrl + ".pieza", 96.0)
    rutas["caja_96cm"] = render("motivo_caja_96cm")
    plan_t = mv.plan(dict(plan["motivo"], proyeccion="triplanar"), cat, receta)
    s.aplicar_motivo(material, plan_t, receta, "render")
    rutas["triplanar_24cm"] = render("motivo_triplanar_24cm")
    s.quitar_motivo(material, receta, "render")
    rutas["sin_motivo"] = render("motivo_sin_motivo")
    if not all(rutas.values()):
        avisar("Arnold no ha dejado imágenes ({}); revisa el render a mano".format(rutas))
        return
    pix = {}
    for nombre, ruta in rutas.items():
        pix[nombre] = _pixeles(ruta)[0]
        desviacion, media = _desviacion(pix[nombre])
        print("   render {}: desviación {:.1f}, media {:.1f}  ({})".format(nombre, desviacion, media, ruta))

    def distintos(a, b):
        return sum(1 for x, y in zip(pix[a], pix[b]) if abs(x - y) > 2) / float(len(pix[a]))

    comprobar(distintos("caja_24cm", "sin_motivo") > 0.02,
              "render caja: el motivo se ve (Arnold lee tt_motivo) ({:.0%})".format(distintos("caja_24cm", "sin_motivo")))
    comprobar(distintos("triplanar_24cm", "sin_motivo") > 0.02,
              "render triplanar: el motivo se ve ({:.0%})".format(distintos("triplanar_24cm", "sin_motivo")))
    comprobar(distintos("caja_24cm", "caja_96cm") > 0.02,
              "render: cambiar la pieza en el control cambia el render ({:.0%})".format(
                  distintos("caja_24cm", "caja_96cm")))
    comprobar(distintos("caja_24cm", "junta_blanca") > 0.02,
              "render: la junta blanca cambia el render (la máscara llega a Arnold) ({:.0%})".format(
                  distintos("caja_24cm", "junta_blanca")))
    if renders:
        print("   imágenes en", salida)


def mm_control(s, material):
    from materials import motivo_maya as mm
    return mm.control_de(material)


if __name__ == "__main__":
    main()
