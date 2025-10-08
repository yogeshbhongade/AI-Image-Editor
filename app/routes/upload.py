from flask import Blueprint, request, redirect, url_for, flash, render_template, send_from_directory, jsonify, current_app
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
    # Accept JSON or form data
    data = request.get_json(silent=True) or request.form
    image_id = data.get('image_id') or data.get('_id') or data.get('id')
    filename = data.get('filename')

    # Resolve: image_id preferred (it's the DB _id), fallback to filename
    doc = None
    if image_id:
        try:
            from bson import ObjectId
            doc = extensions.db.processed.find_one({'_id': ObjectId(image_id), 'created_by': current_user.id})
        except Exception:
            doc = None
    elif filename:
        doc = extensions.db.processed.find_one({'processed_filename': filename, 'created_by': current_user.id})

    if not doc:
        flash('Image not found or access denied.', 'error')
        return redirect(url_for('upload.my_images'))

    # Helper to safely remove file
    def _safe_remove(path):
        try:
            if not path:
                return
            if not os.path.isabs(path):
                path = os.path.join(Config.PROCESSED_FOLDER, path) if os.path.basename(path) == path else path
            if os.path.exists(path):
                os.remove(path)
                current_app.logger.info("Deleted file %s", path)
        except Exception as e:
            current_app.logger.exception("Failed removing file %s: %s", path, e)

    # Remove processed file
    _safe_remove(doc.get('output_path') or os.path.join(Config.PROCESSED_FOLDER, doc.get('processed_filename')))

    # Optionally remove any associated 'uploads' record and file
    try:
        if 'source_upload_id' in doc:
            from bson import ObjectId
            up = extensions.db.uploads.find_one({'_id': ObjectId(doc['source_upload_id'])})
            if up:
                _safe_remove(up.get('path') or os.path.join(Config.UPLOAD_FOLDER, up.get('filename')))
                extensions.db.uploads.delete_one({'_id': up['_id']})
    except Exception:
        current_app.logger.exception("Failed removing source upload for %s", doc.get('_id'))

    # Remove processed DB doc
    extensions.db.processed.delete_one({'_id': doc['_id']})
    flash('Image and associated files deleted.', 'success')
    return redirect(url_for('upload.my_images'))

