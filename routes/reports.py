from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import Task, User, Notification, db
from datetime import datetime, date, timedelta
import csv
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports/tasks-summary', methods=['GET'])
@jwt_required()
def get_tasks_summary_report():
    """Generate tasks summary report"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build base query
        query = Task.query
        
        # Non-admin users can only see their own tasks
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Apply date filters if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Task.created_at >= start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Task.created_at <= end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        tasks = query.all()
        
        # Generate report data
        report_data = []
        for task in tasks:
            report_data.append({
                'id': task.id,
                'title': task.title,
                'status': task.status,
                'priority': task.priority,
                'assigned_to': task.assignee.full_name if task.assignee else 'Unassigned',
                'created_by': task.creator.full_name if task.creator else 'Unknown',
                'due_date': task.due_date.isoformat() if task.due_date else '',
                'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
                'updated_at': task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if task.updated_at else ''
            })
        
        return jsonify({
            'report_type': 'tasks_summary',
            'generated_at': datetime.utcnow().isoformat(),
            'total_tasks': len(report_data),
            'data': report_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to generate tasks summary report', 'details': str(e)}), 500

@reports_bp.route('/reports/tasks-summary/csv', methods=['GET'])
@jwt_required()
def export_tasks_summary_csv():
    """Export tasks summary as CSV"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build base query
        query = Task.query
        
        # Non-admin users can only see their own tasks
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Apply date filters if provided
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Task.created_at >= start_date)
            except ValueError:
                return jsonify({'error': 'Invalid start_date format. Use YYYY-MM-DD'}), 400
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Task.created_at <= end_date)
            except ValueError:
                return jsonify({'error': 'Invalid end_date format. Use YYYY-MM-DD'}), 400
        
        tasks = query.all()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Title', 'Description', 'Status', 'Priority', 
            'Assigned To', 'Created By', 'Due Date', 'Created At', 'Updated At'
        ])
        
        # Write data
        for task in tasks:
            writer.writerow([
                task.id,
                task.title,
                task.description or '',
                task.status,
                task.priority,
                task.assignee.full_name if task.assignee else 'Unassigned',
                task.creator.full_name if task.creator else 'Unknown',
                task.due_date.isoformat() if task.due_date else '',
                task.created_at.strftime('%Y-%m-%d %H:%M:%S') if task.created_at else '',
                task.updated_at.strftime('%Y-%m-%d %H:%M:%S') if task.updated_at else ''
            ])
        
        # Create response
        output.seek(0)
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=tasks_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': 'Failed to export CSV', 'details': str(e)}), 500

@reports_bp.route('/stats/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build base query
        query = Task.query
        
        # Non-admin users can only see their own tasks
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Calculate statistics
        total_tasks = query.count()
        completed_tasks = query.filter(Task.status == 'completed').count()
        pending_tasks = query.filter(Task.status == 'pending').count()
        in_progress_tasks = query.filter(Task.status == 'in_progress').count()
        on_hold_tasks = query.filter(Task.status == 'on_hold').count()
        
        # Tasks due this week
        today = date.today()
        week_end = today + timedelta(days=7)
        tasks_due_this_week = query.filter(
            Task.due_date.between(today, week_end)
        ).count()
        
        # Overdue tasks
        overdue_tasks = query.filter(
            Task.due_date < today,
            Task.status != 'completed'
        ).count()
        
        # Priority statistics
        high_priority_tasks = query.filter(Task.priority == 'high').count()
        urgent_priority_tasks = query.filter(Task.priority == 'urgent').count()
        
        return jsonify({
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'on_hold_tasks': on_hold_tasks,
            'tasks_due_this_week': tasks_due_this_week,
            'overdue_tasks': overdue_tasks,
            'high_priority_tasks': high_priority_tasks,
            'urgent_priority_tasks': urgent_priority_tasks,
            'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 2)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get dashboard statistics', 'details': str(e)}), 500

@reports_bp.route('/stats/tasks-by-status', methods=['GET'])
@jwt_required()
def get_tasks_by_status():
    """Get tasks grouped by status"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build base query
        query = Task.query
        
        # Non-admin users can only see their own tasks
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Group by status
        status_counts = {}
        statuses = ['pending', 'in_progress', 'completed', 'on_hold']
        
        for status in statuses:
            count = query.filter(Task.status == status).count()
            status_counts[status] = count
        
        return jsonify(status_counts), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get tasks by status', 'details': str(e)}), 500

@reports_bp.route('/stats/tasks-by-priority', methods=['GET'])
@jwt_required()
def get_tasks_by_priority():
    """Get tasks grouped by priority"""
    try:
        current_user_id = get_jwt_identity()
        current_user = User.query.get(current_user_id)
        
        # Build base query
        query = Task.query
        
        # Non-admin users can only see their own tasks
        if current_user.role != 'admin':
            query = query.filter(
                (Task.assigned_to == current_user_id) | 
                (Task.created_by == current_user_id)
            )
        
        # Group by priority
        priority_counts = {}
        priorities = ['low', 'medium', 'high', 'urgent']
        
        for priority in priorities:
            count = query.filter(Task.priority == priority).count()
            priority_counts[priority] = count
        
        return jsonify(priority_counts), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get tasks by priority', 'details': str(e)}), 500

