from app import create_app, db
from app.models import User, Inventory

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # 1. Crear Admin (Ya lo tenías)
        if not User.query.filter_by(username='admin').first():
            print("Creando superusuario 'admin'...")
            admin = User(
                username='admin', 
                document_id='1000000000', 
                full_name='Administrador Principal', 
                role='bibliotecario', 
                phone='0000000000'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        # 2. CREAR INVENTARIO BASE
        initial_items = [
            {'name': 'Mouse USB', 'total': 50, 'category': 'general'},
            {'name': 'VideoBeam', 'total': 10, 'category': 'premium'},
            {'name': 'Cable HDMI', 'total': 20, 'category': 'premium'},
            {'name': 'Televisor', 'total': 5, 'category': 'premium'},
            {'name': 'Regleta/Extension', 'total': 15, 'category': 'premium'},
            {'name': 'Kit LEGO Education', 'total': 8, 'category': 'premium'} 
        ]

        for item in initial_items:
            exists = Inventory.query.filter_by(name=item['name']).first()
            if not exists:
                print(f"Creando item de inventario: {item['name']}")
                new_item = Inventory(
                    name=item['name'],
                    total_quantity=item['total'],
                    available_quantity=item['total'], # Al principio están todos
                    category=item['category']
                )
                db.session.add(new_item)
        
        db.session.commit()
    
    app.run(host='0.0.0.0', port=5000, debug=True)