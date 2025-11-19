"""
Sample Data Generator for UCU Study Room Reservation System
Generates comprehensive sample data for all database tables
"""

import os
import bcrypt
from datetime import datetime, date, timedelta
from random import choice, randint, sample
from main import DatabaseManager

# Database configuration - same as app.py
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '100.100.101.1'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', '220505'),
    'database': os.environ.get('DB_NAME', 'UCU_SalasDeEstudio')
}


class SampleDataGenerator:
    """Generates comprehensive sample data"""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
        
    def generate_all(self):
        """Generate all sample data"""
        print("=== Generating Sample Data ===\n")
        
        # Generate in order due to foreign key constraints
        self.generate_facultades()
        self.generate_programas()
        self.generate_edificios()
        self.generate_salas()
        self.generate_turnos()
        self.generate_participantes()
        self.generate_reservas()
        self.generate_sanciones()
        
        print("\n=== Sample Data Generation Complete ===")
    
    def generate_facultades(self):
        """Generate faculties"""
        print("Generating facultades...")
        facultades = [
            "Ingeniería",
            "Ciencias Empresariales",
            "Humanidades",
            "Derecho",
            "Comunicación",
            "Arquitectura",
            "Psicología"
        ]
        
        for fac in facultades:
            try:
                self.db.execute_query(
                    "INSERT IGNORE INTO facultad (nombre) VALUES (%s)",
                    (fac,)
                )
            except Exception as e:
                print(f"  Warning: {e}")
        
        print(f"✓ Generated {len(facultades)} facultades")
    
    def generate_programas(self):
        """Generate academic programs"""
        print("Generating programas académicos...")
        
        # Get all faculties
        facultades = self.db.execute_query("SELECT * FROM facultad", fetch=True)
        if not facultades:
            print("  Error: No facultades found")
            return
        
        # Map of facultad names to programs
        programas_map = {
            "Ingeniería": [
                ("Ingeniería en Sistemas", "grado"),
                ("Ingeniería Industrial", "grado"),
                ("Ingeniería Civil", "grado"),
                ("Maestría en Informática", "posgrado"),
                ("Maestría en Ingeniería", "posgrado"),
            ],
            "Ciencias Empresariales": [
                ("Administración", "grado"),
                ("Contador Público", "grado"),
                ("Marketing", "grado"),
                ("MBA", "posgrado"),
            ],
            "Humanidades": [
                ("Letras", "grado"),
                ("Historia", "grado"),
                ("Maestría en Literatura", "posgrado"),
            ],
            "Derecho": [
                ("Abogacía", "grado"),
                ("Maestría en Derecho", "posgrado"),
            ],
            "Comunicación": [
                ("Comunicación Social", "grado"),
                ("Periodismo", "grado"),
            ],
            "Arquitectura": [
                ("Arquitectura", "grado"),
                ("Diseño de Interiores", "grado"),
            ],
            "Psicología": [
                ("Psicología", "grado"),
                ("Maestría en Psicología Clínica", "posgrado"),
            ]
        }
        
        count = 0
        for fac in facultades:
            programas = programas_map.get(fac['nombre'], [])
            for nombre, tipo in programas:
                try:
                    self.db.execute_query(
                        "INSERT IGNORE INTO programa_academico (nombre_programa, id_facultad, tipo) VALUES (%s, %s, %s)",
                        (nombre, fac['id_facultad'], tipo)
                    )
                    count += 1
                except Exception as e:
                    print(f"  Warning: {e}")
        
        print(f"✓ Generated {count} programas académicos")
    
    def generate_edificios(self):
        """Generate buildings"""
        print("Generating edificios...")
        edificios = [
            ("Edificio Central", "Av. 8 de Octubre 2738", "Montevideo"),
            ("Edificio Norte", "Av. Italia 6201", "Montevideo"),
            ("Edificio Sur", "Av. Libertador 1565", "Montevideo"),
            ("Sede Punta del Este", "Parada 2 de la Brava", "Maldonado"),
            ("Campus Colonia", "Av. General Flores 456", "Colonia"),
        ]
        
        for ed in edificios:
            try:
                self.db.execute_query(
                    "INSERT IGNORE INTO edificio (nombre_edificio, direccion, departamento) VALUES (%s, %s, %s)",
                    ed
                )
            except Exception as e:
                print(f"  Warning: {e}")
        
        print(f"✓ Generated {len(edificios)} edificios")
    
    def generate_salas(self):
        """Generate rooms"""
        print("Generating salas...")
        
        edificios = self.db.execute_query("SELECT nombre_edificio FROM edificio", fetch=True)
        if not edificios:
            print("  Error: No edificios found")
            return
        
        # Generate rooms for each building
        salas_data = []
        for edificio in edificios:
            ed_name = edificio['nombre_edificio']
            # Each building gets different rooms
            if "Central" in ed_name:
                salas_data.extend([
                    ("Sala A", ed_name, 10, "libre"),
                    ("Sala B", ed_name, 15, "libre"),
                    ("Sala C", ed_name, 8, "posgrado"),
                    ("Sala D", ed_name, 20, "libre"),
                    ("Aula Magna", ed_name, 50, "libre"),
                ])
            elif "Norte" in ed_name:
                salas_data.extend([
                    ("Sala 1", ed_name, 12, "libre"),
                    ("Sala 2", ed_name, 6, "docente"),
                    ("Sala 3", ed_name, 10, "libre"),
                    ("Sala 4", ed_name, 8, "posgrado"),
                ])
            elif "Sur" in ed_name:
                salas_data.extend([
                    ("Sala Alpha", ed_name, 15, "libre"),
                    ("Sala Beta", ed_name, 10, "libre"),
                    ("Sala Gamma", ed_name, 12, "libre"),
                ])
            else:
                # Default rooms for other buildings
                salas_data.extend([
                    (f"Sala {i}", ed_name, randint(8, 15), choice(["libre", "libre", "libre", "posgrado"]))
                    for i in range(1, 4)
                ])
        
        count = 0
        for sala in salas_data:
            try:
                self.db.execute_query(
                    "INSERT IGNORE INTO sala (nombre_sala, edificio, capacidad, tipo_sala) VALUES (%s, %s, %s, %s)",
                    sala
                )
                count += 1
            except Exception as e:
                print(f"  Warning: {e}")
        
        print(f"✓ Generated {count} salas")
    
    def generate_turnos(self):
        """Generate time slots if empty"""
        print("Generating turnos...")
        count = self.db.execute_fetchone("SELECT COUNT(*) as cnt FROM turno")
        
        if not count or count['cnt'] == 0:
            for hour in range(8, 23):  # 8 AM to 11 PM
                hora_inicio = f"{hour:02d}:00:00"
                hora_fin = f"{hour+1:02d}:00:00"
                try:
                    self.db.execute_query(
                        "INSERT INTO turno (hora_inicio, hora_fin) VALUES (%s, %s)",
                        (hora_inicio, hora_fin)
                    )
                except Exception as e:
                    print(f"  Warning: {e}")
            print(f"✓ Generated 15 turnos (8:00-23:00)")
        else:
            print(f"✓ Turnos already exist ({count['cnt']} turnos)")
    
    def generate_participantes(self):
        """Generate participants with login and program associations"""
        print("Generating participantes...")
        
        # Sample names
        nombres = [
            "Juan", "María", "Carlos", "Ana", "Pedro", "Lucía", "Diego", "Laura",
            "Miguel", "Carmen", "Roberto", "Patricia", "Fernando", "Silvia", "Andrés",
            "Mónica", "José", "Elena", "Daniel", "Claudia", "Luis", "Marta", "Ricardo",
            "Paula", "Alejandro", "Cristina", "Sergio", "Natalia", "Pablo", "Valentina",
            "Gonzalo", "Florencia", "Martín", "Constanza", "Federico", "Isabel", "Sebastián",
            "Amanda", "Emilio", "Beatriz", "Rafael", "Diana", "Guillermo", "Andrea",
            "Eduardo", "Vanesa", "Mauricio", "Gabriela", "Ignacio", "Roxana"
        ]
        
        apellidos = [
            "García", "Rodríguez", "González", "Fernández", "López", "Martínez", "Sánchez",
            "Pérez", "Gómez", "Martín", "Jiménez", "Ruiz", "Hernández", "Díaz", "Moreno",
            "Muñoz", "Álvarez", "Romero", "Alonso", "Gutiérrez", "Navarro", "Torres",
            "Domínguez", "Vázquez", "Ramos", "Gil", "Ramírez", "Serrano", "Blanco", "Suárez",
            "Molina", "Morales", "Ortega", "Delgado", "Castro", "Ortiz", "Rubio", "Marín",
            "Sanz", "Núñez", "Iglesias", "Medina", "Garrido", "Cortés", "Castillo", "Santos",
            "Lozano", "Guerrero", "Cano", "Prieto", "Méndez", "Calvo", "Cruz", "Gallego"
        ]
        
        # Get academic programs
        programas = self.db.execute_query(
            "SELECT nombre_programa, id_facultad, tipo FROM programa_academico",
            fetch=True
        )
        if not programas:
            print("  Error: No programas found")
            return
        
        participantes_created = []
        default_password = "password123"  # Default password for all users
        hashed_password = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Generate 100 participants
        for i in range(1, 101):
            ci = f"{randint(1000000, 9999999)}-{randint(1, 9)}"
            nombre = choice(nombres)
            apellido = choice(apellidos)
            email = f"{nombre.lower()}.{apellido.lower()}{i}@ucu.edu.uy"
            
            try:
                # Insert participant
                self.db.execute_query(
                    "INSERT IGNORE INTO participante (ci, nombre, apellido, email) VALUES (%s, %s, %s, %s)",
                    (ci, nombre, apellido, email)
                )
                
                # Insert login (only if participant was inserted)
                check = self.db.execute_fetchone("SELECT ci FROM participante WHERE ci = %s", (ci,))
                if check:
                    try:
                        self.db.execute_query(
                            "INSERT IGNORE INTO login (correo, password) VALUES (%s, %s)",
                            (email, hashed_password)
                        )
                    except Exception:
                        pass  # Login might already exist
                    
                    # Associate with 1-2 random programs
                    num_programs = randint(1, 2)
                    selected_programs = sample(programas, min(num_programs, len(programas)))
                    
                    for prog in selected_programs:
                        # Determine role based on program type and probability
                        if prog['tipo'] == 'posgrado':
                            rol = choice(['alumno', 'docente'])  # Higher chance of being alumno
                        else:
                            rol = 'alumno' if randint(1, 10) > 2 else 'docente'  # 80% alumno, 20% docente
                        
                        try:
                            self.db.execute_query(
                                "INSERT IGNORE INTO participante_programa_academico (ci_participante, nombre_programa, id_facultad, rol) VALUES (%s, %s, %s, %s)",
                                (ci, prog['nombre_programa'], prog['id_facultad'], rol)
                            )
                        except Exception:
                            pass  # Association might already exist
                    
                    participantes_created.append(ci)
            except Exception as e:
                print(f"  Warning creating participant {ci}: {e}")
        
        print(f"✓ Generated {len(participantes_created)} participantes with login and program associations")
        print(f"  Default password for all users: {default_password}")
    
    def generate_reservas(self):
        """Generate reservations"""
        print("Generating reservas...")
        
        # Get available data
        salas = self.db.execute_query("SELECT nombre_sala, edificio, capacidad FROM sala", fetch=True)
        turnos = self.db.execute_query("SELECT id_turno FROM turno ORDER BY id_turno", fetch=True)
        participantes = self.db.execute_query("SELECT ci FROM participante", fetch=True)
        
        if not salas or not turnos or not participantes:
            print("  Error: Missing required data (salas, turnos, or participantes)")
            return
        
        # Generate reservations for past 30 days and next 60 days (extended for better testing)
        today = date.today()
        past_dates = [today + timedelta(days=i) for i in range(-30, 0)]
        future_dates = [today + timedelta(days=i) for i in range(1, 61)]
        all_dates = past_dates + future_dates
        
        estados = ['activa', 'finalizada', 'cancelada', 'sin asistencia']
        
        reservas_created = 0
        
        # First, generate random reservations (original logic)
        for _ in range(200):  # Increased from 150 to 200
            sala = choice(salas)
            fecha = choice(all_dates)
            turno = choice(turnos)
            # Bias towards 'activa' for future dates to test availability filter
            if fecha > today:
                estado = choice(['activa', 'activa', 'activa', 'cancelada'])  # 75% active for future
            else:
                estado = choice(estados)
            
            # Check if room is already reserved for this slot
            existing = self.db.execute_fetchone(
                "SELECT id_reserva FROM reserva WHERE nombre_sala = %s AND edificio = %s AND fecha = %s AND id_turno = %s",
                (sala['nombre_sala'], sala['edificio'], fecha, turno['id_turno'])
            )
            
            if existing:
                continue  # Skip if already reserved
            
            try:
                # Insert reservation
                self.db.execute_query(
                    "INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado) VALUES (%s, %s, %s, %s, %s)",
                    (sala['nombre_sala'], sala['edificio'], fecha, turno['id_turno'], estado)
                )
                
                # Get the reservation ID
                reserva = self.db.execute_fetchone(
                    "SELECT id_reserva FROM reserva WHERE nombre_sala = %s AND edificio = %s AND fecha = %s AND id_turno = %s",
                    (sala['nombre_sala'], sala['edificio'], fecha, turno['id_turno'])
                )
                
                if reserva:
                    id_reserva = reserva['id_reserva']
                    fecha_solicitud = datetime.now() - timedelta(days=randint(0, 60))
                    
                    # Add 1-5 participants (within room capacity)
                    num_participantes = min(randint(1, 5), sala['capacidad'])
                    selected_participantes = sample(participantes, min(num_participantes, len(participantes)))
                    
                    # For finalized reservations, set some attendance
                    for p in selected_participantes:
                        asistencia = False
                        if estado == 'finalizada':
                            asistencia = choice([True, True, True, False])  # 75% attendance
                        elif estado == 'sin asistencia':
                            asistencia = False
                        elif estado == 'cancelada':
                            asistencia = False
                        else:  # activa
                            asistencia = False  # Not yet attended
                        
                        try:
                            self.db.execute_query(
                                "INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia) VALUES (%s, %s, %s, %s)",
                                (p['ci'], id_reserva, fecha_solicitud, asistencia)
                            )
                        except Exception:
                            pass
                    
                    reservas_created += 1
            except Exception as e:
                print(f"  Warning creating reservation: {e}")
        
        # Additional: Generate more active reservations for specific future dates to test availability filter
        # Focus on next 7 days with multiple time slots per room
        print("  Generating additional active reservations for availability filter testing...")
        test_dates = [today + timedelta(days=i) for i in range(1, 8)]  # Next 7 days
        
        additional_created = 0
        for test_date in test_dates:
            # For each test date, try to fill multiple time slots across different rooms
            for sala in salas:
                # Try to create 2-4 reservations per room per day
                num_reservations = min(randint(2, 4), len(turnos))
                
                # Sample unique turnos without replacement
                selected_turnos = sample(turnos, num_reservations)
                
                for turno in selected_turnos:
                    
                    # Check if room is already reserved for this slot
                    existing = self.db.execute_fetchone(
                        "SELECT id_reserva FROM reserva WHERE nombre_sala = %s AND edificio = %s AND fecha = %s AND id_turno = %s",
                        (sala['nombre_sala'], sala['edificio'], test_date, turno['id_turno'])
                    )
                    
                    if existing:
                        continue  # Skip if already reserved
                    
                    try:
                        # Insert active reservation
                        self.db.execute_query(
                            "INSERT INTO reserva (nombre_sala, edificio, fecha, id_turno, estado) VALUES (%s, %s, %s, %s, %s)",
                            (sala['nombre_sala'], sala['edificio'], test_date, turno['id_turno'], 'activa')
                        )
                        
                        # Get the reservation ID
                        reserva = self.db.execute_fetchone(
                            "SELECT id_reserva FROM reserva WHERE nombre_sala = %s AND edificio = %s AND fecha = %s AND id_turno = %s",
                            (sala['nombre_sala'], sala['edificio'], test_date, turno['id_turno'])
                        )
                        
                        if reserva:
                            id_reserva = reserva['id_reserva']
                            fecha_solicitud = datetime.now() - timedelta(days=randint(0, 7))
                            
                            # Add 1-3 participants
                            num_participantes = min(randint(1, 3), sala['capacidad'])
                            selected_participantes = sample(participantes, min(num_participantes, len(participantes)))
                            
                            for p in selected_participantes:
                                try:
                                    self.db.execute_query(
                                        "INSERT INTO reserva_participante (ci_participante, id_reserva, fecha_solicitud_reserva, asistencia) VALUES (%s, %s, %s, %s)",
                                        (p['ci'], id_reserva, fecha_solicitud, False)
                                    )
                                except Exception:
                                    pass
                            
                            additional_created += 1
                    except Exception as e:
                        pass  # Silently skip duplicates or errors
        
        print(f"✓ Generated {reservas_created} random reservas with participantes")
        print(f"✓ Generated {additional_created} additional active reservas for availability testing")
        print(f"  Total: {reservas_created + additional_created} reservas")
    
    def generate_sanciones(self):
        """Generate sanctions"""
        print("Generating sanciones...")
        
        participantes = self.db.execute_query("SELECT ci FROM participante", fetch=True)
        if not participantes:
            print("  Error: No participantes found")
            return
        
        # Generate 10-15 sanctions
        today = date.today()
        sanciones_created = 0
        
        for _ in range(randint(10, 15)):
            participante = choice(participantes)
            ci = participante['ci']
            
            # Generate dates: some active, some past, some future
            tipo = choice(['past', 'active', 'future'])
            if tipo == 'past':
                fecha_fin = today - timedelta(days=randint(1, 30))
                fecha_inicio = fecha_fin - timedelta(days=randint(30, 60))
            elif tipo == 'active':
                fecha_inicio = today - timedelta(days=randint(1, 30))
                fecha_fin = today + timedelta(days=randint(1, 60))
            else:  # future
                fecha_inicio = today + timedelta(days=randint(1, 30))
                fecha_fin = fecha_inicio + timedelta(days=randint(30, 60))
            
            try:
                self.db.execute_query(
                    "INSERT INTO sancion_participante (ci_participante, fecha_inicio, fecha_fin) VALUES (%s, %s, %s)",
                    (ci, fecha_inicio, fecha_fin)
                )
                sanciones_created += 1
            except Exception as e:
                print(f"  Warning creating sanction: {e}")
        
        print(f"✓ Generated {sanciones_created} sanciones")


def main():
    """Main function"""
    print("UCU Study Room Reservation System - Sample Data Generator\n")
    
    db = DatabaseManager(**DB_CONFIG)
    
    if not db.connect():
        print("Error: Could not connect to database. Please check your configuration.")
        print(f"Attempted connection to: {DB_CONFIG['host']} as {DB_CONFIG['user']}")
        return
    
    try:
        generator = SampleDataGenerator(db)
        generator.generate_all()
        
        # Print summary
        print("\n=== Database Summary ===")
        tables = [
            'facultad', 'programa_academico', 'edificio', 'sala', 'turno',
            'participante', 'login', 'participante_programa_academico',
            'reserva', 'reserva_participante', 'sancion_participante'
        ]
        
        for table in tables:
            result = db.execute_fetchone(f"SELECT COUNT(*) as cnt FROM {table}")
            if result:
                print(f"{table:35} {result['cnt']:>5} records")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()



