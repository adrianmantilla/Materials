"""Todo lo que Muestrario hace en la escena de Maya.

La ventana no llama a ``maya.cmds`` directamente: usa un objeto
:class:`ServiciosMaya`, y las pruebas sin Maya usan uno falso con los mismos métodos.

Los materiales que crea Muestrario son nodos ``openPBRSurface`` normales con dos
atributos extra: ``muestrarioReceta`` (la receta en JSON, para recordar notas y
valores que no están en el nodo) y ``muestrarioDestino`` (render o juego).
Los nodos de imagen que conecta llevan ``muestrarioEntrada`` para poder
recargarlos o sustituirlos sin duplicar.
"""

import json
import os
import shutil
import subprocess
import sys

from maya import cmds, mel

from muestrario import color as col
from muestrario import intercambio as ic
from muestrario import receta as rc
from muestrario import texturas as tx
from muestrario.i18n import t


def _unir(origen, destino):
    """connectAttr que no avisa si la conexión ya existe."""
    if not cmds.isConnected(origen, destino):
        cmds.connectAttr(origen, destino, force=True)

TIPO = "openPBRSurface"
ATTR_RECETA = "muestrarioReceta"
ATTR_DESTINO = "muestrarioDestino"
ATTR_ENTRADA = "muestrarioEntrada"
ATTR_ENVIO = "muestrarioEnvio"
INFO_DESTINO = "muestrarioDestino"
INFO_MOTOR = "muestrarioMotor"

# Entrada de textura -> atributo del material (escalares) o especial.
ENTRADA_ATRIBUTO = {
    "color": "baseColor",
    "rugosidad": "specularRoughness",
    "metal": "baseMetalness",
    "emision": "emissionColor",
    "opacidad": "geometryOpacity",
    "transmision": "transmissionWeight",
    "subsuperficie": "subsurfaceWeight",
}
COLOR_ATTRS = ("baseColor", "specularColor", "transmissionColor", "subsurfaceColor", "coatColor", "fuzzColor",
               "emissionColor")
TIPOS_CONVERTIBLES = ("standardSurface", "aiStandardSurface", "lambert", "blinn", "phong", "phongE",
                      "usdPreviewSurface")


def _hay(nodo, atributo):
    try:
        return cmds.attributeQuery(atributo, node=nodo, exists=True)
    except RuntimeError:
        return False


def _conectado(nodo, atributo):
    return bool(cmds.listConnections("{}.{}".format(nodo, atributo), source=True, destination=False))


def _espacio_render():
    try:
        if not cmds.colorManagementPrefs(query=True, cmEnabled=True):
            return ""
        return cmds.colorManagementPrefs(query=True, renderingSpaceName=True) or ""
    except Exception:
        return ""


def _espacio_entrada(preferidos):
    """Nombre real del espacio de color de entrada en la configuración de esta escena."""
    try:
        nombres = cmds.colorManagementPrefs(query=True, inputSpaceNames=True) or []
    except Exception:
        nombres = []
    for p in preferidos:
        for n in nombres:
            if n.lower() == p.lower():
                return n
    for p in preferidos:
        for n in nombres:
            if p.lower() in n.lower():
                return n
    return preferidos[0]


ESPACIO_SRGB = ("sRGB", "sRGB - Texture", "Utility - sRGB - Texture", "sRGB Encoded Rec.709 (sRGB)")
ESPACIO_RAW = ("Raw", "Utility - Raw", "Data", "raw")


class ServiciosMaya(object):
    en_maya = True

    # --- Comprobaciones ------------------------------------------------------------------

    def openpbr_disponible(self):
        return TIPO in (cmds.allNodeTypes() or [])

    def proyecto(self):
        return cmds.workspace(query=True, rootDirectory=True) or ""

    def existe(self, nodo):
        return bool(nodo) and cmds.objExists(nodo)

    def deshacer(self, nombre):
        """Uso: ``with servicios.deshacer("x"):`` agrupa en un solo Ctrl+Z."""
        return _Bloque(nombre)

    # --- Destino de la escena ----------------------------------------------------------------

    def destino_escena(self, defecto):
        valor = cmds.fileInfo(INFO_DESTINO, query=True)
        destino = valor[0] if valor else defecto
        return destino if destino in rc.DESTINOS else defecto

    def motor_escena(self, defecto):
        valor = cmds.fileInfo(INFO_MOTOR, query=True)
        return valor[0] if valor and valor[0] in ic.MOTORES else defecto

    def guardar_destino(self, destino, motor):
        cmds.fileInfo(INFO_DESTINO, destino)
        cmds.fileInfo(INFO_MOTOR, motor)

    # --- Materiales ---------------------------------------------------------------------

    def crear_material(self, receta, destino, nombre=None):
        nombre = rc.nombre_material(nombre or receta.get("nombre", "Material"))
        with _Bloque("Muestrario: crear material"):
            material = cmds.shadingNode(TIPO, asShader=True, name=nombre)
            grupo = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=material + "SG")
            _unir(material + ".outColor", grupo + ".surfaceShader")
            for atributo in (ATTR_RECETA, ATTR_DESTINO):
                cmds.addAttr(material, longName=atributo, dataType="string")
            self.actualizar_material(material, receta, destino)
        return material

    def actualizar_material(self, material, receta, destino):
        """Escribe la receta en el nodo. Lo que tiene textura conectada no se toca."""
        if not cmds.objExists(material):
            return []
        atributos = rc.atributos_openpbr(receta, destino)
        espacio = _espacio_render()
        omitidos = []
        for atributo, valor in atributos.items():
            if not _hay(material, atributo):
                omitidos.append(atributo)
                continue
            if _conectado(material, atributo):
                continue
            plug = "{}.{}".format(material, atributo)
            try:
                if isinstance(valor, bool):
                    cmds.setAttr(plug, valor)
                elif isinstance(valor, tuple):
                    if atributo in COLOR_ATTRS:
                        valor = col.a_espacio_render(valor, espacio)
                    cmds.setAttr(plug, *valor, type="double3")
                else:
                    cmds.setAttr(plug, valor)
            except RuntimeError:
                omitidos.append(atributo)
        if _hay(material, ATTR_RECETA):
            datos = {k: v for k, v in rc.normalizar(receta).items() if k in rc.DEFECTO}
            cmds.setAttr(material + "." + ATTR_RECETA, json.dumps(datos, ensure_ascii=False), type="string")
            cmds.setAttr(material + "." + ATTR_DESTINO, destino, type="string")
        return omitidos

    def leer_receta(self, material):
        """Receta del material: los valores vivos del nodo mandan sobre los guardados."""
        guardada = {}
        if _hay(material, ATTR_RECETA):
            try:
                guardada = json.loads(cmds.getAttr(material + "." + ATTR_RECETA) or "{}")
            except ValueError:
                guardada = {}
        espacio = _espacio_render()
        valores = {}
        for atributo in rc.atributos_openpbr(rc.nueva()):
            if not _hay(material, atributo):
                continue
            valor = cmds.getAttr("{}.{}".format(material, atributo))
            if isinstance(valor, list) and valor and isinstance(valor[0], tuple):
                valor = col.desde_espacio_render(valor[0], espacio) if atributo in COLOR_ATTRS else valor[0]
            valores[atributo] = valor
        viva = rc.desde_atributos(valores, nombre=guardada.get("nombre") or material)
        if guardada:
            for clave in ("nombre", "nota", "familia", "destinos"):
                if clave in guardada:
                    viva[clave] = guardada[clave]
            # Colores que dependen de la base: si en la receta eran «automáticos», siguen siéndolo.
            for clave in ("color_transmision", "color_subsuperficie", "color_emision", "color_pelusa"):
                if guardada.get(clave) is None:
                    viva[clave] = None
        final = rc.normalizar(viva)
        final["texturas"] = self.texturas_de(material)
        return final

    def material_seleccionado(self):
        """Primer material de la selección (objeto, cara o el propio nodo)."""
        for elemento in cmds.ls(selection=True, long=True) or []:
            nodo = elemento.split(".")[0]
            if cmds.nodeType(nodo) in (TIPO,) + TIPOS_CONVERTIBLES:
                return nodo
            formas = cmds.listRelatives(nodo, shapes=True, fullPath=True, noIntermediate=True) or [nodo]
            for forma in formas:
                for grupo in cmds.listConnections(forma, type="shadingEngine") or []:
                    if "." in elemento and not self._cara_en_grupo(elemento, grupo):
                        continue
                    materiales = cmds.listConnections(grupo + ".surfaceShader") or []
                    if materiales:
                        return materiales[0]
        return None

    def _cara_en_grupo(self, cara, grupo):
        try:
            return bool(cmds.sets(cara, isMember=grupo))
        except Exception:
            return True

    def _grupo(self, material):
        grupos = cmds.listConnections(material + ".outColor", type="shadingEngine") or []
        if grupos:
            return grupos[0]
        grupo = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=material + "SG")
        _unir(material + ".outColor", grupo + ".surfaceShader")
        return grupo

    def asignar(self, material, elementos=None):
        """Asigna a la selección (objetos o caras). Devuelve cuántos elementos."""
        elementos = elementos or cmds.ls(selection=True, long=True) or []
        validos = []
        for e in elementos:
            nodo = e.split(".")[0]
            if "." in e or cmds.listRelatives(nodo, shapes=True, noIntermediate=True) or \
                    cmds.nodeType(nodo) in ("mesh", "nurbsSurface", "subdiv"):
                validos.append(e)
        if not validos:
            return 0
        with _Bloque("Muestrario: asignar"):
            cmds.sets(validos, edit=True, forceElement=self._grupo(material))
        return len(validos)

    def seleccionar_objetos(self, material):
        grupos = cmds.listConnections(material + ".outColor", type="shadingEngine") or []
        miembros = []
        for g in grupos:
            miembros.extend(cmds.sets(g, query=True) or [])
        cmds.select(miembros, replace=True) if miembros else cmds.select(clear=True)
        return len(miembros)

    def seleccionar_nodo(self, material):
        cmds.select(material, replace=True)
        try:
            mel.eval("openAEWindow")
        except RuntimeError:
            pass

    def renombrar(self, material, nombre):
        nuevo = cmds.rename(material, rc.nombre_material(nombre))
        for g in cmds.listConnections(nuevo + ".outColor", type="shadingEngine") or []:
            if g != "initialShadingGroup":
                cmds.rename(g, nuevo + "SG")
        return nuevo

    def materiales(self):
        """Lista para la pestaña Escena."""
        salida = []
        tipos = (TIPO,) + TIPOS_CONVERTIBLES
        for material in cmds.ls(materials=True) or []:
            tipo = cmds.nodeType(material)
            if tipo not in tipos or material in ("lambert1", "standardSurface1", "particleCloud1", "shaderGlow1"):
                continue
            grupos = cmds.listConnections(material + ".outColor", type="shadingEngine") or []
            miembros = []
            for g in grupos:
                miembros.extend(cmds.sets(g, query=True) or [])
            objetos = sorted({m.split(".")[0] for m in miembros})
            texturas = self.texturas_de(material) if tipo == TIPO else {}
            rotas = [e for e, info in texturas.items() if not info.get("existe", True)]
            salida.append({"nombre": material, "tipo": tipo, "objetos": len(objetos), "texturas": len(texturas),
                           "rotas": len(rotas), "muestrario": _hay(material, ATTR_RECETA),
                           "destino": cmds.getAttr(material + "." + ATTR_DESTINO) if _hay(material, ATTR_DESTINO)
                           else "", "con_prefijo": material.startswith("M_")})
        return salida

    def borrar_sin_usar(self):
        sin_usar = [m["nombre"] for m in self.materiales() if m["objetos"] == 0]
        with _Bloque("Muestrario: borrar sin usar"):
            for material in sin_usar:
                grupos = cmds.listConnections(material + ".outColor", type="shadingEngine") or []
                aguas_arriba = cmds.listHistory(material) or []
                borrar = [n for n in aguas_arriba if cmds.nodeType(n) in ("file", "place2dTexture", "bump2d",
                                                                        "reverse", "displacementShader")]
                cmds.delete([material] + grupos + borrar)
        return len(sin_usar)

    def convertir(self, material, destino):
        """Crea un OpenPBR equivalente a un Standard Surface, aiStandardSurface o Lambert y lo pone en su lugar."""
        tipo = cmds.nodeType(material)
        g = lambda a, d=None: cmds.getAttr(material + "." + a) if _hay(material, a) else d  # noqa: E731
        espacio = _espacio_render()

        def color(a, d=(0.8, 0.8, 0.8)):
            v = g(a)
            return col.desde_espacio_render(v[0], espacio) if v else d
        if tipo in ("standardSurface", "aiStandardSurface"):
            r = rc.nueva(nombre=material, color=col.lineal_a_hex(color("baseColor")), metal=g("metalness", 0.0),
                         rugosidad=g("specularRoughness", 0.5), ior=g("specularIOR", 1.5),
                         transparencia=g("transmission", 0.0), subsuperficie=g("subsurface", 0.0),
                         barniz=g("coat", 0.0), rugosidad_barniz=g("coatRoughness", 0.1),
                         pelusa=g("sheen", 0.0), emision=min(1.0, (g("emission", 0.0) or 0.0) * 0.5),
                         especular=g("specular", 1.0))
        elif tipo == "usdPreviewSurface":
            r = rc.nueva(nombre=material, color=col.lineal_a_hex(color("diffuseColor")), metal=g("metallic", 0.0),
                         rugosidad=g("roughness", 0.5), opacidad=g("opacity", 1.0))
        else:
            transparencia = g("transparency")
            opacidad = 1.0 - (sum(transparencia[0]) / 3.0 if transparencia else 0.0)
            rug = 0.7 if tipo == "lambert" else 0.35
            r = rc.nueva(nombre=material, color=col.lineal_a_hex(color("color")), rugosidad=rug, opacidad=opacidad)
        nombre_nuevo = material if material.startswith("M_") else "M_" + material
        with _Bloque("Muestrario: convertir"):
            nuevo = self.crear_material(r, destino, nombre=nombre_nuevo + "_openPBR")
            # Texturas conectadas al color o la normal se mantienen.
            for viejo, nuevo_attr in (("baseColor", "baseColor"), ("color", "baseColor"), ("diffuseColor", "baseColor"),
                                      ("normalCamera", "normalCamera"), ("specularRoughness", "specularRoughness"),
                                      ("metalness", "baseMetalness")):
                if _hay(material, viejo):
                    origen = cmds.listConnections(material + "." + viejo, source=True, destination=False,
                                                  plugs=True) or []
                    if origen and _hay(nuevo, nuevo_attr):
                        _unir(origen[0], nuevo + "." + nuevo_attr)
            for grupo in cmds.listConnections(material + ".outColor", type="shadingEngine") or []:
                _unir(nuevo + ".outColor", grupo + ".surfaceShader")
        return nuevo

    # --- Texturas -----------------------------------------------------------------------------

    def texturas_de(self, material):
        """entrada -> {ruta, nodo, existe, espacio, nombre} de las imágenes conectadas por Muestrario."""
        salida = {}
        for nodo in cmds.listHistory(material) or []:
            if cmds.nodeType(nodo) != "file":
                continue
            entrada = cmds.getAttr(nodo + "." + ATTR_ENTRADA) if _hay(nodo, ATTR_ENTRADA) else None
            if not entrada:
                continue
            ruta = cmds.getAttr(nodo + ".fileTextureName") or ""
            resuelta = self._resolver(ruta, nodo)
            salida[entrada] = {"ruta": ruta, "nodo": nodo, "nombre": tx.nombre_de_ruta(ruta),
                               "existe": bool(resuelta), "espacio": cmds.getAttr(nodo + ".colorSpace"),
                               "tamano": tx.tamano_imagen(resuelta) if resuelta else None}
        return salida

    def _resolver(self, ruta, nodo=None):
        if not ruta:
            return None
        if nodo is not None and cmds.getAttr(nodo + ".uvTilingMode"):
            # UDIM: basta con que exista una casilla.
            try:
                patron = cmds.getAttr(nodo + ".computedFileTextureNamePattern") or ruta
            except Exception:
                patron = ruta
            carpeta = os.path.dirname(self._absoluta(patron))
            base = os.path.basename(patron).replace("<UDIM>", "")
            if os.path.isdir(carpeta):
                antes, _, despues = os.path.basename(patron).partition("<UDIM>")
                for a in os.listdir(carpeta):
                    if a.startswith(antes) and a.endswith(despues) and base:
                        return os.path.join(carpeta, a)
            return None
        absoluta = self._absoluta(ruta)
        return absoluta if os.path.isfile(absoluta) else None

    def _absoluta(self, ruta):
        if os.path.isabs(ruta):
            return ruta
        return os.path.join(self.proyecto(), ruta)

    def _nodo_imagen(self, material, entrada, ruta, espacio, udim, alfa_es_luminancia):
        nombre = "{}_{}_tex".format(material, entrada)
        existente = None
        for nodo in cmds.listHistory(material) or []:
            if cmds.nodeType(nodo) == "file" and _hay(nodo, ATTR_ENTRADA) and \
                    cmds.getAttr(nodo + "." + ATTR_ENTRADA) == entrada:
                existente = nodo
                break
        nodo = existente or cmds.shadingNode("file", asTexture=True, isColorManaged=True, name=nombre)
        if not existente:
            cmds.addAttr(nodo, longName=ATTR_ENTRADA, dataType="string")
            cmds.setAttr(nodo + "." + ATTR_ENTRADA, entrada, type="string")
            uv = cmds.shadingNode("place2dTexture", asUtility=True, name=nombre + "_uv")
            for a in ("coverage", "translateFrame", "rotateFrame", "mirrorU", "mirrorV", "stagger", "wrapU",
                      "wrapV", "repeatUV", "offset", "rotateUV", "noiseUV", "vertexUvOne", "vertexUvTwo",
                      "vertexUvThree", "vertexCameraOne"):
                _unir(uv + "." + a, nodo + "." + a)
            _unir(uv + ".outUV", nodo + ".uv")
            _unir(uv + ".outUvFilterSize", nodo + ".uvFilterSize")
        cmds.setAttr(nodo + ".uvTilingMode", 3 if udim else 0)
        cmds.setAttr(nodo + ".fileTextureName", ruta, type="string")
        cmds.setAttr(nodo + ".ignoreColorSpaceFileRules", 1)
        cmds.setAttr(nodo + ".colorSpace", _espacio_entrada(ESPACIO_SRGB if espacio == "sRGB" else ESPACIO_RAW),
                     type="string")
        cmds.setAttr(nodo + ".alphaIsLuminance", 1 if alfa_es_luminancia else 0)
        return nodo

    def _salida(self, nodo, canal, invertir, material, entrada):
        """Plug escalar del nodo de imagen (canal o luminancia), invertido si hace falta."""
        plug = {"R": ".outColorR", "G": ".outColorG", "B": ".outColorB", "A": ".outAlpha"}.get(canal, ".outAlpha")
        plug = nodo + plug
        if invertir:
            inversor = "{}_{}_inv".format(material, entrada)
            if not cmds.objExists(inversor):
                inversor = cmds.shadingNode("reverse", asUtility=True, name=inversor)
            _unir(plug, inversor + ".inputX")
            plug = inversor + ".outputX"
        return plug

    def conectar_texturas(self, material, conexiones, opciones=None):
        """``conexiones``: lista de dicts de :meth:`texturas.Conexion.como_dict`. Devuelve entradas conectadas."""
        opciones = opciones or {}
        proyecto = self.proyecto()
        hechas = []
        with _Bloque("Muestrario: conectar texturas"):
            for c in conexiones:
                entrada = c["entrada"]
                if entrada == "ao":
                    continue
                ruta = tx.relativa_al_proyecto(c["ruta"], proyecto)
                escalar = entrada not in ("color", "emision", "normal")
                nodo = self._nodo_imagen(material, entrada, ruta, c.get("espacio", "Raw"), c.get("udim"),
                                         escalar and not c.get("canal"))
                if entrada == "normal":
                    self._conectar_normal(material, nodo, c.get("convencion") or opciones.get("normal", "opengl"))
                elif entrada == "altura":
                    if opciones.get("desplazamiento"):
                        self._conectar_desplazamiento(material, nodo, opciones.get("escala_altura", 0.5))
                    elif not any(x["entrada"] == "normal" for x in conexiones) and not _conectado(material,
                                                                                                    "normalCamera"):
                        self._conectar_bump(material, nodo)
                    else:
                        continue
                elif entrada in ("color", "emision"):
                    atributo = ENTRADA_ATRIBUTO[entrada]
                    _unir(nodo + ".outColor", "{}.{}".format(material, atributo))
                    if entrada == "emision" and cmds.getAttr(material + ".emissionLuminance") <= 0:
                        cmds.setAttr(material + ".emissionLuminance", 1000.0)
                else:
                    atributo = ENTRADA_ATRIBUTO.get(entrada)
                    if not atributo or not _hay(material, atributo):
                        continue
                    plug = self._salida(nodo, c.get("canal"), c.get("invertir"), material, entrada)
                    _unir(plug, "{}.{}".format(material, atributo))
                hechas.append(entrada)
        return hechas

    def _conectar_normal(self, material, nodo, convencion):
        bump = "{}_normal_bump".format(material)
        if not cmds.objExists(bump):
            bump = cmds.shadingNode("bump2d", asUtility=True, name=bump)
        cmds.setAttr(bump + ".bumpInterp", 1)  # normales en espacio tangente
        _unir(nodo + ".outAlpha", bump + ".bumpValue")
        # DirectX tiene el verde al revés que Maya: se invierte en el propio nodo de imagen.
        if convencion == "directx":
            cmds.setAttr(nodo + ".colorGain", 1, -1, 1, type="double3")
            cmds.setAttr(nodo + ".colorOffset", 0, 1, 0, type="double3")
        else:
            cmds.setAttr(nodo + ".colorGain", 1, 1, 1, type="double3")
            cmds.setAttr(nodo + ".colorOffset", 0, 0, 0, type="double3")
        _unir(bump + ".outNormal", material + ".normalCamera")

    def _conectar_bump(self, material, nodo):
        bump = "{}_altura_bump".format(material)
        if not cmds.objExists(bump):
            bump = cmds.shadingNode("bump2d", asUtility=True, name=bump)
        cmds.setAttr(bump + ".bumpInterp", 0)
        cmds.setAttr(bump + ".bumpDepth", 0.05)
        _unir(nodo + ".outAlpha", bump + ".bumpValue")
        _unir(bump + ".outNormal", material + ".normalCamera")

    def _conectar_desplazamiento(self, material, nodo, escala):
        grupo = self._grupo(material)
        desp = "{}_desplazamiento".format(material)
        if not cmds.objExists(desp):
            desp = cmds.shadingNode("displacementShader", asShader=True, name=desp)
        _unir(nodo + ".outAlpha", desp + ".displacement")
        cmds.setAttr(desp + ".scale", escala)
        cmds.setAttr(desp + ".aiDisplacementZeroValue", 0.5) if _hay(desp, "aiDisplacementZeroValue") else None
        _unir(desp + ".displacement", grupo + ".displacementShader")

    def recargar_texturas(self, material=None):
        """Vuelve a leer las imágenes del disco (tras exportar otra vez en Painter)."""
        nodos = []
        fuentes = [material] if material else cmds.ls(type=TIPO) or []
        for m in fuentes:
            nodos.extend(info["nodo"] for info in self.texturas_de(m).values())
        for nodo in nodos:
            ruta = cmds.getAttr(nodo + ".fileTextureName")
            cmds.setAttr(nodo + ".fileTextureName", "", type="string")
            cmds.setAttr(nodo + ".fileTextureName", ruta, type="string")
        return len(nodos)

    def todas_las_imagenes(self):
        return [n for n in cmds.ls(type="file") or []]

    def reparar_rutas(self, carpetas_extra=()):
        """Busca por nombre las imágenes que no se encuentran. Devuelve (arregladas, perdidas)."""
        proyecto = self.proyecto()
        carpetas = [os.path.join(proyecto, "sourceimages")] + [c for c in carpetas_extra if c]
        escena = cmds.file(query=True, sceneName=True)
        if escena:
            carpetas.append(os.path.dirname(escena))
        arregladas, perdidas = [], []
        with _Bloque("Muestrario: reparar rutas"):
            for nodo in self.todas_las_imagenes():
                ruta = cmds.getAttr(nodo + ".fileTextureName") or ""
                if not ruta or self._resolver(ruta, nodo):
                    continue
                nombre = tx.nombre_de_ruta(ruta)
                buscar = nombre.replace("<UDIM>", "1001") if "<UDIM>" in nombre else nombre
                encontrada = tx.buscar_por_nombre(buscar, carpetas)
                if encontrada:
                    if "<UDIM>" in nombre:
                        encontrada = os.path.join(os.path.dirname(encontrada), nombre)
                    cmds.setAttr(nodo + ".fileTextureName", tx.relativa_al_proyecto(encontrada, proyecto),
                                 type="string")
                    arregladas.append(nodo)
                else:
                    perdidas.append(nombre)
        return arregladas, perdidas

    def copiar_al_proyecto(self):
        """Copia a sourceimages las imágenes que están fuera del proyecto y usa rutas relativas."""
        proyecto = self.proyecto()
        destino = os.path.join(proyecto, "sourceimages")
        copiadas = 0
        with _Bloque("Muestrario: copiar al proyecto"):
            for nodo in self.todas_las_imagenes():
                ruta = cmds.getAttr(nodo + ".fileTextureName") or ""
                if not ruta:
                    continue
                relativa = tx.relativa_al_proyecto(self._absoluta(ruta), proyecto)
                if not os.path.isabs(relativa):
                    if relativa != ruta:
                        cmds.setAttr(nodo + ".fileTextureName", relativa, type="string")
                    continue
                origenes = []
                if "<UDIM>" in ruta:
                    carpeta = os.path.dirname(ruta)
                    antes, _, despues = os.path.basename(ruta).partition("<UDIM>")
                    if os.path.isdir(carpeta):
                        origenes = [os.path.join(carpeta, a) for a in os.listdir(carpeta)
                                    if a.startswith(antes) and a.endswith(despues)]
                elif os.path.isfile(ruta):
                    origenes = [ruta]
                if not origenes:
                    continue
                os.makedirs(destino, exist_ok=True)
                for o in origenes:
                    final = os.path.join(destino, os.path.basename(o))
                    if not os.path.exists(final):
                        shutil.copy2(o, final)
                cmds.setAttr(nodo + ".fileTextureName", "sourceimages/" + os.path.basename(ruta), type="string")
                copiadas += 1
        return copiadas

    # --- Painter ------------------------------------------------------------------------------

    def objetos_seleccionados(self):
        """Transformadas con malla de la selección (también si se eligieron caras)."""
        salida = []
        for e in cmds.ls(selection=True, long=True) or []:
            nodo = e.split(".")[0]
            if cmds.nodeType(nodo) == "mesh":
                nodo = (cmds.listRelatives(nodo, parent=True, fullPath=True) or [nodo])[0]
            if cmds.listRelatives(nodo, shapes=True, type="mesh", noIntermediate=True, fullPath=True):
                if nodo not in salida:
                    salida.append(nodo)
            for hijo in cmds.listRelatives(nodo, allDescendents=True, type="mesh", fullPath=True,
                                           noIntermediate=True) or []:
                padre = cmds.listRelatives(hijo, parent=True, fullPath=True)[0]
                if padre not in salida:
                    salida.append(padre)
        return salida

    def materiales_de(self, objetos):
        salida = []
        for o in objetos:
            for forma in cmds.listRelatives(o, shapes=True, fullPath=True, noIntermediate=True) or []:
                for g in cmds.listConnections(forma, type="shadingEngine") or []:
                    for m in cmds.listConnections(g + ".surfaceShader") or []:
                        if m not in salida:
                            salida.append(m)
        return salida

    def sin_uvs(self, objetos):
        malos = []
        for o in objetos:
            for forma in cmds.listRelatives(o, shapes=True, type="mesh", fullPath=True, noIntermediate=True) or []:
                if not (cmds.polyEvaluate(forma, uvcoord=True) or 0):
                    malos.append(o.split("|")[-1])
        return malos

    def enviar_a_painter(self, objetos, destino, motor, resolucion, nombre=None):
        """Exporta la malla y la receta a la carpeta de intercambio. Devuelve la carpeta."""
        if not objetos:
            raise ValueError(t("painter_sin_seleccion"))
        sin = self.sin_uvs(objetos)
        if sin:
            raise ValueError(t("painter_sin_uvs", objetos=", ".join(sin)))
        nombre = ic.limpiar_nombre(nombre or objetos[0].split("|")[-1])
        carpeta = ic.carpeta_envio(self.proyecto(), nombre)
        os.makedirs(carpeta, exist_ok=True)
        ruta_fbx = os.path.join(carpeta, nombre + ".fbx")
        materiales = self.materiales_de(objetos)
        juegos, mapa = {}, {}
        for m in materiales:
            juego = ic.limpiar_nombre(m[2:] if m.startswith("M_") else m)
            receta = self.leer_receta(m) if cmds.nodeType(m) == TIPO else rc.nueva(nombre=m)
            receta.pop("texturas", None)
            receta["material"] = m
            juegos[juego] = receta
            mapa[m] = juego
        self._exportar_fbx(objetos, ruta_fbx, mapa)
        envio = ic.nueva_receta_envio(nombre, ruta_fbx, juegos, destino, motor, resolucion)
        envio["materiales"] = {j: r["material"] for j, r in juegos.items()}
        ic.enviar(carpeta, envio)
        for m in materiales:
            if _hay(m, ATTR_RECETA):
                if not _hay(m, ATTR_ENVIO):
                    cmds.addAttr(m, longName=ATTR_ENVIO, dataType="string")
                cmds.setAttr(m + "." + ATTR_ENVIO, tx.relativa_al_proyecto(carpeta, self.proyecto()), type="string")
        return carpeta

    def _exportar_fbx(self, objetos, ruta, mapa_juegos):
        """Exporta copias con materiales Lambert temporales llamados como los juegos de texturas.

        Painter crea un juego de texturas por material del FBX y le pone su nombre; así se
        reconocen al volver. Se usan copias para no tocar la escena del alumno.
        """
        if not cmds.pluginInfo("fbxmaya", query=True, loaded=True):
            cmds.loadPlugin("fbxmaya", quiet=True)
        seleccion = cmds.ls(selection=True, long=True) or []
        temporales = []
        cmds.undoInfo(openChunk=True, chunkName="Muestrario: exportar")
        try:
            copias = []
            for o in objetos:
                copia = cmds.duplicate(o, name=o.split("|")[-1] + "_painter", returnRootsOnly=True)[0]
                if cmds.listRelatives(copia, parent=True):
                    copia = cmds.parent(copia, world=True)[0]
                copias.append(copia)
            temporales.extend(copias)
            # Material temporal por juego, con el nombre del juego.
            lamberts = {}
            for material, juego in mapa_juegos.items():
                nombre = juego if not cmds.objExists(juego) else juego + "_painter"
                lam = cmds.shadingNode("lambert", asShader=True, name=nombre)
                grupo = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=lam + "SG")
                _unir(lam + ".outColor", grupo + ".surfaceShader")
                lamberts[material] = grupo
                temporales.extend([lam, grupo])
            for copia in copias:
                larga = cmds.ls(copia, long=True)[0]
                for forma in cmds.listRelatives(copia, allDescendents=True, type="mesh", fullPath=True) or []:
                    for g in set(cmds.listConnections(forma, type="shadingEngine") or []):
                        m = (cmds.listConnections(g + ".surfaceShader") or [None])[0]
                        if m not in lamberts:
                            continue
                        miembros = [x for x in cmds.ls(cmds.sets(g, query=True) or [], long=True)
                                    if x.split(".")[0] == larga or x.split(".")[0].startswith(larga + "|")]
                        if miembros:
                            cmds.sets(miembros, edit=True, forceElement=lamberts[m])
            cmds.select(copias, replace=True)
            ruta_mel = ruta.replace("\\", "/")
            for orden in ("FBXResetExport", "FBXExportSmoothingGroups -v true", "FBXExportTangents -v true",
                          "FBXExportSmoothMesh -v false", "FBXExportTriangulate -v false",
                          "FBXExportInputConnections -v false", "FBXExportEmbeddedTextures -v false",
                          "FBXExportCameras -v false", "FBXExportLights -v false", "FBXExportAnimationOnly -v false",
                          "FBXExportBakeComplexAnimation -v false", "FBXExportFileVersion -v FBX202000",
                          'FBXExport -f "{}" -s'.format(ruta_mel)):
                try:
                    mel.eval(orden)
                except RuntimeError:
                    if orden.startswith("FBXExport -f"):
                        raise
        finally:
            existentes = [n for n in temporales if cmds.objExists(n)]
            if existentes:
                cmds.delete(existentes)
            cmds.undoInfo(closeChunk=True)
            if seleccion:
                cmds.select([s for s in seleccion if cmds.objExists(s.split(".")[0])], replace=True)
            else:
                cmds.select(clear=True)
        return ruta

    def envios(self):
        return ic.envios_del_proyecto(self.proyecto())

    def aplicar_manifiesto(self, carpeta, opciones=None):
        """Conecta (o recarga) las texturas que Painter exportó. Devuelve lista de (material, entradas)."""
        manifiesto = ic.leer_manifiesto(carpeta)
        receta_envio = ic.leer_json(os.path.join(carpeta, ic.RECETA)) or {}
        if not manifiesto:
            return []
        opciones = dict(opciones or {})
        opciones.setdefault("normal", receta_envio.get("normal", "opengl"))
        nombres = receta_envio.get("materiales") or {}
        destino = receta_envio.get("destino", rc.RENDER)
        existentes = cmds.ls(type=TIPO) or []
        resultado = []
        for juego, rutas in manifiesto["juegos"].items():
            material = nombres.get(juego)
            if not material or not cmds.objExists(material):
                material = tx.buscar_material(juego, existentes)
            if not material:
                receta = (receta_envio.get("juegos") or {}).get(juego) or rc.nueva(nombre=juego)
                material = self.crear_material(receta, destino, nombre=juego)
                existentes.append(material)
            grupos = tx.analizar(rutas, normal_por_defecto=opciones["normal"])
            conexiones = []
            for g in grupos.values():
                conexiones.extend(c.como_dict() for c in g.conexiones.values())
            hechas = self.conectar_texturas(material, conexiones, opciones)
            self.recargar_texturas(material)
            resultado.append((material, hechas))
        return resultado

    def abrir_painter(self, ruta_preferida=""):
        """Intenta abrir Substance 3D Painter. Devuelve True si se lanzó."""
        candidatos = [ruta_preferida] if ruta_preferida else []
        try:
            if sys.platform == "darwin":
                if ruta_preferida:
                    subprocess.Popen(["open", "-a", ruta_preferida])
                    return True
                for carpeta in ("/Applications",):
                    if os.path.isdir(carpeta):
                        for nombre in sorted(os.listdir(carpeta), reverse=True):
                            if "Substance 3D Painter" in nombre:
                                ruta = os.path.join(carpeta, nombre)
                                app = ruta if ruta.endswith(".app") else os.path.join(
                                    ruta, "Adobe Substance 3D Painter.app")
                                subprocess.Popen(["open", "-a", app if os.path.exists(app) else ruta])
                                return True
                subprocess.Popen(["open", "-a", "Adobe Substance 3D Painter"])
                return True
            if sys.platform.startswith("win"):
                for base in (os.environ.get("ProgramFiles", r"C:\Program Files"),):
                    candidatos.append(os.path.join(base, "Adobe", "Adobe Substance 3D Painter",
                                                   "Adobe Substance 3D Painter.exe"))
                for ruta in candidatos:
                    if ruta and os.path.isfile(ruta):
                        subprocess.Popen([ruta])
                        return True
        except OSError:
            return False
        return False


class _Bloque(object):
    """Agrupa varias órdenes en un solo paso de deshacer."""

    def __init__(self, nombre):
        self.nombre = nombre

    def __enter__(self):
        cmds.undoInfo(openChunk=True, chunkName=self.nombre)
        return self

    def __exit__(self, *_):
        cmds.undoInfo(closeChunk=True)
        return False
