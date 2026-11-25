"""Definiciones de las estructuras de motivo que fabrica Designer (datos puros).

Cada estructura es un «aparejo» de piezas rectangulares a tamaño real:

* ``pieza_cm``: ancho × alto de una pieza sin junta.
* ``junta_cm``: ancho de la junta (mortero, lechada o ranura).
* ``piezas``: cuántas piezas caben en la imagen entera (columnas, filas).
  La imagen mide ``piezas × (pieza + junta)``: siempre repite sin costuras.
* ``desfase``: corrimiento de cada fila respecto a la anterior (0,5 = a soga).
* ``bisel_cm``: redondeo del canto. ``relieve_cm``: profundidad total.
* ``irregular``: 0 = industrial, 1 = hecho a mano (cantos ondulados y astillados).
* ``rugoso``: relieve fino de la cara de la pieza (0-1).
* ``altura_var``: diferencia de altura entre piezas (0-1).
* ``poros``, ``moteado``, ``quemado``: realismo dentro de la pieza (0-1): hoyos de la
  cara, manchas de tono y un extremo más oscuro (ladrillo de horno).
* ``tono_var``: cuánto cambia el tono de una pieza a otra en el mapa (0-1). Las baldosas
  industriales apenas cambian; el ladrillo hecho a mano, mucho. El deslizador «Variación»
  de Maya multiplica esto.

Lo usa el script de Designer (grafos) y ``componer.py`` (mapas finales y motivo.json).
"""

LOTE_1 = [
    dict(id="ladrillo_soga", matiz=0.8, poros=0.7, moteado=0.8, quemado=0.6, tono_var=0.7, nombre="Ladrillo a soga", familia="Ladrillo y bloque",
         pieza_cm=(24.0, 5.5), junta_cm=1.0, piezas=(4, 16), desfase=0.5, bisel_cm=0.4, relieve_cm=1.2,
         irregular=0.55, rugoso=0.6, altura_var=0.3, junta="#a29a8c",
         recomendado_para=["ladrill", "construccion", "fachada"], etiquetas=["fachada", "muro"]),
    dict(id="ladrillo_tizon", matiz=0.8, poros=0.7, moteado=0.8, quemado=0.6, tono_var=0.7, nombre="Ladrillo a tizón", familia="Ladrillo y bloque",
         pieza_cm=(11.5, 5.5), junta_cm=1.0, piezas=(8, 16), desfase=0.5, bisel_cm=0.4, relieve_cm=1.2,
         irregular=0.55, rugoso=0.6, altura_var=0.3, junta="#a29a8c",
         recomendado_para=["ladrill", "construccion"], etiquetas=["fachada", "muro"]),
    dict(id="ladrillo_rustico", matiz=1.0, poros=0.9, moteado=1.0, quemado=0.9, tono_var=0.9, nombre="Ladrillo rústico", familia="Ladrillo y bloque",
         pieza_cm=(24.0, 5.0), junta_cm=1.5, piezas=(4, 16), desfase=0.5, bisel_cm=0.8, relieve_cm=1.8,
         irregular=0.9, rugoso=0.9, altura_var=0.5, junta="#9b9284",
         recomendado_para=["ladrill", "rustic", "antiguo"], etiquetas=["fachada", "muro", "envejecido"]),
    dict(id="bloque_hormigon", matiz=0.15, poros=1.0, moteado=0.35, quemado=0.0, tono_var=0.3, nombre="Bloque de hormigón", familia="Ladrillo y bloque",
         pieza_cm=(39.0, 19.0), junta_cm=1.0, piezas=(2, 4), desfase=0.5, bisel_cm=0.2, relieve_cm=0.8,
         irregular=0.15, rugoso=0.8, altura_var=0.1, junta="#8d8a84",
         recomendado_para=["hormigon", "cemento", "bloque"], etiquetas=["muro", "industrial"]),
    dict(id="sillar", matiz=0.45, poros=0.5, moteado=0.6, quemado=0.0, tono_var=0.5, nombre="Sillería", familia="Piedra",
         pieza_cm=(59.0, 29.0), junta_cm=1.0, piezas=(2, 4), desfase=0.5, bisel_cm=1.2, relieve_cm=2.0,
         irregular=0.5, rugoso=0.7, altura_var=0.3, junta="#b3aa98",
         recomendado_para=["piedra", "granito", "arenisca", "caliza"], etiquetas=["muro", "fachada"]),
    dict(id="adoquin", matiz=0.5, poros=0.5, moteado=0.5, quemado=0.0, tono_var=0.6, nombre="Adoquín", familia="Pavimento",
         pieza_cm=(20.0, 10.0), junta_cm=0.8, piezas=(4, 8), desfase=0.5, bisel_cm=0.8, relieve_cm=1.5,
         irregular=0.6, rugoso=0.6, altura_var=0.35, junta="#6f6a62",
         recomendado_para=["adoquin", "granito", "piedra", "pavimento"], etiquetas=["suelo", "calle"]),
    dict(id="baldosa_30", matiz=0.08, poros=0.1, moteado=0.25, quemado=0.0, tono_var=0.15, nombre="Baldosa 30 × 30", familia="Baldosa y azulejo",
         pieza_cm=(29.7, 29.7), junta_cm=0.3, piezas=(3, 3), desfase=0.0, bisel_cm=0.15, relieve_cm=0.3,
         irregular=0.0, rugoso=0.1, altura_var=0.05, junta="#d6d1c7",
         recomendado_para=["baldosa", "ceram", "gres", "porcelan"], etiquetas=["suelo"]),
    dict(id="baldosa_60", matiz=0.05, poros=0.0, moteado=0.2, quemado=0.0, tono_var=0.1, nombre="Baldosa 60 × 60", familia="Baldosa y azulejo",
         pieza_cm=(59.8, 59.8), junta_cm=0.2, piezas=(2, 2), desfase=0.0, bisel_cm=0.1, relieve_cm=0.25,
         irregular=0.0, rugoso=0.05, altura_var=0.03, junta="#cfcac0",
         recomendado_para=["baldosa", "porcelan", "gres", "marmol"], etiquetas=["suelo"]),
    dict(id="azulejo_metro", matiz=0.05, poros=0.0, moteado=0.15, quemado=0.0, tono_var=0.15, nombre="Azulejo metro", familia="Baldosa y azulejo",
         pieza_cm=(15.0, 7.5), junta_cm=0.2, piezas=(6, 12), desfase=0.5, bisel_cm=0.5, relieve_cm=0.5,
         irregular=0.05, rugoso=0.05, altura_var=0.05, junta="#e4e1da",
         recomendado_para=["azulejo", "ceram", "esmalt"], etiquetas=["pared", "cocina", "baño"]),
    dict(id="azulejo_15", matiz=0.05, poros=0.0, moteado=0.15, quemado=0.0, tono_var=0.15, nombre="Azulejo 15 × 15", familia="Baldosa y azulejo",
         pieza_cm=(14.8, 14.8), junta_cm=0.2, piezas=(6, 6), desfase=0.0, bisel_cm=0.3, relieve_cm=0.4,
         irregular=0.05, rugoso=0.05, altura_var=0.05, junta="#e4e1da",
         recomendado_para=["azulejo", "ceram", "esmalt"], etiquetas=["pared", "cocina", "baño"]),
    dict(id="tablas_madera", matiz=0.6, poros=0.0, moteado=0.3, quemado=0.0, tono_var=0.5, nombre="Tablas de madera", familia="Madera",
         pieza_cm=(119.7, 14.0), junta_cm=0.3, piezas=(2, 8), desfase=0.35, bisel_cm=0.15, relieve_cm=0.4,
         irregular=0.05, rugoso=0.3, altura_var=0.1, junta="#2e2721",
         recomendado_para=["madera", "tarima", "parquet", "pino", "roble", "nogal"], etiquetas=["suelo"]),
    dict(id="tablas_anchas", matiz=0.6, poros=0.0, moteado=0.35, quemado=0.0, tono_var=0.5, nombre="Tablas anchas", familia="Madera",
         pieza_cm=(179.6, 19.6), junta_cm=0.4, piezas=(2, 6), desfase=0.33, bisel_cm=0.2, relieve_cm=0.5,
         irregular=0.08, rugoso=0.4, altura_var=0.15, junta="#2e2721",
         recomendado_para=["madera", "tarima", "roble", "pino"], etiquetas=["suelo", "rústico"]),
]


def tile_cm(d):
    """Medida real de la imagen entera (ancho, alto) en cm."""
    return (d["piezas"][0] * (d["pieza_cm"][0] + d["junta_cm"]),
            d["piezas"][1] * (d["pieza_cm"][1] + d["junta_cm"]))


def por_id(ident, lote=None):
    for d in lote or LOTE_1:
        if d["id"] == ident:
            return d
    raise KeyError(ident)
