"""Puente de Designer: actualiza el repositorio y ejecuta en el Mac una lista de órdenes, una tras otra.

Se copia a ``designer/entrada`` con ``ORDENES`` rellenado. Cada orden es una lista de
argumentos; ``{R}`` es el repositorio, ``{B}`` la carpeta tilingtextures_fabrica, ``{V}`` el
Python del venv y ``{M}`` el mayapy de Maya 2027. No bloquea Designer: el puente avanza
un paso por tic mientras cada orden corre. La salida de cada orden va a
``<B>/registros/<n>_<nombre>.log`` y su final al log del puente.
"""

import os
import subprocess
import time

BASE = os.path.dirname(CARPETA)  # noqa: F821
REPO = os.path.join(BASE, "materials_prueba")
RAMA = "claude/project-thread-8kf6pd"
SUSTITUIR = {"{R}": REPO, "{B}": BASE, "{V}": os.path.join(BASE, "venv", "bin", "python"),
             "{M}": "/Applications/Autodesk/maya2027/Maya.app/Contents/bin/mayapy"}
ACTUALIZAR = True
ORDENES = []      # p. ej. [["{V}", "{R}/herramientas/designer/fabricar.py", ...]]
LINEAS_FINAL = 25
TIEMPO_MAX = 60 * 60


def _sustituir(arg):
    for k, v in SUSTITUIR.items():
        arg = arg.replace(k, v)
    return arg


def _correr(args, registro):
    entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    with open(registro, "w") as salida:
        proceso = subprocess.Popen(args, stdout=salida, stderr=subprocess.STDOUT, cwd=REPO, env=entorno)
        inicio = time.time()
        while proceso.poll() is None:
            yield
    with open(registro, encoding="utf-8", errors="replace") as f:
        lineas = f.read().splitlines()
    print("$", " ".join(args))
    print("  ->", proceso.returncode, "en", round(time.time() - inicio, 1), "s;", len(lineas), "líneas en", registro)
    print("\n".join("  | " + l for l in lineas[-LINEAS_FINAL:]))
    if proceso.returncode:
        raise RuntimeError("falló la orden: " + " ".join(args))


def pasos():
    carpeta = os.path.join(BASE, "registros")
    os.makedirs(carpeta, exist_ok=True)
    marca = time.strftime("%H%M%S")
    todas = []
    if ACTUALIZAR:
        todas += [["git", "-C", REPO, "fetch", "-q", "origin", RAMA],
                  ["git", "-C", REPO, "merge", "--ff-only", "FETCH_HEAD"],
                  ["git", "-C", REPO, "log", "--oneline", "-1"]]
    todas += [[_sustituir(a) for a in orden] for orden in ORDENES]
    for i, args in enumerate(todas):
        nombre = os.path.basename(args[1] if args[0].endswith(("python", "mayapy")) and len(args) > 1 else args[0])
        registro = os.path.join(carpeta, "{}_{:02d}_{}.log".format(marca, i, nombre.replace(".py", "")))
        for paso in _correr(args, registro):
            yield paso
