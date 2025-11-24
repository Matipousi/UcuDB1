# UCU Study Room Reservation System

A simple web application for managing study room reservations at UCU.

## Quick Start

### Option 1: Using Docker (Easiest)

If you have Docker installed, this is the simplest way to run everything:

```bash
docker-compose up -d
```

That's it! The app will be available at `http://localhost:5001` and the database will be set up automatically.

To stop it:
```bash
docker-compose down
```

To stop and delete all data:
```bash
docker-compose down -v
```

### Option 2: Running Locally

#### Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   ```

2. **Install dependencies:**
   ```bash
   # Linux/Mac
   ./venv/bin/pip install -r requirements.txt
   
   # Windows
   venv\Scripts\pip install -r requirements.txt
   ```

3. **Set up the database:**
   - Make sure MySQL is running
   - Create the database: `mysql -u root -p < schema.sql`
   - Or configure the connection in `app.py` if needed

#### Running the Application

**Web version** (opens in browser at `http://localhost:5000`):

- **Linux/Mac:** `./run_web.sh`
- **Windows:** `run_web.bat`

**Console version** (command-line interface):

- **Linux/Mac:** `./run_console.sh`
- **Windows:** `run_console.bat`

That's it! The scripts handle everything for you.

## What This Does

- Users can register and log in
- Create and manage room reservations
- Track attendance
- View reports and statistics
- Manage participants, rooms, and sanctions

## Requirements

- Python 3.8+
- MySQL 5.7+ (or use Docker)
- A web browser

## Need Help?

Check the logs if something goes wrong, or look at the code - it's pretty straightforward!
