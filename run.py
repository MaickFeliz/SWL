from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Crear Admin por defecto si no existe
        if not User.query.filter_by(username='admin').first():
            print("⚠️ Creando superusuario 'admin' con clave 'admin123'...")
            admin = User(username='admin', role='bibliotecario')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True)