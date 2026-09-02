# Pautas de modelado y arquitectura — Sistema Taller

Este documento explica CÓMO está armado el sistema y qué reglas seguir para
que se mantenga ordenado a medida que crece. Leelo antes de tocar código.

---

## 1. Patrón: MVC en capas

El sistema separa las responsabilidades en capas. Cada capa hace UNA sola cosa
y solo habla con la capa de al lado. Esto es lo que se llama MVC bien separado
(con una capa de servicios adentro del "controlador" clásico).

```
  VISTA          →  static/index.html        (lo que ve y toca el usuario)
  CONTROLADOR    →  app/controladores/       (recibe el pedido HTTP, coordina)
  SERVICIO       →  app/servicios/           (LÓGICA DE NEGOCIO: el "qué hacer")
  MODELO         →  app/modelos/             (las tablas de la base de datos)
  ESQUEMA        →  app/esquemas/            (contrato: valida entrada y salida)
  NÚCLEO         →  app/nucleo/              (config y conexión a la base)
```

### Qué va en cada capa

| Capa | Responsabilidad | Qué SÍ va | Qué NO va |
|---|---|---|---|
| **Vista** | Mostrar y capturar datos | HTML, CSS, JS del navegador | Lógica de negocio, SQL |
| **Controlador** | Traducir HTTP ↔ servicio | Recibir request, validar existencia, devolver | Consultas SQL, reglas de negocio |
| **Servicio** | Decidir qué hacer | Reglas de negocio, orquestar la base | Nada de HTTP (ni request ni response) |
| **Modelo** | Estructura de los datos | Definición de tablas y relaciones | Lógica, validaciones complejas |
| **Esquema** | Validar y dar forma | Qué campos entran/salen y de qué tipo | Acceso a la base |

### La regla de oro
> El **controlador NO habla con la base de datos directo**. Siempre pasa por el
> **servicio**. Si ves un `select(...)` o un `session.add(...)` dentro de un
> controlador, está mal ubicado: va al servicio.

---

## 2. Cómo viaja una petición (ejemplo real)

Cuando el usuario aprieta "Guardar cliente":

1. **Vista** (`index.html`) hace `fetch("/api/clientes", POST, {nombre:"Juan"})`.
2. **Controlador** (`cliente_controlador.py`) recibe el POST. FastAPI usa el
   **Esquema** `ClienteCrear` para validar que venga `nombre`.
3. El controlador llama a `ServicioCliente.crear(...)`.
4. **Servicio** (`cliente_servicio.py`) crea el objeto **Modelo** `Cliente` y lo
   guarda en la base.
5. La respuesta vuelve, el **Esquema** `ClienteRespuesta` le da forma (oculta lo
   que no debe salir), y llega a la **Vista** que lo muestra en la lista.

Si mañana querés una regla nueva (ej: "no permitir dos clientes con el mismo
teléfono"), se agrega en el **servicio**, en UN solo lugar. Ni la vista ni el
controlador se enteran.

---

## 3. Pautas de modelado de datos (la base)

Reglas para diseñar tablas nuevas cuando el sistema crezca:

1. **Una entidad = una tabla.** Cliente, Auto, Presupuesto, Orden, Repuesto...
   cada cosa del mundo real es su propia tabla.

2. **Clave primaria `id`** autoincremental en toda tabla.

3. **Relaciones con `ForeignKey`.** Un auto pertenece a un cliente →
   `cliente_id` en la tabla autos apunta a `clientes.id`.

4. **Borrado en cascada cuando corresponde.** Si borrás un cliente, sus autos
   se van con él (`ondelete="CASCADE"`). Pero OJO: las órdenes de trabajo NO se
   deben borrar nunca (regla del negocio), así que esas NO llevarán cascada.

5. **Timestamps siempre.** `creado_en` y `actualizado_en` en cada tabla. Sirven
   para auditar y para las métricas de fin de mes.

6. **No repetir texto libre.** Si un valor se repite mucho (ej: estado de una
   orden: "pendiente", "finalizada", "cobrada"), usar una lista fija de valores
   o una tabla de catálogo, no texto suelto que cada uno escribe distinto.

7. **Índices en lo que se busca.** Nombre y teléfono del cliente, patente del
   auto: llevan índice porque son campos por los que se filtra seguido.

8. **Nombres en español, claros y consistentes.** `kilometraje`, no `km` en una
   tabla y `kilometros` en otra.

---

## 4. Cómo agregar una funcionalidad nueva (receta)

Cuando toque sumar, por ejemplo, "Presupuestos", el orden es SIEMPRE este:

1. **Modelo** — crear `app/modelos/presupuesto.py` con la tabla.
2. **Esquema** — crear `app/esquemas/presupuesto.py` con qué entra/sale.
3. **Servicio** — crear `app/servicios/presupuesto_servicio.py` con la lógica.
4. **Controlador** — crear `app/controladores/presupuesto_controlador.py` con
   los endpoints, que solo llaman al servicio.
5. **Registrar** el controlador en `app/main.py`.
6. **Vista** — sumar la pantalla en `index.html`.

Siempre de adentro (datos) hacia afuera (pantalla). Nunca al revés.

---

## 5. Migraciones (cuidado con la base en producción)

- En **desarrollo** (SQLite local) las tablas se crean solas al arrancar.
- En **producción** (Neon) NO se debe recrear ni borrar tablas a lo loco: se
  pierden datos. Los cambios de estructura se hacen con **migraciones
  aditivas** (agregar columna/tabla nueva sin romper lo que ya existe).
- El `schema.sql` sirve como documentación de diseño y para el primer armado.

---

## 6. Convenciones del proyecto

- Todo el código y los comentarios en **español**.
- Rutas de la API en español: `/api/clientes`, `/api/autos`.
- Una clase de servicio por entidad: `ServicioCliente`, `ServicioAuto`.
- Los controladores son finitos: reciben, llaman al servicio, devuelven.

---

## 7. Etapa 2 — Presupuestos y Órdenes (ya implementada)

Se agregaron dos entidades siguiendo la receta de la sección 4.

### Modelos nuevos
- `Presupuesto` + `PresupuestoItem` (`app/modelos/presupuesto.py`)
- `OrdenTrabajo` + `OrdenItem` (`app/modelos/orden.py`)

### Reglas de negocio aplicadas (importantes)
- **El presupuesto SÍ se puede editar y borrar.** Tiene endpoint DELETE.
- **La orden de trabajo NO se borra nunca.** Es deliberado: NO existe endpoint
  DELETE en `orden_controlador.py`. Queda grabada de forma permanente.
- **Estados de la orden:** `pendiente` → `finalizada` → `cobrada`.
- **`finalizada` es el estado clave**, no `cobrada`. Cuando la orden se marca
  finalizada se guarda `finalizada_en`. En la Etapa 3, en ese mismo punto del
  servicio (`cambiar_estado`), se va a descontar el stock. Se usa 'finalizada'
  y no 'cobrada' porque el auto se puede entregar/cobrar después, pero el
  trabajo ya salió y hay que descontar los repuestos igual.
- **Una orden cobrada no se puede editar** (queda cerrada).
- La orden puede **nacer de un presupuesto** (endpoint `/ordenes/desde-presupuesto`)
  copiando sus ítems, o crearse directa.

### Totales
Los subtotales y el total NO se guardan en la base: se calculan al vuelo en el
servicio cada vez que se pide el documento (función `_armar_respuesta`). Así
nunca quedan desactualizados si cambia un ítem.

### Preparado para la Etapa 3
- `OrdenItem` ya tiene `repuesto_id` y `es_repuesto`, listos para enganchar el
  stock. El descuento irá en `ServicioOrden.cambiar_estado`, cuando el estado
  pasa a 'finalizada'.

---

## 8. Etapa 3 — Stock, descuento automático y alerta (ya implementada)

### Modelo nuevo
- `Repuesto` (`app/modelos/repuesto.py`): nombre, código, precio, cantidad y
  `minimo` (umbral de aviso).

### Cómo se descuenta el stock
- El descuento vive en `ServicioOrden.cambiar_estado`, cuando la orden pasa a
  `finalizada` por primera vez. Recorre los ítems: si el ítem es repuesto y
  tiene `repuesto_id`, llama a `ServicioRepuesto.descontar`.
- **Idempotente:** solo entra cuando `finalizada_en` estaba vacío, así una orden
  nunca descuenta stock dos veces (aunque se vuelva a marcar finalizada).
- Toda la modificación de stock pasa por `ServicioRepuesto` (una sola fuente de
  verdad). El servicio de orden no toca la tabla de repuestos directo.

### Reglas de stock
- El stock nunca queda negativo (los ajustes manuales se rechazan si darían < 0;
  el descuento por orden deja en 0 como piso, porque el trabajo ya se hizo).
- `stock_bajo` se calcula al vuelo: `cantidad <= minimo`. No se guarda.

### Alerta de stock bajo
- `GET /api/repuestos?solo_bajos=true` devuelve los que están en o bajo el
  mínimo. La vista muestra un contador rojo en el botón "Stock" y resalta las
  fichas en rojo.

### Vista
- Se agregó navegación superior (Clientes / Stock).
- Al cargar ítems en una orden se puede elegir un repuesto del stock desde un
  selector; eso setea `repuesto_id` y es lo que habilita el descuento.

### Preparado para la Etapa 4 (WhatsApp)
- El total del presupuesto/orden ya se calcula; falta armar el texto y el link
  wa.me con el teléfono del cliente.

---

## 8. Etapas 4, 5 y 6 (ya implementadas)

### Etapa 4 — WhatsApp con un clic
- Servicio: `app/servicios/whatsapp_servicio.py`. Arma el mensaje (con ítems y
  total) y devuelve un link `wa.me`. NO usa la API de Meta (gratis, sin trámites).
- El teléfono del cliente se limpia dejando solo dígitos (código país incluido).
- El front abre el link con `window.open`, que lanza WhatsApp Web/App con el
  chat y el mensaje ya cargado.
- Endpoints: `/api/whatsapp/presupuesto/{id}` y `/api/whatsapp/orden/{id}`.

### Etapa 5 — Métricas de fin de mes
- Servicio: `app/servicios/metricas_servicio.py`. Cuenta autos ingresados,
  órdenes finalizadas/cobradas, total facturado (órdenes cobradas del mes) y
  repuestos con stock bajo. Devuelve además un resumen en lenguaje natural.
- Endpoint: `/api/metricas/mes?anio=&mes=` (sin parámetros: mes actual).

### Etapa 6 — QR de vehículo con historial
- Servicio: `app/servicios/historial_servicio.py`. Usa el `qr_token` que cada
  auto ya tenía desde la Etapa 1.
- Genera la imagen del QR (librería `qrcode`) que apunta a una URL pública.
- `/api/autos/{id}/qr` devuelve el QR en base64 + la URL.
- `/historial/{qr_token}` es la PÁGINA PÚBLICA (HTML) que se ve al escanear:
  muestra el auto y todo su historial de órdenes. No requiere login (es la
  gracia: el cliente escanea y ve).

### Dependencia nueva
- `qrcode[pil]` (agregada a requirements.txt).
- Se quitó `asyncpg` del requirements fijo (daba error de compilación en
  Windows con Python nuevo). Para producción con Neon se instala aparte.

---

## 9. Dashboard nuevo + Login + IA (implementado)

### Interfaz (TallerPro)
- El `static/index.html` se rediseñó con Tailwind: sidebar, login modal, y las
  vistas Clientes, Stock, Métricas y Diagnóstico IA. Toda la lógica anterior
  (clientes, autos, presupuestos, órdenes, stock, WhatsApp, QR) sigue funcionando,
  ahora dentro de la interfaz nueva.

### Login (Paso 1 — básico)
- `app/nucleo/auth.py` + `app/controladores/auth_controlador.py`.
- Usuario/contraseña en variables de entorno (ADMIN_USUARIO / ADMIN_PASSWORD).
- Genera un token simple guardado en memoria. El front lo guarda en localStorage.
- OJO: es un login básico para un único dueño / uso local. Para producción en
  internet falta el "Paso 3": contraseñas hasheadas en base, expiración de
  tokens, y proteger los endpoints con el token.

### IA (Paso 2 — Gemini)
- `app/servicios/ia_servicio.py` + `app/controladores/ia_controlador.py`.
- Usa la API de Google Gemini (modelo gemini-1.5-flash, plan gratuito).
- Requiere GEMINI_API_KEY en el .env (gratis en aistudio.google.com/apikey).
- Si no hay key, la sección lo avisa y no rompe nada.

### Config
- Ver `.env.ejemplo`. Copiar como `.env` y completar.
- Dependencia nueva: `httpx` (para llamar a Gemini).

---

## 10. Nota opcional en el QR (implementado)

- Se agregó el campo `nota_qr` a la tabla `autos` (público, aparte de `notas`
  que es interno).
- En el modal del QR de cada auto se puede escribir una nota opcional y guardarla.
- La nota aparece en la página pública del historial (arriba de las órdenes),
  como un recuadro "Observación". El historial automático de órdenes sigue igual.
- Como la columna es nueva sobre una tabla existente, hay un `migrate.py`
  aditivo: si ya tenías la base con datos, corré `python migrate.py` una vez.
  Es seguro (no borra nada; si la columna ya existe, no hace nada).
