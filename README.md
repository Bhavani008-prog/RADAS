# Road Accident Data Analysis System (RADAS)

A full-stack, data-driven web application for road accident data recording, severity assessment, trend visualization, and statistical analysis built using **Python, Flask, MySQL, Pandas, NumPy, and Matplotlib**.

---

## 🚦 Features

- **Executive Dashboard**: Database-backed key metrics (Total Accidents, Most Affected Region, Most Common Vehicle, Peak Accident Hour) and severity breakdown.
- **Analytical Insights & Charts**: Auto-generated visualizations produced dynamically with Matplotlib:
  - Accidents by Hour of Day
  - Accidents by Location (Region)
  - Accidents by Severity (Minor, Serious, Fatal)
  - Accidents by Time Period (Morning, Afternoon, Evening, Night)
- **Accident Records Management**:
  - Displays sequential serial numbers (`S.No.`) alongside database IDs.
  - Complete details: Date & Time, Region, Road Name, Vehicle Type, Severity, Weather, and **Cause of Accident**.
  - Safe record deletion with accessible confirmation modal and CSRF protection.
- **Add Accident Record**:
  - Validated input fields with location auto-association.
  - Includes required **Cause of Accident** dropdown (Rash Driving, Over Speeding, Drunk Driving, Street Light Problem, Poor Road Conditions, Distracted Driving, Traffic Rule Violation, Other) with a conditional text field for custom causes.
- **Authentication & Security**:
  - Open user registration (`/signup`) and authentication (`/login`).
  - Passwords hashed using Werkzeug `pbkdf2:sha256` (no plain text).
  - CSRF token validation on all POST requests.
  - Route protection (`@login_required`) and HTTP cache control.
- **UI/UX**:
  - Responsive design with sidebar navigation.
  - Seamless Light Mode and Dark Mode toggle preserved in `localStorage`.

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask, Werkzeug, Gunicorn (Production WSGI)
- **Database**: MySQL (compatible with local MySQL and Railway MySQL)
- **Data Analysis**: Pandas, NumPy, Matplotlib
- **Frontend**: Semantic HTML5, Vanilla CSS (Design Tokens, Light/Dark theme), JavaScript

---

## 📁 Project Structure

```
RoadAccidentAnalysis/
│
├── app.py                  # Flask web application routes & controllers
├── database.py             # Database connection with Railway & local env support
├── init_db.py              # Self-healing database initialization & schema migrations
├── analysis.py             # Pandas aggregations & Matplotlib chart generation
├── gunicorn.conf.py        # Production Gunicorn WSGI configuration
├── Procfile                # Railway / PaaS process runner
├── requirements.txt        # Production dependencies
│
├── .env.example            # Environment variables template
├── .gitignore              # Files excluded from git tracking
│
├── static/
│   ├── style.css           # Global stylesheet with light & dark theme variables
│   └── charts/             # Generated Matplotlib charts (hourly, location, etc.)
│       └── .gitkeep
│
└── templates/
    ├── base.html           # Base layout with sidebar, navbar, and delete modal
    ├── index.html          # Dashboard & Add Accident form
    ├── login.html          # Authentication login view
    ├── signup.html         # User registration view
    ├── analysis.html       # Chart visualization gallery
    └── accidents.html      # Records table with S.No. and Cause of Accident
```

---

## 💻 Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/your-username/road-accident-analysis.git
cd road-accident-analysis
```

### 2. Create and activate a virtual environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Copy `.env.example` to `.env` and fill in your MySQL credentials:
```bash
cp .env.example .env
```
Example `.env`:
```env
FLASK_SECRET_KEY=your_secure_secret_key_here
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=road_accident_db
PORT=5000
```

### 5. Run the application
```bash
python app.py
```
Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser. Database tables and the default administrator account (`admin` / `Admin@123`) will be initialized automatically.

---

## 🚀 Preparing for GitHub

To push this project to your GitHub account:

1. Initialize git (if not already done):
   ```bash
   git init
   git branch -M main
   ```
2. Verify that sensitive files (`.env`, `venv/`, `backup/`) are ignored:
   ```bash
   git status
   ```
3. Stage and commit all project files:
   ```bash
   git add .
   git commit -m "Initial commit: Production-ready Road Accident Data Analysis System"
   ```
4. Create a new repository on GitHub (e.g. `road-accident-analysis`) and link your remote:
   ```bash
   git remote add origin https://github.com/<your-username>/road-accident-analysis.git
   git push -u origin main
   ```

---

## 🚂 Deploying to Railway

### Step 1: Create a Railway Project
1. Log in to [Railway.app](https://railway.app/).
2. Click **"New Project"** → **"Deploy from GitHub repo"**.
3. Select your `road-accident-analysis` repository.

### Step 2: Add MySQL Database on Railway
1. In your Railway project canvas, click **"+ New"** → **"Database"** → **"Add MySQL"**.
2. Railway will automatically provision a managed MySQL instance and provide the following environment variables:
   - `MYSQLHOST`
   - `MYSQLPORT`
   - `MYSQLUSER`
   - `MYSQLPASSWORD`
   - `MYSQLDATABASE`
   - `MYSQL_URL`

### Step 3: Configure Service Variables
In your web service's **Variables** tab, ensure you add:
- `FLASK_SECRET_KEY`: Set to any long, random string (e.g., generated with `openssl rand -hex 32`).
- (Optional) `ADMIN_USERNAME`: Custom administrator username (defaults to `admin`).
- (Optional) `ADMIN_PASSWORD`: Custom administrator password (defaults to `Admin@123`).

> **Note**: `database.py` automatically detects Railway's `MYSQL_URL` or individual `MYSQL*` variables without requiring any code changes.

### Step 4: Verify Deployment
- Railway will automatically read `Procfile` and launch:
  ```bash
  gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app
  ```
- On the first boot, `init_db.py` will automatically create the `locations`, `accidents`, and `users` tables, seed the baseline dataset, and verify the admin account.
- Click on the generated Railway public domain to view your live application.

---

## 📄 License
This project is open-source and available under the [MIT License](LICENSE).

