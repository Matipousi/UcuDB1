"""
UCU Study Room Reservation System
Console application for managing study room reservations
"""

import mysql.connector
from mysql.connector import Error
import bcrypt
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple
import getpass


class DatabaseManager:
    """Handles database connection and operations"""
    
    def __init__(self, host='localhost', user='root', password='', database='UCU_SalasDeEstudio'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        self.connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                print("✓ Connected to MySQL database")
                return True
        except Error as e:
            print(f"✗ Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("✓ Database connection closed")
    
    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Execute a query with parameterized inputs (prevents SQL injection)"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if fetch:
                result = cursor.fetchall()
                self.connection.commit()
                return result
            else:
                self.connection.commit()
                return cursor.rowcount
        except Error as e:
            self.connection.rollback()
            print(f"✗ Database error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()
    
    def execute_fetchone(self, query: str, params: tuple = None):
        """Execute query and fetch one result"""
        cursor = None
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchone()
            self.connection.commit()
            return result
        except Error as e:
            self.connection.rollback()
            print(f"✗ Database error: {e}")
            return None
        finally:
            if cursor:
                cursor.close()


class AuthManager:
    """Handles user authentication"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def register(self, ci: str, nombre: str, apellido: str, email: str, password: str) -> bool:
        """Register a new user"""
        try:
            # Check if user already exists
            check_query = "SELECT ci FROM participante WHERE ci = %s OR email = %s"
            existing = self.db.execute_fetchone(check_query, (ci, email))
            if existing:
                print("✗ User with this CI or email already exists")
                return False
            
            # Insert participant
            insert_participante = """
                INSERT INTO participante (ci, nombre, apellido, email)
                VALUES (%s, %s, %s, %s)
            """
            self.db.execute_query(insert_participante, (ci, nombre, apellido, email))
            
            # Hash password and insert login
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            insert_login = """
                INSERT INTO login (correo, password)
                VALUES (%s, %s)
            """
            self.db.execute_query(insert_login, (email, hashed.decode('utf-8')))
            
            print("✓ User registered successfully")
            return True
        except Exception as e:
            print(f"✗ Registration error: {e}")
            return False
    
    def login(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info"""
        try:
            query = """
                SELECT l.correo, l.password, p.ci, p.nombre, p.apellido
                FROM login l
                JOIN participante p ON l.correo = p.email
                WHERE l.correo = %s
            """
            user = self.db.execute_fetchone(query, (email,))
            
            if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                print(f"✓ Welcome, {user['nombre']} {user['apellido']}!")
                return {
                    'ci': user['ci'],
                    'email': user['correo'],
                    'nombre': user['nombre'],
                    'apellido': user['apellido']
                }
            else:
                print("✗ Invalid email or password")
                return None
        except Exception as e:
            print(f"✗ Login error: {e}")
            return None
    
    def get_user_role(self, ci: str) -> Optional[Dict]:
        """Get user's role and program info"""
        query = """
            SELECT rol, nombre_programa, id_facultad, tipo
            FROM participante_programa_academico ppa
            JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa 
                AND ppa.id_facultad = pa.id_facultad
            WHERE ci_participante = %s
            LIMIT 1
        """
        return self.db.execute_fetchone(query, (ci,))


class ReservationManager:
    """Handles reservation operations"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def validate_reservation(self, ci: str, nombre_sala: str, edificio: str, 
                           fecha: date, id_turno: int, participantes: List[str]) -> Tuple[bool, str]:
        """Validate reservation constraints"""
        # 1. Check hourly blocks only (already enforced by turno table)
        
        # Get room info and user role first to check if exceptions apply
        query_room_type = """
            SELECT tipo_sala, capacidad FROM sala
            WHERE nombre_sala = %s AND edificio = %s
        """
        sala_info = self.db.execute_fetchone(query_room_type, (nombre_sala, edificio))
        if not sala_info:
            return False, "Room not found"
        
        # Get user role
        auth = AuthManager(self.db)
        user_role = auth.get_user_role(ci)
        if not user_role:
            return False, "User role not found"
        
        tipo_sala = sala_info['tipo_sala']
        capacidad = sala_info['capacidad']
        rol = user_role['rol']
        tipo_programa = user_role['tipo']
        
        # Check room-type access
        if tipo_sala == 'posgrado' and tipo_programa != 'posgrado':
            return False, "This room is only for postgraduate students"
        if tipo_sala == 'docente' and rol != 'docente':
            return False, "This room is only for teachers"
        
        # Check if user is exempt from time limitations (teachers/postgrad in exclusive rooms)
        is_exempt = False
        if tipo_sala == 'docente' and rol == 'docente':
            is_exempt = True
        elif tipo_sala == 'posgrado' and tipo_programa == 'posgrado':
            is_exempt = True
        
        # 2. Check ≤2h/day/building (unless exempt)
        if not is_exempt:
            query_hours = """
                SELECT SUM(1) as total_hours
                FROM reserva r
                JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
                WHERE rp.ci_participante = %s
                AND r.edificio = %s
                AND r.fecha = %s
                AND r.estado = 'activa'
            """
            result = self.db.execute_fetchone(query_hours, (ci, edificio, fecha))
            if result and result['total_hours'] and result['total_hours'] >= 2:
                return False, "Maximum 2 hours per day per building exceeded"
        
        # 3. Check ≤3 active/week (unless exempt)
        if not is_exempt:
            week_start = fecha - timedelta(days=fecha.weekday())
            week_end = week_start + timedelta(days=6)
            query_week = """
                SELECT COUNT(DISTINCT r.id_reserva) as total_reservas
                FROM reserva r
                JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
                WHERE rp.ci_participante = %s
                AND r.fecha BETWEEN %s AND %s
                AND r.estado = 'activa'
            """
            result = self.db.execute_fetchone(query_week, (ci, week_start, week_end))
            if result and result['total_reservas'] and result['total_reservas'] >= 3:
                return False, "Maximum 3 active reservations per week exceeded"
        
        # 4. Check capacity
        if len(participantes) > capacidad:
            return False, f"Number of participants ({len(participantes)}) exceeds room capacity ({capacidad})"
        
        # 6. Check no active sanctions
        query_sancion = """
            SELECT id_sancion FROM sancion_participante
            WHERE ci_participante = %s
            AND fecha_fin >= CURDATE()
        """
        sancion = self.db.execute_fetchone(query_sancion, (ci,))
        if sancion:
            return False, "User has an active sanction"
        
        # 7. Check room availability (not already reserved)
        query_availability = """
            SELECT id_reserva FROM reserva
            WHERE nombre_sala = %s AND edificio = %s
            AND fecha = %s AND id_turno = %s
            AND estado = 'activa'
        """
        existing = self.db.execute_fetchone(query_availability, (nombre_sala, edificio, fecha, id_turno))
        if existing:
            return False, "Room already reserved for this time slot"
        
        return True, "Valid"
    
    def create_reservation(self, ci: str, nombre_sala: str, edificio: str,
                          fecha: date, id_turno: int, participantes: List[str]) -> Optional[int]:
        """Create a new reservation"""
        # Validate first
        valid, message = self.validate_reservation(ci, nombre_sala, edificio, fecha, id_turno, participantes)
        if not valid:
            print(f"✗ Validation failed: {message}")
            return None
        
        try:
            # Insert reservation
            insert_reserva = """
                INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado)
                VALUES (%s, %s, %s, %s, 'activa')
            """
            self.db.execute_query(insert_reserva, (nombre_sala, edificio, fecha, id_turno))
            
            # Get the reservation ID
            query_id = """
                SELECT id_reserva FROM reserva
                WHERE nombre_sala = %s AND edificio = %s
                AND fecha = %s AND id_turno = %s
            """
            reserva = self.db.execute_fetchone(query_id, (nombre_sala, edificio, fecha, id_turno))
            if not reserva:
                return None
            
            id_reserva = reserva['id_reserva']
            fecha_solicitud = datetime.now()
            
            # Insert all participants
            insert_participante = """
                INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia)
                VALUES (%s, %s, %s, FALSE)
            """
            for participante_ci in participantes:
                self.db.execute_query(insert_participante, (participante_ci, id_reserva, fecha_solicitud))
            
            print(f"✓ Reservation created successfully (ID: {id_reserva})")
            return id_reserva
        except Exception as e:
            print(f"✗ Error creating reservation: {e}")
            return None
    
    def update_attendance(self, id_reserva: int, participantes_ci: List[str], asistencias: List[bool]):
        """Update attendance for a reservation"""
        if len(participantes_ci) != len(asistencias):
            print("✗ Number of participants and attendance records must match")
            return False
        
        try:
            # Update attendance records
            update_query = """
                UPDATE reserva_participante
                SET asistencia = %s
                WHERE id_reserva = %s AND ci_participante = %s
            """
            for ci, asistencia in zip(participantes_ci, asistencias):
                self.db.execute_query(update_query, (asistencia, id_reserva, ci))
            
            # Check if all participants have FALSE attendance
            check_query = """
                SELECT COUNT(*) as total, SUM(asistencia) as asistieron
                FROM reserva_participante
                WHERE id_reserva = %s
            """
            result = self.db.execute_fetchone(check_query, (id_reserva,))
            
            if result and result['total'] > 0 and result['asistieron'] == 0:
                # All participants have FALSE attendance - create sanction
                # Get reservation date
                fecha_query = "SELECT fecha FROM reserva WHERE id_reserva = %s"
                reserva = self.db.execute_fetchone(fecha_query, (id_reserva,))
                
                if reserva:
                    fecha_reserva = reserva['fecha']
                    fecha_inicio = fecha_reserva
                    fecha_fin = fecha_inicio + timedelta(days=60)  # 2 months
                    
                    # Get all participants
                    participantes_query = """
                        SELECT ci_participante FROM reserva_participante
                        WHERE id_reserva = %s
                    """
                    participantes = self.db.execute_query(participantes_query, (id_reserva,), fetch=True)
                    
                    # Create sanctions for all participants
                    insert_sancion = """
                        INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin)
                        VALUES (%s, %s, %s)
                    """
                    for p in participantes:
                        self.db.execute_query(insert_sancion, (p['ci_participante'], fecha_inicio, fecha_fin))
                    
                    # Update reservation state
                    update_estado = "UPDATE reserva SET estado = 'sin asistencia' WHERE id_reserva = %s"
                    self.db.execute_query(update_estado, (id_reserva,))
                    
                    print("✓ Attendance updated. Sanctions created for all participants (no attendance).")
            else:
                print("✓ Attendance updated successfully")
            
            return True
        except Exception as e:
            print(f"✗ Error updating attendance: {e}")
            return False


class ReportManager:
    """Handles reporting queries"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def get_active_reservations_by_room_date(self, nombre_sala: str = None, 
                                            edificio: str = None, fecha: date = None):
        """Get active reservations filtered by room and/or date"""
        query = """
            SELECT r.id_reserva, r.nombre_sala, r.edificio, r.fecha, 
                   t.hora_inicio, t.hora_fin, r.estado,
                   COUNT(rp.ci_participante) as num_participantes
            FROM reserva r
            JOIN turno t ON r.id_turno = t.id_turno
            LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
            WHERE r.estado = 'activa'
        """
        params = []
        
        if nombre_sala:
            query += " AND r.nombre_sala = %s"
            params.append(nombre_sala)
        if edificio:
            query += " AND r.edificio = %s"
            params.append(edificio)
        if fecha:
            query += " AND r.fecha = %s"
            params.append(fecha)
        
        query += " GROUP BY r.id_reserva ORDER BY r.fecha, t.hora_inicio"
        
        return self.db.execute_query(query, tuple(params), fetch=True)
    
    def get_usage_stats(self):
        """Get usage statistics grouped by building and room type"""
        query = """
            SELECT e.nombre_edificio, s.tipo_sala,
                   COUNT(DISTINCT r.id_reserva) as total_reservas,
                   COUNT(DISTINCT rp.ci_participante) as total_participantes,
                   SUM(CASE WHEN r.estado = 'activa' THEN 1 ELSE 0 END) as reservas_activas
            FROM edificio e
            JOIN sala s ON e.nombre_edificio = s.edificio
            LEFT JOIN reserva r ON s.nombre_sala = r.nombre_sala AND s.edificio = r.edificio
            LEFT JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
            GROUP BY e.nombre_edificio, s.tipo_sala
            ORDER BY e.nombre_edificio, s.tipo_sala
        """
        return self.db.execute_query(query, fetch=True)
    
    def get_sanctioned_users(self):
        """Get list of users with active sanctions"""
        query = """
            SELECT sp.id_sancion, p.ci, p.nombre, p.apellido, p.email,
                   sp.fecha_inicio, sp.fecha_fin,
                   DATEDIFF(sp.fecha_fin, CURDATE()) as dias_restantes
            FROM sancion_participante sp
            JOIN participante p ON sp.ci_participante = p.ci
            WHERE sp.fecha_fin >= CURDATE()
            ORDER BY sp.fecha_fin
        """
        return self.db.execute_query(query, fetch=True)


class DataInitializer:
    """Initializes database with sample data if tables are empty"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def check_and_populate(self):
        """Check if tables are empty and populate with sample data"""
        # Check turno
        turno_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM turno")
        if not turno_count or turno_count['cnt'] == 0:
            print("Populating turno table...")
            for hour in range(8, 23):  # 8 AM to 11 PM
                hora_inicio = f"{hour:02d}:00:00"
                hora_fin = f"{hour+1:02d}:00:00"
                self.db.execute_query(
                    "INSERT INTO turno (hora_inicio, hora_fin) VALUES (%s, %s)",
                    (hora_inicio, hora_fin)
                )
            print("✓ Turno table populated")
        
        # Check facultad
        facultad_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM facultad")
        if not facultad_count or facultad_count['cnt'] == 0:
            print("Populating facultad table...")
            facultades = [
                ("Ingeniería",),
                ("Ciencias Empresariales",),
                ("Humanidades",),
            ]
            for fac in facultades:
                self.db.execute_query("INSERT INTO facultad (nombre) VALUES (%s)", fac)
            print("✓ Facultad table populated")
        
        # Check edificio
        edificio_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM edificio")
        if not edificio_count or edificio_count['cnt'] == 0:
            print("Populating edificio table...")
            edificios = [
                ("Edificio Central", "Av. 8 de Octubre 2738", "Montevideo"),
                ("Edificio Norte", "Av. Italia 6201", "Montevideo"),
            ]
            for ed in edificios:
                self.db.execute_query(
                    "INSERT INTO edificio (nombre_edificio, direccion, departamento) VALUES (%s, %s, %s)",
                    ed
                )
            print("✓ Edificio table populated")
        
        # Check sala
        sala_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM sala")
        if not sala_count or sala_count['cnt'] == 0:
            print("Populating sala table...")
            salas = [
                ("Sala A", "Edificio Central", 10, "libre"),
                ("Sala B", "Edificio Central", 15, "libre"),
                ("Sala C", "Edificio Central", 8, "posgrado"),
                ("Sala D", "Edificio Norte", 12, "libre"),
                ("Sala E", "Edificio Norte", 6, "docente"),
            ]
            for sala in salas:
                self.db.execute_query(
                    "INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES (%s, %s, %s, %s)",
                    sala
                )
            print("✓ Sala table populated")
        
        # Check programa_academico
        programa_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM programa_academico")
        if not programa_count or programa_count['cnt'] == 0:
            print("Populating programa_academico table...")
            # Get facultad IDs
            fac_ing = self.db.execute_fetchone("SELECT id_facultad FROM facultad WHERE nombre = 'Ingeniería'")
            fac_emp = self.db.execute_fetchone("SELECT id_facultad FROM facultad WHERE nombre = 'Ciencias Empresariales'")
            
            programas = []
            if fac_ing:
                programas.extend([
                    ("Ingeniería en Sistemas", fac_ing['id_facultad'], "grado"),
                    ("Maestría en Informática", fac_ing['id_facultad'], "posgrado"),
                ])
            if fac_emp:
                programas.extend([
                    ("Administración", fac_emp['id_facultad'], "grado"),
                ])
            
            for prog in programas:
                self.db.execute_query(
                    "INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES (%s, %s, %s)",
                    prog
                )
            print("✓ Programa_academico table populated")


class ConsoleApp:
    """Main console application"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.current_user = None
        self.auth = None
        self.reservation = None
        self.report = None
    
    def setup(self):
        """Initialize database connection and setup"""
        print("=== UCU Study Room Reservation System ===\n")
        
        # Get database credentials
        host = input("Database host [localhost]: ").strip() or "localhost"
        user = input("Database user [root]: ").strip() or "root"
        password = getpass.getpass("Database password: ")
        database = "UCU_SalasDeEstudio"
        
        self.db.config.update({
            'host': host,
            'user': user,
            'password': password,
            'database': database
        })
        
        if not self.db.connect():
            return False
        
        # Initialize managers
        self.auth = AuthManager(self.db)
        self.reservation = ReservationManager(self.db)
        self.report = ReportManager(self.db)
        
        # Initialize data
        initializer = DataInitializer(self.db)
        initializer.check_and_populate()
        
        return True
    
    def show_main_menu(self):
        """Display main menu"""
        print("\n=== Main Menu ===")
        print("1. Register")
        print("2. Login")
        print("3. Create Reservation")
        print("4. Update Attendance")
        print("5. View Active Reservations")
        print("6. View Usage Statistics")
        print("7. View Sanctioned Users")
        print("8. Exit")
    
    def handle_register(self):
        """Handle user registration"""
        print("\n=== Registration ===")
        ci = input("CI: ").strip()
        nombre = input("First name: ").strip()
        apellido = input("Last name: ").strip()
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        
        if self.auth.register(ci, nombre, apellido, email, password):
            # Ask for program association
            print("\nAssociate with academic program:")
            programas = self.db.execute_query(
                "SELECT nombre_programa, id_facultad, tipo FROM programa_academico",
                fetch=True
            )
            if programas:
                for i, prog in enumerate(programas, 1):
                    print(f"{i}. {prog['nombre_programa']} ({prog['tipo']})")
                choice = input("Select program number: ").strip()
                try:
                    idx = int(choice) - 1
                    if 0 <= idx < len(programas):
                        prog = programas[idx]
                        rol = input("Role (alumno/docente) [alumno]: ").strip() or "alumno"
                        self.db.execute_query(
                            "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                            (ci, prog['nombre_programa'], prog['id_facultad'], rol)
                        )
                        print("✓ Program association added")
                except ValueError:
                    print("✗ Invalid selection")
    
    def handle_login(self):
        """Handle user login"""
        print("\n=== Login ===")
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        self.current_user = self.auth.login(email, password)
        return self.current_user is not None
    
    def handle_create_reservation(self):
        """Handle reservation creation"""
        if not self.current_user:
            print("✗ Please login first")
            return
        
        print("\n=== Create Reservation ===")
        
        # Show available rooms
        salas = self.db.execute_query(
            "SELECT nombre_sala, edificio, capacidad, tipo_sala FROM sala ORDER BY edificio, nombre_sala",
            fetch=True
        )
        if not salas:
            print("✗ No rooms available")
            return
        
        print("\nAvailable rooms:")
        for i, sala in enumerate(salas, 1):
            print(f"{i}. {sala['nombre_sala']} ({sala['edificio']}) - Capacity: {sala['capacidad']}, Type: {sala['tipo_sala']}")
        
        try:
            sala_idx = int(input("\nSelect room number: ").strip()) - 1
            if not (0 <= sala_idx < len(salas)):
                print("✗ Invalid selection")
                return
            sala = salas[sala_idx]
            
            # Get date
            fecha_str = input("Date (YYYY-MM-DD): ").strip()
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            
            # Show available time slots
            turnos = self.db.execute_query(
                "SELECT id_turno, hora_inicio, hora_fin FROM turno ORDER BY hora_inicio",
                fetch=True
            )
            print("\nAvailable time slots:")
            for i, turno in enumerate(turnos, 1):
                print(f"{i}. {turno['hora_inicio']} - {turno['hora_fin']}")
            
            turno_idx = int(input("\nSelect time slot number: ").strip()) - 1
            if not (0 <= turno_idx < len(turnos)):
                print("✗ Invalid selection")
                return
            turno = turnos[turno_idx]
            
            # Get participants
            participantes_str = input(f"Participant CIs (comma-separated, starting with {self.current_user['ci']}): ").strip()
            participantes = [ci.strip() for ci in participantes_str.split(",")]
            
            if self.current_user['ci'] not in participantes:
                participantes.insert(0, self.current_user['ci'])
            
            # Create reservation
            self.reservation.create_reservation(
                self.current_user['ci'],
                sala['nombre_sala'],
                sala['edificio'],
                fecha,
                turno['id_turno'],
                participantes
            )
        except ValueError as e:
            print(f"✗ Invalid input: {e}")
    
    def handle_update_attendance(self):
        """Handle attendance update"""
        if not self.current_user:
            print("✗ Please login first")
            return
        
        print("\n=== Update Attendance ===")
        try:
            id_reserva = int(input("Reservation ID: ").strip())
            
            # Get reservation details
            reserva = self.db.execute_fetchone(
                "SELECT * FROM reserva WHERE id_reserva = %s",
                (id_reserva,)
            )
            if not reserva:
                print("✗ Reservation not found")
                return
            
            # Get participants
            participantes = self.db.execute_query(
                "SELECT ci_participante FROM reserva_participante WHERE id_reserva = %s",
                (id_reserva,),
                fetch=True
            )
            
            if not participantes:
                print("✗ No participants found for this reservation")
                return
            
            print("\nParticipants:")
            asistencias = []
            for p in participantes:
                asist = input(f"Did {p['ci_participante']} attend? (y/n): ").strip().lower()
                asistencias.append(asist == 'y')
            
            self.reservation.update_attendance(
                id_reserva,
                [p['ci_participante'] for p in participantes],
                asistencias
            )
        except ValueError as e:
            print(f"✗ Invalid input: {e}")
    
    def handle_view_reservations(self):
        """Handle viewing reservations"""
        print("\n=== Active Reservations ===")
        nombre_sala = input("Filter by room name (optional): ").strip() or None
        edificio = input("Filter by building (optional): ").strip() or None
        fecha_str = input("Filter by date YYYY-MM-DD (optional): ").strip() or None
        
        fecha = None
        if fecha_str:
            try:
                fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
            except ValueError:
                print("✗ Invalid date format")
                return
        
        results = self.report.get_active_reservations_by_room_date(nombre_sala, edificio, fecha)
        if results:
            print(f"\nFound {len(results)} reservation(s):\n")
            for r in results:
                print(f"ID: {r['id_reserva']} | Room: {r['nombre_sala']} ({r['edificio']}) | "
                      f"Date: {r['fecha']} | Time: {r['hora_inicio']}-{r['hora_fin']} | "
                      f"Participants: {r['num_participantes']}")
        else:
            print("No reservations found")
    
    def handle_usage_stats(self):
        """Handle usage statistics"""
        print("\n=== Usage Statistics ===")
        results = self.report.get_usage_stats()
        if results:
            print("\nBuilding | Room Type | Total Reservations | Total Participants | Active Reservations")
            print("-" * 80)
            for r in results:
                print(f"{r['nombre_edificio']} | {r['tipo_sala']} | {r['total_reservas']} | "
                      f"{r['total_participantes']} | {r['reservas_activas']}")
        else:
            print("No statistics available")
    
    def handle_sanctioned_users(self):
        """Handle viewing sanctioned users"""
        print("\n=== Sanctioned Users ===")
        results = self.report.get_sanctioned_users()
        if results:
            print(f"\nFound {len(results)} user(s) with active sanctions:\n")
            for s in results:
                print(f"CI: {s['ci']} | Name: {s['nombre']} {s['apellido']} | "
                      f"Email: {s['email']} | Sanction: {s['fecha_inicio']} to {s['fecha_fin']} | "
                      f"Days remaining: {s['dias_restantes']}")
        else:
            print("No sanctioned users found")
    
    def run(self):
        """Run the main application loop"""
        if not self.setup():
            return
        
        while True:
            self.show_main_menu()
            choice = input("\nSelect option: ").strip()
            
            if choice == "1":
                self.handle_register()
            elif choice == "2":
                self.handle_login()
            elif choice == "3":
                self.handle_create_reservation()
            elif choice == "4":
                self.handle_update_attendance()
            elif choice == "5":
                self.handle_view_reservations()
            elif choice == "6":
                self.handle_usage_stats()
            elif choice == "7":
                self.handle_sanctioned_users()
            elif choice == "8":
                print("\nGoodbye!")
                break
            else:
                print("✗ Invalid option")


if __name__ == "__main__":
    app = ConsoleApp()
    app.run()
