from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import db, ChatMessage, ChatGroup, ChatGroupMember, User
from datetime import datetime

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/api/chat/messages', methods=['GET'])
@jwt_required()
def get_messages():
    try:
        current_user_id = get_jwt_identity()
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        chat_type = request.args.get('type', 'direct')  # direct or group
        chat_id = request.args.get('chat_id', type=int)
        
        if chat_type == 'direct':
            # Direct messages between two users
            if not chat_id:
                return jsonify({'error': 'chat_id (other user ID) is required for direct messages'}), 400
            
            messages = ChatMessage.query.filter(
                ((ChatMessage.sender_id == current_user_id) & (ChatMessage.receiver_id == chat_id)) |
                ((ChatMessage.sender_id == chat_id) & (ChatMessage.receiver_id == current_user_id))
            ).order_by(ChatMessage.timestamp.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
        else:
            # Group messages
            if not chat_id:
                return jsonify({'error': 'chat_id (group ID) is required for group messages'}), 400
            
            # Check if user is member of the group
            membership = ChatGroupMember.query.filter_by(
                group_id=chat_id, user_id=current_user_id
            ).first()
            if not membership:
                return jsonify({'error': 'You are not a member of this group'}), 403
            
            messages = ChatMessage.query.filter_by(group_id=chat_id).order_by(
                ChatMessage.timestamp.desc()
            ).paginate(
                page=page, per_page=per_page, error_out=False
            )
        
        return jsonify({
            'messages': [message.to_dict() for message in messages.items],
            'total': messages.total,
            'pages': messages.pages,
            'current_page': page
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/messages', methods=['POST'])
@jwt_required()
def send_message():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        message_text = data.get('message_text', '').strip()
        if not message_text:
            return jsonify({'error': 'Message text is required'}), 400
        
        chat_type = data.get('type', 'direct')
        
        if chat_type == 'direct':
            receiver_id = data.get('receiver_id')
            if not receiver_id:
                return jsonify({'error': 'receiver_id is required for direct messages'}), 400
            
            # Check if receiver exists
            receiver = User.query.get(receiver_id)
            if not receiver:
                return jsonify({'error': 'Receiver not found'}), 404
            
            message = ChatMessage(
                sender_id=current_user_id,
                receiver_id=receiver_id,
                message_text=message_text
            )
        else:
            group_id = data.get('group_id')
            if not group_id:
                return jsonify({'error': 'group_id is required for group messages'}), 400
            
            # Check if user is member of the group
            membership = ChatGroupMember.query.filter_by(
                group_id=group_id, user_id=current_user_id
            ).first()
            if not membership:
                return jsonify({'error': 'You are not a member of this group'}), 403
            
            message = ChatMessage(
                sender_id=current_user_id,
                group_id=group_id,
                message_text=message_text
            )
        
        db.session.add(message)
        db.session.commit()
        
        return jsonify(message.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/conversations', methods=['GET'])
@jwt_required()
def get_conversations():
    try:
        current_user_id = get_jwt_identity()
        
        # Get direct conversations (users who have exchanged messages)
        direct_conversations = db.session.query(
            ChatMessage.sender_id,
            ChatMessage.receiver_id
        ).filter(
            (ChatMessage.sender_id == current_user_id) | 
            (ChatMessage.receiver_id == current_user_id)
        ).filter(
            ChatMessage.receiver_id.isnot(None)
        ).distinct().all()
        
        # Process direct conversations
        user_ids = set()
        for conv in direct_conversations:
            if conv.sender_id != current_user_id:
                user_ids.add(conv.sender_id)
            if conv.receiver_id != current_user_id:
                user_ids.add(conv.receiver_id)
        
        direct_users = User.query.filter(User.id.in_(user_ids)).all() if user_ids else []
        
        # Get group conversations
        group_memberships = ChatGroupMember.query.filter_by(user_id=current_user_id).all()
        groups = [membership.group for membership in group_memberships]
        
        return jsonify({
            'direct_conversations': [
                {
                    'user_id': user.id,
                    'user_name': user.full_name,
                    'user_role': user.role
                } for user in direct_users
            ],
            'group_conversations': [group.to_dict() for group in groups]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/groups', methods=['GET'])
@jwt_required()
def get_groups():
    try:
        current_user_id = get_jwt_identity()
        
        # Get groups where user is a member
        memberships = ChatGroupMember.query.filter_by(user_id=current_user_id).all()
        groups = [membership.group for membership in memberships]
        
        return jsonify({
            'groups': [group.to_dict() for group in groups]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/groups', methods=['POST'])
@jwt_required()
def create_group():
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Group name is required'}), 400
        
        group = ChatGroup(
            name=name,
            description=data.get('description', ''),
            created_by=current_user_id
        )
        
        db.session.add(group)
        db.session.flush()  # Get group ID
        
        # Add creator as member
        membership = ChatGroupMember(
            group_id=group.id,
            user_id=current_user_id
        )
        db.session.add(membership)
        
        # Add other members if provided
        member_ids = data.get('member_ids', [])
        for member_id in member_ids:
            if member_id != current_user_id:  # Don't add creator twice
                user = User.query.get(member_id)
                if user:
                    membership = ChatGroupMember(
                        group_id=group.id,
                        user_id=member_id
                    )
                    db.session.add(membership)
        
        db.session.commit()
        
        return jsonify(group.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/groups/<int:group_id>/members', methods=['GET'])
@jwt_required()
def get_group_members(group_id):
    try:
        current_user_id = get_jwt_identity()
        
        # Check if user is member of the group
        membership = ChatGroupMember.query.filter_by(
            group_id=group_id, user_id=current_user_id
        ).first()
        if not membership:
            return jsonify({'error': 'You are not a member of this group'}), 403
        
        members = ChatGroupMember.query.filter_by(group_id=group_id).all()
        
        return jsonify({
            'members': [member.to_dict() for member in members]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/groups/<int:group_id>/members', methods=['POST'])
@jwt_required()
def add_group_member(group_id):
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Check if user is member of the group (only members can add others)
        membership = ChatGroupMember.query.filter_by(
            group_id=group_id, user_id=current_user_id
        ).first()
        if not membership:
            return jsonify({'error': 'You are not a member of this group'}), 403
        
        user_id = data.get('user_id')
        if not user_id:
            return jsonify({'error': 'user_id is required'}), 400
        
        # Check if user exists
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user is already a member
        existing_membership = ChatGroupMember.query.filter_by(
            group_id=group_id, user_id=user_id
        ).first()
        if existing_membership:
            return jsonify({'error': 'User is already a member of this group'}), 400
        
        new_membership = ChatGroupMember(
            group_id=group_id,
            user_id=user_id
        )
        
        db.session.add(new_membership)
        db.session.commit()
        
        return jsonify(new_membership.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/users', methods=['GET'])
@jwt_required()
def get_chat_users():
    try:
        current_user_id = get_jwt_identity()
        
        # Get all active users except current user
        users = User.query.filter(
            User.id != current_user_id,
            User.is_active == True
        ).all()
        
        return jsonify({
            'users': [
                {
                    'id': user.id,
                    'full_name': user.full_name,
                    'role': user.role,
                    'email': user.email
                } for user in users
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@chat_bp.route('/api/chat/messages/<int:message_id>/read', methods=['PUT'])
@jwt_required()
def mark_message_read(message_id):
    try:
        current_user_id = get_jwt_identity()
        message = ChatMessage.query.get_or_404(message_id)
        
        # Only receiver can mark message as read
        if message.receiver_id != current_user_id:
            return jsonify({'error': 'You can only mark your own messages as read'}), 403
        
        message.is_read = True
        db.session.commit()
        
        return jsonify({'message': 'Message marked as read'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

