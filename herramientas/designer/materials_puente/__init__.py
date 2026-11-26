"""Puente de la fábrica de motivos para Adobe Substance 3D Designer.

Complemento de Python para Designer. Mientras está activo, ejecuta dentro de
Designer los scripts que aparecen en

    ~/Documents/DEV/tilingtextures_fabrica/designer/entrada

uno a uno y por orden de nombre, y deja lo que escriben en ``salida``. Así se
crean por script los grafos de los motivos (estructuras y acabados) sin tocar la
interfaz de Designer. Solo mira esa carpeta y no usa la red.

Instalación: copiar la carpeta ``materials_puente`` en la carpeta de complementos
de usuario de Designer (``~/Documents/Adobe/Adobe Substance 3D Designer/python/
sduserplugins``) y reiniciar Designer; se activa solo. Se quita desactivándolo en
Tools > Plugin Manager o borrando la carpeta.

Protocolo (el mismo que el puente de Painter de Trepadora)
---------------------------------------------------------
* Un script nuevo se escribe con otro nombre y se renombra a ``*.py`` al
  terminar, para que el puente nunca lea un archivo a medias.
* Antes de ejecutarlo, el puente lo mueve a ``hechos``: no se ejecuta dos veces.
* Lo que el script imprime va a ``salida/<nombre>.log``. Al acabar se escribe
  ``salida/<nombre>.fin.json`` con el estado (ok, error, cancelado o tiempo).
* Si el script define ``pasos()`` como generador, el puente lo avanza en cada
  tic (un paso por tic) sin bloquear Designer. ``TIEMPO_MAX`` (segundos) limita
  cuánto puede durar; por defecto, 30 minutos.
* Un archivo ``entrada/CANCELAR`` detiene el script en curso.
* ``salida/latido.json`` se renueva cada pocos segundos mientras el puente está
  activo.
* ``lib`` se añade a ``sys.path`` para que los scripts compartan código.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import time
import traceback

try:
    from PySide6 import QtCore
except ImportError:  # Designer antiguo
    from PySide2 import QtCore

CARPETA = os.path.join(os.path.expanduser("~"), "Documents", "DEV", "tilingtextures_fabrica", "designer")
INTERVALO_MS = 300
LATIDO_S = 3.0
TIEMPO_MAX_S = 30 * 60

_estado = {"temporizador": None, "tarea": None, "latido": 0.0, "carpeta": CARPETA}


def _registro():
    try:
        import sd
        return sd.getContext().getLogger()
    except Exception:  # fuera de Designer (pruebas)
        return None


def _ruta(*partes):
    return os.path.join(_estado["carpeta"], *partes)


def _avisar(texto, error=False):
    registro = _registro()
    if registro is not None:
        try:
            (registro.error if error else registro.info)("[materials_puente] " + texto)
            return
        except Exception:
            pass
    sys.__stdout__.write("[materials_puente] " + texto + "\n")


def _escribir_json(ruta, datos):
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    os.replace(temporal, ruta)


class _Tarea(object):
    def __init__(self, nombre, ruta):
        self.nombre = nombre
        self.ruta = ruta
        self.inicio = time.time()
        self.texto = io.StringIO()
        self.pasos = None
        self.tiempo_max = TIEMPO_MAX_S
        self.escrito = 0

    def volcar(self):
        """Añade al .log lo nuevo que haya escrito el script."""
        texto = self.texto.getvalue()
        if len(texto) > self.escrito:
            with open(_ruta("salida", self.nombre + ".log"), "a", encoding="utf-8") as f:
                f.write(texto[self.escrito:])
            self.escrito = len(texto)

    @contextlib.contextmanager
    def capturando(self):
        with contextlib.redirect_stdout(self.texto), contextlib.redirect_stderr(self.texto):
            yield


def _terminar(tarea, estado):
    tarea.volcar()
    _escribir_json(_ruta("salida", tarea.nombre + ".fin.json"),
                   {"estado": estado, "segundos": round(time.time() - tarea.inicio, 2)})
    _avisar("{}: {}".format(tarea.nombre, estado), error=(estado != "ok"))
    _estado["tarea"] = None


def _empezar(archivo):
    nombre = os.path.splitext(archivo)[0]
    ruta = _ruta("hechos", archivo)
    if os.path.exists(ruta):
        ruta = _ruta("hechos", "{}_{}.py".format(nombre, int(time.time())))
    shutil.move(_ruta("entrada", archivo), ruta)
    for viejo in (_ruta("salida", nombre + ".log"), _ruta("salida", nombre + ".fin.json")):
        if os.path.exists(viejo):
            os.remove(viejo)
    tarea = _Tarea(nombre, ruta)
    _estado["tarea"] = tarea
    _avisar("ejecuto " + archivo)
    espacio = {"__name__": "__materials_puente__", "__file__": ruta, "CARPETA": _estado["carpeta"]}
    try:
        with open(ruta, encoding="utf-8") as f:
            codigo = compile(f.read(), ruta, "exec")
        with tarea.capturando():
            exec(codigo, espacio)
            tarea.tiempo_max = float(espacio.get("TIEMPO_MAX", TIEMPO_MAX_S))
            pasos = espacio.get("pasos")
            if callable(pasos):
                tarea.pasos = pasos()
    except BaseException:  # la API de Designer lanza excepciones que no heredan de Exception
        tarea.texto.write(traceback.format_exc())
        _terminar(tarea, "error")
        return
    if tarea.pasos is None:
        _terminar(tarea, "ok")
    else:
        tarea.volcar()


def _avanzar(tarea):
    cancelar = _ruta("entrada", "CANCELAR")
    if os.path.exists(cancelar):
        os.remove(cancelar)
        tarea.texto.write("\n[cancelado]\n")
        _terminar(tarea, "cancelado")
        return
    if time.time() - tarea.inicio > tarea.tiempo_max:
        tarea.texto.write("\n[tiempo agotado: {} s]\n".format(tarea.tiempo_max))
        _terminar(tarea, "tiempo")
        return
    try:
        with tarea.capturando():
            next(tarea.pasos)
    except StopIteration:
        _terminar(tarea, "ok")
        return
    except BaseException:  # la API de Designer lanza excepciones que no heredan de Exception
        tarea.texto.write(traceback.format_exc())
        _terminar(tarea, "error")
        return
    tarea.volcar()


def _latir():
    ahora = time.time()
    if ahora - _estado["latido"] < LATIDO_S:
        return
    _estado["latido"] = ahora
    tarea = _estado["tarea"]
    _escribir_json(_ruta("salida", "latido.json"),
                   {"hora": time.strftime("%Y-%m-%d %H:%M:%S"), "epoca": round(ahora, 1),
                    "ocupado": tarea.nombre if tarea else None, "pid": os.getpid()})


def _tic():
    try:
        _latir()
        tarea = _estado["tarea"]
        if tarea is not None:
            _avanzar(tarea)
            return
        pendientes = sorted(f for f in os.listdir(_ruta("entrada"))
                            if f.endswith(".py") and not f.startswith("."))
        if pendientes:
            _empezar(pendientes[0])
    except Exception:
        _avisar(traceback.format_exc(), error=True)


def empezar(carpeta=None):
    parar()
    _estado["carpeta"] = carpeta or CARPETA
    for sub in ("entrada", "salida", "hechos", "lib"):
        os.makedirs(_ruta(sub), exist_ok=True)
    lib = _ruta("lib")
    if lib not in sys.path:
        sys.path.insert(0, lib)
    temporizador = QtCore.QTimer()
    temporizador.setInterval(INTERVALO_MS)
    temporizador.timeout.connect(_tic)
    temporizador.start()
    _estado["temporizador"] = temporizador
    _estado["latido"] = 0.0
    _avisar("activo; miro " + _ruta("entrada"))


def parar():
    temporizador = _estado["temporizador"]
    if temporizador is not None:
        temporizador.stop()
        _estado["temporizador"] = None
        tarea = _estado["tarea"]
        if tarea is not None:
            tarea.texto.write("\n[complemento desactivado]\n")
            _terminar(tarea, "cancelado")
        latido = _ruta("salida", "latido.json")
        if os.path.exists(latido):
            os.remove(latido)
        _avisar("desactivado")


def initializeSDPlugin():
    """Lo llama Designer al cargar el complemento."""
    empezar()


def uninitializeSDPlugin():
    """Lo llama Designer al descargar el complemento o al cerrarse."""
    parar()
