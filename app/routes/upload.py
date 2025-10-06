from flask import Blueprint, request, redirect, url_for, flash, render_template, send_from_directory, jsonify
from flask_login import login_required, current_user
from app import extensions
from app.security import validate_image_file, premium_required
from app.config import Config
import os
from datetime import datetime
import mimetypes

bp = Blueprint('upload', __name__)

@bp.route('/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    if not file or file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('upload.editing'))
    if file and validate_image_file(file):
        filename = file.filename
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{ext}"
        save_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)
        file.save(save_path)
        try:
            extensions.db.uploads.insert_one({
                'filename': unique_filename,
                'original_name': filename,
                'path': save_path,
                'uploaded_by': current_user.id,
                'uploaded_at': datetime.utcnow(),
                'size_bytes': os.path.getsize(save_path)
            })
            
            flash('Image uploaded successfully!', 'success')
            # Redirect to editing page with the uploaded filename
            return redirect(url_for('upload.editing', filename=unique_filename))
        except Exception as e:
            flash('Upload failed.', 'error')
    else:
        flash('Invalid file type.', 'error')
    return redirect(url_for('upload.editing'))

@bp.route('/editing', defaults={'filename': None})
@bp.route('/editing/<filename>')
@login_required
def editing(filename):
    return render_template('editing.html', filename=filename)

@bp.route('/my-images')
@login_required
@premium_required
def my_images():
    images = list(extensions.db.processed.find({'created_by': current_user.id}))
    return render_template('my_images.html', images=images)

@bp.route('/uploads/<filename>')
@login_required
def show_uploaded(filename):
    return send_from_directory(Config.UPLOAD_FOLDER, filename)

@bp.route('/processed/<filename>')
@login_required
def show_processed(filename):
    doc = extensions.db.processed.find_one({'processed_filename': filename, 'created_by': current_user.id})
    if not doc:
        flash('Access denied.', 'error')
        return redirect(url_for('upload.my_images'))
    return send_from_directory(Config.PROCESSED_FOLDER, filename)

@bp.route('/download/<filename>')
@login_required
def download_image(filename):
    doc = extensions.db.processed.find_one({'processed_filename': filename, 'created_by': current_user.id})
    if not doc:
        flash('Access denied.', 'error')
        return redirect(url_for('upload.my_images'))
    file_path = os.path.join(Config.PROCESSED_FOLDER, filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('upload.my_images'))
    try:
        file_size = os.path.getsize(file_path)
        file_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        original_name = doc.get('source_filename') or filename
        extensions.db.downloads.insert_one({
            'user_id': str(current_user.id),
            'filename': filename,
            'original_name': original_name,
            'relative_path': 'processed/' + filename,
            'download_timestamp': datetime.utcnow(),
            'file_size': file_size,
            'file_type': file_type
        })
    except Exception as e:
        flash(f'Error tracking download: {e}', 'error')
    return send_from_directory(Config.PROCESSED_FOLDER, filename, as_attachment=True)

@bp.route('/delete-image', methods=['POST'])
@login_required
def delete_image():
    filename = request.form.get('filename')
    if not filename:
        flash('No file specified.', 'error')
        return redirect(url_for('upload.my_images'))
    doc = extensions.db.processed.find_one({'processed_filename': filename, 'created_by': current_user.id})
    if not doc:
        flash('Image not found.', 'error')
        return redirect(url_for('upload.my_images'))
    try:
        if os.path.exists(doc['output_path']):
            os.remove(doc['output_path'])
        extensions.db.processed.delete_one({'_id': doc['_id']})
        flash('Image deleted.', 'success')
    except Exception as e:
        flash(f'Error deleting image: {e}', 'error')
    return redirect(url_for('upload.my_images'))
