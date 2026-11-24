"""Aspecto de la ventana: hoja de estilo y dibujo de las tarjetas de la biblioteca.

Todo va acotado a ``#MaterialsVentana`` para no cambiar el resto de Maya. Los colores
siguen el tema oscuro de Maya con un azul de acento; los papeles especiales se marcan con
la propiedad dinámica ``rol`` (``primario``, ``segmento``, ``tenue``, ``titulo``,
``seccion``, ``tarjeta``, ``chip``).
"""

from materials import receta as rc
from materials.qt import QtCore, QtGui, QtWidgets

Qt = QtCore.Qt

ACENTO = "#4a9bd1"
ACENTO_OSCURO = "#3579a8"
FONDO_TARJETA = "#3a3a3a"
FONDO_CAMPO = "#2b2b2b"
BORDE = "#262626"
TEXTO = "#e2e2e2"
TENUE = "#9c9c9c"
COLOR_RENDER = "#d49a4a"
COLOR_JUEGO = "#6fbf73"

# Un color por familia (punto en la lista y franja de la tarjeta).
COLORES_FAMILIA = {
    "metales": "#b8c2cc", "plasticos": "#e0685a", "maderas": "#b07a48", "piedra": "#a59e94",
    "construccion": "#c98d5b", "terreno": "#7f9a52", "transparentes": "#7cc6e8", "telas": "#b583c9",
    "organicos": "#e3a58c", "comida": "#e8c04f", "pinturas": "#d8504f", "luces": "#f4e27a",
    "arcilla": "#c8b6a2", "mis_recetas": ACENTO, "clase": "#9fd18a", "": "#8a8a8a",
}

HOJA = """
#MaterialsVentana { background: #444444; }
#MaterialsVentana QLabel { color: %(texto)s; }
#MaterialsVentana QLabel[rol="tenue"] { color: %(tenue)s; }
#MaterialsVentana QLabel[rol="titulo"] { font-size: 13pt; font-weight: 600; color: #f2f2f2; }
#MaterialsVentana QLabel[rol="seccion"] { color: #8fc0e3; font-weight: 600; padding-top: 6px; }
#MaterialsVentana QLabel[rol="chip"] { border-radius: 8px; padding: 1px 8px; font-size: 8.5pt; font-weight: 600; }
#MaterialsVentana QLabel[rol="paso"] { background: %(acento)s; color: white; border-radius: 10px;
    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px; font-weight: 700; qproperty-alignment: AlignCenter; }

#MaterialsVentana QFrame[rol="tarjeta"] { background: %(tarjeta)s; border: 1px solid #333333; border-radius: 8px; }
#MaterialsVentana QFrame[rol="cabecera"] { background: #3b3b3b; border-bottom: 1px solid #303030; }

#MaterialsVentana QTabWidget::pane { border: none; border-top: 1px solid #353535; top: -1px; }
#MaterialsVentana QTabBar::tab { background: transparent; color: #a8a8a8; padding: 7px 14px; border: none;
    border-bottom: 2px solid transparent; margin-right: 2px; }
#MaterialsVentana QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid %(acento)s; }
#MaterialsVentana QTabBar::tab:hover:!selected { color: #dddddd; border-bottom: 2px solid #5a5a5a; }

#MaterialsVentana QPushButton { background: #575757; color: #eeeeee; border: 1px solid #303030;
    border-radius: 5px; padding: 5px 12px; }
#MaterialsVentana QPushButton:hover { background: #636363; }
#MaterialsVentana QPushButton:pressed { background: #4b4b4b; }
#MaterialsVentana QPushButton:disabled { background: #4a4a4a; color: #858585; }
#MaterialsVentana QPushButton[rol="primario"] { background: %(acento)s; border: 1px solid %(acento_oscuro)s;
    color: white; font-weight: 600; padding: 7px 12px; }
#MaterialsVentana QPushButton[rol="primario"]:hover { background: #5aa9de; }
#MaterialsVentana QPushButton[rol="primario"]:pressed { background: %(acento_oscuro)s; }

#MaterialsVentana QToolButton[rol="segmento"] { background: #383838; color: #bbbbbb; border: 1px solid #2c2c2c;
    padding: 5px 14px; font-weight: 600; }
#MaterialsVentana QToolButton[rol="segmento"][lado="izq"] { border-top-left-radius: 6px; border-bottom-left-radius: 6px; }
#MaterialsVentana QToolButton[rol="segmento"][lado="der"] { border-top-right-radius: 6px; border-bottom-right-radius: 6px;
    border-left: none; }
#MaterialsVentana QToolButton[rol="segmento"]:hover:!checked { background: #424242; color: #e0e0e0; }
#MaterialsVentana QToolButton[rol="segmento"]:checked { background: %(acento)s; color: white; border-color: %(acento_oscuro)s; }
#MaterialsVentana QToolButton { border-radius: 4px; padding: 3px 8px; }

#MaterialsVentana QLineEdit, #MaterialsVentana QComboBox, #MaterialsVentana QDoubleSpinBox,
#MaterialsVentana QPlainTextEdit { background: %(campo)s; color: %(texto)s; border: 1px solid %(borde)s;
    border-radius: 5px; padding: 4px 6px; selection-background-color: %(acento)s; }
#MaterialsVentana QLineEdit:focus, #MaterialsVentana QDoubleSpinBox:focus, #MaterialsVentana QComboBox:focus
    { border: 1px solid %(acento)s; }
#MaterialsVentana QComboBox::drop-down { border: none; width: 18px; }
#MaterialsVentana QDoubleSpinBox::up-button, #MaterialsVentana QDoubleSpinBox::down-button { width: 0px; border: none; }

#MaterialsVentana QListWidget, #MaterialsVentana QTreeWidget, #MaterialsVentana QTableWidget {
    background: #363636; color: %(texto)s; border: 1px solid #2e2e2e; border-radius: 8px; outline: none; }
#MaterialsVentana QListWidget#ListaFamilias { background: transparent; border: none; }
#MaterialsVentana QListWidget#ListaRecetas { background: #333333; padding: 4px; }
#MaterialsVentana QHeaderView::section { background: #3d3d3d; color: #bdbdbd; border: none;
    border-bottom: 1px solid #2c2c2c; padding: 5px 6px; font-weight: 600; }
#MaterialsVentana QTableWidget { gridline-color: #3e3e3e; }
#MaterialsVentana QTableWidget::item:selected, #MaterialsVentana QTreeWidget::item:selected,
#MaterialsVentana QListWidget#ListaEnvios::item:selected { background: %(acento_oscuro)s; color: white; }

#MaterialsVentana QSlider::groove:horizontal { height: 4px; background: #2a2a2a; border-radius: 2px; }
#MaterialsVentana QSlider::sub-page:horizontal { background: %(acento)s; border-radius: 2px; }
#MaterialsVentana QSlider::handle:horizontal { background: #ececec; width: 14px; height: 14px; margin: -5px 0;
    border-radius: 7px; border: 1px solid #2a2a2a; }
#MaterialsVentana QSlider::handle:horizontal:hover { background: #ffffff; }

#MaterialsVentana QCheckBox { color: %(texto)s; spacing: 7px; }
#MaterialsVentana QCheckBox::indicator, #MaterialsVentana QGroupBox::indicator { width: 14px; height: 14px;
    border-radius: 3px; border: 1px solid #222; background: %(campo)s; }
#MaterialsVentana QCheckBox::indicator:checked, #MaterialsVentana QGroupBox::indicator:checked
    { background: %(acento)s; border-color: %(acento_oscuro)s; }

#MaterialsVentana QGroupBox { border: 1px solid #353535; border-radius: 8px; margin-top: 12px; padding-top: 8px;
    background: #3e3e3e; }
#MaterialsVentana QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #cfcfcf; }

#MaterialsVentana QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
#MaterialsVentana QScrollBar::handle:vertical { background: #5a5a5a; border-radius: 4px; min-height: 30px; }
#MaterialsVentana QScrollBar::handle:vertical:hover { background: #6a6a6a; }
#MaterialsVentana QScrollBar::add-line, #MaterialsVentana QScrollBar::sub-line { height: 0; width: 0; }
#MaterialsVentana QScrollBar::add-page, #MaterialsVentana QScrollBar::sub-page { background: transparent; }
#MaterialsVentana QSplitter::handle { background: transparent; }
""" % {"acento": ACENTO, "acento_oscuro": ACENTO_OSCURO, "tarjeta": FONDO_TARJETA, "campo": FONDO_CAMPO,
       "borde": BORDE, "texto": TEXTO, "tenue": TENUE}


def rol(widget, nombre, **extra):
    """Marca un widget con un papel de la hoja de estilo (y propiedades extra)."""
    widget.setProperty("rol", nombre)
    for clave, valor in extra.items():
        widget.setProperty(clave, valor)
    return widget


def etiqueta(texto, papel=None, ajuste=False):
    e = QtWidgets.QLabel(texto)
    if papel:
        rol(e, papel)
    e.setWordWrap(ajuste)
    return e


def formulario(padre=None):
    """QFormLayout igual en Windows y Mac.

    En macOS Qt deja los campos a su tamaño mínimo (FieldsStayAtSizeHint): las etiquetas
    con ajuste de línea se quedan estrechas y el texto se monta sobre la fila siguiente.
    """
    f = QtWidgets.QFormLayout(padre) if padre is not None else QtWidgets.QFormLayout()
    f.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
    f.setRowWrapPolicy(QtWidgets.QFormLayout.DontWrapRows)
    f.setLabelAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
    f.setFormAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
    return f


def tarjeta(margenes=10, espacio=6):
    """Marco redondeado con su capa vertical."""
    marco = QtWidgets.QFrame()
    rol(marco, "tarjeta")
    capa = QtWidgets.QVBoxLayout(marco)
    capa.setContentsMargins(margenes, margenes, margenes, margenes)
    capa.setSpacing(espacio)
    return marco, capa


def chip(texto, color, fondo_alfa=60):
    """Etiqueta en forma de píldora con el color dado."""
    c = QtGui.QColor(color)
    e = etiqueta(texto, "chip")
    e.setStyleSheet("background: rgba({},{},{},{}); color: {};".format(c.red(), c.green(), c.blue(), fondo_alfa,
                                                                      c.lighter(130).name()))
    return e


def color_destinos(destinos):
    destinos = tuple(destinos or ())
    if destinos == (rc.RENDER,):
        return "R", COLOR_RENDER
    if destinos == (rc.JUEGO,):
        return "J", COLOR_JUEGO
    return None, None


# --- Tarjetas de la biblioteca --------------------------------------------------------------

ROL_FAMILIA = Qt.UserRole + 1
ROL_CUENTA = Qt.UserRole + 2


class TarjetaReceta(QtWidgets.QStyledItemDelegate):
    """Dibuja cada receta como una tarjeta: miniatura redondeada, nombre en dos líneas y
    una marca R/J si solo sirve para render o para juego."""

    def __init__(self, lado_imagen=88, padre=None):
        super(TarjetaReceta, self).__init__(padre)
        self.lado = lado_imagen

    def tamano(self):
        linea = QtGui.QFontMetrics(QtWidgets.QApplication.font()).lineSpacing()
        return QtCore.QSize(self.lado + 30, self.lado + 2 * linea + 30)

    def sizeHint(self, opcion, indice):
        return self.tamano()

    def paint(self, pintor, opcion, indice):
        pintor.save()
        pintor.setRenderHint(QtGui.QPainter.Antialiasing, True)
        pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        caja = QtCore.QRectF(opcion.rect).adjusted(4, 4, -4, -4)
        seleccionada = bool(opcion.state & QtWidgets.QStyle.State_Selected)
        encima = bool(opcion.state & QtWidgets.QStyle.State_MouseOver)
        fondo = QtGui.QColor("#474747" if encima or seleccionada else "#3c3c3c")
        camino = QtGui.QPainterPath()
        camino.addRoundedRect(caja, 8, 8)
        pintor.fillPath(camino, fondo)
        if seleccionada:
            pintor.setPen(QtGui.QPen(QtGui.QColor(ACENTO), 2))
            pintor.drawPath(camino)
        # Miniatura
        icono = indice.data(Qt.DecorationRole)
        imagen = QtCore.QRectF(caja.center().x() - self.lado / 2.0, caja.top() + 8, self.lado, self.lado)
        recorte = QtGui.QPainterPath()
        recorte.addRoundedRect(imagen, 6, 6)
        pintor.save()
        pintor.setClipPath(recorte)
        if isinstance(icono, QtGui.QIcon) and not icono.isNull():
            mapa = icono.pixmap(QtCore.QSize(self.lado * 2, self.lado * 2))
            pintor.drawPixmap(imagen.toRect(), mapa)
        else:
            pintor.fillRect(imagen, QtGui.QColor("#4a4a4a"))
        pintor.restore()
        # Franja de color de la familia
        familia = indice.data(ROL_FAMILIA) or ""
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QtGui.QColor(COLORES_FAMILIA.get(familia, COLORES_FAMILIA[""])))
        pintor.drawRoundedRect(QtCore.QRectF(imagen.left() + 6, imagen.bottom() + 3, imagen.width() - 12, 2), 1, 1)
        # Marca R / J
        receta = indice.data(Qt.UserRole) or {}
        letra, color = color_destinos(receta.get("destinos"))
        if letra:
            marca = QtCore.QRectF(imagen.right() - 20, imagen.top() + 4, 16, 16)
            pintor.setBrush(QtGui.QColor(color))
            pintor.drawEllipse(marca)
            pintor.setPen(QtGui.QColor("#1e1e1e"))
            fuente = QtGui.QFont(opcion.font)
            fuente.setBold(True)
            fuente.setPointSizeF(max(6.5, fuente.pointSizeF() * 0.72))
            pintor.setFont(fuente)
            pintor.drawText(marca, Qt.AlignCenter, letra)
        # Nombre (dos líneas como mucho)
        pintor.setFont(opcion.font)
        pintor.setPen(QtGui.QColor("#ffffff" if seleccionada else TEXTO))
        texto = indice.data(Qt.DisplayRole) or ""
        zona = QtCore.QRectF(caja.left() + 4, imagen.bottom() + 8, caja.width() - 8, caja.bottom() - imagen.bottom() - 9)
        metricas = QtGui.QFontMetrics(opcion.font)
        lineas = _partir(texto, metricas, int(zona.width()), 2)
        pintor.drawText(zona, Qt.AlignHCenter | Qt.AlignTop, "\n".join(lineas))
        pintor.restore()


def _partir(texto, metricas, ancho, maximo):
    palabras = texto.split()
    lineas, actual = [], ""
    for palabra in palabras:
        prueba = (actual + " " + palabra).strip()
        if metricas.horizontalAdvance(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    if len(lineas) > maximo:
        lineas = lineas[:maximo]
        lineas[-1] = metricas.elidedText(" ".join(texto.split()[len(" ".join(lineas[:-1]).split()):]),
                                         Qt.ElideRight, ancho)
    return [metricas.elidedText(l, Qt.ElideRight, ancho) for l in lineas]


class FilaFamilia(QtWidgets.QStyledItemDelegate):
    """Fila de familia: punto de color, nombre y número de recetas a la derecha."""

    def sizeHint(self, opcion, indice):
        return QtCore.QSize(150, 28)

    def paint(self, pintor, opcion, indice):
        pintor.save()
        pintor.setRenderHint(QtGui.QPainter.Antialiasing, True)
        caja = QtCore.QRectF(opcion.rect).adjusted(2, 1, -2, -1)
        seleccionada = bool(opcion.state & QtWidgets.QStyle.State_Selected)
        encima = bool(opcion.state & QtWidgets.QStyle.State_MouseOver)
        if seleccionada or encima:
            camino = QtGui.QPainterPath()
            camino.addRoundedRect(caja, 6, 6)
            pintor.fillPath(camino, QtGui.QColor(ACENTO_OSCURO if seleccionada else "#4a4a4a"))
        clave = indice.data(Qt.UserRole) or ""
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QtGui.QColor(COLORES_FAMILIA.get(clave, COLORES_FAMILIA[""])))
        pintor.drawEllipse(QtCore.QRectF(caja.left() + 9, caja.center().y() - 4, 8, 8))
        cuenta = indice.data(ROL_CUENTA)
        texto_cuenta = str(cuenta) if cuenta is not None else ""
        metricas = QtGui.QFontMetrics(opcion.font)
        ancho_cuenta = metricas.horizontalAdvance(texto_cuenta) + 10
        pintor.setFont(opcion.font)
        pintor.setPen(QtGui.QColor("#ffffff" if seleccionada else TEXTO))
        zona = QtCore.QRectF(caja.left() + 24, caja.top(), caja.width() - 30 - ancho_cuenta, caja.height())
        pintor.drawText(zona, Qt.AlignVCenter | Qt.AlignLeft,
                        metricas.elidedText(indice.data(Qt.DisplayRole) or "", Qt.ElideRight, int(zona.width())))
        pintor.setPen(QtGui.QColor("#d8e8f4" if seleccionada else TENUE))
        pintor.drawText(QtCore.QRectF(caja.right() - ancho_cuenta - 6, caja.top(), ancho_cuenta, caja.height()),
                        Qt.AlignVCenter | Qt.AlignRight, texto_cuenta)
        pintor.restore()


def imagen_redondeada(imagen, lado, radio=10, fondo=None, rotulo=None):
    """QPixmap cuadrado con las esquinas redondeadas (para la vista grande) y un rótulo opcional abajo."""
    mapa = QtGui.QPixmap(lado, lado)
    mapa.fill(Qt.transparent)
    pintor = QtGui.QPainter(mapa)
    pintor.setRenderHint(QtGui.QPainter.Antialiasing, True)
    pintor.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
    camino = QtGui.QPainterPath()
    camino.addRoundedRect(QtCore.QRectF(0, 0, lado, lado), radio, radio)
    pintor.setClipPath(camino)
    if fondo:
        pintor.fillRect(0, 0, lado, lado, QtGui.QColor(fondo))
    pintor.drawImage(QtCore.QRect(0, 0, lado, lado), imagen)
    if rotulo:
        fuente = QtWidgets.QApplication.font()
        fuente.setPointSizeF(fuente.pointSizeF() * 0.8)
        pintor.setFont(fuente)
        metricas = QtGui.QFontMetrics(fuente)
        ancho = metricas.horizontalAdvance(rotulo) + 14
        alto = metricas.height() + 4
        caja = QtCore.QRectF(8, lado - alto - 8, ancho, alto)
        pintor.setPen(Qt.NoPen)
        pintor.setBrush(QtGui.QColor(0, 0, 0, 150))
        pintor.drawRoundedRect(caja, alto / 2.0, alto / 2.0)
        pintor.setPen(QtGui.QColor("#e8e8e8"))
        pintor.drawText(caja, Qt.AlignCenter, rotulo)
    pintor.end()
    return mapa
