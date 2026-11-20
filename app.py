import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-before-deploy")
os.makedirs("instance", exist_ok=True)
DB = os.path.join("instance", "hiretrack.db")

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    conn = g.pop("db", None)
    if conn: conn.close()

def init_db():
    c = db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL,
      email TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT DEFAULT 'candidate');
    CREATE TABLE IF NOT EXISTS jobs(id INTEGER PRIMARY KEY, title TEXT NOT NULL,
      company TEXT NOT NULL, location TEXT NOT NULL, kind TEXT NOT NULL,
      description TEXT NOT NULL, skills TEXT NOT NULL, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS applications(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL,
      job_id INTEGER NOT NULL, status TEXT DEFAULT 'Applied', applied TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      UNIQUE(user_id,job_id), FOREIGN KEY(user_id) REFERENCES users(id),
      FOREIGN KEY(job_id) REFERENCES jobs(id));
    """)
    if not c.execute("SELECT id FROM users WHERE email='admin@hiretrack.demo'").fetchone():
        c.execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
          ("HireTrack Admin","admin@hiretrack.demo",generate_password_hash("Admin123!"),"admin"))
    if c.execute("SELECT COUNT(*) n FROM jobs").fetchone()["n"] == 0:
        c.executemany("INSERT INTO jobs(title,company,location,kind,description,skills) VALUES(?,?,?,?,?,?)", [
        ("Python Developer Intern","NovaTech Labs","Noida","Internship","Build and test Python features and work with APIs.","Python, Flask, SQL, Git"),
        ("Junior Data Analyst","InsightWorks","Remote","Full-time","Clean datasets, analyse metrics and prepare reports.","Excel, SQL, Python, Power BI"),
        ("Frontend Developer Trainee","PixelCraft","Delhi NCR","Trainee","Create responsive interfaces and improve user experience.","HTML, CSS, JavaScript"),
        ("Backend Developer Intern","CloudBridge","Noida Hybrid","Internship","Support backend development and database operations.","Python, Flask, SQLite"),
        ("Customer Success Associate","LearnSphere","Noida","Full-time","Support customer onboarding, queries and CRM records.","Communication, Excel, CRM")])
    c.commit()

@app.before_request
def setup(): init_db()

def logged(view):
    @wraps(view)
    def wrapper(*a,**k):
        if not session.get("uid"):
            flash("Please log in first.","warning"); return redirect(url_for("login"))
        return view(*a,**k)
    return wrapper

def admin(view):
    @wraps(view)
    def wrapper(*a,**k):
        if session.get("role") != "admin":
            flash("Admin access only.","danger"); return redirect(url_for("home"))
        return view(*a,**k)
    return wrapper

@app.route("/")
def home():
    q=request.args.get("q","").strip()
    if q:
        p=f"%{q}%"
        jobs=db().execute("SELECT * FROM jobs WHERE title LIKE ? OR company LIKE ? OR location LIKE ? OR skills LIKE ? ORDER BY id DESC",(p,p,p,p)).fetchall()
    else: jobs=db().execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    applied=set()
    if session.get("uid"):
        applied={r["job_id"] for r in db().execute("SELECT job_id FROM applications WHERE user_id=?",(session["uid"],)).fetchall()}
    return render_template("home.html",jobs=jobs,q=q,applied=applied)

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower(); pw=request.form.get("password","")
        if not name or not email or len(pw)<8:
            flash("Enter your name, email and a password of at least 8 characters.","danger")
        else:
            try:
                db().execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",(name,email,generate_password_hash(pw))); db().commit()
                flash("Account created. Please log in.","success"); return redirect(url_for("login"))
            except sqlite3.IntegrityError: flash("Email is already registered.","danger")
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=db().execute("SELECT * FROM users WHERE email=?",(request.form.get("email","").strip().lower(),)).fetchone()
        if u and check_password_hash(u["password"],request.form.get("password","")):
            session.clear(); session.update(uid=u["id"],name=u["name"],role=u["role"])
            return redirect(url_for("admin_home" if u["role"]=="admin" else "home"))
        flash("Invalid email or password.","danger")
    return render_template("auth.html",mode="login")

@app.route("/logout")
def logout(): session.clear(); return redirect(url_for("home"))

@app.route("/apply/<int:jid>",methods=["POST"])
@logged
def apply(jid):
    try:
        db().execute("INSERT INTO applications(user_id,job_id) VALUES(?,?)",(session["uid"],jid)); db().commit()
        flash("Application submitted!","success")
    except sqlite3.IntegrityError: flash("You have already applied (or this job is unavailable).","warning")
    return redirect(url_for("applications"))

@app.route("/applications")
@logged
def applications():
    rows=db().execute("""SELECT a.*,j.title,j.company,j.location FROM applications a
      JOIN jobs j ON j.id=a.job_id WHERE a.user_id=? ORDER BY a.applied DESC""",(session["uid"],)).fetchall()
    return render_template("applications.html",rows=rows)

@app.route("/admin")
@logged
@admin
def admin_home():
    c=db()
    stats=[c.execute("SELECT COUNT(*) n FROM jobs").fetchone()["n"],
           c.execute("SELECT COUNT(*) n FROM users WHERE role='candidate'").fetchone()["n"],
           c.execute("SELECT COUNT(*) n FROM applications").fetchone()["n"],
           c.execute("SELECT COUNT(*) n FROM applications WHERE status='Applied'").fetchone()["n"]]
    rows=c.execute("""SELECT a.id,a.status,a.applied,u.name,u.email,j.title,j.company
      FROM applications a JOIN users u ON u.id=a.user_id JOIN jobs j ON j.id=a.job_id ORDER BY a.applied DESC""").fetchall()
    jobs=c.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    return render_template("admin.html",stats=stats,rows=rows,jobs=jobs)

@app.route("/admin/job",methods=["POST"])
@logged
@admin
def add_job():
    vals=[request.form.get(k,"").strip() for k in ("title","company","location","kind","description","skills")]
    if all(vals):
        db().execute("INSERT INTO jobs(title,company,location,kind,description,skills) VALUES(?,?,?,?,?,?)",vals); db().commit()
        flash("Job posted.","success")
    else: flash("Complete all job fields.","danger")
    return redirect(url_for("admin_home"))

@app.route("/admin/status/<int:aid>",methods=["POST"])
@logged
@admin
def status(aid):
    value=request.form.get("status")
    if value in {"Applied","Under Review","Shortlisted","Rejected","Selected"}:
        db().execute("UPDATE applications SET status=? WHERE id=?",(value,aid)); db().commit(); flash("Status updated.","success")
    return redirect(url_for("admin_home"))

if __name__=="__main__": app.run(debug=True)
