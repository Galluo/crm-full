import os
import sys
# DON'T CHANGE THIS PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models.user import db
from routes.auth import auth_bp
from routes.users import users_bp
from routes.customers import customers_bp
from routes.products import products_bp
from routes.orders import orders_bp
from routes.tasks import tasks_bp
from routes.notifications import notifications_bp
from routes.reports import reports_bp
from routes.settings import settings_bp
from routes.chat import chat_bp

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///crm.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'jwt-secret-string-change-in-production'

# Initialize extensions
db.init_app(app)
jwt = JWTManager(app)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(users_bp)
app.register_blueprint(customers_bp)
app.register_blueprint(products_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(notifications_bp)
app.register_blueprint(reports_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(chat_bp)

# Serve static files
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

# Create tables and default data
with app.app_context():
    db.create_all()
    
    # Create default admin user if not exists
    from models.user import User, Setting
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            full_name='System Administrator',
            email='admin@crm.com',
            role='admin',
            is_active=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
    
    # Create default settings if not exist
    default_settings = [
        {'key': 'company_name', 'value': 'شركة إدارة علاقات العملاء', 'description': 'اسم الشركة'},
        {'key': 'language', 'value': 'ar', 'description': 'اللغة الافتراضية'},
        {'key': 'theme', 'value': 'light', 'description': 'السمة الافتراضية'},
        {'key': 'currency', 'value': 'SAR', 'description': 'العملة الافتراضية'},
        {'key': 'low_stock_threshold', 'value': '10', 'description': 'حد تنبيه المخزون المنخفض'}
    ]
    
    for setting_data in default_settings:
        existing_setting = Setting.query.filter_by(key=setting_data['key']).first()
        if not existing_setting:
            setting = Setting(**setting_data)
            db.session.add(setting)
    
    db.session.commit()
