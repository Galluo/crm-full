from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import db, Customer, Order, Task
from datetime import datetime

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/api/customers', methods=['GET'])
@jwt_required()
def get_customers():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        
        query = Customer.query
        
        if search:
            query = query.filter(
                Customer.name.contains(search) |
                Customer.email.contains(search) |
                Customer.company.contains(search)
            )
        
        customers = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'customers': [customer.to_dict() for customer in customers.items],
            'total': customers.total,
            'pages': customers.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers/<int:customer_id>', methods=['GET'])
@jwt_required()
def get_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        return jsonify(customer.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers', methods=['POST'])
@jwt_required()
def create_customer():
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Name is required'}), 400
        
        # Check if email already exists
        if data.get('email'):
            existing_customer = Customer.query.filter_by(email=data['email']).first()
            if existing_customer:
                return jsonify({'error': 'Email already exists'}), 400
        
        customer = Customer(
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            company=data.get('company'),
            notes=data.get('notes')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify(customer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers/<int:customer_id>', methods=['PUT'])
@jwt_required()
def update_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        data = request.get_json()
        
        # Check if email already exists (excluding current customer)
        if data.get('email') and data['email'] != customer.email:
            existing_customer = Customer.query.filter_by(email=data['email']).first()
            if existing_customer:
                return jsonify({'error': 'Email already exists'}), 400
        
        customer.name = data.get('name', customer.name)
        customer.email = data.get('email', customer.email)
        customer.phone = data.get('phone', customer.phone)
        customer.address = data.get('address', customer.address)
        customer.company = data.get('company', customer.company)
        customer.notes = data.get('notes', customer.notes)
        customer.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(customer.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers/<int:customer_id>', methods=['DELETE'])
@jwt_required()
def delete_customer(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        # Check if customer has orders
        if customer.orders.count() > 0:
            return jsonify({'error': 'Cannot delete customer with existing orders'}), 400
        
        db.session.delete(customer)
        db.session.commit()
        
        return jsonify({'message': 'Customer deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers/<int:customer_id>/orders', methods=['GET'])
@jwt_required()
def get_customer_orders(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        orders = customer.orders.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page,
            'customer': customer.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@customers_bp.route('/api/customers/<int:customer_id>/tasks', methods=['GET'])
@jwt_required()
def get_customer_tasks(customer_id):
    try:
        customer = Customer.query.get_or_404(customer_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        tasks = customer.tasks.order_by(Task.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tasks': [task.to_dict() for task in tasks.items],
            'total': tasks.total,
            'pages': tasks.pages,
            'current_page': page,
            'customer': customer.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

