"""Plugin de Maya para Materials.

Aparece en el Plug-in Manager como «materials_plugin». Al cargarlo crea el menú
Materials y las órdenes para el Editor de atajos; al descargarlo lo quita todo.
"""

import maya.api.OpenMaya as om
from maya import cmds


def maya_useNewAPI():
    pass


def initializePlugin(objeto):
    import materials
    plugin = om.MFnPlugin(objeto, "Materials", materials.__version__, "Any")
    try:
        from materials import interfaz_maya
        cmds.evalDeferred(interfaz_maya.iniciar, lowestPriority=True)
    except Exception as error:
        cmds.warning("Materials no se pudo cargar: {}".format(error))
    return plugin


def uninitializePlugin(objeto):
    try:
        from materials import interfaz_maya
        interfaz_maya.detener()
    except Exception:
        pass
