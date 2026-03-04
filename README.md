# Sistema de Gestión Bibliotecaria
Solución integral de código abierto para la administración de inventarios, préstamos de equipos y control de acceso en centros educativos y empresariales.

## Descripción General
Esta plataforma automatiza el flujo de trabajo de bibliotecas y centros de recursos modernos. Diseñada originalmente para gestionar el alto tráfico de usuarios, el sistema permite un control riguroso sobre activos físicos como equipos de cómputo, material bibliográfico y accesorios técnicos, adaptándose a cualquier institución que requiera una gestión de recursos eficiente.

## Características Principales
### Gestión Multitier de Usuarios
Usuario Estándar: Registro simplificado por perfil (estudiante, empleado, etc.) con límites de solicitud configurables.

Usuario Premium/Instructor: Acceso a inventario especializado (equipos audiovisuales, herramientas técnicas) y gestión de préstamos grupales.

Administrador (SuperUser): Panel de control centralizado para la gestión de inventarios, auditoría de devoluciones y actualización de bases de datos.

### Módulos de Operación
Motor de Préstamos Inteligente: Validación en tiempo real de stock y prevención de duplicados por usuario.

Inventario Dinámico: Categorización flexible de ítems (General vs. Especializado) con trazabilidad por seriales.

Kiosco "Fast Loan": Interfaz de autoservicio optimizada para agilizar procesos de alta demanda mediante búsqueda por documento de identidad, sin fricción de inicio de sesión.

Registro de Actividad: Módulo de control de visitas y estadísticas de uso de espacios físicos.

### 💻 Instalación y Despliegue
1. Configuración del Entorno
Es obligatorio el uso de entornos virtuales para evitar desastres en las dependencias globales de tu sistema.

```bash

# Clonar y acceder
git clone https://github.com/tu-usuario/Sistema-Gestion-Bibliotecaria.git
cd Sistema-Gestion-Bibliotecaria

# Configurar venv
python -m venv venv
source venv/bin/activate  # En Windows use: .\venv\Scripts\activate

# Instalar dependencias
python.exe -m pip install --upgrade pip
pip install -r requirements.txt
```
2. Ejecución
El sistema inicializa la base de datos SQLite automáticamente en el primer arranque.

```bash
python run.py
```
Local: http://localhost:5000

Red Local: Disponible en 0.0.0.0 para acceso desde dispositivos móviles o terminales de kiosco en la misma red.

### 📁 Arquitectura del Proyecto
El software sigue un patrón de diseño modular para facilitar el escalamiento:

app/admin/: Lógica de gestión, reportes y aprobaciones.

app/auth/: Sistema de autenticación y seguridad.

app/main/: Dashboards de usuario y lógica del modo Kiosco.

instance/: Persistencia de datos local.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/MaickFeliz/SWL)
