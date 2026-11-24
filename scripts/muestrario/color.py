"""Conversión de colores entre sRGB (lo que ve el alumno) y lineal (lo que usa el render).

No depende de Maya. Los colores se guardan como texto hexadecimal sRGB («#c22a2a»)
porque es lo que muestra cualquier selector de color, y se pasan a lineal al
escribirlos en el material, que trabaja en el espacio de render de la escena.
"""


def _a_lineal(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _a_srgb(c):
    c = min(1.0, max(0.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def hex_valido(texto):
    if not isinstance(texto, str) or len(texto) != 7 or texto[0] != "#":
        return False
    try:
        int(texto[1:], 16)
        return True
    except ValueError:
        return False


def hex_a_srgb(texto):
    """«#rrggbb» -> (r, g, b) en 0..1, sin pasar a lineal."""
    if not hex_valido(texto):
        raise ValueError("color no válido: {!r}".format(texto))
    return tuple(int(texto[i:i + 2], 16) / 255.0 for i in (1, 3, 5))


def srgb_a_hex(rgb):
    return "#" + "".join("{:02x}".format(int(round(min(1.0, max(0.0, c)) * 255))) for c in rgb)


def hex_a_lineal(texto):
    return tuple(_a_lineal(c) for c in hex_a_srgb(texto))


def lineal_a_hex(rgb):
    return srgb_a_hex(tuple(_a_srgb(c) for c in rgb))


def luminancia(rgb_lineal):
    r, g, b = rgb_lineal
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def mezclar(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


def aclarar_hex(texto, cantidad):
    """Mezcla el color con blanco en sRGB (para la pelusa, algo más clara que la base)."""
    return srgb_a_hex(mezclar(hex_a_srgb(texto), (1.0, 1.0, 1.0), cantidad))


# Maya 2022 y posteriores usan por defecto ACEScg como espacio de render. Los
# valores de las recetas están en sRGB lineal (Rec.709), así que al escribirlos
# se pasan al espacio de render si hace falta (matrices con adaptación Bradford).
_SRGB_A_ACESCG = ((0.6130974, 0.3395231, 0.0473795),
                  (0.0701937, 0.9163539, 0.0134524),
                  (0.0206156, 0.1095698, 0.8698151))
_ACESCG_A_SRGB = ((1.7048587, -0.6217160, -0.0832949),
                  (-0.1300768, 1.1407357, -0.0105981),
                  (-0.0239640, -0.1289755, 1.1530393))


def _matriz(m, v):
    return tuple(m[i][0] * v[0] + m[i][1] * v[1] + m[i][2] * v[2] for i in range(3))


def es_acescg(nombre_espacio):
    return bool(nombre_espacio) and "acescg" in nombre_espacio.lower().replace(" ", "")


def a_espacio_render(rgb_lineal, nombre_espacio):
    return _matriz(_SRGB_A_ACESCG, rgb_lineal) if es_acescg(nombre_espacio) else tuple(rgb_lineal)


def desde_espacio_render(rgb, nombre_espacio):
    if es_acescg(nombre_espacio):
        return tuple(max(0.0, c) for c in _matriz(_ACESCG_A_SRGB, rgb))
    return tuple(rgb)
