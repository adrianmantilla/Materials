"""Preferencias del usuario: destino por defecto, motor, carpeta de clase y otras.

Se guardan en ``<preferencias de Maya>/materials/ajustes.json``. No depende de Maya.
"""

import json
import os

_ARCHIVO = "ajustes.json"
DEFECTOS = {
    "destino": "render",
    "motor_juego": "unreal",
    "carpeta_clase": "",
    "sincronizar": True,
    "resolucion": 2048,
    "familia": "metales",
    "solo_destino": True,
    "desplazamiento": False,
    "ruta_painter": "",
    "abrir_painter": True,
    "ultima_carpeta_texturas": "",
}


class Ajustes(object):
    def __init__(self, carpeta):
        self.carpeta = carpeta
        self.ruta = os.path.join(carpeta, _ARCHIVO) if carpeta else None
        self.datos = self._leer()

    def _leer(self):
        if not self.ruta:
            return {}
        try:
            with open(self.ruta, encoding="utf-8") as f:
                datos = json.load(f)
            return datos if isinstance(datos, dict) else {}
        except (OSError, ValueError):
            return {}

    def guardar(self):
        if not self.ruta:
            return
        try:
            os.makedirs(self.carpeta, exist_ok=True)
            temporal = self.ruta + ".tmp"
            with open(temporal, "w", encoding="utf-8") as f:
                json.dump(self.datos, f, ensure_ascii=False, indent=2)
            os.replace(temporal, self.ruta)
        except OSError:
            pass

    def __getitem__(self, clave):
        valor = self.datos.get(clave, DEFECTOS.get(clave))
        defecto = DEFECTOS.get(clave)
        if defecto is not None and not isinstance(valor, type(defecto)):
            return defecto
        return valor

    def __setitem__(self, clave, valor):
        self.datos[clave] = valor
        self.guardar()
