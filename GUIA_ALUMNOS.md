# Muestrario: guía rápida

Muestrario sirve para poner materiales a tus modelos sin perderte en el Hypershade.

## 1. Abrirlo y elegir destino

Menú **Muestrario › Abrir Muestrario**. Arriba elige:

- **Render (Arnold)** si vas a renderizar en Maya.
- **Videojuego** si el modelo va a Unreal, Unity o un motor web. Elige también el motor.

## 2. Elegir una receta

En **Biblioteca** busca por familia o escribe (oro, vidrio, piel, hormigón…).

- **Clic**: la ves en la esfera.
- **Doble clic**: se crea el material y se pone a lo que tengas seleccionado (objetos o caras).

## 3. Ajustarla

En **Material** mueve los ocho controles. Los cambios se ven al momento en el visor.

| Control | Piensa en… |
|---|---|
| Rugosidad | 0 espejo, 1 mate. Es el que más cambia un material. |
| Metal | 0 o 1. Nada de 0,5 salvo con textura. |
| Transparencia | Vidrio, agua. En videojuego es alfa. |
| Subsuperficie | Piel, cera, mármol, leche. |
| Barniz | Laca, pintura de coche, esmalte. |
| Pelusa | Terciopelo, lana. |
| Emisión | Neones, pantallas. |

Lee los avisos debajo de la esfera: te dicen si algo no es realista y por qué.
Para editar el material de otro objeto, selecciónalo y pulsa **Cuentagotas**.

## 4. Texturas

- **Desde Painter**: selecciona el objeto (con UVs), pestaña **Painter › Enviar a Painter**. En Painter, en el
  panel *Muestrario*, pulsa **Abrir**, pinta y pulsa **Exportar a Maya**. Las texturas aparecen solas en Maya
  cada vez que exportas.
- **De internet o de otra carpeta**: pestaña **Texturas**, elige la carpeta, **Analizar** y **Conectar**.

## 5. Antes de entregar

- **Texturas › Copiar al proyecto**: así las texturas viajan con la escena.
- **Escena**: borra los materiales sin usar y pon el prefijo `M_` a los tuyos.
- Si al abrir en otro ordenador salen texturas rosas: **Texturas › Reparar rutas**.
