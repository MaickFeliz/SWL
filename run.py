from app import create_app, db
from app.models import User, Inventory

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        if not User.query.filter_by(document_id='1000000000').first():
            print("Creando superusuario 'admin'...")
            admin = User(
                document_id='1000000000', 
                full_name='Administrador Principal', 
                role='admin', 
                phone='0000000000',
                email='admin@biblioteca.com'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

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
                    available_quantity=item['total'],
                    category=item['category']
                )
                db.session.add(new_item)
        
        db.session.commit()
    
    app.run(host='0.0.0.0', port=5000, debug=True)