"""
Database Service Layer
Handles all database interactions and business logic
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Tuple
from main import DatabaseManager, AuthManager, ReservationManager, ReportManager, DataInitializer


class DatabaseService:
    """Service layer for database operations"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.auth = AuthManager(db)
        self.reservation = ReservationManager(db)
        self.report = ReportManager(db)
    
    # ==================== AUTHENTICATION ====================
    
    def login(self, email: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user info with admin status"""
        user = self.auth.login(email, password)
        if user:
            # Check if user is admin
            is_admin = self.is_admin(user['ci'])
            user['is_admin'] = is_admin
        return user
    
    def register(self, ci: str, nombre: str, apellido: str, email: str, password: str) -> bool:
        """Register a new user"""
        return self.auth.register(ci, nombre, apellido, email, password)
    
    def get_user_role(self, ci: str) -> Optional[Dict]:
        """Get user's role and program info"""
        return self.auth.get_user_role(ci)
    
    def is_admin(self, ci: str) -> bool:
        """Check if user is an admin"""
        try:
            result = self.db.execute_fetchone(
                "SELECT is_admin FROM participante WHERE ci = %s",
                (ci,)
            )
            # Handle both boolean and integer (0/1) values
            if result:
                is_admin_val = result.get('is_admin')
                return bool(is_admin_val) if is_admin_val is not None else False
            return False
        except Exception:
            # If column doesn't exist yet, return False
            return False
    
    # ==================== PARTICIPANTS ====================
    
    def get_all_participantes(self):
        """Get all participants"""
        return self.db.execute_query(
            "SELECT p.*, GROUP_CONCAT(CONCAT(ppa.rol, ' - ', ppa.nombre_programa) SEPARATOR ', ') as programas FROM participante p LEFT JOIN participante_programa_academico ppa ON p.ci = ppa.ci_participante GROUP BY p.ci ORDER BY p.apellido, p.nombre",
            fetch=True
        ) or []
    
    def get_participante(self, ci: str):
        """Get a single participant"""
        return self.db.execute_fetchone("SELECT * FROM participante WHERE ci = %s", (ci,))
    
    def create_participante(self, ci: str, nombre: str, apellido: str, email: str, password: str = None, nombre_programa: str = None, id_facultad: int = None, rol: str = 'alumno'):
        """Create a new participant"""
        # Check if exists
        existing = self.db.execute_fetchone("SELECT ci FROM participante WHERE ci = %s OR email = %s", (ci, email))
        if existing:
            return False, "Participant with this CI or email already exists"
        
        try:
            # Insert participant
            self.db.execute_query(
                "INSERT INTO participante (ci, nombre, apellido, email) VALUES (%s, %s, %s, %s)",
                (ci, nombre, apellido, email)
            )
            
            # Create login if password provided
            if password:
                import bcrypt
                hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                self.db.execute_query(
                    "INSERT INTO login (correo, password) VALUES (%s, %s)",
                    (email, hashed.decode('utf-8'))
                )
            
            # Associate with program if provided
            if nombre_programa and id_facultad:
                self.db.execute_query(
                    "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                    (ci, nombre_programa, int(id_facultad), rol)
                )
            
            return True, "Participant created successfully"
        except Exception as e:
            return False, str(e)
    
    def update_participante(self, ci: str, nombre: str, apellido: str, email: str):
        """Update participant information"""
        try:
            self.db.execute_query(
                "UPDATE participante SET nombre = %s, apellido = %s, email = %s WHERE ci = %s",
                (nombre, apellido, email, ci)
            )
            return True, "Participant updated successfully"
        except Exception as e:
            return False, str(e)
    
    def delete_participante(self, ci: str):
        """Delete a participant"""
        try:
            self.db.execute_query("DELETE FROM participante WHERE ci = %s", (ci,))
            return True, "Participant deleted successfully"
        except Exception as e:
            return False, str(e)
    
    def get_participante_programs(self, ci: str):
        """Get all programs for a participant"""
        return self.db.execute_query(
            "SELECT ppa.*, pa.tipo, f.nombre as nombre_facultad FROM participante_programa_academico ppa JOIN programa_academico pa ON ppa.nombre_programa = pa.nombre_programa AND ppa.id_facultad = pa.id_facultad JOIN facultad f ON pa.id_facultad = f.id_facultad WHERE ppa.ci_participante = %s",
            (ci,),
            fetch=True
        ) or []
    
    def add_participante_program(self, ci: str, nombre_programa: str, id_facultad: int, rol: str):
        """Add a program association to a participant"""
        try:
            # Check if already exists
            existing = self.db.execute_fetchone(
                "SELECT * FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
                (ci, nombre_programa, int(id_facultad))
            )
            if existing:
                return False, "Program already associated"
            
            self.db.execute_query(
                "INSERT INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                (ci, nombre_programa, int(id_facultad), rol)
            )
            return True, "Program added successfully"
        except Exception as e:
            return False, str(e)
    
    def remove_participante_program(self, ci: str, nombre_programa: str, id_facultad: int):
        """Remove a program association from a participant"""
        try:
            # Check how many programs the user has
            program_count = self.db.execute_fetchone(
                "SELECT COUNT(*) as cnt FROM participante_programa_academico WHERE ci_participante = %s",
                (ci,)
            )
            
            if program_count and program_count['cnt'] <= 1:
                return False, "Cannot remove the last program. A user must have at least one program associated."
            
            result = self.db.execute_query(
                "DELETE FROM participante_programa_academico WHERE ci_participante = %s AND nombre_programa = %s AND id_facultad = %s",
                (ci, nombre_programa, int(id_facultad))
            )
            
            if result is not None and result > 0:
                return True, "Program removed successfully"
            else:
                return False, "Program not found"
        except Exception as e:
            return False, str(e)
    
    def get_participantes_list(self):
        """Get all participants for dropdown"""
        return self.db.execute_query("SELECT ci, nombre, apellido, email FROM participante ORDER BY apellido, nombre", fetch=True) or []
    
    # ==================== PROGRAMS ====================
    
    def get_all_programas(self):
        """Get all academic programs"""
        return self.db.execute_query(
            "SELECT pa.*, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad ORDER BY f.nombre, pa.nombre_programa",
            fetch=True
        ) or []
    
    def get_programa(self, nombre_programa: str, id_facultad: int):
        """Get a single program"""
        return self.db.execute_fetchone(
            "SELECT pa.*, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad WHERE pa.nombre_programa = %s AND pa.id_facultad = %s",
            (nombre_programa, id_facultad)
        )
    
    def create_programa(self, nombre_programa: str, id_facultad: int, tipo: str):
        """Create a new academic program"""
        try:
            # Check if already exists
            existing = self.db.execute_fetchone(
                "SELECT * FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                (nombre_programa, int(id_facultad))
            )
            if existing:
                return False, "Program already exists"
            
            self.db.execute_query(
                "INSERT INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES (%s, %s, %s)",
                (nombre_programa, int(id_facultad), tipo)
            )
            return True, "Program created successfully"
        except Exception as e:
            return False, str(e)
    
    def update_programa(self, nombre_programa: str, id_facultad: int, nuevo_nombre: str, nuevo_id_facultad: int, tipo: str):
        """Update an academic program"""
        try:
            # If name or faculty changed, check if new combination exists
            if nuevo_nombre != nombre_programa or nuevo_id_facultad != id_facultad:
                existing = self.db.execute_fetchone(
                    "SELECT * FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                    (nuevo_nombre, nuevo_id_facultad)
                )
                if existing:
                    return False, "Program with this name and faculty already exists"
            
            self.db.execute_query(
                "UPDATE programa_academico SET nombre_programa = %s, id_facultad = %s, tipo = %s WHERE nombre_programa = %s AND id_facultad = %s",
                (nuevo_nombre, nuevo_id_facultad, tipo, nombre_programa, id_facultad)
            )
            return True, "Program updated successfully"
        except Exception as e:
            return False, str(e)
    
    def delete_programa(self, nombre_programa: str, id_facultad: int):
        """Delete an academic program"""
        try:
            # Check if there are participants associated
            participantes = self.db.execute_fetchone(
                "SELECT COUNT(*) as cnt FROM participante_programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                (nombre_programa, id_facultad)
            )
            
            if participantes and participantes['cnt'] > 0:
                return False, f"Cannot delete program because it has {participantes['cnt']} associated participant(s)"
            
            self.db.execute_query(
                "DELETE FROM programa_academico WHERE nombre_programa = %s AND id_facultad = %s",
                (nombre_programa, id_facultad)
            )
            return True, "Program deleted successfully"
        except Exception as e:
            return False, str(e)
    
    def get_programas(self):
        """Get all academic programs for dropdown"""
        return self.db.execute_query(
            "SELECT pa.nombre_programa, pa.id_facultad, pa.tipo, f.nombre as nombre_facultad FROM programa_academico pa JOIN facultad f ON pa.id_facultad = f.id_facultad ORDER BY f.nombre, pa.nombre_programa",
            fetch=True
        ) or []
    
    # ==================== ROOMS (SALAS) ====================
    
    def get_all_salas(self):
        """Get all rooms"""
        return self.db.execute_query(
            "SELECT s.*, e.direccion, e.departamento FROM sala s JOIN edificio e ON s.edificio = e.nombre_edificio ORDER BY s.edificio, s.nombre_sala",
            fetch=True
        ) or []
    
    def get_available_salas(self, fecha: date = None, id_turno: int = None):
        """Get available rooms, optionally filtered by date and time slot"""
        query = """
            SELECT s.*, e.direccion, e.departamento
            FROM sala s
            JOIN edificio e ON s.edificio = e.nombre_edificio
        """
        params = []
        
        if fecha and id_turno:
            query += """
                WHERE (s.nombre_sala, s.edificio) NOT IN (
                    SELECT r.nombre_sala, r.edificio
                    FROM reserva r
                    WHERE r.fecha = %s AND r.id_turno = %s AND r.estado = 'activa'
                )
            """
            params.extend([fecha, id_turno])
        
        query += " ORDER BY s.edificio, s.nombre_sala"
        return self.db.execute_query(query, tuple(params), fetch=True) or []
    
    def count_available_salas_now(self):
        """Count available rooms at the current time"""
        from datetime import datetime, time
        
        now = datetime.now()
        current_date = now.date()
        current_hour = now.hour
        current_time = time(current_hour, 0, 0)
        
        # Find the turno that matches the current hour
        turno = self.db.execute_fetchone(
            "SELECT id_turno FROM turno WHERE hora_inicio = %s",
            (current_time,)
        )
        
        if not turno:
            # If no turno matches current hour, return total number of rooms
            total = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM sala")
            return total['cnt'] if total else 0
        
        id_turno = turno['id_turno']
        
        # Count rooms that don't have an active reservation for current date and turno
        query = """
            SELECT COUNT(*) as cnt
            FROM sala s
            WHERE (s.nombre_sala, s.edificio) NOT IN (
                SELECT r.nombre_sala, r.edificio
                FROM reserva r
                WHERE r.fecha = %s AND r.id_turno = %s AND r.estado = 'activa'
            )
        """
        result = self.db.execute_fetchone(query, (current_date, id_turno))
        return result['cnt'] if result else 0
    
    def get_sala(self, nombre_sala: str, edificio: str):
        """Get a single room"""
        return self.db.execute_fetchone(
            "SELECT * FROM sala WHERE nombre_sala = %s AND edificio = %s",
            (nombre_sala, edificio)
        )
    
    def create_sala(self, nombre_sala: str, edificio: str, capacidad: int, tipo_sala: str):
        """Create a new room"""
        try:
            self.db.execute_query(
                "INSERT INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES (%s, %s, %s, %s)",
                (nombre_sala, edificio, capacidad, tipo_sala)
            )
            return True, "Room created successfully"
        except Exception as e:
            return False, str(e)
    
    def update_sala(self, nombre_sala: str, edificio: str, capacidad: int, tipo_sala: str):
        """Update a room"""
        try:
            self.db.execute_query(
                "UPDATE sala SET capacidad = %s, tipo_sala = %s WHERE nombre_sala = %s AND edificio = %s",
                (capacidad, tipo_sala, nombre_sala, edificio)
            )
            return True, "Room updated successfully"
        except Exception as e:
            return False, str(e)
    
    def delete_sala(self, nombre_sala: str, edificio: str):
        """Delete a room"""
        try:
            self.db.execute_query("DELETE FROM sala WHERE nombre_sala = %s AND edificio = %s", (nombre_sala, edificio))
            return True, "Room deleted successfully"
        except Exception as e:
            return False, str(e)
    
    def get_edificios(self):
        """Get all buildings"""
        return self.db.execute_query("SELECT * FROM edificio ORDER BY nombre_edificio", fetch=True) or []
    
    # ==================== RESERVATIONS ====================
    
    def get_all_reservas(self):
        """Get all reservations"""
        return self.db.execute_query(
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
    
    def get_user_reservas(self, ci: str):
        """Get reservations for a specific user"""
        return self.db.execute_query(
            """SELECT r.*, s.capacidad, s.tipo_sala, t.hora_inicio, t.hora_fin,
               COUNT(rp.ci_participante) as num_participantes
               FROM reserva r
               JOIN sala s ON r.nombre_sala = s.nombre_sala AND r.edificio = s.edificio
               JOIN turno t ON r.id_turno = t.id_turno
               JOIN reserva_participante rp ON r.id_reserva = rp.id_reserva
               WHERE rp.ci_participante = %s
               GROUP BY r.id_reserva
               ORDER BY r.fecha DESC, t.hora_inicio DESC""",
            (ci,),
            fetch=True
        ) or []
    
    def get_reserva(self, id_reserva: int):
        """Get a single reservation"""
        return self.db.execute_fetchone("SELECT * FROM reserva WHERE id_reserva = %s", (id_reserva,))
    
    def create_reserva(self, ci: str, nombre_sala: str, edificio: str, fecha: date, id_turno: int, participantes: List[str]):
        """Create a new reservation"""
        id_reserva = self.reservation.create_reservation(ci, nombre_sala, edificio, fecha, id_turno, participantes)
        if id_reserva:
            return True, "Reservation created successfully", id_reserva
        else:
            return False, "Error creating reservation. Check restrictions.", None
    
    def update_reserva_estado(self, id_reserva: int, estado: str):
        """Update reservation status"""
        try:
            self.db.execute_query(
                "UPDATE reserva SET estado = %s WHERE id_reserva = %s",
                (estado, id_reserva)
            )
            return True, "Reservation updated successfully"
        except Exception as e:
            return False, str(e)
    
    def delete_reserva(self, id_reserva: int):
        """Delete a reservation"""
        try:
            self.db.execute_query("DELETE FROM reserva WHERE id_reserva = %s", (id_reserva,))
            return True, "Reservation deleted successfully"
        except Exception as e:
            return False, str(e)
    
    def get_reserva_participantes(self, id_reserva: int):
        """Get participants for a reservation"""
        return self.db.execute_query(
            "SELECT rp.*, p.nombre, p.apellido FROM reserva_participante rp JOIN participante p ON rp.ci_participante = p.ci WHERE rp.id_reserva = %s",
            (id_reserva,),
            fetch=True
        ) or []
    
    def update_attendance(self, id_reserva: int, participantes_ci: List[str], asistencias: List[bool]):
        """Update attendance for a reservation"""
        return self.reservation.update_attendance(id_reserva, participantes_ci, asistencias)
    
    def get_turnos(self):
        """Get all time slots"""
        return self.db.execute_query("SELECT * FROM turno ORDER BY hora_inicio", fetch=True) or []
    
    # ==================== SANCTIONS ====================
    
    def get_all_sanciones(self):
        """Get all sanctions"""
        return self.db.execute_query(
            """SELECT sp.*, p.nombre, p.apellido, p.email, p.ci
               FROM sancion_participante sp
               JOIN participante p ON sp.ci_participante = p.ci
               ORDER BY sp.fecha_inicio DESC""",
            fetch=True
        ) or []
    
    def get_user_sanciones(self, ci: str):
        """Get active sanctions for a specific user"""
        return self.db.execute_query(
            """SELECT sp.*, p.nombre, p.apellido, p.email, p.ci
               FROM sancion_participante sp
               JOIN participante p ON sp.ci_participante = p.ci
               WHERE sp.ci_participante = %s AND sp.fecha_fin >= CURDATE()
               ORDER BY sp.fecha_inicio DESC""",
            (ci,),
            fetch=True
        ) or []
    
    def get_sancion(self, id_sancion: int):
        """Get a single sanction"""
        return self.db.execute_fetchone("SELECT * FROM sancion_participante WHERE id_sancion = %s", (id_sancion,))
    
    def create_sancion(self, ci_participante: str, fecha_inicio: date, fecha_fin: date):
        """Create a new sanction"""
        try:
            if fecha_fin <= fecha_inicio:
                return False, "End date must be after start date"
            
            self.db.execute_query(
                "INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin) VALUES (%s, %s, %s)",
                (ci_participante, fecha_inicio, fecha_fin)
            )
            return True, "Sanction created successfully"
        except Exception as e:
            return False, str(e)
    
    def update_sancion(self, id_sancion: int, fecha_inicio: date, fecha_fin: date):
        """Update a sanction"""
        try:
            if fecha_fin <= fecha_inicio:
                return False, "End date must be after start date"
            
            self.db.execute_query(
                "UPDATE sancion_participante SET fecha_inicio = %s, fecha_fin = %s WHERE id_sancion = %s",
                (fecha_inicio, fecha_fin, id_sancion)
            )
            return True, "Sanction updated successfully"
        except Exception as e:
            return False, str(e)
    
    def delete_sancion(self, id_sancion: int):
        """Delete a sanction"""
        try:
            self.db.execute_query("DELETE FROM sancion_participante WHERE id_sancion = %s", (id_sancion,))
            return True, "Sanction deleted successfully"
        except Exception as e:
            return False, str(e)
    
    # ==================== REPORTS ====================
    
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        participantes_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM participante")['cnt']
        salas_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM sala")['cnt']
        reservas_activas_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM reserva WHERE estado = 'activa'")['cnt']
        sanciones_activas_count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM sancion_participante WHERE fecha_fin >= CURDATE()")['cnt']
        
        return {
            'participantes_count': participantes_count,
            'salas_count': salas_count,
            'reservas_activas_count': reservas_activas_count,
            'sanciones_activas_count': sanciones_activas_count
        }
    
    def get_facultades(self):
        """Get all faculties"""
        return self.db.execute_query("SELECT * FROM facultad ORDER BY nombre", fetch=True) or []

