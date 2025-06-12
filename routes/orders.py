from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import db, Order, OrderItem, Customer, Product, User, Notification
from datetime import datetime

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/api/orders', methods=['GET'])
@jwt_required()
def get_orders():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', '')
        customer_id = request.args.get('customer_id', type=int)
        
        query = Order.query
        
        if status:
            query = query.filter_by(status=status)
        
        if customer_id:
            query = query.filter_by(customer_id=customer_id)
        
        orders = query.order_by(Order.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'orders': [order.to_dict() for order in orders.items],
            'total': orders.total,
            'pages': orders.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders/<int:order_id>', methods=['GET'])
@jwt_required()
def get_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        return jsonify(order.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders', methods=['POST'])
@jwt_required()
def create_order():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        if not data.get('customer_id'):
            return jsonify({'error': 'Customer ID is required'}), 400
        if not data.get('items') or len(data['items']) == 0:
            return jsonify({'error': 'Order items are required'}), 400
        
        # Validate customer exists
        customer = Customer.query.get(data['customer_id'])
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        # Create order
        order = Order(
            customer_id=data['customer_id'],
            order_date=datetime.utcnow(),
            status=data.get('status', 'pending'),
            notes=data.get('notes'),
            created_by=current_user_id
        )
        
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        total_amount = 0
        
        # Add order items
        for item_data in data['items']:
            if not item_data.get('product_id') or not item_data.get('quantity'):
                return jsonify({'error': 'Product ID and quantity are required for all items'}), 400
            
            product = Product.query.get(item_data['product_id'])
            if not product:
                return jsonify({'error': f'Product with ID {item_data["product_id"]} not found'}), 404
            
            quantity = item_data['quantity']
            
            # Check stock availability
            if product.stock_quantity < quantity:
                return jsonify({'error': f'Insufficient stock for product {product.name}'}), 400
            
            # Use current product price or provided price
            price = item_data.get('price', product.price)
            
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price_at_order=price
            )
            
            db.session.add(order_item)
            
            # Update product stock
            product.stock_quantity -= quantity
            
            total_amount += quantity * price
        
        order.total_amount = total_amount
        db.session.commit()
        
        # Create notification for order creation
        notification = Notification(
            user_id=current_user_id,
            title='طلب جديد تم إنشاؤه',
            message=f'تم إنشاء طلب جديد رقم {order.id} للعميل {customer.name}',
            type='success',
            related_order_id=order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify(order.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders/<int:order_id>', methods=['PUT'])
@jwt_required()
def update_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        # Update basic order info
        order.status = data.get('status', order.status)
        order.notes = data.get('notes', order.notes)
        order.updated_at = datetime.utcnow()
        
        # If items are provided, update them
        if 'items' in data:
            # Remove existing items and restore stock
            for item in order.order_items:
                product = Product.query.get(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
                db.session.delete(item)
            
            total_amount = 0
            
            # Add new items
            for item_data in data['items']:
                product = Product.query.get(item_data['product_id'])
                if not product:
                    return jsonify({'error': f'Product with ID {item_data["product_id"]} not found'}), 404
                
                quantity = item_data['quantity']
                
                # Check stock availability
                if product.stock_quantity < quantity:
                    return jsonify({'error': f'Insufficient stock for product {product.name}'}), 400
                
                price = item_data.get('price', product.price)
                
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price_at_order=price
                )
                
                db.session.add(order_item)
                
                # Update product stock
                product.stock_quantity -= quantity
                
                total_amount += quantity * price
            
            order.total_amount = total_amount
        
        db.session.commit()
        
        return jsonify(order.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders/<int:order_id>', methods=['DELETE'])
@jwt_required()
def delete_order(order_id):
    try:
        order = Order.query.get_or_404(order_id)
        
        # Restore stock for all items
        for item in order.order_items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock_quantity += item.quantity
        
        db.session.delete(order)
        db.session.commit()
        
        return jsonify({'message': 'Order deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders/<int:order_id>/status', methods=['PUT'])
@jwt_required()
def update_order_status(order_id):
    try:
        current_user_id = get_jwt_identity()
        order = Order.query.get_or_404(order_id)
        data = request.get_json()
        
        new_status = data.get('status')
        if not new_status:
            return jsonify({'error': 'Status is required'}), 400
        
        valid_statuses = ['pending', 'processing', 'shipped', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            return jsonify({'error': 'Invalid status'}), 400
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        # If order is cancelled, restore stock
        if new_status == 'cancelled' and old_status != 'cancelled':
            for item in order.order_items:
                product = Product.query.get(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
        
        db.session.commit()
        
        # Create notification for status change
        notification = Notification(
            user_id=current_user_id,
            title='تم تحديث حالة الطلب',
            message=f'تم تحديث حالة الطلب رقم {order.id} من {old_status} إلى {new_status}',
            type='info',
            related_order_id=order.id
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify(order.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@orders_bp.route('/api/orders/stats', methods=['GET'])
@jwt_required()
def get_order_stats():
    try:
        total_orders = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        processing_orders = Order.query.filter_by(status='processing').count()
        completed_orders = Order.query.filter_by(status='completed').count()
        cancelled_orders = Order.query.filter_by(status='cancelled').count()
        
        # Calculate total revenue
        completed_orders_query = Order.query.filter_by(status='completed')
        total_revenue = sum([order.total_amount for order in completed_orders_query if order.total_amount])
        
        return jsonify({
            'total_orders': total_orders,
            'pending_orders': pending_orders,
            'processing_orders': processing_orders,
            'completed_orders': completed_orders,
            'cancelled_orders': cancelled_orders,
            'total_revenue': float(total_revenue) if total_revenue else 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

