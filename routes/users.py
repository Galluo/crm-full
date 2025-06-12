from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import db, User, Task, Notification
from datetime import datetime
import json

users_bp = Blueprint('users', __name__)

@users_bp.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only admins and managers can view all users
        if current_user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        role = request.args.get('role', '')
        
        query = User.query
        
        if search:
            query = query.filter(
                User.full_name.contains(search) |
                User.username.contains(search) |
                User.email.contains(search)
            )
        
        if role:
            query = query.filter_by(role=role)
        
        users = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'users': [user.to_dict() for user in users.items],
            'total': users.total,
            'pages': users.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Users can view their own profile, admins and managers can view all
        if current_user_id != user_id and current_user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        user = User.query.get_or_404(user_id)
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users', methods=['POST'])
@jwt_required()
def create_user():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only admins can create users
        if current_user.role != 'admin':
            return jsonify({'error': 'Only admins can create users'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['username', 'password', 'full_name', 'email']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        if existing_user:
            return jsonify({'error': 'Username or email already exists'}), 400
        
        user = User(
            username=data['username'],
            full_name=data['full_name'],
            email=data['email'],
            role=data.get('role', 'employee'),
            permissions=json.dumps(data.get('permissions', {})) if data.get('permissions') else None,
            is_active=data.get('is_active', True)
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify(user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Users can update their own profile, admins can update all
        if current_user_id != user_id and current_user.role != 'admin':
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        user = User.query.get_or_404(user_id)
        data = request.get_json()
        
        # Check if username or email already exists (excluding current user)
        if data.get('username') and data['username'] != user.username:
            existing_user = User.query.filter_by(username=data['username']).first()
            if existing_user:
                return jsonify({'error': 'Username already exists'}), 400
        
        if data.get('email') and data['email'] != user.email:
            existing_user = User.query.filter_by(email=data['email']).first()
            if existing_user:
                return jsonify({'error': 'Email already exists'}), 400
        
        # Update fields
        user.username = data.get('username', user.username)
        user.full_name = data.get('full_name', user.full_name)
        user.email = data.get('email', user.email)
        
        # Only admins can change role and permissions
        if current_user.role == 'admin':
            user.role = data.get('role', user.role)
            user.permissions = json.dumps(data.get('permissions', {})) if data.get('permissions') else user.permissions
            user.is_active = data.get('is_active', user.is_active)
        
        # Update password if provided
        if data.get('password'):
            user.set_password(data['password'])
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only admins can delete users
        if current_user.role != 'admin':
            return jsonify({'error': 'Only admins can delete users'}), 403
        
        # Cannot delete self
        if current_user_id == user_id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        user = User.query.get_or_404(user_id)
        
        # Check if user has assigned tasks
        if user.assigned_tasks.count() > 0:
            return jsonify({'error': 'Cannot delete user with assigned tasks'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>/assign-task', methods=['POST'])
@jwt_required()
def assign_task_to_user(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only admins and managers can assign tasks
        if current_user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Only admins and managers can assign tasks'}), 403
        
        data = request.get_json()
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'error': 'task_id is required'}), 400
        
        user = User.query.get_or_404(user_id)
        task = Task.query.get_or_404(task_id)
        
        # Assign task to user
        task.assigned_to = user_id
        task.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create notification for assigned user
        notification = Notification(
            user_id=user_id,
            title='مهمة جديدة تم إسنادها إليك',
            message=f'تم إسناد المهمة "{task.title}" إليك من قبل {current_user.full_name}',
            type='info',
            related_task_id=task_id
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({
            'message': 'Task assigned successfully',
            'task': task.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/<int:user_id>/tasks', methods=['GET'])
@jwt_required()
def get_user_tasks(user_id):
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Users can view their own tasks, admins and managers can view all
        if current_user_id != user_id and current_user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        user = User.query.get_or_404(user_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status', '')
        
        query = user.assigned_tasks
        
        if status:
            query = query.filter_by(status=status)
        
        tasks = query.order_by(Task.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'tasks': [task.to_dict() for task in tasks.items],
            'total': tasks.total,
            'pages': tasks.pages,
            'current_page': page,
            'user': user.to_dict()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/roles', methods=['GET'])
@jwt_required()
def get_roles():
    try:
        roles = [
            {'value': 'admin', 'label': 'مدير النظام'},
            {'value': 'manager', 'label': 'مدير'},
            {'value': 'sales', 'label': 'موظف مبيعات'},
            {'value': 'support', 'label': 'دعم فني'},
            {'value': 'employee', 'label': 'موظف'}
        ]
        
        return jsonify({'roles': roles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/api/users/employees', methods=['GET'])
@jwt_required()
def get_employees():
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Only admins and managers can view employees list
        if current_user.role not in ['admin', 'manager']:
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        employees = User.query.filter(
            User.is_active == True,
            User.role.in_(['employee', 'sales', 'support'])
        ).all()
        
        return jsonify({
            'employees': [
                {
                    'id': emp.id,
                    'full_name': emp.full_name,
                    'role': emp.role,
                    'email': emp.email,
                    'assigned_tasks_count': emp.assigned_tasks.count()
                } for emp in employees
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

