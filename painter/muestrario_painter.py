"""Muestrario para Substance 3D Painter: recibe objetos de Maya y le devuelve las texturas.

Se instala solo al instalar Muestrario en Maya (o copiándolo a mano en la carpeta
``Documentos/Adobe/Adobe Substance 3D Painter/python/plugins``). En Painter se
activa en el menú Python ▸ muestrario_painter. Añade un panel «Muestrario».

Cómo funciona (ver ``scripts/muestrario/intercambio.py`` en Maya):
1. Maya deja un aviso en ``Documentos/Muestrario/buzon``. El panel lo muestra.
2. «Abrir» crea un proyecto con la malla, con una capa de relleno por juego de
   texturas con los valores de Maya, y lo guarda junto a la malla.
3. «Exportar a Maya» exporta con la plantilla del destino (Arnold, Unreal,
   Unity o glTF) a la carpeta ``texturas`` y escribe ``manifiesto.json``.
   Maya lo ve y conecta o recarga las texturas solo.
   Si exportas con la ventana normal de Painter, el manifiesto se escribe igual.

No abre puertos de red ni necesita nada instalado aparte de Painter.
"""

import datetime
import json
import os
import time
import traceback

import substance_painter as sp

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # pragma: no cover - Painter antiguo
    from PySide2 import QtCore, QtWidgets

VERSION = "1.0.0"
METADATOS = "muestrario"
_estado = {"panel": None, "temporizador": None, "pendiente": None, "conectado": False}

TEXTOS = {
    "titulo": "Muestrario",
    "sin_avisos": "No hay envíos de Maya. En Maya: Muestrario ▸ Painter ▸ Enviar a Painter.",
    "abrir": "Abrir",
    "descartar": "Descartar",
    "exportar": "Exportar a Maya",
    "enlazado": "Proyecto enlazado con Maya: {objeto} ({destino}, {motor}, {res} px)",
    "no_enlazado": "Este proyecto no viene de Maya. Abre un envío de la lista.",
    "proyecto_abierto": "Hay un proyecto abierto. Guárdalo y ciérralo antes de abrir otro envío.",
    "abriendo": "Abriendo {objeto}…",
    "listo": "Listo: {n} juegos de texturas con los valores de Maya.",
    "exportando": "Exportando…",
    "exportado": "Exportadas {n} texturas. Maya las conectará en unos segundos.",
    "error": "Error: {e}",
    "falta_malla": "No se encuentra la malla {ruta}.",
    "envios": "Envíos desde Maya",
    "malla_nueva": "Maya ha enviado una malla nueva de este objeto.",
    "recargar_malla": "Recargar malla (conserva las capas)",
    "malla_recargada": "Malla recargada.",
}


def tr(clave, **v):
    texto = TEXTOS.get(clave, clave)
    try:
        return texto.format(**v)
    except (KeyError, IndexError):
        return texto


def _log(texto):
    try:
        sp.logging.info("Muestrario: " + texto)
    except Exception:
        print("Muestrario: " + texto)


# --- Archivos compartidos con Maya -------------------------------------------------------

def carpeta_buzon():
    base = os.environ.get("MUESTRARIO_CASA") or os.path.join(os.path.expanduser("~"), "Documents", "Muestrario")
    return os.path.join(base, "buzon")


def leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else None
    except (OSError, ValueError):
        return None


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)


def avisos():
    carpeta = carpeta_buzon()
    if not os.path.isdir(carpeta):
        return []
    salida = []
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.endswith(".json"):
            ruta = os.path.join(carpeta, nombre)
            datos = leer_json(ruta)
            if datos and datos.get("receta") and os.path.isfile(datos["receta"]):
                datos["_ruta"] = ruta
                salida.append(datos)
            elif datos:
                _quitar(ruta)
    return salida


def _quitar(ruta):
    try:
        os.remove(ruta)
    except OSError:
        pass


def escribir_manifiesto(carpeta, texturas_por_juego):
    ruta = os.path.join(carpeta, "manifiesto.json")
    anterior = leer_json(ruta) or {}
    datos = {
        "version": 1,
        "exportado": datetime.datetime.now().replace(microsecond=0).isoformat(),
        "contador": int(anterior.get("contador", 0)) + 1,
        "juegos": {j: [os.path.abspath(r) for r in rutas] for j, rutas in texturas_por_juego.items()},
    }
    escribir_json(ruta, datos)
    return datos


# --- Color ------------------------------------------------------------------------------------

def _hex_a_srgb(texto):
    try:
        return tuple(int(texto[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    except (TypeError, ValueError):
        return (0.8, 0.8, 0.8)


def _a_lineal(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# --- Plantillas de exportación ---------------------------------------------------------------

def _canal(dest, src, tipo, nombre):
    return {"destChannel": dest, "srcChannel": src, "srcMapType": tipo, "srcMapName": nombre}


def _rgb(nombre, tipo="documentMap"):
    return [_canal(c, c, tipo, nombre) for c in "RGB"]


def _gris(nombre, tipo="documentMap", dest="L"):
    return [_canal(dest, "L", tipo, nombre)]


def _mapa(sufijo, canales, bits="8", formato="png"):
    return {"fileName": "$textureSet_" + sufijo + "(.$udim)", "channels": canales,
            "parameters": {"fileFormat": formato, "bitDepth": bits, "dithering": bits == "8"}}


def plantilla(motor, receta_juego=None):
    """Mapas que se exportan para cada destino. Los nombres los reconoce Muestrario en Maya."""
    emision = _mapa("Emissive", _rgb("emissive"))
    opacidad = _mapa("Opacity", _gris("opacity"))
    if motor == "unreal":
        mapas = [_mapa("BaseColor", _rgb("basecolor")),
                 _mapa("OcclusionRoughnessMetallic", [_canal("R", "L", "virtualMap", "AO_Mixed"),
                                                      _canal("G", "L", "documentMap", "roughness"),
                                                      _canal("B", "L", "documentMap", "metallic")]),
                 _mapa("Normal_DirectX", _rgb("Normal_DirectX", "virtualMap"))]
    elif motor == "unity":
        mapas = [_mapa("BaseMap", _rgb("basecolor") + [_canal("A", "L", "documentMap", "opacity")]),
                 _mapa("MaskMap", [_canal("R", "L", "documentMap", "metallic"),
                                   _canal("G", "L", "virtualMap", "AO_Mixed"),
                                   _canal("A", "L", "virtualMap", "Glossiness")]),
                 _mapa("Normal_OpenGL", _rgb("Normal_OpenGL", "virtualMap"))]
        opacidad = None
    elif motor == "gltf":
        mapas = [_mapa("BaseColor", _rgb("basecolor")),
                 _mapa("OcclusionRoughnessMetallic", [_canal("R", "L", "virtualMap", "AO_Mixed"),
                                                      _canal("G", "L", "documentMap", "roughness"),
                                                      _canal("B", "L", "documentMap", "metallic")]),
                 _mapa("Normal_OpenGL", _rgb("Normal_OpenGL", "virtualMap"))]
    else:  # arnold
        mapas = [_mapa("BaseColor", _rgb("basecolor")),
                 _mapa("Roughness", _gris("roughness")),
                 _mapa("Metallic", _gris("metallic")),
                 _mapa("Normal_OpenGL", _rgb("Normal_OpenGL", "virtualMap")),
                 _mapa("Height", _gris("height"), bits="16")]
    receta_juego = receta_juego or {}
    if receta_juego.get("emision", 0) > 0 or motor == "arnold":
        mapas.append(emision)
    if opacidad and (receta_juego.get("opacidad", 1.0) < 1.0 or motor == "arnold"):
        mapas.append(opacidad)
    return mapas


# --- Proyecto ---------------------------------------------------------------------------------

def receta_enlazada():
    """Ruta de receta.json del proyecto abierto, o None."""
    try:
        if not sp.project.is_open():
            return None
        ruta = sp.project.Metadata(METADATOS).get("receta")
        return ruta if ruta and os.path.isfile(ruta) else None
    except Exception:
        return None


def abrir_envio(aviso, al_terminar=None):
    ruta_receta = aviso["receta"]
    receta = leer_json(ruta_receta) or {}
    carpeta = os.path.dirname(ruta_receta)
    malla = os.path.join(carpeta, receta.get("malla", ""))
    if not os.path.isfile(malla):
        raise RuntimeError(tr("falta_malla", ruta=malla))
    if sp.project.is_open():
        raise RuntimeError(tr("proyecto_abierto"))
    ajustes = {}
    try:
        formato = sp.project.NormalMapFormat.DirectX if receta.get("normal") == "directx" else \
            sp.project.NormalMapFormat.OpenGL
        ajustes["normal_map_format"] = formato
    except AttributeError:
        pass
    ajustes["default_texture_resolution"] = int(receta.get("resolucion", 2048))
    try:
        configuracion = sp.project.Settings(import_cameras=False, **ajustes)
    except TypeError:
        configuracion = sp.project.Settings(**{k: v for k, v in ajustes.items() if k == "normal_map_format"})
    sp.project.create(mesh_file_path=malla, settings=configuracion)
    _estado["pendiente"] = {"malla": malla, "receta": receta, "ruta_receta": ruta_receta, "aviso": aviso.get("_ruta"),
                            "inicio": time.time(), "al_terminar": al_terminar}


def _preparar_cuando_cargue():
    """Se llama con el temporizador hasta que el proyecto nuevo está listo."""
    pendiente = _estado["pendiente"]
    if not pendiente:
        return
    if time.time() - pendiente["inicio"] > 300:
        _estado["pendiente"] = None
        return
    try:
        if not sp.project.is_open() or sp.project.is_busy():
            return
        conjuntos = sp.textureset.all_texture_sets()
    except Exception:
        return
    if not conjuntos:
        return
    _estado["pendiente"] = None
    receta = pendiente["receta"]
    n = 0
    try:
        datos = sp.project.Metadata(METADATOS)
        datos.set("receta", pendiente["ruta_receta"])
        datos.set("malla_mtime", _mtime(pendiente["malla"]))
        juegos = receta.get("juegos") or {}
        for conjunto in conjuntos:
            valores = juegos.get(conjunto.name())
            if valores is None and len(juegos) == 1 and len(conjuntos) == 1:
                valores = list(juegos.values())[0]
            if valores:
                _capa_base(conjunto, valores)
                n += 1
        carpeta = os.path.dirname(pendiente["ruta_receta"])
        destino_spp = os.path.join(carpeta, receta.get("objeto", "objeto") + ".spp")
        try:
            sp.project.save_as(destino_spp)
        except Exception as error:  # guardar no es imprescindible
            _log("no se pudo guardar el proyecto: {}".format(error))
        if pendiente.get("aviso"):
            _quitar(pendiente["aviso"])
        mensaje = tr("listo", n=n)
    except Exception as error:
        _log(traceback.format_exc())
        mensaje = tr("error", e=error)
    if pendiente.get("al_terminar"):
        pendiente["al_terminar"](mensaje)


def _poner(capa, canal, valor):
    """Pone un valor uniforme en un canal de la capa de relleno, probando las formas del API."""
    Color = sp.colormanagement.Color
    intentos = []
    if isinstance(valor, tuple):
        intentos = [lambda: capa.set_source(canal, Color(*valor))]
    else:
        intentos = [lambda: capa.set_source(canal, float(valor)),
                    lambda: capa.set_source(canal, Color(valor, valor, valor))]
    for intento in intentos:
        try:
            intento()
            return True
        except Exception:
            continue
    _log("no se pudo poner el canal {}".format(canal))
    return False


def _capa_base(conjunto, valores):
    ls = sp.layerstack
    pila = conjunto.get_stack()
    CT = sp.textureset.ChannelType
    canales_pila = set(pila.all_channels().keys()) if hasattr(pila, "all_channels") else set()
    if valores.get("emision", 0) > 0 and CT.Emissive not in canales_pila:
        try:
            pila.add_channel(CT.Emissive, sp.textureset.ChannelFormat.sRGB8)
        except Exception:
            pass
    if valores.get("opacidad", 1.0) < 1.0 and CT.Opacity not in canales_pila:
        try:
            pila.add_channel(CT.Opacity, sp.textureset.ChannelFormat.L8)
        except Exception:
            pass
    capa = ls.insert_fill(ls.InsertPosition.from_textureset_stack(pila))
    capa.set_name("Maya · " + str(valores.get("nombre", "base")))
    color = _hex_a_srgb(valores.get("color", "#cccccc"))
    color_lineal = tuple(_a_lineal(c) for c in color)
    activos = {CT.BaseColor, CT.Roughness, CT.Metallic}
    _poner(capa, CT.BaseColor, color_lineal)
    _poner(capa, CT.Roughness, float(valores.get("rugosidad", 0.5)))
    _poner(capa, CT.Metallic, float(valores.get("metal", 0.0)))
    if valores.get("emision", 0) > 0:
        emision = valores.get("color_emision") or valores.get("color", "#ffffff")
        _poner(capa, CT.Emissive, tuple(_a_lineal(c) for c in _hex_a_srgb(emision)))
        activos.add(CT.Emissive)
    if valores.get("opacidad", 1.0) < 1.0:
        _poner(capa, CT.Opacity, float(valores["opacidad"]))
        activos.add(CT.Opacity)
    try:
        capa.active_channels = activos
    except Exception:
        pass


def _mtime(ruta):
    try:
        return int(os.path.getmtime(ruta))
    except OSError:
        return 0


def malla_cambiada():
    """Ruta de la malla si Maya la ha vuelto a exportar después de abrir el proyecto."""
    ruta_receta = receta_enlazada()
    if not ruta_receta:
        return None
    receta = leer_json(ruta_receta) or {}
    malla = os.path.join(os.path.dirname(ruta_receta), receta.get("malla", ""))
    try:
        guardado = int(sp.project.Metadata(METADATOS).get("malla_mtime") or 0)
    except Exception:
        return None
    return malla if os.path.isfile(malla) and _mtime(malla) > guardado else None


def recargar_malla(al_terminar=None):
    malla = malla_cambiada()
    if not malla:
        return

    def _fin(estado):
        try:
            sp.project.Metadata(METADATOS).set("malla_mtime", _mtime(malla))
        except Exception:
            pass
        if al_terminar:
            al_terminar(tr("malla_recargada"))
    try:
        ajustes = sp.project.MeshReloadingSettings(import_cameras=False, preserve_strokes=True)
    except Exception:
        ajustes = sp.project.MeshReloadingSettings()
    sp.project.reload_mesh(malla, ajustes, _fin)


def exportar_a_maya():
    ruta_receta = receta_enlazada()
    if not ruta_receta:
        raise RuntimeError(tr("no_enlazado"))
    receta = leer_json(ruta_receta) or {}
    carpeta = os.path.dirname(ruta_receta)
    destino = os.path.join(carpeta, receta.get("texturas", "texturas"))
    os.makedirs(destino, exist_ok=True)
    motor = receta.get("motor", "arnold")
    juegos = receta.get("juegos") or {}
    tam = int(receta.get("resolucion", 2048))
    tamano_log2 = max(7, min(13, tam.bit_length() - 1))
    presets, lista = [], []
    for conjunto in sp.textureset.all_texture_sets():
        nombre = conjunto.name()
        preset = "muestrario_" + nombre
        presets.append({"name": preset, "maps": plantilla(motor, juegos.get(nombre))})
        lista.append({"rootPath": nombre, "exportPreset": preset})
    configuracion = {
        "exportShaderParams": False,
        "exportPath": destino,
        "defaultExportPreset": presets[0]["name"] if presets else "",
        "exportPresets": presets,
        "exportList": lista,
        "exportParameters": [{"parameters": {"sizeLog2": tamano_log2, "paddingAlgorithm": "infinite"}}],
    }
    _estado["exportando_nosotros"] = True
    try:
        resultado = sp.export.export_project_textures(configuracion)
    finally:
        _estado["exportando_nosotros"] = False
    texturas = _texturas_de(resultado)
    escribir_manifiesto(carpeta, texturas)
    return sum(len(v) for v in texturas.values())


def _texturas_de(resultado):
    salida = {}
    for clave, rutas in (getattr(resultado, "textures", None) or {}).items():
        juego = clave[0] if isinstance(clave, tuple) else str(clave)
        salida.setdefault(juego, []).extend(rutas)
    return salida


def _al_exportar(evento):
    """Exportación hecha con la ventana normal de Painter: también se avisa a Maya."""
    if _estado.get("exportando_nosotros"):
        return
    ruta_receta = receta_enlazada()
    if not ruta_receta:
        return
    texturas = _texturas_de(evento)
    if texturas:
        escribir_manifiesto(os.path.dirname(ruta_receta), texturas)
        _log("manifiesto escrito para Maya ({} juegos)".format(len(texturas)))


# --- Panel ------------------------------------------------------------------------------------

class Panel(QtWidgets.QWidget):
    def __init__(self):
        super(Panel, self).__init__()
        self.setObjectName("MuestrarioPanel")
        self.setWindowTitle(tr("titulo"))
        capa = QtWidgets.QVBoxLayout(self)
        self.estado = QtWidgets.QLabel()
        self.estado.setWordWrap(True)
        capa.addWidget(self.estado)
        self.boton_exportar = QtWidgets.QPushButton(tr("exportar"))
        self.boton_exportar.clicked.connect(self._exportar)
        capa.addWidget(self.boton_exportar)
        self.aviso_malla = QtWidgets.QLabel(tr("malla_nueva"))
        self.aviso_malla.setWordWrap(True)
        self.boton_malla = QtWidgets.QPushButton(tr("recargar_malla"))
        self.boton_malla.clicked.connect(self._recargar_malla)
        capa.addWidget(self.aviso_malla)
        capa.addWidget(self.boton_malla)
        capa.addWidget(QtWidgets.QLabel("<b>{}</b>".format(tr("envios"))))
        self.lista = QtWidgets.QVBoxLayout()
        capa.addLayout(self.lista)
        capa.addStretch(1)
        self.mensaje = QtWidgets.QLabel()
        self.mensaje.setWordWrap(True)
        capa.addWidget(self.mensaje)
        self._firma = None
        self.refrescar()

    def refrescar(self):
        ruta = receta_enlazada()
        if ruta:
            r = leer_json(ruta) or {}
            self.estado.setText(tr("enlazado", objeto=r.get("objeto", "?"), destino=r.get("destino", "render"),
                                   motor=r.get("motor", "arnold"), res=r.get("resolucion", 2048)))
        else:
            self.estado.setText(tr("no_enlazado"))
        self.boton_exportar.setEnabled(bool(ruta))
        nueva = bool(ruta) and bool(malla_cambiada())
        self.aviso_malla.setVisible(nueva)
        self.boton_malla.setVisible(nueva)
        lista = avisos()
        firma = tuple(a.get("_ruta") for a in lista)
        if firma == self._firma:
            return
        self._firma = firma
        while self.lista.count():
            item = self.lista.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not lista:
            vacio = QtWidgets.QLabel(tr("sin_avisos"))
            vacio.setWordWrap(True)
            self.lista.addWidget(vacio)
        for aviso in lista:
            fila = QtWidgets.QWidget()
            h = QtWidgets.QHBoxLayout(fila)
            h.setContentsMargins(0, 0, 0, 0)
            h.addWidget(QtWidgets.QLabel("{} · {}".format(aviso.get("objeto", "?"), aviso.get("creado", "")[11:16])),
                        1)
            abrir = QtWidgets.QPushButton(tr("abrir"))
            abrir.clicked.connect(lambda _=False, a=aviso: self._abrir(a))
            descartar = QtWidgets.QPushButton(tr("descartar"))
            descartar.clicked.connect(lambda _=False, a=aviso: (_quitar(a["_ruta"]), self.refrescar()))
            h.addWidget(abrir)
            h.addWidget(descartar)
            self.lista.addWidget(fila)

    def _abrir(self, aviso):
        try:
            self.mensaje.setText(tr("abriendo", objeto=aviso.get("objeto", "")))
            abrir_envio(aviso, al_terminar=self._terminado)
        except Exception as error:
            self.mensaje.setText(tr("error", e=error))

    def _terminado(self, mensaje):
        self.mensaje.setText(mensaje)
        self._firma = None
        self.refrescar()

    def _recargar_malla(self):
        try:
            recargar_malla(al_terminar=self._terminado)
        except Exception as error:
            _log(traceback.format_exc())
            self.mensaje.setText(tr("error", e=error))

    def _exportar(self):
        try:
            self.mensaje.setText(tr("exportando"))
            QtWidgets.QApplication.processEvents()
            n = exportar_a_maya()
            self.mensaje.setText(tr("exportado", n=n))
        except Exception as error:
            _log(traceback.format_exc())
            self.mensaje.setText(tr("error", e=error))


def _tic():
    try:
        _preparar_cuando_cargue()
        panel = _estado["panel"]
        if panel is not None:
            panel.refrescar()
    except Exception:
        _log(traceback.format_exc())


def start_plugin():
    panel = Panel()
    _estado["panel"] = panel
    try:
        sp.ui.add_dock_widget(panel)
    except Exception:
        _log(traceback.format_exc())
    temporizador = QtCore.QTimer()
    temporizador.setInterval(1500)
    temporizador.timeout.connect(_tic)
    temporizador.start()
    _estado["temporizador"] = temporizador
    try:
        sp.event.DISPATCHER.connect(sp.event.ExportTexturesEnded, _al_exportar)
        _estado["conectado"] = True
    except Exception:
        _log(traceback.format_exc())
    _log("plugin {} cargado; buzón en {}".format(VERSION, carpeta_buzon()))


def close_plugin():
    if _estado["temporizador"] is not None:
        _estado["temporizador"].stop()
        _estado["temporizador"] = None
    if _estado["conectado"]:
        try:
            sp.event.DISPATCHER.disconnect(sp.event.ExportTexturesEnded, _al_exportar)
        except Exception:
            pass
        _estado["conectado"] = False
    if _estado["panel"] is not None:
        try:
            sp.ui.delete_ui_element(_estado["panel"])
        except Exception:
            pass
        _estado["panel"] = None


if __name__ == "__main__":
    start_plugin()
