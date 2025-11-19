# How to Run the Project

## Prerequisites
- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- Virtual environment (recommended)

## Step-by-Step Instructions

### 1. Run the Admin Support SQL Script (REQUIRED - First Time Only)

Before running the application for the first time, you need to add admin support to the database:

```bash
cd /Users/matipou/.cursor/worktrees/UcuDB1/EOkPl
mysql -h 100.100.101.1 -u root -p220505 UCU_SalasDeEstudio < add_admin_support.sql
```

Or manually in MySQL:
```sql
USE UCU_SalasDeEstudio;
ALTER TABLE participante ADD COLUMN is_admin BOOLEAN DEFAULT FALSE NOT NULL;
UPDATE participante SET is_admin = TRUE WHERE email = 'matipousi22@gmail.com';
```

### 2. Set Up Virtual Environment (If Not Already Done)

```bash
cd /Users/matipou/.cursor/worktrees/UcuDB1/EOkPl
python -m venv venv
```

### 3. Install Dependencies

**Option A: Using virtual environment's pip directly:**
```bash
./venv/bin/pip install -r requirements.txt
```

**Option B: Activate virtual environment first:**
```bash
source venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

### 4. Run the Application

**Option A: Using the run script:**
```bash
chmod +x run_web.sh
./run_web.sh
```

**Option B: Run directly with Python:**
```bash
./venv/bin/python app.py
```

Or if virtual environment is activated:
```bash
source venv/bin/activate
python app.py
```

### 5. Access the Application

Once running, open your browser and go to:
```
http://localhost:5000
```

## Important Notes

- The application will prompt you for database configuration on first run (or use built-in defaults)
- Admin user: Login with `matipousi22@gmail.com` to access admin features
- Regular users: Can view rooms, check sanctions, and make appointments
- Admin users: Can access all CRUD operations for rooms, sanctions, participants, and programs

## Troubleshooting

If you get database connection errors:
1. Make sure MySQL is running
2. Verify database credentials in `app.py` or use the interactive prompt
3. Ensure the database `UCU_SalasDeEstudio` exists (run `schema.sql` if needed)

If you get import errors:
1. Make sure all dependencies are installed: `pip install -r requirements.txt`
2. Verify you're using the correct Python environment

