# LIMS Routes - مسارات التطبيق
# Flask Routes for LIMS Module

from flask import Flask

from .auth import auth_bp
from .samples import samples_bp
from .results import results_bp
from .reports import reports_bp
from .dashboard import dashboard_bp

def register_blueprints(app: Flask):
    """تسجيل جميع المسارات في التطبيق"""
    
    # Register authentication routes
    app.register_blueprint(auth_bp)
    
    # Register main application routes
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(samples_bp)
    app.register_blueprint(results_bp)
    app.register_blueprint(reports_bp)
    
    # Add main route redirects
    @app.route('/')
    def index():
        """الصفحة الرئيسية - إعادة توجيه إلى لوحة التحكم"""
        from flask import redirect, url_for
        from flask_login import current_user
        
        if current_user.is_authenticated:
            return redirect(url_for('dashboard.index'))
        else:
            return redirect(url_for('auth.login'))
    
    @app.route('/health')
    def health_check():
        """فحص صحة النظام"""
        from flask import jsonify
        from datetime import datetime
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0',
            'service': 'Jawdati LIMS'
        })

__all__ = [
    'auth_bp',
    'samples_bp', 
    'results_bp',
    'reports_bp',
    'dashboard_bp',
    'register_blueprints'
]