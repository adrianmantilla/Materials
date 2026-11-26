"""Prueba de Materials dentro de Maya, sin interfaz (herramienta de desarrollo).

Desde la terminal, con el mayapy de cada versión:

    /Applications/Autodesk/maya2027/Maya.app/Contents/bin/mayapy herramientas/prueba_maya.py
    "C:\\Program Files\\Autodesk\\Maya2027\\bin\\mayapy.exe" herramientas\\prueba_maya.py

No toca tus preferencias de Maya ni tus proyectos: trabaja en una carpeta temporal.
Comprueba: el plugin carga, crear materiales desde recetas (render y juego),
leerlos de vuelta, asignar a objetos y caras, conectar texturas de Painter,
Unreal y Unity (espacios de color, canales, normal DirectX, UDIM), recargar,
reparar rutas, copiar al proyecto, convertir un Standard Surface, la lista de
la escena, enviar a Painter (FBX + receta) y recibir su manifiesto.
Termina con «RESULTADO: OK» o con la lista de fallos.
"""

import json
import os
import shutil
import struct
import sys
import tempfile
import traceback
import zlib

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))

fallos = []


def comprobar(condicion, texto):
    print(("  ok    " if condicion else "  FALLO ") + texto, flush=True)
    if not condicion:
        fallos.append(texto)


def cerca(a, b, tolerancia=2e-3):
    return abs(a - b) <= tolerancia


def png(ruta, ancho=16, alto=16):
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xffffffff)
    filas = b"".join(b"\x00" + b"\x80\x60\x40" * ancho for _ in range(alto))
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)) +
                bloque(b"IDAT", zlib.compress(filas)) + bloque(b"IEND", b""))
    return ruta


def entrada_de(cmds, material, atributo):
    origen = cmds.listConnections("{}.{}".format(material, atributo), source=True, destination=False, plugs=True)
    return origen[0] if origen else None


def main():
    import maya.standalone
    maya.standalone.initialize(name="python")
    from maya import cmds

    print("Maya", cmds.about(version=True), "-", cmds.about(operatingSystem=True))
    temporal = tempfile.mkdtemp(prefix="materials_")
    os.environ["MATERIALS_CASA"] = os.path.join(temporal, "casa")
    try:
        _pruebas(cmds, temporal)
    except Exception:
        sys.stdout.flush()
        traceback.print_exc()
        fallos.append("excepción inesperada")
    finally:
        shutil.rmtree(temporal, ignore_errors=True)
    print()
    print("RESULTADO: OK" if not fallos else "RESULTADO: {} FALLOS\n - ".format(len(fallos)) + "\n - ".join(fallos))
    try:
        maya.standalone.uninitialize()
    except Exception:
        pass
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if not fallos else 1)


def _pruebas(cmds, temporal):
    cmds.loadPlugin(os.path.join(RAIZ, "plug-ins", "materials_plugin.py"))
    comprobar(cmds.pluginInfo("materials_plugin", query=True, loaded=True), "el plugin se carga")
    from materials import interfaz_maya
    interfaz_maya.iniciar()
    for nombre in interfaz_maya.COMANDOS:
        comprobar(cmds.runTimeCommand(nombre, exists=True), "existe la orden " + nombre)

    from materials import biblioteca as bib
    from materials import intercambio as ic
    from materials import receta as rc
    from materials.escena_maya import ServiciosMaya
    s = ServiciosMaya()
    comprobar(s.openpbr_disponible(), "existe el nodo openPBRSurface")
    if not s.openpbr_disponible():
        return

    proyecto = os.path.join(temporal, "proyecto")
    os.makedirs(os.path.join(proyecto, "sourceimages"))
    cmds.workspace(proyecto, openWorkspace=True)
    cmds.file(new=True, force=True)
    print("   espacio de render:", cmds.colorManagementPrefs(query=True, renderingSpaceName=True))

    # --- Atributos que existen de verdad --------------------------------------------------
    prueba = cmds.shadingNode("openPBRSurface", asShader=True, name="prueba_atributos")
    faltan = [a for a in rc.atributos_openpbr(rc.nueva()) if not cmds.attributeQuery(a, node=prueba, exists=True)]
    comprobar(not faltan, "todos los atributos de la receta existen en openPBRSurface ({})".format(faltan))
    cmds.delete(prueba)

    # --- Crear desde recetas -----------------------------------------------------------------
    b = bib.Biblioteca()
    oro = b.receta("Oro")
    vidrio = b.receta("Vidrio")
    cubo = cmds.polyCube(name="cubo")[0]
    esfera = cmds.polySphere(name="esfera")[0]
    cmds.select(cubo)
    m_oro = s.crear_material(oro, "render")
    comprobar(m_oro == "M_Oro", "nombre del material: " + m_oro)
    comprobar(cmds.nodeType(m_oro) == "openPBRSurface", "el material es openPBRSurface")
    comprobar(s.asignar(m_oro) == 1, "asignar a un objeto")
    comprobar(s.material_seleccionado() == m_oro, "cuentagotas encuentra el material del objeto")
    comprobar(cerca(cmds.getAttr(m_oro + ".baseMetalness"), 1.0), "metal = 1")
    comprobar(cerca(cmds.getAttr(m_oro + ".specularRoughness"), oro["rugosidad"]), "rugosidad de la receta")
    vuelta = s.leer_receta(m_oro)
    comprobar(vuelta["color"] == oro["color"], "el color vuelve igual ({} / {})".format(vuelta["color"], oro["color"]))
    comprobar(not rc.diferencias(oro, vuelta, tolerancia=0.01) or
              rc.diferencias(oro, vuelta, tolerancia=0.01) == ["familia"],
              "la receta leída coincide ({})".format(rc.diferencias(oro, vuelta, tolerancia=0.01)))
    # Juego: sin transmisión ni barniz.
    m_vidrio = s.crear_material(vidrio, "juego", nombre="Vidrio juego")
    comprobar(cmds.getAttr(m_vidrio + ".transmissionWeight") == 0, "juego: sin transmisión")
    comprobar(cmds.getAttr(m_vidrio + ".geometryOpacity") < 0.5, "juego: vidrio por opacidad")
    comprobar(cmds.getAttr(m_vidrio + ".materialsDestino") == "juego", "se guarda el destino")
    # Caras
    cmds.select(esfera + ".f[0:20]")
    m_caras = s.crear_material(rc.nueva(nombre="Caras", color="#33aa33"), "render")
    comprobar(s.asignar(m_caras) == 1, "asignar a caras")
    cmds.select(esfera + ".f[5]")
    comprobar(s.material_seleccionado() == m_caras, "cuentagotas en una cara")
    # Toda la biblioteca se puede crear sin errores
    errores = []
    for r in list(b.todas())[::7]:
        try:
            m = s.crear_material(r, "render")
            if s.actualizar_material(m, r, "juego"):
                errores.append(r["nombre"])
        except Exception as e:
            errores.append("{}: {}".format(r["nombre"], e))
    comprobar(not errores, "crear recetas de la biblioteca ({})".format(errores[:3]))

    # --- Texturas -------------------------------------------------------------------------------
    carpeta = os.path.join(proyecto, "sourceimages", "silla")
    for mapa in ("BaseColor", "Roughness", "Metallic", "Normal_OpenGL", "Height", "AO"):
        for udim in (1001, 1002):
            png(os.path.join(carpeta, "silla_Madera_{}.{}.png".format(mapa, udim)))
    from materials import texturas as tx
    analisis = tx.analizar(tx.listar_imagenes(carpeta))
    conexiones = [c.como_dict() for c in analisis["silla_madera"].conexiones.values()]
    m_madera = s.crear_material(b.receta("Roble"), "render", nombre="Madera")
    hechas = s.conectar_texturas(m_madera, conexiones)
    comprobar(set(hechas) == {"color", "rugosidad", "metal", "normal"}, "conectadas: {}".format(hechas))
    color = entrada_de(cmds, m_madera, "baseColor")
    comprobar(color and color.endswith(".outColor"), "color base conectado")
    nodo_color = color.split(".")[0]
    comprobar(cmds.getAttr(nodo_color + ".uvTilingMode") == 3, "UDIM activado")
    comprobar("<UDIM>" in cmds.getAttr(nodo_color + ".fileTextureName"), "ruta con <UDIM>")
    comprobar(not os.path.isabs(cmds.getAttr(nodo_color + ".fileTextureName")), "ruta relativa al proyecto")
    comprobar("srgb" in cmds.getAttr(nodo_color + ".colorSpace").lower(), "color en sRGB")
    rug = entrada_de(cmds, m_madera, "specularRoughness").split(".")[0]
    comprobar("raw" in cmds.getAttr(rug + ".colorSpace").lower() or "data" in cmds.getAttr(rug + ".colorSpace").lower(),
              "rugosidad en Raw ({})".format(cmds.getAttr(rug + ".colorSpace")))
    comprobar(cmds.getAttr(rug + ".alphaIsLuminance"), "rugosidad con alfa = luminancia")
    normal = entrada_de(cmds, m_madera, "normalCamera")
    comprobar(normal and cmds.nodeType(normal.split(".")[0]) == "bump2d" and
              cmds.getAttr(normal.split(".")[0] + ".bumpInterp") == 1, "normal por bump2d en espacio tangente")
    # Repetir no duplica nodos
    antes = len(cmds.ls(type="file"))
    s.conectar_texturas(m_madera, conexiones)
    comprobar(len(cmds.ls(type="file")) == antes, "conectar otra vez reutiliza los nodos")
    comprobar(s.recargar_texturas(m_madera) == 4, "recargar texturas")
    comprobar(len(s.texturas_de(m_madera)) == 4 and all(i["existe"] for i in s.texturas_de(m_madera).values()),
              "texturas_de las encuentra")
    # Selector «Relieve»: la altura como bump aunque haya normal, y vuelta a normales.
    hechas = s.conectar_texturas(m_madera, conexiones, {"relieve": "altura"})
    comprobar(set(hechas) == {"color", "rugosidad", "metal", "altura"}, "relieve altura: conectadas {}".format(hechas))
    bump = (entrada_de(cmds, m_madera, "normalCamera") or "").split(".")[0]
    comprobar(bump.endswith("_altura_bump") and cmds.getAttr(bump + ".bumpInterp") == 0,
              "relieve altura: bump con la altura ({})".format(bump))
    s.conectar_texturas(m_madera, conexiones, {"relieve": "normal"})
    bump = (entrada_de(cmds, m_madera, "normalCamera") or "").split(".")[0]
    comprobar(bump.endswith("_normal_bump"), "relieve normal: vuelve el mapa de normales ({})".format(bump))
    hechas = s.conectar_texturas(m_madera, conexiones, {"relieve": "desplazamiento"})
    grupos = cmds.listConnections(m_madera, type="shadingEngine") or []
    comprobar("altura" in hechas and "normal" in hechas and grupos and cmds.listConnections(
        grupos[0] + ".displacementShader"),
        "relieve desplazamiento: altura al desplazamiento y normal conectado")
    # Unreal: ORM + DirectX
    carpeta_u = os.path.join(proyecto, "sourceimages", "unreal")
    rutas_u = [png(os.path.join(carpeta_u, "Caja_{}.png".format(m))) for m in
               ("BaseColor", "OcclusionRoughnessMetallic", "Normal_DirectX")]
    m_caja = s.crear_material(rc.nueva(nombre="Caja"), "juego")
    con_u = [c.como_dict() for c in tx.analizar(rutas_u)["caja"].conexiones.values()]
    s.conectar_texturas(m_caja, con_u)
    comprobar((entrada_de(cmds, m_caja, "specularRoughness") or "").endswith(".outColorG"), "ORM: rugosidad en G")
    comprobar((entrada_de(cmds, m_caja, "baseMetalness") or "").endswith(".outColorB"), "ORM: metal en B")
    nodo_n = [i["nodo"] for e, i in s.texturas_de(m_caja).items() if e == "normal"][0]
    comprobar(cerca(cmds.getAttr(nodo_n + ".colorGain")[0][1], -1.0), "DirectX: verde invertido")
    # Unity: suavidad invertida
    carpeta_y = os.path.join(proyecto, "sourceimages", "unity")
    rutas_y = [png(os.path.join(carpeta_y, "Bote_{}.png".format(m))) for m in ("BaseMap", "MaskMap")]
    m_bote = s.crear_material(rc.nueva(nombre="Bote"), "juego")
    s.conectar_texturas(m_bote, [c.como_dict() for c in tx.analizar(rutas_y)["bote"].conexiones.values()])
    rug_y = entrada_de(cmds, m_bote, "specularRoughness") or ""
    comprobar(cmds.nodeType(rug_y.split(".")[0]) == "reverse", "Unity: suavidad invertida con reverse")
    met_y = entrada_de(cmds, m_bote, "baseMetalness") or ""
    comprobar(cmds.nodeType(met_y.split(".")[0]) == "condition", "Unity: metal dividido por el alfa (premultiplicado)")
    antes_y = len(cmds.ls(type="multiplyDivide"))
    s.conectar_texturas(m_bote, [c.como_dict() for c in tx.analizar(rutas_y)["bote"].conexiones.values()])
    comprobar(len(cmds.ls(type="multiplyDivide")) == antes_y, "Unity: reconectar no duplica la división")

    # --- Rutas ----------------------------------------------------------------------------------
    movida = os.path.join(proyecto, "sourceimages", "movidas")
    shutil.move(carpeta_u, movida)
    arregladas, perdidas = s.reparar_rutas()
    comprobar(len(arregladas) >= 3 and not perdidas, "reparar rutas ({} / {})".format(len(arregladas), perdidas))
    externa = png(os.path.join(temporal, "fuera", "Suelta_BaseColor.png"))
    m_suelta = s.crear_material(rc.nueva(nombre="Suelta"), "render")
    s.conectar_texturas(m_suelta, [c.como_dict() for c in tx.analizar([externa])["suelta"].conexiones.values()])
    comprobar(s.copiar_al_proyecto() >= 1, "copiar al proyecto")
    comprobar(os.path.isfile(os.path.join(proyecto, "sourceimages", "Suelta_BaseColor.png")), "la imagen está copiada")

    # --- Convertir y escena ---------------------------------------------------------------------
    estandar = cmds.shadingNode("standardSurface", asShader=True, name="viejo")
    cmds.setAttr(estandar + ".metalness", 1)
    cmds.setAttr(estandar + ".specularRoughness", 0.25)
    cmds.select(cmds.polyCylinder(name="cilindro")[0])
    grupo = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name="viejoSG")
    cmds.connectAttr(estandar + ".outColor", grupo + ".surfaceShader")
    cmds.sets("cilindro", edit=True, forceElement=grupo)
    nuevo = s.convertir(estandar, "render")
    comprobar(cmds.nodeType(nuevo) == "openPBRSurface" and cerca(cmds.getAttr(nuevo + ".baseMetalness"), 1),
              "convertir Standard Surface")
    comprobar(cmds.listConnections(grupo + ".surfaceShader")[0] == nuevo, "el convertido ocupa su lugar")
    lista = {m["nombre"]: m for m in s.materiales()}
    comprobar(lista[m_oro]["objetos"] == 1 and lista[m_oro]["materials"], "lista de escena: M_Oro")
    comprobar(lista["viejo"]["objetos"] == 0, "lista de escena: el viejo queda sin usar")
    nuevo_nombre = s.renombrar(m_caras, "Hierba")
    comprobar(nuevo_nombre == "M_Hierba" and cmds.objExists("M_HierbaSG"), "renombrar material y grupo")

    # --- Painter --------------------------------------------------------------------------------
    comprobar(s.materiales_compartidos(["|cubo", "|esfera"]) == [], "sin materiales compartidos")
    comprobar(s.tamano_objetos(m_oro) and s.tamano_objetos(m_oro) > 0.5, "tamaño de los objetos del material")
    cmds.select(cubo)
    carpeta_envio = s.enviar_a_painter(s.objetos_seleccionados(), "render", "arnold", 1024)
    fbx = os.path.join(carpeta_envio, "cubo.fbx")
    comprobar(os.path.isfile(fbx) and os.path.getsize(fbx) > 1000, "FBX exportado")
    receta_envio = ic.leer_json(os.path.join(carpeta_envio, "receta.json"))
    comprobar(receta_envio and list(receta_envio["juegos"]) == ["Oro"], "receta.json con el juego Oro")
    comprobar(len(ic.avisos_pendientes()) == 1, "aviso en el buzón")
    comprobar(cmds.objExists("cubo") and not cmds.ls("cubo_painter*") and not cmds.ls("Oro*", type="lambert"),
              "la escena queda limpia tras exportar")
    with open(fbx, "rb") as f:
        contenido = f.read()
    comprobar(b"Oro" in contenido, "el FBX lleva el material «Oro» (juego de texturas)")
    rutas_p = [png(os.path.join(carpeta_envio, "texturas", "Oro_{}.png".format(m)))
               for m in ("BaseColor", "Roughness", "Metallic", "Normal_OpenGL")]
    ic.escribir_manifiesto(carpeta_envio, {"Oro": rutas_p})
    resultado = s.aplicar_manifiesto(carpeta_envio)
    comprobar(resultado and resultado[0][0] == m_oro and len(resultado[0][1]) == 4,
              "manifiesto de Painter conectado a M_Oro ({})".format(resultado))
    cmds.select(cmds.polyPlane(name="sin_uvs")[0])
    cmds.polyMapDel("sin_uvs")
    try:
        s.enviar_a_painter(["|sin_uvs"], "render", "arnold", 1024)
        comprobar(False, "avisa de objeto sin UVs")
    except ValueError:
        comprobar(True, "avisa de objeto sin UVs")

    comprobar(s.borrar_sin_usar() >= 1 and not cmds.objExists("viejo"), "borrar sin usar")
    os.makedirs(os.path.join(proyecto, "scenes"), exist_ok=True)
    cmds.file(rename=os.path.join(proyecto, "scenes", "prueba.ma"))
    s.guardar_destino("juego", "unity")
    cmds.file(save=True, type="mayaAscii")
    cmds.file(new=True, force=True)
    cmds.file(os.path.join(proyecto, "scenes", "prueba.ma"), open=True, force=True)
    comprobar(s.destino_escena("render") == "juego" and s.motor_escena("unreal") == "unity",
              "la escena recuerda el destino")
    comprobar(json.loads(cmds.getAttr("M_Oro.materialsReceta"))["nombre"] == "Oro", "la receta se guarda en la escena")


if __name__ == "__main__":
    main()
