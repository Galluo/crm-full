from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import db, Product
from datetime import datetime

products_bp = Blueprint('products', __name__)

@products_bp.route('/api/products', methods=['GET'])
@jwt_required()
def get_products():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        low_stock = request.args.get('low_stock', False, type=bool)
        
        query = Product.query.filter_by(is_active=True)
        
        if search:
            query = query.filter(
                Product.name.contains(search) |
                Product.description.contains(search) |
                Product.sku.contains(search)
            )
        
        if category:
            query = query.filter_by(category=category)
        
        if low_stock:
            query = query.filter(Product.stock_quantity <= 10)
        
        products = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'products': [product.to_dict() for product in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<int:product_id>', methods=['GET'])
@jwt_required()
def get_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        return jsonify(product.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products', methods=['POST'])
@jwt_required()
def create_product():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        if not data.get('price'):
            return jsonify({'error': 'Price is required'}), 400
        
        # Check if SKU already exists
        if data.get('sku'):
            existing_product = Product.query.filter_by(sku=data['sku']).first()
            if existing_product:
                return jsonify({'error': 'SKU already exists'}), 400
        
        product = Product(
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            stock_quantity=data.get('stock_quantity', 0),
            sku=data.get('sku'),
            category=data.get('category'),
            is_active=data.get('is_active', True)
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify(product.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<int:product_id>', methods=['PUT'])
@jwt_required()
def update_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        # Check if SKU already exists (excluding current product)
        if data.get('sku') and data['sku'] != product.sku:
            existing_product = Product.query.filter_by(sku=data['sku']).first()
            if existing_product:
                return jsonify({'error': 'SKU already exists'}), 400
        
        product.name = data.get('name', product.name)
        product.description = data.get('description', product.description)
        product.price = data.get('price', product.price)
        product.stock_quantity = data.get('stock_quantity', product.stock_quantity)
        product.sku = data.get('sku', product.sku)
        product.category = data.get('category', product.category)
        product.is_active = data.get('is_active', product.is_active)
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(product.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<int:product_id>', methods=['DELETE'])
@jwt_required()
def delete_product(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        
        # Check if product has order items
        if product.order_items.count() > 0:
            return jsonify({'error': 'Cannot delete product with existing orders'}), 400
        
        db.session.delete(product)
        db.session.commit()
        
        return jsonify({'message': 'Product deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/categories', methods=['GET'])
@jwt_required()
def get_categories():
    try:
        categories = db.session.query(Product.category).filter(
            Product.category.isnot(None),
            Product.is_active == True
        ).distinct().all()
        
        return jsonify({
            'categories': [cat[0] for cat in categories if cat[0]]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/low-stock', methods=['GET'])
@jwt_required()
def get_low_stock_products():
    try:
        threshold = request.args.get('threshold', 10, type=int)
        
        products = Product.query.filter(
            Product.stock_quantity <= threshold,
            Product.is_active == True
        ).all()
        
        return jsonify({
            'products': [product.to_dict() for product in products],
            'count': len(products)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@products_bp.route('/api/products/<int:product_id>/adjust-stock', methods=['POST'])
@jwt_required()
def adjust_stock(product_id):
    try:
        product = Product.query.get_or_404(product_id)
        data = request.get_json()
        
        adjustment = data.get('adjustment', 0)
        reason = data.get('reason', '')
        
        if not isinstance(adjustment, int):
            return jsonify({'error': 'Adjustment must be an integer'}), 400
        
        new_quantity = product.stock_quantity + adjustment
        
        if new_quantity < 0:
            return jsonify({'error': 'Stock quantity cannot be negative'}), 400
        
        product.stock_quantity = new_quantity
        product.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Stock adjusted successfully',
            'product': product.to_dict(),
            'adjustment': adjustment,
            'reason': reason
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

