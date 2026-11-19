# RelAİ Workbench

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009485?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Electron](https://img.shields.io/badge/Electron-35-2F3246?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Licencia: MIT](https://img.shields.io/badge/License-MIT-6d8768.svg)](LICENSE)
[![Demo en vivo](https://img.shields.io/badge/Live-Demo-2ea043?style=flat-square)](http://185.34.101.41:8000)

**Un escritorio de IA autoalojado con aspecto hecho a mano, no por una plantilla.**

RelAİ es un servidor central de IA con una interfaz web cálida y artesanal y un cliente de escritorio Electron. Ejecuta modelos locales de [Ollama](https://ollama.com/), busca en la web cuando una pregunta necesita datos reales, lee tus archivos y mantiene chats, usuarios, roles y estadísticas de administración en un mismo lugar tranquilo.

> Documentación: [Türkçe](README.tr.md) · [English](README.md) · **Español**

**Demo en vivo → <http://185.34.101.41:8000>**

El registro está abierto. SMTP no está configurado a propósito en la demo, así que el código de verificación de 6 dígitos aparece en la pantalla de registro; úsalo para verificar tu cuenta y entrar al instante.

---

## Por qué destaca

- **Datos antes que conjeturas.** Las preguntas informativas pasan por una búsqueda HTML de DuckDuckGo *antes* de que el modelo responda. Las matemáticas puras se calculan directamente.
- **Una interfaz con huella propia.** Papel cálido, barra lateral de «escritorio» oscura, titulares serif, iconos SVG propios, avatares con iniciales y un interruptor real de claro/oscuro. Sin emojis de robot ni degradados morados.
- **Verificación por correo.** Códigos de seis dígitos, 10 minutos de validez, 5 intentos, 60 segundos de espera para reenviar y acceso automático tras verificar.
- **Una identidad en todas partes.** Inicia sesión con usuario *o* correo. Sesiones, roles, usuarios bloqueados, historial y análisis de archivos se comparten entre web y escritorio.
- **Voz dentro, voz fuera.** Reconocimiento de voz del navegador para escribir y síntesis de voz para escuchar las respuestas.
- **Compañero opcional de Discord.** Moderación, niveles, economía, tickets, mensajes de bienvenida y módulos de música incluidos.

## Stack

| Capa | Tecnología |
| --- | --- |
| API | FastAPI + Uvicorn |
| Almacenamiento | SQLite (usuarios, sesiones, chats, archivos, registros) |
| Modelo | Ollama (local) |
| Web | HTML / CSS / JavaScript puro — sin framework |
| Escritorio | Electron 35 |
| Correo | SMTP mediante `smtp.json` |

## Estructura del repositorio

```text
relai-workbench/
├── server/
│   ├── app.py            # API, canal de chat, búsqueda web obligatoria
│   ├── auth.py           # contraseñas PBKDF2 + sesiones bearer
│   ├── db.py             # esquema y consultas SQLite
│   ├── mailer.py         # códigos de verificación SMTP
│   ├── ollama.py         # cliente del modelo local
│   ├── tools.py          # búsqueda web, calculadora, clima
│   ├── static/           # interfaces de acceso, app y administración
│   └── requirements.txt
├── desktop/              # carcasa Electron (carga la URL del servidor)
└── discord-bot/          # bot de Discord opcional
```

## Inicio rápido

### 1. Instala y ejecuta el servidor

```bash
cd server
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

Configura las variables de entorno (ejemplo en PowerShell):

```powershell
$env:OLLAMA_MODEL = 'gemma2:2b'
$env:ADMIN_USERNAME = 'admin'
$env:ADMIN_PASSWORD = 'elige-una-clave-fuerte'
python -m uvicorn app:app --host 0.0.0.0 --port 8000
```

Abre <http://localhost:8000>. El panel de administración está en `/admin`.

### 2. Descarga un modelo

```bash
ollama pull gemma2:2b
```

`gemma2:2b` va rápido con 4 GB de RAM. `qwen2.5:3b` es más potente, pero mucho más lento en equipos pequeños.

### 3. Activa correos de verificación reales

```bash
copy server\smtp.example.json server\smtp.json
```

Rellena `host`, `port`, `security`, `username`, `password` y `from`. Gmail requiere una **contraseña de aplicación**, no la contraseña de la cuenta. Si SMTP no está configurado, el código de seis dígitos se muestra en la pantalla de registro para que puedas probar el flujo igualmente.

### 4. Compila el cliente de escritorio

```bash
cd desktop
npm install
copy config.example.json config.json
# ajusta "serverUrl" a tu servidor, p. ej. http://localhost:8000
npm run build
```

El instalador aparece en `desktop/dist/`. La ventana de Electron solo carga la app web, así que los cambios de interfaz no requieren recompilar.

### 5. Bot de Discord opcional

```bash
cd discord-bot
copy config.example.json config.json
# pega el token de tu bot en config.json
pip install -r requirements.txt
python bot.py
```

## Resumen de la API

| Método | Ruta | Uso |
| --- | --- | --- |
| POST | `/api/register` | Crear cuenta + enviar código |
| POST | `/api/verify-email` | Verificar código, devolver token de sesión |
| POST | `/api/resend-code` | Pedir otro código (espera de 60 s) |
| POST | `/api/login` | Acceder con usuario o correo |
| GET | `/api/me` | Usuario actual |
| POST | `/api/chat` | Preguntar al asistente |
| GET / POST / DELETE | `/api/conversations`, `/api/files` | Historial y análisis de archivos |
| GET | `/api/admin/stats`, `/api/admin/users` | Datos de administración |

## Notas de seguridad

- Cambia la contraseña de administrador por defecto de inmediato.
- Pon HTTPS delante del servidor (Caddy o Nginx) antes de exponerlo a internet.
- Nunca subas `server/data/`, `server/smtp.json`, `desktop/config.json`, `discord-bot/config.json` ni ningún archivo `.env`. `.gitignore` ya los cubre.

## Licencia

MIT — consulta [LICENSE](LICENSE). Hecho con cuidado, no con una plantilla.
