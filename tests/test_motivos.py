"""Pruebas sin Maya de los motivos: catálogo, plan, medidas y pestaña Motivo."""

import os
import shutil
import sys
import tempfile
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "scripts"))
sys.path.insert(0, os.path.join(RAIZ, "tests"))
sys.path.insert(0, os.path.join(RAIZ, "herramientas"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from materials import motivos as mv  # noqa: E402
from materials import receta as rc  # noqa: E402

try:
    import numpy  # noqa: F401
    import PIL  # noqa: F401
    import generar_motivos_prueba as gen
except ImportError:  # pragma: no cover
    gen = None

_CATALOGO = {}


def catalogo_de_prueba():
    """Genera una vez los 6 motivos de prueba (pequeños) en una carpeta temporal."""
    if "carpeta" not in _CATALOGO:
        carpeta = tempfile.mkdtemp()
        gen.generar(carpeta, 64)
        _CATALOGO["carpeta"] = carpeta
    return _CATALOGO["carpeta"]


def tearDownModule():
    if "carpeta" in _CATALOGO:
        shutil.rmtree(_CATALOGO.pop("carpeta"), ignore_errors=True)


class PruebaNormalizar(unittest.TestCase):
    def test_apagado_por_defecto(self):
        self.assertFalse(mv.normalizar(None)["activo"])
        self.assertFalse(mv.normalizar({})["activo"])
        self.assertEqual(mv.normalizar(None)["proyeccion"], "caja")

    def test_valores_fuera_de_rango(self):
        m = mv.normalizar({"activo": 1, "desgaste": 7, "proyeccion": "rara", "color2": "verde", "pieza_cm": -3,
                           "eje": "w", "otra": 1})
        self.assertTrue(m["activo"])
        self.assertEqual(m["desgaste"], 1.0)
        self.assertEqual(m["proyeccion"], "caja")
        self.assertEqual(m["color2"], mv.DEFECTO["color2"])
        self.assertEqual(m["pieza_cm"], 0.0)
        self.assertEqual(m["eje"], "y")
        self.assertNotIn("otra", m)

    def test_cambios(self):
        a = mv.normalizar({"activo": True, "estructura": "x"})
        self.assertEqual(mv.cambios(a, a), "nada")
        self.assertEqual(mv.cambios(a, dict(a, pieza_cm=30)), "vivo")
        self.assertEqual(mv.cambios(a, dict(a, color_junta="#ffffff")), "vivo")
        self.assertEqual(mv.cambios(a, dict(a, espacio="mundo")), "reproyectar")
        self.assertEqual(mv.cambios(a, dict(a, proyeccion="uv")), "red")
        self.assertEqual(mv.cambios(a, dict(a, estructura="y", pieza_cm=3)), "red")

    def test_triplanar_no_va_a_juego(self):
        self.assertEqual(mv.proyeccion_valida("triplanar", "juego"), "caja")
        self.assertEqual(mv.proyeccion_valida("triplanar", "render"), "triplanar")

    def test_la_receta_guarda_el_motivo(self):
        r = rc.normalizar({"nombre": "Muro", "motivo": {"activo": True, "estructura": "ladrillo_soga"}})
        self.assertEqual(r["motivo"]["estructura"], "ladrillo_soga")
        self.assertNotIn("motivo", rc.nueva(nombre="Otro"))

    def test_desfase_fijo_por_objeto(self):
        self.assertEqual(mv.desfase("pCube1"), mv.desfase("pCube1"))
        self.assertNotEqual(mv.desfase("pCube1"), mv.desfase("pCube2"))
        self.assertEqual(mv.desfase("pCube1", activo=False), (0.0, 0.0))
        u, v = mv.desfase("muro")
        self.assertTrue(0 <= u <= 1 and 0 <= v <= 1)

    def test_vuelta_cerrada(self):
        # Columna de 1 m de circunferencia con piezas de 30 cm: 3 piezas enteras -> 0,9 m de U.
        self.assertAlmostEqual(mv.vuelta_cerrada(100.0, 30.0), 0.9)
        self.assertAlmostEqual(mv.vuelta_cerrada(100.0, 0.0), 1.0)
        self.assertAlmostEqual(mv.vuelta_cerrada(10.0, 50.0), 0.5)


@unittest.skipIf(gen is None, "sin numpy o Pillow")
class PruebaCatalogo(unittest.TestCase):
    def setUp(self):
        self.cat = mv.Catalogo(catalogo_de_prueba())

    def test_lee_estructuras_y_acabados(self):
        self.assertEqual(len(self.cat), 6)
        self.assertEqual(sorted(m.id for m in self.cat.estructuras()),
                         ["baldosa_cuadrada", "ladrillo_soga", "tablas_madera"])
        e = self.cat.estructura("ladrillo_soga")
        self.assertEqual(e.tile_cm, (50.0, 12.5))
        self.assertEqual(e.pieza_cm, 24.0)
        self.assertTrue(e.prueba)
        self.assertTrue(e.mapa("mascara").endswith(os.path.join("1k", "mascara.png")))
        self.assertTrue(e.mapa("mascara", "4k").endswith(os.path.join("1k", "mascara.png")))
        self.assertIsNone(e.mapa("normal"))
        self.assertTrue(e.miniatura())

    def test_ignora_incompletos_y_repetidos(self):
        otra = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(otra, "acabados", "roto"))
            with open(os.path.join(otra, "acabados", "roto", "motivo.json"), "w") as f:
                f.write('{"id": "roto"}')
            shutil.copytree(os.path.join(catalogo_de_prueba(), "acabados", "hormigon"),
                            os.path.join(otra, "acabados", "hormigon"))
            cat = mv.Catalogo([otra, catalogo_de_prueba()])
            self.assertIsNone(cat.acabado("roto"))
            self.assertEqual(cat.acabado("hormigon").carpeta, os.path.join(otra, "acabados", "hormigon"))
            self.assertEqual(len(cat), 6)
        finally:
            shutil.rmtree(otra)

    def test_acabado_propuesto(self):
        self.assertEqual(mv.acabado_propuesto({"nombre": "Acero cepillado", "familia": "metales"}, self.cat),
                         "cepillado")
        self.assertEqual(mv.acabado_propuesto({"nombre": "Naranja", "familia": "comida"}, self.cat), "piel_naranja")
        self.assertEqual(mv.acabado_propuesto({"nombre": "Muro", "familia": "construccion"}, self.cat), "hormigon")
        self.assertEqual(mv.acabado_propuesto({"nombre": "Seda", "familia": "telas"}, self.cat), "")

    def test_recomendados_primero(self):
        receta = {"nombre": "Ladrillo visto", "familia": "construccion"}
        orden = [m.id for m in self.cat.ordenados(mv.ESTRUCTURAS, receta)]
        self.assertEqual(orden[0], "ladrillo_soga")
        orden = [m.id for m in self.cat.ordenados(mv.ACABADOS, receta)]
        self.assertEqual(orden[0], "hormigon")

    def test_plan_apagado_o_vacio(self):
        self.assertIsNone(mv.plan(None, self.cat))
        self.assertIsNone(mv.plan({"activo": True}, self.cat, {"nombre": "Seda", "familia": "telas"}))

    def test_plan_ladrillo(self):
        receta = {"nombre": "Oro", "familia": "metales"}  # sin restricción: muro de oro en ladrillo
        p = mv.plan({"activo": True, "estructura": "ladrillo_soga"}, self.cat, receta)
        self.assertEqual(p["motivo"]["pieza_cm"], 24.0)
        self.assertEqual(p["motivo"]["acabado"], "cepillado")
        self.assertEqual(p["motivo"]["color_junta"], "#9a948a")
        self.assertEqual(set(p["capas"]), {"estructura", "acabado"})
        self.assertTrue(os.path.isfile(p["capas"]["estructura"]["mapas"]["mascara"]))
        self.assertAlmostEqual(p["tile_u_cm"], 50.0)
        # Un metro de muro = 2 imágenes de ladrillo a lo ancho y 8 a lo alto.
        r = mv.repeticiones(p["motivo"], self.cat.estructura("ladrillo_soga"), self.cat.acabado("cepillado"))
        self.assertAlmostEqual(r["estructura"][0], 2.0)
        self.assertAlmostEqual(r["estructura"][1], 8.0)
        self.assertAlmostEqual(r["acabado"][0], 5.0)

    def test_pieza_de_85_cm(self):
        e = self.cat.estructura("baldosa_cuadrada")
        m = mv.normalizar({"activo": True, "estructura": e.id, "pieza_cm": 85.0})
        ancho, alto = mv.tamano_tile(m, e)
        self.assertAlmostEqual(ancho, 60.8 * 85.0 / 30.0)
        f = mv.factores(e, None)
        self.assertAlmostEqual(f["kU"] / 85.0, 100.0 / ancho)

    def test_plan_falta_estructura(self):
        p = mv.plan({"activo": True, "estructura": "no_existe", "acabado": "hormigon"}, self.cat)
        self.assertEqual(p["faltan"], ["no_existe"])
        self.assertEqual(set(p["capas"]), {"acabado"})

    def test_plan_juego_sin_triplanar(self):
        p = mv.plan({"activo": True, "acabado": "hormigon", "proyeccion": "triplanar"}, self.cat, destino="juego")
        self.assertEqual(p["motivo"]["proyeccion"], "caja")

    def test_resumen(self):
        m = {"activo": True, "estructura": "ladrillo_soga", "acabado": "hormigon"}
        self.assertEqual(mv.resumen(m, self.cat), "Ladrillo a soga (prueba) · Hormigón (prueba) · caja")
        self.assertEqual(mv.resumen({}, self.cat), "")


try:
    from PySide6 import QtWidgets
except ImportError:  # pragma: no cover
    QtWidgets = None

if QtWidgets is not None:
    from materials.ajustes import Ajustes
    from materials.ventana import VentanaMaterials
    from test_qt import ServiciosFalsos

    class ServiciosConMotivo(ServiciosFalsos):
        def __init__(self, proyecto):
            ServiciosFalsos.__init__(self, proyecto)
            self.llamadas = []
            self.motivos = {}

        def aplicar_motivo(self, material, plan, receta, destino):
            self.llamadas.append(("aplicar", material, plan["motivo"]["proyeccion"]))
            self.motivos[material] = dict(plan["motivo"])
            return material + "_tt_control"

        def ajustar_motivo(self, material, motivo):
            self.llamadas.append(("ajustar", material, motivo["pieza_cm"]))
            self.motivos[material] = dict(motivo)
            return True

        def reproyectar(self, material):
            self.llamadas.append(("reproyectar", material))
            return ["pCubeShape1"]

        def quitar_motivo(self, material, receta, destino):
            self.llamadas.append(("quitar", material))
            self.motivos.pop(material, None)
            return True

        def leer_receta(self, material):
            r = ServiciosFalsos.leer_receta(self, material)
            if material in self.motivos:
                r["motivo"] = dict(self.motivos[material], activo=True)
            return r


@unittest.skipIf(QtWidgets is None or gen is None, "sin PySide6, numpy o Pillow")
class PruebaPestanaMotivo(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.mkdtemp()
        os.environ["MATERIALS_CASA"] = os.path.join(self.temporal, "casa")
        proyecto = os.path.join(self.temporal, "proyecto")
        os.makedirs(proyecto)
        self.servicios = ServiciosConMotivo(proyecto)
        preferencias = os.path.join(self.temporal, "prefs")
        ajustes = Ajustes(preferencias)
        ajustes["carpeta_motivos"] = catalogo_de_prueba()
        self.v = VentanaMaterials(self.servicios, ajustes, preferencias)
        self.p = self.v.pestana_motivo

    def tearDown(self):
        self.v.cerrar()
        self.v.deleteLater()
        os.environ.pop("MATERIALS_CASA", None)
        shutil.rmtree(self.temporal)

    def elegir_estructura(self, ident):
        for i in range(self.p.lista_estructuras.count()):
            if self.p.lista_estructuras.item(i).data(0x0100) == ident:
                self.p.lista_estructuras.setCurrentRow(i)
                return
        self.fail("no está " + ident)

    def test_pestana_y_apagado(self):
        self.assertEqual(self.v.pestanas.tabText(2), "Motivo")
        self.assertFalse(self.p.casilla.isChecked())
        self.assertFalse(self.p.cuerpo.isEnabled())
        self.assertEqual(self.p.lista_estructuras.count(), 4)   # «Ninguna» + 3
        self.assertIn("3 estructuras y 3 acabados", self.v.etiqueta_motivos.text())
        # Las otras pestañas siguen respondiendo a su página (los índices se han movido).
        self.v.pestanas.setCurrentWidget(self.v.pagina_escena)
        self.v.pestanas.setCurrentWidget(self.v.pagina_painter)

    def test_sin_catalogo(self):
        self.v.campo_motivos.setText(os.path.join(self.temporal, "vacia"))
        self.v._al_cambiar_carpeta_motivos()
        self.assertFalse(self.p.casilla.isEnabled())
        self.assertFalse(self.p.cuerpo.isVisibleTo(self.p))

    def test_en_vivo_sobre_material(self):
        self.v.asignar()
        material = self.v.material
        self.assertEqual(self.servicios.llamadas, [])   # sin motivo no se toca nada
        self.p.casilla.setChecked(True)
        # «Pintura de coche» propone un acabado que no está instalado: aún no hay nada que montar.
        self.assertEqual(self.servicios.llamadas, [])
        self.assertIn("Elige", self.p.etiqueta_estado.text())
        self.elegir_estructura("ladrillo_soga")
        self.assertEqual(self.servicios.llamadas[-1], ("aplicar", material, "caja"))
        self.assertEqual(self.servicios.motivos[material]["estructura"], "ladrillo_soga")
        self.assertEqual(self.p.deslizadores["pieza_cm"].valor(), 24.0)
        n = len(self.servicios.llamadas)
        # Pieza de 85 cm: solo valores (sin rehacer la red).
        self.p.deslizadores["pieza_cm"].cambiado.emit(85.0)
        self.p._aplicar_vivo()
        self.assertEqual(self.servicios.llamadas[n:], [("ajustar", material, 85.0)])
        # Espacio: reproyectar.
        self.p.combo_espacio.setCurrentIndex(self.p.combo_espacio.findData("mundo"))
        self.assertIn(("reproyectar", material), self.servicios.llamadas[n:])
        # Proyección: rehacer la red.
        self.p.combo_proyeccion.setCurrentIndex(self.p.combo_proyeccion.findData("cilindrica"))
        self.assertEqual(self.servicios.llamadas[-1], ("aplicar", material, "cilindrica"))
        self.assertTrue(self.p.combo_eje.isVisibleTo(self.p))
        # Apagar: quitar.
        self.p.casilla.setChecked(False)
        self.assertEqual(self.servicios.llamadas[-1], ("quitar", material))

    def test_receta_con_motivo_crea_material_con_motivo(self):
        self.p.casilla.setChecked(True)
        self.elegir_estructura("baldosa_cuadrada")
        self.assertEqual(self.servicios.llamadas, [])   # sin material todavía
        self.assertEqual(self.v.receta["motivo"]["estructura"], "baldosa_cuadrada")
        self.v.asignar()
        self.assertEqual(self.servicios.llamadas, [("aplicar", self.v.material, "caja")])

    def test_cuentagotas_lee_el_motivo(self):
        self.p.casilla.setChecked(True)
        self.elegir_estructura("tablas_madera")
        self.v.asignar()
        material = self.v.material
        self.v.cargar_receta(rc.nueva(nombre="Otra"))
        self.assertFalse(self.p.casilla.isChecked())
        self.v.editar_material(material)
        self.assertTrue(self.p.casilla.isChecked())
        self.assertEqual(self.p.motivo["estructura"], "tablas_madera")
        # Ya está aplicado: un cambio en vivo no rehace la red.
        n = len(self.servicios.llamadas)
        self.p.deslizadores["desgaste"].cambiado.emit(0.7)
        self.p._aplicar_vivo()
        self.assertEqual([x[0] for x in self.servicios.llamadas[n:]], ["ajustar"])

    def test_triplanar_en_juego(self):
        self.p.casilla.setChecked(True)
        self.p.combo_proyeccion.setCurrentIndex(self.p.combo_proyeccion.findData("triplanar"))
        self.assertTrue(self.p.deslizadores["mezcla"].isVisibleTo(self.p))
        self.v._poner_destino("juego")
        indice = self.p.combo_proyeccion.findData("triplanar")
        self.assertFalse(self.p.combo_proyeccion.model().item(indice).isEnabled())
        self.assertIn("Caja", self.p.etiqueta_proyeccion.text())

    def test_color_de_pieza_es_el_de_la_receta(self):
        self.p.casilla.setChecked(True)
        self.p._al_color_pieza("#336699")
        self.assertEqual(self.v.receta["color"], "#336699")
        self.assertEqual(self.v.boton_color.color(), "#336699")

    def test_guardar_receta_con_motivo(self):
        self.p.casilla.setChecked(True)
        self.elegir_estructura("ladrillo_soga")
        ruta = self.v.biblioteca.guardar_mia(dict(self.v.receta, nombre="Muro de prueba"))
        self.v.biblioteca.recargar()
        r = self.v.biblioteca.receta("Muro de prueba")
        self.assertTrue(os.path.isfile(ruta))
        self.assertEqual(r["motivo"]["estructura"], "ladrillo_soga")


if __name__ == "__main__":
    unittest.main()
