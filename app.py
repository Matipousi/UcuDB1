
"""
UCU Study Room Reservation System - Flask Web Application
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
from datetime import datetime, date, timedelta
from main import DatabaseManager, AuthManager, ReservationManager, ReportManager, DataInitializer

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - will be set dynamically
DB_CONFIG = {}

# Global database manager (will be initialized after DB_CONFIG is set)
db = None
auth = None
reservation = None
report = None


def get_db_config():
    """Prompt user for database configuration"""
    # Built-in default credentials
    builtin_config = {
        'host': '100.100.101.1',
        'user': 'root',
        'password': '220505',
        'database': 'UCU_SalasDeEstudio'
    }
    
    print("\n" + "="*60)
    print("Database Configuration")
    print("="*60)
    print("\nChoose an option:")
    print("1. Use built-in access credentials")
    print("2. Input new credentials")
    
    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        
        if choice == '1':
            print("\nUsing built-in credentials...")
            return builtin_config
        elif choice == '2':
            print("\nPlease enter database credentials (press Enter to use default):")
            host = input("Host (default: 100.100.101.1): ").strip() or '100.100.101.1'
            user = input("User (default: root): ").strip() or 'root'
            password = input("Password (default: 220505): ").strip() or '220505'
            database = input("Database (default: UCU_SalasDeEstudio): ").strip() or 'UCU_SalasDeEstudio'
            
            return {
                'host': host,
                'user': user,
                'password': password,
                'database': database
            }
        else:
            print("Invalid choice. Please enter 1 or 2.")


def init_db():
    """Initialize database connection and managers"""
    global db, auth, reservation, report
    
    # Initialize database manager if not already done
    if db is None:
        db = DatabaseManager(**DB_CONFIG)
    
    if not db.connection or not db.connection.is_connected():
        db.config.update(DB_CONFIG)
        if not db.connect():
            return False
    
    auth = AuthManager(db)
    reservation = ReservationManager(db)
    report = ReportManager(db)
    
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


@app.before_request
def before_request():
    """Initialize database before each request"""
    if db is None or not db.connection or not db.connection.is_connected():
        init_db()


@app.route('/')
def index():
    """Home page"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('login.html')
        
        user = auth.login(email, password)
        if user:
            session['user'] = user
            flash(f'¡Bienvenido, {user["nombre"]} {user["apellido"]}!', 'success')
            return redirect(url_for('dashboard'))
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
            return render_template('register.html', programas=get_programas())
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('register.html', programas=get_programas())
        
        if auth.register(ci, nombre, apellido, email, password):
            # Associate with program if provided
            if nombre_programa and id_facultad:
                try:
                    db.execute_query(
                        "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                        (ci, nombre_programa, int(id_facultad), rol)
                    )
                except Exception as e:
                    flash(f'Usuario creado pero error al asociar programa: {str(e)}', 'warning')
            
            flash('Registro exitoso. Por favor, inicia sesión.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Error al registrar usuario. El CI o email ya existe.', 'error')
    
    return render_template('register.html', programas=get_programas())


@app.route('/logout')
def logout():
    """User logout"""
    session.pop('user', None)
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    # Check if user has program association
    user_role = auth.get_user_role(session['user']['ci'])
    if not user_role:
        flash('Por favor, agrega tu programa académico para poder usar todas las funcionalidades.', 'warning')
    
    participantes_count = db.execute_fetchone("SELECT COUNT(*) as cnt FROM participante")['cnt']
    salas_count = db.execute_fetchone("SELECT COUNT(*) as cnt FROM sala")['cnt']
    reservas_activas_count = db.execute_fetchone("SELECT COUNT(*) as cnt FROM reserva WHERE estado = 'activa'")['cnt']
    sanciones_activas_count = db.execute_fetchone("SELECT COUNT(*) as cnt FROM sancion_participante WHERE fecha_fin >= CURDATE()")['cnt']
    
    return render_template('dashboard.html',
                         participantes_count=participantes_count,
                         salas_count=salas_count,
                         reservas_activas_count=reservas_activas_count,
                         sanciones_activas_count=sanciones_activas_count,
                         has_program=user_role is not None)


def get_programas():
    """Get all academic programs"""
    return db.execute_query(
        "SELECT pa.nombre_programa, pa.id_facultad, pa.tipo, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad ORDER BY f.nombre, pa.nombre_programa",
        fetch=True
    ) or []


@app.route('/add-program', methods=['GET', 'POST'])
@login_required
def add_program():
    """Add program association for current user"""
    # Check if user already has a program
    user_role = auth.get_user_role(session['user']['ci'])
    if user_role:
        flash('Ya tienes un programa académico asociado.', 'info')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        rol = request.form.get('rol', 'alumno').strip()
        
        # Debug: print form data
        print(f"DEBUG - Form data: nombre_programa={nombre_programa}, id_facultad={id_facultad}, rol={rol}, ci={session.get('user', {}).get('ci')}")
        
        # If id_facultad is empty, try to get it from the selected programa
        if not id_facultad and nombre_programa:
            programa_info = db.execute_fetchone(
                "SELECT id_facultad FROM programa_academico WHERE nombre_programa = %s LIMIT 1",
                (nombre_programa,)
            )
            if programa_info:
                id_facultad = str(programa_info['id_facultad'])
        
        if not nombre_programa or not id_facultad:
            flash('Por favor, selecciona un programa académico completo.', 'error')
            return render_template('add_program.html', programas=get_programas())
        
        try:
            id_facultad_int = int(id_facultad)
            # Check if already exists
            existing = db.execute_fetchone(
                "SELECT * FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
                (session['user']['ci'], nombre_programa, id_facultad_int)
            )
            if existing:
                flash('Ya tienes este programa académico asociado.', 'info')
                return redirect(url_for('dashboard'))
            
            result = db.execute_query(
                "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                (session['user']['ci'], nombre_programa, id_facultad_int, rol)
            )
            print(f"DEBUG - Insert result: {result}")
            if result is not None:
                flash('Programa académico agregado exitosamente. Ahora puedes hacer reservas.', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Error al agregar programa. Por favor, intenta nuevamente.', 'error')
        except Exception as e:
            flash(f'Error al agregar programa: {str(e)}', 'error')
            import traceback
            print(f"Error details: {traceback.format_exc()}")
    
    return render_template('add_program.html', programas=get_programas())


# ==================== ABM PARTICIPANTES ====================

@app.route('/participantes')
@login_required
def list_participantes():
    """List all participants"""
    participantes = db.execute_query(
        "SELECT p.*, GROUP_CONCAT(CONCAT(ppa.rol, ' - ', ppa.nombre_programa) SEPARATOR ', ') as programas FROM participante p LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante GROUP BY p.ci ORDER BY p.apellido, p.nombre",
        fetch=True
    ) or []
    return render_template('participantes/list.html', participantes=participantes)


@app.route('/participantes/create', methods=['GET', 'POST'])
@login_required
def create_participante():
    """Create new participant"""
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
            return render_template('participantes/create.html', programas=get_programas())
        
        # Check if exists
        existing = db.execute_fetchone("SELECT ci FROM participante WHERE ci = %s OR email = %s", (ci, email))
        if existing:
            flash('Ya existe un participante con este CI o email.', 'error')
            return render_template('participantes/create.html', programas=get_programas())
        
        # Insert participant
        try:
            db.execute_query(
                "INSERT INTO participante (ci, nombre, apellido, email) VALUES (%s, %s, %s, %s)",
                (ci, nombre, apellido, email)
            )
            
            # Create login if password provided
            if password:
                import bcrypt
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                db.execute_query(
                    "INSERT INTO login (correo, password) VALUES (%s, %s)",
                    (email, hashed.decode('utf-8'))
                )
            
            # Associate with program if provided
            if nombre_programa and id_facultad:
                db.execute_query(
                    "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                    (ci, nombre_programa, int(id_facultad), rol)
                )
            
            flash('Participante creado exitosamente.', 'success')
            return redirect(url_for('list_participantes'))
        except Exception as e:
            flash(f'Error al crear participante: {str(e)}', 'error')
    
    return render_template('participantes/create.html', programas=get_programas())


@app.route('/participantes/<ci>/edit', methods=['GET', 'POST'])
@login_required
def edit_participante(ci):
    """Edit participant"""
    participante = db.execute_fetchone("SELECT * FROM participante WHERE ci = %s", (ci,))
    if not participante:
        flash('Participante no encontrado.', 'error')
        return redirect(url_for('list_participantes'))
    
    # Get current programs
    current_programs = db.execute_query(
        "SELECT ppa.*, pa.tipo, f.nombre as nombre_facultad FROM participante_programa_academico ppa JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa AND ppa.id_facultad = pa.id_facultad JOIN facultad f ON pa.id_facultad = f.id_facultad WHERE ppa.ci_participante = %s",
        (ci,),
        fetch=True
    ) or []
    
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
            return render_template('participantes/edit.html', participante=participante, programas=get_programas(), current_programs=current_programs)
        
        try:
            db.execute_query(
                "UPDATE participante SET nombre = %s, apellido = %s, email = %s WHERE ci = %s",
                (nombre, apellido, email, ci)
            )
            
            # Add program if provided
            if nombre_programa and id_facultad:
                # Check if already exists
                existing = db.execute_fetchone(
                    "SELECT * FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
                    (ci, nombre_programa, int(id_facultad))
                )
                if not existing:
                    db.execute_query(
                        "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                        (ci, nombre_programa, int(id_facultad), rol)
                    )
                    flash('Participante y programa académico actualizados exitosamente.', 'success')
                else:
                    flash('Participante actualizado. El programa ya estaba asociado.', 'info')
            else:
                flash('Participante actualizado exitosamente.', 'success')
            
            return redirect(url_for('list_participantes'))
        except Exception as e:
            flash(f'Error al actualizar participante: {str(e)}', 'error')
            import traceback
            print(f"Error details: {traceback.format_exc()}")
    
    return render_template('participantes/edit.html', participante=participante, programas=get_programas(), current_programs=current_programs)


@app.route('/participantes/<ci>/remove-program', methods=['POST'])
@login_required
def remove_program(ci):
    """Remove program association from participant"""
    nombre_programa = request.form.get('nombre_programa', '').strip()
    id_facultad = request.form.get('id_facultad', '').strip()
    
    print(f"DEBUG remove_program - CI: {ci}, nombre_programa: {nombre_programa}, id_facultad: {id_facultad}")
    
    if not nombre_programa or not id_facultad:
        flash('Error: Faltan datos del programa.', 'error')
        return redirect(url_for('edit_participante', ci=ci))
    
    try:
        # Check how many programs the user has
        program_count = db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM participante_programa_academico WHERE ci_participante = %s",
            (ci,)
        )
        
        print(f"DEBUG - Program count: {program_count}")
        
        if program_count and program_count['cnt'] <= 1:
            flash('No se puede eliminar el último programa académico. Un usuario debe tener al menos un programa asociado.', 'error')
            return redirect(url_for('edit_participante', ci=ci))
        
        # Verify the program exists before deleting
        existing = db.execute_fetchone(
            "SELECT * FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
            (ci, nombre_programa, int(id_facultad))
        )
        
        print(f"DEBUG - Existing program: {existing}")
        
        if not existing:
            flash('No se encontró el programa para eliminar.', 'warning')
            return redirect(url_for('edit_participante', ci=ci))
        
        # Delete the program association
        result = db.execute_query(
            "DELETE FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
            (ci, nombre_programa, int(id_facultad))
        )
        
        print(f"DEBUG - Delete result: {result}, type: {type(result)}")
        
        # execute_query returns rowcount (int) for DELETE, or None on error
        if result is not None:
            if result > 0:
                flash('Programa académico eliminado exitosamente.', 'success')
            else:
                flash('No se encontró el programa para eliminar. Puede que ya haya sido eliminado.', 'warning')
        else:
            flash('Error: No se pudo eliminar el programa. Por favor, intenta nuevamente.', 'error')
    except Exception as e:
        flash(f'Error al eliminar programa: {str(e)}', 'error')
        import traceback
        print(f"Error details: {traceback.format_exc()}")
    
    return redirect(url_for('edit_participante', ci=ci))


@app.route('/participantes/<ci>/delete', methods=['POST'])
@login_required
def delete_participante(ci):
    """Delete participant"""
    try:
        db.execute_query("DELETE FROM participante WHERE ci = %s", (ci,))
        flash('Participante eliminado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar participante: {str(e)}', 'error')
    return redirect(url_for('list_participantes'))


# ==================== ABM PROGRAMAS ACADÉMICOS ====================

@app.route('/programas')
@login_required
def list_programas():
    """List all academic programs"""
    programas = db.execute_query(
        "SELECT pa.*, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad ORDER BY f.nombre, pa.nombre_programa",
        fetch=True
    ) or []
    return render_template('programas/list.html', programas=programas)


@app.route('/programas/create', methods=['GET', 'POST'])
@login_required
def create_programa():
    """Create new academic program"""
    if request.method == 'POST':
        nombre_programa = request.form.get('nombre_programa', '').strip()
        id_facultad = request.form.get('id_facultad', '').strip()
        tipo = request.form.get('tipo', 'grado').strip()
        
        if not all([nombre_programa, id_facultad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('programas/create.html', facultades=get_facultades())
        
        try:
            # Check if already exists
            existing = db.execute_fetchone(
                "SELECT * FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                (nombre_programa, int(id_facultad))
            )
            if existing:
                flash('Ya existe un programa con este nombre en esta facultad.', 'error')
                return render_template('programas/create.html', facultades=get_facultades())
            
            db.execute_query(
                "INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES (%s, %s, %s)",
                (nombre_programa, int(id_facultad), tipo)
            )
            flash('Programa académico creado exitosamente.', 'success')
            return redirect(url_for('list_programas'))
        except Exception as e:
            flash(f'Error al crear programa: {str(e)}', 'error')
            import traceback
            print(f"Error details: {traceback.format_exc()}")
    
    return render_template('programas/create.html', facultades=get_facultades())


@app.route('/programas/<nombre_programa>/<int:id_facultad>/edit', methods=['GET', 'POST'])
@login_required
def edit_programa(nombre_programa, id_facultad):
    """Edit academic program"""
    programa = db.execute_fetchone(
        "SELECT pa.*, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad WHERE pa.nombre_programa = %s AND pa.id_facultad = %s",
        (nombre_programa, id_facultad)
    )
    if not programa:
        flash('Programa no encontrado.', 'error')
        return redirect(url_for('list_programas'))
    
    if request.method == 'POST':
        nuevo_nombre = request.form.get('nombre_programa', '').strip()
        nuevo_id_facultad = request.form.get('id_facultad', '').strip()
        tipo = request.form.get('tipo', 'grado').strip()
        
        if not all([nuevo_nombre, nuevo_id_facultad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('programas/edit.html', programa=programa, facultades=get_facultades())
        
        try:
            nuevo_id_facultad = int(nuevo_id_facultad)
            # If name or faculty changed, check if new combination exists
            if nuevo_nombre != nombre_programa or nuevo_id_facultad != id_facultad:
                existing = db.execute_fetchone(
                    "SELECT * FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                    (nuevo_nombre, nuevo_id_facultad)
                )
                if existing:
                    flash('Ya existe un programa con este nombre en esta facultad.', 'error')
                    return render_template('programas/edit.html', programa=programa, facultades=get_facultades())
            
            # Update the program
            db.execute_query(
                "UPDATE programa_academico SET nombre_programa = %s, id_facultad = %s, tipo = %s WHERE nombre_programa = %s AND id_facultad = %s",
                (nuevo_nombre, nuevo_id_facultad, tipo, nombre_programa, id_facultad)
            )
            flash('Programa académico actualizado exitosamente.', 'success')
            return redirect(url_for('list_programas'))
        except Exception as e:
            flash(f'Error al actualizar programa: {str(e)}', 'error')
            import traceback
            print(f"Error details: {traceback.format_exc()}")
    
    return render_template('programas/edit.html', programa=programa, facultades=get_facultades())


@app.route('/programas/<nombre_programa>/<int:id_facultad>/delete', methods=['POST'])
@login_required
def delete_programa(nombre_programa, id_facultad):
    """Delete academic program"""
    try:
        # Check if there are participants associated
        participantes = db.execute_fetchone(
            "SELECT COUNT(*) as cnt FROM participante_programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
            (nombre_programa, id_facultad)
        )
        
        if participantes and participantes['cnt'] > 0:
            flash(f'No se puede eliminar el programa porque tiene {participantes["cnt"]} participante(s) asociado(s).', 'error')
            return redirect(url_for('list_programas'))
        
        db.execute_query(
            "DELETE FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
            (nombre_programa, id_facultad)
        )
        flash('Programa académico eliminado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar programa: {str(e)}', 'error')
        import traceback
        print(f"Error details: {traceback.format_exc()}")
    return redirect(url_for('list_programas'))


def get_facultades():
    """Get all faculties"""
    return db.execute_query("SELECT * FROM facultad ORDER BY nombre", fetch=True) or []


# ==================== ABM SALAS ====================

@app.route('/salas')
@login_required
def list_salas():
    """List all rooms"""
    salas = db.execute_query(
        "SELECT s.*, e.direccion, e.departamento FROM sala s JOIN edificio e ON s.edificio = e.nombre_edificio ORDER BY s.edificio, s.nombre_sala",
        fetch=True
    ) or []
    return render_template('salas/list.html', salas=salas)


@app.route('/salas/create', methods=['GET', 'POST'])
@login_required
def create_sala():
    """Create new room"""
    if request.method == 'POST':
        nombre_sala = request.form.get('nombre_sala', '').strip()
        edificio = request.form.get('edificio', '').strip()
        capacidad = request.form.get('capacidad', '').strip()
        tipo_sala = request.form.get('tipo_sala', 'libre').strip()
        
        if not all([nombre_sala, edificio, capacidad]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('salas/create.html', edificios=get_edificios())
        
        try:
            capacidad = int(capacidad)
            db.execute_query(
                "INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES (%s, %s, %s, %s)",
                (nombre_sala, edificio, capacidad, tipo_sala)
            )
            flash('Sala creada exitosamente.', 'success')
            return redirect(url_for('list_salas'))
        except Exception as e:
            flash(f'Error al crear sala: {str(e)}', 'error')
    
    return render_template('salas/create.html', edificios=get_edificios())


@app.route('/salas/<edificio>/<nombre_sala>/edit', methods=['GET', 'POST'])
@login_required
def edit_sala(edificio, nombre_sala):
    """Edit room"""
    sala = db.execute_fetchone(
        "SELECT * FROM sala WHERE nombre_sala = %s AND edificio = %s",
        (nombre_sala, edificio)
    )
    if not sala:
        flash('Sala no encontrada.', 'error')
        return redirect(url_for('list_salas'))
    
    if request.method == 'POST':
        capacidad = request.form.get('capacidad', '').strip()
        tipo_sala = request.form.get('tipo_sala', 'libre').strip()
        
        try:
            capacidad = int(capacidad)
            db.execute_query(
                "UPDATE sala SET capacidad = %s, tipo_sala = %s WHERE nombre_sala = %s AND edificio = %s",
                (capacidad, tipo_sala, nombre_sala, edificio)
            )
            flash('Sala actualizada exitosamente.', 'success')
            return redirect(url_for('list_salas'))
        except Exception as e:
            flash(f'Error al actualizar sala: {str(e)}', 'error')
    
    return render_template('salas/edit.html', sala=sala, edificios=get_edificios())


@app.route('/salas/<edificio>/<nombre_sala>/delete', methods=['POST'])
@login_required
def delete_sala(edificio, nombre_sala):
    """Delete room"""
    try:
        db.execute_query("DELETE FROM sala WHERE nombre_sala = %s AND edificio = %s", (nombre_sala, edificio))
        flash('Sala eliminada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar sala: {str(e)}', 'error')
    return redirect(url_for('list_salas'))


def get_edificios():
    """Get all buildings"""
    return db.execute_query("SELECT * FROM edificio ORDER BY nombre_edificio", fetch=True) or []


# ==================== ABM RESERVAS ====================

@app.route('/reservas')
@login_required
def list_reservas():
    """List all reservations"""
    reservas = db.execute_query(
        """SELECT r.*, s.capacidad, s.tipo_sala, t.hora_inicio, t.hora_fin,
           COUNT(rp.ci_participante) as num_participantes
           FROM reserva r
           JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
           JOIN turno t ON r.id_turno = t.id_turno
           LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
           GROUP BY r.id_reserva
           ORDER BY r.fecha DESC, t.hora_inicio DESC""",
        fetch=True
    ) or []
    return render_template('reservas/list.html', reservas=reservas)


@app.route('/reservas/create', methods=['GET', 'POST'])
@login_required
def create_reserva():
    """Create new reservation"""
    # Check if user has a role/program association
    user_role = auth.get_user_role(session['user']['ci'])
    if not user_role:
        flash('No tienes un programa académico asociado. Por favor, agrega tu programa académico antes de hacer reservas.', 'error')
        return redirect(url_for('add_program'))
    
    if request.method == 'POST':
        nombre_sala = request.form.get('nombre_sala', '').strip()
        edificio = request.form.get('edificio', '').strip()
        fecha_str = request.form.get('fecha', '').strip()
        id_turno = request.form.get('id_turno', '').strip()
        participantes_str = request.form.get('participantes', '').strip()
        
        if not all([nombre_sala, edificio, fecha_str, id_turno]):
            flash('Por favor, completa todos los campos obligatorios.', 'error')
            return render_template('reservas/create.html', salas=get_salas(), turnos=get_turnos())
        
        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            id_turno = int(id_turno)
            participantes = [ci.strip() for ci in participantes_str.split(',') if ci.strip()]
            
            # Ensure current user is in participants
            if session['user']['ci'] not in participantes:
                participantes.insert(0, session['user']['ci'])
            
            id_reserva = reservation.create_reservation(
                session['user']['ci'],
                nombre_sala,
                edificio,
                fecha,
                id_turno,
                participantes
            )
            
            if id_reserva:
                flash('Reserva creada exitosamente.', 'success')
                return redirect(url_for('list_reservas'))
            else:
                flash('Error al crear reserva. Verifica las restricciones.', 'error')
        except ValueError as e:
            flash(f'Error en los datos ingresados: {str(e)}', 'error')
    
    return render_template('reservas/create.html', salas=get_salas(), turnos=get_turnos())


@app.route('/reservas/<int:id_reserva>/edit', methods=['GET', 'POST'])
@login_required
def edit_reserva(id_reserva):
    """Edit reservation (mainly to cancel)"""
    reserva = db.execute_fetchone("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    if not reserva:
        flash('Reserva no encontrada.', 'error')
        return redirect(url_for('list_reservas'))
    
    if request.method == 'POST':
        estado = request.form.get('estado', '').strip()
        try:
            db.execute_query(
                "UPDATE reserva SET estado = %s WHERE id_reserva = %s",
                (estado, id_reserva)
            )
            flash('Reserva actualizada exitosamente.', 'success')
            return redirect(url_for('list_reservas'))
        except Exception as e:
            flash(f'Error al actualizar reserva: {str(e)}', 'error')
    
    participantes = db.execute_query(
        "SELECT rp.*, p.nombre, p.apellido FROM reserva_participante rp JOIN participante p ON rp.ci_participante = p.ci WHERE rp.id_reserva = %s",
        (id_reserva,),
        fetch=True
    ) or []
    
    return render_template('reservas/edit.html', reserva=reserva, participantes=participantes)


@app.route('/reservas/<int:id_reserva>/attendance', methods=['GET', 'POST'])
@login_required
def update_attendance(id_reserva):
    """Update attendance for a reservation"""
    reserva = db.execute_fetchone("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    if not reserva:
        flash('Reserva no encontrada.', 'error')
        return redirect(url_for('list_reservas'))
    
    participantes = db.execute_query(
        "SELECT rp.*, p.nombre, p.apellido FROM reserva_participante rp JOIN participante p ON rp.ci_participante = p.ci WHERE rp.id_reserva = %s",
        (id_reserva,),
        fetch=True
    ) or []
    
    if request.method == 'POST':
        asistencias = []
        participantes_ci = []
        for p in participantes:
            asistencia = request.form.get(f"asistencia_{p['ci_participante']}", 'false')
            asistencias.append(asistencia == 'true')
            participantes_ci.append(p['ci_participante'])
        
        if reservation.update_attendance(id_reserva, participantes_ci, asistencias):
            flash('Asistencia actualizada exitosamente.', 'success')
            return redirect(url_for('list_reservas'))
        else:
            flash('Error al actualizar asistencia.', 'error')
    
    return render_template('reservas/attendance.html', reserva=reserva, participantes=participantes)


@app.route('/reservas/<int:id_reserva>/delete', methods=['POST'])
@login_required
def delete_reserva(id_reserva):
    """Delete reservation"""
    try:
        db.execute_query("DELETE FROM reserva WHERE id_reserva = %s", (id_reserva,))
        flash('Reserva eliminada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar reserva: {str(e)}', 'error')
    return redirect(url_for('list_reservas'))


def get_salas():
    """Get all rooms"""
    return db.execute_query("SELECT * FROM sala ORDER BY edificio, nombre_sala", fetch=True) or []


def get_turnos():
    """Get all time slots"""
    return db.execute_query("SELECT * FROM turno ORDER BY hora_inicio", fetch=True) or []


# ==================== ABM SANCIONES ====================

@app.route('/sanciones')
@login_required
def list_sanciones():
    """List all sanctions"""
    sanciones = db.execute_query(
        """SELECT sp.*, p.nombre, p.apellido, p.email, p.ci
           FROM sancion_participante sp
           JOIN participante p ON sp.ci_participante = p.ci
           ORDER BY sp.fecha_inicio DESC""",
        fetch=True
    ) or []
    today = date.today()
    return render_template('sanciones/list.html', sanciones=sanciones, today=today)


@app.route('/sanciones/create', methods=['GET', 'POST'])
@login_required
def create_sancion():
    """Create new sanction"""
    if request.method == 'POST':
        ci_participante = request.form.get('ci_participante', '').strip()
        fecha_inicio_str = request.form.get('fecha_inicio', '').strip()
        fecha_fin_str = request.form.get('fecha_fin', '').strip()
        
        if not all([ci_participante, fecha_inicio_str, fecha_fin_str]):
            flash('Por favor, completa todos los campos.', 'error')
            return render_template('sanciones/create.html', participantes=get_participantes_list())
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            
            if fecha_fin <= fecha_inicio:
                flash('La fecha de fin debe ser posterior a la fecha de inicio.', 'error')
                return render_template('sanciones/create.html', participantes=get_participantes_list())
            
            db.execute_query(
                "INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin) VALUES (%s, %s, %s)",
                (ci_participante, fecha_inicio, fecha_fin)
            )
            flash('Sanción creada exitosamente.', 'success')
            return redirect(url_for('list_sanciones'))
        except Exception as e:
            flash(f'Error al crear sanción: {str(e)}', 'error')
    
    return render_template('sanciones/create.html', participantes=get_participantes_list())


@app.route('/sanciones/<int:id_sancion>/edit', methods=['GET', 'POST'])
@login_required
def edit_sancion(id_sancion):
    """Edit sanction"""
    sancion = db.execute_fetchone("SELECT * FROM sancion_participante WHERE id_sancion = %s", (id_sancion,))
    if not sancion:
        flash('Sanción no encontrada.', 'error')
        return redirect(url_for('list_sanciones'))
    
    if request.method == 'POST':
        fecha_inicio_str = request.form.get('fecha_inicio', '').strip()
        fecha_fin_str = request.form.get('fecha_fin', '').strip()
        
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
            
            if fecha_fin <= fecha_inicio:
                flash('La fecha de fin debe ser posterior a la fecha de inicio.', 'error')
                return render_template('sanciones/edit.html', sancion=sancion)
            
            db.execute_query(
                "UPDATE sancion_participante SET fecha_inicio = %s, fecha_fin = %s WHERE id_sancion = %s",
                (fecha_inicio, fecha_fin, id_sancion)
            )
            flash('Sanción actualizada exitosamente.', 'success')
            return redirect(url_for('list_sanciones'))
        except Exception as e:
            flash(f'Error al actualizar sanción: {str(e)}', 'error')
    
    return render_template('sanciones/edit.html', sancion=sancion)


@app.route('/sanciones/<int:id_sancion>/delete', methods=['POST'])
@login_required
def delete_sancion(id_sancion):
    """Delete sanction"""
    try:
        db.execute_query("DELETE FROM sancion_participante WHERE id_sancion = %s", (id_sancion,))
        flash('Sanción eliminada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al eliminar sanción: {str(e)}', 'error')
    return redirect(url_for('list_sanciones'))


def get_participantes_list():
    """Get all participants for dropdown"""
    return db.execute_query("SELECT ci, nombre, apellido, email FROM participante ORDER BY apellido, nombre", fetch=True) or []


# ==================== REPORTES ====================

@app.route('/reportes')
@login_required
def reportes():
    """Reports dashboard"""
    return render_template('reportes/index.html')


@app.route('/reportes/salas-mas-reservadas')
@login_required
def reporte_salas_mas_reservadas():
    """Most reserved rooms"""
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


@app.route('/reportes/turnos-mas-demandados')
@login_required
def reporte_turnos_mas_demandados():
    """Most demanded time slots"""
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


@app.route('/reportes/promedio-participantes-sala')
@login_required
def reporte_promedio_participantes_sala():
    """Average participants per room"""
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


@app.route('/reportes/reservas-por-carrera-facultad')
@login_required
def reporte_reservas_por_carrera_facultad():
    """Reservations per program and faculty"""
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


@app.route('/reportes/ocupacion-por-edificio')
@login_required
def reporte_ocupacion_por_edificio():
    """Room occupancy percentage per building"""
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


@app.route('/reportes/reservas-asistencias-profesores-alumnos')
@login_required
def reporte_reservas_asistencias_profesores_alumnos():
    """Reservations and attendances for teachers and students"""
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


@app.route('/reportes/sanciones-profesores-alumnos')
@login_required
def reporte_sanciones_profesores_alumnos():
    """Sanctions for teachers and students"""
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


@app.route('/reportes/porcentaje-reservas-utilizadas')
@login_required
def reporte_porcentaje_reservas_utilizadas():
    """Percentage of used vs canceled/no-show reservations"""
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


# Additional suggested reports
@app.route('/reportes/reservas-por-mes')
@login_required
def reporte_reservas_por_mes():
    """Reservations per month (suggested report 1)"""
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
    results = db.execute_query(query, fetch=True) or []
    return render_template('reportes/reservas_por_mes.html', results=results)


@app.route('/reportes/participantes-mas-activos')
@login_required
def reporte_participantes_mas_activos():
    """Most active participants (suggested report 2)"""
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


@app.route('/reportes/eficiencia-uso-salas')
@login_required
def reporte_eficiencia_uso_salas():
    """Room usage efficiency (suggested report 3)"""
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

