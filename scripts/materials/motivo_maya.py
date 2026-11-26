"""Red de nodos de un motivo en Maya: nodo de control, texturas, mezcla y proyección.

Todo cuelga de un nodo de control (``network``) con atributos legibles (Pieza en cm,
Rotación, Desgaste, Color de junta...). Los nodos de la red están conectados a esos
atributos, así que cambiar un valor en la pestaña Motivo o en el Channel Box se ve
al momento, sin abrir el Hypershade.

Cadena de color (con estructura y acabado)::

    color pieza ─┬─ blendColors(color 2, máscara A)
                 ├─ × (1 + 2·(G − 0,5)·variación)        tono distinto por pieza
                 ├─ × mezcla(1, tono × 2, variación/0,3)  matiz por pieza (si hay mapa tono)
                 ├─ × color del acabado × 2               el acabado gira alrededor de 0,5
                 ├─ blendColors(color junta, máscara R)
                 └─ blendColors(color desgaste, remap(B)) desgaste
                    → baseColor

Rugosidad = base + (acabado − 0,5), junta y desgaste encima; metal = base fuera de juntas
y desgaste; altura = estructura + peso · acabado (cada una con sus cm reales) → un solo bump2d.

Proyecciones: ``uv`` usa las UV del objeto con su densidad real; ``caja``, ``planar``,
``cilindrica`` y ``esferica`` escriben un conjunto de UV aparte (``tt_motivo``) con nodos
de proyección de Maya (respetan el historial y se deshacen con Ctrl+Z) y un ``uvChooser``;
``triplanar`` envuelve la red en ``aiTriplanar`` (solo Arnold).
"""

import json
import math

from maya import cmds

from materials import color as col
from materials import motivos as mv

ATTR = "materialsMotivo"            # en cada nodo de la red: el material al que pertenece
ATTR_DATOS = "materialsMotivoDatos"  # en el control: el motivo en JSON
ATTR_ANTES = "materialsMotivoAntes"
ATTR_CONTROL = "materialsMotivoControl"  # en el material: conexión desde el control  # en el control: lo que estaba conectado antes
SALIDAS = ("baseColor", "specularRoughness", "baseMetalness", "normalCamera")
VARIACION_DEFECTO = mv.DEFECTO["variacion"]  # con este valor el mapa tono se ve tal cual
TIPOS_PROYECCION = ("polyPlanarProj", "polyCylProj", "polySphProj")
# aiTriplanar: escala para que una unidad de textura mida un metro (se comprueba en el Mac).
TRIPLANAR_ESCALA = 0.01
CM_POR_UNIDAD = {"mm": 0.1, "millimeter": 0.1, "cm": 1.0, "centimeter": 1.0, "m": 100.0, "meter": 100.0,
                 "km": 100000.0, "kilometer": 100000.0, "in": 2.54, "inch": 2.54, "ft": 30.48, "foot": 30.48,
                 "yd": 91.44, "yard": 91.44}

# atributo del control -> (clave del motivo, tipo, mínimo, máximo, nombre visible)
NUMEROS = (
    ("pieza", "pieza_cm", 0.01, None, "Pieza (cm)"),
    ("repeticion", "repeticion_cm", 0.01, None, "Repeticion acabado (cm)"),
    ("mezcla", "mezcla", 0.0, 1.0, "Mezcla triplanar"),
    ("variacion", "variacion", 0.0, 1.0, "Variacion por pieza"),
    ("relieve", "relieve", 0.0, 1.0, "Relieve"),
    ("desgaste", "desgaste", 0.0, 1.0, "Desgaste"),
    ("rugosidadDesgaste", "rugosidad_desgaste", 0.0, 1.0, "Rugosidad del desgaste"),
    ("rugosidadJunta", "rugosidad_junta", 0.0, 1.0, "Rugosidad de la junta"),
)
COLORES = (("color2", "color2", "Color 2"), ("colorJunta", "color_junta", "Color de junta"),
           ("colorDesgaste", "color_desgaste", "Color del desgaste"))
OCULTOS = ("kU", "kV", "aU", "aV", "relieveCm", "alturaAcabado")
RECREADOS = []   # controles que Maya borró al rehacer la red (para la prueba en Maya)
RECREADOS_POR = []


def _unir(origen, destino):
    if not cmds.isConnected(origen, destino):
        cmds.connectAttr(origen, destino, force=True)


def _hay(nodo, atributo):
    try:
        return cmds.attributeQuery(atributo, node=nodo, exists=True)
    except RuntimeError:
        return False


def _nombre(material, sufijo):
    return "{}_tt_{}".format(material, sufijo)


def cm_por_unidad():
    return CM_POR_UNIDAD.get(cmds.currentUnit(query=True, linear=True), 1.0)


def _marcar(nodo, material):
    if not _hay(nodo, ATTR):
        cmds.addAttr(nodo, longName=ATTR, dataType="string")
    cmds.setAttr(nodo + "." + ATTR, material, type="string")
    return nodo


def _nodo(tipo, material, sufijo, utilidad=True):
    if utilidad:
        nodo = cmds.shadingNode(tipo, asUtility=True, name=_nombre(material, sufijo))
    else:
        nodo = cmds.shadingNode(tipo, asTexture=True, name=_nombre(material, sufijo))
    return _marcar(nodo, material)


def nodos_de(material, tipos=None):
    """Nodos de la red del motivo de ``material`` (sin el control)."""
    salida = []
    for nodo in cmds.ls("*." + ATTR, objectsOnly=True) or []:
        if nodo == control_de(material):
            continue
        try:
            if cmds.getAttr(nodo + "." + ATTR) != material:
                continue
        except (RuntimeError, ValueError):
            continue
        if tipos and cmds.nodeType(nodo) not in tipos:
            continue
        salida.append(nodo)
    return salida


def control_de(material):
    """Nodo de control del motivo del material, o None."""
    if not material or not cmds.objExists(material):
        return None
    candidatos = []
    if _hay(material, ATTR_CONTROL):
        candidatos += cmds.listConnections(material + "." + ATTR_CONTROL, source=True, destination=False) or []
    candidatos += cmds.listConnections(material + ".message", destination=True, source=False) or []
    for nodo in candidatos:
        if cmds.nodeType(nodo) == "network" and _hay(nodo, ATTR_DATOS):
            return nodo
    return None


# --- Nodo de control ----------------------------------------------------------------------------


def _crear_control(material):
    ctrl = cmds.createNode("network", name=_nombre(material, "control"), skipSelect=True)
    _marcar(ctrl, material)
    # El control apunta al material (y no al revés): así siempre tiene una conexión de salida y
    # Maya no lo borra solo cuando se borra la red que colgaba de él.
    if not _hay(material, ATTR_CONTROL):
        cmds.addAttr(material, longName=ATTR_CONTROL, attributeType="message")
    _unir(ctrl + ".message", material + "." + ATTR_CONTROL)
    for nombre in (ATTR_DATOS, ATTR_ANTES, "estructura", "acabado"):
        cmds.addAttr(ctrl, longName=nombre, dataType="string")
    cmds.addAttr(ctrl, longName="proyeccion", attributeType="enum", enumName=":".join(mv.PROYECCIONES))
    cmds.addAttr(ctrl, longName="espacio", attributeType="enum", enumName=":".join(mv.ESPACIOS))
    cmds.addAttr(ctrl, longName="eje", attributeType="enum", enumName=":".join(mv.EJES))
    cmds.addAttr(ctrl, longName="azar", attributeType="bool")
    for atributo, _clave, minimo, maximo, visible in NUMEROS:
        banderas = {"minValue": minimo} if minimo is not None else {}
        if maximo is not None:
            banderas["maxValue"] = maximo
        cmds.addAttr(ctrl, longName=atributo, niceName=visible, attributeType="double", keyable=True, **banderas)
    cmds.addAttr(ctrl, longName="rotacion", niceName="Rotacion", attributeType="doubleAngle", keyable=True)
    cmds.addAttr(ctrl, longName="rugosidad", niceName="Rugosidad base", attributeType="double",
                 minValue=0, maxValue=1, keyable=True)
    cmds.addAttr(ctrl, longName="metal", niceName="Metal base", attributeType="double",
                 minValue=0, maxValue=1, keyable=True)
    for atributo, _clave, visible in (("colorPieza", None, "Color de pieza"),) + COLORES:
        cmds.addAttr(ctrl, longName=atributo, niceName=visible, attributeType="float3", usedAsColor=True)
        for canal in "RGB":
            cmds.addAttr(ctrl, longName=atributo + canal, attributeType="float", parent=atributo)
    for atributo in OCULTOS:
        cmds.addAttr(ctrl, longName=atributo, attributeType="double", hidden=True)
    cmds.setAttr(ctrl + ".alturaAcabado", mv.ALTURA_ACABADO)
    return ctrl


def _poner_color(ctrl, atributo, hex_o_rgb, espacio):
    rgb = col.hex_a_lineal(hex_o_rgb) if isinstance(hex_o_rgb, str) else tuple(hex_o_rgb)
    cmds.setAttr("{}.{}".format(ctrl, atributo), *col.a_espacio_render(rgb, espacio), type="float3")


def _leer_color(ctrl, atributo, espacio):
    valor = cmds.getAttr("{}.{}".format(ctrl, atributo))[0]
    return col.lineal_a_hex(col.desde_espacio_render(valor, espacio))


def poner_valores(ctrl, motivo, espacio):
    """Escribe en el control lo que se puede cambiar en vivo."""
    m = mv.normalizar(motivo)
    for atributo, clave, _a, _b, _c in NUMEROS:
        if m[clave] > 0 or clave not in ("pieza_cm", "repeticion_cm"):
            cmds.setAttr("{}.{}".format(ctrl, atributo), m[clave])
    cmds.setAttr(ctrl + ".rotacion", m["rotacion"])   # en grados (unidad de ángulo de la escena)
    for atributo, clave, _v in COLORES:
        if m[clave]:
            _poner_color(ctrl, atributo, m[clave], espacio)
    cmds.setAttr(ctrl + ".proyeccion", mv.PROYECCIONES.index(m["proyeccion"]))
    cmds.setAttr(ctrl + ".espacio", mv.ESPACIOS.index(m["espacio"]))
    cmds.setAttr(ctrl + ".eje", mv.EJES.index(m["eje"]))
    cmds.setAttr(ctrl + ".azar", m["azar"])
    cmds.setAttr(ctrl + ".estructura", m["estructura"], type="string")
    cmds.setAttr(ctrl + ".acabado", m["acabado"], type="string")
    cmds.setAttr(ctrl + "." + ATTR_DATOS, json.dumps(m, ensure_ascii=False), type="string")


def poner_base(ctrl, color_lineal, rugosidad, metal, espacio):
    """Color, rugosidad y metal de la receta (los que manda la pestaña Material)."""
    _poner_color(ctrl, "colorPieza", color_lineal, espacio)
    cmds.setAttr(ctrl + ".rugosidad", rugosidad)
    cmds.setAttr(ctrl + ".metal", metal)


def leer(material, espacio):
    """Motivo del material con los valores vivos del control (o None si no tiene)."""
    ctrl = control_de(material)
    if not ctrl:
        return None
    try:
        m = json.loads(cmds.getAttr(ctrl + "." + ATTR_DATOS) or "{}")
    except ValueError:
        m = {}
    for atributo, clave, _a, _b, _c in NUMEROS:
        m[clave] = cmds.getAttr("{}.{}".format(ctrl, atributo))
    m["rotacion"] = cmds.getAttr(ctrl + ".rotacion")
    for atributo, clave, _v in COLORES:
        m[clave] = _leer_color(ctrl, atributo, espacio)
    m["proyeccion"] = mv.PROYECCIONES[cmds.getAttr(ctrl + ".proyeccion")]
    m["espacio"] = mv.ESPACIOS[cmds.getAttr(ctrl + ".espacio")]
    m["eje"] = mv.EJES[cmds.getAttr(ctrl + ".eje")]
    m["azar"] = bool(cmds.getAttr(ctrl + ".azar"))
    m["estructura"] = cmds.getAttr(ctrl + ".estructura") or ""
    m["acabado"] = cmds.getAttr(ctrl + ".acabado") or ""
    m["activo"] = True
    return mv.normalizar(m)


def leer_base(material, espacio):
    """(color hex, rugosidad, metal) de la receta guardados en el control."""
    ctrl = control_de(material)
    if not ctrl:
        return None
    return (_leer_color(ctrl, "colorPieza", espacio), cmds.getAttr(ctrl + ".rugosidad"),
            cmds.getAttr(ctrl + ".metal"))


# --- Red de nodos ---------------------------------------------------------------------------------


def _place(material, sufijo, ctrl, rep_u, rep_v):
    p = _nodo("place2dTexture", material, sufijo)
    md = _nodo("multiplyDivide", material, sufijo + "_rep")
    cmds.setAttr(md + ".operation", 2)
    _unir("{}.{}".format(ctrl, rep_u[0]), md + ".input1X")
    _unir("{}.{}".format(ctrl, rep_v[0]), md + ".input1Y")
    _unir("{}.{}".format(ctrl, rep_u[1]), md + ".input2X")
    _unir("{}.{}".format(ctrl, rep_v[1]), md + ".input2Y")
    _unir(md + ".outputX", p + ".repeatU")
    _unir(md + ".outputY", p + ".repeatV")
    _unir(ctrl + ".rotacion", p + ".rotateUV")
    return p


def _imagen(material, sufijo, ruta, espacio_color, place, escalar):
    nodo = cmds.shadingNode("file", asTexture=True, isColorManaged=True, name=_nombre(material, sufijo))
    _marcar(nodo, material)
    for a in ("coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger", "wrapU", "wrapV",
              "repeatUV", "offset", "rotateUV", "noiseUV", "vertexUvOne", "vertexUvTwo", "vertexUvThree",
              "vertexCameraOne"):
        _unir(place + "." + a, nodo + "." + a)
    _unir(place + ".outUV", nodo + ".uv")
    _unir(place + ".outUvFilterSize", nodo + ".uvFilterSize")
    cmds.setAttr(nodo + ".fileTextureName", ruta, type="string")
    cmds.setAttr(nodo + ".ignoreColorSpaceFileRules", 1)
    cmds.setAttr(nodo + ".colorSpace", espacio_color, type="string")
    cmds.setAttr(nodo + ".alphaIsLuminance", 1 if escalar else 0)
    return nodo


def _suma(material, sufijo, entradas):
    """plusMinusAverage 1D: cada entrada es un plug o un número."""
    pma = _nodo("plusMinusAverage", material, sufijo)
    cmds.setAttr(pma + ".operation", 1)
    for i, e in enumerate(entradas):
        destino = "{}.input1D[{}]".format(pma, i)
        if isinstance(e, str):
            _unir(e, destino)
        else:
            cmds.setAttr(destino, e)
    return pma + ".output1D"


def _producto(material, sufijo, a, b):
    md = _nodo("multiplyDivide", material, sufijo)
    for plug, destino in ((a, md + ".input1X"), (b, md + ".input2X")):
        if isinstance(plug, str):
            _unir(plug, destino)
        else:
            cmds.setAttr(destino, plug)
    return md + ".outputX"


def _mezcla(material, sufijo, encima, debajo, cuanto):
    """blendColors: ``encima`` donde ``cuanto`` = 1, ``debajo`` donde 0 (plugs de color)."""
    bc = _nodo("blendColors", material, sufijo)
    _unir(encima, bc + ".color1")
    _unir(debajo, bc + ".color2")
    _unir(cuanto, bc + ".blender")
    return bc + ".output"


def _conexiones_previas(material):
    antes = {}
    for atributo in SALIDAS:
        origen = cmds.listConnections("{}.{}".format(material, atributo), source=True, destination=False,
                                      plugs=True) or []
        if origen and not _hay(origen[0].split(".")[0], ATTR):
            antes[atributo] = origen[0]
    return antes


def montar(material, plan, base, espacio, espacio_srgb, espacio_raw, escala_uv=100.0):
    """Crea (o rehace) la red del motivo. ``base``: (color lineal, rugosidad, metal) de la receta.

    Devuelve el nodo de control.
    """
    m = plan["motivo"]
    capas = plan["capas"]
    est = capas.get("estructura")
    aca = capas.get("acabado")
    ctrl = control_de(material)
    if ctrl is None:
        antes = json.dumps(_conexiones_previas(material))
    else:
        antes = cmds.getAttr(ctrl + "." + ATTR_ANTES) or "{}"
    for atributo in SALIDAS:
        plug = "{}.{}".format(material, atributo)
        for origen in cmds.listConnections(plug, source=True, destination=False, plugs=True) or []:
            cmds.disconnectAttr(origen, plug)
    viejos = [n for n in nodos_de(material) if n != ctrl and cmds.nodeType(n) not in TIPOS_PROYECCION]
    for nodo in viejos:
        if cmds.objExists(nodo):
            cmds.delete(nodo)
        if ctrl is not None and not cmds.objExists(ctrl) and not RECREADOS_POR:
            RECREADOS_POR.append("{} ({})".format(nodo, ",".join(viejos)))
    if ctrl is not None and not cmds.objExists(ctrl):
        # Maya puede llevarse el control al borrar la red vieja: se crea de nuevo con lo que había antes.
        RECREADOS.append(ctrl)
        ctrl = None
    if ctrl is None:
        ctrl = _crear_control(material)
        cmds.setAttr(ctrl + "." + ATTR_ANTES, antes, type="string")
    poner_valores(ctrl, m, espacio)
    poner_base(ctrl, base[0], base[1], base[2], espacio)
    f = plan["factores"]
    escala = escala_uv / 100.0
    for clave in ("kU", "kV", "aU", "aV"):
        cmds.setAttr("{}.{}".format(ctrl, clave), f[clave] * escala)
    cmds.setAttr(ctrl + ".relieveCm", (est or aca)["relieve_cm"])
    if est and aca:
        # La altura del acabado lleva su propio relieve en cm (unos milímetros): con un peso fijo, el
        # grano de un acabado sobre una teja de 10 cm salía de 3,5 cm y borraba la curva de la teja.
        cmds.setAttr(ctrl + ".alturaAcabado", mv.peso_altura_acabado(est["relieve_cm"], aca["relieve_cm"]))

    mascara = altura_e = zona2 = tono = color_a = rug_a = altura_a = metal_a = None
    places = []
    if est:
        pe = _place(material, "uvEstructura", ctrl, ("kU", "pieza"), ("kV", "pieza"))
        places.append(pe)
        mascara = _imagen(material, "mascara", est["mapas"]["mascara"], espacio_raw, pe, False)
        altura_e = _imagen(material, "altura", est["mapas"]["altura"], espacio_raw, pe, True)
        if est.get("color2") and est["mapas"].get("zona2"):
            zona2 = _imagen(material, "zona2", est["mapas"]["zona2"], espacio_raw, pe, True)
        if est["mapas"].get("tono"):
            tono = _imagen(material, "tono", est["mapas"]["tono"], espacio_raw, pe, False)
            cmds.setAttr(tono + ".colorGain", 2, 2, 2, type="double3")
    if aca:
        pa = _place(material, "uvAcabado", ctrl, ("aU", "repeticion"), ("aV", "repeticion"))
        places.append(pa)
        color_a = _imagen(material, "acabadoColor", aca["mapas"]["color"], espacio_raw, pa, False)
        cmds.setAttr(color_a + ".colorGain", 2, 2, 2, type="double3")
        rug_a = _imagen(material, "acabadoRugosidad", aca["mapas"]["rugosidad"], espacio_raw, pa, True)
        if aca["mapas"].get("altura"):
            altura_a = _imagen(material, "acabadoAltura", aca["mapas"]["altura"], espacio_raw, pa, True)
        if aca["mapas"].get("metal"):
            # Óxido, cardenillo o pintura sobre metal: donde el mapa es 0 deja de ser metal.
            metal_a = _imagen(material, "acabadoMetal", aca["mapas"]["metal"], espacio_raw, pa, True)

    # Color
    color = ctrl + ".colorPieza"
    desgaste = None
    if est:
        if zona2:
            color = _mezcla(material, "color2", ctrl + ".color2", color, zona2 + ".outAlpha")
        g = _suma(material, "variacionG", [mascara + ".outColorG", -0.5])
        gv = _producto(material, "variacionPor", g, ctrl + ".variacion")
        factor = _suma(material, "variacionFactor", [1.0, gv, gv])
        md = _nodo("multiplyDivide", material, "variacion")
        _unir(color, md + ".input1")
        for canal in "XYZ":
            _unir(factor, md + ".input2" + canal)
        color = md + ".output"
        if tono:
            # El matiz por pieza llega entero con Variación 0,3 (el valor por defecto) y se apaga en 0.
            cuanto = _nodo("clamp", material, "tonoCuanto")
            _unir(_producto(material, "tonoPor", ctrl + ".variacion", 1.0 / VARIACION_DEFECTO), cuanto + ".inputR")
            cmds.setAttr(cuanto + ".maxR", 1.0)
            bc = _nodo("blendColors", material, "tonoMezcla")
            _unir(tono + ".outColor", bc + ".color1")
            cmds.setAttr(bc + ".color2", 1.0, 1.0, 1.0, type="double3")
            _unir(cuanto + ".outputR", bc + ".blender")
            md = _nodo("multiplyDivide", material, "tono")
            _unir(color, md + ".input1")
            _unir(bc + ".output", md + ".input2")
            color = md + ".output"
    if aca:
        md = _nodo("multiplyDivide", material, "acabado")
        _unir(color, md + ".input1")
        _unir(color_a + ".outColor", md + ".input2")
        color = md + ".output"
    if est:
        color = _mezcla(material, "junta", ctrl + ".colorJunta", color, mascara + ".outColorR")
        inverso = _nodo("reverse", material, "desgasteInverso")
        _unir(ctrl + ".desgaste", inverso + ".inputX")
        tope = _suma(material, "desgasteTope", [inverso + ".outputX", 0.2])
        remap = _nodo("remapValue", material, "desgasteMapa")
        _unir(mascara + ".outColorB", remap + ".inputValue")
        _unir(inverso + ".outputX", remap + ".inputMin")
        _unir(tope, remap + ".inputMax")
        desgaste = remap + ".outValue"
        color = _mezcla(material, "desgaste", ctrl + ".colorDesgaste", color, desgaste)

    # Rugosidad (R) y metal (G)
    rugosidad = ctrl + ".rugosidad"
    metal = ctrl + ".metal"
    if aca:
        rugosidad = _suma(material, "rugosidad", [rugosidad, rug_a + ".outAlpha", -0.5])
    if metal_a:
        metal = _producto(material, "metalAcabado", metal, metal_a + ".outAlpha")
    if est:
        for sufijo, encima, cuanto in (("rmJunta", ctrl + ".rugosidadJunta", mascara + ".outColorR"),
                                       ("rmDesgaste", ctrl + ".rugosidadDesgaste", desgaste)):
            bc = _nodo("blendColors", material, sufijo)
            _unir(encima, bc + ".color1R")
            cmds.setAttr(bc + ".color1G", 0.0)
            _unir(rugosidad, bc + ".color2R")
            _unir(metal, bc + ".color2G")
            _unir(cuanto, bc + ".blender")
            rugosidad, metal = bc + ".outputR", bc + ".outputG"

    # Altura
    altura = None
    if altura_e and altura_a:
        parte = _producto(material, "alturaAcabado", altura_a + ".outAlpha", ctrl + ".alturaAcabado")
        altura = _suma(material, "alturaTotal", [altura_e + ".outAlpha", parte])
    elif altura_e or altura_a:
        altura = (altura_e or altura_a) + ".outAlpha"

    if m["proyeccion"] == "triplanar":
        tri_c = _triplanar(material, "triplanarColor", ctrl, color)
        datos = _nodo("plusMinusAverage", material, "datos")
        _unir(rugosidad, datos + ".input3D[0].input3Dx")
        _unir(metal, datos + ".input3D[0].input3Dy")
        if altura:
            _unir(altura, datos + ".input3D[0].input3Dz")
        tri_d = _triplanar(material, "triplanarDatos", ctrl, datos + ".output3D")
        color = tri_c + ".outColor"
        rugosidad, metal = tri_d + ".outColorR", tri_d + ".outColorG"
        altura = tri_d + ".outColorB" if altura else None

    limite = _nodo("clamp", material, "limite")
    cmds.setAttr(limite + ".max", 1, 1, 1, type="double3")
    _unir(rugosidad, limite + ".inputR")
    _unir(metal, limite + ".inputG")
    _unir(color, material + ".baseColor")
    _unir(limite + ".outputR", material + ".specularRoughness")
    _unir(limite + ".outputG", material + ".baseMetalness")
    if altura:
        bump = _nodo("bump2d", material, "relieve")
        cmds.setAttr(bump + ".bumpInterp", 0)
        _unir(altura, bump + ".bumpValue")
        _unir(_producto(material, "relieveCm", ctrl + ".relieve", ctrl + ".relieveCm"), bump + ".bumpDepth")
        _unir(bump + ".outNormal", material + ".normalCamera")
    _guardar_places(ctrl, places)
    return ctrl


def _guardar_places(ctrl, places):
    if not _hay(ctrl, "places"):
        cmds.addAttr(ctrl, longName="places", attributeType="message", multi=True)
    for i in cmds.getAttr(ctrl + ".places", multiIndices=True) or []:
        cmds.removeMultiInstance("{}.places[{}]".format(ctrl, i), b=True)
    for i, p in enumerate(places):
        _unir(p + ".message", "{}.places[{}]".format(ctrl, i))


def places_de(ctrl):
    if not ctrl or not _hay(ctrl, "places"):
        return []
    return cmds.listConnections(ctrl + ".places", source=True, destination=False) or []


def _triplanar(material, sufijo, ctrl, entrada):
    tri = _nodo("aiTriplanar", material, sufijo, utilidad=False)
    _unir(entrada, tri + ".input")
    _unir(ctrl + ".mezcla", tri + ".blend")
    if _hay(tri, "scale"):
        cmds.setAttr(tri + ".scale", TRIPLANAR_ESCALA, TRIPLANAR_ESCALA, TRIPLANAR_ESCALA, type="double3")
    if _hay(tri, "coordSpace"):
        nombres = (cmds.attributeQuery("coordSpace", node=tri, listEnum=True) or [""])[0].split(":")
        quiero = "world" if cmds.getAttr(ctrl + ".espacio") == mv.ESPACIOS.index("mundo") else "object"
        if quiero in nombres:
            cmds.setAttr(tri + ".coordSpace", nombres.index(quiero))
    return tri


def quitar(material):
    """Borra la red y las proyecciones y vuelve a conectar lo que había antes. Devuelve las formas tocadas."""
    ctrl = control_de(material)
    if not ctrl:
        return []
    try:
        antes = json.loads(cmds.getAttr(ctrl + "." + ATTR_ANTES) or "{}")
    except ValueError:
        antes = {}
    formas = borrar_proyecciones(material)
    nodos = nodos_de(material)
    for nodo in nodos + [ctrl]:
        if cmds.objExists(nodo):
            cmds.delete(nodo)
    for atributo, origen in antes.items():
        if cmds.objExists(origen.split(".")[0]):
            try:
                _unir(origen, "{}.{}".format(material, atributo))
            except RuntimeError:
                pass
    limpiar_conjuntos(formas)
    return formas


# --- Proyección -------------------------------------------------------------------------------


def miembros(grupo):
    """[(transform, forma, componentes)] de un shadingEngine. ``componentes``: "pCube1.f[0:3]" o None."""
    salida = []
    for m in cmds.sets(grupo, query=True) or []:
        nodo = m.split(".")[0]
        if not cmds.objExists(nodo):
            continue
        if cmds.nodeType(nodo) == "mesh":
            forma = cmds.ls(nodo, long=True)[0]
            transform = cmds.listRelatives(forma, parent=True, fullPath=True)[0]
        else:
            transform = cmds.ls(nodo, long=True)[0]
            formas = cmds.listRelatives(transform, shapes=True, noIntermediate=True, fullPath=True, type="mesh")
            if not formas:
                continue
            forma = formas[0]
        componentes = m if "." in m else None
        salida.append((transform, forma, componentes))
    return salida


def _om():
    import maya.api.OpenMaya as om
    return om


def _geometria(forma, componentes, espacio):
    """Puntos (cm), normales y caras de lo que lleva el material, en el espacio pedido."""
    om = _om()
    sel = om.MSelectionList()
    sel.add(forma)
    dag = sel.getDagPath(0)
    malla = om.MFnMesh(dag)
    caras = None
    if componentes:
        sc = om.MSelectionList()
        sc.add(componentes)
        _ruta, comp = sc.getComponent(0)
        if not comp.isNull():
            caras = list(om.MFnSingleIndexedComponent(comp).getElements())
    if caras is None:
        caras = list(range(malla.numPolygons))
    om_espacio = om.MSpace.kWorld if espacio == "mundo" else om.MSpace.kObject
    puntos = malla.getPoints(om_espacio)
    escala = (1.0, 1.0, 1.0)
    if espacio == "objeto":
        escala = tuple(abs(x) for x in om.MTransformationMatrix(dag.inclusiveMatrix()).scale(om.MSpace.kWorld))
    usados = set()
    normales = {}
    for c in caras:
        ids = malla.getPolygonVertices(c)
        usados.update(ids)
        n = malla.getPolygonNormal(c, om_espacio)
        normales[c] = (n.x * escala[0], n.y * escala[1], n.z * escala[2]) if espacio == "objeto" else (n.x, n.y, n.z)
    pts = [(puntos[i].x * escala[0], puntos[i].y * escala[1], puntos[i].z * escala[2]) for i in usados] \
        if espacio == "objeto" else [(puntos[i].x, puntos[i].y, puntos[i].z) for i in usados]
    if not pts:
        return None
    minimo = [min(p[k] for p in pts) for k in range(3)]
    maximo = [max(p[k] for p in pts) for k in range(3)]
    centro = [(a + b) / 2.0 for a, b in zip(minimo, maximo)]
    return {"caras": caras, "normales": normales, "puntos": pts, "centro": centro, "min": minimo, "max": maximo,
            "escala": escala}


def _radio(geo, eje):
    k = "xyz".index(eje)
    otros = [i for i in range(3) if i != k]
    c = geo["centro"]
    distancias = [math.hypot(p[otros[0]] - c[otros[0]], p[otros[1]] - c[otros[1]]) for p in geo["puntos"]]
    return max(1e-3, sum(distancias) / len(distancias))


def _componentes(transform, caras):
    if not caras:
        return []
    caras = sorted(caras)
    tramos = []
    inicio = previo = caras[0]
    for c in caras[1:]:
        if c == previo + 1:
            previo = c
            continue
        tramos.append((inicio, previo))
        inicio = previo = c
    tramos.append((inicio, previo))
    return ["{}.f[{}:{}]".format(transform, a, b) if a != b else "{}.f[{}]".format(transform, a) for a, b in tramos]


def _proyeccion(material, comps, tipo, eje, forma):
    nodos = cmds.polyProjection(comps, type=tipo, mapDirection=eje, uvSetName=mv.CONJUNTO_UV,
                                createNewMap=False, insertBeforeDeformers=True, constructionHistory=True) or []
    nodo = nodos[0]
    _marcar(nodo, material)
    if not _hay(nodo, "materialsForma"):
        cmds.addAttr(nodo, longName="materialsForma", dataType="string")
    cmds.setAttr(nodo + ".materialsForma", forma, type="string")
    return nodo


ROTACION_CILINDRO = {"y": (0.0, 0.0, 0.0), "x": (0.0, 0.0, 90.0), "z": (90.0, 0.0, 0.0)}


def proyectar(material, grupo, motivo, tile_u_cm=0.0):
    """Escribe el conjunto de UV ``tt_motivo`` en lo que lleva el material. Devuelve las formas."""
    m = mv.normalizar(motivo)
    viejas = borrar_proyecciones(material)
    if m["proyeccion"] not in mv.ESCRIBEN_UV:
        limpiar_conjuntos(viejas)
        return []
    unidad = cm_por_unidad()
    metro = 100.0 / unidad   # un metro en unidades de la escena
    formas = []
    for transform, forma, componentes in miembros(grupo):
        geo = _geometria(forma, componentes, m["espacio"])
        if not geo:
            continue
        if mv.CONJUNTO_UV not in (cmds.polyUVSet(forma, query=True, allUVSets=True) or []):
            cmds.polyUVSet(forma, create=True, uvSet=mv.CONJUNTO_UV)
        du, dv = mv.desfase(transform.split("|")[-1], m["azar"])
        centro = [x / unidad for x in geo["centro"]]
        if m["espacio"] == "mundo":
            centro_nodo = centro
        else:
            centro_nodo = [x / s if s else x for x, s in zip(centro, geo["escala"])]
        tareas = []
        if m["proyeccion"] == "planar":
            tareas.append(("Planar", m["eje"], geo["caras"]))
        elif m["proyeccion"] == "caja":
            grupos = {"x": [], "y": [], "z": []}
            for c, n in geo["normales"].items():
                k = max(range(3), key=lambda i: abs(n[i]))
                grupos["xyz"[k]].append(c)
            for eje in "xyz":
                if grupos[eje]:
                    tareas.append(("Planar", eje, grupos[eje]))
        elif m["proyeccion"] == "cilindrica":
            k = "xyz".index(m["eje"])
            tapas = [c for c, n in geo["normales"].items() if abs(n[k]) > 0.7 * math.sqrt(sum(x * x for x in n) or 1)]
            lados = [c for c in geo["caras"] if c not in set(tapas)]
            if lados:
                tareas.append(("Cylindrical", m["eje"], lados))
            if tapas:
                tareas.append(("Planar", m["eje"], tapas))
        elif m["proyeccion"] == "esferica":
            tareas.append(("Spherical", m["eje"], geo["caras"]))
        for tipo, eje, caras in tareas:
            nodo = _proyeccion(material, _componentes(transform, caras), tipo, eje, forma)
            if _hay(nodo, "worldSpace"):
                try:
                    cmds.setAttr(nodo + ".worldSpace", m["espacio"] == "mundo")
                except RuntimeError:
                    pass
            if _hay(nodo, "projectionCenter"):
                cmds.setAttr(nodo + ".projectionCenter", *centro_nodo, type="double3")
            if tipo == "Planar":
                escala = geo["escala"] if m["espacio"] == "objeto" else (1.0, 1.0, 1.0)
                ancho = {"x": (2, 1), "y": (0, 2), "z": (0, 1)}[eje]
                cmds.setAttr(nodo + ".projectionWidth", metro / (escala[ancho[0]] or 1.0))
                cmds.setAttr(nodo + ".projectionHeight", metro / (escala[ancho[1]] or 1.0))
                cmds.setAttr(nodo + ".imageScale", 1.0, 1.0, type="double2")
            else:
                radio = _radio(geo, eje)
                vuelta = 2.0 * math.pi * radio
                cmds.setAttr(nodo + ".rotate", *ROTACION_CILINDRO[eje], type="double3")
                cmds.setAttr(nodo + ".projectionHorizontalSweep", 360.0)
                if tipo == "Cylindrical":
                    k = "xyz".index(eje)
                    alto = max(geo["max"][k] - geo["min"][k], 1e-3)
                    s_eje = geo["escala"][k] if m["espacio"] == "objeto" else 1.0
                    cmds.setAttr(nodo + ".projectionHeight", alto / unidad / (s_eje or 1.0))
                    cmds.setAttr(nodo + ".imageScale", mv.vuelta_cerrada(vuelta, tile_u_cm), alto / 100.0,
                                 type="double2")
                else:
                    cmds.setAttr(nodo + ".projectionVerticalSweep", 180.0)
                    cmds.setAttr(nodo + ".imageScale", mv.vuelta_cerrada(vuelta, tile_u_cm), vuelta / 200.0,
                                 type="double2")
                if _hay(nodo, "radius"):
                    cmds.setAttr(nodo + ".radius", radio / unidad)
            cmds.setAttr(nodo + ".imageCenter", 0.5 + du, 0.5 + dv, type="double2")
        formas.append(forma)
    limpiar_conjuntos([f for f in viejas if f not in formas])
    return formas


def tile_u_de(ctrl):
    """Ancho real (cm) de la imagen de la estructura con la pieza actual (para cerrar costuras)."""
    k = cmds.getAttr(ctrl + ".kU")
    if cmds.getAttr(ctrl + ".estructura") and k > 0:
        return 100.0 * cmds.getAttr(ctrl + ".pieza") / k
    return cmds.getAttr(ctrl + ".repeticion")


def borrar_proyecciones(material):
    formas = []
    nodos = nodos_de(material, TIPOS_PROYECCION)
    for n in nodos:
        if _hay(n, "materialsForma"):
            forma = cmds.getAttr(n + ".materialsForma")
            if forma and forma not in formas:
                formas.append(forma)
    if nodos:
        cmds.delete(nodos)
    return formas


def limpiar_conjuntos(formas):
    """Quita ``tt_motivo`` de las formas que ya no tienen ninguna proyección de motivo."""
    en_uso = set()
    for n in cmds.ls(type=list(TIPOS_PROYECCION)) or []:
        if _hay(n, "materialsForma"):
            en_uso.add(cmds.getAttr(n + ".materialsForma"))
    for forma in formas:
        if forma in en_uso or not cmds.objExists(forma):
            continue
        conjuntos = cmds.polyUVSet(forma, query=True, allUVSets=True) or []
        if mv.CONJUNTO_UV not in conjuntos:
            continue
        actual = (cmds.polyUVSet(forma, query=True, currentUVSet=True) or [""])[0]
        if actual == mv.CONJUNTO_UV:
            otros = [c for c in conjuntos if c != mv.CONJUNTO_UV]
            if otros:
                cmds.polyUVSet(forma, currentUVSet=True, uvSet=otros[0])
        try:
            cmds.polyUVSet(forma, delete=True, uvSet=mv.CONJUNTO_UV)
        except RuntimeError:
            pass


def conectar_conjuntos(material, ctrl, formas):
    """uvChooser: las texturas del motivo leen ``tt_motivo`` en cada forma."""
    elegidor = _nombre(material, "uvs")
    if cmds.objExists(elegidor):
        cmds.delete(elegidor)
    places = places_de(ctrl)
    if not formas or not places:
        return None
    elegidor = _nodo("uvChooser", material, "uvs")
    k = 0
    for forma in formas:
        for i in cmds.getAttr(forma + ".uvSet", multiIndices=True) or []:
            if cmds.getAttr("{}.uvSet[{}].uvSetName".format(forma, i)) == mv.CONJUNTO_UV:
                _unir("{}.uvSet[{}].uvSetName".format(forma, i), "{}.uvSets[{}]".format(elegidor, k))
                k += 1
                break
    for p in places:
        _unir(elegidor + ".outUv", p + ".uvCoord")
        for a, b in (("outVertexCameraOne", "vertexCameraOne"), ("outVertexUvOne", "vertexUvOne"),
                     ("outVertexUvTwo", "vertexUvTwo"), ("outVertexUvThree", "vertexUvThree")):
            _unir(elegidor + "." + a, p + "." + b)
    return elegidor


def densidad_uv(grupo):
    """Centímetros que mide una unidad de UV en lo que lleva el material (proyección «uv»)."""
    om = _om()
    area3d = area_uv = 0.0
    for _transform, forma, componentes in miembros(grupo):
        sel = om.MSelectionList()
        sel.add(componentes or forma)
        ruta, comp = sel.getComponent(0)
        it = om.MItMeshPolygon(ruta, comp) if comp and not comp.isNull() else om.MItMeshPolygon(ruta)
        while not it.isDone():
            try:
                if it.hasUVs():
                    area3d += it.getArea(om.MSpace.kWorld)
                    area_uv += it.getUVArea()
            except RuntimeError:
                pass
            it.next()
    if area_uv <= 1e-12 or area3d <= 0:
        return 100.0
    return math.sqrt(area3d / area_uv)
