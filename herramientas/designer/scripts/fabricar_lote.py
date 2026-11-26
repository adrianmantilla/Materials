"""Puente de Designer: actualiza el repositorio, monta los grafos y fabrica el lote, todo en el Mac.

Se copia a ``designer/entrada`` (con las variables de abajo ajustadas). Hace, por orden:

1. ``git fetch`` + ``git merge --ff-only`` de la rama en ``materials_prueba``.
2. Copia ``herramientas/designer/lib/*.py`` a ``designer/lib``.
3. Ejecuta dentro de Designer el script de grafos (``SCRIPT_GRAFOS``).
4. Lanza ``fabricar.py`` con el Python del venv (sbscooker, sbsrender y composición),
   sin bloquear Designer: el puente avanza un paso por tic mientras corre.
"""

import os
import shutil
import subprocess
import time

BASE = os.path.dirname(CARPETA)  # noqa: F821  (tilingtextures_fabrica)
REPO = os.path.join(BASE, "materials_prueba")
RAMA = "claude/project-thread-8kf6pd"
VENV = os.path.join(BASE, "venv", "bin", "python")
SCRIPT_GRAFOS = "01_aparejos.py"
LOTE = "lote1"  # lote de estructuras_def.LOTES
PAQUETE = os.path.join(CARPETA, "paquetes", "aparejos_{}.sbs")  # noqa: F821
CATALOGO = os.path.join(BASE, "catalogo")
RES = 1024
SOLO = ""
TIEMPO_MAX = 40 * 60


def orden(args, **kw):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)
    print("$", " ".join(args), "->", r.returncode)
    texto = (r.stdout + r.stderr).strip()
    if texto:
        print(texto[-2000:])
    if r.returncode:
        raise RuntimeError("falló: " + " ".join(args))
    return texto


def pasos():
    orden(["git", "-C", REPO, "fetch", "-q", "origin", RAMA])
    orden(["git", "-C", REPO, "merge", "--ff-only", "FETCH_HEAD"])
    print("HEAD", orden(["git", "-C", REPO, "log", "--oneline", "-1"]))
    lib = os.path.join(REPO, "herramientas", "designer", "lib")
    for f in os.listdir(lib):
        if f.endswith(".py"):
            shutil.copy(os.path.join(lib, f), os.path.join(CARPETA, "lib", f))  # noqa: F821
    yield
    ruta = os.path.join(REPO, "herramientas", "designer", "scripts", SCRIPT_GRAFOS)
    espacio = {"__name__": "__grafos__", "__file__": ruta, "CARPETA": CARPETA, "LOTE": LOTE}  # noqa: F821
    with open(ruta, encoding="utf-8") as f:
        exec(compile(f.read(), ruta, "exec"), espacio)
    yield
    args = [VENV, os.path.join(REPO, "herramientas", "designer", "fabricar.py"), PAQUETE.format(LOTE), CATALOGO,
            "--res", str(RES), "--lote", LOTE]
    if SOLO:
        args += ["--solo", SOLO]
    print("$", " ".join(args))
    registro = os.path.join(BASE, "catalogo_fabricar.log")
    with open(registro, "w") as salida:
        entorno = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        proceso = subprocess.Popen(args, stdout=salida, stderr=subprocess.STDOUT, cwd=REPO, env=entorno)
        inicio = time.time()
        while proceso.poll() is None:
            yield
        print("fabricar.py ->", proceso.returncode, "en", round(time.time() - inicio, 1), "s")
    with open(registro, encoding="utf-8", errors="replace") as f:
        lineas = f.read().splitlines()
    for linea in lineas:
        if linea.startswith(("OK", "ERROR", "FALTAN", "hoja", "Traceback")) or "Error" in linea:
            print(linea)
    if proceso.returncode:
        print("\n".join(lineas[-30:]))
        raise RuntimeError("fabricar.py falló")
