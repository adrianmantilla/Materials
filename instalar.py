"""Instalador de Muestrario.

Arrastra este archivo desde el explorador de archivos hasta el visor de Maya.
- Crea el módulo «muestrario.mod» en tu carpeta de Maya apuntando a esta carpeta,
  carga el plugin y lo marca para que se cargue siempre.
- Copia el complemento de Substance 3D Painter a
  «Documentos/Adobe/Adobe Substance 3D Painter/python/plugins» (si Painter no está
  instalado no pasa nada: se puede copiar más tarde).
Para desinstalar, borra ese archivo .mod y «muestrario_painter.py» de la carpeta
de plugins de Painter (las rutas se muestran en el Script Editor al instalar).

No muevas la carpeta del plugin después de instalar; si lo haces, vuelve a
arrastrar este archivo.
"""

import os
import shutil
import sys

PLUGIN = "muestrario_plugin"


def _raiz():
    return os.path.dirname(os.path.abspath(__file__))


def contenido_mod(raiz, version):
    raiz = raiz.replace("\\", "/")
    return ("+ Muestrario {version} {raiz}\n"
            "scripts: scripts\n"
            "plug-ins: plug-ins\n").format(version=version, raiz=raiz)


def _version(raiz):
    ruta = os.path.join(raiz, "scripts", "muestrario", "__init__.py")
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("__version__"):
                return linea.split("=")[1].strip().strip("\"'")
    return "0.0.0"


def carpeta_plugins_painter():
    return os.path.join(os.path.expanduser("~"), "Documents", "Adobe", "Adobe Substance 3D Painter", "python",
                        "plugins")


def instalar_en_painter(raiz):
    """Copia el complemento de Painter. Devuelve la ruta o None si no se pudo."""
    origen = os.path.join(raiz, "painter", "muestrario_painter.py")
    destino = carpeta_plugins_painter()
    try:
        os.makedirs(destino, exist_ok=True)
        shutil.copy2(origen, os.path.join(destino, "muestrario_painter.py"))
        return os.path.join(destino, "muestrario_painter.py")
    except OSError as error:
        print("Muestrario | no se pudo copiar el complemento de Painter: {}".format(error))
        return None


def instalar():
    from maya import cmds

    raiz = _raiz()
    print("Muestrario | instalando desde " + raiz)
    version = _version(raiz)
    carpeta_modulos = os.path.join(cmds.internalVar(userAppDir=True), "modules")
    os.makedirs(carpeta_modulos, exist_ok=True)
    ruta_mod = os.path.join(carpeta_modulos, "muestrario.mod")
    with open(ruta_mod, "w", encoding="utf-8") as f:
        f.write(contenido_mod(raiz, version))
    print("Muestrario | módulo escrito en " + ruta_mod)
    ruta_painter = instalar_en_painter(raiz)
    if ruta_painter:
        print("Muestrario | complemento de Painter copiado en " + ruta_painter)

    scripts = os.path.join(raiz, "scripts")
    sys.path[:] = [p for p in sys.path
                   if os.path.normpath(p) == os.path.normpath(scripts)
                   or not os.path.isfile(os.path.join(p, "muestrario", "__init__.py"))]
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    for nombre in [m for m in sys.modules if m == "muestrario" or m.startswith("muestrario.")]:
        del sys.modules[nombre]

    ruta_plugin = os.path.join(raiz, "plug-ins", PLUGIN + ".py")
    if cmds.pluginInfo(PLUGIN, query=True, loaded=True):
        cmds.unloadPlugin(PLUGIN, force=True)
    cmds.loadPlugin(ruta_plugin)
    cmds.pluginInfo(PLUGIN, edit=True, autoload=True)

    from muestrario.i18n import t
    texto = t("instalado_texto", version=version)
    if ruta_painter:
        texto += "\n\n" + t("instalado_painter")
    cmds.confirmDialog(title=t("instalado_titulo"), message=texto, button=[t("boton_aceptar")])


def onMayaDroppedPythonFile(*_):
    """Maya llama a esta función al soltar el archivo en el visor."""
    try:
        instalar()
    except Exception as error:
        from maya import cmds
        cmds.confirmDialog(title="Muestrario", message="No se pudo instalar Muestrario: {}".format(error),
                           button=["OK"])
        raise
    finally:
        sys.modules.pop(__name__, None)
