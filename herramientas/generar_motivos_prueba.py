"""Motivos de prueba (herramienta de desarrollo): 3 estructuras y 3 acabados hechos con numpy.

Sirven para probar la pestaña Motivo y la red de nodos mientras la fábrica de Substance
Designer produce los definitivos. Llevan ``"prueba": true`` en su motivo.json y no se
publican con el plugin.

    python3 herramientas/generar_motivos_prueba.py <carpeta> [--res 1024]

Crea ``<carpeta>/estructuras/<id>/1k/...`` y ``<carpeta>/acabados/<id>/1k/...``.
Necesita numpy y Pillow.
"""

import argparse
import json
import os

import numpy as np
from PIL import Image


def _ruido(n, beta=2.0, estirar=(1.0, 1.0), semilla=0):
    """Ruido que se repite sin costuras (filtrado en frecuencia), normalizado a 0-1."""
    rng = np.random.default_rng(semilla)
    f = np.fft.fft2(rng.standard_normal((n, n)))
    fy = np.fft.fftfreq(n)[:, None] * estirar[1]
    fx = np.fft.fftfreq(n)[None, :] * estirar[0]
    radio = np.sqrt(fx * fx + fy * fy)
    radio[0, 0] = 1.0
    campo = np.real(np.fft.ifft2(f / radio ** (beta / 2.0)))
    campo -= campo.min()
    return campo / (campo.max() or 1.0)


def _suave(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _guardar(carpeta, nombre, datos, bits=8):
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, nombre + ".png")
    datos = np.clip(datos, 0.0, 1.0)
    if bits == 16:
        Image.fromarray((datos * 65535).astype(np.uint16)).save(ruta)
    elif datos.ndim == 2:
        Image.fromarray((datos * 255).astype(np.uint8), "L").save(ruta)
    else:
        Image.fromarray((datos * 255).astype(np.uint8), "RGBA" if datos.shape[2] == 4 else "RGB").save(ruta)
    return ruta


def _escribir(raiz, tipo, ident, datos, mapas, miniatura, res):
    carpeta = os.path.join(raiz, tipo, ident)
    sub = os.path.join(carpeta, {256: "1k", 512: "1k", 1024: "1k", 2048: "2k", 4096: "4k"}.get(res, "1k"))
    for nombre, (imagen, bits) in mapas.items():
        _guardar(sub, nombre, imagen, bits)
    _guardar(carpeta, "miniatura", miniatura)
    datos = dict(datos, id=ident, prueba=True, licencia="CC0")
    with open(os.path.join(carpeta, "motivo.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return carpeta


def _piezas(n, ancho, alto, filas, junta, desfases, semilla, pieza_largo=None):
    """Aparejo de piezas rectangulares. Devuelve (id de pieza, distancia al borde en cm)."""
    y, x = np.mgrid[0:n, 0:n].astype(float)
    x = x / n * ancho
    y = y / n * alto
    alto_fila = alto / filas
    fila = np.floor(y / alto_fila).astype(int)
    largo = pieza_largo or (ancho / 2.0)
    desplazado = (x + np.take(desfases, fila % len(desfases)) * largo) % ancho
    columna = np.floor(desplazado / largo).astype(int)
    dx = np.minimum(desplazado - columna * largo, (columna + 1) * largo - desplazado)
    yy = y - fila * alto_fila
    dy = np.minimum(yy, alto_fila - yy)
    borde = np.minimum(dx, dy) - junta / 2.0
    columnas = int(round(ancho / largo))
    ident = fila * 97 + (columna % columnas)
    rng = np.random.default_rng(semilla)
    tabla = rng.uniform(0.25, 0.75, size=filas * 97 + columnas + 1)
    return tabla[ident], borde


def _estructura(n, ancho, alto, filas, junta, desfases, semilla, bisel, pieza_largo=None, veta=False):
    gris, borde = _piezas(n, ancho, alto, filas, junta, desfases, semilla, pieza_largo)
    en_junta = (borde <= 0).astype(float)
    ruido = _ruido(n, 2.2, semilla=semilla + 1)
    fino = _ruido(n, 1.2, semilla=semilla + 2)
    if veta:
        fino = _ruido(n, 2.0, estirar=(0.15, 3.0), semilla=semilla + 3)
    altura = np.where(en_junta > 0, 0.18 + 0.05 * ruido,
                      0.55 + 0.4 * _suave(borde, 0, bisel) - 0.06 * fino * _suave(borde, 0, bisel))
    desgaste = np.clip(1.15 * ruido - 0.6 * _suave(borde, 0, bisel * 3) + 0.25 * fino, 0, 1)
    mascara = np.dstack([en_junta, gris, desgaste, np.zeros_like(gris)])
    tono = (0.35 + 0.5 * altura) * (0.8 + 0.4 * gris)
    mini = np.dstack([tono * 0.95, tono * 0.8, tono * 0.7])
    return {"altura": (altura, 16), "mascara": (mascara, 8)}, mini


def _acabado(n, semilla, estirar=(1.0, 1.0), beta=2.0, poros=0.0, contraste=0.08):
    base = _ruido(n, beta, estirar, semilla)
    detalle = _ruido(n, 1.0, estirar, semilla + 5)
    altura = 0.6 * base + 0.4 * detalle
    if poros:
        celdas = _ruido(n, 0.6, semilla=semilla + 9)
        altura = altura - poros * _suave(celdas, 0.72, 0.9)
    altura = (altura - altura.min()) / (np.ptp(altura) or 1.0)
    color = 0.5 + contraste * (base - 0.5) * 2 + 0.02 * (detalle - 0.5)
    color = np.dstack([color, color * 0.995, color * 0.99])
    rugosidad = 0.5 + 0.12 * (detalle - 0.5) * 2
    mini = np.dstack([altura * 0.6 + 0.2] * 3)
    return {"color": (color, 8), "rugosidad": (rugosidad, 8), "altura": (altura, 16)}, mini


def generar(raiz, res=1024):
    n = int(res)
    hechos = []
    mapas, mini = _estructura(n, 50.0, 12.5, 2, 1.0, [0.0, 0.5], 11, 0.6, pieza_largo=25.0)
    hechos.append(_escribir(raiz, "estructuras", "ladrillo_soga", {
        "nombre": "Ladrillo a soga (prueba)", "familia": "Ladrillo y bloque", "tile_cm": [50.0, 12.5],
        "pieza_cm": 24.0, "relieve_cm": 1.0, "junta": "#9a948a",
        "recomendado_para": ["ladrill", "construccion"]}, mapas, mini, n))
    mapas, mini = _estructura(n, 60.8, 60.8, 2, 0.4, [0.0, 0.0], 21, 0.3, pieza_largo=30.4)
    hechos.append(_escribir(raiz, "estructuras", "baldosa_cuadrada", {
        "nombre": "Baldosa cuadrada (prueba)", "familia": "Baldosa y azulejo", "tile_cm": [60.8, 60.8],
        "pieza_cm": 30.0, "relieve_cm": 0.3, "junta": "#d8d4cc",
        "recomendado_para": ["baldosa", "azulejo", "ceram"]}, mapas, mini, n))
    mapas, mini = _estructura(n, 120.0, 57.2, 4, 0.3, [0.0, 0.5, 0.25, 0.75], 31, 0.15, pieza_largo=120.0,
                              veta=True)
    hechos.append(_escribir(raiz, "estructuras", "tablas_madera", {
        "nombre": "Tablas de madera (prueba)", "familia": "Madera", "tile_cm": [120.0, 57.2],
        "pieza_cm": 120.0, "relieve_cm": 0.2, "junta": "#2e2721",
        "recomendado_para": ["madera", "tarima", "parquet", "pino", "roble", "nogal"]}, mapas, mini, n))
    mapas, mini = _acabado(n, 41, beta=2.4, poros=0.25, contraste=0.1)
    hechos.append(_escribir(raiz, "acabados", "hormigon", {
        "nombre": "Hormigón (prueba)", "familia": "Piedra y mármol", "tile_cm": [50.0, 50.0], "relieve_cm": 0.15,
        "recomendado_para": ["hormigon", "cemento", "mortero"]}, mapas, mini, n))
    mapas, mini = _acabado(n, 51, estirar=(0.05, 4.0), beta=1.6, contraste=0.05)
    hechos.append(_escribir(raiz, "acabados", "cepillado", {
        "nombre": "Cepillado (prueba)", "familia": "Metales", "tile_cm": [20.0, 20.0], "relieve_cm": 0.005,
        "recomendado_para": ["cepill", "acero", "alumin", "inox"]}, mapas, mini, n))
    mapas, mini = _acabado(n, 61, beta=1.4, poros=0.6, contraste=0.06)
    hechos.append(_escribir(raiz, "acabados", "piel_naranja", {
        "nombre": "Piel de naranja (prueba)", "familia": "Frutas y verduras", "tile_cm": [5.0, 5.0],
        "relieve_cm": 0.05, "recomendado_para": ["naranja", "limon", "mandarina"]}, mapas, mini, n))
    return hechos


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("carpeta")
    p.add_argument("--res", type=int, default=1024)
    a = p.parse_args()
    for c in generar(a.carpeta, a.res):
        print(c)
