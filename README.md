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

### Instalación y Despliegue

#### Prerrequisitos

- Python 3.10 o superior
- **Servidor PostgreSQL en ejecución** (local o remoto). Crea una base de datos vacía antes de continuar:
  ```sql
  CREATE DATABASE swl_db;
  ```

#### 1. Configuración del Entorno

```bash
# Clonar y acceder
git clone https://github.com/tu-usuario/Sistema-Gestion-Bibliotecaria.git
cd Sistema-Gestion-Bibliotecaria

# Crear y activar entorno virtual
python -m venv venv
source venv/bin/activate      # Linux / macOS
.\venv\Scripts\activate       # Windows

# Instalar dependencias
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### 2. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto (nunca lo versiones):

```env
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY=cambia_este_valor_por_uno_seguro

# Formato: postgresql://usuario:password@host:puerto/nombre_base_de_datos
DATABASE_URL=postgresql://usuario:password@localhost:5432/swl_db
```

#### 3. Inicializar el Esquema con Flask-Migrate

```bash
# Solo la primera vez — crea la carpeta migrations/ si no existe
flask db init

# Genera el script de migración a partir de los modelos
flask db migrate -m "Migración inicial"

# Aplica la migración a la base de datos PostgreSQL
flask db upgrade
```

> **Actualizaciones futuras**: ante cualquier cambio en los modelos, ejecuta únicamente `flask db migrate -m "descripción"` y `flask db upgrade`.

#### 4. Ejecutar en Desarrollo

```bash
flask run
# o directamente:
python run.py
```

- Local: http://localhost:5000
- Red local: disponible en `0.0.0.0` para acceso desde otros dispositivos en la misma red.


### 📁 Arquitectura del Proyecto
El software sigue un patrón de diseño modular para facilitar el escalamiento:

app/admin/: Lógica de gestión, reportes y aprobaciones.

app/auth/: Sistema de autenticación y seguridad.

app/main/: Dashboards de usuario y lógica del modo Kiosco.

instance/: Persistencia de datos local.

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/MaickFeliz/SWL)
[![Ask Mintlify](https://mintlify.com)](https://maickfeliz-swl.mintlify.app/introduction)
