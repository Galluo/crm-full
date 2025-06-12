from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import Notification, db

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/notifications', methods=['GET'])
@jwt_required()
def get_notifications():
    """Get notifications for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        # Get query parameters
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = request.args.get('limit', type=int)
        
        # Build query
        query = Notification.query.filter_by(user_id=current_user_id)
        
        if unread_only:
            query = query.filter_by(is_read=False)
        
        # Order by created_at desc
        query = query.order_by(Notification.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        notifications = query.all()
        
        return jsonify([notification.to_dict() for notification in notifications]), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch notifications', 'details': str(e)}), 500

@notifications_bp.route('/notifications/count', methods=['GET'])
@jwt_required()
def get_notification_count():
    """Get unread notification count for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        count = Notification.query.filter_by(
            user_id=current_user_id, 
            is_read=False
        ).count()
        
        return jsonify({'count': count}), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get notification count', 'details': str(e)}), 500

@notifications_bp.route('/notifications/<int:notification_id>/read', methods=['PUT'])
@jwt_required()
def mark_notification_read(notification_id):
    """Mark notification as read"""
    try:
        current_user_id = get_jwt_identity()
        
        notification = Notification.query.filter_by(
            id=notification_id, 
            user_id=current_user_id
        ).first_or_404()
        
        notification.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Notification marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark notification as read', 'details': str(e)}), 500

@notifications_bp.route('/notifications/mark-all-read', methods=['PUT'])
@jwt_required()
def mark_all_notifications_read():
    """Mark all notifications as read for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        Notification.query.filter_by(
            user_id=current_user_id, 
            is_read=False
        ).update({'is_read': True})
        
        db.session.commit()
        
        return jsonify({'message': 'All notifications marked as read'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to mark all notifications as read', 'details': str(e)}), 500

@notifications_bp.route('/notifications/read', methods=['DELETE'])
@jwt_required()
def delete_read_notifications():
    """Delete all read notifications for current user"""
    try:
        current_user_id = get_jwt_identity()
        
        deleted_count = Notification.query.filter_by(
            user_id=current_user_id, 
            is_read=True
        ).delete()
        
        db.session.commit()
        
        return jsonify({
            'message': f'Deleted {deleted_count} read notifications'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete read notifications', 'details': str(e)}), 500

