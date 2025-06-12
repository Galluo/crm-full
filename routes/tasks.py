from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import Task, User, db
from datetime import datetime, date

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/tasks', methods=['GET'])
@jwt_required()
def get_tasks():
    """Get tasks with optional filtering"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build query
        query = Task.query
        
        # Non-admin users can only see their own tasks (assigned or created)
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Apply filters
        status = request.args.get('status')
        if status:
            query = query.filter(Task.status == status)
        
        priority = request.args.get('priority')
        if priority:
            query = query.filter(Task.priority == priority)
        
        assigned_to = request.args.get('assigned_to')
        if assigned_to:
            query = query.filter(Task.assigned_to == assigned_to)
        
        search = request.args.get('search')
        if search:
            query = query.filter(
                (Task.title.contains(search)) | 
                (Task.description.contains(search))
            )
        
        # Order by created_at desc
        tasks = query.order_by(Task.created_at.desc()).all()
        
        return jsonify([task.to_dict() for task in tasks]), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch tasks', 'details': str(e)}), 500

@tasks_bp.route('/tasks', methods=['POST'])
@jwt_required()
def create_task():
    """Create new task"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        # Parse due_date if provided
        due_date = None
        if data.get('due_date'):
            try:
                due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        task = Task(
            title=data['title'],
            description=data.get('description', ''),
            assigned_to=data.get('assigned_to'),
            created_by=current_user_id,
            status=data.get('status', 'pending'),
            priority=data.get('priority', 'medium'),
            due_date=due_date
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Create notification for assigned user if different from creator
        if task.assigned_to and task.assigned_to != current_user_id:
            from models.user import Notification
            notification = Notification(
                user_id=task.assigned_to,
                title='New Task Assigned',
                message=f'You have been assigned a new task: {task.title}',
                type='task_assigned',
                related_task_id=task.id
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify(task.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create task', 'details': str(e)}), 500

@tasks_bp.route('/tasks/<int:task_id>', methods=['GET'])
@jwt_required()
def get_task(task_id):
    """Get specific task"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        task = Task.query.get_or_404(task_id)
        
        # Check access permissions
        if (current_user.role != 'admin' and 
            task.assigned_to != current_user_id and 
            task.created_by != current_user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch task', 'details': str(e)}), 500

@tasks_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    """Update task"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        task = Task.query.get_or_404(task_id)
        
        # Check access permissions
        if (current_user.role != 'admin' and 
            task.assigned_to != current_user_id and 
            task.created_by != current_user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update fields
        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'status' in data:
            task.status = data['status']
        if 'priority' in data:
            task.priority = data['priority']
        
        # Only admins and creators can reassign tasks
        if 'assigned_to' in data and (current_user.role == 'admin' or task.created_by == current_user_id):
            old_assigned_to = task.assigned_to
            task.assigned_to = data['assigned_to']
            
            # Create notification for newly assigned user
            if (task.assigned_to and task.assigned_to != old_assigned_to and 
                task.assigned_to != current_user_id):
                from models.user import Notification
                notification = Notification(
                    user_id=task.assigned_to,
                    title='Task Reassigned',
                    message=f'You have been assigned to task: {task.title}',
                    type='task_assigned',
                    related_task_id=task.id
                )
                db.session.add(notification)
        
        # Parse due_date if provided
        if 'due_date' in data:
            if data['due_date']:
                try:
                    task.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
            else:
                task.due_date = None
        
        db.session.commit()
        return jsonify(task.to_dict()), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update task', 'details': str(e)}), 500

@tasks_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    """Delete task"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        task = Task.query.get_or_404(task_id)
        
        # Only admins and creators can delete tasks
        if current_user.role != 'admin' and task.created_by != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(task)
        db.session.commit()
        
        return jsonify({'message': 'Task deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete task', 'details': str(e)}), 500

