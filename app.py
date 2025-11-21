"""
UCU Study Room Reservation System - Flask Web Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from functools import wraps
import os
from datetime import datetime, date, timedelta
from main import DatabaseManager, DataInitializer
from database_service import DatabaseService

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
# Configure session lifetime for permanent sessions (7 days)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Database configuration - will be set dynamically
DB_CONFIG = {}

# Global database manager and service (will be initialized after DB_CONFIG is set)
db = None
db_service = None


def get_db_config():
    """Prompt user for database configuration"""
    # Check for environment variables first (Docker mode)
    if os.environ.get('DB_HOST'):
        config = {
            'host': os.environ.get('DB_HOST', 'db'),
            'user': os.environ.get('DB_USER', 'root'),
            'password': os.environ.get('DB_PASSWORD', 'rootpassword'),
            'database': os.environ.get('DB_NAME', 'UCU_SalasDeEstudio')
        }
        print("\n" + "="*60)
        print("Database Configuration")
        print("="*60)
        print("\nUsing environment variables for database connection...")
        return config
    
    # Built-in default credentials
    builtin_config = {
        'host': '100.100.101.1',
        'user': 'root',
        'password': '220505',
        'database': 'UCU_SalasDeEstudio'
    }
    
    # Check if stdin is available (not running in background/non-interactive mode)
    import sys
    if not sys.stdin.isatty():
        # Non-interactive mode - use built-in credentials
        print("\n" + "="*60)
        print("Database Configuration")
        print("="*60)
        print("\nNon-interactive mode detected. Using built-in credentials...")
        return builtin_config
    
    print("\n" + "="*60)
    print("Database Configuration")
    print("="*60)
    print("\nChoose an option:")
    print("1. Use built-in access credentials")
    print("2. Input new credentials")
    
    while True:
        try:
            choice = input("\nEnter your choice (1 or 2): ").strip()
        except (EOFError, KeyboardInterrupt):
            # If input is not available, default to built-in credentials
            print("\nInput not available. Using built-in credentials...")
            return builtin_config
        
        if choice == '1':
            print("\nUsing built-in credentials...")
            return builtin_config
        elif choice == '2':
            print("\nPlease enter database credentials (press Enter to use default):")
            try:
                host = input("Host (default: 100.100.101.1): ").strip() or '100.100.101.1'
                user = input("User (default: root): ").strip() or 'root'
                password = input("Password (default: 220505): ").strip() or '220505'
                database = input("Database (default: UCU_SalasDeEstudio): ").strip() or 'UCU_SalasDeEstudio'
            except (EOFError, KeyboardInterrupt):
                print("\nInput interrupted. Using built-in credentials...")
                return builtin_config
            
            return {
                'host': host,
                'user': user,
                'password': password,
                'database': database
            }
        else:
            print("Invalid choice. Please enter 1 or 2.")


def init_db():
    """Initialize database connection and service"""
    global db, db_service
    
    # Initialize database manager if not already done
    if db is None:
        db = DatabaseManager(**DB_CONFIG)
    
    if not db.connection or not db.connection.is_connected():
        db.config.update(DB_CONFIG)
        if not db.connect():
            return False
    
    # Initialize database service
    db_service = DatabaseService(db)
    
    # Initialize sample data if needed
    initializer = DataInitializer(db)
    initializer.check_and_populate()
    
    return True


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin privileges - validates token for security"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Ensure db_service is initialized
        if db_service is None:
            if not init_db():
                flash('Error de conexión a la base de datos. Por favor, intenta nuevamente.', 'error')
                return redirect(url_for('login'))
        
        # First check session
        user = session.get('user', {})
        is_admin_session = user.get('is_admin', False)
        
        # Validate token from cookie if available
        access_token = request.cookies.get('access_token')
        is_admin_token = False
        token_valid = False
        
        if access_token:
            try:
                token_user = db_service.validate_access_token(access_token)
                if token_user:
                    token_valid = True
                    is_admin_token = token_user.get('is_admin', False)
                    # Update session with token data (token is source of truth)
                    session['user'] = token_user
                    session.permanent = True
                    session.modified = True
            except Exception:
                # If token validation fails due to error, fall back to session check
                pass
        
        # Primary check: If session says user is admin, allow access
        # This handles immediate post-login access where token might not be validated yet
        if is_admin_session:
            # Session indicates admin - allow access
            # Token validation is secondary security check
            if access_token and not token_valid:
                # Token exists but validation failed - this is suspicious but allow if session is valid
                # The session was just set during login, so it's trustworthy
                pass
            return f(*args, **kwargs)
        
        # Secondary check: If token says user is admin, allow access
        if is_admin_token:
            return f(*args, **kwargs)
        
        # Neither session nor token indicates admin access
        flash('Acceso denegado. Se requieren privilegios de administrador.', 'error')
        return redirect(url_for('dashboard'))
    return decorated_function


@app.before_request
def before_request():
    """Initialize database before each request and check for access tokens"""
    if db is None or not db.connection or not db.connection.is_connected():
        init_db()
    
    # Cleanup expired tokens periodically (every 100 requests, approximate)
    # Only if db_service is initialized
    if db_service is not None:
        import random
        if random.randint(1, 100) == 1:
            db_service.cleanup_expired_tokens()
    
    # Ensure db_service is initialized before using it
    if db_service is None:
        if not init_db():
            return  # Can't proceed without database
    
    # If user is already in session, keep it (don't clear on first request after login)
    # Only validate/update from token if no session exists or if token is present
    access_token = request.cookies.get('access_token')
    
    if 'user' in session:
        # Session exists - validate token if present, but don't clear session if token is missing
        # (token might not be set yet on the first request after login)
        if access_token:
            token_user = db_service.validate_access_token(access_token)
            if token_user:
                # Token is valid, update session with latest info
                session['user'] = token_user
                session.permanent = True
                session.modified = True
            # If token is invalid but session exists, don't clear it immediately
            # (might be a temporary issue or token not yet propagated)
    else:
        # No session - try to restore from token
        if access_token:
            token_user = db_service.validate_access_token(access_token)
            if token_user:
                # Token is valid, restore session
                session['user'] = token_user
                session.permanent = True
                session.modified = True


@app.route('/')
def index():
    """Home page"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    # If user is already logged in, redirect to dashboard
    if 'user' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('login.html')
        
        # Ensure db_service is initialized
        if db_service is None:
            if not init_db():
                flash('Error de conexión a la base de datos. Por favor, intenta nuevamente.', 'error')
                return render_template('login.html')
        
        user = db_service.login(email, password)
        if user:
            # Generate access token
            is_admin = user.get('is_admin', False)
            access_token = db_service.generate_access_token(user['ci'], is_admin)
            
            if access_token:
                # Set session and mark as permanent to ensure it's saved
                session['user'] = user
                session.permanent = True
                session.modified = True  # Explicitly mark session as modified
                
                # Set flash message
                flash(f'¡Bienvenido, {user["nombre"]} {user["apellido"]}!', 'success')
                
                # Create redirect response with cookie
                # Flask will automatically save the session when this response is returned
                response = make_response(redirect(url_for('dashboard')))
                response.set_cookie(
                    'access_token',
                    access_token,
                    max_age=7*24*60*60,  # 7 days in seconds
                    httponly=True,  # Prevent JavaScript access (XSS protection)
                    secure=False,  # Set to True in production with HTTPS
                    samesite='Lax'  # CSRF protection
                )
                
                return response
            else:
                flash('Error al generar token de acceso. Por favor, intenta nuevamente.', 'error')
        else:
            flash('Email o contraseña incorrectos.', 'error')
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        ci = request.form.get('ci', '').strip()
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password_confirm = request.form.get('password_confirm', '')
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        rol = request.form.get('rol', 'alumno').strip()
        
        if not all([ci, nombre, apellido, email, password]):
            flash('Por favor, completa todos los campos obligatorios.', 'error')
            return render_template('register.html', programas=db_service.get_programas())
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('register.html', programas=db_service.get_programas())
        
        if db_service.register(ci, nombre, apellido, email, password):
            # Associate with program if provided
            if nombre_programa and id_facultad:
                success, message = db_service.add_participante_program(ci, nombre_programa, int(id_facultad), rol)
                if not success:
                    flash(f'Usuario creado pero error al asociar programa: {message}', 'warning')
            
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error al registrar usuario. El CI o email ya existe.', 'error')
    
    return render_template('register.html', programas=db_service.get_programas())


@app.route('/logout')
def logout():
    """User logout"""
    # Revoke access token if present
    access_token = request.cookies.get('access_token')
    if access_token:
        db_service.revoke_access_token(access_token)
    
    # Clear session
    session.pop('user', None)
    
    # Create response and clear cookie
    response = make_response(redirect(url_for('login')))
    response.set_cookie('access_token', '', expires=0)
    flash('Sesión cerrada exitosamente.', 'info')
    return response


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page - different for admin vs regular users"""
    user = session['user']
    is_admin = user.get('is_admin', False)
    
    if is_admin:
        # Admin dashboard
        stats = db_service.get_dashboard_stats()
        return render_template('dashboard.html',
                             participantes_count=stats['participantes_count'],
                             salas_count=stats['salas_count'],
                             reservas_activas_count=stats['reservas_activas_count'],
                             sanciones_activas_count=stats['sanciones_activas_count'],
                             is_admin=True)
    else:
        # User dashboard - show their reservations and sanctions
        user_role = db_service.get_user_role(user['ci'])
        if not user_role:
            flash('Por favor, agrega tu programa académico para poder usar todas las funcionalidades.', 'warning')
        
        # Get user's reservations
        reservas = db_service.get_user_reservas(user['ci'])
        # Filter to only active reservations for the count
        reservas_activas = [r for r in reservas if r['estado'] == 'activa']
        # Get user's active sanctions
        sanciones = db_service.get_user_sanciones(user['ci'])
        # Get count of available rooms at current time
        salas_disponibles_count = db_service.count_available_salas_now()
        
        return render_template('user_dashboard.html',
                             reservas=reservas,
                             reservas_activas_count=len(reservas_activas),
                             sanciones=sanciones,
                             has_program=user_role is not None,
                             is_admin=False,
                             salas_disponibles_count=salas_disponibles_count)


@app.route('/add-program', methods=['GET', 'POST'])
@login_required
def add_program():
    """Add program association for current user"""
    # Check if user already has a program
    user_role = db_service.get_user_role(session['user']['ci'])
    if user_role:
        flash('Ya tienes un programa académico asociado.', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        rol = request.form.get('rol', 'alumno').strip()
        
        # If id_facultad is empty, try to get it from the selected programa
        if not id_facultad and nombre_programa:
            # Find the program in the list
            programas = db_service.get_programas()
            for prog in programas:
                if prog['nombre_programa'] == nombre_programa:
                    id_facultad = str(prog['id_facultad'])
                    break
        
        if not nombre_programa or not id_facultad:
            flash('Por favor, selecciona un programa académico completo.', 'error')
            return render_template('add_program.html', programas=db_service.get_programas())
        
        try:
            id_facultad_int = int(id_facultad)
            success, message = db_service.add_participante_program(session['user']['ci'], nombre_programa, id_facultad_int, rol)
            if success:
                flash('Programa académico agregado exitosamente. Ahora puedes hacer reservas.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash(f'Error al agregar programa: {message}', 'error')
        except Exception as e:
            flash(f'Error al agregar programa: {str(e)}', 'error')
    
    return render_template('add_program.html', programas=db_service.get_programas())


# ==================== USER-FACING ROUTES ====================

@app.route('/rooms')
@login_required
def view_rooms():
    """View available rooms - user-facing"""
    from datetime import time
    
    fecha_str = request.args.get('fecha', '')
    id_turno_inicio = request.args.get('id_turno_inicio', '')
    id_turno_fin = request.args.get('id_turno_fin', '')
    
    fecha = None
    hora_inicio = None
    hora_fin = None
    
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except ValueError:
            flash('Fecha inválida.', 'error')
    
    # Get all turnos to find the selected ones
    turnos = db_service.get_turnos()
    turnos_dict = {t['id_turno']: t for t in turnos}
    
    if id_turno_inicio:
        try:
            turno_id = int(id_turno_inicio)
            if turno_id in turnos_dict:
                hora_inicio = turnos_dict[turno_id]['hora_inicio']
        except (ValueError, KeyError):
            flash('Turno de inicio inválido.', 'error')
    
    if id_turno_fin:
        try:
            turno_id = int(id_turno_fin)
            if turno_id in turnos_dict:
                hora_fin = turnos_dict[turno_id]['hora_fin']
        except (ValueError, KeyError):
            flash('Turno de fin inválido.', 'error')
    
    # Validate time range
    if hora_inicio and hora_fin and hora_fin <= hora_inicio:
        flash('La hora de fin debe ser posterior a la hora de inicio.', 'error')
        hora_inicio = None
        hora_fin = None
    
    # Get user role for filtering rooms by access
    user_role = db_service.get_user_role(session['user']['ci'])
    rol = user_role.get('rol', 'alumno') if user_role else 'alumno'
    tipo_programa = user_role.get('tipo', 'grado') if user_role else 'grado'
    
    # Get available rooms (filtered by date, time range, and user access)
    salas = db_service.get_available_salas(fecha, hora_inicio, hora_fin, rol, tipo_programa)
    
    return render_template('user/rooms.html', salas=salas, turnos=turnos, 
                         fecha=fecha_str, id_turno_inicio=id_turno_inicio, id_turno_fin=id_turno_fin)


@app.route('/my-sanctions')
@login_required
def my_sanctions():
    """View user's sanctions"""
    sanciones = db_service.get_user_sanciones(session['user']['ci'])
    today = date.today()
    return render_template('user/sanctions.html', sanciones=sanciones, today=today)


@app.route('/my-reservations')
@login_required
def my_reservations():
    """View user's reservations"""
    user = session.get('user', {})
    reservas = db_service.get_user_reservas(user['ci'])
    is_admin = user.get('is_admin', False)
    return render_template('user/reservations.html', reservas=reservas, is_admin=is_admin)


@app.route('/my-reservations/<int:id_reserva>/cancel', methods=['POST'])
@login_required
def cancel_my_reserva(id_reserva):
    """Cancel user's own reservation"""
    success, message = db_service.cancel_reserva(id_reserva, session['user']['ci'])
    if success:
        flash(message, 'success')
    else:
        flash(message, 'error')
    return redirect(url_for('my_reservations'))


@app.route('/make-appointment', methods=['GET', 'POST'])
@login_required
def make_appointment():
    """Make a room reservation - user-facing"""
    # Check if user has a role/program association
    user_role = db_service.get_user_role(session['user']['ci'])
    if not user_role:
        flash('No tienes un programa académico asociado. Por favor, agrega tu programa académico antes de hacer reservas.', 'error')
        return redirect(url_for('add_program'))
    
    # Get filtered rooms based on user role and program type
    rol = user_role.get('rol', 'alumno')
    tipo_programa = user_role.get('tipo', 'grado')
    salas = db_service.get_salas_for_user(rol, tipo_programa)
    
    if request.method == 'POST':
        nombre_sala = request.form.get('nombre_sala', '').strip()
        edificio = request.form.get('edificio', '').strip()
        fecha_str = request.form.get('fecha', '').strip()
        id_turno = request.form.get('id_turno', '').strip()
        participantes_str = request.form.get('participantes', '').strip()
        
        if not all([nombre_sala, edificio, fecha_str, id_turno]):
            flash('Por favor, completa todos los campos obligatorios.', 'error')
            return render_template('user/make_appointment.html', 
                                 salas=salas, 
                                 turnos=db_service.get_turnos())
        
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            id_turno_int = int(id_turno)
            participantes = [ci.strip() for ci in participantes_str.split(',') if ci.strip()]
            
            # Ensure current user is in participants
            if session['user']['ci'] not in participantes:
                participantes.insert(0, session['user']['ci'])
            
            success, message, id_reserva = db_service.create_reserva(
                session['user']['ci'],
                nombre_sala,
                edificio,
                fecha,
                id_turno_int,
                participantes
            )
            
            if success:
                flash('Reserva creada exitosamente.', 'success')
                return redirect(url_for('my_reservations'))
            else:
                flash(f'Error al crear reserva: {message}', 'error')
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'error')
    
    return render_template('user/make_appointment.html', 
                         salas=salas, 
                         turnos=db_service.get_turnos())


# ==================== ADMIN ROUTES - PARTICIPANTS ====================

@app.route('/admin/participantes')
@admin_required
def admin_list_participantes():
    """List all participants - admin only"""
    participantes = db_service.get_all_participantes()
    return render_template('participantes/list.html', participantes=participantes)


@app.route('/admin/participantes/create', methods=['GET', 'POST'])
@admin_required
def admin_create_participante():
    """Create new participant - admin only"""
    if request.method == 'POST':
        ci = request.form.get('ci', '').strip()
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        rol = request.form.get('rol', 'alumno').strip()
        
        if not all([ci, nombre, apellido, email]):
            flash('Por favor, completa todos los campos obligatorios.', 'error')
            return render_template('participantes/create.html', programas=db_service.get_programas())
        
        success, message = db_service.create_participante(ci, nombre, apellido, email, password, nombre_programa, int(id_facultad) if id_facultad else None, rol)
        if success:
            flash('Participante creado exitosamente.', 'success')
            return redirect(url_for('admin_list_participantes'))
        else:
            flash(f'Error: {message}', 'error')
    
    return render_template('participantes/create.html', programas=db_service.get_programas())


@app.route('/admin/participantes/<ci>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_participante(ci):
    """Edit participant - admin only"""
    participante = db_service.get_participante(ci)
    if not participante:
        flash('Participante no encontrado.', 'error')
        return redirect(url_for('admin_list_participantes'))
    
    current_programs = db_service.get_participante_programs(ci)
    
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip()
        
        # Check if adding a new program
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        rol = request.form.get('rol', 'alumno').strip()
        
        if not all([nombre, apellido, email]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('participantes/edit.html', participante=participante, programas=db_service.get_programas(), current_programs=current_programs)
        
        success, message = db_service.update_participante(ci, nombre, apellido, email)
        if not success:
            flash(f'Error: {message}', 'error')
            return render_template('participantes/edit.html', participante=participante, programas=db_service.get_programas(), current_programs=current_programs)
        
        # Add program if provided
        if nombre_programa and id_facultad:
            success, message = db_service.add_participante_program(ci, nombre_programa, int(id_facultad), rol)
            if success:
                flash('Participante y programa académico actualizados exitosamente.', 'success')
            else:
                flash(f'Participante actualizado. {message}', 'info')
        else:
            flash('Participante actualizado exitosamente.', 'success')
        
        return redirect(url_for('admin_list_participantes'))
    
    return render_template('participantes/edit.html', participante=participante, programas=db_service.get_programas(), current_programs=current_programs)


@app.route('/admin/participantes/<ci>/remove-program', methods=['POST'])
@admin_required
def admin_remove_program(ci):
    """Remove program association from participant - admin only"""
    nombre_programa = request.form.get('nombre_programa', '').strip()
    id_facultad = request.form.get('id_facultad', '').strip()
    
    if not nombre_programa or not id_facultad:
        flash('Error: Faltan datos del programa.', 'error')
        return redirect(url_for('admin_edit_participante', ci=ci))
    
    success, message = db_service.remove_participante_program(ci, nombre_programa, int(id_facultad))
    if success:
        flash('Programa académico eliminado exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    
    return redirect(url_for('admin_edit_participante', ci=ci))


@app.route('/admin/participantes/<ci>/delete', methods=['POST'])
@admin_required
def admin_delete_participante(ci):
    """Delete participant - admin only"""
    success, message = db_service.delete_participante(ci)
    if success:
        flash('Participante eliminado exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    return redirect(url_for('admin_list_participantes'))


# ==================== ADMIN ROUTES - PROGRAMS ====================

@app.route('/admin/programas')
@admin_required
def admin_list_programas():
    """List all academic programs - admin only"""
    programas = db_service.get_all_programas()
    return render_template('programas/list.html', programas=programas)


@app.route('/admin/programas/create', methods=['GET', 'POST'])
@admin_required
def admin_create_programa():
    """Create new academic program - admin only"""
    if request.method == 'POST':
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        tipo = request.form.get('tipo', 'grado').strip()
        
        if not all([nombre_programa, id_facultad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('programas/create.html', facultades=db_service.get_facultades())
        
        success, message = db_service.create_programa(nombre_programa, int(id_facultad), tipo)
        if success:
            flash('Programa académico creado exitosamente.', 'success')
            return redirect(url_for('admin_list_programas'))
        else:
            flash(f'Error: {message}', 'error')
    
    return render_template('programas/create.html', facultades=db_service.get_facultades())


@app.route('/admin/programas/<nombre_programa>/<int:id_facultad>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_programa(nombre_programa, id_facultad):
    """Edit academic program - admin only"""
    programa = db_service.get_programa(nombre_programa, id_facultad)
    if not programa:
        flash('Programa no encontrado.', 'error')
        return redirect(url_for('admin_list_programas'))
    
    if request.method == 'POST':
        nuevo_nombre = request.form.get('nombre_programa', '').strip()
        nuevo_id_facultad = request.form.get('id_facultad', '').strip()
        tipo = request.form.get('tipo', 'grado').strip()
        
        if not all([nuevo_nombre, nuevo_id_facultad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('programas/edit.html', programa=programa, facultades=db_service.get_facultades())
        
        success, message = db_service.update_programa(nombre_programa, id_facultad, nuevo_nombre, int(nuevo_id_facultad), tipo)
        if success:
            flash('Programa académico actualizado exitosamente.', 'success')
            return redirect(url_for('admin_list_programas'))
        else:
            flash(f'Error: {message}', 'error')
    
    return render_template('programas/edit.html', programa=programa, facultades=db_service.get_facultades())


@app.route('/admin/programas/<nombre_programa>/<int:id_facultad>/delete', methods=['POST'])
@admin_required
def admin_delete_programa(nombre_programa, id_facultad):
    """Delete academic program - admin only"""
    success, message = db_service.delete_programa(nombre_programa, id_facultad)
    if success:
        flash('Programa académico eliminado exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    return redirect(url_for('admin_list_programas'))


# ==================== ADMIN ROUTES - ROOMS ====================

@app.route('/admin/salas')
@admin_required
def admin_list_salas():
    """List all rooms - admin only"""
    salas = db_service.get_all_salas()
    return render_template('salas/list.html', salas=salas)


@app.route('/admin/salas/create', methods=['GET', 'POST'])
@admin_required
def admin_create_sala():
    """Create new room - admin only"""
    if request.method == 'POST':
        nombre_sala = request.form.get('nombre_sala', '').strip()
        edificio = request.form.get('edificio', '').strip()
        capacidad = request.form.get('capacidad', '').strip()
        tipo_sala = request.form.get('tipo_sala', 'libre').strip()
        
        if not all([nombre_sala, edificio, capacidad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('salas/create.html', edificios=db_service.get_edificios())
        
        try:
            capacidad_int = int(capacidad)
            success, message = db_service.create_sala(nombre_sala, edificio, capacidad_int, tipo_sala)
            if success:
                flash('Sala creada exitosamente.', 'success')
                return redirect(url_for('admin_list_salas'))
            else:
                flash(f'Error: {message}', 'error')
        except ValueError:
            flash('Capacidad debe ser un número.', 'error')
    
    return render_template('salas/create.html', edificios=db_service.get_edificios())


@app.route('/admin/salas/<edificio>/<nombre_sala>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_sala(edificio, nombre_sala):
    """Edit room - admin only"""
    sala = db_service.get_sala(nombre_sala, edificio)
    if not sala:
        flash('Sala no encontrada.', 'error')
        return redirect(url_for('admin_list_salas'))
    
    if request.method == 'POST':
        capacidad = request.form.get('capacidad', '').strip()
        tipo_sala = request.form.get('tipo_sala', 'libre').strip()
        
        try:
            capacidad_int = int(capacidad)
            success, message = db_service.update_sala(nombre_sala, edificio, capacidad_int, tipo_sala)
            if success:
                flash('Sala actualizada exitosamente.', 'success')
                return redirect(url_for('admin_list_salas'))
            else:
                flash(f'Error: {message}', 'error')
        except ValueError:
            flash('Capacidad debe ser un número.', 'error')
    
    return render_template('salas/edit.html', sala=sala, edificios=db_service.get_edificios())


@app.route('/admin/salas/<edificio>/<nombre_sala>/delete', methods=['POST'])
@admin_required
def admin_delete_sala(edificio, nombre_sala):
    """Delete room - admin only"""
    success, message = db_service.delete_sala(nombre_sala, edificio)
    if success:
        flash('Sala eliminada exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    return redirect(url_for('admin_list_salas'))


# ==================== ADMIN ROUTES - RESERVATIONS ====================

@app.route('/admin/reservas')
@admin_required
def admin_list_reservas():
    """List all reservations - admin only"""
    reservas = db_service.get_all_reservas()
    return render_template('reservas/list.html', reservas=reservas)


@app.route('/admin/reservas/<int:id_reserva>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_reserva(id_reserva):
    """Edit reservation - admin only"""
    reserva = db_service.get_reserva(id_reserva)
    if not reserva:
        flash('Reserva no encontrada.', 'error')
        return redirect(url_for('admin_list_reservas'))
    
    if request.method == 'POST':
        estado = request.form.get('estado', '').strip()
        success, message = db_service.update_reserva_estado(id_reserva, estado)
        if success:
            flash('Reserva actualizada exitosamente.', 'success')
            return redirect(url_for('admin_list_reservas'))
        else:
            flash(f'Error: {message}', 'error')
    
    participantes = db_service.get_reserva_participantes(id_reserva)
    return render_template('reservas/edit.html', reserva=reserva, participantes=participantes)


@app.route('/admin/reservas/<int:id_reserva>/attendance', methods=['GET', 'POST'])
@admin_required
def admin_update_attendance(id_reserva):
    """Update attendance for a reservation - admin only"""
    reserva = db_service.get_reserva(id_reserva)
    if not reserva:
        flash('Reserva no encontrada.', 'error')
        return redirect(url_for('admin_list_reservas'))
    
    participantes = db_service.get_reserva_participantes(id_reserva)
    
    if request.method == 'POST':
        asistencias = []
        participantes_ci = []
        for p in participantes:
            asistencia = request.form.get(f"asistencia_{p['ci_participante']}", 'false')
            asistencias.append(asistencia == 'true')
            participantes_ci.append(p['ci_participante'])
        
        if db_service.update_attendance(id_reserva, participantes_ci, asistencias):
            flash('Asistencia actualizada exitosamente.', 'success')
            return redirect(url_for('admin_list_reservas'))
        else:
            flash('Error al actualizar asistencia.', 'error')
    
    return render_template('reservas/attendance.html', reserva=reserva, participantes=participantes)


@app.route('/admin/reservas/<int:id_reserva>/delete', methods=['POST'])
@admin_required
def admin_delete_reserva(id_reserva):
    """Delete reservation - admin only"""
    success, message = db_service.delete_reserva(id_reserva)
    if success:
        flash('Reserva eliminada exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    return redirect(url_for('admin_list_reservas'))


# ==================== ADMIN ROUTES - SANCTIONS ====================

@app.route('/admin/sanciones')
@admin_required
def admin_list_sanciones():
    """List all sanctions - admin only"""
    sanciones = db_service.get_all_sanciones()
    today = date.today()
    return render_template('sanciones/list.html', sanciones=sanciones, today=today)


@app.route('/admin/sanciones/create', methods=['GET', 'POST'])
@admin_required
def admin_create_sancion():
    """Create new sanction - admin only"""
    if request.method == 'POST':
        ci_participante = request.form.get('ci_participante', '').strip()
        fecha_inicio_str = request.form.get('fecha_inicio', '').strip()
        fecha_fin_str = request.form.get('fecha_fin', '').strip()
        
        if not all([ci_participante, fecha_inicio_str, fecha_fin_str]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('sanciones/create.html', participantes=db_service.get_participantes_list())
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            
            success, message = db_service.create_sancion(ci_participante, fecha_inicio, fecha_fin)
            if success:
                flash('Sanción creada exitosamente.', 'success')
                return redirect(url_for('admin_list_sanciones'))
            else:
                flash(f'Error: {message}', 'error')
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'error')
    
    return render_template('sanciones/create.html', participantes=db_service.get_participantes_list())


@app.route('/admin/sanciones/<int:id_sancion>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_sancion(id_sancion):
    """Edit sanction - admin only"""
    sancion = db_service.get_sancion(id_sancion)
    if not sancion:
        flash('Sanción no encontrada.', 'error')
        return redirect(url_for('admin_list_sanciones'))
    
    if request.method == 'POST':
        fecha_inicio_str = request.form.get('fecha_inicio', '').strip()
        fecha_fin_str = request.form.get('fecha_fin', '').strip()
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            
            success, message = db_service.update_sancion(id_sancion, fecha_inicio, fecha_fin)
            if success:
                flash('Sanción actualizada exitosamente.', 'success')
                return redirect(url_for('admin_list_sanciones'))
            else:
                flash(f'Error: {message}', 'error')
        except ValueError:
            flash('Formato de fecha inválido. Use YYYY-MM-DD.', 'error')
    
    return render_template('sanciones/edit.html', sancion=sancion)


@app.route('/admin/sanciones/<int:id_sancion>/delete', methods=['POST'])
@admin_required
def admin_delete_sancion(id_sancion):
    """Delete sanction - admin only"""
    success, message = db_service.delete_sancion(id_sancion)
    if success:
        flash('Sanción eliminada exitosamente.', 'success')
    else:
        flash(f'Error: {message}', 'error')
    return redirect(url_for('admin_list_sanciones'))


# ==================== ADMIN ROUTES - REPORTS ====================

@app.route('/admin/reportes')
@admin_required
def admin_reportes():
    """Reports dashboard - admin only"""
    return render_template('reportes/index.html')


@app.route('/admin/reportes/salas-mas-reservadas')
@admin_required
def admin_reporte_salas_mas_reservadas():
    """Most reserved rooms - admin only"""
    query = """
        SELECT s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad,
               COUNT(r.id_reserva) as total_reservas
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        GROUP BY s.nombre_sala, s.edificio, s.tipo_sala, s.capacidad
        ORDER BY total_reservas DESC, s.edificio, s.nombre_sala
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/salas_mas_reservadas.html', results=results)


@app.route('/admin/reportes/turnos-mas-demandados')
@admin_required
def admin_reporte_turnos_mas_demandados():
    """Most demanded time slots - admin only"""
    query = """
        SELECT t.id_turno, t.hora_inicio, t.hora_fin,
               COUNT(r.id_reserva) as total_reservas
        FROM turno t
        LEFT JOIN reserva r ON t.id_turno = r.id_turno
        GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
        ORDER BY total_reservas DESC, t.hora_inicio
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/turnos_mas_demandados.html', results=results)


@app.route('/admin/reportes/promedio-participantes-sala')
@admin_required
def admin_reporte_promedio_participantes_sala():
    """Average participants per room - admin only"""
    query = """
        SELECT s.nombre_sala, s.edificio, s.capacidad,
               COUNT(DISTINCT r.id_reserva) as total_reservas,
               COUNT(rp.ci_participante) as total_participantes,
               CASE 
                   WHEN COUNT(DISTINCT r.id_reserva) > 0 
                   THEN ROUND(COUNT(rp.ci_participante) / COUNT(DISTINCT r.id_reserva), 2)
                   ELSE 0 
               END as promedio_participantes
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
        GROUP BY s.nombre_sala, s.edificio, s.capacidad
        ORDER BY promedio_participantes DESC, s.edificio, s.nombre_sala
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/promedio_participantes_sala.html', results=results)


@app.route('/admin/reportes/reservas-por-carrera-facultad')
@admin_required
def admin_reporte_reservas_por_carrera_facultad():
    """Reservations per program and faculty - admin only"""
    query = """
        SELECT f.nombre as facultad, pa.nombre_programa, pa.tipo,
               COUNT(DISTINCT r.id_reserva) as total_reservas,
               COUNT(DISTINCT rp.ci_participante) as total_participantes
        FROM facultad f
        JOIN programa_academico pa ON f.id_facultad = pa.id_facultad
        LEFT JOIN participante_programa_academico ppa ON pa.nombre_programa = ppa.nombre_programa AND pa.id_facultad = ppa.id_facultad
        LEFT JOIN reserva_participante rp ON ppa.ci_participante = rp.ci_participante
        LEFT JOIN reserva r ON rp.id_reserva = r.id_reserva
        GROUP BY f.nombre, pa.nombre_programa, pa.tipo
        ORDER BY f.nombre, pa.nombre_programa
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/reservas_por_carrera_facultad.html', results=results)


@app.route('/admin/reportes/ocupacion-por-edificio')
@admin_required
def admin_reporte_ocupacion_por_edificio():
    """Room occupancy percentage per building - admin only"""
    query = """
        SELECT e.nombre_edificio, e.direccion,
               COUNT(DISTINCT s.nombre_sala) as total_salas,
               COUNT(DISTINCT CASE WHEN r.estado = 'activa' THEN r.id_reserva END) as reservas_activas,
               COUNT(DISTINCT r.id_reserva) as total_reservas,
               CASE 
                   WHEN COUNT(DISTINCT s.nombre_sala) > 0 
                   THEN ROUND((COUNT(DISTINCT CASE WHEN r.estado = 'activa' THEN r.id_reserva END) * 100.0) / COUNT(DISTINCT s.nombre_sala), 2)
                   ELSE 0 
               END as porcentaje_ocupacion
        FROM edificio e
        LEFT JOIN sala s ON e.nombre_edificio = s.edificio
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        GROUP BY e.nombre_edificio, e.direccion
        ORDER BY porcentaje_ocupacion DESC, e.nombre_edificio
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/ocupacion_por_edificio.html', results=results)


@app.route('/admin/reportes/reservas-asistencias-profesores-alumnos')
@admin_required
def admin_reporte_reservas_asistencias_profesores_alumnos():
    """Reservations and attendances for teachers and students - admin only"""
    query = """
        SELECT ppa.rol, pa.tipo,
               COUNT(DISTINCT r.id_reserva) as total_reservas,
               COUNT(DISTINCT CASE WHEN rp.asistencia = TRUE THEN r.id_reserva END) as reservas_con_asistencia,
               COUNT(rp.ci_participante) as total_participaciones,
               SUM(CASE WHEN rp.asistencia = TRUE THEN 1 ELSE 0 END) as total_asistencias,
               CASE 
                   WHEN COUNT(rp.ci_participante) > 0 
                   THEN ROUND((SUM(CASE WHEN rp.asistencia = TRUE THEN 1 ELSE 0 END) * 100.0) / COUNT(rp.ci_participante), 2)
                   ELSE 0 
               END as porcentaje_asistencia
        FROM participante_programa_academico ppa
        JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa AND ppa.id_facultad = pa.id_facultad
        LEFT JOIN reserva_participante rp ON ppa.ci_participante = rp.ci_participante
        LEFT JOIN reserva r ON rp.id_reserva = r.id_reserva
        GROUP BY ppa.rol, pa.tipo
        ORDER BY ppa.rol, pa.tipo
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/reservas_asistencias_profesores_alumnos.html', results=results)


@app.route('/admin/reportes/sanciones-profesores-alumnos')
@admin_required
def admin_reporte_sanciones_profesores_alumnos():
    """Sanctions for teachers and students - admin only"""
    query = """
        SELECT ppa.rol, pa.tipo,
               COUNT(DISTINCT sp.id_sancion) as total_sanciones,
               COUNT(DISTINCT sp.ci_participante) as participantes_sancionados
        FROM participante_programa_academico ppa
        JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa AND ppa.id_facultad = pa.id_facultad
        LEFT JOIN sancion_participante sp ON ppa.ci_participante = sp.ci_participante
        WHERE sp.fecha_fin >= CURDATE() OR sp.id_sancion IS NULL
        GROUP BY ppa.rol, pa.tipo
        ORDER BY ppa.rol, pa.tipo
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/sanciones_profesores_alumnos.html', results=results)


@app.route('/admin/reportes/porcentaje-reservas-utilizadas')
@admin_required
def admin_reporte_porcentaje_reservas_utilizadas():
    """Percentage of used vs canceled/no-show reservations - admin only"""
    query = """
        SELECT 
            COUNT(*) as total_reservas,
            SUM(CASE WHEN estado = 'activa' THEN 1 ELSE 0 END) as reservas_activas,
            SUM(CASE WHEN estado = 'finalizada' THEN 1 ELSE 0 END) as reservas_finalizadas,
            SUM(CASE WHEN estado = 'cancelada' THEN 1 ELSE 0 END) as reservas_canceladas,
            SUM(CASE WHEN estado = 'sin asistencia' THEN 1 ELSE 0 END) as reservas_sin_asistencia,
            CASE 
                WHEN COUNT(*) > 0 
                THEN ROUND((SUM(CASE WHEN estado = 'finalizada' THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 2)
                ELSE 0 
            END as porcentaje_utilizadas,
            CASE 
                WHEN COUNT(*) > 0 
                THEN ROUND(((SUM(CASE WHEN estado = 'cancelada' THEN 1 ELSE 0 END) + SUM(CASE WHEN estado = 'sin asistencia' THEN 1 ELSE 0 END)) * 100.0) / COUNT(*), 2)
                ELSE 0 
            END as porcentaje_no_utilizadas
        FROM reserva
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/porcentaje_reservas_utilizadas.html', results=results[0] if results else {})


@app.route('/admin/reportes/reservas-por-mes')
@admin_required
def admin_reporte_reservas_por_mes():
    """Reservations per month - admin only"""
    query = """
        SELECT 
            DATE_FORMAT(fecha, '%Y-%m') as mes,
            COUNT(*) as total_reservas,
            COUNT(DISTINCT nombre_sala, edificio) as salas_utilizadas,
            COUNT(DISTINCT rp.ci_participante) as participantes_unicos
        FROM reserva r
        LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
        GROUP BY DATE_FORMAT(fecha, '%Y-%m')
        ORDER BY mes DESC
    """
    results = db_service.db.execute_query(query, fetch=True) or []
    return render_template('reportes/reservas_por_mes.html', results=results)


@app.route('/admin/reportes/participantes-mas-activos')
@admin_required
def admin_reporte_participantes_mas_activos():
    """Most active participants - admin only"""
    query = """
        SELECT 
            p.ci, p.nombre, p.apellido, p.email,
            COUNT(DISTINCT r.id_reserva) as total_reservas,
            SUM(CASE WHEN rp.asistencia = TRUE THEN 1 ELSE 0 END) as total_asistencias,
            COUNT(DISTINCT sp.id_sancion) as total_sanciones
        FROM participante p
        LEFT JOIN reserva_participante rp ON p.ci = rp.ci_participante
        LEFT JOIN reserva r ON rp.id_reserva = r.id_reserva
        LEFT JOIN sancion_participante sp ON p.ci = sp.ci_participante
        GROUP BY p.ci, p.nombre, p.apellido, p.email
        HAVING total_reservas > 0
        ORDER BY total_reservas DESC, total_asistencias DESC
        LIMIT 20
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/participantes_mas_activos.html', results=results)


@app.route('/admin/reportes/eficiencia-uso-salas')
@admin_required
def admin_reporte_eficiencia_uso_salas():
    """Room usage efficiency - admin only"""
    query = """
        SELECT 
            s.nombre_sala, s.edificio, s.capacidad, s.tipo_sala,
            COUNT(DISTINCT r.id_reserva) as total_reservas,
            AVG((SELECT COUNT(*) FROM reserva_participante rp2 WHERE rp2.id_reserva = r.id_reserva)) as promedio_participantes,
            SUM(CASE WHEN r.estado = 'finalizada' THEN 1 ELSE 0 END) as reservas_completadas,
            SUM(CASE WHEN r.estado = 'sin asistencia' THEN 1 ELSE 0 END) as reservas_no_asistidas,
            CASE 
                WHEN COUNT(DISTINCT r.id_reserva) > 0 
                THEN ROUND((SUM(CASE WHEN r.estado = 'finalizada' THEN 1 ELSE 0 END) * 100.0) / COUNT(DISTINCT r.id_reserva), 2)
                ELSE 0 
            END as tasa_uso
        FROM sala s
        LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
        GROUP BY s.nombre_sala, s.edificio, s.capacidad, s.tipo_sala
        ORDER BY tasa_uso DESC, total_reservas DESC
    """
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/eficiencia_uso_salas.html', results=results)


if __name__ == '__main__':
    import os
    import json
    
    # Flask's reloader runs the main block twice (parent and child process)
    # Use environment variable to cache config and avoid double prompts
    config_env_key = 'FLASK_DB_CONFIG'
    
    # Check if config is already cached in environment variable
    if config_env_key in os.environ:
        # Load config from environment variable
        DB_CONFIG.update(json.loads(os.environ[config_env_key]))
    else:
        # Get database configuration from user
        DB_CONFIG.update(get_db_config())
        # Cache it in environment variable for reloader
        os.environ[config_env_key] = json.dumps(DB_CONFIG)
    
    # Initialize database manager with the configuration
    db = DatabaseManager(**DB_CONFIG)
    
    # Initialize database connection and managers
    if init_db():
        # Only show success message in the main process (child of reloader)
        if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
            print("\n" + "="*60)
            print("Database connection established successfully!")
            print("Starting web server...")
            print("="*60 + "\n")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("\nError: Could not connect to database. Please check your configuration.")
