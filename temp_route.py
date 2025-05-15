@app.route('/delete_break', methods=['POST'])
def delete_break():
    if not session.get('username'):
        return jsonify({'error': 'Not authorized'}), 401
    
    # Check if user is admin
    if not session.get('admin_logged_in'):
        return jsonify({'error': 'Only admins can delete breaks'}), 403
    
    break_id = request.form.get('break_id')
    
    if not break_id:
        return jsonify({'success': False, 'message': 'No break ID provided'})
    
    db = get_db()
    cursor = db.cursor()
    
    # Delete the break
    try:
        cursor.execute("DELETE FROM breaks WHERE id = ?", (break_id,))
        db.commit()
        return jsonify({'success': True})
    except sqlite3.Error as e:
        app.logger.error(f"Error deleting break: {e}")
        return jsonify({'success': False, 'message': str(e)})
