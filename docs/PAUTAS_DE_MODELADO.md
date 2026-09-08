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

---

## 11. Vistas generales (Vehículos, Presupuestos, Órdenes)

Antes estos ítems del menú solo avisaban "está dentro del cliente". Ahora son
pantallas propias con vista general de todo el taller:

- **Vehículos**: tabla con todos los autos, búsqueda por patente/marca/modelo/cliente.
- **Presupuestos**: todos los presupuestos del taller con su auto y cliente.
- **Órdenes**: todas las órdenes, con filtro por estado (pendiente/finalizada/cobrada).

Cada fila tiene un botón "Abrir/Ver" que lleva al cliente correspondiente con el
auto ya desplegado, para operar (crear orden, mandar WhatsApp, etc.). La gestión
sigue viviendo dentro del cliente; estas vistas son de consulta rápida.

Endpoints nuevos:
- `GET /api/autos?q=` (todos los vehículos)
- `GET /api/presupuestos` (todos)
- `GET /api/ordenes?estado=` (todas, con filtro)

Los servicios ganaron un método `listar_todos` que incluye datos del auto y
cliente en la respuesta.

---

## 12. Rebranding a "Dodorico Mecánica"

Se reemplazó "TallerPro" por "Dodorico Mecánica" en todo lo visible: título de
la pestaña, logo del sidebar, barra del celular, login y título de la API
(app/main.py). Los nombres técnicos internos (tablas, variables, rutas) NO se
tocaron para no romper nada.

---

## 13. Etapa A — Estado "En Proceso", validación de stock, borrado con rol y auditoría

### Estados de la orden
Ahora son cuatro: ESTADOS_ORDEN = ("pendiente", "en_proceso", "finalizada", "cobrada").
Flujo: Pendiente → En Proceso → Finalizada → Cobrada.

### Validación de stock (ServicioOrden.cambiar_estado)
- Al pasar de "pendiente" a "en_proceso": por cada ítem repuesto sin reserva
  previa, se reserva el stock en el momento (lo que valida disponibilidad). Si
  no alcanza, HTTPException(400) con el detalle del repuesto que falta.
- Al finalizar: se consume el stock (baja cantidad Y reservado a la vez).

### Auditoría
- Modelo LogAccion (app/modelos/log_accion.py): usuario, accion, detalle, creado_en.
- ServicioLog.registrar(...) (sin commit propio, entra en la transacción del que llama).

### Rol REAL en el backend (¡importante!)
- Hasta ahora el control de rol vivía solo en el frontend (esconder botones).
- Se agregó requiere_rol("admin") en app/nucleo/auth.py: una dependencia de
  FastAPI que lee el header "Authorization: Bearer <token>", valida el token y
  devuelve 401/403 según corresponda. El frontend manda el token en ese header.

### Borrado de órdenes (DELETE /api/ordenes/{id})
- Solo admin (Depends(requiere_rol("admin"))), solo si la orden está pendiente
  (si no, 400). Libera las reservas de los ítems y registra la baja en LogAccion.
- Es el ÚNICO lugar con botón de eliminar orden (en la vista general de Órdenes),
  visible solo para admin y solo en órdenes pendientes.

---

## 14. Etapa B — Reserva de stock (físico / reservado / disponible)

### Modelo
- Repuesto ganó el campo 'reservado' (INTEGER, default 0, CheckConstraint >= 0).
- disponible = cantidad - reservado (calculado al vuelo en _armar, como stock_bajo).
- OrdenItem ganó el flag 'reservado' (bool): marca si ese ítem ya tiene su reserva.

### Servicio (ServicioRepuesto)
- reservar(sesion, repuesto_id, cantidad): sube 'reservado'. Falla con 400 si
  disponible < cantidad. Sin commit propio.
- liberar(...): baja 'reservado'. Sin commit propio.
- descontar(..., desde_reserva=False): baja 'cantidad'; si desde_reserva=True,
  también baja 'reservado' (la reserva se convierte en consumo real).
- Los tres releen el repuesto con with_for_update=True (bloqueo de fila) para
  control de concurrencia: dos órdenes no pueden reservar las mismas unidades.

### Flujo de reservas
- Crear orden con ítem repuesto → reserva (si no hay stock, se agrega sin reserva).
- Finalizar orden → consume la reserva (no queda "reservado" fantasma).
- Borrar orden pendiente → libera las reservas de sus ítems.

### Migración
- Columnas nuevas agregadas a la migración automática de main.py:
  repuestos.reservado y orden_items.reservado (aditivas, no borran datos).

### Pendiente (próximas etapas)
- Etapa C: buscador predictivo también en presupuestos + compatibilidad marca/modelo.
- Etapa D: proveedores + modal de faltante + disparador de compra por WhatsApp.

---

## 15. Etapa C — Buscador predictivo en presupuestos + compatibilidad

### Buscador predictivo unificado
- Antes el buscador con autocompletado solo existía en Órdenes. Ahora también
  en Presupuestos, usando funciones genéricas (buscarRepPredictivoGen,
  elegirRepBuscadoGen) parametrizadas por el arreglo destino (itemsTmp o
  itemsOrdTmp) y el prefijo del contenedor de sugerencias.
- PresupuestoItem ganó repuesto_id (igual que OrdenItem), y el esquema y
  _armar_respuesta del presupuesto lo exponen.

### Compatibilidad marca/modelo
- Repuesto ganó marca_compatible y modelo_compatible (texto libre opcional).
  Si están vacíos, el repuesto sirve para cualquier auto.
- ServicioRepuesto.listar acepta marca/modelo: los repuestos compatibles con
  ese auto se listan PRIMERO (no se excluyen los demás). Cada repuesto sale con
  un flag "compatible".
- El frontend pasa la marca/modelo del auto activo (autosActivos) a la búsqueda,
  y muestra una etiqueta azul "✓ compatible" en los que matchean.
- El form de repuesto (stock) permite cargar la marca/modelo compatible.

### Conversión presupuesto → orden
- crear_desde_presupuesto ahora COPIA el repuesto_id de cada ítem (antes lo
  perdía) y RESERVA el stock igual que ServicioOrden.crear (mantiene la lógica
  de Etapa B: si no hay stock, se agrega sin reserva).

### Nota de diseño sobre reservas
- El presupuesto NO reserva stock (es una cotización). La reserva ocurre cuando
  se crea la orden (directa o desde presupuesto). Así se evita la doble reserva
  y el "reservado fantasma" si un presupuesto nunca se convierte en orden.

### Migración
- Columnas nuevas en la migración automática: repuestos.marca_compatible,
  repuestos.modelo_compatible, presupuesto_items.repuesto_id (todas aditivas).

### Pendiente
- Etapa D: proveedores + modal de faltante + disparador de compra por WhatsApp.

---

## 16. Etapa D — Proveedores + modal de faltante + disparador de compra

### Proveedores (entidad nueva, receta completa)
- Modelo Proveedor (app/modelos/proveedor.py): id, nombre, telefono, notas, timestamps.
- Esquema, ServicioProveedor (CRUD), proveedor_controlador.py (CRUD),
  registrado en main.py. Rutas: /api/proveedores.
- Sección "Proveedores" en el menú (solo admin) con CRUD desde el frontend.

### Vínculo repuesto ↔ proveedor
- Repuesto ganó proveedor_id (FK opcional). El form de repuesto (stock) tiene un
  selector de proveedor. Expuesto en el esquema y en _armar.

### Modal de faltante (reemplaza el confirm nativo)
- Antes, elegir un repuesto sin stock usaba confirm(). Ahora abre una modal
  propia (modalFaltante, mismo patrón visual que modalQR) que muestra el nombre
  del repuesto y dos/tres botones:
  - "Agregar igual (sin stock)": comportamiento anterior.
  - "Pedir a proveedor": SOLO visible si el repuesto tiene proveedor_id.
  - "Cancelar".

### Disparador de compra por WhatsApp
- whatsapp_servicio.py ganó link_reposicion(sesion, repuesto_id): arma un
  mensaje "Hola [proveedor], necesitamos reponer [repuesto] (código [x])..."
  con cantidad sugerida (para llegar al mínimo) y devuelve el link wa.me con el
  teléfono del proveedor. Mismo patrón de limpieza de teléfono que clientes.
- Endpoint GET /api/whatsapp/reposicion/{repuesto_id}. Da 404 con mensaje claro
  si el repuesto no tiene proveedor.
- El botón "Pedir a proveedor" de la modal llama al endpoint y abre el link con
  window.open (igual que enviarWhatsApp para presupuestos/órdenes).

### Migración
- Columna nueva en la migración automática: repuestos.proveedor_id (aditiva).
- Tabla proveedores se crea sola con create_all.

### Estado del proyecto
Con las Etapas A, B, C y D completas, la Especificación de Requerimientos del
módulo de Presupuestos/Órdenes/Stock quedó implementada: estados con validación,
reserva de stock, buscador predictivo con compatibilidad, y proveedores con
disparador de compra. Todo con rol validado en backend y auditoría de borrados.

---

## 17. Módulo de Compras + métricas de evolución de precios

### Modelo Compra (historial de compras)
- app/modelos/compra.py: repuesto_id, proveedor_id (opcional), fecha, cantidad,
  costo_unitario, creado_en. Cada compra es un registro histórico.
- Registrado en __init__ y con esquema/servicio/controlador completos.

### Registrar compra (suma stock)
- ServicioCompra.registrar: guarda la compra Y suma la cantidad al stock del
  repuesto (with_for_update para concurrencia), todo en una transacción.
- Convive con el +/- manual: el +/- es para ajustes rápidos sin costo; registrar
  compra es la forma "buena" de reponer (con fecha, costo y proveedor).
- Frontend: botón de carrito en cada fila del stock abre la modal de compra
  (fecha por defecto hoy, cantidad, costo unitario, proveedor pre-seleccionado
  del repuesto). Endpoint POST /api/compras.

### Métricas de evolución de precios
- ServicioMetricasCompras.evolucion_precios: por cada repuesto con 2+ compras,
  calcula la variación de costo entre la primera y la última compra (monto y %),
  ordenado por mayor aumento. También lista los más comprados.
- Endpoint GET /api/metricas/precios.
- Frontend: en Métricas, un reporte "Evolución de precios de compra" que muestra
  1ra compra, última, y variación % con flecha (▲ rojo si subió, ▼ verde si bajó).
  Sirve para decidir qué comprar por cantidad o negociar precio.

### Por qué es útil (visión de negocio)
- Saber qué repuesto más aumenta y más rota permite al dueño comprar por
  cantidad o pelear el precio antes de una suba. Es una métrica accionable.

### Nota
- La tabla compras se crea sola con create_all (no requiere migración de columnas).
