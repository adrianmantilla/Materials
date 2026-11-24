"""Une Muestrario con Maya: menú, panel acoplable, órdenes para atajos y avisos de escena."""

import os

from maya import cmds

import muestrario
from muestrario.ajustes import Ajustes
from muestrario.i18n import t
from muestrario.qt import QtWidgets, destruir, shiboken, sigue_vivo

CONTROL = "MuestrarioWorkspaceControl"
MENU = "MuestrarioMenu"
COMANDOS = {
    "MuestrarioAbrir": ("cmd_abrir", "alternar()"),
    "MuestrarioAsignar": ("cmd_asignar", "asignar()"),
    "MuestrarioCuentagotas": ("cmd_cuentagotas", "cuentagotas()"),
    "MuestrarioEnviarPainter": ("cmd_enviar", "enviar_a_painter()"),
}

_estado = {"ventana": None, "ajustes": None, "servicios": None, "trabajos": []}


def carpeta_preferencias():
    return os.path.join(cmds.internalVar(userAppDir=True), "muestrario")


def ajustes():
    if _estado["ajustes"] is None:
        _estado["ajustes"] = Ajustes(carpeta_preferencias())
    return _estado["ajustes"]


def servicios():
    if _estado["servicios"] is None:
        from muestrario.escena_maya import ServiciosMaya
        _estado["servicios"] = ServiciosMaya()
    return _estado["servicios"]


def ventana():
    v = _estado["ventana"]
    return v if sigue_vivo(v) else None


def _crear_ventana():
    from muestrario.ventana import VentanaMuestrario
    v = VentanaMuestrario(servicios=servicios(), ajustes=ajustes(), carpeta_preferencias=carpeta_preferencias())
    _estado["ventana"] = v
    return v


def restaurar():
    """Maya lo llama al crear (o recuperar) el panel: mete la ventana dentro."""
    from maya import OpenMayaUI as omui
    puntero = omui.MQtUtil.getCurrentParent()
    padre = shiboken.wrapInstance(int(puntero), QtWidgets.QWidget)
    v = ventana() or _crear_ventana()
    padre.layout().addWidget(v)


def mostrar():
    if not servicios().openpbr_disponible():
        cmds.warning(t("sin_openpbr"))
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.workspaceControl(CONTROL, edit=True, restore=True, visible=True)
        if ventana() is None:
            cmds.deleteUI(CONTROL)
        else:
            return ventana()
    cmds.workspaceControl(CONTROL, label="Muestrario", retain=False, floating=True, initialWidth=900,
                          initialHeight=640, minimumWidth=420,
                          uiScript="import muestrario.interfaz_maya as m\nm.restaurar()",
                          closeCommand="import muestrario.interfaz_maya as m\nm.al_cerrar()")
    return ventana()


def alternar():
    if cmds.workspaceControl(CONTROL, exists=True) and cmds.workspaceControl(CONTROL, query=True, visible=True):
        cmds.workspaceControl(CONTROL, edit=True, visible=False)
    else:
        mostrar()


def al_cerrar():
    v = ventana()
    if v is not None:
        v.cerrar()
    _estado["ventana"] = None


def asignar():
    v = ventana() or mostrar()
    if v is not None:
        v.asignar()


def cuentagotas():
    v = ventana() or mostrar()
    if v is not None:
        v.cuentagotas()


def enviar_a_painter():
    v = ventana() or mostrar()
    if v is not None:
        v.pestanas.setCurrentIndex(3)
        v.enviar_a_painter()


def _al_cambiar_escena():
    v = ventana()
    if v is not None:
        v.al_cambiar_escena()


def _crear_ordenes():
    for nombre, (clave, llamada) in COMANDOS.items():
        codigo = "import muestrario.interfaz_maya as m\nm.{}".format(llamada)
        if cmds.runTimeCommand(nombre, exists=True):
            cmds.runTimeCommand(nombre, edit=True, command=codigo, commandLanguage="python", annotation=t(clave))
        else:
            cmds.runTimeCommand(nombre, command=codigo, commandLanguage="python", annotation=t(clave),
                                category="Custom Scripts.Muestrario")


def _crear_menu():
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU)
    cmds.menu(MENU, label="Muestrario", parent="MayaWindow", tearOff=True)
    cmds.menuItem(label=t("menu_abrir"), command=lambda *_: mostrar(), annotation=t("cmd_abrir"))
    cmds.menuItem(label=t("menu_asignar"), command=lambda *_: asignar())
    cmds.menuItem(label=t("menu_cuentagotas"), command=lambda *_: cuentagotas())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_enviar"), command=lambda *_: enviar_a_painter())
    cmds.menuItem(divider=True)
    cmds.menuItem(label=t("menu_acerca", version=muestrario.__version__), enable=False)


def iniciar():
    _crear_ordenes()
    if cmds.about(batch=True):
        return
    _crear_menu()
    _estado["trabajos"] = [
        cmds.scriptJob(event=["SceneOpened", _al_cambiar_escena]),
        cmds.scriptJob(event=["NewSceneOpened", _al_cambiar_escena]),
        cmds.scriptJob(event=["workspaceChanged", _al_cambiar_escena]),
    ]


def detener():
    for trabajo in _estado["trabajos"]:
        if cmds.scriptJob(exists=trabajo):
            cmds.scriptJob(kill=trabajo, force=True)
    _estado["trabajos"] = []
    v = ventana()
    if v is not None:
        v.cerrar()
    if cmds.workspaceControl(CONTROL, exists=True):
        cmds.deleteUI(CONTROL)
    if v is not None:
        destruir(v)
    _estado["ventana"] = None
    if cmds.menu(MENU, exists=True):
        cmds.deleteUI(MENU)
