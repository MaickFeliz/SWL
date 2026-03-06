from app import create_app, db
from app.models import User, Catalog, ItemInstance, InventoryStatus

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 

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
            exists = Catalog.query.filter_by(title_or_name=item['name']).first()
            if not exists:
                print(f"Creando item de inventario: {item['name']}")
                new_item = Catalog(
                    title_or_name=item['name'],
                    category=item['category']
                )
                db.session.add(new_item)
                db.session.flush()
                
                for i in range(item['total']):
                    code = f"{item['name'][:3].upper().replace(' ', '')}-{new_item.id}-{i+1:03d}"
                    instance = ItemInstance(
                        catalog_id=new_item.id,
                        unique_code=code,
                        status=InventoryStatus.AVAILABLE,
                    )
                    db.session.add(instance)
        
        db.session.commit()
    
    app.run(host='0.0.0.0', port=5000, debug=True)