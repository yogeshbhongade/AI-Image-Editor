from flask import Blueprint, request, jsonify, abort, url_for
from flask_login import login_required, current_user
from app import extensions
from app.security import is_ajax_request, premium_required
from rq.job import Job
from rq.exceptions import NoSuchJobError

bp = Blueprint('edit_async', __name__)

@bp.route('/edit-task/<operation>/<filename>', methods=['POST'])
@login_required
def enqueue_edit_task(operation, filename):
    data = request.form if request.form else request.get_json(force=True)
    processed = data.get('processed')
    value = data.get('value')
    width = data.get('width', type=int)
    height = data.get('height', type=int)
    session_id = data.get('session_id')
    sequence = data.get('sequence')
    edit_status = data.get('edit_status', 'temporary')
    from tasks import process_image_task
    # Determine if operation requires premium
    requires_premium = operation in {'emboss','edges','enhance','batch','bulk_download'}
    queue_to_use = extensions.premium_queue if requires_premium else extensions.queue
    job = queue_to_use.enqueue(
        process_image_task,
        user_id=current_user.id,
        operation=operation,
        filename=filename,
        edit_status=edit_status,
        processed=processed,
        value=value,
        width=width,
        height=height,
        session_id=session_id,
        sequence=sequence,
    )
    return jsonify({'success': True, 'job_id': job.get_id()})

@bp.route('/ai-edit-task/<filename>', methods=['POST'])
@login_required
def enqueue_ai_edit_task(filename):
    data = request.form if request.form else request.get_json(force=True)
    prompt = data.get('prompt')
    processed = data.get('processed')
    strength = float(data.get('strength', 0.75))
    steps = int(data.get('steps', 30))
    session_id = data.get('session_id')
    sequence = data.get('sequence')
    edit_status = data.get('edit_status', 'temporary')
    if not prompt:
        return jsonify({'success': False, 'error': 'Prompt required'}), 400
    from tasks import process_ai_edit_task
    # AI operations could be premium features
    queue_to_use = extensions.premium_queue
    job = queue_to_use.enqueue(
        process_ai_edit_task,
        user_id=current_user.id,
        prompt=prompt,
        filename=filename,
        processed=processed,
        strength=strength,
        steps=steps,
        session_id=session_id,
        sequence=sequence,
        edit_status=edit_status,
    )
    return jsonify({'success': True, 'job_id': job.get_id()})

@bp.route('/job-status/<job_id>')
@login_required
def job_status(job_id):
    try:
        job = Job.fetch(job_id, connection=extensions.queue.connection)
    except NoSuchJobError:
        return jsonify({'success': False, 'status': 'not_found'}), 404
    status = job.get_status()
    response = {'success': True, 'status': status}
    if status == 'finished':
        result = job.result
        if isinstance(result, dict) and 'processed_filename' in result:
            response['result'] = result
            response['processed_filename'] = result['processed_filename']
        else:
            response['result'] = result
    elif status == 'failed':
        response['error'] = str(job.exc_info) if job.exc_info else 'Job failed.'
    return jsonify(response)
