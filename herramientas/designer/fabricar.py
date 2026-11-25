"""Fábrica de motivos (Mac): .sbs de Designer → .sbsar → PNG → mapas finales del catálogo.

    venv/bin/python herramientas/designer/fabricar.py <paquete.sbs> <catalogo> [--res 1024] [--solo id,id]

1. ``sbscooker`` cocina el paquete en .sbsar.
2. ``sbsrender`` saca, por cada grafo, las salidas en bruto (forma del aparejo, nubes, motas,
   grunge) a ``<catalogo>/_bruto/<id>/``. Los cantos irregulares, el detalle fino y la numeración
   de las piezas se hacen aquí en numpy: es rápido, repite sin costuras y mide en cm.
3. ``componer`` las convierte en los mapas que lee Materials a tamaño real:
   ``estructuras/<id>/<res>/altura.png`` (16 bits), ``mascara.png`` (RGB sin alfa:
   R junta, G gris por pieza, B desgaste), ``normal.png`` (OpenGL), ``tono.png`` (matiz por
   pieza, si la estructura tiene ``matiz``), ``miniatura.png`` y
   ``motivo.json``. Además deja ``<catalogo>/_hoja_<paquete>.jpg`` con todas las miniaturas
   y ``_informe_<paquete>.json`` con medidas de control (costuras, proporción de junta...).

Necesita numpy y Pillow (el venv de la fábrica).
"""

import argparse
import glob
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "lib"))
import estructuras_def as ed  # noqa: E402

DESIGNER = "/Applications/Adobe Substance 3D Designer/Adobe Substance 3D Designer.app/Contents/MacOS"
BRUTOS = ("forma", "nubes", "motas", "grunge")
CARPETA_RES = {256: "1k", 512: "1k", 1024: "1k", 2048: "2k", 4096: "4k"}


def ejecutar(orden):
    print("$", " ".join(orden))
    r = subprocess.run(orden, capture_output=True, text=True)
    salida = (r.stdout + r.stderr).strip()
    if salida:
        print("\n".join(salida.splitlines()[-15:]))
    if r.returncode:
        raise RuntimeError("falló ({}): {}".format(r.returncode, orden[0]))
    return salida


def cocinar(sbs):
    carpeta = os.path.dirname(os.path.abspath(sbs))
    ejecutar([os.path.join(DESIGNER, "sbscooker"), "--inputs", sbs, "--output-path", carpeta])
    return os.path.splitext(os.path.abspath(sbs))[0] + ".sbsar"


def renderizar(sbsar, ident, destino, res, semilla=1):
    os.makedirs(destino, exist_ok=True)
    for viejo in glob.glob(os.path.join(destino, "*.png")):
        os.remove(viejo)
    log2 = int(round(np.log2(res)))
    ejecutar([os.path.join(DESIGNER, "sbsrender"), "render", "--input", sbsar, "--input-graph", "pkg://" + ident,
              "--output-path", destino, "--output-name", "{outputNodeName}", "--output-format", "png",
              "--set-value", "$outputsize@{},{}".format(log2, log2), "--set-value", "$randomseed@{}".format(semilla)])


# --- Composición (numpy) -------------------------------------------------------------------------

def leer(ruta):
    im = Image.open(ruta)
    a = np.asarray(im)
    if a.ndim == 3:
        a = a[..., :3].mean(axis=2)
    escala = 65535.0 if a.dtype == np.uint16 or a.max() > 255 else 255.0
    return a.astype(np.float64) / escala


def suave(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def distancia_interior(mascara, px_x, px_y, maximo_cm):
    """Distancia aproximada (cm) de cada píxel de pieza al borde, hasta ``maximo_cm``. Repite sin costuras."""
    paso = min(px_x, px_y)
    d = np.where(mascara, maximo_cm, 0.0)
    vecinos = [((0, 1), px_x), ((0, -1), px_x), ((1, 0), px_y), ((-1, 0), px_y),
               ((1, 1), np.hypot(px_x, px_y)), ((1, -1), np.hypot(px_x, px_y)),
               ((-1, 1), np.hypot(px_x, px_y)), ((-1, -1), np.hypot(px_x, px_y))]
    for _ in range(int(np.ceil(maximo_cm / paso)) + 2):
        nuevo = d
        for (dy, dx), coste in vecinos:
            nuevo = np.minimum(nuevo, np.roll(d, (dy, dx), axis=(0, 1)) + coste)
        nuevo = np.where(mascara, nuevo, 0.0)
        if np.array_equal(nuevo, d):
            break
        d = nuevo
    return np.minimum(d, maximo_cm)


def normal_opengl(altura, relieve_cm, cm_px_x, cm_px_y):
    h = altura * relieve_cm
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) / (2 * cm_px_x)
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) / (2 * cm_px_y)
    # Imagen con y hacia abajo; OpenGL (Maya) tiene el verde hacia arriba.
    n = np.dstack([-dx, dy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def hex_a_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def vista(altura, normal, mascara_rgb, junta_hex, lado=256, tono=None):
    """Miniatura sombreada: pieza gris cálido con variación, junta de su color, luz rasante."""
    n = normal * 2 - 1
    luz = np.array([-0.55, 0.45, 0.70])
    luz /= np.linalg.norm(luz)
    lambert = np.clip((n * luz).sum(axis=2), 0, 1)
    pieza = np.array([0.62, 0.42, 0.33]) * (0.8 + 0.4 * mascara_rgb[..., 1:2])
    pieza = pieza * (1 - 0.35 * mascara_rgb[..., 2:3]) + 0.35 * mascara_rgb[..., 2:3] * np.array([0.75, 0.7, 0.62])
    if tono is not None:
        pieza = pieza * 2 * tono
    base = pieza * (1 - mascara_rgb[..., 0:1]) + hex_a_rgb(junta_hex) * mascara_rgb[..., 0:1]
    color = base * (0.25 + 0.9 * lambert[..., None])
    im = Image.fromarray((np.clip(color, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8), "RGB")
    return im.resize((lado, lado), Image.LANCZOS)


def costura(a):
    """Salto en el borde de la imagen dividido por el mayor salto entre columnas (o filas) interiores.

    Hasta ~1 no hay costura (el borde no salta más que una junta normal); bastante más de 1 la delata.
    """
    peor = 0.0
    for eje in (0, 1):
        b = np.moveaxis(a, eje, 0)
        interior = np.abs(np.diff(b, axis=0)).mean(axis=1).max() + 1e-9
        borde = np.abs(b[0] - b[-1]).mean()
        peor = max(peor, borde / interior)
    return round(float(peor), 2)


def ruido_cm(forma, cm_px_x, cm_px_y, tam_cm, semilla, octavas=1):
    """Ruido que repite sin costuras con rasgos de ``tam_cm`` a tamaño real (0-1, media 0,5).

    Se filtra ruido blanco en frecuencia (FFT, periódica por naturaleza) con una gaussiana medida
    en cm en cada eje, así un píxel no cuadrado no estira el grano. Mucho más rápido que los ruidos
    FX-map de Designer a escalas altas.
    """
    rng = np.random.default_rng(semilla)
    fy = np.fft.fftfreq(forma[0], d=cm_px_y)[:, None]
    fx = np.fft.fftfreq(forma[1], d=cm_px_x)[None, :]
    total = np.zeros(forma)
    peso = 1.0
    for o in range(octavas):
        sigma = max(tam_cm / (2.0 ** o), 0.7 * max(cm_px_x, cm_px_y)) / 2.0
        filtro = np.exp(-2.0 * (np.pi * sigma) ** 2 * (fx ** 2 + fy ** 2))
        r = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal(forma)) * filtro))
        total += peso * r / (r.std() + 1e-9)
        peso *= 0.5
    total /= total.std() + 1e-9
    return np.clip(0.5 + 0.18 * total, 0.0, 1.0)


def deformar(forma, cm_px_x, cm_px_y, amplitud_cm, semilla):
    """Desplaza la forma con un ruido suave (~3 cm, más un detalle de ~1 cm) y la vuelve a umbralizar.

    Da cantos ondulados de pieza hecha a mano sin flecos. ``amplitud_cm`` es el desplazamiento típico.
    """
    if amplitud_cm <= 0:
        return forma > 0.5
    alto, ancho = forma.shape
    desp = []
    for k in range(2):
        r = (ruido_cm(forma.shape, cm_px_x, cm_px_y, 3.0, semilla + k) - 0.5
             + 0.35 * (ruido_cm(forma.shape, cm_px_x, cm_px_y, 1.0, semilla + 10 + k) - 0.5))
        desp.append(r / 0.18 * amplitud_cm)
    y, x = np.mgrid[0:alto, 0:ancho].astype(np.float64)
    xs = x + desp[0] / cm_px_x
    ys = y + desp[1] / cm_px_y
    x0, y0 = np.floor(xs).astype(int), np.floor(ys).astype(int)
    fx, fy = xs - x0, ys - y0

    def en(yy, xx):
        return forma[yy % alto, xx % ancho]

    valor = ((en(y0, x0) * (1 - fx) + en(y0, x0 + 1) * fx) * (1 - fy)
             + (en(y0 + 1, x0) * (1 - fx) + en(y0 + 1, x0 + 1) * fx) * fy)
    return valor > 0.5


def etiquetar(mascara):
    """Numera las piezas (vecinos en cruz) teniendo en cuenta que la imagen repite.

    Una pieza cortada por el borde es una sola. Devuelve (etiquetas, n) con -1 fuera de pieza.
    Trabaja por tramos de cada fila, así que es rápido aunque haya muchas piezas.
    """
    alto, ancho = mascara.shape
    padre = []

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    def unir(a, b):
        ra, rb = raiz(a), raiz(b)
        if ra != rb:
            padre[max(ra, rb)] = min(ra, rb)

    filas = []
    for fila in mascara.astype(np.int8):
        cambio = np.diff(np.concatenate([[0], fila, [0]]))
        ini, fin = np.flatnonzero(cambio == 1), np.flatnonzero(cambio == -1)
        ids = list(range(len(padre), len(padre) + len(ini)))
        padre.extend(ids)
        if len(ini) >= 2 and ini[0] == 0 and fin[-1] == ancho:
            unir(ids[0], ids[-1])
        filas.append((ini, fin, ids))

    def solapar(a, b):
        (ia, fa, da), (ib, fb, db) = a, b
        i = j = 0
        while i < len(ia) and j < len(ib):
            if ia[i] < fb[j] and ib[j] < fa[i]:
                unir(da[i], db[j])
            if fa[i] < fb[j]:
                i += 1
            else:
                j += 1

    for y in range(1, alto):
        solapar(filas[y - 1], filas[y])
    solapar(filas[-1], filas[0])
    raices = np.array([raiz(i) for i in range(len(padre))], dtype=np.int64)
    _, compacto = np.unique(raices, return_inverse=True)
    etiquetas = np.full(mascara.shape, -1, dtype=np.int64)
    for y, (ini, fin, ids) in enumerate(filas):
        for a, b, i in zip(ini, fin, ids):
            etiquetas[y, a:b] = compacto[i]
    return etiquetas, (int(compacto.max()) + 1 if len(compacto) else 0)


def limpiar_piezas(mascara, pieza_px):
    """Quita islas de pieza sueltas en la junta y tapa agujeros de junta dentro de una pieza."""
    lab, n = etiquetar(mascara)
    area = np.bincount(lab[lab >= 0], minlength=n)
    mascara = mascara & (area[np.maximum(lab, 0)] >= 0.05 * pieza_px)
    hueco, m = etiquetar(~mascara)
    area = np.bincount(hueco[hueco >= 0], minlength=m)
    # La junta es una red conectada enorme; un trozo de junta pequeño es un agujero dentro de una pieza.
    return mascara | ((hueco >= 0) & (area[np.maximum(hueco, 0)] < 0.02 * pieza_px))


def por_pieza(lab, n, cm_px_x, cm_px_y, semilla):
    """Datos aleatorios de cada pieza: gris, altura e inclinación (plano 0-1 en dirección al azar)."""
    rng = np.random.default_rng(semilla)
    alto, ancho = lab.shape
    dentro = lab >= 0
    l = lab[dentro]
    y, x = np.nonzero(dentro)
    centro = []
    for v, tam in ((x, ancho), (y, alto)):
        ang = 2 * np.pi * v / tam
        c = np.arctan2(np.bincount(l, np.sin(ang), n), np.bincount(l, np.cos(ang), n)) * tam / (2 * np.pi)
        centro.append(((v - c[l] + tam / 2.0) % tam - tam / 2.0))
    dx, dy = centro[0] * cm_px_x, centro[1] * cm_px_y
    ang = rng.uniform(0, 2 * np.pi, n)
    u = dx * np.cos(ang[l]) + dy * np.sin(ang[l])
    lo = np.full(n, np.inf)
    hi = np.full(n, -np.inf)
    np.minimum.at(lo, l, u)
    np.maximum.at(hi, l, u)
    incl = np.zeros(lab.shape)
    incl[dentro] = (u - lo[l]) / np.maximum(hi[l] - lo[l], 1e-6)
    gris, alt = np.full(lab.shape, 0.5), np.full(lab.shape, 0.5)
    gris[dentro] = rng.uniform(0, 1, n)[l]
    alt[dentro] = rng.uniform(0, 1, n)[l]
    return gris, alt, incl


def componer(d, bruto, destino_raiz, res):
    b = {n: leer(os.path.join(bruto, n + ".png")) for n in BRUTOS}
    forma = b["forma"].shape
    tw, th = ed.tile_cm(d)
    cm_px_x, cm_px_y = tw / forma[1], th / forma[0]
    pix = max(cm_px_x, cm_px_y)
    pieza_px = d["pieza_cm"][0] * d["pieza_cm"][1] / (cm_px_x * cm_px_y)
    mascara = deformar(b["forma"], cm_px_x, cm_px_y, 0.35 * d["irregular"], 21)
    mascara = limpiar_piezas(mascara, pieza_px)
    lab, n = etiquetar(mascara)
    gris_p, alt_p, incl = por_pieza(lab, n, cm_px_x, cm_px_y, semilla=len(d["id"]) * 7 + 1)
    av, ru, ir = d["altura_var"], d["rugoso"], d["irregular"]
    po, mo, qu = d.get("poros", 0.0), d.get("moteado", 0.0), d.get("quemado", 0.0)
    bisel = max(d["bisel_cm"], 0.6 * pix)
    dist = distancia_interior(mascara, cm_px_x, cm_px_y, max(bisel * 3.0, 3.0))
    # Ruidos finos a tamaño real (numpy): grano de ~5 mm, arena de ~1,5 mm, poros de ~3 mm, canto de ~1 cm.
    grano = ruido_cm(forma, cm_px_x, cm_px_y, 0.5, 11, octavas=3)
    arena = ruido_cm(forma, cm_px_x, cm_px_y, 0.15, 13, octavas=2)
    poros = ruido_cm(forma, cm_px_x, cm_px_y, 0.3, 12)
    canto = ruido_cm(forma, cm_px_x, cm_px_y, 1.0, 14, octavas=2)
    golpe = ruido_cm(forma, cm_px_x, cm_px_y, 1.0, 15, octavas=3)

    # Canto redondeado (cuarto de círculo) que no es una línea perfecta: el redondeo varía a lo largo.
    dist_c = np.maximum(dist + ir * bisel * 1.2 * (canto - 0.5) * 2.0, 0.0)
    t = np.clip(dist_c / bisel, 0.0, 1.0)
    perfil = np.sqrt(1.0 - (1.0 - t) ** 2)
    # Cara: cada pieza a su altura y algo inclinada; ondulación suave, grano y poros.
    cara = (0.72 + av * (0.12 * (alt_p - 0.5) + 0.07 * (incl - 0.5))
            + ru * (0.03 * (b["nubes"] - 0.5) + 0.025 * (b["motas"] - 0.5) + 0.035 * (grano - 0.5)
                    + 0.012 * (arena - 0.5)))
    hoyo = suave(poros, 0.80, 0.84) * po
    cara = cara - 0.07 * hoyo
    # Desconchones: casi siempre junto al canto, con pared viva y fondo áspero.
    banda = 1.0 - suave(dist, 0.2, 0.6 + 1.2 * ir)
    golpeado = golpe + 0.25 * banda + 0.05 * (1.0 - b["grunge"])
    umbral = 0.97 - 0.12 * ir
    desconchon = suave(golpeado, umbral, umbral + 0.02) * min(1.0, 2.0 * ir)
    cara = cara - desconchon * (0.16 + 0.10 * golpe + 0.05 * arena)
    # Mortero rehundido, con arena y alguna oquedad.
    junta = (0.10 + 0.025 * b["nubes"] + 0.02 * (grano - 0.5) + 0.03 * (arena - 0.5)
             - 0.03 * suave(poros, 0.78, 0.86))
    altura = junta + (np.maximum(cara, junta) - junta) * perfil
    altura = np.clip(altura, 0.0, 1.0)

    mancha = 1.0 - b["grunge"]  # grunge_map_001 es casi blanco con manchas oscuras
    desgaste = np.clip(1.2 * mancha * (1.0 - 0.5 * perfil) - 0.2 + 0.9 * desconchon
                       + 0.25 * (1.0 - perfil), 0.0, 1.0) * mascara
    tv = d.get("tono_var", 0.5)
    # Tono: uno por pieza, manchado dentro, un extremo más quemado, motas de hierro y canto algo más oscuro.
    tono = (0.5 + (gris_p - 0.5) * tv
            + 0.20 * mo * (b["nubes"] - 0.5) + 0.12 * mo * (b["motas"] - 0.5) + 0.06 * mo * (grano - 0.5)
            - 0.20 * qu * suave(incl, 0.6, 1.0)
            - 0.12 * po * suave(poros, 0.86, 0.92)
            - 0.06 * (1.0 - perfil))
    gris = np.where(mascara, np.clip(tono, 0.0, 1.0), 0.5)
    # Matiz por pieza (mapa tono, RGB alrededor de 0,5): más naranja o más fría, más morada o
    # más parda; el extremo quemado tira a morado y hay manchas de color dentro de la pieza.
    mz = d.get("matiz", 0.0)
    if mz > 0:
        rng = np.random.default_rng(len(d["id"]) * 13 + 5)
        calido = np.array([0.08, 0.015, -0.09])
        # La madera no tira a morado; el ladrillo y la piedra sí (más o menos cocidos, óxidos).
        morado = np.array([0.0, 0.0, 0.0]) if d["familia"] == "Madera" else np.array([0.02, -0.05, 0.035])
        exponente = mz * (rng.standard_normal((n, 1)) * calido + rng.standard_normal((n, 1)) * morado
                          + 0.10 * rng.standard_normal((n, 1)))
        mult = np.ones(forma + (3,))
        mult[mascara] = np.exp(exponente[lab[mascara]])
        mult *= np.exp(-qu * mz * suave(incl, 0.7, 1.0)[..., None] * np.array([0.20, 0.35, 0.25]))
        mult *= np.exp(mz * 0.10 * (b["nubes"] - 0.5)[..., None] * np.array([1.0, 0.5, -0.3]))
        tono_rgb = np.where(mascara[..., None], np.clip(0.5 * mult, 0.0, 1.0), 0.5)
    else:
        tono_rgb = None
    en_junta = 1.0 - suave(dist, 0.0, 1.5 * pix)  # canto suavizado un píxel
    mascara_rgb = np.dstack([en_junta, gris, desgaste])
    normal = normal_opengl(altura, d["relieve_cm"], cm_px_x, cm_px_y)

    carpeta = os.path.join(destino_raiz, "estructuras", d["id"])
    sub = os.path.join(carpeta, CARPETA_RES.get(res, "1k"))
    os.makedirs(sub, exist_ok=True)
    Image.fromarray((altura * 65535).round().astype(np.uint16)).save(os.path.join(sub, "altura.png"))
    Image.fromarray((mascara_rgb * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "mascara.png"))
    Image.fromarray((normal * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "normal.png"))
    if tono_rgb is not None:
        Image.fromarray((tono_rgb * 255).round().astype(np.uint8), "RGB").save(os.path.join(sub, "tono.png"))
    mini = vista(altura, normal, mascara_rgb, d["junta"], tono=tono_rgb)
    mini.save(os.path.join(carpeta, "miniatura.png"))
    datos = {k: d[k] for k in ("id", "nombre", "familia", "junta", "recomendado_para", "etiquetas", "relieve_cm")}
    datos.update(tile_cm=[round(tw, 3), round(th, 3)], pieza_cm=d["pieza_cm"][0], color2=False, licencia="CC0",
                 fabrica="designer", version=2)
    with open(os.path.join(carpeta, "motivo.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    junta_real = 1.0 - (d["pieza_cm"][0] * d["pieza_cm"][1]) / ((d["pieza_cm"][0] + d["junta_cm"]) *
                                                              (d["pieza_cm"][1] + d["junta_cm"]))
    area = np.bincount(lab[lab >= 0], minlength=n)
    informe = {"id": d["id"], "res": [int(x) for x in forma],
               "junta_px": round(float(1.0 - mascara.mean()), 4), "junta_esperada": round(junta_real, 4),
               "piezas_contadas": int((area > 0.3 * pieza_px).sum()), "piezas_esperadas": d["piezas"][0] * d["piezas"][1],
               "piezas_pegadas": int((area > 1.6 * pieza_px).sum()),
               "costura_altura": costura(altura), "costura_mascara": costura(mascara_rgb[..., 0]),
               "altura_min_max": [round(float(altura.min()), 3), round(float(altura.max()), 3)],
               "desconchon": round(float(desconchon[mascara].mean()), 3),
               "desgaste_medio": round(float(desgaste.mean()), 3)}
    return mini, informe


def hoja(minis, ruta, columnas=6):
    lado = 256
    filas = (len(minis) + columnas - 1) // columnas
    lienzo = Image.new("RGB", (columnas * lado, filas * (lado + 18)), (24, 24, 24))
    dibujo = ImageDraw.Draw(lienzo)
    for i, (nombre, im) in enumerate(minis):
        x, y = (i % columnas) * lado, (i // columnas) * (lado + 18)
        lienzo.paste(im, (x, y))
        dibujo.text((x + 4, y + lado + 3), nombre, fill=(220, 220, 220))
    lienzo.save(ruta, quality=88)
    return ruta


def hoja_renders(carpeta, ruta, lado=360, columnas=4):
    """Junta los PNG de hoja_arnold.py en una hoja con el nombre debajo de cada uno."""
    minis = []
    for f in sorted(os.listdir(carpeta)):
        if f.endswith(".png"):
            im = Image.open(os.path.join(carpeta, f)).convert("RGB").resize((lado, lado), Image.LANCZOS)
            minis.append((os.path.splitext(f)[0], im))
    filas = (len(minis) + columnas - 1) // columnas
    lienzo = Image.new("RGB", (columnas * lado, filas * (lado + 20)), (24, 24, 24))
    dibujo = ImageDraw.Draw(lienzo)
    for i, (nombre, im) in enumerate(minis):
        x, y = (i % columnas) * lado, (i // columnas) * (lado + 20)
        lienzo.paste(im, (x, y))
        dibujo.text((x + 5, y + lado + 4), nombre, fill=(225, 225, 225))
    lienzo.save(ruta, quality=90)
    print("hoja:", ruta, len(minis), "renders")
    return ruta


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--hoja-renders":
        hoja_renders(sys.argv[2], sys.argv[3])
        return
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("sbs")
    p.add_argument("catalogo")
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--solo", default="")
    p.add_argument("--sin-render", action="store_true", help="solo componer desde _bruto")
    a = p.parse_args()
    solo = [x for x in a.solo.split(",") if x]
    sbsar = os.path.splitext(os.path.abspath(a.sbs))[0] + ".sbsar"
    if not a.sin_render:
        sbsar = cocinar(a.sbs)
        print(ejecutar([os.path.join(DESIGNER, "sbsrender"), "info", "--input", sbsar])[:3000])
    minis, informes = [], []
    for d in ed.LOTE_1:
        if solo and d["id"] not in solo:
            continue
        bruto = os.path.join(a.catalogo, "_bruto", d["id"])
        try:
            if not a.sin_render:
                renderizar(sbsar, d["id"], bruto, a.res)
            faltan = [n for n in BRUTOS if not os.path.isfile(os.path.join(bruto, n + ".png"))]
            if faltan:
                print("FALTAN", d["id"], faltan, os.listdir(bruto) if os.path.isdir(bruto) else "-")
                continue
            mini, informe = componer(d, bruto, a.catalogo, a.res)
            minis.append((d["id"], mini))
            informes.append(informe)
            print("OK", json.dumps(informe, ensure_ascii=False))
        except Exception as e:  # sigue con las demás
            print("ERROR", d["id"], e)
    nombre = os.path.splitext(os.path.basename(a.sbs))[0]
    if minis:
        print("hoja:", hoja(minis, os.path.join(a.catalogo, "_hoja_{}.jpg".format(nombre))))
    with open(os.path.join(a.catalogo, "_informe_{}.json".format(nombre)), "w", encoding="utf-8") as f:
        json.dump(informes, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
