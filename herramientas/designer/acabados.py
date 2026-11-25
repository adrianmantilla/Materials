"""Acabados de motivo (la superficie del material): color, rugosidad y altura a tamaño real.

    venv/bin/python herramientas/designer/acabados.py <catalogo> [--res 1024] [--solo id,id]

Escribe ``<catalogo>/acabados/<id>/1k/{color.png, rugosidad.png, altura.png}``, ``miniatura.png``
y ``motivo.json``. Materials multiplica el color de la receta por ``2 × color`` (0,5 = neutro),
suma ``rugosidad − 0,5`` a la rugosidad y añade la altura a la de la estructura (con su peso).
Por eso el color es una variación alrededor de gris medio, en espacio lineal (Raw), y la
altura se mueve poco alrededor de 0,5: el relieve grande lo pone la estructura.

Se calcula en numpy con ruido medido en cm (``fabricar.ruido_cm``): repite sin costuras.
"""

import argparse
import json
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from fabricar import CARPETA_RES, costura, normal_opengl, ruido_cm, suave  # noqa: E402


def _mezclar(base, color, peso):
    return base * (1.0 - peso[..., None]) + np.asarray(color)[None, None, :] * peso[..., None]


def _salpicado(forma, cx, cy, tam_cm, semilla, cobertura):
    """Manchas sueltas de ``tam_cm`` que cubren más o menos ``cobertura`` (0-1) de la superficie."""
    r = ruido_cm(forma, cx, cy, tam_cm, semilla)
    corte = np.quantile(r, 1.0 - cobertura)
    return suave(r, corte, corte + 0.03)


def arcilla_ladrillo(forma, cx, cy):
    """Cara de ladrillo de arcilla cocida: manchas del horno, arena, motas de hierro y poros."""
    manchas = ruido_cm(forma, cx, cy, 6.0, 101, octavas=3) - 0.5
    calor = ruido_cm(forma, cx, cy, 12.0, 102, octavas=2) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.08, 103, octavas=2) - 0.5
    arena = _salpicado(forma, cx, cy, 0.12, 104, 0.035)
    hierro = _salpicado(forma, cx, cy, 0.18, 105, 0.012)
    poros = _salpicado(forma, cx, cy, 0.22, 106, 0.02)
    lum = 0.5 + 0.30 * manchas + 0.10 * grano
    color = np.dstack([lum * (1 + 0.10 * calor), lum, lum * (1 - 0.14 * calor)])
    color = _mezclar(color, (0.64, 0.61, 0.53), 0.8 * arena)
    color = _mezclar(color, (0.24, 0.21, 0.19), 0.9 * hierro)
    color = color * (1.0 - 0.25 * poros[..., None])
    rugosidad = 0.5 + 0.10 * grano + 0.04 * manchas - 0.05 * arena + 0.06 * poros
    altura = 0.5 + 0.35 * grano + 0.06 * manchas + 0.10 * arena - 0.30 * poros
    return color, rugosidad, altura


def hormigon(forma, cx, cy):
    """Hormigón prensado (bloque): árido fino, muchos poros pequeños y manchas de fraguado."""
    manchas = ruido_cm(forma, cx, cy, 8.0, 201, octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.1, 202, octavas=2) - 0.5
    arido = ruido_cm(forma, cx, cy, 0.35, 203) - 0.5
    claro = _salpicado(forma, cx, cy, 0.25, 204, 0.06)
    oscuro = _salpicado(forma, cx, cy, 0.2, 205, 0.04)
    poros = _salpicado(forma, cx, cy, 0.15, 206, 0.05)
    lum = 0.5 + 0.16 * manchas + 0.12 * grano + 0.10 * arido + 0.10 * claro - 0.10 * oscuro
    color = np.dstack([lum * 1.01, lum, lum * 0.98]) * (1.0 - 0.45 * poros[..., None])
    rugosidad = 0.5 + 0.06 * grano + 0.08 * poros - 0.03 * manchas
    altura = 0.5 + 0.30 * grano + 0.25 * arido - 0.45 * poros
    return color, rugosidad, altura


def arenisca(forma, cx, cy):
    """Piedra arenisca labrada: estratos suaves, grano de arena y huellas de la gradina."""
    estrato = ruido_cm((forma[0], forma[1]), cx * 0.15, cy, 1.5, 301, octavas=3) - 0.5
    manchas = ruido_cm(forma, cx, cy, 10.0, 302, octavas=3) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.06, 303, octavas=2) - 0.5
    oxido = _salpicado(forma, cx, cy, 3.0, 304, 0.08)
    y, x = np.mgrid[0:forma[0], 0:forma[1]]
    # Gradina: surcos paralelos diagonales de ~6 mm, a tramos (golpes del cincel).
    tramos = ruido_cm(forma, cx, cy, 4.0, 305) - 0.5
    fase = 2 * np.pi * (x * cx + y * cy) / 0.6
    surcos = np.sin(fase + 3.0 * tramos) * suave(tramos, -0.05, 0.15)
    lum = 0.5 + 0.18 * estrato + 0.22 * manchas + 0.10 * grano
    color = np.dstack([lum, lum * 0.99, lum * 0.96])
    color = color * (1 + oxido[..., None] * np.array([0.10, 0.0, -0.12]) * (0.5 + manchas[..., None]))
    rugosidad = 0.5 + 0.08 * grano + 0.03 * surcos
    altura = 0.5 + 0.30 * grano + 0.10 * estrato + 0.08 * surcos
    return color, rugosidad, altura


def granito(forma, cx, cy):
    """Granito abujardado: cristales claros y oscuros de 2-5 mm y superficie áspera."""
    feldespato = _salpicado(forma, cx, cy, 0.4, 401, 0.30)
    mica = _salpicado(forma, cx, cy, 0.25, 402, 0.12)
    cuarzo = _salpicado(forma, cx, cy, 0.3, 403, 0.15)
    grano = ruido_cm(forma, cx, cy, 0.07, 404, octavas=2) - 0.5
    manchas = ruido_cm(forma, cx, cy, 8.0, 405, octavas=2) - 0.5
    lum = 0.5 + 0.10 * manchas + 0.08 * grano
    color = np.dstack([lum, lum, lum])
    color = _mezclar(color, (0.66, 0.62, 0.60), 0.7 * feldespato)
    color = _mezclar(color, (0.58, 0.58, 0.60), 0.6 * cuarzo)
    color = _mezclar(color, (0.16, 0.16, 0.17), 0.9 * mica)
    rugosidad = 0.5 + 0.10 * grano - 0.10 * cuarzo
    altura = 0.5 + 0.45 * grano + 0.05 * feldespato - 0.05 * mica
    return color, rugosidad, altura


def veta_madera(forma, cx, cy):
    """Madera aserrada a lo largo (eje X): vetas de crecimiento que ondulan, poros alargados y nudos suaves."""
    alto, ancho = forma
    y = np.mgrid[0:alto, 0:ancho][0]
    yc = y * cy
    # Desvío de la veta (cm): lento a lo largo de la tabla, para que los anillos vayan casi paralelos.
    onda = ((ruido_cm(forma, cx * 0.04, cy, 1.2, 501, octavas=2) - 0.5) * 20.0
            + (ruido_cm(forma, cx * 0.15, cy, 0.8, 506) - 0.5) * 0.8)
    tono = ruido_cm(forma, cx * 0.1, cy, 3.0, 502, octavas=2) - 0.5
    fibra = ruido_cm(forma, cx * 0.04, cy, 0.05, 503, octavas=2) - 0.5
    poros = ruido_cm(forma, cx * 0.06, cy, 0.04, 504) - 0.5
    # Anillos: periodo ~0,45 cm; tardío (oscuro y estrecho) frente a temprano (claro).
    periodo = alto * cy / max(1, round(alto * cy / 0.45))  # número entero de anillos: repite
    t = ((yc + onda) / periodo) % 1.0
    tardio = suave(t, 0.62, 0.72) * (1.0 - suave(t, 0.9, 1.0))
    # Bandas de varios anillos (claras y oscuras) que siguen la veta: lo que se ve de lejos.
    largo = alto * cy
    k1, k2 = max(1, round(largo / periodo / 7)), max(1, round(largo / periodo / 17))  # enteros: repite
    bandas = (np.sin(2 * np.pi * (yc + onda) * k1 / largo)
              + 0.6 * np.sin(2 * np.pi * (yc + 0.7 * onda) * k2 / largo))
    lum = 0.5 + 0.20 * tono + 0.06 * bandas + 0.08 * fibra - 0.14 * tardio - 0.06 * suave(poros, 0.2, 0.35)
    color = np.dstack([lum * 1.02, lum, lum * 0.96])
    rugosidad = 0.5 + 0.05 * fibra + 0.06 * tardio
    altura = 0.5 + 0.25 * fibra - 0.12 * tardio - 0.20 * suave(poros, 0.2, 0.35)
    return color, rugosidad, altura


ACABADOS = [
    dict(id="arcilla_ladrillo", funcion=arcilla_ladrillo, nombre="Arcilla cocida", familia="Construcción",
         tile_cm=(50.0, 50.0), relieve_cm=0.4, muestra="#a5502f",
         recomendado_para=["ladrill", "arcilla", "terracota", "barro cocido", "teja"]),
    dict(id="hormigon", funcion=hormigon, nombre="Hormigón", familia="Construcción",
         tile_cm=(60.0, 60.0), relieve_cm=0.4, muestra="#8e8b85",
         recomendado_para=["hormigon", "cemento", "bloque", "mortero"]),
    dict(id="arenisca", funcion=arenisca, nombre="Arenisca labrada", familia="Piedra",
         tile_cm=(80.0, 80.0), relieve_cm=0.4, muestra="#c4b49a",
         recomendado_para=["arenisca", "sillar", "silleria", "caliza"]),
    dict(id="granito", funcion=granito, nombre="Granito abujardado", familia="Piedra",
         tile_cm=(40.0, 40.0), relieve_cm=0.3, muestra="#77726c",
         recomendado_para=["granito", "adoquin", "basalto"]),
    dict(id="veta_madera", funcion=veta_madera, nombre="Veta de madera", familia="Madera",
         tile_cm=(160.0, 20.0), relieve_cm=0.15, muestra="#8a5a35",
         recomendado_para=["madera", "tablas", "tarima", "parquet", "roble", "pino", "nogal"]),
]


def vista(color, altura, cx, cy, muestra, lado=256):
    n = normal_opengl(altura, 0.4, cx, cy) * 2 - 1
    luz = np.array([-0.55, 0.45, 0.70])
    luz /= np.linalg.norm(luz)
    lambert = np.clip((n * luz).sum(axis=2), 0, 1)
    base = np.array([int(muestra.lstrip("#")[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]) ** 2.2
    c = base * 2 * color * (0.25 + 0.9 * lambert[..., None])
    im = Image.fromarray((np.clip(c, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8), "RGB")
    return im.resize((lado, lado), Image.LANCZOS)


def fabricar(d, catalogo, res):
    forma = (res, res)
    cx, cy = d["tile_cm"][0] / res, d["tile_cm"][1] / res
    color, rugosidad, altura = d["funcion"](forma, cx, cy)
    color, rugosidad, altura = (np.clip(a, 0.0, 1.0) for a in (color, rugosidad, altura))
    carpeta = os.path.join(catalogo, "acabados", d["id"])
    sub = os.path.join(carpeta, CARPETA_RES.get(res, "1k"))
    os.makedirs(sub, exist_ok=True)
    Image.fromarray((color * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "color.png"))
    Image.fromarray((rugosidad * 255).round().astype(np.uint8), "L").save(os.path.join(sub, "rugosidad.png"))
    Image.fromarray((altura * 65535).round().astype(np.uint16)).save(os.path.join(sub, "altura.png"))
    vista(color, altura, cx, cy, d["muestra"]).save(os.path.join(carpeta, "miniatura.png"))
    datos = {k: d[k] for k in ("id", "nombre", "familia", "relieve_cm", "recomendado_para")}
    datos.update(tile_cm=list(d["tile_cm"]), licencia="CC0", fabrica="numpy", version=1)
    with open(os.path.join(carpeta, "motivo.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    return {"id": d["id"], "costura_color": costura(color.mean(axis=2)), "costura_altura": costura(altura),
            "color_medio": [round(float(v), 3) for v in color.reshape(-1, 3).mean(axis=0)],
            "altura_min_max": [round(float(altura.min()), 3), round(float(altura.max()), 3)],
            "recortado": round(float(((altura <= 0) | (altura >= 1)).mean()), 4)}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("catalogo")
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--solo", default="")
    a = p.parse_args()
    solo = [x for x in a.solo.split(",") if x]
    for d in ACABADOS:
        if solo and d["id"] not in solo:
            continue
        print("OK", json.dumps(fabricar(d, a.catalogo, a.res), ensure_ascii=False))


if __name__ == "__main__":
    main()
