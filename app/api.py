from flask import Blueprint, jsonify, request, send_from_directory, g
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from app.models import User, Application, ApkVersion, Category, VersionFlag, OneTimeDownloadLink
from app import db
from config import Config
import os
from datetime import datetime
from functools import wraps

api = Blueprint('api', __name__, url_prefix='/api/v1')
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        g.current_user = user
        return user
    return None

@auth.error_handler
def auth_error():
    return jsonify({
        'error': 'Unauthorized',
        'message': 'Invalid credentials'
    }), 401

def paginate(query, schema=None):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    items = pagination.items
    if schema:
        items = [schema(item) for item in items]
    
    return {
        'items': items,
        'total': pagination.total,
        'page': page,
        'pages': pagination.pages
    }

def serialize_application(app):
    latest_version = app.get_latest_release()
    latest_version_data = None
    if latest_version:
        latest_version_data = {
            'version_number': latest_version.version_number,
            'branch': latest_version.branch,
            'is_stable': latest_version.is_stable
        }
    
    return {
        'id': app.id,
        'package_name': app.package_name,
        'name': app.name,
        'description': app.description,
        'category_id': app.category_id,
        'category_name': app.category.name,
        'latest_version': latest_version_data
    }

def serialize_version(version):
    return {
        'id': version.id,
        'version_number': version.version_number,
        'branch': version.branch,
        'upload_date': version.upload_date.isoformat(),
        'file_size': version.file_size,
        'downloads': version.downloads,
        'is_stable': version.is_stable,
        'changelog': version.changelog
    }

@api.route('/applications')
@auth.login_required
def get_applications():
    query = Application.query
    
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    return jsonify(paginate(query, serialize_application))

@api.route('/applications/<int:id>')
@auth.login_required
def get_application(id):
    app = Application.query.get_or_404(id)
    data = serialize_application(app)
    data['versions'] = [serialize_version(v) for v in app.versions]
    return jsonify(data)

@api.route('/applications', methods=['POST'])
@auth.login_required
def create_application():
    data = request.get_json()
    
    if not all(k in data for k in ('package_name', 'name', 'category_id')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if Application.query.filter_by(package_name=data['package_name']).first():
        return jsonify({'error': 'Application with this package name already exists'}), 409
    
    app = Application(
        package_name=data['package_name'],
        name=data['name'],
        description=data.get('description', ''),
        category_id=data['category_id']
    )
    
    try:
        db.session.add(app)
        db.session.commit()
        return jsonify(serialize_application(app)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/applications/<int:id>/versions')
@auth.login_required
def get_versions(id):
    app = Application.query.get_or_404(id)
    query = ApkVersion.query.filter_by(application_id=id)
    
    branch = request.args.get('branch')
    if branch:
        query = query.filter_by(branch=branch)
    
    is_stable = request.args.get('is_stable', type=bool)
    if is_stable is not None:
        query = query.filter_by(is_stable=is_stable)
    
    return jsonify(paginate(query, serialize_version))

@api.route('/applications/<int:id>/versions', methods=['POST'])
@auth.login_required
def upload_version(id):
    app = Application.query.get_or_404(id)
    
    if 'apk_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['apk_file']
    if not file:
        return jsonify({'error': 'Empty file'}), 400
    
    filename = secure_filename(file.filename)
    package_name, version_number, branch = ApkVersion.parse_filename(filename)
    
    if not package_name or package_name != app.package_name:
        return jsonify({'error': 'Invalid filename format'}), 400
    
    if ApkVersion.query.filter_by(
        application_id=id,
        version_number=version_number,
        branch=branch
    ).first():
        return jsonify({'error': 'Version already exists'}), 409
    
    try:
        if not os.path.exists(Config.UPLOAD_FOLDER):
            os.makedirs(Config.UPLOAD_FOLDER)
        
        file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        version = ApkVersion(
            application_id=id,
            version_number=version_number,
            branch=branch,
            filename=filename,
            file_size=os.path.getsize(file_path),
            changelog=request.form.get('changelog', ''),
            is_stable=request.form.get('is_stable', 'false').lower() == 'true',
            uploader=g.current_user
        )
        
        db.session.add(version)
        db.session.commit()
        
        return jsonify(serialize_version(version)), 201
        
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/versions/<int:id>', methods=['PATCH'])
@auth.login_required
def update_version(id):
    version = ApkVersion.query.get_or_404(id)
    data = request.get_json()
    
    if 'changelog' in data:
        version.changelog = data['changelog']
    if 'is_stable' in data:
        version.is_stable = data['is_stable']
    if 'branch' in data:
        if data['branch'] not in ['release', 'debug', 'beta', 'alpha']:
            return jsonify({'error': 'Invalid branch value'}), 400
        version.branch = data['branch']
    
    try:
        db.session.commit()
        return jsonify(serialize_version(version))
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@api.route('/versions/<int:id>/download')
@auth.login_required
def download_version(id):
    version = ApkVersion.query.get_or_404(id)
    file_path = os.path.join(Config.UPLOAD_FOLDER, version.filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    version.downloads += 1
    db.session.commit()
    
    return send_from_directory(Config.UPLOAD_FOLDER, version.filename, as_attachment=True)

@api.route('/versions/<int:id>/generate-link', methods=['POST'])
@auth.login_required
def generate_download_link(id):
    version = ApkVersion.query.get_or_404(id)
    link = OneTimeDownloadLink.create_for_version(version, g.current_user)
    
    return jsonify({
        'download_url': f"{Config.HOST_URL}/api/v1/download/{link.token}",
        'expires_at': link.expires_at.isoformat()
    })

@api.route('/download/<token>')
def download_by_link(token):
    link = OneTimeDownloadLink.query.filter_by(token=token).first_or_404()
    
    if not link.is_valid():
        return jsonify({
            'error': 'Link expired or already used'
        }), 400
    
    file_path = os.path.join(Config.UPLOAD_FOLDER, link.version.filename)
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    link.mark_as_used(request.remote_addr)
    link.version.downloads += 1
    db.session.commit()
    
    return send_from_directory(Config.UPLOAD_FOLDER, link.version.filename, as_attachment=True)

@api.route('/categories')
@auth.login_required
def get_categories():
    categories = Category.query.all()
    return jsonify({
        'items': [{
            'id': c.id,
            'name': c.name,
            'description': c.description,
            'applications_count': len(c.applications)
        } for c in categories]
    })

@api.route('/versions/<int:id>/flags', methods=['POST'])
@auth.login_required
def add_flag(id):
    version = ApkVersion.query.get_or_404(id)
    data = request.get_json()
    
    if not all(k in data for k in ('flag_type', 'description')):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if data['flag_type'] not in ['bug', 'feature', 'warning']:
        return jsonify({'error': 'Invalid flag type'}), 400
    
    flag = VersionFlag(
        version_id=version.id,
        flag_type=data['flag_type'],
        description=data['description'],
        created_by=g.current_user
    )
    
    try:
        db.session.add(flag)
        db.session.commit()
        
        return jsonify({
            'id': flag.id,
            'flag_type': flag.flag_type,
            'description': flag.description,
            'created_date': flag.created_date.isoformat(),
            'created_by': flag.created_by.username
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400 