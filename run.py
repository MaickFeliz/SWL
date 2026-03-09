from app import create_app

app = create_app()

# El esquema de la base de datos se gestiona exclusivamente mediante Flask-Migrate.
# Para inicializar o actualizar el esquema, ejecuta:
#
#   flask db init          (solo la primera vez, si no existe la carpeta migrations/)
#   flask db migrate -m "Migración inicial"
#   flask db upgrade
#
# Para poblar la base de datos con datos iniciales, usa los comandos CLI definidos
# en app/cli.py (por ejemplo: flask seed-db).

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)