"""Pruebas sin Maya de la ventana de Muestrario con Qt sin pantalla y servicios falsos.

Necesitan PySide6 (``pip install PySide6-Essentials``); si no está, se saltan.
"""

import os
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "tests"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    from muestrario import intercambio as ic
    from muestrario import receta as rc
    from muestrario.ajustes import Ajustes
    from muestrario.ventana import Servicios, VentanaMuestrario
    APP = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

from test_logica import png  # noqa: E402


class ServiciosFalsos(Servicios if QtWidgets else object):
    """Imita una escena: materiales en un diccionario."""
    en_maya = True

    def __init__(self, proyecto):
        self.carpeta_proyecto = proyecto
        self.mats = {}
        self.asignaciones = {}
        self.seleccion = ["pCube1"]
        self.conexiones = {}
        self.envios_hechos = []
        self.destino_guardado = None

    def proyecto(self):
        return self.carpeta_proyecto

    def guardar_destino(self, destino, motor):
        self.destino_guardado = (destino, motor)

    def existe(self, material):
        return material in self.mats

    def crear_material(self, receta, destino, nombre=None):
        nombre = rc.nombre_material(nombre or receta["nombre"])
        while nombre in self.mats:
            nombre += "1"
        self.mats[nombre] = {"receta": rc.normalizar(receta), "destino": destino}
        return nombre

    def actualizar_material(self, material, receta, destino):
        self.mats[material] = {"receta": rc.normalizar(receta), "destino": destino}
        return []

    def leer_receta(self, material):
        r = dict(self.mats[material]["receta"])
        r["texturas"] = self.texturas_de(material)
        return r

    def material_seleccionado(self):
        for m, objetos in self.asignaciones.items():
            if set(self.seleccion) & set(objetos):
                return m
        return None

    def asignar(self, material, elementos=None):
        for m in self.asignaciones:
            self.asignaciones[m] = [o for o in self.asignaciones[m] if o not in self.seleccion]
        self.asignaciones[material] = sorted(set(self.asignaciones.get(material, [])) | set(self.seleccion))
        return len(self.seleccion)

    def renombrar(self, material, nombre):
        nuevo = rc.nombre_material(nombre)
        self.mats[nuevo] = self.mats.pop(material)
        if material in self.asignaciones:
            self.asignaciones[nuevo] = self.asignaciones.pop(material)
        return nuevo

    def materiales(self):
        return [{"nombre": m, "tipo": "openPBRSurface", "objetos": len(self.asignaciones.get(m, [])),
                 "texturas": len(self.conexiones.get(m, [])), "rotas": 0, "muestrario": True,
                 "destino": d["destino"], "con_prefijo": m.startswith("M_")} for m, d in self.mats.items()]

    def borrar_sin_usar(self):
        sin = [m for m in self.mats if not self.asignaciones.get(m)]
        for m in sin:
            del self.mats[m]
        return len(sin)

    def texturas_de(self, material):
        return {c["entrada"]: {"espacio": c["espacio"], "nombre": c["nombre"]} for c in self.conexiones.get(material, [])}

    def conectar_texturas(self, material, conexiones, opciones=None):
        self.conexiones[material] = list(conexiones)
        return [c["entrada"] for c in conexiones]

    def objetos_seleccionados(self):
        return list(self.seleccion)

    def enviar_a_painter(self, objetos, destino, motor, resolucion, nombre=None):
        carpeta = ic.carpeta_envio(self.carpeta_proyecto, objetos[0])
        juegos = {m[2:]: dict(self.mats[m]["receta"], material=m) for m, o in self.asignaciones.items()
                  if set(o) & set(objetos)}
        envio = ic.nueva_receta_envio(objetos[0], objetos[0] + ".fbx", juegos, destino, motor, resolucion)
        envio["materiales"] = {j: r["material"] for j, r in juegos.items()}
        ic.enviar(carpeta, envio)
        self.envios_hechos.append((objetos, destino, motor, resolucion))
        return carpeta

    def envios(self):
        return ic.envios_del_proyecto(self.carpeta_proyecto)

    def aplicar_manifiesto(self, carpeta, opciones=None):
        from muestrario import texturas as tx
        m = ic.leer_manifiesto(carpeta)
        envio = ic.leer_json(os.path.join(carpeta, ic.RECETA))
        salida = []
        for juego, rutas in m["juegos"].items():
            material = envio["materiales"].get(juego)
            analisis = tx.analizar(rutas)
            conexiones = [c.como_dict() for g in analisis.values() for c in g.conexiones.values()]
            salida.append((material, self.conectar_texturas(material, conexiones)))
        return salida


@unittest.skipIf(QtWidgets is None, "sin PySide6")
class PruebaVentana(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.mkdtemp()
        os.environ["MUESTRARIO_CASA"] = os.path.join(self.temporal, "casa")
        self.proyecto = os.path.join(self.temporal, "proyecto")
        os.makedirs(self.proyecto)
        self.servicios = ServiciosFalsos(self.proyecto)
        self.preferencias = os.path.join(self.temporal, "prefs")
        self.v = VentanaMuestrario(self.servicios, Ajustes(self.preferencias), self.preferencias)
        self.v.resize(1000, 700)

    def tearDown(self):
        self.v.cerrar()
        self.v.deleteLater()
        os.environ.pop("MUESTRARIO_CASA", None)
        shutil.rmtree(self.temporal)

    def esperar_miniaturas(self):
        for _ in range(2000):
            if not self.v._cola_miniaturas:
                break
            self.v._siguiente_miniatura()

    def elegir_familia(self, clave):
        for i in range(self.v.lista_familias.count()):
            if self.v.lista_familias.item(i).data(QtCore.Qt.UserRole) == clave:
                self.v.lista_familias.setCurrentRow(i)
                return
        self.fail("no hay familia " + clave)

    def item_receta(self, nombre):
        for i in range(self.v.lista_recetas.count()):
            it = self.v.lista_recetas.item(i)
            if it.data(QtCore.Qt.UserRole)["nombre"] == nombre:
                return it
        self.fail("no está " + nombre)

    def test_abre_con_biblioteca(self):
        self.assertGreater(self.v.lista_familias.count(), 12)
        self.elegir_familia("metales")
        self.assertGreater(self.v.lista_recetas.count(), 20)
        self.esperar_miniaturas()
        self.assertFalse(self.item_receta("Oro").icon().isNull())
        self.assertIsNotNone(self.v.vista.pixmap())
        # Las miniaturas se guardan en disco para la próxima vez.
        self.assertTrue(os.listdir(os.path.join(self.preferencias, "miniaturas")))

    def test_buscar(self):
        self.elegir_familia("")
        self.v.campo_buscar.setText("marmol")
        nombres = [self.v.lista_recetas.item(i).data(QtCore.Qt.UserRole)["nombre"]
                   for i in range(self.v.lista_recetas.count())]
        self.assertIn("Mármol blanco", nombres)
        self.assertTrue(all("rmol" in n for n in nombres))

    def test_elegir_y_asignar(self):
        self.elegir_familia("metales")
        self.v._al_elegir_receta(self.item_receta("Cobre"))
        self.assertIsNone(self.v.material)
        self.assertEqual(self.v.receta["nombre"], "Cobre")
        self.assertEqual(self.v.deslizadores["metal"].valor(), 1.0)
        self.v.asignar()
        self.assertEqual(self.v.material, "M_Cobre")
        self.assertEqual(self.servicios.asignaciones["M_Cobre"], ["pCube1"])
        # Con material vinculado, los cambios se escriben en la escena.
        self.v.deslizadores["rugosidad"].poner(0.9)
        self.v.deslizadores["rugosidad"].cambiado.emit(0.9)
        self.v._aplicar_ahora()
        self.assertAlmostEqual(self.servicios.mats["M_Cobre"]["receta"]["rugosidad"], 0.9)
        # Otra receta desvincula y crea un material nuevo.
        self.v._al_doble_clic_receta(self.item_receta("Oro"))
        self.assertEqual(self.v.material, "M_Oro")
        self.assertEqual(self.servicios.asignaciones["M_Cobre"], [])

    def test_cuentagotas(self):
        self.v.asignar()
        material = self.v.material
        self.v.cargar_receta(rc.nueva(nombre="Otra"))
        self.v.cuentagotas()
        self.assertEqual(self.v.material, material)
        self.servicios.seleccion = ["nada"]
        self.v.cuentagotas()
        self.assertIn("Selecciona", self.v.barra_estado.text())

    def test_destino_juego(self):
        self.elegir_familia("transparentes")
        self.v._al_elegir_receta(self.item_receta("Vidrio"))
        self.v.boton_juego.click()
        self.assertEqual(self.v.destino, rc.JUEGO)
        self.assertEqual(self.servicios.destino_guardado, (rc.JUEGO, "unreal"))
        self.assertFalse(self.v.deslizadores["barniz"].isEnabled())
        self.assertTrue(self.v.combo_motor.isVisibleTo(self.v))
        self.assertIn("alfa", self.v.rotulos["transparencia"].text())
        # «Transparencia (alfa)» en juego mueve la opacidad.
        self.v._cambiar("transparencia", 0.7)
        self.assertEqual(self.v.receta["transparencia"], 0.0)
        self.assertAlmostEqual(self.v.receta["opacidad"], 0.3)
        # Solo recetas que sirven para juego si está marcada la casilla.
        self.elegir_familia("organicos")
        nombres = [self.v.lista_recetas.item(i).data(QtCore.Qt.UserRole)["nombre"]
                   for i in range(self.v.lista_recetas.count())]
        self.assertIn("Piel (juego)", nombres)
        self.assertNotIn("Piel clara", nombres)
        self.v.combo_motor.setCurrentIndex(self.v.combo_motor.findData("unity"))
        self.assertEqual(self.servicios.destino_guardado, (rc.JUEGO, "unity"))
        self.v.boton_render.click()
        self.assertTrue(self.v.deslizadores["barniz"].isEnabled())

    def test_guardar_receta_propia(self):
        self.v.receta["nombre"] = "Mi rojo"
        ruta = self.v.biblioteca.guardar_mia(dict(self.v.receta))
        self.assertTrue(os.path.isfile(ruta))
        self.v._rellenar_familias(seleccionar="mis_recetas")
        self.assertEqual(self.v.lista_recetas.count(), 1)

    def test_texturas_por_carpeta(self):
        carpeta = os.path.join(self.proyecto, "sourceimages", "silla")
        os.makedirs(carpeta)
        for mapa in ("BaseColor", "Roughness", "Metallic", "Normal_OpenGL", "AO"):
            png(os.path.join(carpeta, "silla_Madera_{}.png".format(mapa)), 8, 8)
        self.v.campo_carpeta.setText(carpeta)
        self.v.analizar_carpeta()
        self.assertEqual(self.v.arbol_texturas.topLevelItemCount(), 1)
        self.assertEqual(self.v.arbol_texturas.topLevelItem(0).childCount(), 5)
        self.v.conectar_texturas()
        self.assertIn("M_Madera", self.servicios.conexiones)
        self.assertEqual({c["entrada"] for c in self.servicios.conexiones["M_Madera"]},
                         {"color", "rugosidad", "metal", "normal"})
        self.assertEqual(self.v.material, "M_Madera")

    def test_ida_y_vuelta_painter(self):
        self.v.asignar()
        material = self.v.material
        self.v.pestanas.setCurrentIndex(3)
        self.v.enviar_a_painter()
        self.assertEqual(len(self.servicios.envios_hechos), 1)
        self.assertEqual(self.v.lista_envios.count(), 1)
        self.assertEqual(len(ic.avisos_pendientes()), 1)
        carpeta = ic.envios_del_proyecto(self.proyecto)[0]
        # Painter exporta: escribe texturas y manifiesto.
        juego = material[2:]
        rutas = []
        for mapa in ("BaseColor", "Roughness", "Metallic", "Normal_OpenGL"):
            ruta = os.path.join(carpeta, "texturas", "{}_{}.png".format(juego, mapa))
            png(ruta, 8, 8)
            rutas.append(ruta)
        ic.escribir_manifiesto(carpeta, {juego: rutas})
        self.v.vigilar_painter()
        self.assertEqual(len(self.servicios.conexiones[material]), 4)
        self.assertIn("4", self.v.registro.toPlainText())
        # Sin cambios nuevos no se vuelve a aplicar.
        self.servicios.conexiones.clear()
        self.v.vigilar_painter()
        self.assertEqual(self.servicios.conexiones, {})

    def test_escena(self):
        self.v.asignar()
        self.v.nuevo_material()
        self.servicios.seleccion = ["pSphere1"]
        self.servicios.crear_material(rc.nueva(nombre="suelto"), "render", "suelto")
        self.servicios.mats["sin_prefijo"] = self.servicios.mats.pop("M_suelto")
        self.v.refrescar_escena()
        self.assertEqual(self.v.tabla_escena.rowCount(), 3)
        self.v._poner_prefijos()
        self.assertIn("M_sin_prefijo", self.servicios.mats)
        n_antes = len(self.servicios.mats)
        QtWidgets.QMessageBox.question = staticmethod(lambda *a, **k: QtWidgets.QMessageBox.Yes)
        self.v._borrar_sin_usar()
        self.assertLess(len(self.servicios.mats), n_antes)

    def test_receta_de_clase(self):
        clase = os.path.join(self.temporal, "clase")
        os.makedirs(clase)
        with open(os.path.join(clase, "r.json"), "w", encoding="utf-8") as f:
            f.write('{"nombre": "Receta del profe", "color": "#336699"}')
        self.v.campo_clase.setText(clase)
        self.v._al_cambiar_clase()
        self.assertEqual(self.v.lista_recetas.count(), 1)
        self.assertEqual(self.v.ajustes["carpeta_clase"], clase)


if __name__ == "__main__":
    unittest.main()
