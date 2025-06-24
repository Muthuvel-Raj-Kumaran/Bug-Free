import os
import psycopg2
from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for
from werkzeug.utils import secure_filename
from email.message import EmailMessage
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, session

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # max 16MB upload
app.secret_key = 'dev-secret-key-123'

# DB connection info — replace with your credentials
DB_HOST = 'localhost'
DB_NAME = 'JiraCloneDB'
DB_USER = 'postgres'
DB_PASS = 'root'

def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def send_email(to_email, subject, html_content):
    import smtplib
    from email.message import EmailMessage

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = 'muthuvelraj2818@gmail.com'
    msg['To'] = to_email
    msg.set_content("This email requires an HTML-compatible viewer.")
    msg.add_alternative(html_content, subtype='html')

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('muthuvelraj2818@gmail.com', 'kxgh igwf elbh xibo')
        server.send_message(msg)

@app.route('/')
def index():
    return redirect(url_for('register'))

@app.route('/dashboard.html')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    game_name = request.args.get('game_name')
    phase = request.args.get('phase')
    return render_template('dashboard.html', game_name=game_name, phase=phase)

@app.route('/project')
def project():
    email = request.args.get('email')
    return render_template('projects.html', email=email)

@app.route('/accept_invite', methods=['GET'])
def accept_invite_form():
    return render_template('accept_invite.html')

@app.route('/invite_user', methods=['POST'])
def invite_user():
    data = request.json
    email = data.get('email', '').strip().lower()
    print(f"Received invite request for: {email}")

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
    existing = cur.fetchone()
    print(f"Existing user check result: {existing}")

    if existing:
        return jsonify({'error': 'User already exists'}), 409

    cur.execute("INSERT INTO users (email) VALUES (%s)", (email,))
    conn.commit()
    cur.close()
    conn.close()

    invite_link = f"http://localhost:5000/accept_invite?email={email}"
    html_body = f"""
    <html>
    <body>
        <p>You've been invited to join BUG FREE.</p>
        <p>
        <a href="{invite_link}" style="display:inline-block;padding:10px 15px;
            background-color:#28a745;color:white;text-decoration:none;border-radius:4px;">
            Accept Invite
        </a>
        </p>
    </body>
    </html>
    """

    send_email(email, "You're invited!", html_body)
    return jsonify({'message': 'Invitation sent'})

@app.route('/accept_invite', methods=['POST'])
def accept_invite():
    data = request.json
    email = data.get('email')
    name = data.get('name')

    if not email or not name:
        return jsonify({'error': 'Missing email or name'}), 400

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("UPDATE users SET name = %s, is_active = TRUE WHERE email = %s", (name, email))
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({'message': 'Invitation accepted'})

@app.route('/active_users', methods=['GET'])
def active_users():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM users WHERE is_active = TRUE")
    users = [{'id': r[0], 'name': r[1]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(users)

@app.route('/assign_user', methods=['POST'])
def assign_user():
    data = request.json
    user_id = data.get('user_id')
    project_name = data.get('project_name')

    if not user_id or not project_name:
        return jsonify({'error': 'Missing user_id or project_name'}), 400

    conn = get_db_conn()
    cur = conn.cursor()

    # Get email and name of the user
    cur.execute("SELECT email, name FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'error': 'User not found'}), 404
    email, name = row

    # Assign user to the project
    cur.execute("INSERT INTO project_assignments (user_id, project_name) VALUES (%s, %s)", (user_id, project_name))
    conn.commit()

    # Optional: Fetch project/game info to include in the email
    cur.execute("SELECT phase, category FROM projects WHERE game_name = %s", (project_name,))
    proj_info = cur.fetchone()
    phase = proj_info[0] if proj_info else 'N/A'
    category = proj_info[1] if proj_info else 'N/A'

    cur.close()
    conn.close()

    # Build email content
    html_body = f"""
    <html>
    <body>
        <p>Hi {name},</p>
        <p>You have been assigned to the project: <strong>{project_name}</strong>.</p>
        <p><strong>Phase:</strong> {phase} <br>
           <strong>Category:</strong> {category}</p>
        <p>Please login to your BUG FREE application to view your tickets.</p>
        <p>Thanks!</p>
    </body>
    </html>
    """

    send_email(email, "Project Assignment Notification", html_body)
    return jsonify({'message': 'User assigned and notified'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')

    name = request.form.get('name')
    email = request.form.get('email').strip().lower()
    password = request.form.get('password')

    if not name or not email or not password:
        return "Missing fields", 400

    hashed_pw = generate_password_hash(password)

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
    if cur.fetchone():
        cur.close()
        conn.close()
        return "Email already registered", 409

    cur.execute("INSERT INTO users (name, email, password, is_active) VALUES (%s, %s, %s, TRUE)", (name, email, hashed_pw))
    conn.commit()
    cur.close()
    conn.close()

    # Send welcome email
    html_body = f"""
    <html>
    <body>
        <p>Hi {name},</p>
        <p>Welcome to <strong>BUG FREE</strong>! </p>
        <p>Your account has been successfully created. You can now <a href="http://localhost:5000/login">login here</a>.</p>
        <p>Happy bug tracking!<br>The BUG FREE Team</p>
    </body>
    </html>
    """

    try:
        send_email(email, "Welcome to BUG FREE!", html_body)
    except Exception as e:
        print(f"Failed to send welcome email: {e}")

    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email').strip().lower()
    password = request.form.get('password')

    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name, password FROM users WHERE email = %s AND is_active = TRUE", (email,))
    user = cur.fetchone()
    cur.close()
    conn.close()

    if user and check_password_hash(user[2], password):
        session['user_id'] = user[0]
        session['user_name'] = user[1]
        return redirect('/projects')
    else:
        return "Invalid credentials", 401
    
@app.route('/projects')
def projects_alias():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('projects.html', email=session.get('user_email'))

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/get_tickets', methods=['GET'])
def get_tickets():
    work_type = request.args.get('workType')
    game_name = request.args.get('gameName')
    search = request.args.get('search')

    conn = get_db_conn()
    cur = conn.cursor()

    query = """
        SELECT id, summary, project, work_type, status, description, assignee, team, game_name
        FROM tickets
        WHERE 1=1
    """
    params = []

    if work_type:
        query += " AND work_type = %s"
        params.append(work_type)

    if game_name:
        query += " AND game_name = %s"
        params.append(game_name)

    if search:
        query += " AND (summary ILIKE %s OR description ILIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])

    cur.execute(query, params)
    tickets = cur.fetchall()

    ticket_list = []
    for row in tickets:
        ticket = {
            'id': row[0],
            'summary': row[1],
            'project': row[2],
            'work_type': row[3],
            'status': row[4],
            'description': row[5],
            'assignee': row[6],
            'team': row[7],
            'game_name': row[8],
            'attachments': []
        }

        # Fetch attachments for this ticket
        cur.execute("SELECT id, filename FROM ticket_attachments WHERE ticket_id = %s", (ticket['id'],))
        attachments = cur.fetchall()
        ticket['attachments'] = [{'id': a[0], 'filename': a[1]} for a in attachments]

        ticket_list.append(ticket)

    cur.close()
    conn.close()
    return jsonify(ticket_list)


@app.route('/update_ticket/<int:ticket_id>', methods=['POST'])
def update_ticket(ticket_id):
    if request.content_type.startswith('multipart/form-data'):
        attachment = request.files.get('newAttachment')
        if not attachment:
            return jsonify({'error': 'No attachment file provided'}), 400

        filename = secure_filename(attachment.filename)
        data = attachment.read()

        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ticket_attachments (ticket_id, filename, data) VALUES (%s, %s, %s)",
            (ticket_id, filename, data)
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Attachment saved'}), 200

    data = request.json or {}
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    allowed_fields = ['summary','project','work_type','status','description','assignee','team','game_name']

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("SELECT assignee, status, summary FROM tickets WHERE id = %s", (ticket_id,))
    old_ticket = cur.fetchone()
    if not old_ticket:
        cur.close()
        conn.close()
        return jsonify({'error': 'Ticket not found'}), 404

    old_assignee, old_status, summary = old_ticket

    updates = []
    params = []
    for field in allowed_fields:
        if field in data:
            updates.append(f"{field} = %s")
            params.append(data[field])

    if not updates:
        cur.close()
        conn.close()
        return jsonify({'message': 'No fields to update'}), 400

    params.append(ticket_id)
    update_query = f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s"
    cur.execute(update_query, params)
    conn.commit()

    new_status = data.get('status', old_status)
    new_assignee = data.get('assignee', old_assignee)

    if (new_status != old_status) or (new_assignee != old_assignee):
        if new_assignee:
            cur.execute("SELECT email, name FROM users WHERE id = %s", (new_assignee,))
            user = cur.fetchone()
            if user:
                to_email, user_name = user

                cur.execute("""
                    SELECT summary, description, project, status, work_type, game_name
                    FROM tickets WHERE id = %s
                """, (ticket_id,))
                ticket_details = cur.fetchone()

                if ticket_details:
                    summary, description, project, status, work_type, game_name = ticket_details

                    html_content = f"""
                    <html>
                    <body>
                        <p>Hello {user_name},</p>
                        <p>This ticket has been updated:</p>
                        <ul>
                            <li><strong>Summary:</strong> {summary}</li>
                            <li><strong>Description:</strong> {description}</li>
                            <li><strong>Project:</strong> {project}</li>
                            <li><strong>Status:</strong> {status}</li>
                            <li><strong>Work Type:</strong> {work_type}</li>
                            <li><strong>Game Name:</strong> {game_name}</li>
                        </ul>
                    </body>
                    </html>
                    """
                    try:
                        send_email(to_email, f"Ticket Updated: {summary}", html_content)
                        print(f"Notification email sent to {to_email}")
                    except Exception as e:
                        print(f"Error sending update email: {e}")

    cur.close()
    conn.close()

    return jsonify({'message': 'Ticket updated successfully'})

@app.route('/api/assignees')
def get_project_assignees():
    project = request.args.get('project')
    if not project:
        return jsonify([])

    conn = get_db_conn()
    cur = conn.cursor()

    query = '''
        SELECT users.id, users.name
        FROM users
        JOIN project_invitations ON users.id = project_invitations.user_id
        WHERE project_invitations.status = 'accepted'
        AND project_invitations.project_name = %s
    '''
    cur.execute(query, (project,))
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([{'id': row[0], 'name': row[1]} for row in rows])

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """
    Get list of projects, optionally filtered by search or game_name.
    """
    search = request.args.get('search', '').strip()
    game_filter = request.args.get('game_name', '').strip()

    conn = get_db_conn()
    cur = conn.cursor()

    query = "SELECT id, game_name, phase, category FROM projects WHERE 1=1"
    params = []

    if search:
        query += " AND LOWER(game_name) LIKE %s"
        params.append(f"%{search.lower()}%")
    if game_filter:
        query += " AND game_name = %s"
        params.append(game_filter)

    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    projects = [{
        "id": r[0],
        "game_name": r[1],
        "phase": r[2],
        "categories": r[3]
    } for r in rows]

    return jsonify(projects)

@app.route('/create_project', methods=['POST'])
def create_project():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Missing JSON body'}), 400

    game_name = data.get('game_name', '').strip()
    phase = data.get('phase', '').strip()
    categories = data.get('categories', '').strip()

    if not game_name:
        return jsonify({'error': 'Game name is required'}), 400

    print(f"Creating project with: game_name={game_name}, phase={phase}, categories={categories}")

    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute(
        "INSERT INTO projects (game_name, phase, category) VALUES (%s, %s, %s)",
        (game_name, phase, categories)
    )

        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'message': 'Project created successfully'})
    except Exception as e:
        print(f"Error creating project: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_game_names', methods=['GET'])
def get_game_names():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT game_name FROM tickets WHERE game_name IS NOT NULL AND game_name != ''")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([row[0] for row in rows])


@app.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    data = request.form
    project = data.get('project')
    work_type = data.get('workType')
    status = data.get('status')
    summary = data.get('summary')
    description = data.get('description')
    assignee = data.get('assignee')
    team = data.get('team')
    game_name = data.get('gameName')

    try:
        conn = get_db_conn()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO tickets 
            (project, work_type, status, summary, description, assignee, team, game_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
            """,
            (project, work_type, status, summary, description, assignee, team, game_name)
        )
        ticket_id = cur.fetchone()[0]

        files = request.files.getlist('attachment')  
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_data = file.read()
                cur.execute(
                    "INSERT INTO ticket_attachments (ticket_id, filename, data) VALUES (%s, %s, %s)",
                    (ticket_id, filename, file_data)
                )

        conn.commit()
        cur.close()
        conn.close()

        if assignee:
            try:
                conn = get_db_conn()
                cur = conn.cursor()
                cur.execute("SELECT name, email FROM users WHERE id = %s", (assignee,))
                user = cur.fetchone()
                cur.close()
                conn.close()

                if user:
                    assignee_name, assignee_email = user
                    html_content = f"""
                    <html>
                    <body>
                        <p>Hello {assignee_name},</p>
                        <p>You have been assigned a new ticket:</p>
                        <ul>
                            <li><strong>Summary:</strong> {summary}</li>
                            <li><strong>Description:</strong> {description}</li>
                            <li><strong>Project:</strong> {project}</li>
                            <li><strong>Work Type:</strong> {work_type}</li>
                            <li><strong>Status:</strong> {status}</li>
                            <li><strong>Game Name:</strong> {game_name}</li>
                        </ul>
                        <p>Please log in to <a href="http://localhost:5000">BUG FREE</a> to view the details.</p>
                    </body>
                    </html>
                    """
                    send_email(assignee_email, f"New Ticket Assigned: {summary}", html_content)
                    print(f"Email sent to {assignee_email}")
            except Exception as e:
                print(f"Error sending email to assignee: {e}")

        return jsonify({'ticket_id': ticket_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ticket_attachment/<int:ticket_id>', methods=['GET'])
def ticket_attachment(ticket_id):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT attachment, attachment_filename FROM tickets WHERE id = %s", (ticket_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row or not row[0]:
            return jsonify({'error': 'No attachment found'}), 404

        attachment_data, filename = row
        return send_file(
            BytesIO(attachment_data),
            download_name=filename,  
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/upload_attachment/<int:ticket_id>', methods=['POST'])
def upload_attachment(ticket_id):
    try:
        files = request.files.getlist('attachments')
        conn = get_db_conn()
        cur = conn.cursor()

        inserted_ids = []
        for file in files:
            if file.filename:
                data = file.read()
                filename = secure_filename(file.filename)
                cur.execute(
                    "INSERT INTO ticket_attachments (ticket_id, filename, data) VALUES (%s, %s, %s) RETURNING id",
                    (ticket_id, filename, data)
                )
                new_id = cur.fetchone()[0]
                inserted_ids.append(new_id)

        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'status': 'ok', 'inserted_ids': inserted_ids})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/attachment/<int:attachment_id>', methods=['GET'])
def get_attachment(attachment_id):
    try:
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("SELECT data, filename FROM ticket_attachments WHERE id = %s", (attachment_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            return jsonify({'error': 'Attachment not found'}), 404

        data, filename = row
        return send_file(
            BytesIO(data),
            download_name=filename,
            as_attachment=True
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_attachment/<int:attachment_id>', methods=['DELETE'])
def delete_attachment(attachment_id):
    print(f"Delete request received for attachment: {attachment_id}")
    try:
        conn = get_db_conn()
        cur = conn.cursor()

        # Optional: Check if attachment exists first
        cur.execute("SELECT id FROM ticket_attachments WHERE id = %s", (attachment_id,))
        if cur.fetchone() is None:
            cur.close()
            conn.close()
            return jsonify({'error': 'Attachment not found'}), 404

        # Delete the attachment
        cur.execute("DELETE FROM ticket_attachments WHERE id = %s", (attachment_id,))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'message': 'Attachment deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
