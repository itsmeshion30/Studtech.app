"""
StudTech - Student/Faculty Management System
A comprehensive web-based system for managing student records, announcements, and schedules.
"""

from flask import Flask, render_template_string, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func, text
from werkzeug.security import check_password_hash, generate_password_hash
import io
import os
import re

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "studtech_secret_key_2024")

database_url = os.getenv("DATABASE_URL", "sqlite:///studtech.db")
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
db = SQLAlchemy(app)

# ===================== MODELS ===================== #

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    fullname = db.Column(db.String(100))

class StudentUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    program = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    program = db.Column(db.String(50), nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    visit_date = db.Column(db.String(10))
    visit_time = db.Column(db.String(5))
    purpose = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Schedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    message = db.Column(db.String(200), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.String(500), nullable=False)
    schedule = db.Column(db.String(25), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="Pending")
    rejection_reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_type = db.Column(db.String(20), nullable=False)
    recipient_id = db.Column(db.String(50), nullable=False)
    sender = db.Column(db.String(20), nullable=False, default="System")
    title = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(30), nullable=False, default="info")
    status_label = db.Column(db.String(30), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(50))
    user_type = db.Column(db.String(20))  # 'student' or 'admin'
    action = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text, nullable=True)
    student_reply = db.Column(db.Text, nullable=True)  # Student can reply back to admin
    sender_type = db.Column(db.String(20), nullable=False, default="Student")
    message_type = db.Column(db.String(20), nullable=False, default="conversation")
    status_update = db.Column(db.String(30), nullable=True)
    is_read = db.Column(db.Boolean, default=False)
    is_replied = db.Column(db.Boolean, default=False)
    student_replied = db.Column(db.Boolean, default=False)  # Track if student has replied
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    messages = db.relationship(
        'ConversationMessage',
        backref='conversation',
        lazy=True,
        cascade='all, delete-orphan',
        order_by='ConversationMessage.timestamp.asc(), ConversationMessage.id.asc()'
    )


class ConversationMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False, index=True)
    sender_type = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    is_read = db.Column(db.Boolean, default=False)
    legacy_source_key = db.Column(db.String(60), unique=True, nullable=True)

def create_notification(recipient_type, recipient_id, title, message, category="info", sender="System", status_label=None):
    notification = Notification(
        recipient_type=recipient_type,
        recipient_id=str(recipient_id),
        sender=sender,
        title=title,
        message=message,
        category=category,
        status_label=status_label
    )
    db.session.add(notification)
    return notification

def create_status_message(student_id, student_name, subject, body, sender_type="Admin", status_update=None):
    status_message = ContactMessage(
        student_id=student_id,
        student_name=student_name,
        subject=subject,
        message=body,
        sender_type=sender_type,
        message_type="status",
        status_update=status_update,
        is_replied=True,
        is_read=False
    )
    db.session.add(status_message)
    return status_message


def get_or_create_conversation(student_id):
    conversation = Conversation.query.filter_by(student_id=student_id).first()
    if conversation:
        return conversation

    conversation = Conversation(student_id=student_id)
    db.session.add(conversation)
    db.session.flush()
    return conversation


def get_conversation_by_student_id(student_id):
    return Conversation.query.filter_by(student_id=student_id).first()


def add_conversation_message(conversation, sender_type, message, is_read=False, legacy_source_key=None, timestamp=None):
    cleaned_message = normalize_text(message)
    if not cleaned_message:
        return None
    if legacy_source_key and ConversationMessage.query.filter_by(legacy_source_key=legacy_source_key).first():
        return None

    created_at = timestamp or datetime.utcnow()
    chat_message = ConversationMessage(
        conversation_id=conversation.id,
        sender_type=sender_type.lower(),
        message=cleaned_message,
        timestamp=created_at,
        is_read=is_read,
        legacy_source_key=legacy_source_key
    )
    conversation.updated_at = created_at
    db.session.add(chat_message)
    return chat_message


def get_student_for_conversation(conversation):
    return StudentUser.query.filter_by(student_id=conversation.student_id).first()


def get_conversation_messages(conversation):
    return ConversationMessage.query.filter_by(conversation_id=conversation.id).order_by(
        ConversationMessage.timestamp.asc(),
        ConversationMessage.id.asc()
    ).all()


def mark_conversation_read(conversation, viewer_type):
    sender_type = 'admin' if viewer_type == 'student' else 'student'
    unread_messages = ConversationMessage.query.filter_by(
        conversation_id=conversation.id,
        sender_type=sender_type,
        is_read=False
    ).all()
    for message in unread_messages:
        message.is_read = True


def build_admin_conversation_items(search_term=""):
    conversations = Conversation.query.order_by(Conversation.updated_at.desc(), Conversation.id.desc()).all()
    search_value = normalize_text(search_term).lower()
    items = []

    for conversation in conversations:
        latest_message = ConversationMessage.query.filter_by(conversation_id=conversation.id).order_by(
            ConversationMessage.timestamp.desc(),
            ConversationMessage.id.desc()
        ).first()
        if not latest_message:
            continue

        student = get_student_for_conversation(conversation)
        student_name = student.fullname if student else conversation.student_id
        searchable_text = f"{student_name} {conversation.student_id}".lower()
        if search_value and search_value not in searchable_text:
            continue

        unread_count = ConversationMessage.query.filter_by(
            conversation_id=conversation.id,
            sender_type='student',
            is_read=False
        ).count()
        items.append({
            'conversation': conversation,
            'student': student,
            'student_name': student_name,
            'student_id': conversation.student_id,
            'latest_message': latest_message,
            'unread_count': unread_count
        })

    return items


def migrate_contact_messages_to_conversations():
    legacy_messages = ContactMessage.query.order_by(ContactMessage.student_id.asc(), ContactMessage.created_at.asc(), ContactMessage.id.asc()).all()

    for legacy_message in legacy_messages:
        conversation = get_or_create_conversation(legacy_message.student_id)
        student_seen_student_message = bool(legacy_message.reply or legacy_message.is_read)
        admin_seen_student_reply = bool(legacy_message.is_read)

        add_conversation_message(
            conversation,
            'student',
            legacy_message.message,
            is_read=student_seen_student_message,
            legacy_source_key=f"{legacy_message.id}:student_message",
            timestamp=legacy_message.created_at
        )
        add_conversation_message(
            conversation,
            'admin',
            legacy_message.reply,
            is_read=legacy_message.is_read,
            legacy_source_key=f"{legacy_message.id}:admin_reply",
            timestamp=legacy_message.created_at
        )
        add_conversation_message(
            conversation,
            'student',
            legacy_message.student_reply,
            is_read=admin_seen_student_reply,
            legacy_source_key=f"{legacy_message.id}:student_reply",
            timestamp=legacy_message.created_at
        )

PASSWORD_MIN_LENGTH = 8


def normalize_text(value):
    return (value or "").strip()


def hash_password(password):
    return generate_password_hash(password)


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(("pbkdf2:", "scrypt:"))


def password_meets_rules(password):
    if len(password) < PASSWORD_MIN_LENGTH:
        return False, f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must include at least one letter."
    if not re.search(r"\d", password):
        return False, "Password must include at least one number."
    return True, ""


def verify_password(account, submitted_password):
    stored_password = account.password or ""
    if is_password_hash(stored_password):
        return check_password_hash(stored_password, submitted_password), False
    return stored_password == submitted_password, True


def try_upgrade_legacy_password(account, submitted_password):
    matched, is_legacy_plain_text = verify_password(account, submitted_password)
    if matched and is_legacy_plain_text:
        account.password = hash_password(submitted_password)
    return matched


def migrate_sqlite_password_columns():
    db.session.execute(text("PRAGMA foreign_keys=OFF"))
    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS admin_new (
                id INTEGER PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                fullname VARCHAR(100)
            )
        """))
        db.session.execute(text("""
            INSERT INTO admin_new (id, username, password, fullname)
            SELECT id, username, password, fullname FROM admin
        """))
        db.session.execute(text("DROP TABLE admin"))
        db.session.execute(text("ALTER TABLE admin_new RENAME TO admin"))

        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS student_user_new (
                id INTEGER PRIMARY KEY,
                student_id VARCHAR(20) UNIQUE NOT NULL,
                fullname VARCHAR(100) NOT NULL,
                age INTEGER NOT NULL,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                program VARCHAR(50) NOT NULL,
                gender VARCHAR(10) NOT NULL,
                created_at DATETIME
            )
        """))
        db.session.execute(text("""
            INSERT INTO student_user_new (id, student_id, fullname, age, username, password, program, gender, created_at)
            SELECT id, student_id, fullname, age, username, password, program, gender, created_at FROM student_user
        """))
        db.session.execute(text("DROP TABLE student_user"))
        db.session.execute(text("ALTER TABLE student_user_new RENAME TO student_user"))
        db.session.commit()
        print("Expanded password columns for admin and student_user tables")
    except Exception:
        db.session.rollback()
        raise
    finally:
        db.session.execute(text("PRAGMA foreign_keys=ON"))
        db.session.commit()

# ===================== HTML TEMPLATES ===================== #

BASE_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    :root {
        --bg-start: #dfe7f1;
        --bg-end: #edf3f8;
        --primary: #275d93;
        --primary-dark: #183f6a;
        --secondary: #6ea2c9;
        --accent: #d08a44;
        --success: #2f8f7d;
        --warning: #d9a63f;
        --danger: #c8614b;
        --text-main: #1b2b3d;
        --text-soft: #607181;
        --card-bg: rgba(255,255,255,0.82);
        --border-soft: rgba(92,118,145,0.18);
        --shadow-soft: 0 18px 40px rgba(30, 52, 75, 0.10);
        --shadow-strong: 0 28px 70px rgba(16, 33, 53, 0.16);
        --glass-highlight: rgba(255,255,255,0.72);
    }
    * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Poppins', sans-serif; }

    .password-group {
        position: relative;
    }
    .password-group .form-control {
        padding-right: 48px;
    }
    .password-toggle-btn {
        position: absolute;
        right: 12px;
        top: 50%;
        transform: translateY(-50%);
        width: 34px;
        height: 34px;
        border: none;
        border-radius: 50%;
        background: rgba(63,114,175,0.12);
        color: var(--primary-dark);
        display: inline-flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: background 0.2s ease, color 0.2s ease, transform 0.2s ease;
        padding: 0;
    }
    .password-toggle-btn svg {
        width: 18px;
        height: 18px;
    }
    .password-toggle-btn:hover {
        background: rgba(63,114,175,0.2);
        transform: translateY(-50%) scale(1.05);
    }
    .password-toggle-btn:focus-visible {
        outline: 2px solid rgba(63,114,175,0.35);
        outline-offset: 2px;
    }
    body.dark .password-toggle-btn {
        background: rgba(137,183,221,0.14);
        color: #eef6ff;
    }
    body.dark .password-toggle-btn:hover {
        background: rgba(137,183,221,0.24);
    }
    body {
        background:
            radial-gradient(circle at top left, rgba(255,255,255,0.95), transparent 24%),
            radial-gradient(circle at 84% 12%, rgba(110,162,201,0.18), transparent 20%),
            radial-gradient(circle at 18% 82%, rgba(208,138,68,0.14), transparent 18%),
            linear-gradient(180deg, #f5f8fb 0%, var(--bg-start) 42%, var(--bg-end) 100%);
        min-height: 100vh;
        color: var(--text-main);
        position: relative;
        overflow-x: hidden;
    }
    body::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        background:
            linear-gradient(120deg, rgba(255,255,255,0.38), transparent 24%, transparent 72%, rgba(255,255,255,0.18)),
            repeating-linear-gradient(90deg, rgba(255,255,255,0.05) 0, rgba(255,255,255,0.05) 1px, transparent 1px, transparent 140px);
        opacity: 0.55;
    }
    body.dark {
        background:
            radial-gradient(circle at 18% 16%, rgba(84,125,170,0.24), transparent 22%),
            radial-gradient(circle at 82% 20%, rgba(208,138,68,0.14), transparent 18%),
            linear-gradient(180deg, #0b1420 0%, #111b29 48%, #162334 100%) !important;
    }
    .container { max-width: 1460px; margin: 0 auto; padding: 24px; width: 100%; }

    .logo-container {
        text-align: center;
        margin-bottom: 30px;
        animation: fadeInDown 0.8s ease;
    }
    .logo {
        width: 120px;
        height: 120px;
        background:
            radial-gradient(circle at 30% 28%, rgba(255,255,255,0.75), transparent 28%),
            linear-gradient(145deg, #2b6ca6, #19456f 58%, #c8843f 100%);
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border: 1px solid rgba(255,255,255,0.65);
        box-shadow: var(--shadow-strong);
        animation: pulse 2s infinite;
        position: relative;
    }
    .logo::after {
        content: "";
        position: absolute;
        inset: 8px;
        border-radius: 50%;
        border: 1px solid rgba(255,255,255,0.28);
    }
    .logo-text {
        font-size: 36px;
        font-weight: 700;
        color: white;
        text-shadow: 0 4px 18px rgba(0,0,0,0.25);
        letter-spacing: 1px;
    }
    .logo-subtitle {
        color: rgba(34,48,70,0.85);
        font-size: 14px;
        margin-top: 10px;
        letter-spacing: 3px;
        text-transform: uppercase;
    }
    body.dark .logo-subtitle { color: rgba(255,255,255,0.85); }

    @keyframes fadeInDown {
        from { opacity: 0; transform: translateY(-30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); box-shadow: var(--shadow-strong); }
        50% { transform: scale(1.03); box-shadow: 0 32px 80px rgba(31, 61, 96, 0.18); }
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .card {
        background: var(--card-bg);
        border-radius: 24px;
        box-shadow: var(--shadow-soft);
        padding: 30px;
        margin-bottom: 22px;
        border: 1px solid var(--border-soft);
        backdrop-filter: blur(18px);
        position: relative;
        overflow: hidden;
    }
    .card::before {
        content: "";
        position: absolute;
        inset: 0 0 auto 0;
        height: 120px;
        background: linear-gradient(180deg, rgba(255,255,255,0.52), transparent);
        pointer-events: none;
    }
    body.dark .card {
        background: rgba(20, 31, 47, 0.88) !important;
        color: #fff;
        border-color: rgba(128,155,184,0.16);
        box-shadow: 0 24px 54px rgba(0,0,0,0.28);
    }
    .card-header {
        font-size: 24px;
        font-weight: 600;
        color: var(--text-main);
        margin-bottom: 20px;
        border-bottom: 1px solid rgba(63,114,175,0.14);
        padding-bottom: 12px;
    }
    body.dark .card-header { color: #fff !important; }

    .btn {
        padding: 12px 24px;
        border: 1px solid rgba(255,255,255,0.14);
        border-radius: 14px;
        cursor: pointer;
        font-weight: 600;
        transition: all 0.25s ease;
        box-shadow: 0 10px 24px rgba(31, 61, 96, 0.12);
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    .btn::before {
        content: "";
        position: absolute;
        inset: 0;
        background: linear-gradient(180deg, rgba(255,255,255,0.22), transparent 46%);
        pointer-events: none;
    }
    .btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 16px 30px rgba(31, 61, 96, 0.16);
    }
    .btn-primary { background: linear-gradient(145deg, #2a6aa1, #1b4f7d 62%, #173e63); color: white; }
    .btn-primary:hover { background: linear-gradient(145deg, var(--primary-dark), #1f5587); }
    .btn-danger { background: linear-gradient(145deg, #d36a53, #b6503c); color: white; }
    .btn-danger:hover { background: linear-gradient(145deg, #bc5640, #9e4331); }
    .btn-success { background: linear-gradient(145deg, #379986, #267767); color: white; }
    .btn-success:hover { background: linear-gradient(145deg, #2c8675, #21695a); }
    .btn-warning { background: linear-gradient(145deg, #dfa84e, #c77f37); color: white; }
    .btn-warning:hover { background: linear-gradient(145deg, #cf9442, #b26f2f); }
    .btn-info { background: linear-gradient(145deg, #72a9cb, #3f6f99); color: white; }
    .btn-info:hover { background: linear-gradient(145deg, #5f99bf, #335c81); }
    .btn-light {
        background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,245,250,0.88));
        color: var(--primary-dark);
        border-color: rgba(117,145,174,0.24);
    }

    .form-group { margin-bottom: 20px; }
    .form-control, .form-select {
        width: 100%;
        padding: 14px 18px;
        border: 1px solid rgba(106,133,161,0.18);
        border-radius: 14px;
        font-size: 14px;
        transition: all 0.25s ease;
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,248,251,0.94));
        box-shadow: inset 0 1px 2px rgba(255,255,255,0.65), 0 4px 10px rgba(31,61,96,0.03);
    }
    body.dark .form-control, body.dark .form-select {
        background: linear-gradient(180deg, rgba(20,42,67,0.95), rgba(16,34,56,0.92)) !important;
        border-color: rgba(101,130,163,0.28) !important;
        color: #fff !important;
        box-shadow: inset 0 1px 2px rgba(255,255,255,0.03) !important;
    }
    .form-control:focus, .form-select:focus {
        border-color: var(--primary);
        outline: none;
        box-shadow: 0 0 0 4px rgba(39,93,147,0.10), 0 16px 26px rgba(31,61,96,0.08);
    }
    label { display: block; margin-bottom: 8px; font-weight: 500; color: #555; }
    body.dark label { color: #ccc !important; }

    h1, h2, h3, h4 { color: var(--text-main); font-weight: 600; }
    body.dark h1, body.dark h2, body.dark h3, body.dark h4 { color: #fff !important; }

    .table { width: 100%; border-collapse: separate; border-spacing: 0; margin-top: 20px; }
    .table th, .table td { padding: 14px; text-align: left; border-bottom: 1px solid #eee; vertical-align: top; }
    .table th {
        background: linear-gradient(145deg, #316c9d, #214f79);
        color: white;
        font-weight: 600;
    }
    .table tr:hover { background: linear-gradient(90deg, rgba(84,125,170,0.08), rgba(255,255,255,0.98)); }
    body.dark .table tr:hover { background: #1a1a2e !important; }
    .table-responsive {
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        border-radius: 18px;
    }

    .alert {
        padding: 16px 20px;
        border-radius: 14px;
        margin-bottom: 15px;
        animation: slideIn 0.5s ease;
    }
    .alert-success { background: linear-gradient(135deg, #e3f5ef, #d1eee5); color: #155724; border: 1px solid #a3d8c7; }
    .alert-danger { background: linear-gradient(135deg, #fbe1dd, #f8d1cb); color: #721c24; border: 1px solid #efb5ac; }
    .alert-info { background: linear-gradient(135deg, #e3f0fb, #d8ebf9); color: #184b68; border: 1px solid #bdd7ea; }
    .alert-warning { background: linear-gradient(135deg, #fff4dc, #ffeac3); color: #7b5a08; border: 1px solid #f3d88a; }

    .nav-tabs {
        display: flex;
        border-bottom: 2px solid rgba(63,114,175,0.12);
        margin-bottom: 25px;
        gap: 8px;
        flex-wrap: wrap;
    }
    .nav-tabs button {
        padding: 14px 24px;
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(63,114,175,0.10);
        cursor: pointer;
        font-size: 15px;
        color: var(--text-soft);
        transition: all 0.25s ease;
        border-radius: 14px 14px 0 0;
        position: relative;
        overflow: hidden;
    }
    .nav-tabs button:hover {
        color: var(--primary-dark);
        background: rgba(63,114,175,0.10);
    }
    .nav-tabs button.active {
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: white;
        font-weight: 600;
        border-color: transparent;
    }
    body.dark .nav-tabs button { color: #ccc !important; }
    body.dark .nav-tabs { border-bottom-color: #533483 !important; }
    .dashboard-layout {
        display: grid;
        grid-template-columns: minmax(240px, 24%) minmax(0, 1fr);
        gap: 22px;
        align-items: start;
        min-height: calc(100vh - 48px);
    }
    .dashboard-sidebar {
        position: sticky;
        top: 24px;
        align-self: stretch;
    }
    .sidebar-card {
        background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(243,247,251,0.88));
        border: 1px solid rgba(63,114,175,0.12);
        border-radius: 24px;
        box-shadow: 0 16px 34px rgba(31,61,96,0.09);
        padding: 18px;
        backdrop-filter: blur(14px);
        min-height: calc(100vh - 48px);
        display: flex;
        flex-direction: column;
    }
    .sidebar-title {
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: var(--text-soft);
        margin-bottom: 14px;
        padding: 0 4px;
    }
    .sidebar-tabs {
        display: grid;
        gap: 10px;
        margin-bottom: 0;
        border-bottom: none;
    }
    .sidebar-tabs button {
        width: 100%;
        border-radius: 18px;
        text-align: left;
        padding: 14px 16px;
        background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(242,246,250,0.88));
        border: 1px solid rgba(63,114,175,0.10);
        color: var(--text-main);
        box-shadow: 0 8px 18px rgba(31,61,96,0.06);
    }
    .sidebar-tabs button:hover {
        background: linear-gradient(180deg, rgba(228,239,248,0.96), rgba(214,229,241,0.90));
        color: var(--primary-dark);
        transform: translateX(2px);
    }
    .sidebar-tabs button.active {
        background: linear-gradient(145deg, #2b679c, #1c4d79);
        color: #fff;
        border-color: transparent;
        box-shadow: 0 16px 28px rgba(31,61,96,0.16);
    }
    .sidebar-spacer {
        flex: 1;
        min-height: 16px;
    }
    .sidebar-footer-tabs {
        margin-top: 0;
        padding-top: 16px;
        border-top: 1px solid rgba(63,114,175,0.10);
    }
    .sidebar-tabs .sidebar-link-button {
        display: flex;
        align-items: center;
        width: 100%;
        border-radius: 18px;
        text-align: left;
        padding: 14px 16px;
        background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(242,246,250,0.88));
        border: 1px solid rgba(63,114,175,0.10);
        color: var(--text-main);
        box-shadow: 0 8px 18px rgba(31,61,96,0.06);
        text-decoration: none;
        transition: all 0.25s ease;
    }
    .sidebar-tabs .sidebar-link-button:hover {
        background: linear-gradient(180deg, rgba(228,239,248,0.96), rgba(214,229,241,0.90));
        color: var(--primary-dark);
        transform: translateX(2px);
        text-decoration: none;
    }
    .sidebar-footer-tabs .sidebar-link-button,
    .sidebar-footer-tabs button {
        width: 100%;
        margin-left: 0;
    }
    .dashboard-main {
        min-width: 0;
        max-height: calc(100vh - 170px);
        overflow-y: auto;
        padding-right: 6px;
    }
    .dashboard-panel {
        min-height: 680px;
        margin-bottom: 0;
    }
    .sidebar-meta {
        margin-bottom: 18px;
        padding: 4px 6px 16px;
        border-bottom: 1px solid rgba(63,114,175,0.10);
    }
    .sidebar-brand {
        font-size: 24px;
        font-weight: 700;
        color: var(--primary-dark);
        margin-bottom: 6px;
    }
    .sidebar-subtitle {
        color: var(--text-soft);
        font-size: 13px;
        line-height: 1.5;
    }
    .header-action-group {
        display: flex;
        gap: 15px;
        align-items: center;
        flex-wrap: wrap;
        justify-content: flex-end;
    }
    .header-action-group .btn,
    .header-action-group summary {
        border-radius: 18px;
        text-align: left;
        padding: 14px 16px;
        background: linear-gradient(180deg, rgba(255,255,255,0.94), rgba(242,246,250,0.88));
        border: 1px solid rgba(63,114,175,0.10);
        color: var(--text-main);
        box-shadow: 0 8px 18px rgba(31,61,96,0.06);
    }
    .header-action-group .btn:hover,
    .header-action-group summary:hover {
        background: linear-gradient(180deg, rgba(228,239,248,0.96), rgba(214,229,241,0.90));
        color: var(--primary-dark);
        transform: translateX(2px);
    }

    .tab-content { display: none; }
    .tab-content.active { display: block; animation: fadeIn 0.5s ease; }
    .section-header,
    .split-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 15px;
        flex-wrap: wrap;
    }
    .section-header {
        margin-bottom: 15px;
    }
    .split-row.align-start {
        align-items: flex-start;
    }
    .inline-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        align-items: center;
    }
    .align-end-group {
        display: flex;
        align-items: flex-end;
    }

    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 30px;
        padding: 24px 26px;
        background:
            radial-gradient(circle at top left, rgba(255,255,255,0.28), transparent 28%),
            linear-gradient(145deg, rgba(31,84,132,0.96), rgba(22,62,101,0.97) 62%, rgba(14,39,65,0.98));
        border-radius: 28px;
        backdrop-filter: blur(18px);
        box-shadow: var(--shadow-strong);
        border: 1px solid rgba(255,255,255,0.16);
        gap: 18px;
    }
    .header-actions {
        display: flex;
        gap: 15px;
        align-items: center;
        flex-wrap: wrap;
        justify-content: flex-end;
        flex: 1;
    }
    .header-bar > div:last-child {
        display: flex;
        gap: 15px;
        align-items: center;
        flex-wrap: wrap;
        justify-content: flex-end;
        flex: 1;
    }
    .logout-btn { margin-left: 10px; }

    .charts-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 25px;
        margin: 25px 0;
    }
    .chart-box {
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(244,248,252,0.94));
        padding: 25px;
        border-radius: 24px;
        box-shadow: 0 16px 34px rgba(31,61,96,0.10);
        transition: all 0.3s ease;
        border: 1px solid rgba(63,114,175,0.12);
    }
    .chart-box:hover {
        transform: translateY(-6px);
        box-shadow: 0 24px 46px rgba(31,61,96,0.14);
    }
    body.dark .chart-box { background: linear-gradient(180deg, rgba(24,35,52,0.98), rgba(18,29,44,0.94)) !important; }

    .badge {
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        animation: pulse 2s infinite;
        display: inline-flex;
        align-items: center;
        justify-content: center;
    }
    .badge-new { background: linear-gradient(135deg, var(--danger), #c95d47); color: white; }

    .welcome-msg {
        font-size: 28px;
        color: #111;
        text-align: center;
        margin: 20px 0;
        text-shadow: 0 2px 10px rgba(255,255,255,0.55);
        animation: fadeIn 1s ease;
    }
    body.dark .welcome-msg { color: #fff; text-shadow: 0 2px 16px rgba(0,0,0,0.35); }

    .detail-view { background: white; padding: 30px; border-radius: 20px; }
    body.dark .detail-view { background: #16213e !important; }
    .back-btn { margin-bottom: 20px; }
    .settings-card {
        max-width: 500px;
        margin: 50px auto;
    }

    .print-area { display: none; }
    @media print {
        .no-print { display: none !important; }
        .print-area { display: block !important; }
        .charts-container { display: none !important; }
        .header-bar { display: none !important; }
    }

    .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
    .grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; }
    .grid-4 { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 20px; }
    @media (max-width: 768px) {
        .grid-2, .grid-3, .grid-4, .dashboard-split, .subtle-grid, .dashboard-layout { grid-template-columns: 1fr; }
        .logo { width: 80px; height: 80px; }
        .logo-text { font-size: 24px; }
        .container { padding: 14px; }
        .card, .detail-view, .chart-box, .messenger-body, .composer-body { padding: 18px; }
        .card-header { font-size: 20px; }
        h1 { font-size: 1.6rem; line-height: 1.25; }
        h2 { font-size: 1.35rem; }
        h3 { font-size: 1.15rem; }
        .btn { width: 100%; padding: 12px 16px; }
        .btn.btn-sm { width: auto; }
        .header-bar h1 { text-align: center; width: 100%; }
        .header-bar { flex-direction: column; gap: 16px; align-items: stretch; }
        .header-actions, .header-bar > div { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; width: 100%; }
        .header-actions > *, .header-bar > div:last-child > * { flex: 1 1 100%; }
        .nav-tabs {
            flex-wrap: nowrap;
            overflow-x: auto;
            padding-bottom: 8px;
            scrollbar-width: thin;
        }
        .nav-tabs button {
            flex: 0 0 78%;
            min-width: 220px;
            border-radius: 14px;
            white-space: normal;
            text-align: center;
        }
        .table { min-width: 640px; }
        .table th, .table td { padding: 12px 10px; font-size: 13px; }
        .section-header, .split-row, .notification-top, .messenger-topbar, .messenger-title, .send-row {
            flex-direction: column;
            align-items: stretch;
        }
        .inline-actions {
            width: 100%;
            justify-content: stretch;
        }
        .inline-actions > *,
        .card-actions > * {
            flex: 1 1 100%;
        }
        .align-end-group {
            display: block;
        }
        .preview-panel {
            left: 50%;
            right: auto;
            transform: translateX(-50%);
            width: min(92vw, 340px);
        }
        .welcome-msg { font-size: 22px; }
        .composer-card, .settings-card, .login-container { margin: 20px auto; }
        .chat-bubble, .chat-bubble.system { max-width: 100%; }
        .messenger-thread { max-height: none; }
        .messenger-split { grid-template-columns: 1fr; min-height: auto; }
        .chat-list-panel { border-right: none; border-bottom: 1px solid rgba(63,114,175,0.12); }
        .chat-pane { min-height: 520px; }
        .dashboard-sidebar {
            position: static;
        }
        .dashboard-main {
            max-height: none;
            overflow: visible;
            padding-right: 0;
        }
        .sidebar-card {
            min-height: auto;
        }
        .sidebar-tabs {
            grid-template-columns: 1fr;
        }
        .student-info-value, .notification-card, .message-card { word-break: break-word; }
    }

    .login-container {
        max-width: 450px;
        margin: 50px auto;
        animation: fadeInUp 0.8s ease;
    }
    .login-header {
        text-align: center;
        margin-bottom: 30px;
    }
    .login-header h1 {
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, var(--primary), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 14px;
        border-radius: 999px;
        color: #fff;
        font-size: 13px;
        font-weight: 600;
        line-height: 1;
    }
    .status-pill.pending { background: linear-gradient(135deg, var(--warning), var(--accent)); }
    .status-pill.accepted { background: linear-gradient(135deg, var(--success), #23877c); }
    .status-pill.rejected { background: linear-gradient(135deg, var(--danger), #cb5d45); }
    .soft-note {
        margin-top: 8px;
        color: var(--text-soft);
        font-size: 13px;
        line-height: 1.5;
    }
    .card-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-top: 14px;
        padding-top: 14px;
        border-top: 1px solid rgba(63,114,175,0.10);
    }
    .notification-feed { display: grid; gap: 14px; margin-top: 18px; }
    .notification-card {
        border: 1px solid rgba(63,114,175,0.12);
        border-radius: 22px;
        padding: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(242,247,251,0.95));
        box-shadow: 0 14px 28px rgba(31, 61, 96, 0.07);
    }
    body.dark .notification-card { background: #1b2744 !important; }
    body.dark .chat-list-panel,
    body.dark .chat-composer,
    body.dark .chat-list-item { background: #1b2744 !important; }
    body.dark .chat-pane { background: linear-gradient(180deg, #16213e, #111827) !important; }
    body.dark .chat-list-name { color: #fff !important; }
    body.dark .chat-list-item.active {
        background: linear-gradient(135deg, rgba(137,183,221,0.18), rgba(63,114,175,0.24)) !important;
    }
    .notification-top {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }
    .notification-title { font-weight: 700; color: var(--text-main); }
    body.dark .notification-title { color: #fff; }
    .notification-meta { color: var(--text-soft); font-size: 12px; }
    .dashboard-split { display: grid; grid-template-columns: 1.3fr 0.9fr; gap: 20px; }
    .chat-thread { display: grid; gap: 14px; }
    .chat-bubble {
        max-width: 86%;
        padding: 16px 18px;
        border-radius: 24px;
        box-shadow: 0 12px 24px rgba(31, 61, 96, 0.08);
        border: 1px solid rgba(63,114,175,0.10);
    }
    .chat-bubble.student {
        margin-right: auto;
        background: linear-gradient(180deg, #ffffff, #eff4f8);
        border-bottom-left-radius: 10px;
    }
    .chat-bubble.admin {
        margin-left: auto;
        background: linear-gradient(145deg, #2d6799, #1c4b76);
        color: #fff;
        border-bottom-right-radius: 10px;
        border-color: transparent;
    }
    .chat-bubble.system { margin-left: auto; margin-right: auto; max-width: 96%; background: linear-gradient(180deg, #fff6ea, #fcebd3); }
    .chat-meta {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 8px;
        font-size: 12px;
        color: var(--text-soft);
        flex-wrap: wrap;
    }
    .chat-label { font-weight: 700; color: var(--text-main); }
    body.dark .chat-label { color: #fff; }
    .section-kicker {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(63,114,175,0.10);
        color: var(--primary-dark);
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 14px;
    }
    .subtle-grid { display: grid; gap: 14px; }
    .mini-stat {
        padding: 16px 18px;
        border-radius: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,0.96), rgba(245,249,255,0.92));
        border: 1px solid rgba(63,114,175,0.12);
    }
    .mini-stat strong {
        display: block;
        font-size: 24px;
        color: var(--primary-dark);
    }
    .empty-state {
        padding: 24px;
        border-radius: 18px;
        background: rgba(255,255,255,0.8);
        border: 1px dashed rgba(63,114,175,0.24);
        text-align: center;
        color: var(--text-soft);
    }
    .messenger-shell {
        border: 1px solid rgba(63,114,175,0.12);
        border-radius: 28px;
        overflow: hidden;
        background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(243,248,252,0.94));
        box-shadow: 0 24px 50px rgba(31,61,96,0.11);
    }
    .messenger-split {
        display: grid;
        grid-template-columns: minmax(280px, 340px) minmax(0, 1fr);
        min-height: 620px;
    }
    .chat-list-panel {
        border-right: 1px solid rgba(63,114,175,0.12);
        background: linear-gradient(180deg, rgba(248,251,255,0.98), rgba(240,246,252,0.95));
        display: flex;
        flex-direction: column;
        min-height: 0;
    }
    .chat-list-head {
        padding: 20px;
        border-bottom: 1px solid rgba(63,114,175,0.10);
        display: grid;
        gap: 14px;
    }
    .chat-search {
        position: relative;
    }
    .chat-search .form-control {
        padding-left: 42px;
    }
    .chat-search-icon {
        position: absolute;
        left: 14px;
        top: 50%;
        transform: translateY(-50%);
        color: var(--text-soft);
        font-size: 14px;
    }
    .chat-list {
        display: grid;
        gap: 8px;
        padding: 12px;
        overflow-y: auto;
    }
    .chat-list-item {
        display: grid;
        gap: 6px;
        padding: 14px 16px;
        border-radius: 20px;
        text-decoration: none;
        color: inherit;
        background: linear-gradient(180deg, rgba(255,255,255,0.88), rgba(243,247,251,0.82));
        border: 1px solid transparent;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        box-shadow: 0 8px 22px rgba(31,61,96,0.05);
    }
    .chat-list-item:hover {
        transform: translateY(-1px);
        border-color: rgba(63,114,175,0.18);
        box-shadow: 0 12px 24px rgba(31,61,96,0.08);
    }
    .chat-list-item.active {
        background: linear-gradient(145deg, rgba(100,144,182,0.20), rgba(214,229,239,0.52));
        border-color: rgba(63,114,175,0.28);
    }
    .chat-list-top,
    .chat-list-bottom {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
    }
    .chat-list-name {
        font-weight: 700;
        color: var(--text-main);
    }
    .chat-list-preview {
        color: var(--text-soft);
        font-size: 13px;
        line-height: 1.5;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .chat-time {
        color: var(--text-soft);
        font-size: 12px;
        white-space: nowrap;
    }
    .chat-pane {
        display: grid;
        grid-template-rows: auto 1fr auto;
        min-height: 0;
        background:
            radial-gradient(circle at top right, rgba(137,183,221,0.16), transparent 30%),
            linear-gradient(180deg, rgba(251,253,255,0.98), rgba(241,246,251,0.96));
    }
    .chat-pane-head {
        padding: 18px 22px;
        border-bottom: 1px solid rgba(63,114,175,0.10);
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: center;
        flex-wrap: wrap;
    }
    .chat-thread-window {
        padding: 22px;
        overflow-y: auto;
        min-height: 0;
        display: grid;
        gap: 14px;
    }
    .chat-composer {
        padding: 18px 22px 22px;
        border-top: 1px solid rgba(63,114,175,0.10);
        background: rgba(255,255,255,0.72);
        backdrop-filter: blur(10px);
    }
    .chat-composer form {
        display: grid;
        gap: 12px;
    }
    .chat-empty {
        display: grid;
        place-items: center;
        min-height: 100%;
        text-align: center;
        color: var(--text-soft);
        padding: 40px 24px;
    }
    .chat-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        background: rgba(63,114,175,0.10);
        color: var(--primary-dark);
        font-size: 12px;
        font-weight: 600;
    }
    .messenger-topbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 16px;
        padding: 18px 22px;
        background:
            radial-gradient(circle at top left, rgba(255,255,255,0.22), transparent 26%),
            linear-gradient(145deg, #2a679d, #1d4f7b 62%, #153d62);
        color: #fff;
        flex-wrap: wrap;
    }
    .messenger-title {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .messenger-avatar {
        width: 44px;
        height: 44px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background: linear-gradient(180deg, rgba(255,255,255,0.28), rgba(255,255,255,0.12));
        font-weight: 700;
        font-size: 15px;
        color: #fff;
        border: 1px solid rgba(255,255,255,0.22);
        box-shadow: inset 0 1px 2px rgba(255,255,255,0.18);
    }
    .messenger-name {
        font-weight: 700;
        font-size: 16px;
    }
    .messenger-subtitle {
        font-size: 12px;
        opacity: 0.88;
    }
    .messenger-body {
        padding: 22px;
        background:
            radial-gradient(circle at top right, rgba(137,183,221,0.18), transparent 30%),
            linear-gradient(180deg, rgba(250,252,255,0.98), rgba(244,248,252,0.96));
    }
    .messenger-thread {
        display: grid;
        gap: 14px;
        max-height: 560px;
        overflow-y: auto;
        padding-right: 6px;
    }
    .messenger-thread::-webkit-scrollbar {
        width: 8px;
    }
    .messenger-thread::-webkit-scrollbar-thumb {
        background: rgba(63,114,175,0.25);
        border-radius: 999px;
    }
    .message-row {
        display: flex;
        width: 100%;
    }
    .message-row.left { justify-content: flex-start; }
    .message-row.right { justify-content: flex-end; }
    .message-row.center { justify-content: center; }
    .message-stack {
        display: grid;
        gap: 10px;
    }
    .chat-bubble {
        max-width: min(78%, 620px);
        padding: 14px 16px;
        border-radius: 22px;
        box-shadow: 0 10px 24px rgba(31, 61, 96, 0.08);
        border: 1px solid rgba(63,114,175,0.10);
        position: relative;
        line-height: 1.55;
    }
    .chat-bubble.student {
        background: linear-gradient(180deg, #ffffff, #f5f9ff);
        border-bottom-left-radius: 8px;
    }
    .chat-bubble.admin {
        background: linear-gradient(180deg, #4d88c7, #3f72af);
        color: #fff;
        border-bottom-right-radius: 8px;
        border-color: transparent;
    }
    .chat-bubble.system {
        background: linear-gradient(180deg, #fff8ed, #fff0dc);
        color: var(--text-main);
        max-width: min(92%, 760px);
        border-radius: 18px;
    }
    .chat-meta {
        display: flex;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 8px;
        font-size: 12px;
        color: var(--text-soft);
        flex-wrap: wrap;
    }
    .chat-bubble.admin .chat-meta,
    .chat-bubble.admin .chat-label {
        color: rgba(255,255,255,0.92);
    }
    .chat-label { font-weight: 700; color: var(--text-main); }
    body.dark .chat-label { color: #fff; }
    .message-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        padding-top: 14px;
        border-top: 1px solid rgba(63,114,175,0.10);
        margin-top: 14px;
    }
    .message-card {
        padding: 18px;
        border-radius: 22px;
        background: rgba(255,255,255,0.78);
        border: 1px solid rgba(63,114,175,0.10);
        box-shadow: 0 12px 24px rgba(31,61,96,0.06);
    }
    .composer-card {
        max-width: 760px;
        margin: 50px auto;
        border-radius: 26px;
        overflow: hidden;
    }
    .composer-head {
        padding: 20px 24px;
        background: linear-gradient(135deg, var(--primary), var(--secondary));
        color: #fff;
    }
    .composer-body {
        padding: 24px;
    }
    .composer-sticky {
        position: sticky;
        bottom: 0;
        background: rgba(255,255,255,0.96);
        padding-top: 16px;
        border-top: 1px solid rgba(63,114,175,0.10);
        backdrop-filter: blur(8px);
    }
    .send-row {
        display: flex;
        gap: 12px;
        align-items: flex-end;
        flex-wrap: wrap;
    }
    .send-row .form-control {
        flex: 1;
        min-height: 56px;
    }
    .send-icon {
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .status-tag {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        background: rgba(63,114,175,0.10);
        color: var(--primary-dark);
        font-size: 11px;
        font-weight: 700;
    }
    .preview-menu {
        position: relative;
    }
    .preview-menu summary {
        list-style: none;
    }
    .preview-menu summary::-webkit-details-marker {
        display: none;
    }
    .preview-panel {
        position: absolute;
        right: 0;
        top: calc(100% + 10px);
        width: 340px;
        max-width: 92vw;
        padding: 14px;
        border-radius: 18px;
        background: rgba(255,255,255,0.98);
        border: 1px solid rgba(63,114,175,0.12);
        box-shadow: 0 16px 32px rgba(31,61,96,0.16);
        z-index: 20;
    }
    .preview-list {
        display: grid;
        gap: 10px;
        margin-top: 10px;
    }
    .preview-item {
        padding: 10px 12px;
        border-radius: 14px;
        background: rgba(244,248,252,0.92);
        border: 1px solid rgba(63,114,175,0.10);
    }
    .preview-item strong {
        display: block;
        margin-bottom: 4px;
        color: var(--text-main);
    }
    body.dark,
    body.dark p,
    body.dark span,
    body.dark small,
    body.dark div,
    body.dark li,
    body.dark td,
    body.dark th,
    body.dark strong,
    body.dark a:not(.btn) {
        color: #eef6ff;
    }
    body.dark .table td {
        background: rgba(17, 25, 45, 0.82);
        border-bottom-color: rgba(137,183,221,0.12);
    }
    body.dark .table th {
        background: linear-gradient(135deg, #294d78, #3f72af);
        color: #fff;
    }
    body.dark .notification-meta,
    body.dark .soft-note,
    body.dark .messenger-subtitle,
    body.dark .chat-meta,
    body.dark .preview-item .soft-note {
        color: #bcd4ea !important;
    }
    body.dark .notification-card,
    body.dark .message-card,
    body.dark .mini-stat,
    body.dark .empty-state,
    body.dark .preview-panel,
    body.dark .preview-item,
    body.dark .messenger-shell,
    body.dark .messenger-body,
    body.dark .composer-body,
    body.dark .composer-sticky,
    body.dark .detail-view,
    body.dark .chart-box {
        background: #15233d !important;
        color: #eef6ff !important;
        border-color: rgba(137,183,221,0.14) !important;
    }
    body.dark .mini-stat strong,
    body.dark .notification-title,
    body.dark .preview-item strong {
        color: #ffffff !important;
    }
    body.dark .student-info-value {
        background: rgba(9, 18, 36, 0.92) !important;
        color: #f8fbff !important;
        border: 1px solid rgba(137,183,221,0.22);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
    }
    body.dark .section-kicker,
    body.dark .status-tag {
        background: rgba(137,183,221,0.16);
        color: #eef6ff;
    }
    body.dark .chat-bubble.student {
        background: linear-gradient(180deg, #223454, #1c2d49);
        color: #eef6ff;
        border-color: rgba(137,183,221,0.14);
    }
    body.dark .chat-bubble.system {
        background: linear-gradient(180deg, #3a2b17, #2f2414);
        color: #fff1d6;
        border-color: rgba(244,162,97,0.14);
    }
    body.dark .nav-tabs button {
        background: rgba(21,35,61,0.92);
        border-color: rgba(137,183,221,0.12);
        color: #d7eaff !important;
    }
    body.dark .nav-tabs button:hover {
        background: rgba(63,114,175,0.24);
        color: #ffffff !important;
    }
    body.dark .sidebar-card {
        background: linear-gradient(180deg, rgba(24,35,52,0.96), rgba(18,29,44,0.92)) !important;
        border-color: rgba(128,155,184,0.16);
    }
    body.dark .sidebar-tabs button {
        background: linear-gradient(180deg, rgba(29,43,63,0.96), rgba(21,34,50,0.92));
        color: #d8e5f1 !important;
        border-color: rgba(101,130,163,0.18);
    }
    body.dark .sidebar-tabs button.active {
        background: linear-gradient(145deg, #315e8b, #21486d) !important;
        color: #fff !important;
    }
    body.dark .sidebar-tabs .sidebar-link-button {
        background: linear-gradient(180deg, rgba(29,43,63,0.96), rgba(21,34,50,0.92));
        color: #d8e5f1 !important;
        border-color: rgba(101,130,163,0.18);
    }
    body.dark .header-action-group .btn,
    body.dark .header-action-group summary {
        background: linear-gradient(180deg, rgba(29,43,63,0.96), rgba(21,34,50,0.92)) !important;
        color: #d8e5f1 !important;
        border-color: rgba(101,130,163,0.18);
    }
    body.dark .form-control::placeholder,
    body.dark textarea::placeholder {
        color: #b8cae0;
    }
    body.dark .alert-success {
        background: linear-gradient(135deg, #1b4038, #22534a);
        color: #d9fff3;
        border-color: #2a6b5f;
    }
    body.dark .alert-danger {
        background: linear-gradient(135deg, #4b2330, #5d2838);
        color: #ffdce4;
        border-color: #7d3d4f;
    }
    body.dark .alert-info {
        background: linear-gradient(135deg, #1e3d56, #264c6b);
        color: #e0f4ff;
        border-color: #376b93;
    }
    body.dark .alert-warning {
        background: linear-gradient(135deg, #4f3d16, #624b1a);
        color: #fff3cd;
        border-color: #8e6f2d;
    }
</style>
<script>
    function passwordIcon(isVisible) {
        if (isVisible) {
            return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6-10-6-10-6Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>';
        }

        return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.6-6 10-6c2.1 0 3.9.65 5.42 1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 12s-3.6 6-10 6c-2.1 0-3.9-.65-5.42-1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.88 9.88A3 3 0 0 1 14.12 14.12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    }

    function togglePassword(inputId, button) {
        const input = document.getElementById(inputId);
        if (!input || !button) {
            return;
        }

        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        button.innerHTML = passwordIcon(isHidden);
        button.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
        button.setAttribute('title', isHidden ? 'Hide password' : 'Show password');
    }
</script>
"""

LOGIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Login</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
</head>
<body>
    <div class="container">
        <!-- Logo Section -->
        <div class="logo-container">
            <div class="logo">
                <span class="logo-text">ST</span>
            </div>
            <div class="logo-subtitle">STUDENT & FACULTY MANAGEMENT</div>
        </div>
        
        <div class="login-container">
            <div class="card" style="border-radius: 20px; box-shadow: 0 15px 50px rgba(0,0,0,0.3);">
                <div class="login-header">
                    <h1>Welcome to StudTech!</h1>
                    <p style="color: #666; margin-top: 10px;">Login to your account</p>
                </div>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                <form method="POST" action="{{ url_for('login') }}">
                    <div class="form-group">
                        <label>Login As:</label>
                        <select name="user_type" class="form-select" id="userType" onchange="toggleFields()">
                            <option value="student">Student</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Username</label>
                        <input type="text" name="username" class="form-control" placeholder="Enter username" required>
                    </div>
                    <div class="form-group">
                        <label>Password</label>
                        <div class="password-group">
                            <input type="password" id="loginPass" name="password" class="form-control" placeholder="Enter password" required>
                            <button type="button" class="password-toggle-btn" aria-label="Show password" title="Show password" onclick="togglePassword('loginPass', this)"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.6-6 10-6c2.1 0 3.9.65 5.42 1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 12s-3.6 6-10 6c-2.1 0-3.9-.65-5.42-1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.88 9.88A3 3 0 0 1 14.12 14.12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary w-100" style="padding: 14px; font-size: 16px;">Login</button>
                </form>
                <div style="margin-top: 20px; text-align: center;">
                    <a href="{{ url_for('about_system') }}" style="color: #3f72af; font-weight: 500; display: inline-block; margin-bottom: 10px;">About the System</a><br>
                    <a href="{{ url_for('register') }}" style="color: #667eea; font-weight: 500;">Don't have an account? Register here</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

REGISTER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Register</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
</head>
<body>
    <div class="container">
        <div class="row justify-content-center">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">Student Registration</div>
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            {% for category, message in messages %}
                                <div class="alert alert-{{ category }}">{{ message }}</div>
                            {% endfor %}
                        {% endif %}
                    {% endwith %}
                    
                    <form method="POST" action="{{ url_for('register') }}">
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Student ID</label>
                                <input type="text" name="student_id" class="form-control" required>
                            </div>
                            <div class="form-group">
                                <label>Full Name</label>
                                <input type="text" name="fullname" class="form-control" required>
                            </div>
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Age</label>
                                <input type="number" name="age" class="form-control" required>
                            </div>
                            <div class="form-group">
                                <label>Gender</label>
                                <select name="gender" class="form-select" required>
                                    <option value="">Select Gender</option>
                                    <option value="Male">Male</option>
                                    <option value="Female">Female</option>
                                </select>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Program</label>
                            <select name="program" class="form-select" required>
                                <option value="">Select Program</option>
                                <option value="BCSC">BCSC</option>
                                <option value="FoodTech">FoodTech</option>
                                <option value="BindTech">BindTech</option>
                                <option value="Midwifery">Midwifery</option>
                                <option value="BEED">BEED</option>
                                <option value="BSF">BSF</option>
                            </select>
                        </div>
                        <div class="grid-2">
                            <div class="form-group">
                                <label>Username</label>
                                <input type="text" name="username" class="form-control" required>
                            </div>
                            <div class="form-group">
                                <label>Password</label>
                                <div class="password-group">
                                    <input type="password" id="regPass" name="password" class="form-control" required>
                                    <button type="button" class="password-toggle-btn" aria-label="Show password" title="Show password" onclick="togglePassword('regPass', this)"><svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M2 12s3.6-6 10-6c2.1 0 3.9.65 5.42 1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M22 12s-3.6 6-10 6c-2.1 0-3.9-.65-5.42-1.58" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M9.88 9.88A3 3 0 0 1 14.12 14.12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 3l18 18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
                                </div>
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Register</button>
                    </form>
                    <div style="margin-top: 15px; text-align: center;">
                        <a href="{{ url_for('login') }}" style="color: #667eea;">Back to Login</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""

ADMIN_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Admin Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    """ + BASE_CSS + """
</head>
<body class="{{ theme }}">
    <div class="container">
        <div class="dashboard-layout">
            <aside class="dashboard-sidebar">
                <div class="sidebar-card">
                    <div class="sidebar-meta">
                        <div class="sidebar-brand">StudTech</div>
                        <div class="sidebar-subtitle">Admin control panel for student records, schedules, requests, notifications, and communication.</div>
                    </div>
                    <div class="sidebar-title">Admin Menu</div>
                    <div class="nav-tabs sidebar-tabs">
                        <button class="active" onclick="showTab('overview')">📊 Statistical Overview</button>
                        <button onclick="showTab('addstudent')">➕ Add Student</button>
                        <button onclick="showTab('students')">📋 Student List</button>
                        <button onclick="showTab('announcement')">📢 Announcements</button>
                        <button onclick="showTab('requests')">📝 Student Requests</button>
                        <button onclick="showTab('schedule')">📅 Schedule</button>
                        <button onclick="showTab('notifications')">🔔 Notifications {% if unread_admin_notifications > 0 %}<span class="badge badge-new">{{ unread_admin_notifications }}</span>{% endif %}</button>
                    </div>
                    <div class="sidebar-spacer"></div>
                    <div class="nav-tabs sidebar-tabs sidebar-footer-tabs">
                        <button onclick="showTab('about')">ℹ️ About</button>
                        <a href="{{ url_for('logout') }}" class="sidebar-link-button">↩ Logout</a>
                    </div>
                </div>
            </aside>
            <div class="dashboard-main">
        <div class="header-bar">
            <h1 style="color: white;">StudTech - Admin Dashboard</h1>
            <div class="header-action-group">
                <details class="preview-menu">
                    <summary class="btn btn-primary">🔔 Notifications {% if unread_admin_notifications > 0 %}<span class="badge badge-new">{{ unread_admin_notifications }}</span>{% endif %}</summary>
                    <div class="preview-panel">
                        <strong>Recent Alerts</strong>
                        <div class="preview-list">
                            {% for note in admin_notifications[:3] %}
                            <div class="preview-item">
                                <strong>{{ note.title }}</strong>
                                <div>{{ note.message }}</div>
                                <div class="soft-note">{{ note.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                            </div>
                            {% else %}
                            <div class="preview-item">No recent alerts</div>
                            {% endfor %}
                        </div>
                    </div>
                </details>
                <a href="{{ url_for('view_messages') }}" class="btn btn-info">📬 Messages {% if total_notifications > 0 %}<span class="badge badge-new">{{ total_notifications }}</span>{% endif %}</a>
                <a href="{{ url_for('admin_settings') }}" class="btn btn-warning">⚙️ Settings</a>
            </div>
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="card dashboard-panel">

            <div id="overview" class="tab-content active">
                <div class="section-header">
                    <div>
                        <div class="section-kicker">Analytics</div>
                        <h3>📊 Statistical Overview</h3>
                    </div>
                </div>
                <div class="charts-container">
                    <div class="chart-box">
                        <h5 style="text-align: center;">Gender Distribution</h5>
                        <canvas id="genderChart"></canvas>
                    </div>
                    <div class="chart-box">
                        <h5 style="text-align: center;">Students by Program</h5>
                        <canvas id="programChart"></canvas>
                    </div>
                    <div class="chart-box">
                        <h5 style="text-align: center;">Monthly Visits</h5>
                        <canvas id="visitsChart"></canvas>
                    </div>
                </div>
            </div>

            <!-- Add Student Tab -->
            <div id="addstudent" class="tab-content">
                <h3>Add New Student Record</h3>
                <form method="POST" action="{{ url_for('add_student') }}">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Student ID</label>
                            <input type="text" name="student_id" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label>Full Name</label>
                            <input type="text" name="fullname" class="form-control" required>
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Program</label>
                            <select name="program" class="form-select" required>
                                <option value="">Select Program</option>
                                <option value="BCSC">BCSC</option>
                                <option value="FoodTech">FoodTech</option>
                                <option value="BindTech">BindTech</option>
                                <option value="Midwifery">Midwifery</option>
                                <option value="BEED">BEED</option>
                                <option value="BSF">BSF</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Gender</label>
                            <select name="gender" class="form-select" required>
                                <option value="">Select Gender</option>
                                <option value="Male">Male</option>
                                <option value="Female">Female</option>
                            </select>
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Visit Date</label>
                            <input type="date" name="visit_date" class="form-control" required>
                        </div>
                        <div class="form-group">
                            <label>Visit Time</label>
                            <input type="time" name="visit_time" class="form-control" required>
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Purpose</label>
                        <textarea name="purpose" class="form-control" rows="3" placeholder="Purpose of visit (e.g., enrollment, consultation, document submission)"></textarea>
                    </div>
                    <button type="submit" class="btn btn-success">➕ Add Student</button>
                </form>
            </div>

            <!-- Student List Tab -->
            <div id="students" class="tab-content">
                <h3>Student Records</h3>
                <form method="GET" action="{{ url_for('admin_dashboard') }}" class="mb-3">
                    <div class="grid-3">
                        <div class="form-group">
                            <label>Filter by Month</label>
                            <input type="month" name="filter_month" class="form-control" value="{{ selected_month }}">
                        </div>
                        <div class="form-group align-end-group">
                            <button type="submit" class="btn btn-primary">🔍 Filter</button>
                        </div>
                        <div class="form-group align-end-group">
                            <button type="button" onclick="printTable()" class="btn btn-success">🖨️ Print</button>
                        </div>
                    </div>
                </form>

                <div class="table-responsive">
                    <table class="table" id="studentTable">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Full Name</th>
                                <th>Program</th>
                                <th>Gender</th>
                                <th>Visit Date</th>
                                <th>Visit Time</th>
                                <th>Purpose</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for s in students %}
                            <tr>
                                <td>{{ s.student_id }}</td>
                                <td>{{ s.fullname }}</td>
                                <td>{{ s.program }}</td>
                                <td>{{ s.gender }}</td>
                                <td>{{ s.visit_date }}</td>
                                <td>{{ s.visit_time }}</td>
                                <td>{{ s.purpose or 'N/A' }}</td>
                                <td>
                                    <a href="{{ url_for('view_student', student_id=s.student_id) }}" class="btn btn-info btn-sm">👁️ View</a>
                                    <a href="{{ url_for('delete_student', student_id=s.student_id) }}" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?')">🗑️ Delete</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Announcements Tab -->
            <div id="announcement" class="tab-content">
                <h3>Create Announcement (For All)</h3>
                <form method="POST" action="{{ url_for('create_announcement') }}" class="mb-4">
                    <div class="form-group">
                        <label>Title</label>
                        <input type="text" name="title" class="form-control" placeholder="Announcement Title" required>
                    </div>
                    <div class="form-group">
                        <label>Message</label>
                        <textarea name="message" class="form-control" placeholder="Enter announcement details..." rows="4" required></textarea>
                    </div>
                    <button type="submit" class="btn btn-success">📢 Post Announcement</button>
                </form>

                <h4>Existing Announcements</h4>
                {% for a in announcements %}
                    <div class="alert alert-info">
                        <strong>{{ a.title }}</strong><br>
                        {{ a.message }}<br>
                        <small>{{ a.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                    </div>
                {% endfor %}
            </div>

            <!-- Requests Tab -->
            <div id="requests" class="tab-content">
                <div class="section-kicker">Request Center</div>
                <h3>Student Requests</h3>
                <p style="margin-bottom: 15px; color: #666;">Accepting a request automatically creates a student schedule entry and saves the accepted request as a visit record.</p>
                {% if student_requests %}
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Full Name</th>
                                <th>Student ID</th>
                                <th>Purpose</th>
                                <th>Schedule</th>
                                <th>Status</th>
                                <th>Rejection Reason</th>
                                <th>Date Requested</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for req in student_requests %}
                            <tr>
                                <td>{{ req.fullname }}</td>
                                <td>{{ req.student_id }}</td>
                                <td>{{ req.purpose }}</td>
                                <td>{{ req.schedule }}</td>
                                <td>
                                    <span class="status-pill {% if req.status == 'Accepted' %}accepted{% elif req.status == 'Rejected' %}rejected{% else %}pending{% endif %}">
                                        {{ req.status }}
                                    </span>
                                </td>
                                <td>{{ req.rejection_reason or 'N/A' }}</td>
                                <td>{{ req.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                                <td>
                                    {% if req.status == 'Pending' %}
                                    <form method="POST" action="{{ url_for('update_request_status', request_id=req.id) }}" style="display: inline-block;">
                                        <input type="hidden" name="action" value="accept">
                                        <button type="submit" class="btn btn-success btn-sm">Accept</button>
                                    </form>
                                    <form method="POST" action="{{ url_for('update_request_status', request_id=req.id) }}" style="display: inline-grid; gap: 8px; min-width: 220px;">
                                        <input type="hidden" name="action" value="reject">
                                        <textarea name="rejection_reason" class="form-control" rows="2" placeholder="Reason for rejection" required></textarea>
                                        <button type="submit" class="btn btn-danger btn-sm">Reject</button>
                                    </form>
                                    {% else %}
                                    <span style="color: #666;">Completed</span>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-warning">No student requests submitted yet.</div>
                {% endif %}
            </div>

            <div id="notifications" class="tab-content">
                <div class="split-row">
                    <div>
                        <div class="section-kicker">Live Alerts</div>
                        <h3>Admin Notifications</h3>
                    </div>
                    <a href="{{ url_for('mark_all_notifications_read') }}?panel=admin" class="btn btn-info btn-sm">Mark All Read</a>
                </div>
                <div class="subtle-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 18px;">
                    <div class="mini-stat"><strong>{{ unread_admin_notifications }}</strong>Unread alerts</div>
                    <div class="mini-stat"><strong>{{ student_requests|length }}</strong>Total requests</div>
                    <div class="mini-stat"><strong>{{ schedules|length }}</strong>Schedules posted</div>
                </div>
                {% if admin_notifications %}
                <div class="notification-feed">
                    {% for note in admin_notifications %}
                    <div class="notification-card">
                        <div class="notification-top">
                            <div class="notification-title">{{ note.title }}</div>
                            <div class="notification-meta">{{ note.sender }} • {{ note.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                        </div>
                        <div>{{ note.message }}</div>
                        <div class="soft-note">
                            {% if note.status_label %}Status: {{ note.status_label }} • {% endif %}
                            Category: {{ note.category|title }}
                            {% if not note.is_read %} • New{% endif %}
                        </div>
                        <div class="card-actions">
                            <a href="{{ url_for('delete_notification', notification_id=note.id, panel='admin') }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete this notification?')">Delete</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="empty-state">No notifications yet. Request submissions and schedule actions will appear here automatically.</div>
                {% endif %}
            </div>

            <!-- Schedule Tab -->
            <div id="schedule" class="tab-content">
                <div class="dashboard-split">
                    <div>
                        <div class="section-kicker">Scheduling</div>
                        <h3>Create Schedule (For Student)</h3>
                        <form method="POST" action="{{ url_for('create_schedule') }}" class="mb-4">
                            <div class="grid-2">
                                <div class="form-group">
                                    <label>Student ID</label>
                                    <input type="text" name="student_id" class="form-control" placeholder="Student ID" required>
                                </div>
                                <div class="form-group">
                                    <label>Message</label>
                                    <input type="text" name="message" class="form-control" placeholder="Schedule Message" required>
                                </div>
                            </div>
                            <button type="submit" class="btn btn-success">📅 Post Schedule</button>
                        </form>
                    </div>
                    <div class="mini-stat">
                        <span class="section-kicker">Sync</span>
                        <strong>{{ schedules|length }}</strong>
                        Schedule entries are mirrored to the student schedule panel and produce notifications automatically.
                    </div>
                </div>

                <h4>Existing Schedules</h4>
                {% for s in schedules %}
                    <div class="notification-card">
                        <div class="notification-top">
                            <div class="notification-title">Student ID: {{ s.student_id }}</div>
                            <div class="notification-meta">{{ s.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                        </div>
                        <div>{{ s.message }}</div>
                    </div>
                {% endfor %}
            </div>

            <div id="about" class="tab-content">
                <div class="section-header">
                    <div>
                        <div class="section-kicker">System Overview</div>
                        <h3>ℹ️ About StudTech</h3>
                    </div>
                </div>
                <div class="subtle-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 24px;">
                    <div class="mini-stat"><strong>Student Records</strong>Centralized student registration details and visit tracking for faster monitoring.</div>
                    <div class="mini-stat"><strong>Request Workflow</strong>Students can submit requests while admins review, approve, or reject them in one place.</div>
                    <div class="mini-stat"><strong>Schedules & Alerts</strong>Schedules, announcements, and notifications are shared quickly across the system.</div>
                    <div class="mini-stat"><strong>Messaging</strong>Messenger-style communication keeps each student conversation organized in one thread.</div>
                </div>
                <div class="grid-2">
                    <div class="notification-card">
                        <div class="notification-title">What The System Does</div>
                        <p style="margin-top: 12px;">StudTech is a student support platform for managing records, announcements, schedules, requests, notifications, and direct communication between students and admin.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">Admin Experience</div>
                        <p style="margin-top: 12px;">Admin can add and manage student data, review requests, publish announcements, post schedules, monitor notifications, and respond to students from a threaded inbox.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">Student Experience</div>
                        <p style="margin-top: 12px;">Students can view their own records, read updates, track requests, check schedules, receive notifications, and message admin through their personal conversation view.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">Why It Helps</div>
                        <p style="margin-top: 12px;">The system reduces scattered communication, keeps actions organized by student, and makes support workflows easier to track for both admin and students.</p>
                    </div>
                </div>
            </div>
        </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let adminHasUnsavedChanges = false;

        function trackFormChanges() {
            document.querySelectorAll('form input, form textarea, form select').forEach(field => {
                field.addEventListener('input', function() {
                    adminHasUnsavedChanges = true;
                });
                field.addEventListener('change', function() {
                    adminHasUnsavedChanges = true;
                });
            });

            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function() {
                    adminHasUnsavedChanges = false;
                });
            });
        }

        function scheduleAdminRefresh() {
            setTimeout(function() {
                const activeElement = document.activeElement;
                const isTyping = activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeElement.tagName);
                if (!adminHasUnsavedChanges && !isTyping) {
                    window.location.reload();
                    return;
                }
                scheduleAdminRefresh();
            }, 15000);
        }

        function showTab(tabId, button) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-tabs button').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            const targetButton = button || event.currentTarget;
            if (targetButton) {
                targetButton.classList.add('active');
            }
            localStorage.setItem('adminActiveTab', tabId);
        }

        document.addEventListener('DOMContentLoaded', function() {
            const activeTab = localStorage.getItem('adminActiveTab');
            if (activeTab) {
                const button = Array.from(document.querySelectorAll('.nav-tabs button'))
                    .find(btn => btn.getAttribute('onclick') && btn.getAttribute('onclick').includes("'" + activeTab + "'"));
                if (button && document.getElementById(activeTab)) {
                    showTab(activeTab, button);
                }
            }

            trackFormChanges();
            scheduleAdminRefresh();
        });

        function printTable() {
            window.print();
        }

        // Gender Chart
        new Chart(document.getElementById('genderChart'), {
            type: 'pie',
            data: {
                labels: ['Male', 'Female'],
                datasets: [{ data: [{{ male_count }}, {{ female_count }}], backgroundColor: ['#3498db', '#e74c3c'] }]
            }
        });

        // Program Chart
        new Chart(document.getElementById('programChart'), {
            type: 'bar',
            data: {
                labels: {{ program_labels | safe }},
                datasets: [{ label: 'Students', data: {{ program_values | safe }}, backgroundColor: '#667eea' }]
            }
        });

        // Visits Chart
        new Chart(document.getElementById('visitsChart'), {
            type: 'line',
            data: {
                labels: {{ month_labels | safe }},
                datasets: [{ label: 'Visits', data: {{ visit_values | safe }}, borderColor: '#2ecc71', fill: false }]
            }
        });
    </script>
</body>
</html>
"""

VIEW_STUDENT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Student Details</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
</head>
<body>
    <div class="container">
        <div class="card detail-view">
            <a href="{{ url_for('admin_dashboard') }}" class="btn btn-primary back-btn no-print">⬅️ Back to List</a>
            
            <h2 style="text-align: center; color: #667eea; margin-bottom: 30px;">Student Details</h2>
            
            <div style="margin-bottom: 20px;" class="no-print">
                <button onclick="window.print()" class="btn btn-success">🖨️ Print Student Details</button>
            </div>
            
            <div class="grid-2">
                <div class="form-group">
                    <label>Student ID</label>
                    <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.student_id }}</p>
                </div>
                <div class="form-group">
                    <label>Full Name</label>
                    <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.fullname }}</p>
                </div>
            </div>
            <div class="grid-2">
                <div class="form-group">
                    <label>Program</label>
                    <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.program }}</p>
                </div>
                <div class="form-group">
                    <label>Gender</label>
                    <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.gender }}</p>
                </div>
            </div>
            <div class="grid-2">
                <div class="form-group">
                    <label>Visit Date</label>
                    <p style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.visit_date }}</p>
                </div>
                <div class="form-group">
                    <label>Visit Time</label>
                    <p style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.visit_time }}</p>
                </div>
            </div>
            {% if student.purpose %}
            <div class="form-group">
                <label>Purpose of Visit</label>
                <p style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.purpose }}</p>
            </div>
            {% endif %}
            <div class="form-group">
                <label>Created At</label>
                <p style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.created_at.strftime('%Y-%m-%d %H:%M:%S') }}</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

STUDENT_DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Student Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
</head>
<body class="{{ theme }}">
    <div class="container">
        <div class="dashboard-layout">
            <aside class="dashboard-sidebar">
                <div class="sidebar-card">
                    <div class="sidebar-meta">
                        <div class="sidebar-brand">StudTech</div>
                        <div class="sidebar-subtitle">Student portal for announcements, requests, schedules, notifications, and admin messaging.</div>
                    </div>
                    <div class="sidebar-title">Student Menu</div>
                    <div class="nav-tabs sidebar-tabs">
                        <button class="active" onclick="showTab('profile')">
                            👤 My Profile
                        </button>
                        <button onclick="showTab('announcements')">
                            📢 Announcements {% if unread_announcements > 0 %}<span class="badge badge-new">{{ unread_announcements }}</span>{% endif %}
                        </button>
                        <button onclick="showTab('requests')">
                            📝 My Requests {% if pending_requests > 0 %}<span class="badge badge-new">{{ pending_requests }}</span>{% endif %}
                        </button>
                        <button onclick="showTab('notifications')">
                            🔔 Notifications {% if unread_student_notifications > 0 %}<span class="badge badge-new">{{ unread_student_notifications }}</span>{% endif %}
                        </button>
                        <button onclick="showTab('schedules')">
                            📅 My Schedules {% if unread_schedules > 0 %}<span class="badge badge-new">{{ unread_schedules }}</span>{% endif %}
                        </button>
                        <button onclick="showTab('messages')">
                            📬 My Messages {% if unread_messages > 0 %}<span class="badge badge-new">{{ unread_messages }}</span>{% endif %}
                        </button>
                    </div>
                    <div class="sidebar-spacer"></div>
                    <div class="nav-tabs sidebar-tabs sidebar-footer-tabs">
                        <button onclick="showTab('about')">ℹ️ About</button>
                        <a href="{{ url_for('logout') }}" class="sidebar-link-button">↩ Logout</a>
                    </div>
                </div>
            </aside>
            <div class="dashboard-main">
        <div class="header-bar">
            <h1 style="color: white;">StudTech - Student Dashboard</h1>
            <div class="header-action-group">
                <details class="preview-menu">
                    <summary class="btn btn-primary">🔔 Notifications {% if unread_student_notifications > 0 %}<span class="badge badge-new">{{ unread_student_notifications }}</span>{% endif %}</summary>
                    <div class="preview-panel">
                        <strong>Recent Alerts</strong>
                        <div class="preview-list">
                            {% for note in student_notifications[:3] %}
                            <div class="preview-item">
                                <strong>{{ note.title }}</strong>
                                <div>{{ note.message }}</div>
                                <div class="soft-note">{{ note.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                            </div>
                            {% else %}
                            <div class="preview-item">No recent alerts</div>
                            {% endfor %}
                        </div>
                    </div>
                </details>
                <a href="{{ url_for('contact_admin') }}" class="btn btn-info">📬 Contact Admin {% if unread_messages > 0 %}<span class="badge badge-new">{{ unread_messages }}</span>{% endif %}</a>
                <a href="{{ url_for('student_settings') }}" class="btn btn-warning settings-btn">⚙️ Settings</a>
            </div>
        </div>

        <div class="welcome-msg">
            Welcome, {{ student.fullname }}! 🎉
        </div>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}
        <div class="card dashboard-panel">

            <div id="profile" class="tab-content active">
                <div class="section-header">
                    <div>
                        <div class="section-kicker">Student Account</div>
                        <h3>👤 My Profile</h3>
                    </div>
                </div>
                <div class="card" style="box-shadow: none; margin-bottom: 0;">
                    <div class="card-header">📝 Your Registration Information</div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Student ID</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.student_id }}</p>
                        </div>
                        <div class="form-group">
                            <label>Full Name</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.fullname }}</p>
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Age</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.age }}</p>
                        </div>
                        <div class="form-group">
                            <label>Gender</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.gender }}</p>
                        </div>
                    </div>
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Program</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.program }}</p>
                        </div>
                        <div class="form-group">
                            <label>Username</label>
                            <p class="student-info-value" style="padding: 10px; background: #f5f5f5; border-radius: 5px;">{{ student.username }}</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Announcements Tab -->
            <div id="announcements" class="tab-content">
                <div class="section-header">
                    <h3>📢 Announcements</h3>
                    <div>
                        <a href="{{ url_for('mark_all_announcements_read') }}" class="btn btn-info btn-sm">Mark All Read</a>
                    </div>
                </div>
                {% if announcements %}
                    {% for a in announcements %}
                        <div class="alert alert-info" style="{% if not a.is_read %}border-left: 4px solid #e74c3c;{% endif %}">
                            <div class="split-row align-start">
                                <div>
                                    <strong>{{ a.title }}</strong><br>
                                    {{ a.message }}<br>
                                    <small class="text-muted">Posted: {{ a.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                                    {% if not a.is_read %}<span class="badge badge-new">New</span>{% endif %}
                                </div>
                                <div class="inline-actions">
                                    {% if not a.is_read %}
                                    <a href="{{ url_for('mark_announcement_read', announcement_id=a.id) }}" class="btn btn-warning btn-sm">Mark Read</a>
                                    {% endif %}
                                    <a href="{{ url_for('delete_announcement', announcement_id=a.id) }}" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?')">Delete</a>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="alert alert-warning">No announcement made</div>
                {% endif %}
            </div>

            <!-- Requests Tab -->
            <div id="requests" class="tab-content">
                <div class="section-kicker">Track Progress</div>
                <h3>📝 My Requests</h3>
                <form method="POST" action="{{ url_for('create_request') }}" class="mb-4">
                    <div class="grid-2">
                        <div class="form-group">
                            <label>Purpose</label>
                            <textarea name="purpose" class="form-control" rows="3" placeholder="State the reason for your request" required></textarea>
                        </div>
                        <div class="form-group">
                            <label>Preferred Schedule</label>
                            <input type="date" name="schedule" class="form-control" required>
                        </div>
                    </div>
                    <button type="submit" class="btn btn-primary">Submit Request</button>
                </form>

                {% if student_requests %}
                <div class="table-responsive">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Full Name</th>
                                <th>Purpose</th>
                                <th>Schedule</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for req in student_requests %}
                            <tr>
                                <td>{{ req.fullname }}</td>
                                <td>{{ req.purpose }}</td>
                                <td>{{ req.schedule }}</td>
                                <td>
                                    <span class="status-pill {% if req.status == 'Accepted' %}accepted{% elif req.status == 'Rejected' %}rejected{% else %}pending{% endif %}">
                                        {{ req.status }}
                                    </span>
                                    {% if req.status == 'Rejected' and req.rejection_reason %}
                                    <div class="soft-note">Rejected - Reason: {{ req.rejection_reason }}</div>
                                    {% endif %}
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% else %}
                <div class="alert alert-warning">No requests yet. Submit one above to start tracking.</div>
                {% endif %}
                <div class="alert alert-info">This page refreshes automatically so request decisions from the admin side appear without a manual refresh.</div>
            </div>

            <div id="notifications" class="tab-content">
                <div class="split-row">
                    <div>
                        <div class="section-kicker">Updates</div>
                        <h3>🔔 Notifications</h3>
                    </div>
                    <a href="{{ url_for('mark_all_notifications_read') }}?panel=student" class="btn btn-info btn-sm">Mark All Read</a>
                </div>
                <div class="subtle-grid" style="grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); margin-top: 18px;">
                    <div class="mini-stat"><strong>{{ unread_student_notifications }}</strong>Unread notifications</div>
                    <div class="mini-stat"><strong>{{ student_requests|length }}</strong>Tracked requests</div>
                    <div class="mini-stat"><strong>{{ schedules|length }}</strong>Visible schedules</div>
                </div>
                {% if student_notifications %}
                <div class="notification-feed">
                    {% for note in student_notifications %}
                    <div class="notification-card">
                        <div class="notification-top">
                            <div class="notification-title">{{ note.title }}</div>
                            <div class="notification-meta">{{ note.sender }} • {{ note.created_at.strftime('%Y-%m-%d %H:%M') }}</div>
                        </div>
                        <div>{{ note.message }}</div>
                        <div class="soft-note">
                            {% if note.status_label %}Status: {{ note.status_label }} • {% endif %}
                            Category: {{ note.category|title }}
                            {% if not note.is_read %} • New{% endif %}
                        </div>
                        <div class="card-actions">
                            <a href="{{ url_for('delete_notification', notification_id=note.id, panel='student') }}" class="btn btn-danger btn-sm" onclick="return confirm('Delete this notification?')">Delete</a>
                        </div>
                    </div>
                    {% endfor %}
                </div>
                {% else %}
                <div class="empty-state">No notifications yet. Request updates and schedules will appear here automatically.</div>
                {% endif %}
            </div>

            <!-- Schedules Tab -->
            <div id="schedules" class="tab-content">
                <div class="section-header">
                    <h3>📅 My Schedules</h3>
                    <div>
                        <a href="{{ url_for('mark_all_schedules_read') }}" class="btn btn-info btn-sm">Mark All Read</a>
                    </div>
                </div>
                {% if schedules %}
                    {% for s in schedules %}
                        <div class="alert alert-success" style="{% if not s.is_read %}border-left: 4px solid #e74c3c;{% endif %}">
                            <div class="split-row align-start">
                                <div>
                                    <strong>Message:</strong> {{ s.message }}<br>
                                    <small class="text-muted">Posted: {{ s.created_at.strftime('%Y-%m-%d %H:%M') }}</small>
                                    {% if not s.is_read %}<span class="badge badge-new">New</span>{% endif %}
                                </div>
                                <div class="inline-actions">
                                    {% if not s.is_read %}
                                    <a href="{{ url_for('mark_schedule_read', schedule_id=s.id) }}" class="btn btn-warning btn-sm">Mark Read</a>
                                    {% endif %}
                                    <a href="{{ url_for('delete_schedule', schedule_id=s.id) }}" class="btn btn-danger btn-sm" onclick="return confirm('Are you sure?')">Delete</a>
                                </div>
                            </div>
                        </div>
                    {% endfor %}
                {% else %}
                    <div class="alert alert-warning">No schedule made</div>
                {% endif %}
            </div>

            <!-- Messages Tab -->
            <div id="messages" class="tab-content">
                <div class="section-header">
                    <div>
                        <div class="section-kicker">Conversation View</div>
                        <h3>📬 My Messages</h3>
                    </div>
                    <a href="{{ url_for('contact_admin') }}" class="btn btn-primary">Open Full Chat</a>
                </div>
                {% if student_messages %}
                    <div class="messenger-shell">
                        <div class="messenger-topbar">
                            <div class="messenger-title">
                                <div class="messenger-avatar">AD</div>
                                <div>
                                    <div class="messenger-name">Admin Support</div>
                                    <div class="messenger-subtitle">Messenger-style conversation history</div>
                                </div>
                            </div>
                            <div class="messenger-subtitle">{{ student_messages|length }} total message(s)</div>
                        </div>
                        <div class="messenger-body">
                            <div class="messenger-thread" id="studentDashboardThread">
                            {% for m in student_messages %}
                                <div class="message-row {% if m.sender_type == 'admin' %}left{% else %}right{% endif %}">
                                    <div class="chat-bubble {% if m.sender_type == 'admin' %}admin{% else %}student{% endif %}">
                                        <div class="chat-meta">
                                            <span class="chat-label">{% if m.sender_type == 'admin' %}Admin{% else %}You{% endif %}</span>
                                            <span>
                                                {% if m.sender_type == 'admin' and not m.is_read %}
                                                <span class="status-tag">New</span>
                                                {% else %}
                                                <span class="status-tag">{% if m.is_read %}Seen{% else %}Sent{% endif %}</span>
                                                {% endif %}
                                                {{ m.timestamp.strftime('%b %d, %I:%M %p') }}
                                            </span>
                                        </div>
                                        <div>{{ m.message }}</div>
                                    </div>
                                </div>
                            {% endfor %}
                            </div>
                        </div>
                    </div>
                {% else %}
                    <div class="alert alert-warning">No messages sent yet. Open the full chat to start your conversation with admin.</div>
                {% endif %}
            </div>

            <div id="about" class="tab-content">
                <div class="section-header">
                    <div>
                        <div class="section-kicker">System Overview</div>
                        <h3>ℹ️ About StudTech</h3>
                    </div>
                </div>
                <div class="subtle-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 24px;">
                    <div class="mini-stat"><strong>Announcements</strong>Students receive important updates from admin in one visible panel.</div>
                    <div class="mini-stat"><strong>Requests</strong>Request submissions and status tracking are organized so students can follow progress easily.</div>
                    <div class="mini-stat"><strong>Schedules & Notifications</strong>System notices help students stay updated on appointments, schedules, and changes.</div>
                    <div class="mini-stat"><strong>Private Messaging</strong>Each student sees only their own conversation with admin in a secure thread.</div>
                </div>
                <div class="grid-2">
                    <div class="notification-card">
                        <div class="notification-title">What The System Does</div>
                        <p style="margin-top: 12px;">StudTech is a student portal that combines records, announcements, requests, schedules, notifications, and messaging in one dashboard.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">For Students</div>
                        <p style="margin-top: 12px;">Students can view their own information, check announcements, submit requests, read schedules, monitor notifications, and message admin when they need support.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">For Admin</div>
                        <p style="margin-top: 12px;">Admin manages student records, shares announcements, handles requests, assigns schedules, and keeps communication organized through conversation threads.</p>
                    </div>
                    <div class="notification-card">
                        <div class="notification-title">Why It Helps</div>
                        <p style="margin-top: 12px;">The system creates a cleaner and more reliable workflow by keeping student services, updates, and communication in one place.</p>
                    </div>
                </div>
            </div>
        </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let studentHasUnsavedChanges = false;

        function trackStudentFormChanges() {
            document.querySelectorAll('form input, form textarea, form select').forEach(field => {
                field.addEventListener('input', function() {
                    studentHasUnsavedChanges = true;
                });
                field.addEventListener('change', function() {
                    studentHasUnsavedChanges = true;
                });
            });

            document.querySelectorAll('form').forEach(form => {
                form.addEventListener('submit', function() {
                    studentHasUnsavedChanges = false;
                });
            });
        }

        function scheduleStudentRefresh() {
            setTimeout(function() {
                const activeElement = document.activeElement;
                const isTyping = activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeElement.tagName);
                if (!studentHasUnsavedChanges && !isTyping) {
                    window.location.reload();
                    return;
                }
                scheduleStudentRefresh();
            }, 15000);
        }

        function showTab(tabId, button) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-tabs button').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            const targetButton = button || event.currentTarget;
            if (targetButton) {
                targetButton.classList.add('active');
            }
            localStorage.setItem('studentActiveTab', tabId);
        }

        document.addEventListener('DOMContentLoaded', function() {
            const activeTab = localStorage.getItem('studentActiveTab');
            if (activeTab) {
                const button = Array.from(document.querySelectorAll('.nav-tabs button'))
                    .find(btn => btn.getAttribute('onclick') && btn.getAttribute('onclick').includes("'" + activeTab + "'"));
                if (button && document.getElementById(activeTab)) {
                    showTab(activeTab, button);
                }
            }

            const studentDashboardThread = document.getElementById('studentDashboardThread');
            if (studentDashboardThread) {
                studentDashboardThread.scrollTop = studentDashboardThread.scrollHeight;
            }

            trackStudentFormChanges();
            scheduleStudentRefresh();
        });
    </script>
</body>
</html>
"""

SETTINGS_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - Settings</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
    <style>
        .dark-theme { background: #1a1a2e !important; }
        .dark-theme .card { background: #16213e; color: #fff; }
        .dark-theme .card-header { color: #fff; }
        .dark-theme h4 { color: #fff; }
        .dark-theme label { color: #ccc; }
        .dark-theme .form-control { background: #0f3460; border-color: #533483; color: #fff; }
        .dark-theme .btn-secondary { background: #533483; border-color: #533483; color: #fff; }
    </style>
</head>
<body class="{{ theme }}">
    <div class="container">
        <div class="card settings-card">
            <div class="card-header">⚙️ Settings</div>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ category }}">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <!-- Theme Selection -->
            <h4>Theme</h4>
            <form method="POST" action="{{ url_for('update_theme') }}" class="mb-4">
                <div class="form-group">
                    <label>Select Theme</label>
                    <select name="theme" class="form-select">
                        <option value="light" {% if theme=='light' %}selected{% endif %}>Light</option>
                        <option value="dark" {% if theme=='dark' %}selected{% endif %}>Dark</option>
                    </select>
                </div>
                <button type="submit" class="btn btn-primary">Apply Theme</button>
            </form>
            <hr>

            <!-- Change Username/Password -->
            <h4>Change Username & Password</h4>
            <form method="POST" action="{{ url_for('update_credentials') }}">
                <div class="form-group">
                    <label>New Username</label>
                    <input type="text" name="new_username" class="form-control" required>
                </div>
                <div class="form-group">
                    <label>New Password</label>
                    <input type="password" name="new_password" class="form-control" required>
                </div>
                <button type="submit" class="btn btn-primary">Update Credentials</button>
            </form>
            <hr>

            <!-- Back Button -->
            {% if session.get('admin') %}
                <a href="{{ url_for('admin_dashboard') }}" class="btn btn-secondary">⬅️ Back to Dashboard</a>
            {% else %}
                <a href="{{ url_for('student_dashboard') }}" class="btn btn-secondary">⬅️ Back to Dashboard</a>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

ABOUT_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>StudTech - About</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
    """ + BASE_CSS + """
</head>
<body class="{{ theme }}">
    <div class="container">
        <div class="card" style="max-width: 1100px; margin: 40px auto;">
            <div class="split-row" style="margin-bottom: 20px;">
                <div>
                    <div class="section-kicker">System Overview</div>
                    <h1>About StudTech</h1>
                    <div class="soft-note">A student and faculty support platform for communication, records, schedules, requests, and updates.</div>
                </div>
                <a href="{{ back_url }}" class="btn btn-primary">{{ back_label }}</a>
            </div>

            <div class="subtle-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); margin-bottom: 24px;">
                <div class="mini-stat"><strong>Students</strong>Register, track requests, check schedules, receive notifications, and message admin.</div>
                <div class="mini-stat"><strong>Admin</strong>Manage records, announcements, schedules, requests, notifications, and student conversations.</div>
                <div class="mini-stat"><strong>Messaging</strong>Messenger-style chat with one conversation thread per Student ID.</div>
            </div>

            <div class="grid-2">
                <div class="notification-card">
                    <div class="notification-title">System Purpose</div>
                    <p style="margin-top: 12px;">StudTech is designed to organize student-related processes in one place. It helps reduce manual tracking by combining registration details, visit records, request handling, schedules, announcements, notifications, and direct communication between students and admin.</p>
                </div>
                <div class="notification-card">
                    <div class="notification-title">Who Can Use It</div>
                    <p style="margin-top: 12px;">Students use the system to maintain their account, submit requests, view announcements, view schedules, receive admin updates, and send concerns through the chat feature. Admin uses the system to monitor student activity, manage information, review requests, and respond to messages efficiently.</p>
                </div>
            </div>

            <div class="notification-card" style="margin-top: 20px;">
                <div class="notification-title">Main Features</div>
                <div class="table-responsive" style="margin-top: 14px;">
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Feature</th>
                                <th>Description</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>Authentication</td>
                                <td>Secure login and registration for students, plus admin access for system management.</td>
                            </tr>
                            <tr>
                                <td>Student Information</td>
                                <td>Stores student identity, program, gender, age, and visit-related records for easier monitoring.</td>
                            </tr>
                            <tr>
                                <td>Announcements</td>
                                <td>Lets admin post important updates that students can read and track.</td>
                            </tr>
                            <tr>
                                <td>Schedules</td>
                                <td>Allows admin to assign schedules and lets students view them from their dashboard.</td>
                            </tr>
                            <tr>
                                <td>Request Management</td>
                                <td>Students submit requests and admin can accept or reject them with status updates.</td>
                            </tr>
                            <tr>
                                <td>Notifications</td>
                                <td>Provides status alerts for requests, schedules, announcements, and messaging activity.</td>
                            </tr>
                            <tr>
                                <td>Conversation Inbox</td>
                                <td>Groups student-admin messages into one thread per Student ID for cleaner communication.</td>
                            </tr>
                            <tr>
                                <td>Activity Monitoring</td>
                                <td>Tracks actions like login and logout for better visibility into usage.</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="grid-2" style="margin-top: 20px;">
                <div class="notification-card">
                    <div class="notification-title">Student Experience</div>
                    <p style="margin-top: 12px;">Students can log in, view their registration information, submit requests, read announcements, see schedules, receive notifications, and contact admin through a scrollable conversation interface. This creates a single place for updates and support.</p>
                </div>
                <div class="notification-card">
                    <div class="notification-title">Admin Experience</div>
                    <p style="margin-top: 12px;">Admin can maintain student records, publish announcements, approve or reject requests, create schedules, and answer student concerns using a structured inbox that shows conversation previews, timestamps, and unread indicators.</p>
                </div>
            </div>

            <div class="notification-card" style="margin-top: 20px;">
                <div class="notification-title">Why This System Helps</div>
                <p style="margin-top: 12px;">StudTech improves organization, speeds up communication, and makes student support easier to manage. Instead of handling updates through scattered notes or separate tools, the system keeps operational data and communication in one accessible platform.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# ===================== ROUTES ===================== #

@app.route("/", methods=["GET", "POST"])
def login():
    """Main login page with choice for student or admin"""
    if request.method == "POST":
        user_type = request.form.get('user_type')
        username = normalize_text(request.form.get('username'))
        password = request.form.get('password') or ""
        
        if user_type == "admin":
            admin = Admin.query.filter_by(username=username).first()
            if admin and try_upgrade_legacy_password(admin, password):
                session['admin'] = True
                session['admin_id'] = admin.id
                session['username'] = admin.username
                # Log admin login
                log = ActivityLog(user_id=username, user_type='admin', action='Logged in')
                db.session.add(log)
                db.session.commit()
                return redirect(url_for('admin_dashboard'))
            else:
                flash("Invalid admin credentials", "danger")
        else:
            user = StudentUser.query.filter_by(username=username).first()
            if user and try_upgrade_legacy_password(user, password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['student_id'] = user.student_id
                # Log student login
                log = ActivityLog(user_id=user.student_id, user_type='student', action='Logged in')
                db.session.add(log)
                db.session.commit()
                return redirect(url_for('student_dashboard'))
            else:
                flash("Invalid student credentials", "danger")
    
    return render_template_string(LOGIN_HTML)

@app.route("/register", methods=["GET", "POST"])
def register():
    """Student registration page"""
    if request.method == "POST":
        student_id = normalize_text(request.form.get('student_id'))
        fullname = normalize_text(request.form.get('fullname'))
        age = request.form.get('age')
        gender = normalize_text(request.form.get('gender'))
        program = normalize_text(request.form.get('program'))
        username = normalize_text(request.form.get('username'))
        password = request.form.get('password') or ""

        if not all([student_id, fullname, age, gender, program, username, password]):
            flash("Please complete all required fields.", "danger")
            return redirect(url_for('register'))

        if not age.isdigit() or int(age) < 1 or int(age) > 120:
            flash("Please enter a valid age.", "danger")
            return redirect(url_for('register'))

        password_ok, password_message = password_meets_rules(password)
        if not password_ok:
            flash(password_message, "danger")
            return redirect(url_for('register'))
        
        # Check if username already exists
        if StudentUser.query.filter_by(username=username).first():
            flash("Username already exists", "danger")
            return redirect(url_for('register'))
        
        # Check if student_id already exists
        if StudentUser.query.filter_by(student_id=student_id).first():
            flash("Student ID already registered", "danger")
            return redirect(url_for('register'))
        
        # Create new student
        new_student = StudentUser(
            student_id=student_id,
            fullname=fullname,
            age=age,
            gender=gender,
            program=program,
            username=username,
            password=hash_password(password)
        )
        db.session.add(new_student)
        db.session.commit()
        
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    
    return render_template_string(REGISTER_HTML)

@app.route("/student")
def student_dashboard():
    """Student dashboard with their info, announcements, and schedules"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = StudentUser.query.get(session.get('user_id'))
    if not student:
        return redirect(url_for('login'))
    
    # Get all announcements (for all students)
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    
    # Get schedules for this student
    schedules = Schedule.query.filter_by(student_id=student.student_id).order_by(Schedule.created_at.desc()).all()

    # Get requests for this student
    student_requests = StudentRequest.query.filter_by(student_id=student.student_id).order_by(StudentRequest.created_at.desc()).all()

    # Get notifications for this student
    student_notifications = Notification.query.filter_by(
        recipient_type='student',
        recipient_id=student.student_id
    ).order_by(Notification.created_at.desc()).all()
    
    student_conversation = get_conversation_by_student_id(student.student_id)
    student_messages = get_conversation_messages(student_conversation) if student_conversation else []
    unread_messages = ConversationMessage.query.filter_by(
        conversation_id=student_conversation.id,
        sender_type='admin',
        is_read=False
    ).count() if student_conversation else 0
    
    # Count unread announcements and schedules
    unread_announcements = sum(1 for a in announcements if not a.is_read)
    unread_schedules = sum(1 for s in schedules if not s.is_read)
    pending_requests = sum(1 for req in student_requests if req.status == "Pending")
    unread_student_notifications = sum(1 for n in student_notifications if not n.is_read)
    
    return render_template_string(STUDENT_DASHBOARD_HTML, 
                                   student=student,
                                   announcements=announcements,
                                   student_requests=student_requests,
                                   student_notifications=student_notifications,
                                   schedules=schedules,
                                   student_conversation=student_conversation,
                                   student_messages=student_messages,
                                   unread_announcements=unread_announcements,
                                   unread_schedules=unread_schedules,
                                   pending_requests=pending_requests,
                                   unread_student_notifications=unread_student_notifications,
                                   unread_messages=unread_messages,
                                   theme=session.get('theme', 'light'))

@app.route("/admin")
def admin_dashboard():
    """Admin dashboard with charts, student management, announcements, and schedules"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    theme = session.get('theme', 'light')
    
    # Get statistics for charts
    male_count = StudentRecord.query.filter_by(gender='Male').count()
    female_count = StudentRecord.query.filter_by(gender='Female').count()
    
    # Program statistics
    programs = db.session.query(StudentRecord.program, func.count(StudentRecord.id))\
        .group_by(StudentRecord.program).all()
    program_labels = [p[0] for p in programs]
    program_values = [p[1] for p in programs]
    
    # Monthly visits statistics
    visits = db.session.query(StudentRecord.visit_date, func.count(StudentRecord.id))\
        .group_by(StudentRecord.visit_date).all()
    month_labels = [v[0] for v in visits]
    visit_values = [v[1] for v in visits]
    
    # Filter by month if selected
    selected_month = request.args.get('filter_month')
    if selected_month:
        students = StudentRecord.query.filter(StudentRecord.visit_date.like(f"{selected_month}%")).all()
    else:
        students = StudentRecord.query.all()
    
    # Get all announcements and schedules
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    schedules = Schedule.query.order_by(Schedule.created_at.desc()).all()
    student_requests = StudentRequest.query.order_by(StudentRequest.created_at.desc()).all()
    admin_notifications = Notification.query.filter_by(
        recipient_type='admin',
        recipient_id='admin'
    ).order_by(Notification.created_at.desc()).all()
    
    unread_msg_count = ConversationMessage.query.filter_by(sender_type='student', is_read=False).count()
    total_notifications = unread_msg_count
    unread_admin_notifications = sum(1 for n in admin_notifications if not n.is_read)
    
    return render_template_string(ADMIN_DASHBOARD_HTML,
                                   male_count=male_count,
                                   female_count=female_count,
                                   program_labels=program_labels,
                                   program_values=program_values,
                                   month_labels=month_labels,
                                   visit_values=visit_values,
                                   students=students,
                                   announcements=announcements,
                                   student_requests=student_requests,
                                   admin_notifications=admin_notifications,
                                   schedules=schedules,
                                   selected_month=selected_month,
                                   unread_msg_count=unread_msg_count,
                                   total_notifications=total_notifications,
                                   unread_admin_notifications=unread_admin_notifications,
                                   theme=theme)

@app.route("/add_student", methods=["POST"])
def add_student():
    """Add a new student record (Admin)"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    student_id = request.form.get('student_id')
    fullname = request.form.get('fullname')
    program = request.form.get('program')
    gender = request.form.get('gender')
    visit_date = request.form.get('visit_date')
    visit_time = request.form.get('visit_time')
    purpose = request.form.get('purpose', '')
    
    new_record = StudentRecord(
        student_id=student_id,
        fullname=fullname,
        program=program,
        gender=gender,
        visit_date=visit_date,
        visit_time=visit_time,
        purpose=purpose
    )
    db.session.add(new_record)
    db.session.commit()
    
    flash("Student record added successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/view_student/<student_id>")
def view_student(student_id):
    """View student details (Admin)"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    student = StudentRecord.query.filter_by(student_id=student_id).first()
    if not student:
        flash("Student not found", "danger")
        return redirect(url_for('admin_dashboard'))
    
    return render_template_string(VIEW_STUDENT_HTML, student=student)

@app.route("/delete_student/<student_id>")
def delete_student(student_id):
    """Delete a student record (Admin)"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    student = StudentRecord.query.filter_by(student_id=student_id).first()
    if student:
        db.session.delete(student)
        db.session.commit()
        flash("Student record deleted successfully!", "success")
    
    return redirect(url_for('admin_dashboard'))

@app.route("/create_announcement", methods=["POST"])
def create_announcement():
    """Create an announcement for all students (Admin)"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    title = request.form.get('title')
    message = request.form.get('message')
    
    new_announcement = Announcement(title=title, message=message)
    db.session.add(new_announcement)
    db.session.commit()
    
    flash("Announcement posted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/create_schedule", methods=["POST"])
def create_schedule():
    """Create a schedule for a specific student (Admin)"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    student_id = request.form.get('student_id')
    message = request.form.get('message')
    
    new_schedule = Schedule(student_id=student_id, message=message)
    db.session.add(new_schedule)
    student = StudentUser.query.filter_by(student_id=student_id).first()
    if student:
        create_notification(
            'student',
            student_id,
            'New Schedule Created',
            f'Admin created a schedule for you: {message}',
            category='schedule',
            sender='Admin',
            status_label='Scheduled'
        )
        create_status_message(
            student_id,
            student.fullname,
            'Schedule Update',
            f'Your schedule has been created. Details: {message}',
            sender_type='Admin',
            status_update='Scheduled'
        )
    create_notification(
        'admin',
        'admin',
        'Schedule Posted',
        f'Schedule created for student ID {student_id}.',
        category='schedule',
        sender='Admin',
        status_label='Scheduled'
    )
    db.session.commit()
    
    flash("Schedule posted successfully!", "success")
    return redirect(url_for('admin_dashboard'))

@app.route("/create_request", methods=["POST"])
def create_request():
    """Student submits a new request for admin approval"""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    student = StudentUser.query.get(session.get('user_id'))
    if not student:
        return redirect(url_for('login'))

    purpose = request.form.get('purpose', '').strip()
    schedule = request.form.get('schedule', '').strip()

    if not purpose or not schedule:
        flash("Purpose and preferred schedule are required.", "danger")
        return redirect(url_for('student_dashboard'))

    new_request = StudentRequest(
        student_id=student.student_id,
        fullname=student.fullname,
        purpose=purpose,
        schedule=schedule,
        status="Pending"
    )
    db.session.add(new_request)
    create_notification(
        'admin',
        'admin',
        'New Request Submitted',
        f'{student.fullname} submitted a request for {schedule} with purpose: {purpose}',
        category='request',
        sender='Student',
        status_label='Pending'
    )
    create_notification(
        'student',
        student.student_id,
        'Request Submitted',
        f'Your request for {schedule} has been submitted and is waiting for admin review.',
        category='request',
        sender='System',
        status_label='Pending'
    )
    create_status_message(
        student.student_id,
        student.fullname,
        'Request Submitted',
        f'Request submitted for {schedule}. Purpose: {purpose}',
        sender_type='Student',
        status_update='Pending'
    )
    db.session.commit()

    flash("Request submitted successfully and is now pending admin approval.", "success")
    return redirect(url_for('student_dashboard'))

@app.route("/request/<int:request_id>/status", methods=["POST"])
def update_request_status(request_id):
    """Admin accepts or rejects a student request"""
    if not session.get('admin'):
        return redirect(url_for('login'))

    student_request = StudentRequest.query.get_or_404(request_id)
    action = request.form.get('action', '').strip().lower()
    rejection_reason = request.form.get('rejection_reason', '').strip()

    if student_request.status != "Pending":
        flash("This request has already been processed.", "info")
        return redirect(url_for('admin_dashboard'))

    if action == "accept":
        student_request.status = "Accepted"
        student_request.rejection_reason = None

        student_user = StudentUser.query.filter_by(student_id=student_request.student_id).first()
        existing_record = StudentRecord.query.filter_by(
            student_id=student_request.student_id,
            purpose=student_request.purpose,
            visit_date=student_request.schedule
        ).first()
        if not existing_record:
            accepted_record = StudentRecord(
                student_id=student_request.student_id,
                fullname=student_request.fullname,
                program=student_user.program if student_user else "N/A",
                gender=student_user.gender if student_user else "N/A",
                visit_date=student_request.schedule,
                visit_time="00:00",
                purpose=student_request.purpose
            )
            db.session.add(accepted_record)

        request_date = student_request.created_at.strftime('%Y-%m-%d')
        schedule_message = (
            f"Accepted request for {student_request.fullname} | "
            f"Purpose: {student_request.purpose} | "
            f"Date of request: {request_date} | "
            f"Scheduled: {student_request.schedule}"
        )
        db.session.add(Schedule(student_id=student_request.student_id, message=schedule_message))
        create_notification(
            'student',
            student_request.student_id,
            'Request Accepted',
            f'Your request has been accepted. Scheduled date: {student_request.schedule}.',
            category='request',
            sender='Admin',
            status_label='Accepted'
        )
        create_notification(
            'admin',
            'admin',
            'Request Accepted',
            f'Accepted request of {student_request.fullname} for {student_request.schedule}.',
            category='request',
            sender='Admin',
            status_label='Accepted'
        )
        create_notification(
            'student',
            student_request.student_id,
            'Schedule Created',
            f'A schedule entry was created for {student_request.schedule}.',
            category='schedule',
            sender='Admin',
            status_label='Scheduled'
        )
        create_notification(
            'admin',
            'admin',
            'Schedule Created',
            f'Schedule entry created automatically for {student_request.fullname}.',
            category='schedule',
            sender='Admin',
            status_label='Scheduled'
        )
        create_status_message(
            student_request.student_id,
            student_request.fullname,
            'Request Update',
            f'Your request was accepted. Purpose: {student_request.purpose}. Scheduled date: {student_request.schedule}.',
            sender_type='Admin',
            status_update='Accepted'
        )
        create_status_message(
            student_request.student_id,
            student_request.fullname,
            'Schedule Created',
            f'A schedule entry is now available for {student_request.schedule}.',
            sender_type='Admin',
            status_update='Scheduled'
        )
        flash("Request accepted. Student and admin schedules were updated automatically.", "success")
    elif action == "reject":
        if not rejection_reason:
            flash("Please provide a rejection reason before rejecting the request.", "danger")
            return redirect(url_for('admin_dashboard'))
        student_request.status = "Rejected"
        student_request.rejection_reason = rejection_reason
        create_notification(
            'student',
            student_request.student_id,
            'Request Rejected',
            f'Your request was rejected. Reason: {rejection_reason}',
            category='request',
            sender='Admin',
            status_label='Rejected'
        )
        create_notification(
            'admin',
            'admin',
            'Request Rejected',
            f'Rejected request of {student_request.fullname}. Reason: {rejection_reason}',
            category='request',
            sender='Admin',
            status_label='Rejected'
        )
        create_status_message(
            student_request.student_id,
            student_request.fullname,
            'Request Update',
            f'Your request was rejected. Reason: {rejection_reason}',
            sender_type='Admin',
            status_update='Rejected'
        )
        flash("Request rejected. The student view will update automatically.", "success")
    else:
        flash("Invalid request action.", "danger")
        return redirect(url_for('admin_dashboard'))

    db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route("/settings")
def student_settings():
    """Student settings page"""
    if 'user_id' not in session and not session.get('admin'):
        return redirect(url_for('login'))
    
    theme = session.get('theme', 'light')
    return render_template_string(SETTINGS_HTML, theme=theme)

@app.route("/admin_settings")
def admin_settings():
    """Admin settings page"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    theme = session.get('theme', 'light')
    return render_template_string(SETTINGS_HTML, theme=theme)

@app.route("/about")
def about_system():
    """Shared About page for admin, students, and visitors."""
    theme = session.get('theme', 'light')

    if session.get('admin'):
        back_url = url_for('admin_dashboard')
        back_label = "Back to Admin Dashboard"
    elif session.get('user_id'):
        back_url = url_for('student_dashboard')
        back_label = "Back to Student Dashboard"
    else:
        back_url = url_for('login')
        back_label = "Back to Login"

    return render_template_string(
        ABOUT_HTML,
        theme=theme,
        back_url=back_url,
        back_label=back_label
    )

@app.route("/update_theme", methods=["POST"])
def update_theme():
    """Update theme preference"""
    theme = request.form.get('theme', 'light')
    session['theme'] = theme
    
    if session.get('admin'):
        return redirect(url_for('admin_dashboard'))
    elif session.get('user_id'):
        return redirect(url_for('student_dashboard'))
    return redirect(url_for('login'))

@app.route("/update_credentials", methods=["POST"])
def update_credentials():
    """Update username and password"""
    new_username = normalize_text(request.form.get('new_username'))
    new_password = request.form.get('new_password') or ""

    if not new_username:
        flash("Username cannot be empty.", "danger")
        if session.get('admin'):
            return redirect(url_for('admin_settings'))
        if session.get('user_id'):
            return redirect(url_for('settings'))
        return redirect(url_for('login'))

    password_ok, password_message = password_meets_rules(new_password)
    if not password_ok:
        flash(password_message, "danger")
        if session.get('admin'):
            return redirect(url_for('admin_settings'))
        if session.get('user_id'):
            return redirect(url_for('settings'))
        return redirect(url_for('login'))
    
    if session.get('admin'):
        # Update admin credentials in database
        admin = Admin.query.get(session['admin_id'])
        if admin:
            # Simple check - could add username uniqueness validation
            existing_admin = Admin.query.filter(Admin.username != admin.username, Admin.username == new_username).first()
            if existing_admin:
                flash("Username already taken", "danger")
                if session.get('admin'):
                    return redirect(url_for('admin_settings'))
                else:
                    return redirect(url_for('student_settings'))
            
            admin.username = new_username
            admin.password = hash_password(new_password)
            db.session.commit()
            session['username'] = new_username
            flash("Admin credentials updated successfully! They now persist in database.", "success")
        else:
            flash("Admin not found in database", "danger")
        return redirect(url_for('admin_dashboard'))
    elif session.get('user_id'):
        # Update student credentials
        student = StudentUser.query.get(session.get('user_id'))
        if student:
            # Check if username is already taken by another student
            existing = StudentUser.query.filter_by(username=new_username).first()
            if existing and existing.id != student.id:
                flash("Username already taken", "danger")
                return redirect(url_for('student_settings'))
            
            student.username = new_username
            student.password = hash_password(new_password)
            db.session.commit()
            session['username'] = new_username
            flash("Credentials updated successfully!", "success")
            return redirect(url_for('student_dashboard'))
    
    flash("Error updating credentials", "danger")
    return redirect(url_for('login'))

@app.route("/logout")
def logout():
    """Logout and redirect to login"""
    # Log logout action before clearing session
    if session.get('admin'):
        log = ActivityLog(user_id=session.get('username'), user_type='admin', action='Logged out')
        db.session.add(log)
        db.session.commit()
    elif session.get('user_id'):
        log = ActivityLog(user_id=session.get('student_id'), user_type='student', action='Logged out')
        db.session.add(log)
        db.session.commit()
    
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('login'))

# Routes for marking announcements as read
@app.route("/mark_announcement_read/<int:announcement_id>")
def mark_announcement_read(announcement_id):
    """Mark an announcement as read"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    announcement = Announcement.query.get(announcement_id)
    if announcement:
        announcement.is_read = True
        db.session.commit()
    
    return redirect(url_for('student_dashboard'))

@app.route("/mark_all_announcements_read")
def mark_all_announcements_read():
    """Mark all announcements as read"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    Announcement.query.update({'is_read': True})
    db.session.commit()
    
    return redirect(url_for('student_dashboard'))

@app.route("/delete_announcement/<int:announcement_id>")
def delete_announcement(announcement_id):
    """Delete an announcement"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    announcement = Announcement.query.get(announcement_id)
    if announcement:
        db.session.delete(announcement)
        db.session.commit()
        flash("Announcement deleted", "success")
    
    return redirect(url_for('student_dashboard'))

# Routes for marking schedules as read
@app.route("/mark_schedule_read/<int:schedule_id>")
def mark_schedule_read(schedule_id):
    """Mark a schedule as read"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    schedule = Schedule.query.get(schedule_id)
    if schedule:
        schedule.is_read = True
        db.session.commit()
    
    return redirect(url_for('student_dashboard'))

@app.route("/mark_all_schedules_read")
def mark_all_schedules_read():
    """Mark all schedules as read"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student_id = session.get('student_id')
    if student_id:
        Schedule.query.filter_by(student_id=student_id).update({'is_read': True})
        db.session.commit()
    
    return redirect(url_for('student_dashboard'))

@app.route("/delete_schedule/<int:schedule_id>")
def delete_schedule(schedule_id):
    """Delete a schedule"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    schedule = Schedule.query.get(schedule_id)
    if schedule:
        db.session.delete(schedule)
        db.session.commit()
        flash("Schedule deleted", "success")
    
    return redirect(url_for('student_dashboard'))

# ===================== CONTACT ADMIN FEATURE ===================== #

@app.route("/contact_admin", methods=["GET", "POST"])
def contact_admin():
    """Student messenger-style chat with admin."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = StudentUser.query.get(session.get('user_id'))
    if not student:
        return redirect(url_for('login'))
    
    conversation = get_conversation_by_student_id(student.student_id)
    
    if request.method == "POST":
        message = normalize_text(request.form.get('message'))
        if not message:
            flash("Please enter a message before sending.", "danger")
            return redirect(url_for('contact_admin'))

        conversation = conversation or get_or_create_conversation(student.student_id)
        add_conversation_message(conversation, 'student', message, is_read=False)
        create_notification(
            'admin',
            'admin',
            'New Student Message',
            f'{student.fullname} sent a new message to admin.',
            category='message',
            sender='Student'
        )
        db.session.commit()
        
        flash("Message sent to admin successfully!", "success")
        return redirect(url_for('contact_admin'))

    if conversation:
        mark_conversation_read(conversation, 'student')
        db.session.commit()
        messages = get_conversation_messages(conversation)
    else:
        messages = []
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>StudTech - Contact Admin</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
        """ + BASE_CSS + """
    </head>
    <body class="{{ theme }}">
        <div class="container">
            <div class="messenger-shell">
                <div class="messenger-topbar">
                    <div class="messenger-title">
                        <div class="messenger-avatar">AD</div>
                        <div>
                            <div class="messenger-name">Admin Support</div>
                            <div class="messenger-subtitle">Private conversation for {{ student.fullname }}</div>
                        </div>
                    </div>
                    <div class="inline-actions">
                        <span class="chat-chip">{{ student.student_id }}</span>
                        <a href="{{ url_for('student_dashboard') }}" class="btn btn-light btn-sm">Back to Dashboard</a>
                    </div>
                </div>
                <div class="chat-pane" style="min-height: 680px;">
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                        <div style="padding: 18px 22px 0;">
                            {% for category, message in messages %}
                                <div class="alert alert-{{ category }}">{{ message }}</div>
                            {% endfor %}
                        </div>
                        {% endif %}
                    {% endwith %}
                    <div class="chat-pane-head">
                        <div>
                            <div class="messenger-name" style="color: var(--text-main);">Conversation with Admin</div>
                            <div class="notification-meta">Messages are shown in time order and refresh automatically.</div>
                        </div>
                        <div class="inline-actions">
                            <div class="chat-chip">{{ messages|length }} total message(s)</div>
                            {% if conversation %}
                            <form method="POST" action="{{ url_for('delete_conversation', conversation_id=conversation.id) }}" onsubmit="return confirm('Delete this whole conversation? This will remove all messages in the thread.');">
                                <button type="submit" class="btn btn-danger btn-sm">Delete Conversation</button>
                            </form>
                            {% endif %}
                        </div>
                    </div>
                    <div class="chat-thread-window" id="studentConversationThread">
                        {% if messages %}
                            {% for item in messages %}
                            <div class="message-row {% if item.sender_type == 'admin' %}left{% else %}right{% endif %}">
                                <div class="chat-bubble {% if item.sender_type == 'admin' %}admin{% else %}student{% endif %}">
                                    <div class="chat-meta">
                                        <span class="chat-label">{% if item.sender_type == 'admin' %}Admin{% else %}You{% endif %}</span>
                                        <span>
                                            {% if item.sender_type == 'admin' and not item.is_read %}
                                            <span class="status-tag">New</span>
                                            {% else %}
                                            <span class="status-tag">{% if item.is_read %}Seen{% else %}Sent{% endif %}</span>
                                            {% endif %}
                                            {{ item.timestamp.strftime('%b %d, %I:%M %p') }}
                                        </span>
                                    </div>
                                    <div>{{ item.message }}</div>
                                </div>
                            </div>
                            {% endfor %}
                        {% else %}
                        <div class="chat-empty">
                            <div>
                                <div class="messenger-name" style="color: var(--text-main); margin-bottom: 8px;">Start your conversation</div>
                                <div>Send your first message and admin replies will appear here.</div>
                            </div>
                        </div>
                        {% endif %}
                    </div>
                    <div class="chat-composer">
                        <form method="POST" action="{{ url_for('contact_admin') }}" id="studentMessageForm">
                            <label>Message</label>
                            <div class="send-row">
                                <textarea name="message" id="studentMessageInput" class="form-control" placeholder="Type your message to admin..." rows="3" required></textarea>
                                <button type="submit" class="btn btn-primary send-icon">Send ➤</button>
                            </div>
                            <div class="soft-note">Press Enter to send. Use Shift + Enter for a new line.</div>
                        </form>
                    </div>
                </div>
            </div>
        </div>
        <script>
            const studentComposer = document.getElementById('studentMessageInput');
            const studentForm = document.getElementById('studentMessageForm');
            const studentConversationThread = document.getElementById('studentConversationThread');
            let studentTyping = false;
            if (studentConversationThread) {
                studentConversationThread.scrollTop = studentConversationThread.scrollHeight;
            }
            if (studentComposer && studentForm) {
                studentComposer.addEventListener('input', function() {
                    studentTyping = studentComposer.value.trim().length > 0;
                });
                studentComposer.addEventListener('keydown', function(event) {
                    if (event.key === 'Enter' && !event.shiftKey) {
                        event.preventDefault();
                        studentForm.submit();
                    }
                });
            }
            setTimeout(function refreshStudentConversation() {
                const activeElement = document.activeElement;
                const isTypingField = activeElement && ['INPUT', 'TEXTAREA'].includes(activeElement.tagName);
                if (!studentTyping && !isTypingField) {
                    window.location.reload();
                    return;
                }
                setTimeout(refreshStudentConversation, 15000);
            }, 15000);
        </script>
    </body>
    </html>
    """, student=student, conversation=conversation, messages=messages, theme=session.get('theme', 'light'))

@app.route("/view_messages")
def view_messages():
    """Admin messenger-style inbox grouped by student."""
    if not session.get('admin'):
        return redirect(url_for('login'))

    search_query = normalize_text(request.args.get('q'))
    conversation_items = build_admin_conversation_items(search_query)
    selected_conversation_id = request.args.get('conversation_id', type=int)
    selected_item = None
    if selected_conversation_id:
        selected_item = next((item for item in conversation_items if item['conversation'].id == selected_conversation_id), None)
    if not selected_item and conversation_items:
        selected_item = conversation_items[0]

    active_conversation = selected_item['conversation'] if selected_item else None
    if active_conversation:
        mark_conversation_read(active_conversation, 'admin')
        db.session.commit()
        selected_item['unread_count'] = 0
    active_messages = get_conversation_messages(active_conversation) if active_conversation else []

    theme = session.get('theme', 'light')
    admin_notifications = Notification.query.filter_by(recipient_type='admin', recipient_id='admin').order_by(Notification.created_at.desc()).all()
    unread_admin_notifications = sum(1 for n in admin_notifications if not n.is_read)
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>StudTech - Contact Messages</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">
        """ + BASE_CSS + """
    </head>
    <body class="{{ theme }}">
        <div class="container">
            <div class="card">
                <a href="{{ url_for('admin_dashboard') }}" class="btn btn-primary back-btn">⬅️ Back to Dashboard</a>
                <div class="notification-top" style="margin-bottom: 24px;">
                    <h2 style="text-align: center; color: #667eea; margin-bottom: 0;">📬 Contact Messages</h2>
                    <a href="{{ url_for('mark_all_notifications_read') }}?panel=admin" class="btn btn-info btn-sm">🔔 Alerts {{ unread_admin_notifications }}</a>
                </div>
                
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        {% for category, message in messages %}
                            <div class="alert alert-{{ category }}">{{ message }}</div>
                        {% endfor %}
                    {% endif %}
                {% endwith %}
                
                {% if conversation_items %}
                    <div class="messenger-shell">
                        <div class="messenger-topbar">
                            <div class="messenger-title">
                                <div class="messenger-avatar">ST</div>
                                <div>
                                    <div class="messenger-name">Student Conversations</div>
                                    <div class="messenger-subtitle">One thread per Student ID, with newest activity first</div>
                                </div>
                            </div>
                            <div class="messenger-subtitle">{{ conversation_items|length }} conversation(s)</div>
                        </div>
                        <div class="messenger-split">
                            <aside class="chat-list-panel">
                                <div class="chat-list-head">
                                    <div>
                                        <div class="messenger-name" style="color: var(--text-main);">Inbox</div>
                                        <div class="notification-meta">Search by student name or Student ID.</div>
                                    </div>
                                    <form method="GET" action="{{ url_for('view_messages') }}" class="chat-search">
                                        <span class="chat-search-icon">⌕</span>
                                        <input type="text" name="q" value="{{ search_query }}" class="form-control" placeholder="Search student or ID">
                                        {% if active_conversation %}
                                        <input type="hidden" name="conversation_id" value="{{ active_conversation.id }}">
                                        {% endif %}
                                    </form>
                                </div>
                                <div class="chat-list">
                                    {% for item in conversation_items %}
                                    <a href="{{ url_for('view_messages', conversation_id=item.conversation.id, q=search_query) }}" class="chat-list-item {% if active_conversation and item.conversation.id == active_conversation.id %}active{% endif %}">
                                        <div class="chat-list-top">
                                            <div class="chat-list-name">{{ item.student_name }}</div>
                                            <div class="chat-time">{{ item.latest_message.timestamp.strftime('%b %d, %I:%M %p') }}</div>
                                        </div>
                                        <div class="chat-list-bottom">
                                            <div class="chat-list-preview">{% if item.latest_message.sender_type == 'admin' %}You: {% endif %}{{ item.latest_message.message }}</div>
                                            <div>{% if item.unread_count > 0 %}<span class="badge badge-new">{{ item.unread_count }}</span>{% endif %}</div>
                                        </div>
                                        <div class="notification-meta">Student ID: {{ item.student_id }}</div>
                                    </a>
                                    {% endfor %}
                                </div>
                            </aside>
                            <section class="chat-pane">
                                {% if active_conversation %}
                                <div class="chat-pane-head">
                                    <div class="messenger-title">
                                        <div class="messenger-avatar" style="background: linear-gradient(135deg, var(--primary), var(--secondary));">{{ (selected_item.student_name[:2] if selected_item.student_name else 'ST')|upper }}</div>
                                        <div>
                                            <div class="messenger-name" style="color: var(--text-main);">{{ selected_item.student_name }}</div>
                                            <div class="notification-meta">Student ID: {{ selected_item.student_id }}</div>
                                        </div>
                                    </div>
                                    <div class="inline-actions">
                                        <div class="chat-chip">{{ active_messages|length }} message(s)</div>
                                        <form method="POST" action="{{ url_for('delete_conversation', conversation_id=active_conversation.id) }}" onsubmit="return confirm('Delete this whole conversation? This will remove all messages in the thread.');">
                                            <button type="submit" class="btn btn-danger btn-sm">Delete Conversation</button>
                                        </form>
                                    </div>
                                </div>
                                <div class="chat-thread-window" id="adminConversationThread">
                                    {% for item in active_messages %}
                                    <div class="message-row {% if item.sender_type == 'admin' %}right{% else %}left{% endif %}">
                                        <div class="chat-bubble {% if item.sender_type == 'admin' %}admin{% else %}student{% endif %}">
                                            <div class="chat-meta">
                                                <span class="chat-label">{% if item.sender_type == 'admin' %}Admin{% else %}Student{% endif %}</span>
                                                <span>
                                                    {% if item.sender_type == 'student' and not item.is_read %}
                                                    <span class="status-tag">Unread</span>
                                                    {% else %}
                                                    <span class="status-tag">{% if item.is_read %}Seen{% else %}Sent{% endif %}</span>
                                                    {% endif %}
                                                    {{ item.timestamp.strftime('%b %d, %I:%M %p') }}
                                                </span>
                                            </div>
                                            <div>{{ item.message }}</div>
                                        </div>
                                    </div>
                                    {% endfor %}
                                </div>
                                <div class="chat-composer">
                                    <form method="POST" action="{{ url_for('conversation_reply', conversation_id=active_conversation.id) }}" id="adminConversationReplyForm">
                                        <label>Reply as Admin</label>
                                        <div class="send-row">
                                            <textarea name="message" id="adminConversationReplyInput" class="form-control" rows="3" placeholder="Type your reply..." required></textarea>
                                            <button type="submit" class="btn btn-success send-icon">Send ➤</button>
                                        </div>
                                        <div class="soft-note">Replies stay inside this student's thread only.</div>
                                    </form>
                                </div>
                                {% else %}
                                <div class="chat-empty">
                                    <div>
                                        <div class="messenger-name" style="color: var(--text-main); margin-bottom: 8px;">No conversation selected</div>
                                        <div>Choose a student from the left panel to open the full message history.</div>
                                    </div>
                                </div>
                                {% endif %}
                            </section>
                        </div>
                    </div>
                {% else %}
                    <div class="alert alert-warning">No student conversations yet.</div>
                {% endif %}
            </div>
            <script>
                const adminConversationThread = document.getElementById('adminConversationThread');
                const adminConversationReplyInput = document.getElementById('adminConversationReplyInput');
                const adminConversationReplyForm = document.getElementById('adminConversationReplyForm');
                let adminConversationTyping = false;
                if (adminConversationThread) {
                    adminConversationThread.scrollTop = adminConversationThread.scrollHeight;
                }
                if (adminConversationReplyInput && adminConversationReplyForm) {
                    adminConversationReplyInput.addEventListener('input', function() {
                        adminConversationTyping = adminConversationReplyInput.value.trim().length > 0;
                    });
                    adminConversationReplyInput.addEventListener('keydown', function(event) {
                        if (event.key === 'Enter' && !event.shiftKey) {
                            event.preventDefault();
                            adminConversationReplyForm.submit();
                        }
                    });
                }
                setTimeout(function refreshAdminConversation() {
                    const activeElement = document.activeElement;
                    const isTypingField = activeElement && ['INPUT', 'TEXTAREA'].includes(activeElement.tagName);
                    if (!adminConversationTyping && !isTypingField) {
                        window.location.reload();
                        return;
                    }
                    setTimeout(refreshAdminConversation, 15000);
                }, 15000);
            </script>
        </div>
    </body>
    </html>
    """, conversation_items=conversation_items, active_conversation=active_conversation, active_messages=active_messages, selected_item=selected_item, search_query=search_query, theme=theme, unread_admin_notifications=unread_admin_notifications)

@app.route("/conversation/<int:conversation_id>/reply", methods=["POST"])
def conversation_reply(conversation_id):
    """Admin reply inside an existing student conversation."""
    if not session.get('admin'):
        return redirect(url_for('login'))

    conversation = Conversation.query.get_or_404(conversation_id)
    reply = normalize_text(request.form.get('message'))
    if not reply:
        flash("Reply cannot be empty.", "danger")
        return redirect(url_for('view_messages', conversation_id=conversation.id))

    add_conversation_message(conversation, 'admin', reply, is_read=False)
    create_notification(
        'student',
        conversation.student_id,
        'New Admin Reply',
        'Admin sent you a new message in your conversation thread.',
        category='message',
        sender='Admin'
    )
    db.session.commit()
    flash("Reply sent successfully!", "success")
    return redirect(url_for('view_messages', conversation_id=conversation.id))


@app.route("/conversation/<int:conversation_id>/delete", methods=["POST"])
def delete_conversation(conversation_id):
    """Delete a full conversation thread with ownership checks."""
    conversation = Conversation.query.get_or_404(conversation_id)

    if session.get('admin'):
        db.session.delete(conversation)
        db.session.commit()
        flash("Conversation deleted successfully.", "success")
        return redirect(url_for('view_messages'))

    if session.get('user_id'):
        if conversation.student_id != session.get('student_id'):
            flash("You are not allowed to delete that conversation.", "danger")
            return redirect(url_for('student_dashboard'))

        db.session.delete(conversation)
        db.session.commit()
        flash("Your conversation was deleted.", "success")
        return redirect(url_for('contact_admin'))

    return redirect(url_for('login'))

@app.route("/reply_message/<int:message_id>", methods=["GET", "POST"])
def reply_message(message_id):
    """Compatibility redirect for older single-message links."""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    message = ContactMessage.query.get(message_id)
    if not message:
        return redirect(url_for('view_messages'))

    conversation = get_conversation_by_student_id(message.student_id) or get_or_create_conversation(message.student_id)
    db.session.commit()
    return redirect(url_for('view_messages', conversation_id=conversation.id))

@app.route("/mark_message_read/<int:message_id>")
def mark_message_read(message_id):
    """Mark a message as read"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    message = ContactMessage.query.get(message_id)
    if message:
        message.is_read = True
        db.session.commit()
    
    return redirect(url_for('view_messages'))

@app.route("/delete_message/<int:message_id>")
def delete_message(message_id):
    """Delete a message"""
    if not session.get('admin'):
        return redirect(url_for('login'))
    
    message = ContactMessage.query.get(message_id)
    if message:
        db.session.delete(message)
        db.session.commit()
        flash("Message deleted", "success")
    
    return redirect(url_for('view_messages'))

@app.route("/student_reply/<int:message_id>", methods=["GET", "POST"])
def student_reply_message(message_id):
    """Compatibility redirect for older student reply links."""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = ContactMessage.query.get(message_id)
    if not message:
        return redirect(url_for('student_dashboard'))
    
    # Verify the message belongs to the logged-in student
    if message.student_id != session.get('student_id'):
        return redirect(url_for('student_dashboard'))
    
    return redirect(url_for('contact_admin'))

@app.route("/notifications/mark-all")
def mark_all_notifications_read():
    """Mark all notifications as read for the active panel"""
    panel = request.args.get('panel', '').strip().lower()

    if panel == 'admin' and session.get('admin'):
        Notification.query.filter_by(recipient_type='admin', recipient_id='admin', is_read=False).update({'is_read': True})
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    if panel == 'student' and session.get('user_id'):
        student_id = session.get('student_id')
        Notification.query.filter_by(recipient_type='student', recipient_id=student_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return redirect(url_for('student_dashboard'))

    return redirect(url_for('login'))

@app.route("/notifications/delete/<int:notification_id>")
def delete_notification(notification_id):
    """Delete a notification for admin or the owning student."""
    notification = Notification.query.get_or_404(notification_id)

    if session.get('admin'):
        db.session.delete(notification)
        db.session.commit()
        flash("Notification deleted successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    if session.get('user_id'):
        student_id = session.get('student_id')
        if notification.recipient_type == 'student' and notification.recipient_id == student_id:
            db.session.delete(notification)
            db.session.commit()
            flash("Notification deleted successfully!", "success")
        else:
            flash("You are not allowed to delete that notification.", "danger")
        return redirect(url_for('student_dashboard'))

    return redirect(url_for('login'))

@app.route("/student_delete_message/<int:message_id>")
def student_delete_message(message_id):
    """Student delete their own message"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    message = ContactMessage.query.get(message_id)
    if not message:
        return redirect(url_for('student_dashboard'))
    
    # Verify the message belongs to the logged-in student
    if message.student_id != session.get('student_id'):
        return redirect(url_for('student_dashboard'))
    
    db.session.delete(message)
    db.session.commit()
    flash("Message deleted successfully!", "success")
    
    return redirect(url_for('student_dashboard'))

# ===================== APP INITIALIZATION ===================== #

def init_db():
    """Initialize database and handle lightweight schema checks."""
    with app.app_context():
        db.create_all()
        engine_name = db.engine.url.get_backend_name()

        if engine_name == "sqlite":
            # Legacy SQLite patch-ups for older local databases.
            tables_with_created_at = ['student_record', 'announcement', 'schedule', 'student_user']

            try:
                for table_name in tables_with_created_at:
                    try:
                        result = db.session.execute(text(f"PRAGMA table_info({table_name})"))
                        columns = [row[1] for row in result]
                        if 'created_at' not in columns:
                            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN created_at TIMESTAMP"))
                            db.session.commit()
                            print(f"Added missing 'created_at' column to {table_name} table")
                    except Exception as e:
                        print(f"Note: Could not check {table_name} table: {e}")
            except Exception as e:
                print(f"Note: Could not check/add created_at columns: {e}")

            try:
                try:
                    result = db.session.execute(text("PRAGMA table_info(announcement)"))
                    columns = [row[1] for row in result]
                    if 'is_read' not in columns:
                        db.session.execute(text("ALTER TABLE announcement ADD COLUMN is_read BOOLEAN DEFAULT 0"))
                        db.session.commit()
                        print("Added missing 'is_read' column to announcement table")
                except Exception as e:
                    print(f"Note: Could not check/update announcement table: {e}")

                try:
                    result = db.session.execute(text("PRAGMA table_info(schedule)"))
                    columns = [row[1] for row in result]
                    if 'is_read' not in columns:
                        db.session.execute(text("ALTER TABLE schedule ADD COLUMN is_read BOOLEAN DEFAULT 0"))
                        db.session.commit()
                        print("Added missing 'is_read' column to schedule table")
                except Exception as e:
                    print(f"Note: Could not check/update schedule table: {e}")
            except Exception as e:
                print(f"Note: Could not add is_read columns: {e}")

            try:
                try:
                    result = db.session.execute(text("PRAGMA table_info(contact_message)"))
                    columns = [row[1] for row in result]
                    if 'reply' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN reply TEXT"))
                        db.session.commit()
                        print("Added missing 'reply' column to contact_message table")
                    if 'is_replied' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN is_replied BOOLEAN DEFAULT 0"))
                        db.session.commit()
                        print("Added missing 'is_replied' column to contact_message table")
                    if 'student_reply' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN student_reply TEXT"))
                        db.session.commit()
                        print("Added missing 'student_reply' column to contact_message table")
                    if 'student_replied' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN student_replied BOOLEAN DEFAULT 0"))
                        db.session.commit()
                        print("Added missing 'student_replied' column to contact_message table")
                    if 'sender_type' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN sender_type TEXT DEFAULT 'Student'"))
                        db.session.commit()
                        print("Added missing 'sender_type' column to contact_message table")
                    if 'message_type' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN message_type TEXT DEFAULT 'conversation'"))
                        db.session.commit()
                        print("Added missing 'message_type' column to contact_message table")
                    if 'status_update' not in columns:
                        db.session.execute(text("ALTER TABLE contact_message ADD COLUMN status_update TEXT"))
                        db.session.commit()
                        print("Added missing 'status_update' column to contact_message table")
                except Exception as e:
                    print(f"Note: Could not check/update contact_message table: {e}")
            except Exception as e:
                print(f"Note: Could not add reply columns: {e}")

            try:
                result = db.session.execute(text("PRAGMA table_info(student_request)"))
                columns = [row[1] for row in result]
                if 'status' not in columns:
                    db.session.execute(text("ALTER TABLE student_request ADD COLUMN status TEXT DEFAULT 'Pending'"))
                    db.session.commit()
                    print("Added missing 'status' column to student_request table")
                if 'rejection_reason' not in columns:
                    db.session.execute(text("ALTER TABLE student_request ADD COLUMN rejection_reason TEXT"))
                    db.session.commit()
                    print("Added missing 'rejection_reason' column to student_request table")
                if 'created_at' not in columns:
                    db.session.execute(text("ALTER TABLE student_request ADD COLUMN created_at TIMESTAMP"))
                    db.session.commit()
                    print("Added missing 'created_at' column to student_request table")
                if 'updated_at' not in columns:
                    db.session.execute(text("ALTER TABLE student_request ADD COLUMN updated_at TIMESTAMP"))
                    db.session.commit()
                    print("Added missing 'updated_at' column to student_request table")
            except Exception as e:
                print(f"Note: Could not check/update student_request table: {e}")

            try:
                result = db.session.execute(text("PRAGMA table_info(notification)"))
                columns = [row[1] for row in result]
                if 'recipient_type' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN recipient_type TEXT"))
                    db.session.commit()
                if 'recipient_id' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN recipient_id TEXT"))
                    db.session.commit()
                if 'sender' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN sender TEXT DEFAULT 'System'"))
                    db.session.commit()
                if 'title' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN title TEXT"))
                    db.session.commit()
                if 'message' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN message TEXT"))
                    db.session.commit()
                if 'category' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN category TEXT DEFAULT 'info'"))
                    db.session.commit()
                if 'status_label' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN status_label TEXT"))
                    db.session.commit()
                if 'is_read' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN is_read BOOLEAN DEFAULT 0"))
                    db.session.commit()
                if 'created_at' not in columns:
                    db.session.execute(text("ALTER TABLE notification ADD COLUMN created_at TIMESTAMP"))
                    db.session.commit()
            except Exception as e:
                print(f"Note: Could not check/update notification table: {e}")

            try:
                result = db.session.execute(text("PRAGMA table_info(student_record)"))
                columns = [row[1] for row in result]
                if 'purpose' not in columns:
                    db.session.execute(text("ALTER TABLE student_record ADD COLUMN purpose TEXT"))
                    db.session.commit()
                    print("Added missing 'purpose' column to student_record table")
            except Exception as e:
                print(f"Note: Could not check/update student_record.purpose column: {e}")

            try:
                admin_password_info = db.session.execute(text("PRAGMA table_info(admin)")).fetchall()
                student_password_info = db.session.execute(text("PRAGMA table_info(student_user)")).fetchall()
                admin_password_column = next((row for row in admin_password_info if row[1] == 'password'), None)
                student_password_column = next((row for row in student_password_info if row[1] == 'password'), None)

                if admin_password_column and student_password_column:
                    admin_type = str(admin_password_column[2]).upper()
                    student_type = str(student_password_column[2]).upper()
                    if '255' not in admin_type or '255' not in student_type:
                        migrate_sqlite_password_columns()
            except Exception as e:
                print(f"Note: Could not expand password column sizes: {e}")
        else:
            print(f"Using {engine_name} database; skipping SQLite-specific schema patch checks.")

        try:
            migrate_contact_messages_to_conversations()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Note: Could not migrate legacy contact messages to threaded conversations: {e}")

        if not Admin.query.filter_by(username="admin").first():
            default_admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
            admin = Admin(
                username="admin",
                password=hash_password(default_admin_password),
                fullname="System Administrator"
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin created with username 'admin'.")

init_db()

if __name__ == "__main__":
    print("StudTech is running! Open http://127.0.0.1:5000 in your browser")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)








