# Taller — Sistema de gestión (versión MVC)

Programa base para taller mecánico, armado en **capas MVC bien separadas**.
Etapa 1: clientes y vehículos. Pensado para ejecutarlo y seguir creciendo prolijo.

> 📄 **Leé primero `docs/PAUTAS_DE_MODELADO.md`** — explica cómo está armado y las
> reglas para agregar cosas nuevas sin desordenar el proyecto.

## Estructura (cada carpeta es una capa)

```
taller_mvc/
├── app/
│   ├── nucleo/              # NÚCLEO: config y conexión a la base
│   │   ├── config.py
│   │   └── base_datos.py
│   ├── modelos/            # MODELO: las tablas (cliente.py, auto.py)
│   ├── esquemas/          # ESQUEMA: validación entrada/salida
│   ├── servicios/         # SERVICIO: la lógica de negocio
│   ├── controladores/     # CONTROLADOR: los endpoints HTTP
│   └── main.py            # arma todo y sirve la vista
├── static/
│   └── index.html         # VISTA: la pantalla
├── docs/
│   └── PAUTAS_DE_MODELADO.md
├── requirements.txt
└── test_api.py            # prueba de humo
```

## Correrlo

```bash
python -m venv venv
# Windows (Git Bash):
source venv/Scripts/activate
# Linux/Mac:  source venv/bin/activate

pip install -r requirements.txt
python migrate.py   # solo si ya tenías la base con datos (agrega columnas nuevas)
uvicorn app.main:app --reload
```

Abrir: http://127.0.0.1:8000

Sin configurar nada usa SQLite local. Para Neon, crear `.env`:

```
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx-pooler.sa-east-1.aws.neon.tech/db?sslmode=require
```

(Neon + asyncpg: endpoint POOLER + `sslmode=require`, SIN `channel_binding`.)

## Probar el backend

```bash
python test_api.py
```

## Diferencia con la versión anterior

- Antes: el controlador hablaba con la base directo (mezclaba lógica y HTTP).
- Ahora: se agregó la capa **servicios** en el medio. El controlador solo
  coordina, la lógica vive en el servicio. Es MVC de manual.

## Próximas etapas (receta en las pautas, sección 4)

2. Presupuestos y órdenes de trabajo
3. Stock + descuento automático al finalizar + alerta de stock bajo
4. WhatsApp con un clic
5. Métricas simples de fin de mes
6. QR de vehículo con historial
```
