"""Esfera de vista previa de una receta, calculada en Python puro (sin Arnold).

No depende de Maya ni de Qt: devuelve los píxeles RGB como ``bytes`` para que la
ventana los convierta en imagen. Es una aproximación rápida (GGX + entorno de
estudio) pensada para elegir y comparar, no para juzgar el render final.
"""

import os
import math

from muestrario import color as col
from muestrario import receta as rc


def _norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


_L1 = _norm((-0.55, 0.6, 0.6))
_L2 = _norm((0.7, 0.05, 0.4))
_H1 = _norm((_L1[0], _L1[1], _L1[2] + 1))
_H2 = _norm((_L2[0], _L2[1], _L2[2] + 1))
_SB = _norm((-0.5, 0.55, 0.65))


def _entorno(d):
    y = d[1]
    k = 0.22 + 0.55 * (y ** 0.6) if y > 0 else 0.12 + 0.06 * (1 + y)
    sb = max(0.0, d[0] * _SB[0] + d[1] * _SB[1] + d[2] * _SB[2])
    return k + (sb ** 40) * 3.0


def _ggx(ndh, a):
    a2 = a * a
    d = ndh * ndh * (a2 - 1) + 1
    return a2 / (math.pi * d * d)


def _fondo(x, y, n):
    s = int(x / (n / 8.0)) + int(y / (n / 8.0))
    return 0.09 if s % 2 else 0.13


def _tono(c):
    c = 1 - math.exp(-c * 1.5)
    return int(255 * max(0.0, c) ** (1 / 2.2) + 0.5)


def pixeles(receta, tamano=128, destino=rc.RENDER):
    """``bytes`` RGB de ``tamano`` x ``tamano`` píxeles."""
    r = rc.para_juego(receta) if destino == rc.JUEGO else rc.normalizar(receta)
    base = col.hex_a_lineal(r["color"])
    rough = r["rugosidad"]
    m = r["metal"]
    t = r["transparencia"]
    s = r["subsuperficie"]
    co = r["barniz"]
    fz = r["pelusa"]
    em = r["emision"]
    op = r["opacidad"]
    a = max(0.02, rough * rough)
    f0 = [0.04 * (1 - m) + base[i] * m for i in range(3)]
    em_k = (rc.emision_a_nits(em) / 1000.0) ** 0.5 * 1.6 if em > 0 else 0.0
    fz_col = col.hex_a_lineal(r["color_pelusa"] or col.aclarar_hex(r["color"], 0.25))
    w = 0.7 * s
    R = 0.9
    salida = bytearray(tamano * tamano * 3)
    n_ = float(tamano)
    for y in range(tamano):
        py = -(((y + 0.5) / n_) * 2 - 1) / R
        for x in range(tamano):
            px = (((x + 0.5) / n_) * 2 - 1) / R
            r2 = px * px + py * py
            o = (y * tamano + x) * 3
            if r2 > 1:
                g = _tono(_fondo(x, y, n_))
                salida[o] = salida[o + 1] = salida[o + 2] = g
                continue
            nz = math.sqrt(1 - r2)
            nx, ny = px, py
            ndv = max(0.001, nz)
            fres = (1 - ndv) ** 5
            dif = 0.18 + 0.1 * ny
            spec = 0.0
            for (lx, ly, lz), (hx, hy, hz), inten in ((_L1, _H1, 1.0), (_L2, _H2, 0.3)):
                ndl_raw = nx * lx + ny * ly + nz * lz
                dif += inten * max(0.0, (ndl_raw + w) / (1 + w))
                ndl = max(0.0, ndl_raw)
                if ndl:
                    spec += inten * _ggx(max(0.0, nx * hx + ny * hy + nz * hz), a) * ndl / (4 * max(ndv, 0.25))
            spec = min(spec, 30.0)
            rd = (2 * nz * nx, 2 * nz * ny, 2 * nz * nz - 1)
            env_puro = _entorno(rd)
            env = env_puro * (1 - rough) + 0.33 * rough
            ox = min(n_ - 1, max(0, round(x - nx * n_ * 0.18)))
            oy = min(n_ - 1, max(0, round(y + ny * n_ * 0.18)))
            bg = _fondo(ox, oy, n_) * (1 + rough * 1.5) + 0.15 * rough
            fondo_directo = _fondo(x, y, n_)
            if co > 0:
                fc = 0.04 + 0.96 * fres
                sc = _ggx(max(0.0, nx * _H1[0] + ny * _H1[1] + nz * _H1[2]), 0.04) * \
                    max(0.0, nx * _L1[0] + ny * _L1[1] + nz * _L1[2]) / (4 * max(ndv, 0.25))
            for i in range(3):
                fv = f0[i] + (1 - f0[i]) * fres * (1 - rough * 0.7)
                kd = (1 - m) * (1 - t)
                c = kd * base[i] * dif * (1 - fv)
                if s > 0:
                    c += kd * s * base[i] * base[i] * 0.25
                c += (1 - m) * t * bg * (0.35 + 0.65 * base[i]) * (1 - fv)
                c += fv * (env * 0.9 + spec * 0.12)
                if fz > 0:
                    c += fz * (1 - ndv) ** 2.2 * (0.25 + 0.6 * fz_col[i])
                if co > 0:
                    c = c * (1 - co * fc) + co * fc * env_puro * 0.95 + co * 0.04 * min(sc, 60.0)
                if em_k:
                    c += em_k * base[i]
                if op < 1:
                    c = c * op + fondo_directo * (1 - op)
                salida[o + i] = _tono(c)
    return bytes(salida)


CARPETA_ARNOLD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "biblioteca", "miniaturas")


def clave_arnold(receta, destino):
    """Nombre (sin extensión) de la miniatura renderizada en Arnold que viene con el plugin.

    Depende de los valores de la receta: si una receta cambia, su miniatura deja de
    encontrarse y se usa la vista previa calculada hasta que se vuelva a renderizar.
    """
    return clave_cache(receta, "arnold", destino)


def miniatura_arnold(receta, destino):
    """Ruta de la miniatura de Arnold de esta receta y destino, o None."""
    ruta = os.path.join(CARPETA_ARNOLD, clave_arnold(receta, destino) + ".jpg")
    return ruta if os.path.isfile(ruta) else None


def clave_cache(receta, tamano, destino):
    """Texto estable para cachear miniaturas en disco."""
    import hashlib
    import json
    r = rc.normalizar(receta)
    datos = {k: r[k] for k in rc.DEFECTO if k not in ("nombre", "familia", "nota", "destinos")}
    texto = json.dumps([datos, tamano, destino, 1], sort_keys=True)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16]
