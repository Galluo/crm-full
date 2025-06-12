from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import Setting, User, db

settings_bp = Blueprint('settings', __name__)

def require_admin():
    """Helper function to check if current user is admin"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    return user and user.role == 'admin'

@settings_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    """Get all settings"""
    try:
        settings = Setting.query.all()
        settings_dict = {}
        
        for setting in settings:
            settings_dict[setting.key] = {
                'value': setting.value,
                'description': setting.description
            }
        
        return jsonify(settings_dict), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch settings', 'details': str(e)}), 500

@settings_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    """Update settings (admin only)"""
    try:
        if not require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updated_settings = []
        
        for key, value in data.items():
            setting = Setting.query.filter_by(key=key).first()
            
            if setting:
                setting.value = str(value) if value is not None else None
            else:
                setting = Setting(key=key, value=str(value) if value is not None else None)
                db.session.add(setting)
            
            updated_settings.append(key)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Settings updated successfully',
            'updated_settings': updated_settings
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update settings', 'details': str(e)}), 500

@settings_bp.route('/settings/<string:key>', methods=['GET'])
@jwt_required()
def get_setting(key):
    """Get specific setting"""
    try:
        setting = Setting.query.filter_by(key=key).first()
        
        if not setting:
            return jsonify({'error': 'Setting not found'}), 404
        
        return jsonify({
            'key': setting.key,
            'value': setting.value,
            'description': setting.description
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch setting', 'details': str(e)}), 500

@settings_bp.route('/settings/<string:key>', methods=['PUT'])
@jwt_required()
def update_setting(key):
    """Update specific setting (admin only)"""
    try:
        if not require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({'error': 'Value is required'}), 400
        
        setting = Setting.query.filter_by(key=key).first()
        
        if setting:
            setting.value = str(data['value']) if data['value'] is not None else None
            if 'description' in data:
                setting.description = data['description']
        else:
            setting = Setting(
                key=key,
                value=str(data['value']) if data['value'] is not None else None,
                description=data.get('description')
            )
            db.session.add(setting)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Setting updated successfully',
            'setting': setting.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update setting', 'details': str(e)}), 500

@settings_bp.route('/settings/<string:key>', methods=['DELETE'])
@jwt_required()
def delete_setting(key):
    """Delete specific setting (admin only)"""
    try:
        if not require_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        setting = Setting.query.filter_by(key=key).first_or_404()
        
        db.session.delete(setting)
        db.session.commit()
        
        return jsonify({'message': 'Setting deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete setting', 'details': str(e)}), 500

