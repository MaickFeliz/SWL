# Sistema de Gestión Bibliotecaria

> **Plataforma integral para la administración de préstamos, inventario y control de acceso en ambientes de formación.**

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Framework-Flask-green.svg)
![Status](https://img.shields.io/badge/Estado-En_Desarrollo-orange.svg)

## Descripción
Este sistema automatiza el flujo de trabajo de la biblioteca del SENA, permitiendo gestionar préstamos de equipos de cómputo, libros y accesorios. Incluye un módulo de **Kiosco de Autoservicio** y lógica de roles diferenciada para **Aprendices** e **Instructores**.

## Características Principales

### Gestión de Usuarios & Roles
* **Aprendiz:** Registro con Ficha y Programa. Solicitudes limitadas (1 equipo, Mouses).
* **Instructor:** Préstamos masivos para ambientes, acceso a inventario especial (VideoBeams, TV, LEGO).
* **Bibliotecario (Admin):** Panel de control total, aprobación de préstamos, gestión de devoluciones.

### Módulos del Sistema
1.  **Préstamos de Cómputo:**
    * Validación de stock y préstamos duplicados.
    * Asignación de seriales por parte del bibliotecario.
2.  **Inventario en Tiempo Real:**
    * Control de stock (entradas y salidas).
    * Categorización de items (General vs Instructor).
3.  **Kiosco "Fast Loan" (Préstamo Rápido):**
    * Modo para agilizar la fila sin necesidad de login.
    * Búsqueda por documento de identidad.
4.  **Control de Visitas:**
    * Registro de entrada, actividad (Lectura, PC, etc.) y salida.

## Instalación y Puesta en Marcha

### 1. Requisitos Previos
* Python 3.x instalado.
* Git (opcional).

### 2. Configuración del Entorno
```bash
# Clonar el repositorio (si aplica) o descargar la carpeta
cd Biblioteca-SENA

# Crear entorno virtual (Recomendado)
python -m venv venv
# Activar: 
#   Windows: venv\Scripts\activate
#   Mac/Linux: source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

### 3. Ejecución
# El sistema está configurado para inicializar la base de datos automáticamente en la primera ejecución.
```bash
python run.py

# Accede en tu navegador a: http://localhost:5000
# Modo Red Local: El sistema se ejecutará en 0.0.0.0, permitiendo acceso desde otros dispositivos en la misma red WiFi.

SuperAdmin - 1000000000,admin123
Instructor - (Registrar en app),(Personal)
Aprendiz - (Registrar en app),(Personal)

#Nota: El usuario Admin se crea automáticamente al iniciar la aplicación por primera vez.

📂 Estructura del Proyecto
Biblioteca-SENA/
├── app/
│   ├── admin/      # Rutas de gestión y aprobaciones
│   ├── auth/       # Login y Registro
│   ├── main/       # Dashboard Instructor/Aprendiz y Kiosco
│   ├── models.py   # Modelos de Base de Datos (SQLAlchemy)
│   ├── templates/  # Vistas HTML (Jinja2)
│   └── static/     # CSS y Estilos
├── instance/       # Base de datos SQLite (app.db)
├── run.py          # Punto de entrada
└── requirements.txt # Lista de dependencias

Desarrollado por Nosotros.