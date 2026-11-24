"""Ventana de Muestrario (Qt). No llama a Maya: todo pasa por ``servicios``.

Estado de la ventana:
- ``receta``: lo que se ve en la vista previa y en los controles.
- ``material``: el material de la escena que se está editando, o None. Si hay
  material, cada cambio se escribe en él al momento. Al elegir una receta de la
  biblioteca la ventana se desvincula, y «Asignar a selección» crea uno nuevo.
"""

import os
import traceback

import muestrario
from muestrario import biblioteca as bib
from muestrario import comprobacion as chk
from muestrario import intercambio as ic
from muestrario import receta as rc
from muestrario import texturas as tx
from muestrario import vista_previa as vp
from muestrario.i18n import t
from muestrario.qt import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt
TAM_VISTA = 200
TAM_MINI = 64
MOTORES_JUEGO = ("unreal", "unity", "gltf")
COLORES_AVISO = {chk.OK: "#7ccf98", chk.AVISO: "#f0c060", chk.INFO: "#8cc4ea"}
SIMBOLOS = {chk.OK: "✓", chk.AVISO: "!", chk.INFO: "i"}


class Servicios(object):
    """Servicios sin Maya (para probar la ventana). ``escena_maya.ServiciosMaya`` los implementa de verdad."""
    en_maya = False

    def openpbr_disponible(self): return True
    def proyecto(self): return ""
    def destino_escena(self, defecto): return defecto
    def motor_escena(self, defecto): return defecto
    def guardar_destino(self, destino, motor): pass
    def existe(self, material): return False
    def crear_material(self, receta, destino, nombre=None): return None
    def actualizar_material(self, material, receta, destino): return []
    def leer_receta(self, material): return rc.nueva(nombre=material)
    def material_seleccionado(self): return None
    def asignar(self, material, elementos=None): return 0
    def seleccionar_objetos(self, material): return 0
    def seleccionar_nodo(self, material): pass
    def renombrar(self, material, nombre): return material
    def materiales(self): return []
    def borrar_sin_usar(self): return 0
    def convertir(self, material, destino): return None
    def texturas_de(self, material): return {}
    def conectar_texturas(self, material, conexiones, opciones=None): return []
    def recargar_texturas(self, material=None): return 0
    def reparar_rutas(self, carpetas_extra=()): return [], []
    def copiar_al_proyecto(self): return 0
    def objetos_seleccionados(self): return []
    def enviar_a_painter(self, objetos, destino, motor, resolucion, nombre=None): return ""
    def envios(self): return []
    def aplicar_manifiesto(self, carpeta, opciones=None): return []
    def abrir_painter(self, ruta_preferida=""): return False


def imagen_de(receta, tam, destino):
    datos = vp.pixeles(receta, tam, destino)
    imagen = QtGui.QImage(datos, tam, tam, tam * 3, QtGui.QImage.Format_RGB888)
    return imagen.copy()


class BotonColor(QtWidgets.QPushButton):
    cambiado = QtCore.Signal(str)

    def __init__(self, padre=None, permite_auto=False):
        super(BotonColor, self).__init__(padre)
        self._color = "#cccccc"
        self._auto = False
        self.permite_auto = permite_auto
        self.setFixedHeight(22)
        self.setMinimumWidth(70)
        self.clicked.connect(self._elegir)
        self._pintar()

    def color(self):
        return None if self._auto else self._color

    def poner(self, color, auto_desde=None):
        self._auto = color is None and self.permite_auto
        self._color = color or auto_desde or "#cccccc"
        self._pintar()

    def _pintar(self):
        claro = QtGui.QColor(self._color).lightnessF() > 0.55
        texto = t("color_auto") if self._auto else self._color.upper()
        self.setText(texto)
        self.setStyleSheet("QPushButton{{background:{};color:{};border:1px solid #222;border-radius:3px}}".format(
            self._color, "#111" if claro else "#eee"))

    def _elegir(self):
        dialogo = QtWidgets.QColorDialog(QtGui.QColor(self._color), self)
        dialogo.setOption(QtWidgets.QColorDialog.DontUseNativeDialog, True)
        dialogo.currentColorChanged.connect(lambda c: self._en_vivo(c.name()))
        anterior = (self._color, self._auto)
        if dialogo.exec():
            self._en_vivo(dialogo.currentColor().name())
        else:
            self._color, self._auto = anterior
            self._pintar()
            self.cambiado.emit(self.color() or "")

    def _en_vivo(self, nombre):
        self._color = nombre
        self._auto = False
        self._pintar()
        self.cambiado.emit(nombre)


class Deslizador(QtWidgets.QWidget):
    """Deslizador 0..1 (o min..max) con casilla numérica, sin bucles de señales."""
    cambiado = QtCore.Signal(float)

    def __init__(self, minimo=0.0, maximo=1.0, decimales=2, padre=None):
        super(Deslizador, self).__init__(padre)
        self.minimo, self.maximo = minimo, maximo
        capa = QtWidgets.QHBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        self.barra = QtWidgets.QSlider(Qt.Horizontal)
        self.barra.setRange(0, 1000)
        self.caja = QtWidgets.QDoubleSpinBox()
        self.caja.setRange(minimo, maximo)
        self.caja.setDecimals(decimales)
        self.caja.setSingleStep((maximo - minimo) / 100.0)
        self.caja.setFixedWidth(64)
        capa.addWidget(self.barra, 1)
        capa.addWidget(self.caja)
        self._quieto = False
        self.barra.valueChanged.connect(self._de_barra)
        self.caja.valueChanged.connect(self._de_caja)

    def valor(self):
        return self.caja.value()

    def poner(self, valor):
        self._quieto = True
        self.caja.setValue(valor)
        self.barra.setValue(int(round((valor - self.minimo) / (self.maximo - self.minimo) * 1000)))
        self._quieto = False

    def _de_barra(self, n):
        if self._quieto:
            return
        valor = self.minimo + (self.maximo - self.minimo) * n / 1000.0
        self._quieto = True
        self.caja.setValue(valor)
        self._quieto = False
        self.cambiado.emit(valor)

    def _de_caja(self, valor):
        if self._quieto:
            return
        self._quieto = True
        self.barra.setValue(int(round((valor - self.minimo) / (self.maximo - self.minimo) * 1000)))
        self._quieto = False
        self.cambiado.emit(valor)


class VentanaMuestrario(QtWidgets.QWidget):
    material_cambiado = QtCore.Signal(str)

    def __init__(self, servicios=None, ajustes=None, carpeta_preferencias=None, padre=None):
        super(VentanaMuestrario, self).__init__(padre)
        self.setObjectName("MuestrarioVentana")
        self.servicios = servicios or Servicios()
        self.ajustes = ajustes
        self.carpeta_preferencias = carpeta_preferencias
        carpeta_mias = os.path.join(carpeta_preferencias, "recetas") if carpeta_preferencias else None
        self.biblioteca = bib.Biblioteca(carpeta_mias, self._ajuste("carpeta_clase") or None)
        self.carpeta_miniaturas = os.path.join(carpeta_preferencias, "miniaturas") if carpeta_preferencias else None
        self.destino = self.servicios.destino_escena(self._ajuste("destino"))
        self.motor = self.servicios.motor_escena(self._ajuste("motor_juego"))
        self.receta = rc.nueva(**self._primera_receta())
        self.material = None
        self.analisis = {}
        self._huellas = {}
        self._miniaturas = {}
        self._cola_miniaturas = []
        self._cargando = False

        self._aplicar_t = QtCore.QTimer(self, singleShot=True, interval=120, timeout=self._aplicar_ahora)
        self._vista_t = QtCore.QTimer(self, singleShot=True, interval=40, timeout=self._pintar_vista)
        self._mini_t = QtCore.QTimer(self, interval=15, timeout=self._siguiente_miniatura)
        self._vigia_t = QtCore.QTimer(self, interval=1500, timeout=self.vigilar_painter)

        self._construir()
        self._poner_destino(self.destino, guardar=False)
        self.cargar_receta(self.receta, vincular=None)
        self._rellenar_familias()
        self.refrescar_escena()
        self.refrescar_envios()
        if self._ajuste("sincronizar"):
            self._vigia_t.start()

    # --- Utilidades ---------------------------------------------------------------------------

    def _ajuste(self, clave):
        from muestrario.ajustes import DEFECTOS
        return self.ajustes[clave] if self.ajustes is not None else DEFECTOS[clave]

    def _guardar_ajuste(self, clave, valor):
        if self.ajustes is not None:
            self.ajustes[clave] = valor

    def _primera_receta(self):
        r = self.biblioteca.receta("Pintura de coche roja")
        return dict(r) if r else {"nombre": "Material"}

    def mensaje(self, texto, error=False):
        self.barra_estado.setText(texto)
        self.barra_estado.setStyleSheet("color:{}".format("#f08080" if error else ""))

    def _seguro(self, funcion, *args):
        try:
            return funcion(*args)
        except Exception as error:  # se muestra en la ventana en vez de romperla
            traceback.print_exc()
            self.mensaje(t("error", e=error), error=True)
            return None

    # --- Construcción -------------------------------------------------------------------------

    def _construir(self):
        principal = QtWidgets.QVBoxLayout(self)
        principal.setContentsMargins(6, 6, 6, 6)
        principal.addLayout(self._barra_destino())
        division = QtWidgets.QSplitter(Qt.Horizontal)
        division.addWidget(self._panel_vista())
        self.pestanas = QtWidgets.QTabWidget()
        self.pestanas.addTab(self._pestana_biblioteca(), t("tab_biblioteca"))
        self.pestanas.addTab(self._pestana_material(), t("tab_material"))
        self.pestanas.addTab(self._pestana_texturas(), t("tab_texturas"))
        self.pestanas.addTab(self._pestana_painter(), t("tab_painter"))
        self.pestanas.addTab(self._pestana_escena(), t("tab_escena"))
        self.pestanas.addTab(self._pestana_ajustes(), t("tab_ajustes"))
        self.pestanas.currentChanged.connect(self._al_cambiar_pestana)
        division.addWidget(self.pestanas)
        division.setStretchFactor(1, 1)
        division.setSizes([240, 620])
        principal.addWidget(division, 1)
        self.barra_estado = QtWidgets.QLabel()
        self.barra_estado.setWordWrap(True)
        principal.addWidget(self.barra_estado)
        if not self.servicios.openpbr_disponible():
            self.mensaje(t("sin_openpbr"), error=True)

    def _barra_destino(self):
        fila = QtWidgets.QHBoxLayout()
        fila.addWidget(QtWidgets.QLabel(t("destino")))
        self.grupo_destino = QtWidgets.QButtonGroup(self)
        self.boton_render = QtWidgets.QToolButton(text=t("destino_render"), checkable=True)
        self.boton_juego = QtWidgets.QToolButton(text=t("destino_juego"), checkable=True)
        self.boton_render.setToolTip(t("destino_render_ayuda"))
        self.boton_juego.setToolTip(t("destino_juego_ayuda"))
        for b in (self.boton_render, self.boton_juego):
            b.setStyleSheet("QToolButton{padding:3px 10px}QToolButton:checked{background:#5285a6;color:white}")
            self.grupo_destino.addButton(b)
            fila.addWidget(b)
        self.boton_render.clicked.connect(lambda: self._poner_destino(rc.RENDER))
        self.boton_juego.clicked.connect(lambda: self._poner_destino(rc.JUEGO))
        self.combo_motor = QtWidgets.QComboBox()
        for m in MOTORES_JUEGO:
            self.combo_motor.addItem(t("motor_" + m), m)
        self.combo_motor.currentIndexChanged.connect(self._al_cambiar_motor)
        fila.addWidget(self.combo_motor)
        fila.addStretch(1)
        version = QtWidgets.QLabel("Muestrario " + muestrario.__version__)
        version.setStyleSheet("color:#888")
        fila.addWidget(version)
        return fila

    def _panel_vista(self):
        panel = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(panel)
        capa.setContentsMargins(0, 0, 6, 0)
        self.vista = QtWidgets.QLabel()
        self.vista.setFixedSize(TAM_VISTA, TAM_VISTA)
        self.vista.setAlignment(Qt.AlignCenter)
        self.vista.setToolTip(t("vista_ayuda"))
        capa.addWidget(self.vista, 0, Qt.AlignHCenter)
        self.campo_nombre = QtWidgets.QLineEdit()
        self.campo_nombre.setPlaceholderText(t("nombre_receta"))
        self.campo_nombre.editingFinished.connect(self._al_cambiar_nombre)
        capa.addWidget(self.campo_nombre)
        self.etiqueta_vinculo = QtWidgets.QLabel()
        self.etiqueta_vinculo.setWordWrap(True)
        self.etiqueta_vinculo.setStyleSheet("color:#9a9a9a")
        capa.addWidget(self.etiqueta_vinculo)
        self.etiqueta_chequeo = QtWidgets.QLabel()
        self.etiqueta_chequeo.setWordWrap(True)
        self.etiqueta_chequeo.setTextFormat(Qt.RichText)
        capa.addWidget(self.etiqueta_chequeo)
        self.etiqueta_nota = QtWidgets.QLabel()
        self.etiqueta_nota.setWordWrap(True)
        self.etiqueta_nota.setStyleSheet("color:#b8b8b8;font-style:italic")
        capa.addWidget(self.etiqueta_nota)
        capa.addStretch(1)
        self.boton_asignar = QtWidgets.QPushButton(t("asignar"))
        self.boton_asignar.setToolTip(t("asignar_ayuda"))
        self.boton_asignar.setStyleSheet("QPushButton{background:#5285a6;color:white;padding:5px}")
        self.boton_asignar.clicked.connect(self.asignar)
        capa.addWidget(self.boton_asignar)
        fila = QtWidgets.QHBoxLayout()
        self.boton_nuevo = QtWidgets.QPushButton(t("nuevo_material"))
        self.boton_nuevo.setToolTip(t("nuevo_material_ayuda"))
        self.boton_nuevo.clicked.connect(self.nuevo_material)
        self.boton_cuentagotas = QtWidgets.QPushButton(t("cuentagotas"))
        self.boton_cuentagotas.setToolTip(t("cuentagotas_ayuda"))
        self.boton_cuentagotas.clicked.connect(self.cuentagotas)
        fila.addWidget(self.boton_nuevo)
        fila.addWidget(self.boton_cuentagotas)
        capa.addLayout(fila)
        self.boton_guardar = QtWidgets.QPushButton(t("guardar_receta"))
        self.boton_guardar.setToolTip(t("guardar_receta_ayuda"))
        self.boton_guardar.clicked.connect(self.guardar_receta)
        capa.addWidget(self.boton_guardar)
        panel.setMinimumWidth(TAM_VISTA + 12)
        return panel

    def _pestana_biblioteca(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        fila = QtWidgets.QHBoxLayout()
        self.campo_buscar = QtWidgets.QLineEdit()
        self.campo_buscar.setPlaceholderText(t("buscar"))
        self.campo_buscar.setClearButtonEnabled(True)
        self.campo_buscar.textChanged.connect(self._rellenar_recetas)
        fila.addWidget(self.campo_buscar, 1)
        self.casilla_solo_destino = QtWidgets.QCheckBox(t("solo_destino"))
        self.casilla_solo_destino.setChecked(self._ajuste("solo_destino"))
        self.casilla_solo_destino.toggled.connect(self._al_solo_destino)
        fila.addWidget(self.casilla_solo_destino)
        capa.addLayout(fila)
        division = QtWidgets.QSplitter(Qt.Horizontal)
        self.lista_familias = QtWidgets.QListWidget()
        self.lista_familias.setMaximumWidth(190)
        self.lista_familias.currentRowChanged.connect(lambda _: self._rellenar_recetas())
        division.addWidget(self.lista_familias)
        self.lista_recetas = QtWidgets.QListWidget()
        self.lista_recetas.setViewMode(QtWidgets.QListView.IconMode)
        self.lista_recetas.setIconSize(QtCore.QSize(TAM_MINI, TAM_MINI))
        self.lista_recetas.setGridSize(QtCore.QSize(TAM_MINI + 50, TAM_MINI + 44))
        self.lista_recetas.setTextElideMode(Qt.ElideNone)
        self.lista_recetas.setResizeMode(QtWidgets.QListView.Adjust)
        self.lista_recetas.setMovement(QtWidgets.QListView.Static)
        self.lista_recetas.setWordWrap(True)
        self.lista_recetas.setUniformItemSizes(True)
        self.lista_recetas.itemClicked.connect(self._al_elegir_receta)
        self.lista_recetas.itemDoubleClicked.connect(self._al_doble_clic_receta)
        self.lista_recetas.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_recetas.customContextMenuRequested.connect(self._menu_receta)
        division.addWidget(self.lista_recetas)
        division.setStretchFactor(1, 1)
        capa.addWidget(division, 1)
        ayuda = QtWidgets.QLabel(t("biblioteca_ayuda"))
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("color:#9a9a9a")
        capa.addWidget(ayuda)
        return w

    def _pestana_material(self):
        w = QtWidgets.QWidget()
        exterior = QtWidgets.QVBoxLayout(w)
        desplazable = QtWidgets.QScrollArea()
        desplazable.setWidgetResizable(True)
        desplazable.setFrameShape(QtWidgets.QFrame.NoFrame)
        interior = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(interior)
        formulario = QtWidgets.QFormLayout()
        formulario.setLabelAlignment(Qt.AlignRight)
        self.boton_color = BotonColor()
        self.boton_color.cambiado.connect(lambda c: self._cambiar("color", c) if c else None)
        formulario.addRow(t("c_color"), self.boton_color)
        self.deslizadores = {}
        self.rotulos = {}
        for clave in rc.DESLIZADORES:
            d = Deslizador()
            d.cambiado.connect(lambda v, k=clave: self._cambiar(k, v))
            d.setToolTip(t("ayuda_" + clave))
            rotulo = QtWidgets.QLabel(t("c_" + clave))
            rotulo.setToolTip(t("ayuda_" + clave))
            self.deslizadores[clave] = d
            self.rotulos[clave] = rotulo
            formulario.addRow(rotulo, d)
        self.etiqueta_nits = QtWidgets.QLabel()
        self.etiqueta_nits.setStyleSheet("color:#9a9a9a")
        formulario.addRow("", self.etiqueta_nits)
        capa.addLayout(formulario)

        self.grupo_mas = QtWidgets.QGroupBox(t("mas"))
        self.grupo_mas.setCheckable(True)
        self.grupo_mas.setChecked(False)
        self.contenido_mas = QtWidgets.QWidget()
        QtWidgets.QVBoxLayout(self.grupo_mas).addWidget(self.contenido_mas)
        mas = QtWidgets.QFormLayout(self.contenido_mas)
        self.finos = {}
        self.colores_finos = {}
        finos = [("ior", 1.0, 3.0, 3), ("especular", 0.0, 1.0, 2), ("anisotropia", 0.0, 1.0, 2),
                 ("profundidad_transmision", 0.0, 100.0, 2), ("radio_subsuperficie", 0.0, 20.0, 2),
                 ("rugosidad_barniz", 0.0, 1.0, 2), ("ior_barniz", 1.0, 3.0, 2), ("rugosidad_pelusa", 0.0, 1.0, 2),
                 ("opacidad", 0.0, 1.0, 2), ("pelicula", 0.0, 1.0, 2), ("grosor_pelicula", 0.0, 2000.0, 0)]
        for clave, minimo, maximo, decimales in finos:
            d = Deslizador(minimo, maximo, decimales)
            d.cambiado.connect(lambda v, k=clave: self._cambiar(k, v))
            self.finos[clave] = d
            rotulo = QtWidgets.QLabel(t("c_" + clave))
            rotulo.setToolTip(t("ayuda_" + clave))
            mas.addRow(rotulo, d)
        for clave in ("color_especular", "color_barniz"):
            b = BotonColor()
            b.cambiado.connect(lambda c, k=clave: self._cambiar(k, c) if c else None)
            self.colores_finos[clave] = b
            mas.addRow(t("c_" + clave), b)
        for clave in ("color_transmision", "color_subsuperficie", "color_pelusa", "color_emision"):
            b = BotonColor(permite_auto=True)
            b.cambiado.connect(lambda c, k=clave: self._cambiar(k, c or None))
            fila = QtWidgets.QHBoxLayout()
            fila.addWidget(b, 1)
            auto = QtWidgets.QToolButton(text=t("color_auto"))
            auto.setToolTip(t("color_auto_ayuda"))
            auto.clicked.connect(lambda _=False, k=clave: self._cambiar(k, None))
            fila.addWidget(auto)
            self.colores_finos[clave] = b
            mas.addRow(t("c_" + clave), fila)
        self.casilla_pared = QtWidgets.QCheckBox(t("c_pared_fina"))
        self.casilla_pared.setToolTip(t("ayuda_pared_fina"))
        self.casilla_pared.toggled.connect(lambda v: self._cambiar("pared_fina", bool(v)))
        mas.addRow("", self.casilla_pared)
        self.grupo_mas.toggled.connect(self.contenido_mas.setVisible)
        self.contenido_mas.setVisible(False)
        capa.addWidget(self.grupo_mas)
        fila = QtWidgets.QHBoxLayout()
        self.boton_experto = QtWidgets.QPushButton(t("experto"))
        self.boton_experto.setToolTip(t("experto_ayuda"))
        self.boton_experto.clicked.connect(self._modo_experto)
        self.boton_restaurar = QtWidgets.QPushButton(t("restaurar"))
        self.boton_restaurar.setToolTip(t("restaurar_ayuda"))
        self.boton_restaurar.clicked.connect(self._restaurar)
        fila.addWidget(self.boton_experto)
        fila.addWidget(self.boton_restaurar)
        fila.addStretch(1)
        capa.addLayout(fila)
        capa.addStretch(1)
        desplazable.setWidget(interior)
        exterior.addWidget(desplazable)
        return w

    def _pestana_texturas(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        fila = QtWidgets.QHBoxLayout()
        self.campo_carpeta = QtWidgets.QLineEdit(self._ajuste("ultima_carpeta_texturas"))
        self.campo_carpeta.setPlaceholderText(t("tex_carpeta"))
        self.campo_carpeta.returnPressed.connect(self.analizar_carpeta)
        examinar = QtWidgets.QPushButton(t("examinar"))
        examinar.clicked.connect(self._elegir_carpeta)
        analizar = QtWidgets.QPushButton(t("tex_analizar"))
        analizar.clicked.connect(self.analizar_carpeta)
        fila.addWidget(self.campo_carpeta, 1)
        fila.addWidget(examinar)
        fila.addWidget(analizar)
        capa.addLayout(fila)
        self.arbol_texturas = QtWidgets.QTreeWidget()
        self.arbol_texturas.setHeaderLabels([t("tex_col_archivo"), t("tex_col_va_a"), t("tex_col_espacio")])
        self.arbol_texturas.setColumnWidth(0, 260)
        self.arbol_texturas.setColumnWidth(1, 200)
        capa.addWidget(self.arbol_texturas, 1)
        formulario = QtWidgets.QFormLayout()
        self.combo_material_tex = QtWidgets.QComboBox()
        formulario.addRow(t("tex_material"), self.combo_material_tex)
        self.combo_normal = QtWidgets.QComboBox()
        for clave in ("auto", "opengl", "directx"):
            self.combo_normal.addItem(t("normal_" + clave), clave)
        formulario.addRow(t("tex_normal"), self.combo_normal)
        self.casilla_desplazamiento = QtWidgets.QCheckBox(t("tex_desplazamiento"))
        self.casilla_desplazamiento.setToolTip(t("tex_desplazamiento_ayuda"))
        self.casilla_desplazamiento.setChecked(self._ajuste("desplazamiento"))
        self.casilla_desplazamiento.toggled.connect(lambda v: self._guardar_ajuste("desplazamiento", bool(v)))
        formulario.addRow("", self.casilla_desplazamiento)
        capa.addLayout(formulario)
        fila = QtWidgets.QHBoxLayout()
        self.boton_conectar = QtWidgets.QPushButton(t("tex_conectar"))
        self.boton_conectar.setStyleSheet("QPushButton{background:#5285a6;color:white;padding:4px 10px}")
        self.boton_conectar.clicked.connect(self.conectar_texturas)
        recargar = QtWidgets.QPushButton(t("tex_recargar"))
        recargar.setToolTip(t("tex_recargar_ayuda"))
        recargar.clicked.connect(self._recargar_texturas)
        reparar = QtWidgets.QPushButton(t("tex_reparar"))
        reparar.setToolTip(t("tex_reparar_ayuda"))
        reparar.clicked.connect(self.reparar_rutas)
        copiar = QtWidgets.QPushButton(t("tex_copiar"))
        copiar.setToolTip(t("tex_copiar_ayuda"))
        copiar.clicked.connect(self.copiar_al_proyecto)
        for b in (self.boton_conectar, recargar, reparar, copiar):
            fila.addWidget(b)
        fila.addStretch(1)
        capa.addLayout(fila)
        return w

    def _pestana_painter(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        ayuda = QtWidgets.QLabel(t("painter_ayuda"))
        ayuda.setWordWrap(True)
        capa.addWidget(ayuda)
        formulario = QtWidgets.QFormLayout()
        self.etiqueta_objetos = QtWidgets.QLabel()
        self.etiqueta_objetos.setWordWrap(True)
        formulario.addRow(t("painter_objetos"), self.etiqueta_objetos)
        self.combo_resolucion = QtWidgets.QComboBox()
        for r in ic.RESOLUCIONES:
            self.combo_resolucion.addItem("{} px".format(r), r)
        self.combo_resolucion.setCurrentIndex(max(0, list(ic.RESOLUCIONES).index(self._ajuste("resolucion"))
                                                  if self._ajuste("resolucion") in ic.RESOLUCIONES else 2))
        self.combo_resolucion.currentIndexChanged.connect(
            lambda _: self._guardar_ajuste("resolucion", self.combo_resolucion.currentData()))
        formulario.addRow(t("painter_resolucion"), self.combo_resolucion)
        self.etiqueta_plantilla = QtWidgets.QLabel()
        self.etiqueta_plantilla.setWordWrap(True)
        formulario.addRow(t("painter_plantilla"), self.etiqueta_plantilla)
        capa.addLayout(formulario)
        fila = QtWidgets.QHBoxLayout()
        self.boton_enviar = QtWidgets.QPushButton(t("painter_enviar"))
        self.boton_enviar.setStyleSheet("QPushButton{background:#5285a6;color:white;padding:4px 10px}")
        self.boton_enviar.clicked.connect(self.enviar_a_painter)
        abrir = QtWidgets.QPushButton(t("painter_abrir"))
        abrir.clicked.connect(self._abrir_painter)
        fila.addWidget(self.boton_enviar)
        fila.addWidget(abrir)
        fila.addStretch(1)
        capa.addLayout(fila)
        self.casilla_sincronizar = QtWidgets.QCheckBox(t("painter_sincronizar"))
        self.casilla_sincronizar.setChecked(self._ajuste("sincronizar"))
        self.casilla_sincronizar.toggled.connect(self._al_sincronizar)
        capa.addWidget(self.casilla_sincronizar)
        capa.addWidget(QtWidgets.QLabel(t("painter_envios")))
        self.lista_envios = QtWidgets.QListWidget()
        capa.addWidget(self.lista_envios, 1)
        fila = QtWidgets.QHBoxLayout()
        traer = QtWidgets.QPushButton(t("painter_traer"))
        traer.setToolTip(t("painter_traer_ayuda"))
        traer.clicked.connect(self._traer_envio)
        reenviar = QtWidgets.QPushButton(t("painter_reenviar"))
        reenviar.setToolTip(t("painter_reenviar_ayuda"))
        reenviar.clicked.connect(self.enviar_a_painter)
        fila.addWidget(traer)
        fila.addWidget(reenviar)
        fila.addStretch(1)
        capa.addLayout(fila)
        self.registro = QtWidgets.QPlainTextEdit()
        self.registro.setReadOnly(True)
        self.registro.setMaximumHeight(90)
        capa.addWidget(self.registro)
        return w

    def _pestana_escena(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QVBoxLayout(w)
        self.tabla_escena = QtWidgets.QTableWidget(0, 5)
        self.tabla_escena.setHorizontalHeaderLabels([t("esc_material"), t("esc_tipo"), t("esc_objetos"),
                                                     t("esc_texturas"), t("esc_estado")])
        self.tabla_escena.horizontalHeader().setStretchLastSection(True)
        self.tabla_escena.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tabla_escena.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tabla_escena.verticalHeader().setVisible(False)
        self.tabla_escena.cellDoubleClicked.connect(lambda fila, _c: self._editar_de_tabla())
        capa.addWidget(self.tabla_escena, 1)
        fila = QtWidgets.QHBoxLayout()
        for clave, accion in (("esc_actualizar", self.refrescar_escena), ("esc_editar", self._editar_de_tabla),
                              ("esc_seleccionar", self._seleccionar_de_tabla), ("esc_prefijo", self._poner_prefijos),
                              ("esc_convertir", self._convertir_de_tabla), ("esc_borrar", self._borrar_sin_usar)):
            b = QtWidgets.QPushButton(t(clave))
            b.setToolTip(t(clave + "_ayuda"))
            b.clicked.connect(accion)
            fila.addWidget(b)
        fila.addStretch(1)
        capa.addLayout(fila)
        self.etiqueta_resumen = QtWidgets.QLabel()
        capa.addWidget(self.etiqueta_resumen)
        return w

    def _pestana_ajustes(self):
        w = QtWidgets.QWidget()
        capa = QtWidgets.QFormLayout(w)
        fila = QtWidgets.QHBoxLayout()
        self.campo_clase = QtWidgets.QLineEdit(self._ajuste("carpeta_clase"))
        self.campo_clase.setPlaceholderText(t("aj_clase_vacia"))
        self.campo_clase.editingFinished.connect(self._al_cambiar_clase)
        elegir = QtWidgets.QPushButton(t("examinar"))
        elegir.clicked.connect(self._elegir_clase)
        fila.addWidget(self.campo_clase, 1)
        fila.addWidget(elegir)
        capa.addRow(t("aj_clase"), fila)
        ayuda = QtWidgets.QLabel(t("aj_clase_ayuda"))
        ayuda.setWordWrap(True)
        ayuda.setStyleSheet("color:#9a9a9a")
        capa.addRow("", ayuda)
        self.campo_painter = QtWidgets.QLineEdit(self._ajuste("ruta_painter"))
        self.campo_painter.setPlaceholderText(t("aj_painter_auto"))
        self.campo_painter.editingFinished.connect(
            lambda: self._guardar_ajuste("ruta_painter", self.campo_painter.text().strip()))
        capa.addRow(t("aj_painter"), self.campo_painter)
        carpeta_mias = self.biblioteca.carpeta_mias or ""
        capa.addRow(t("aj_mias"), QtWidgets.QLabel(carpeta_mias))
        capa.addRow(t("aj_buzon"), QtWidgets.QLabel(ic.carpeta_buzon()))
        return w

    # --- Destino ---------------------------------------------------------------------------------

    def _poner_destino(self, destino, guardar=True):
        self.destino = destino if destino in rc.DESTINOS else rc.RENDER
        juego = self.destino == rc.JUEGO
        self.boton_render.setChecked(not juego)
        self.boton_juego.setChecked(juego)
        self.combo_motor.setVisible(juego)
        indice = self.combo_motor.findData(self.motor)
        self.combo_motor.blockSignals(True)
        self.combo_motor.setCurrentIndex(max(0, indice))
        self.combo_motor.blockSignals(False)
        self.rotulos["transparencia"].setText(t("c_opacidad_juego") if juego else t("c_transparencia"))
        for clave in rc.SOLO_RENDER:
            self.deslizadores[clave].setEnabled(not juego)
            self.rotulos[clave].setEnabled(not juego)
            self.deslizadores[clave].setToolTip(t("solo_render") if juego else t("ayuda_" + clave))
        for clave in ("anisotropia", "pelicula", "grosor_pelicula", "profundidad_transmision", "radio_subsuperficie",
                      "rugosidad_barniz", "ior_barniz", "rugosidad_pelusa"):
            self.finos[clave].setEnabled(not juego)
        self.etiqueta_plantilla.setText(t("plantilla_" + (self.motor if juego else "arnold")))
        if guardar:
            self._guardar_ajuste("destino", self.destino)
            self._seguro(self.servicios.guardar_destino, self.destino, self._motor_actual())
            if self.material:
                self._aplicar_t.start()
        self._rellenar_recetas()
        self._actualizar_vista()

    def _motor_actual(self):
        return self.motor if self.destino == rc.JUEGO else "arnold"

    def _al_cambiar_motor(self, _indice):
        self.motor = self.combo_motor.currentData() or "unreal"
        self._guardar_ajuste("motor_juego", self.motor)
        self._poner_destino(self.destino)

    # --- Receta y vista previa ---------------------------------------------------------------------

    def _controles_valor(self, receta):
        """Valor que muestra cada deslizador (en juego, «Opacidad» es la opacidad)."""
        valores = {k: receta[k] for k in rc.DESLIZADORES}
        if self.destino == rc.JUEGO:
            valores["transparencia"] = round(1.0 - rc.para_juego(receta)["opacidad"], 4)
        return valores

    def cargar_receta(self, receta, vincular=None):
        """Pone la receta en los controles. ``vincular``: material de la escena o None."""
        self._cargando = True
        try:
            texturas = receta.get("texturas") if isinstance(receta, dict) else None
            self.receta = rc.normalizar(receta)
            if texturas:
                self.receta["texturas"] = texturas
            self.material = vincular
            self.campo_nombre.setText(vincular or self.receta["nombre"])
            self.boton_color.poner(self.receta["color"])
            for clave, valor in self._controles_valor(self.receta).items():
                self.deslizadores[clave].poner(valor)
            for clave, d in self.finos.items():
                d.poner(self.receta[clave])
            for clave, b in self.colores_finos.items():
                b.poner(self.receta[clave], auto_desde=self.receta["color"])
            self.casilla_pared.setChecked(self.receta["pared_fina"])
        finally:
            self._cargando = False
        self._actualizar_vinculo()
        self._actualizar_vista()

    def _cambiar(self, clave, valor):
        if self._cargando:
            return
        if self.destino == rc.JUEGO and clave == "transparencia":
            # En juego el deslizador es la opacidad.
            self.receta["transparencia"] = 0.0
            self.receta["opacidad"] = round(1.0 - valor, 4)
            self.finos["opacidad"].poner(self.receta["opacidad"])
        else:
            self.receta[clave] = valor
        if clave == "color":
            for k, b in self.colores_finos.items():
                if b.color() is None:
                    b.poner(None, auto_desde=valor)
        if self.material:
            self._aplicar_t.start()
        self._actualizar_vista()

    def _al_cambiar_nombre(self):
        texto = self.campo_nombre.text().strip()
        if not texto:
            return
        if self.material and texto != self.material:
            nuevo = self._seguro(self.servicios.renombrar, self.material, texto)
            if nuevo:
                self.material = nuevo
                self.campo_nombre.setText(nuevo)
                self.refrescar_escena()
        else:
            self.receta["nombre"] = texto
        self._actualizar_vinculo()

    def _aplicar_ahora(self):
        if self.material:
            omitidos = self._seguro(self.servicios.actualizar_material, self.material, self.receta, self.destino)
            if omitidos:
                self.mensaje(t("atributos_omitidos", lista=", ".join(omitidos[:6])))

    def _actualizar_vista(self):
        self._vista_t.start()
        avisos = chk.comprobar(self.receta, self.destino, self.receta.get("texturas"))
        filas = []
        for nivel, clave, valores in avisos:
            filas.append("<div style='margin:2px 0'><b style='color:{}'>{}</b>&nbsp;{}</div>".format(
                COLORES_AVISO[nivel], SIMBOLOS[nivel], t(clave, **valores)))
        self.etiqueta_chequeo.setText("".join(filas))
        self.etiqueta_nota.setText(self.receta.get("nota", ""))
        self.etiqueta_nota.setVisible(bool(self.receta.get("nota")))
        nits = rc.emision_a_nits(self.receta["emision"])
        self.etiqueta_nits.setText(t("nits", nits=int(round(nits))) if nits > 0 else "")

    def _pintar_vista(self):
        imagen = imagen_de(self.receta, TAM_VISTA, self.destino)
        self.vista.setPixmap(QtGui.QPixmap.fromImage(imagen))

    def _actualizar_vinculo(self):
        if self.material:
            n = len(self.receta.get("texturas") or {})
            texto = t("vinculo_material", material=self.material)
            if n:
                texto += " " + t("vinculo_texturas", n=n)
        else:
            texto = t("vinculo_ninguno")
        self.etiqueta_vinculo.setText(texto)
        self.boton_asignar.setText(t("asignar") if self.material else t("asignar_nuevo"))

    # --- Acciones principales -------------------------------------------------------------------

    def asignar(self):
        material = self.material if self.material and self.servicios.existe(self.material) else None
        if material is None:
            material = self._seguro(self.servicios.crear_material, self.receta, self.destino, self.receta["nombre"])
            if not material:
                return
            self.material = material
            self.campo_nombre.setText(material)
        n = self._seguro(self.servicios.asignar, material)
        self._actualizar_vinculo()
        self.refrescar_escena()
        if n:
            self.mensaje(t("asignado", material=material, n=n))
        else:
            self.mensaje(t("creado_sin_asignar", material=material))
        self.material_cambiado.emit(material)

    def nuevo_material(self):
        material = self._seguro(self.servicios.crear_material, self.receta, self.destino, self.receta["nombre"])
        if material:
            self.material = material
            self.campo_nombre.setText(material)
            n = self._seguro(self.servicios.asignar, material) or 0
            self._actualizar_vinculo()
            self.refrescar_escena()
            self.mensaje(t("asignado", material=material, n=n) if n else t("creado_sin_asignar", material=material))

    def cuentagotas(self):
        material = self._seguro(self.servicios.material_seleccionado)
        if not material:
            self.mensaje(t("cuentagotas_nada"), error=True)
            return
        self.editar_material(material)

    def editar_material(self, material):
        receta = self._seguro(self.servicios.leer_receta, material)
        if receta is None:
            return
        self.cargar_receta(receta, vincular=material)
        self.pestanas.setCurrentIndex(1)
        self.mensaje(t("editando", material=material))

    def guardar_receta(self):
        nombre, ok = QtWidgets.QInputDialog.getText(self, t("guardar_receta"), t("guardar_receta_nombre"),
                                                    text=self.receta["nombre"] if not self.material else
                                                    self.material.replace("M_", "").replace("_", " "))
        if not ok or not nombre.strip():
            return
        receta = dict(self.receta, nombre=nombre.strip(), destinos=[self.destino] if self.destino == rc.JUEGO
                      else self.receta.get("destinos", list(rc.DESTINOS)))
        ruta = self._seguro(self.biblioteca.guardar_mia, receta)
        if ruta:
            self._rellenar_familias(seleccionar=bib.MIS_RECETAS)
            self.mensaje(t("receta_guardada", ruta=ruta))

    def _modo_experto(self):
        if not self.material:
            self.mensaje(t("experto_sin_material"), error=True)
            return
        self._seguro(self.servicios.seleccionar_nodo, self.material)

    def _restaurar(self):
        receta = self.biblioteca.receta(self.receta.get("nombre", ""))
        if receta:
            self.cargar_receta(dict(receta), vincular=self.material)
            if self.material:
                self._aplicar_t.start()

    # --- Biblioteca -------------------------------------------------------------------------------

    def _rellenar_familias(self, seleccionar=None):
        actual = seleccionar or self._ajuste("familia")
        self.lista_familias.blockSignals(True)
        self.lista_familias.clear()
        todas = QtWidgets.QListWidgetItem(t("familia_todas", n=self.biblioteca.total()))
        todas.setData(Qt.UserRole, "")
        self.lista_familias.addItem(todas)
        fila_elegida = 0
        for f in self.biblioteca.familias:
            item = QtWidgets.QListWidgetItem("{} ({})".format(f.nombre, len(f.recetas)))
            item.setData(Qt.UserRole, f.clave)
            self.lista_familias.addItem(item)
            if f.clave == actual:
                fila_elegida = self.lista_familias.count() - 1
        self.lista_familias.setCurrentRow(fila_elegida)
        self.lista_familias.blockSignals(False)
        self._rellenar_recetas()

    def _al_solo_destino(self, valor):
        self._guardar_ajuste("solo_destino", bool(valor))
        self._rellenar_recetas()

    def _rellenar_recetas(self, *_):
        if not hasattr(self, "lista_recetas"):
            return
        item = self.lista_familias.currentItem()
        familia = item.data(Qt.UserRole) if item else ""
        if familia:
            self._guardar_ajuste("familia", familia)
        destino = self.destino if self.casilla_solo_destino.isChecked() else None
        recetas = self.biblioteca.buscar(self.campo_buscar.text(), familia or None, destino)
        self.lista_recetas.clear()
        self._cola_miniaturas = []
        marca = {(rc.RENDER,): " ·R", (rc.JUEGO,): " ·J"}
        for r in recetas:
            texto = r["nombre"] + marca.get(tuple(r["destinos"]), "")
            it = QtWidgets.QListWidgetItem(texto)
            it.setData(Qt.UserRole, r)
            it.setToolTip(self._ayuda_receta(r))
            clave = vp.clave_cache(r, TAM_MINI, self.destino)
            if clave in self._miniaturas:
                it.setIcon(self._miniaturas[clave])
            else:
                self._cola_miniaturas.append((it, r, clave))
            self.lista_recetas.addItem(it)
        if self._cola_miniaturas:
            self._mini_t.start()

    def _ayuda_receta(self, r):
        destinos = " + ".join(t("destino_corto_" + d) for d in r["destinos"])
        partes = ["<b>{}</b>".format(r["nombre"]), t("sirve_para", destinos=destinos)]
        if r.get("nota"):
            partes.append("<i>{}</i>".format(r["nota"]))
        return "<br>".join(partes)

    def _siguiente_miniatura(self):
        if not self._cola_miniaturas:
            self._mini_t.stop()
            return
        it, receta, clave = self._cola_miniaturas.pop(0)
        icono = self._miniatura(receta, clave)
        try:
            it.setIcon(icono)
        except RuntimeError:  # la lista ya se ha vaciado
            pass

    def _miniatura(self, receta, clave):
        if clave in self._miniaturas:
            return self._miniaturas[clave]
        ruta = os.path.join(self.carpeta_miniaturas, clave + ".png") if self.carpeta_miniaturas else None
        imagen = QtGui.QImage(ruta) if ruta and os.path.isfile(ruta) else QtGui.QImage()
        if imagen.isNull():
            imagen = imagen_de(receta, TAM_MINI, self.destino)
            if ruta:
                try:
                    os.makedirs(self.carpeta_miniaturas, exist_ok=True)
                    imagen.save(ruta)
                except OSError:
                    pass
        icono = QtGui.QIcon(QtGui.QPixmap.fromImage(imagen))
        self._miniaturas[clave] = icono
        return icono

    def _al_elegir_receta(self, item):
        receta = item.data(Qt.UserRole)
        if receta:
            self.cargar_receta(dict(receta), vincular=None)
            self.mensaje(t("receta_cargada", nombre=receta["nombre"]))

    def _al_doble_clic_receta(self, item):
        self._al_elegir_receta(item)
        self.asignar()

    def _menu_receta(self, punto):
        item = self.lista_recetas.itemAt(punto)
        if not item:
            return
        receta = item.data(Qt.UserRole)
        menu = QtWidgets.QMenu(self)
        menu.addAction(t("menu_asignar"), lambda: self._al_doble_clic_receta(item))
        if self.material:
            menu.addAction(t("menu_aplicar_activo", material=self.material), lambda: self._aplicar_a_activo(receta))
        if receta.get("origen") == bib.MIS_RECETAS:
            menu.addAction(t("menu_borrar_receta"), lambda: self._borrar_receta(receta))
        menu.exec(self.lista_recetas.mapToGlobal(punto))

    def _aplicar_a_activo(self, receta):
        material = self.material
        self.cargar_receta(dict(receta), vincular=material)
        self._aplicar_ahora()

    def _borrar_receta(self, receta):
        if self.biblioteca.borrar_mia(receta):
            self._rellenar_familias(seleccionar=bib.MIS_RECETAS)

    # --- Texturas ----------------------------------------------------------------------------------

    def _elegir_carpeta(self):
        inicio = self.campo_carpeta.text() or os.path.join(self.servicios.proyecto() or "", "sourceimages")
        carpeta = QtWidgets.QFileDialog.getExistingDirectory(self, t("tex_carpeta"), inicio)
        if carpeta:
            self.campo_carpeta.setText(carpeta)
            self.analizar_carpeta()

    def analizar_carpeta(self):
        carpeta = self.campo_carpeta.text().strip()
        if not os.path.isdir(carpeta):
            self.mensaje(t("tex_no_carpeta"), error=True)
            return
        self._guardar_ajuste("ultima_carpeta_texturas", carpeta)
        normal = self.combo_normal.currentData()
        por_defecto = ic.NORMAL_DE_MOTOR.get(self._motor_actual(), "opengl") if normal == "auto" else normal
        self.analisis = tx.analizar(tx.listar_imagenes(carpeta), normal_por_defecto=por_defecto)
        if normal != "auto":
            for juego in self.analisis.values():
                if "normal" in juego.mapas:
                    juego.mapas["normal"].convencion = normal
        self.arbol_texturas.clear()
        for juego in self.analisis.values():
            raiz = QtWidgets.QTreeWidgetItem([juego.nombre or t("tex_sin_nombre"),
                                              t("tex_n_mapas", n=len(juego.conexiones)), ""])
            raiz.setFirstColumnSpanned(False)
            for entrada, c in sorted(juego.conexiones.items()):
                destino = t("entrada_" + entrada)
                if c.canal:
                    destino += " · " + t("canal", canal=c.canal)
                if c.invertir:
                    destino += " · " + t("invertido")
                if entrada == "normal":
                    destino += " · " + (c.mapa.convencion or "opengl").upper()
                if entrada == "altura" and not self.casilla_desplazamiento.isChecked():
                    destino += " · " + t("tex_altura_bump")
                QtWidgets.QTreeWidgetItem(raiz, [c.mapa.nombre + (" (UDIM)" if c.mapa.udim else ""), destino,
                                                 c.espacio])
            for nombre, motivo in juego.ignorados:
                QtWidgets.QTreeWidgetItem(raiz, [nombre, t("ignorado_" + motivo), "—"])
            self.arbol_texturas.addTopLevelItem(raiz)
            raiz.setExpanded(True)
        self._rellenar_combo_materiales()
        if not self.analisis:
            self.mensaje(t("tex_nada"), error=True)
        else:
            self.mensaje(t("tex_encontrados", n=len(self.analisis)))

    def _rellenar_combo_materiales(self):
        self.combo_material_tex.clear()
        self.combo_material_tex.addItem(t("tex_por_nombre"), "")
        if self.material:
            self.combo_material_tex.addItem(t("tex_activo", material=self.material), self.material)
        for m in self._seguro(self.servicios.materiales) or []:
            if m["tipo"] == "openPBRSurface" and m["nombre"] != self.material:
                self.combo_material_tex.addItem(m["nombre"], m["nombre"])
        if self.material:
            self.combo_material_tex.setCurrentIndex(1)

    def conectar_texturas(self):
        if not self.analisis:
            self.analizar_carpeta()
            if not self.analisis:
                return
        elegido = self.combo_material_tex.currentData()
        opciones = {"desplazamiento": self.casilla_desplazamiento.isChecked(),
                    "normal": ic.NORMAL_DE_MOTOR.get(self._motor_actual(), "opengl")}
        materiales = [m["nombre"] for m in self._seguro(self.servicios.materiales) or []
                      if m["tipo"] == "openPBRSurface"]
        hechos = []
        for juego in self.analisis.values():
            conexiones = [c.como_dict() for c in juego.conexiones.values()]
            if not conexiones:
                continue
            if elegido:
                material = elegido
            else:
                material = tx.buscar_material(juego.nombre, materiales) or tx.buscar_material(juego.clave, materiales)
                if not material:
                    base = rc.normalizar(self.receta) if len(self.analisis) == 1 else rc.nueva()
                    base["nombre"] = juego.nombre or "Textura"
                    material = self._seguro(self.servicios.crear_material, base, self.destino, base["nombre"])
                    if not material:
                        continue
                    materiales.append(material)
            if self._seguro(self.servicios.conectar_texturas, material, conexiones, opciones) is not None:
                hechos.append(material)
            if elegido:
                break
        if hechos:
            if self.material in hechos or (len(hechos) == 1 and not self.material):
                self.editar_material(hechos[0])
            self.refrescar_escena()
            self.mensaje(t("tex_conectadas", materiales=", ".join(hechos)))

    def _recargar_texturas(self):
        n = self._seguro(self.servicios.recargar_texturas) or 0
        self.mensaje(t("tex_recargadas", n=n))

    def reparar_rutas(self):
        resultado = self._seguro(self.servicios.reparar_rutas, [self.campo_carpeta.text().strip()])
        if resultado is None:
            return
        arregladas, perdidas = resultado
        texto = t("rutas_arregladas", n=len(arregladas))
        if perdidas:
            texto += " " + t("rutas_perdidas", n=len(perdidas), lista=", ".join(perdidas[:5]))
        self.mensaje(texto, error=bool(perdidas))
        self.refrescar_escena()

    def copiar_al_proyecto(self):
        n = self._seguro(self.servicios.copiar_al_proyecto)
        if n is not None:
            self.mensaje(t("copiadas", n=n))

    # --- Painter -------------------------------------------------------------------------------------

    def _al_cambiar_pestana(self, indice):
        if self.pestanas.widget(indice) is self.pestanas.widget(3):
            objetos = self._seguro(self.servicios.objetos_seleccionados) or []
            self.etiqueta_objetos.setText(", ".join(o.split("|")[-1] for o in objetos) or t("painter_ninguno"))
            self.refrescar_envios()
        elif indice == 4:
            self.refrescar_escena()
        elif indice == 2:
            self._rellenar_combo_materiales()

    def log(self, texto):
        self.registro.appendPlainText(texto)

    def enviar_a_painter(self):
        objetos = self._seguro(self.servicios.objetos_seleccionados) or []
        self.etiqueta_objetos.setText(", ".join(o.split("|")[-1] for o in objetos) or t("painter_ninguno"))
        if not objetos:
            self.mensaje(t("painter_sin_seleccion"), error=True)
            return
        carpeta = self._seguro(self.servicios.enviar_a_painter, objetos, self.destino, self._motor_actual(),
                               self.combo_resolucion.currentData())
        if not carpeta:
            return
        self._huellas[carpeta] = ic.huella_manifiesto(carpeta)
        self.log(t("painter_enviado", carpeta=carpeta))
        self.mensaje(t("painter_enviado_corto"))
        if self._ajuste("abrir_painter"):
            self._abrir_painter(silencioso=True)
        self.refrescar_envios()

    def _abrir_painter(self, silencioso=False):
        ok = self._seguro(self.servicios.abrir_painter, self._ajuste("ruta_painter"))
        if not ok and not silencioso:
            self.mensaje(t("painter_no_abre"), error=True)

    def refrescar_envios(self):
        envios = self._seguro(self.servicios.envios) or []
        self.lista_envios.clear()
        for carpeta in envios:
            manifiesto = ic.leer_manifiesto(carpeta)
            receta_envio = ic.leer_json(os.path.join(carpeta, ic.RECETA)) or {}
            estado = t("envio_exportado", hora=manifiesto["exportado"][11:16], n=manifiesto.get("contador", 1)) \
                if manifiesto else t("envio_esperando")
            item = QtWidgets.QListWidgetItem("{} · {} · {}".format(
                receta_envio.get("objeto", os.path.basename(carpeta)),
                t("motor_" + receta_envio.get("motor", "arnold")) if receta_envio.get("motor") != "arnold"
                else t("destino_render"), estado))
            item.setData(Qt.UserRole, carpeta)
            self.lista_envios.addItem(item)
            if carpeta not in self._huellas:
                self._huellas[carpeta] = ic.huella_manifiesto(carpeta)

    def _traer_envio(self):
        item = self.lista_envios.currentItem()
        carpetas = [item.data(Qt.UserRole)] if item else list(self._huellas)
        for carpeta in carpetas:
            self._aplicar_manifiesto(carpeta)

    def _aplicar_manifiesto(self, carpeta):
        resultado = self._seguro(self.servicios.aplicar_manifiesto, carpeta,
                                 {"desplazamiento": self.casilla_desplazamiento.isChecked()})
        self._huellas[carpeta] = ic.huella_manifiesto(carpeta)
        if not resultado:
            return
        for material, entradas in resultado:
            self.log(t("painter_recibido", material=material, n=len(entradas)))
        self.mensaje(t("painter_recibido_corto", n=len(resultado)))
        if self.material in [m for m, _ in resultado]:
            self.editar_material(self.material)
        self.refrescar_envios()
        self.refrescar_escena()

    def _al_sincronizar(self, valor):
        self._guardar_ajuste("sincronizar", bool(valor))
        if valor:
            self._vigia_t.start()
        else:
            self._vigia_t.stop()

    def vigilar_painter(self):
        """Mira si Painter ha exportado algo nuevo en alguna carpeta de envío conocida."""
        for carpeta in list(self._huellas):
            huella = ic.huella_manifiesto(carpeta)
            if huella and huella != self._huellas.get(carpeta):
                self._aplicar_manifiesto(carpeta)

    # --- Escena -------------------------------------------------------------------------------------

    def refrescar_escena(self):
        materiales = self._seguro(self.servicios.materiales) or []
        self._materiales_escena = materiales
        self.tabla_escena.setRowCount(len(materiales))
        sin_usar = 0
        for fila, m in enumerate(materiales):
            estados = []
            if m["objetos"] == 0:
                estados.append(t("estado_sin_usar"))
                sin_usar += 1
            if m["rotas"]:
                estados.append(t("estado_rotas", n=m["rotas"]))
            if m["tipo"] != "openPBRSurface":
                estados.append(t("estado_convertible"))
            elif not m["con_prefijo"]:
                estados.append(t("estado_sin_prefijo"))
            if m.get("destino"):
                estados.append(t("destino_corto_" + m["destino"]))
            valores = [m["nombre"], m["tipo"], str(m["objetos"]), str(m["texturas"]), " · ".join(estados) or "✓"]
            for columna, valor in enumerate(valores):
                celda = QtWidgets.QTableWidgetItem(valor)
                if columna == 4 and (m["rotas"] or m["objetos"] == 0):
                    celda.setForeground(QtGui.QBrush(QtGui.QColor("#f0c060")))
                self.tabla_escena.setItem(fila, columna, celda)
        self.tabla_escena.resizeColumnsToContents()
        self.etiqueta_resumen.setText(t("esc_resumen", n=len(materiales), sin_usar=sin_usar))

    def _material_de_tabla(self):
        fila = self.tabla_escena.currentRow()
        if fila < 0 or fila >= len(getattr(self, "_materiales_escena", [])):
            self.mensaje(t("esc_elige"), error=True)
            return None
        return self._materiales_escena[fila]

    def _editar_de_tabla(self):
        m = self._material_de_tabla()
        if not m:
            return
        if m["tipo"] != "openPBRSurface":
            self.mensaje(t("esc_convierte_primero"), error=True)
            return
        self.editar_material(m["nombre"])

    def _seleccionar_de_tabla(self):
        m = self._material_de_tabla()
        if m:
            n = self._seguro(self.servicios.seleccionar_objetos, m["nombre"]) or 0
            self.mensaje(t("seleccionados", n=n))

    def _poner_prefijos(self):
        n = 0
        for m in list(getattr(self, "_materiales_escena", [])):
            if m["tipo"] == "openPBRSurface" and not m["con_prefijo"]:
                nuevo = self._seguro(self.servicios.renombrar, m["nombre"], m["nombre"])
                if nuevo:
                    n += 1
                    if self.material == m["nombre"]:
                        self.material = nuevo
        self.refrescar_escena()
        self._actualizar_vinculo()
        self.mensaje(t("prefijos_puestos", n=n))

    def _convertir_de_tabla(self):
        m = self._material_de_tabla()
        if not m:
            return
        if m["tipo"] == "openPBRSurface":
            self.mensaje(t("esc_ya_openpbr"))
            return
        nuevo = self._seguro(self.servicios.convertir, m["nombre"], self.destino)
        if nuevo:
            self.refrescar_escena()
            self.editar_material(nuevo)
            self.mensaje(t("convertido", viejo=m["nombre"], nuevo=nuevo))

    def _borrar_sin_usar(self):
        sin_usar = [m["nombre"] for m in getattr(self, "_materiales_escena", []) if m["objetos"] == 0]
        if not sin_usar:
            self.mensaje(t("nada_sin_usar"))
            return
        respuesta = QtWidgets.QMessageBox.question(self, t("esc_borrar"),
                                                   t("confirmar_borrar", n=len(sin_usar),
                                                     lista=", ".join(sin_usar[:8])))
        if respuesta != QtWidgets.QMessageBox.Yes:
            return
        n = self._seguro(self.servicios.borrar_sin_usar) or 0
        if self.material in sin_usar:
            self.material = None
            self._actualizar_vinculo()
        self.refrescar_escena()
        self.mensaje(t("borrados", n=n))

    # --- Ajustes ---------------------------------------------------------------------------------------

    def _elegir_clase(self):
        carpeta = QtWidgets.QFileDialog.getExistingDirectory(self, t("aj_clase"), self.campo_clase.text())
        if carpeta:
            self.campo_clase.setText(carpeta)
            self._al_cambiar_clase()

    def _al_cambiar_clase(self):
        carpeta = self.campo_clase.text().strip()
        self._guardar_ajuste("carpeta_clase", carpeta)
        self.biblioteca.carpeta_clase = carpeta or None
        self.biblioteca.recargar()
        self._rellenar_familias(seleccionar=bib.CLASE if carpeta else None)

    # --- Escena nueva -----------------------------------------------------------------------------------

    def al_cambiar_escena(self):
        self.material = None
        self._huellas = {}
        self.destino = self.servicios.destino_escena(self._ajuste("destino"))
        self.motor = self.servicios.motor_escena(self._ajuste("motor_juego"))
        self._poner_destino(self.destino, guardar=False)
        self._actualizar_vinculo()
        self.refrescar_escena()
        self.refrescar_envios()

    def cerrar(self):
        if self._aplicar_t.isActive():
            self._aplicar_ahora()
        for temporizador in (self._aplicar_t, self._vista_t, self._mini_t, self._vigia_t):
            temporizador.stop()
