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
from fabricar import CARPETA_RES, costura, distancia_interior, normal_opengl, ruido_cm, suave  # noqa: E402

sys.path.insert(0, os.path.join(AQUI, "lib"))
import patrones  # noqa: E402


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
    surcos = np.sin(fase + 3.0 * tramos) * suave(tramos, 0.05, 0.2)
    lum = 0.5 + 0.10 * estrato + 0.12 * manchas + 0.10 * grano
    color = np.dstack([lum, lum * 0.99, lum * 0.96])
    color = color * (1 + oxido[..., None] * np.array([0.10, 0.0, -0.12]) * (0.5 + manchas[..., None]))
    rugosidad = 0.5 + 0.08 * grano + 0.015 * surcos
    altura = 0.5 + 0.30 * grano + 0.10 * estrato + 0.03 * surcos
    return color, rugosidad, altura


def granito(forma, cx, cy):
    """Granito abujardado: cristales claros y oscuros de 2-5 mm y superficie áspera."""
    feldespato = _salpicado(forma, cx, cy, 0.4, 401, 0.30)
    mica = _salpicado(forma, cx, cy, 0.25, 402, 0.07)
    cuarzo = _salpicado(forma, cx, cy, 0.3, 403, 0.15)
    grano = ruido_cm(forma, cx, cy, 0.07, 404, octavas=2) - 0.5
    manchas = ruido_cm(forma, cx, cy, 8.0, 405, octavas=2) - 0.5
    lum = 0.5 + 0.10 * manchas + 0.08 * grano
    color = np.dstack([lum, lum, lum])
    color = _mezclar(color, (0.66, 0.62, 0.60), 0.7 * feldespato)
    color = _mezclar(color, (0.58, 0.58, 0.60), 0.6 * cuarzo)
    color = _mezclar(color, (0.22, 0.22, 0.23), 0.8 * mica)
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


def terrazo(forma, cx, cy):
    """Terrazo pulido: trozos angulosos de mármol (blanco, negro, rojo, gris) en cemento claro."""
    alto, ancho = forma
    tile = (ancho * cx, alto * cy)
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    x, y = (xx + 0.5) * cx, (yy + 0.5) * cy
    celdas = (max(4, int(round(tile[0] / 0.7))), max(4, int(round(tile[1] / 0.7))))
    ids = patrones.voronoi_azar(x, y, tile, celdas, 601, temblor=0.9, pesos=0.8)
    rng = np.random.default_rng(602)
    n = celdas[0] * celdas[1]
    tipo = rng.choice(5, n, p=[0.55, 0.22, 0.10, 0.08, 0.05])  # cemento, blanco, gris, negro, rojo
    paleta = np.array([[0.50, 0.49, 0.46], [0.66, 0.65, 0.62], [0.47, 0.47, 0.47], [0.16, 0.16, 0.17],
                       [0.50, 0.33, 0.28]])
    tono = np.where(tipo == 0, 1.0, rng.uniform(0.9, 1.1, n))  # el cemento no deja ver sus celdas
    borde = (ids != np.roll(ids, 1, 0)) | (ids != np.roll(ids, 1, 1))
    hueco = distancia_interior(~borde, cx, cy, 0.3) < 0.09  # cemento entre trozos
    color = paleta[tipo[ids]] * tono[ids][..., None]
    color = np.where(hueco[..., None], paleta[0], color)
    grano = ruido_cm(forma, cx, cy, 0.05, 603) - 0.5
    color = color + 0.04 * grano[..., None]
    rugosidad = 0.5 + 0.03 * grano + 0.04 * hueco
    altura = 0.5 + 0.03 * grano - 0.05 * hueco
    return color, rugosidad, altura


def pizarra(forma, cx, cy):
    """Pizarra de exfoliación: lajas finas en escalones, vetas claras y brillo irregular."""
    capas = ruido_cm(forma, cx * 0.25, cy, 2.0, 701, octavas=3) - 0.5
    escalon = np.floor((capas + 0.5) * 6.0) / 6.0 - 0.5
    manchas = ruido_cm(forma, cx, cy, 8.0, 702, octavas=2) - 0.5
    grano = ruido_cm(forma, cx, cy, 0.05, 703) - 0.5
    lum = 0.5 + 0.10 * escalon + 0.10 * manchas + 0.05 * grano
    color = np.dstack([lum * 0.98, lum, lum * 1.03])
    rugosidad = 0.5 + 0.10 * manchas + 0.04 * grano
    altura = 0.5 + 0.35 * escalon + 0.10 * grano
    return color, rugosidad, altura


def marmol(forma, cx, cy):
    """Mármol veteado: fondo blanco con nubes grises y vetas finas que se ramifican."""
    base = ruido_cm(forma, cx, cy, 6.0, 801, octavas=4) - 0.5
    giro = ruido_cm(forma, cx, cy, 10.0, 802, octavas=3) - 0.5
    fino = ruido_cm(forma, cx, cy, 1.5, 803, octavas=3) - 0.5
    alto, ancho = forma
    y, x = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    largo = ancho * cx
    # Vetas: isolíneas de un campo retorcido (periódico en X con número entero de ondas).
    alto_cm = alto * cy
    campo = 2 * np.pi * (2 * x * cx / largo + y * cy / alto_cm) + 5.0 * giro + 1.2 * fino
    veta = (np.exp(-(np.sin(campo) / 0.09) ** 2) * (0.6 + 0.8 * suave(base, -0.1, 0.15))
            + 0.4 * np.exp(-(np.sin(2.0 * campo + 3 * base) / 0.04) ** 2) * suave(base, 0.0, 0.15))
    nube = suave(base + 0.3 * giro, 0.05, 0.3)
    lum = 0.56 + 0.04 * base - 0.06 * nube - 0.20 * np.clip(veta, 0, 1)
    color = np.dstack([lum, lum * 0.995, lum * 0.985])
    rugosidad = 0.5 + 0.02 * fino + 0.03 * veta
    altura = 0.5 + 0.02 * fino
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
    dict(id="terrazo", funcion=terrazo, nombre="Terrazo", familia="Construcción", tile_cm=(40.0, 40.0),
         relieve_cm=0.05, muestra="#cfc8bc", recomendado_para=["terrazo"]),
    dict(id="pizarra", funcion=pizarra, nombre="Pizarra", familia="Piedra", tile_cm=(40.0, 40.0),
         relieve_cm=0.3, muestra="#4a4d52", recomendado_para=["pizarra"]),
    dict(id="marmol", funcion=marmol, nombre="Mármol veteado", familia="Piedra", tile_cm=(80.0, 80.0),
         relieve_cm=0.02, muestra="#e6e3de", recomendado_para=["marmol"]),
    dict(id="veta_madera", funcion=veta_madera, nombre="Veta de madera", familia="Madera",
         tile_cm=(160.0, 20.0), relieve_cm=0.15, muestra="#8a5a35",
         recomendado_para=["madera", "tablas", "tarima", "parquet", "roble", "pino", "nogal"]),
]


import acab_metal  # noqa: E402
import acab_plastico  # noqa: E402
import acab_tela  # noqa: E402
import acab_organico  # noqa: E402
import acab_comida  # noqa: E402
import acab_madera  # noqa: E402
import acab_piedra  # noqa: E402

# Lotes de acabados: el primero son los de las estructuras de los lotes 1-3.
LOTES = {"base": ACABADOS, "metal": acab_metal.ACABADOS, "plastico": acab_plastico.ACABADOS,
         "tela": acab_tela.ACABADOS, "organico": acab_organico.ACABADOS,
         "comida": acab_comida.ACABADOS, "madera": acab_madera.ACABADOS,
         "piedra": acab_piedra.ACABADOS}
TODOS = [d for lote in LOTES.values() for d in lote]


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
    resultado = d["funcion"](forma, cx, cy)
    color, rugosidad, altura = resultado[:3]
    metal = resultado[3] if len(resultado) > 3 else None  # opcional: 1 = metal, 0 = deja de serlo
    rugosidad = np.broadcast_to(np.asarray(rugosidad, dtype=np.float64), forma)
    altura = np.broadcast_to(np.asarray(altura, dtype=np.float64), forma)
    color, rugosidad, altura = (np.clip(a, 0.0, 1.0) for a in (color, rugosidad, altura))
    carpeta = os.path.join(catalogo, "acabados", d["id"])
    sub = os.path.join(carpeta, CARPETA_RES.get(res, "1k"))
    os.makedirs(sub, exist_ok=True)
    Image.fromarray((color * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "color.png"))
    Image.fromarray((rugosidad * 255).round().astype(np.uint8), "L").save(os.path.join(sub, "rugosidad.png"))
    Image.fromarray((altura * 65535).round().astype(np.uint16)).save(os.path.join(sub, "altura.png"))
    if metal is not None:
        metal = np.clip(np.broadcast_to(np.asarray(metal, dtype=np.float64), forma), 0.0, 1.0)
        Image.fromarray((metal * 255).round().astype(np.uint8), "L").save(os.path.join(sub, "metal.png"))
    elif os.path.exists(os.path.join(sub, "metal.png")):
        os.remove(os.path.join(sub, "metal.png"))
    vista(color, altura, cx, cy, d["muestra"]).save(os.path.join(carpeta, "miniatura.png"))
    datos = {k: d[k] for k in ("id", "nombre", "familia", "relieve_cm", "recomendado_para")}
    datos.update({k: d[k] for k in ("muestra", "muestra_rug", "muestra_metal") if k in d})
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
    p.add_argument("--lote", default="", help="lote de LOTES (vacío = todos)")
    a = p.parse_args()
    solo = [x for x in a.solo.split(",") if x]
    for d in (LOTES[a.lote] if a.lote else TODOS):
        if solo and d["id"] not in solo:
            continue
        print("OK", json.dumps(fabricar(d, a.catalogo, a.res), ensure_ascii=False))


if __name__ == "__main__":
    main()
