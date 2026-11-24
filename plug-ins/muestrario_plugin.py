"""Plugin de Maya para Muestrario.

Aparece en el Plug-in Manager como «muestrario_plugin». Al cargarlo crea el menú
Muestrario y las órdenes para el Editor de atajos; al descargarlo lo quita todo.
"""

import maya.api.OpenMaya as om
from maya import cmds


def maya_useNewAPI():
    pass


def initializePlugin(objeto):
    import muestrario
    plugin = om.MFnPlugin(objeto, "Muestrario", muestrario.__version__, "Any")
    try:
        from muestrario import interfaz_maya
        cmds.evalDeferred(interfaz_maya.iniciar, lowestPriority=True)
    except Exception as error:
        cmds.warning("Muestrario no se pudo cargar: {}".format(error))
    return plugin


def uninitializePlugin(objeto):
    try:
        from muestrario import interfaz_maya
        interfaz_maya.detener()
    except Exception:
        pass
