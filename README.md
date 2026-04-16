# SWL — System Warehouse Library 📖🚀
> **Gestión de activos de alto tráfico, sin fricción y con arquitectura modular.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org/)

**SWL** no es solo un sistema de biblioteca; es un motor de gestión de inventario diseñado para la escala. Desde material bibliográfico hasta equipos técnicos de alto costo, el sistema garantiza trazabilidad total mediante un backend robusto en **Flask** y una persistencia de datos sólida en **PostgreSQL**.

---

## 🔥 Por qué SWL es diferente
* **Arquitectura Desacoplada:** Olvídate del código espagueti. Usamos *Blueprints* para separar la autenticación, la lógica administrativa y la experiencia del usuario final.
* **Kiosco "Fast Loan":** Diseñado para la eficiencia. Préstamos en segundos sin necesidad de login tedioso, ideal para centros de alto tráfico.
* **Tier-Based Access:** Sistema de permisos granular (Standard, Premium, Admin) que controla desde quién puede pedir un libro hasta quién puede auditar un laptop de alta gama.
* **DB Migrations Ready:** Implementación profesional con `Flask-Migrate` para asegurar que tu esquema evolucione sin romper los datos existentes.

---

## 🛠️ Stack Tecnológico
* **Backend:** Python 3.10+ & Flask.
* **Database:** PostgreSQL (Optimizado para relaciones complejas).
* **Frontend:** Jinja2 & CSS3 (Interfaz limpia y funcional).
* **Seguridad:** Werkzeug para hashing de credenciales y Flask-Login para sesiones seguras.

---

## 🚀 Quick Start (No-BS Setup)

### 1. Entorno y Dependencias
```bash
git clone [https://github.com/MaickFeliz/swl.git](https://github.com/MaickFeliz/swl.git)
cd swl
python -m venv venv
# Activa el entorno (Windows: .\venv\Scripts\activate | Linux: source venv/bin/activate)
pip install -r requirements.txt
```

### 2. Base de Datos (PostgreSQL)
Crea tu base de datos y configura el `.env`:
```sql
CREATE DATABASE swl_db;
```
Archivo `.env` (No lo subas al repo, usa `.env.example` como guía):
```env
DATABASE_URL=postgresql://tu_usuario:tu_password@localhost:5432/swl_db
SECRET_KEY=tu_token_super_secreto
```

### 3. Migración y Ejecución
```bash
flask db upgrade
python run.py
```

---

## 📁 Estructura del Proyecto
```text
├── app/
│   ├── admin/      # Control total, reportes y auditoría.
│   ├── auth/       # Seguridad y gestión de sesiones.
│   ├── main/       # El core del usuario y modo Kiosco.
│   ├── services/   # Lógica de negocio (Emails, Préstamos, Inventario).
│   └── models.py   # Esquema de datos centralizado.
├── migrations/     # Historial de versiones de la DB.
└── run.py          # Punto de entrada de la aplicación.
```

---

## 👨‍💻 Autor
Desarrollado con enfoque en la eficiencia por **Maick Arevalo (@MaickFeliz)**.
