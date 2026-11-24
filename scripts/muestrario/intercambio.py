"""Carpeta de intercambio entre Maya y Substance 3D Painter.

No depende de Maya ni de Painter. Los dos programas se hablan con archivos,
sin abrir puertos de red, así que funciona igual en Mac y en Windows y aunque
uno de los dos se abra más tarde:

    <proyecto>/sourceimages/muestrario/<objeto>/
        <objeto>.fbx          malla que manda Maya (un juego de texturas por material)
        receta.json           destino, motor y valores de cada material
        texturas/             aquí exporta Painter
        manifiesto.json       lo escribe Painter al terminar cada exportación

    <carpeta personal>/Muestrario/buzon/<id>.json
        aviso para Painter de que hay un envío nuevo (apunta a receta.json)

El plugin de Painter (``painter/muestrario_painter.py``) usa el mismo formato.
"""

import datetime
import json
import os
import time
import uuid

VERSION = 1
CARPETA_TEXTURAS = "texturas"
RECETA = "receta.json"
MANIFIESTO = "manifiesto.json"

MOTORES = ("arnold", "unreal", "unity", "gltf")
NORMAL_DE_MOTOR = {"arnold": "opengl", "unreal": "directx", "unity": "opengl", "gltf": "opengl"}
RESOLUCIONES = (512, 1024, 2048, 4096)


def carpeta_personal_muestrario():
    """Carpeta compartida por Maya y Painter en la cuenta del usuario (la del buzón)."""
    base = os.environ.get("MUESTRARIO_CASA") or os.path.join(os.path.expanduser("~"), "Documents", "Muestrario")
    return base


def carpeta_buzon():
    return os.path.join(carpeta_personal_muestrario(), "buzon")


def carpeta_envio(proyecto, objeto):
    return os.path.join(proyecto, "sourceimages", "muestrario", limpiar_nombre(objeto))


def limpiar_nombre(nombre):
    nombre = str(nombre).split("|")[-1].split(":")[-1]
    limpio = "".join(c if (c.isalnum() and ord(c) < 128) or c in "-_" else "_" for c in nombre).strip("_")
    return limpio or "objeto"


def ahora():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


def escribir_json(ruta, datos):
    """Escritura atómica: el otro programa nunca lee un archivo a medias."""
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    temporal = ruta + ".tmp"
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    os.replace(temporal, ruta)


def leer_json(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)
        return datos if isinstance(datos, dict) else None
    except (OSError, ValueError):
        return None


def nueva_receta_envio(objeto, malla, juegos, destino="render", motor="arnold", resolucion=2048):
    """``juegos``: nombre del juego de texturas (= material) -> receta de Muestrario."""
    if motor not in MOTORES:
        motor = "arnold"
    if resolucion not in RESOLUCIONES:
        resolucion = 2048
    return {
        "version": VERSION,
        "programa": "Muestrario",
        "objeto": objeto,
        "malla": os.path.basename(malla),
        "destino": destino,
        "motor": motor,
        "normal": NORMAL_DE_MOTOR[motor],
        "resolucion": resolucion,
        "texturas": CARPETA_TEXTURAS,
        "creado": ahora(),
        "juegos": juegos,
    }


def enviar(carpeta, receta_envio):
    """Escribe receta.json y deja el aviso en el buzón. Devuelve la ruta del aviso."""
    os.makedirs(os.path.join(carpeta, CARPETA_TEXTURAS), exist_ok=True)
    ruta_receta = os.path.join(carpeta, RECETA)
    escribir_json(ruta_receta, receta_envio)
    aviso = {"version": VERSION, "receta": os.path.abspath(ruta_receta), "objeto": receta_envio.get("objeto"),
             "creado": ahora(), "id": uuid.uuid4().hex[:12]}
    ruta_aviso = os.path.join(carpeta_buzon(), "{}_{}.json".format(int(time.time()), aviso["id"]))
    escribir_json(ruta_aviso, aviso)
    return ruta_aviso


def avisos_pendientes():
    """Avisos del buzón, del más antiguo al más nuevo (lo usa el plugin de Painter)."""
    carpeta = carpeta_buzon()
    if not os.path.isdir(carpeta):
        return []
    salida = []
    for nombre in sorted(os.listdir(carpeta)):
        if nombre.endswith(".json"):
            datos = leer_json(os.path.join(carpeta, nombre))
            if datos and datos.get("receta"):
                datos["_ruta"] = os.path.join(carpeta, nombre)
                salida.append(datos)
    return salida


def escribir_manifiesto(carpeta, texturas_por_juego, contador=None):
    """Lo llama Painter al exportar: ``texturas_por_juego`` es juego -> lista de rutas."""
    anterior = leer_json(os.path.join(carpeta, MANIFIESTO)) or {}
    datos = {
        "version": VERSION,
        "exportado": ahora(),
        "contador": int(contador if contador is not None else anterior.get("contador", 0) + 1),
        "juegos": {j: [os.path.abspath(r) for r in rutas] for j, rutas in texturas_por_juego.items()},
    }
    escribir_json(os.path.join(carpeta, MANIFIESTO), datos)
    return datos


def leer_manifiesto(carpeta):
    datos = leer_json(os.path.join(carpeta, MANIFIESTO))
    if not datos or not isinstance(datos.get("juegos"), dict):
        return None
    juegos = {}
    for juego, rutas in datos["juegos"].items():
        if isinstance(rutas, list):
            juegos[str(juego)] = [_ruta_local(carpeta, r) for r in rutas if isinstance(r, str)]
    datos["juegos"] = juegos
    return datos


def _ruta_local(carpeta, ruta):
    """Si la carpeta se ha movido (otro ordenador), busca el archivo en texturas/ por nombre."""
    if os.path.isfile(ruta):
        return ruta
    nombre = ruta.replace("\\", "/").split("/")[-1]
    candidata = os.path.join(carpeta, CARPETA_TEXTURAS, nombre)
    return candidata if os.path.isfile(candidata) else ruta


def huella_manifiesto(carpeta):
    """Algo que cambia cada vez que Painter exporta (para vigilar sin leer el JSON)."""
    try:
        st = os.stat(os.path.join(carpeta, MANIFIESTO))
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def envios_del_proyecto(proyecto):
    """Carpetas de envío que hay en el proyecto (con su receta.json)."""
    base = os.path.join(proyecto, "sourceimages", "muestrario")
    if not os.path.isdir(base):
        return []
    salida = []
    for nombre in sorted(os.listdir(base)):
        carpeta = os.path.join(base, nombre)
        if os.path.isfile(os.path.join(carpeta, RECETA)):
            salida.append(carpeta)
    return salida
