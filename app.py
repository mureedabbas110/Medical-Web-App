import sqlite3, os, json
from datetime import date, datetime, timedelta
from functools import wraps
from flask import Flask, g, render_template, request, redirect, url_for, session, flash, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")
DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clinic.db")
MODULES = {"opd": "OPD", "ot": "Operations (OT)", "ultrasound": "Ultrasound", "xray": "X-ray",
           "lab": "Laboratory", "ecg": "ECG", "sugar": "Sugar"}
DOCTORS = ["Dr. Abdul Hayee Phulpoto", "Dr. Khair Un Nisa Panhyar", "Dr. Allah Warayo Panhyar",
           "Dr. Dost Mohammad Sohu", "Dr. Salman Wahid Shaikh", "Dr. Mohammad Awais Panhyar"]
TESTS = [("CBC", 400), ("Blood Sugar (Random)", 100), ("Urine R/E", 150), ("Hepatitis B", 600),
         ("Hepatitis C", 600), ("Typhidot", 500), ("Malaria Parasite", 200), ("Lipid Profile", 1200),
         ("LFTs", 900), ("Creatinine", 300), ("Pregnancy Test", 200)]

OPS = [("C-Section", "Gynae", 25000), ("Normal Delivery", "Gynae", 10000), ("D&C", "Gynae", 8000),
       ("Hysterectomy", "Gynae", 40000), ("Fracture Fixation (Plate/Rod)", "Orthopedic", 40000),
       ("Fracture Reduction & POP", "Orthopedic", 5000), ("Arthroscopy / Joint", "Orthopedic", 50000),
       ("Appendectomy", "Surgery", 20000), ("Hernia Repair", "Surgery", 25000),
       ("Gallbladder Removal", "Surgery", 35000), ("Minor Surgery", "Surgery", 3000)]

def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB); g.db.row_factory = sqlite3.Row
    return g.db
@app.teardown_appcontext
def close_db(e=None):
    d = g.pop("db", None)
    if d: d.close()
def qa(s, a=()): return db().execute(s, a).fetchall()
def q1(s, a=()): return db().execute(s, a).fetchone()
def ex(s, a=()):
    c = db().execute(s, a); db().commit(); return c
def today(): return date.today().isoformat()

def init_db():
    d = sqlite3.connect(DB)
    d.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT);
    CREATE TABLE IF NOT EXISTS doctors(id INTEGER PRIMARY KEY, name TEXT, fee REAL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS tests(id INTEGER PRIMARY KEY, name TEXT, price REAL);
    CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY, pid TEXT UNIQUE, name TEXT, age_y INTEGER,
        age_m INTEGER, address TEXT, phone TEXT);
    CREATE TABLE IF NOT EXISTS visits(id INTEGER PRIMARY KEY, token_no INTEGER, vdate TEXT, module TEXT,
        patient_id INTEGER, pid TEXT, name TEXT, age_y INTEGER, age_m INTEGER, address TEXT, phone TEXT,
        referred_by TEXT, doctor_id INTEGER, doctor_name TEXT, tests TEXT, fee REAL, discount REAL,
        total REAL, created_by TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS operations(id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL);
    CREATE TABLE IF NOT EXISTS medicines(id INTEGER PRIMARY KEY, name TEXT, company TEXT, stock REAL DEFAULT 0, buy_price REAL DEFAULT 0, sell_price REAL DEFAULT 0, expiry TEXT DEFAULT '', min_stock REAL DEFAULT 10);
    CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY, bill_no INTEGER, sdate TEXT, customer TEXT, phone TEXT, subtotal REAL, discount REAL, total REAL, profit REAL, created_by TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS sale_items(id INTEGER PRIMARY KEY, sale_id INTEGER, med_id INTEGER, name TEXT, qty REAL, price REAL, cost REAL);
    CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
    CREATE INDEX IF NOT EXISTS ix_v ON visits(vdate, module, doctor_name);
    """)
    cols = [r[1] for r in d.execute("PRAGMA table_info(visits)")]
    for c, t in (("op_type", "TEXT DEFAULT ''"), ("room", "REAL DEFAULT 0"), ("other", "REAL DEFAULT 0"),
                 ("advance", "REAL DEFAULT 0"), ("notes", "TEXT DEFAULT ''"), ("detail", "TEXT DEFAULT ''")):
        if c not in cols: d.execute("ALTER TABLE visits ADD COLUMN %s %s" % (c, t))
    if not d.execute("SELECT 1 FROM operations").fetchone():
        d.executemany("INSERT INTO operations(name,category,price) VALUES(?,?,?)", OPS)
    if not d.execute("SELECT 1 FROM users").fetchone():
        d.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", ("admin", generate_password_hash("admin123"), "admin"))
        d.execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", ("user", generate_password_hash("user123"), "user"))
        d.executemany("INSERT INTO doctors(name,fee) VALUES(?,500)", [(n,) for n in DOCTORS])
        d.executemany("INSERT INTO tests(name,price) VALUES(?,?)", TESTS)
    d.commit(); d.close()
init_db()

@app.before_request
def gate():
    if request.endpoint in ("login", "static"): return
    if "user" not in session: return redirect(url_for("login"))
def admin(f):
    @wraps(f)
    def w(*a, **k):
        if session.get("role") != "admin": abort(403)
        return f(*a, **k)
    return w
@app.context_processor
def ctx(): return dict(MODULES=MODULES, today=today(), path=request.path)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = q1("SELECT * FROM users WHERE username=?", (request.form["username"].strip(),))
        if u and check_password_hash(u["password"], request.form["password"]):
            session.update(user=u["username"], role=u["role"]); return redirect("/")
        flash("Wrong username or password", "err")
    return render_template("login.html")
@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))

@app.route("/")
def dashboard():
    t = today()
    stats = q1("SELECT COUNT(*) n, COALESCE(SUM(total),0) amt FROM visits WHERE vdate=?", (t,))
    pats = q1("SELECT COUNT(*) n FROM patients")["n"]
    docs = qa("SELECT d.name, COUNT(v.id) n, COALESCE(SUM(v.total),0) amt FROM doctors d LEFT JOIN visits v "
              "ON v.doctor_name=d.name AND v.vdate=? GROUP BY d.id ORDER BY d.id", (t,))
    mods = {r["module"]: r for r in qa("SELECT module, COUNT(*) n, SUM(total) amt FROM visits WHERE vdate=? GROUP BY module", (t,))}
    latest = qa("SELECT * FROM visits WHERE vdate=? ORDER BY id DESC LIMIT 8", (t,))
    mx = max([d["n"] for d in docs] + [1])
    st = q1("SELECT COUNT(*) n, COALESCE(SUM(total),0) t FROM sales WHERE sdate=?", (t,))
    low = q1("SELECT COUNT(*) n FROM medicines WHERE stock<=min_stock")["n"]
    soon = q1("SELECT COUNT(*) n FROM medicines WHERE expiry!='' AND expiry<=? AND stock>0", ((date.today() + timedelta(days=60)).isoformat(),))["n"]
    return render_template("dashboard.html", stats=stats, pats=pats, docs=docs, mods=mods, latest=latest, mx=mx, st=st, low=low, soon=soon)

def clean_num(v):
    try: return max(float(v or 0), 0)
    except ValueError: return 0

@app.route("/entry/<module>", methods=["GET", "POST"])
def entry(module):
    if module not in MODULES: abort(404)
    doctors, tests = qa("SELECT * FROM doctors ORDER BY name"), qa("SELECT * FROM tests ORDER BY name")
    ops = qa("SELECT * FROM operations ORDER BY category, name")
    if request.method == "POST":
        f = request.form
        name = f["name"].strip()
        if not name: flash("Patient name is required", "err"); return redirect(request.url)
        ay, am = int(clean_num(f.get("age_y"))), min(int(clean_num(f.get("age_m"))), 11)
        p = q1("SELECT * FROM patients WHERE pid=?", (f.get("pid", "").strip(),)) if f.get("pid", "").strip() else None
        vals = (name, ay, am, f.get("address", "").strip(), f.get("phone", "").strip())
        if p:
            ex("UPDATE patients SET name=?,age_y=?,age_m=?,address=?,phone=? WHERE id=?", vals + (p["id"],)); pid_n, pid = p["id"], p["pid"]
        else:
            c = ex("INSERT INTO patients(pid,name,age_y,age_m,address,phone) VALUES('',?,?,?,?,?)", vals)
            pid = "P-%06d" % c.lastrowid; ex("UPDATE patients SET pid=? WHERE id=?", (pid, c.lastrowid)); pid_n = c.lastrowid
        doc = q1("SELECT * FROM doctors WHERE id=?", (f.get("doctor_id") or 0,))
        if module == "opd" and not doc: flash("Select a doctor", "err"); return redirect(request.url)
        tnames, fee = "", clean_num(f.get("fee"))
        op_type, room, other, adv, detail = "", 0, 0, 0, ""
        if module == "lab":
            ids = [int(i) for i in f.getlist("tests") if i.isdigit()]
            rows = [r for r in (q1("SELECT * FROM tests WHERE id=?", (i,)) for i in ids) if r]
            if not rows: flash("Select at least one test", "err"); return redirect(request.url)
            tnames = ", ".join(r["name"] for r in rows); fee = sum(r["price"] for r in rows)
            detail = json.dumps([[r["name"], r["price"]] for r in rows])
        if module == "ot":
            op = q1("SELECT * FROM operations WHERE id=?", (f.get("op_id") or 0,))
            if not op or not doc: flash("Select operation and surgeon", "err"); return redirect(request.url)
            op_type = op["name"]; room = clean_num(f.get("room")); other = clean_num(f.get("other"))
        gross = fee + room + other
        disc = min(clean_num(f.get("discount")), gross); total = gross - disc
        if module == "ot": adv = min(clean_num(f.get("advance")), total)
        vdate = f.get("vdate") if session["role"] == "admin" and f.get("vdate") else today()
        tok = (q1("SELECT MAX(token_no) m FROM visits WHERE vdate=? AND module=?", (vdate, module))["m"] or 0) + 1
        c = ex("INSERT INTO visits(token_no,vdate,module,patient_id,pid,name,age_y,age_m,address,phone,referred_by,doctor_id,"
               "doctor_name,tests,fee,discount,total,created_by,created_at,op_type,room,other,advance,notes,detail) VALUES(%s)" % ",".join("?" * 25),
               (tok, vdate, module, pid_n, pid, name, ay, am, vals[3], vals[4], f.get("referred_by", "").strip(),
                doc["id"] if doc else None, doc["name"] if doc else "", tnames, fee, disc, total, session["user"],
                datetime.now().strftime("%Y-%m-%d %H:%M"), op_type, room, other, adv, f.get("notes", "").strip(), detail))
        act = f.get("action")
        if act == "token": return redirect(url_for("token", vid=c.lastrowid, print=1))
        if act in ("both", "print"): return redirect(url_for("memo", vid=c.lastrowid, print=1, token=1))
        flash("Saved. Token #%d" % tok, "ok"); return redirect(request.path)
    pre = q1("SELECT * FROM patients WHERE pid=?", (request.args.get("pid", ""),))
    return render_template("entry.html", module=module, label=MODULES[module], doctors=doctors, tests=tests, ops=ops, pre=dict(pre) if pre else None)

@app.route("/api/patient/<pid>")
def api_patient(pid):
    p = q1("SELECT * FROM patients WHERE pid=?", (pid.strip(),))
    return jsonify(dict(p) if p else {})

@app.route("/token/<int:vid>")
def token(vid):
    v = q1("SELECT * FROM visits WHERE id=?", (vid,)) or abort(404)
    vn = q1("SELECT COUNT(*) n FROM visits WHERE patient_id=? AND id<=?", (v["patient_id"], v["id"]))["n"]
    return render_template("token.html", v=v, label=MODULES[v["module"]], vn=vn)

def filt(a):
    w, p = ["1=1"], []
    if session["role"] != "admin": w.append("vdate=?"); p.append(today())
    else:
        if a.get("from"): w.append("vdate>=?"); p.append(a["from"])
        if a.get("to"): w.append("vdate<=?"); p.append(a["to"])
    for k, col in (("module", "module"), ("doctor", "doctor_name"), ("patient", "patient_id")):
        if a.get(k): w.append(col + "=?"); p.append(a[k])
    if a.get("q"): w.append("(name LIKE ? OR pid LIKE ? OR phone LIKE ?)"); p += ["%" + a["q"] + "%"] * 3
    return " AND ".join(w), p

@app.route("/history")
def history():
    w, p = filt(request.args)
    vs = qa("SELECT * FROM visits WHERE %s ORDER BY vdate DESC, id DESC LIMIT 1000" % w, p)
    tot = q1("SELECT COUNT(*) n, COALESCE(SUM(fee),0) fee, COALESCE(SUM(discount),0) disc, COALESCE(SUM(total),0) net "
             "FROM visits WHERE %s" % w, p)
    doctors = qa("SELECT name FROM doctors ORDER BY name")
    return render_template("history.html", vs=vs, tot=tot, a=request.args, doctors=doctors)

@app.route("/visit/<int:vid>/delete", methods=["POST"])
@admin
def del_visit(vid):
    ex("DELETE FROM visits WHERE id=?", (vid,)); flash("Record deleted", "ok")
    return redirect(request.referrer or url_for("history"))

@app.route("/patients")
def patients():
    s = "%" + request.args.get("q", "") + "%"
    ps = qa("SELECT p.*, COUNT(v.id) visits, COALESCE(SUM(v.total),0) paid FROM patients p LEFT JOIN visits v "
            "ON v.patient_id=p.id WHERE p.name LIKE ? OR p.pid LIKE ? OR p.phone LIKE ? GROUP BY p.id ORDER BY p.id DESC LIMIT 500", (s, s, s))
    return render_template("patients.html", ps=ps)

@app.route("/reports")
@admin
def reports():
    a = request.args; fr, to = a.get("from") or today(), a.get("to") or today(); batch = int(clean_num(a.get("batch")) or 20)
    rng = (fr, to)
    docs = qa("SELECT doctor_name, COUNT(*) n, SUM(module='ot') ops, SUM(fee) fee, SUM(discount) disc, SUM(total) net FROM visits "
              "WHERE vdate BETWEEN ? AND ? AND doctor_name!='' GROUP BY doctor_name ORDER BY n DESC", rng)
    mods = qa("SELECT module, COUNT(*) n, SUM(fee) fee, SUM(discount) disc, SUM(total) net FROM visits "
              "WHERE vdate BETWEEN ? AND ? GROUP BY module", rng)
    tot = q1("SELECT COUNT(*) n, COALESCE(SUM(total),0) net FROM visits WHERE vdate BETWEEN ? AND ?", rng)
    opsr = qa("SELECT op_type, COUNT(*) n, SUM(total) net FROM visits WHERE module='ot' AND vdate BETWEEN ? AND ? GROUP BY op_type ORDER BY n DESC", rng)
    stt = q1("SELECT COUNT(*) n, COALESCE(SUM(total),0) t, COALESCE(SUM(profit),0) p FROM sales WHERE sdate BETWEEN ? AND ?", rng)
    return render_template("reports.html", docs=docs, mods=mods, tot=tot, fr=fr, to=to, batch=batch, opsr=opsr, stt=stt)

@app.route("/settings", methods=["GET", "POST"])
@admin
def settings():
    if request.method == "POST":
        f, a = request.form, request.form.get("action")
        try:
            if a == "add_doctor": ex("INSERT INTO doctors(name,fee) VALUES(?,?)", (f["name"].strip(), clean_num(f["fee"])))
            elif a == "upd_doctor": ex("UPDATE doctors SET fee=? WHERE id=?", (clean_num(f["fee"]), f["id"]))
            elif a == "del_doctor": ex("DELETE FROM doctors WHERE id=?", (f["id"],))
            elif a == "add_test": ex("INSERT INTO tests(name,price) VALUES(?,?)", (f["name"].strip(), clean_num(f["price"])))
            elif a == "del_test": ex("DELETE FROM tests WHERE id=?", (f["id"],))
            elif a == "set_printer": set_setting("thermal_printer", f.get("printer", "").strip())
            elif a == "test_printer":
                ok, msg = thermal_print(b"\x1b@\x1ba\x01\x1bE\x01Shifa Medical Centre\n\x1bE\x00Test print OK\n\n\n\x1dV\x42\x00")
                flash("Test print bhej diya gaya" if ok else "Print nahi hua: " + msg, "ok" if ok else "err")
            elif a == "add_op": ex("INSERT INTO operations(name,category,price) VALUES(?,?,?)", (f["name"].strip(), f["category"], clean_num(f["price"])))
            elif a == "upd_op": ex("UPDATE operations SET price=? WHERE id=?", (clean_num(f["price"]), f["id"]))
            elif a == "del_op": ex("DELETE FROM operations WHERE id=?", (f["id"],))
            elif a == "add_user":
                ex("INSERT INTO users(username,password,role) VALUES(?,?,?)", (f["username"].strip(), generate_password_hash(f["password"]), f["role"]))
            elif a == "del_user":
                if q1("SELECT username FROM users WHERE id=?", (f["id"],))["username"] != session["user"]: ex("DELETE FROM users WHERE id=?", (f["id"],))
                else: flash("You cannot delete yourself", "err")
            if a != "test_printer": flash("Done", "ok")
        except sqlite3.IntegrityError: flash("That already exists", "err")
        return redirect(url_for("settings"))
    return render_template("settings.html", doctors=qa("SELECT * FROM doctors ORDER BY name"),
                           tests=qa("SELECT * FROM tests ORDER BY name"), ops=qa("SELECT * FROM operations ORDER BY category,name"), users=qa("SELECT * FROM users"), printers=list_printers(), cur=get_setting("thermal_printer"))

def int_q(v):
    try: return max(int(float(v or 0)), 0)
    except ValueError: return 0
def digits(s): return "".join(ch for ch in s if ch.isdigit())
PH = "REPLACE(REPLACE(REPLACE(phone,'-',''),' ',''),'+','')"

@app.route("/returning")
def returning():
    q, res = request.args.get("q", "").strip(), []
    if q:
        d = digits(q)[-10:]
        w, p = ["name LIKE ?", "pid LIKE ?"], ["%" + q + "%"] * 2
        if len(d) >= 4: w.append(PH + " LIKE ?"); p.append("%" + d + "%")
        for pt in qa("SELECT * FROM patients WHERE " + " OR ".join(w) + " ORDER BY id DESC LIMIT 20", p):
            vs = qa("SELECT * FROM visits WHERE patient_id=? ORDER BY id DESC", (pt["id"],))
            res.append(dict(p=pt, vs=vs, paid=sum(v["total"] for v in vs)))
    return render_template("returning.html", q=q, res=res)

@app.route("/api/phone/<ph>")
def api_phone(ph):
    d = digits(ph)[-10:]
    if len(d) < 6: return jsonify([])
    rows = qa("SELECT p.*, (SELECT COUNT(*) FROM visits v WHERE v.patient_id=p.id) visits, (SELECT MAX(vdate) FROM visits v WHERE v.patient_id=p.id) last "
              "FROM patients p WHERE " + PH.replace("phone", "p.phone") + " LIKE ? LIMIT 6", ("%" + d + "%",))
    return jsonify([dict(r) for r in rows])

@app.route("/store/sale", methods=["GET", "POST"])
def store_sale():
    if request.method == "POST":
        f, want = request.form, {}
        for i, qv in zip(f.getlist("med_id"), f.getlist("qty")):
            if i.isdigit() and int_q(qv) > 0: want[int(i)] = want.get(int(i), 0) + int_q(qv)
        if not want: flash("Select at least one medicine", "err"); return redirect(request.url)
        items, sub, cost = [], 0, 0
        for mid, qty in want.items():
            m = q1("SELECT * FROM medicines WHERE id=?", (mid,))
            if not m: continue
            if m["expiry"] and m["expiry"] < today(): flash("%s is expired" % m["name"], "err"); return redirect(request.url)
            if qty > m["stock"]: flash("Not enough stock for %s (available %d)" % (m["name"], m["stock"]), "err"); return redirect(request.url)
            items.append((m, qty)); sub += m["sell_price"] * qty; cost += m["buy_price"] * qty
        disc = min(clean_num(f.get("discount")), sub); total = sub - disc
        bill_no = (q1("SELECT MAX(bill_no) m FROM sales WHERE sdate=?", (today(),))["m"] or 0) + 1
        c = ex("INSERT INTO sales(bill_no,sdate,customer,phone,subtotal,discount,total,profit,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
               (bill_no, today(), f.get("customer", "").strip(), f.get("phone", "").strip(), sub, disc, total, total - cost,
                session["user"], datetime.now().strftime("%Y-%m-%d %H:%M")))
        for m, qty in items:
            db().execute("INSERT INTO sale_items(sale_id,med_id,name,qty,price,cost) VALUES(?,?,?,?,?,?)", (c.lastrowid, m["id"], m["name"], qty, m["sell_price"], m["buy_price"]))
            db().execute("UPDATE medicines SET stock=stock-? WHERE id=?", (qty, m["id"]))
        db().commit()
        if f.get("action") == "print": return redirect(url_for("bill", sid=c.lastrowid, print=1))
        flash("Sale saved. Bill #%d" % bill_no, "ok"); return redirect(request.path)
    meds = [dict(m) for m in qa("SELECT id,name,company,stock,sell_price FROM medicines WHERE stock>0 AND (expiry='' OR expiry>=?) ORDER BY name", (today(),))]
    pre = q1("SELECT * FROM patients WHERE pid=?", (request.args.get("pid", ""),))
    return render_template("store_sale.html", meds=meds, pre=dict(pre) if pre else None)

@app.route("/store/bill/<int:sid>")
def bill(sid):
    s = q1("SELECT * FROM sales WHERE id=?", (sid,)) or abort(404)
    return render_template("bill.html", s=s, items=qa("SELECT * FROM sale_items WHERE sale_id=?", (sid,)))

@app.route("/store/medicines", methods=["GET", "POST"])
def medicines():
    if request.method == "POST":
        if session["role"] != "admin": abort(403)
        f, a = request.form, request.form.get("action")
        if a == "add":
            ex("INSERT INTO medicines(name,company,stock,buy_price,sell_price,expiry,min_stock) VALUES(?,?,?,?,?,?,?)",
               (f["name"].strip(), f.get("company", "").strip(), int_q(f.get("stock")), clean_num(f.get("buy_price")), clean_num(f.get("sell_price")), f.get("expiry", ""), int_q(f.get("min_stock") or 10)))
        elif a == "update":
            ex("UPDATE medicines SET buy_price=?,sell_price=?,expiry=?,min_stock=? WHERE id=?", (clean_num(f["buy_price"]), clean_num(f["sell_price"]), f.get("expiry", ""), int_q(f.get("min_stock")), f["id"]))
        elif a == "add_stock": ex("UPDATE medicines SET stock=stock+? WHERE id=?", (int_q(f["qty"]), f["id"]))
        elif a == "del": ex("DELETE FROM medicines WHERE id=?", (f["id"],))
        flash("Done", "ok"); return redirect(url_for("medicines"))
    s = "%" + request.args.get("q", "") + "%"
    ms = qa("SELECT * FROM medicines WHERE name LIKE ? OR company LIKE ? ORDER BY name", (s, s))
    return render_template("medicines.html", ms=ms, soon=(date.today() + timedelta(days=60)).isoformat())

@app.route("/store/sales")
def store_sales():
    a, w, p = request.args, ["1=1"], []
    if session["role"] != "admin": w.append("sdate=?"); p.append(today())
    else:
        if a.get("from"): w.append("sdate>=?"); p.append(a["from"])
        if a.get("to"): w.append("sdate<=?"); p.append(a["to"])
    if a.get("q"): w.append("(customer LIKE ? OR phone LIKE ?)"); p += ["%" + a["q"] + "%"] * 2
    W = " AND ".join(w)
    rows = qa("SELECT s.*, (SELECT GROUP_CONCAT(name || ' x' || CAST(qty AS INTEGER), ', ') FROM sale_items WHERE sale_id=s.id) items FROM sales s WHERE " + W + " ORDER BY id DESC LIMIT 1000", p)
    tot = q1("SELECT COUNT(*) n, COALESCE(SUM(total),0) t, COALESCE(SUM(discount),0) d, COALESCE(SUM(profit),0) pr FROM sales WHERE " + W, p)
    return render_template("store_sales.html", rows=rows, tot=tot, a=a)

@app.route("/store/sale/<int:sid>/delete", methods=["POST"])
@admin
def del_sale(sid):
    for it in qa("SELECT * FROM sale_items WHERE sale_id=?", (sid,)):
        db().execute("UPDATE medicines SET stock=stock+? WHERE id=?", (it["qty"], it["med_id"]))
    db().execute("DELETE FROM sale_items WHERE sale_id=?", (sid,)); db().execute("DELETE FROM sales WHERE id=?", (sid,)); db().commit()
    flash("Bill deleted and stock restored", "ok"); return redirect(request.referrer or url_for("store_sales"))

def get_setting(k, d=""):
    r = q1("SELECT value FROM settings WHERE key=?", (k,)); return r["value"] if r else d
def set_setting(k, v):
    ex("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))

def list_printers():
    try:
        import win32print
        return sorted({p[2] for p in win32print.EnumPrinters(2 | 4)})
    except Exception: return []

def thermal_print(data):
    name = get_setting("thermal_printer")
    if not name: return False, "Settings me thermal printer select karein"
    try: import win32print
    except ImportError: return False, "pywin32 install nahi hai (SETUP.bat dobara chalayein)"
    try:
        h = win32print.OpenPrinter(name)
        try:
            win32print.StartDocPrinter(h, 1, ("Token", None, "RAW")); win32print.StartPagePrinter(h)
            win32print.WritePrinter(h, data); win32print.EndPagePrinter(h); win32print.EndDocPrinter(h)
        finally: win32print.ClosePrinter(h)
        return True, "OK"
    except Exception as e: return False, str(e)

TW = 42
def _t(s): return (s + "\n").encode("cp437", "replace")
def token_bytes(v, label, vn=1):
    import textwrap
    b = b"\x1b@\x1ba\x01\x1bE\x01\x1d!\x11" + _t("SHIFA MEDICAL CENTRE") + b"\x1d!\x00\x1bE\x00"
    b += _t("Civil Hospital Road, Khairpur Mirs") + _t("Ph: 0300-2989753") + _t("-" * TW)
    b += b"\x1bE\x01" + _t(label.upper()) + b"\x1d!\x11" + _t("TOKEN # %d" % v["token_no"]) + b"\x1d!\x00\x1bE\x00" + _t("-" * TW) + b"\x1ba\x00"
    rows = [("Date", "%s  %s" % (v["vdate"], (v["created_at"] or "")[11:])), ("Patient ID", v["pid"]), ("Name", v["name"]), ("Age", "%sy %sm" % (v["age_y"], v["age_m"]))]
    if vn > 1: rows.append(("Visit", "Follow-up #%d" % vn))
    if v["doctor_name"]: rows.append(("Doctor", v["doctor_name"]))
    if v["op_type"]: rows.append(("Operation", v["op_type"]))
    if v["tests"]: rows.append(("Tests", v["tests"]))
    for k, val in rows:
        for i, ln in enumerate(textwrap.wrap(str(val), TW - 12) or [""]):
            b += _t(((k + ":") if i == 0 else "").ljust(12) + ln)
    return b + _t("-" * TW) + b"\x1ba\x01" + _t("Allah shifa de") + b"\n\n\n\x1dV\x42\x00"

@app.route("/token/<int:vid>/thermal", methods=["POST"])
def token_thermal(vid):
    v = q1("SELECT * FROM visits WHERE id=?", (vid,)) or abort(404)
    vn = q1("SELECT COUNT(*) n FROM visits WHERE patient_id=? AND id<=?", (v["patient_id"], v["id"]))["n"]
    ok, msg = thermal_print(token_bytes(v, MODULES[v["module"]], vn))
    return jsonify(ok=ok, msg=msg)

def memo_lines(v):
    m, L = v["module"], []
    if m == "opd": L.append(("Consultation fee - " + (v["doctor_name"] or ""), v["fee"]))
    elif m == "lab":
        try: d = json.loads(v["detail"] or "[]")
        except ValueError: d = []
        L += [("Lab test: " + n, p) for n, p in d] if d else [("Laboratory: " + (v["tests"] or ""), v["fee"])]
    elif m == "ot":
        L.append(("%s - operation charges" % v["op_type"], v["fee"]))
        if v["room"]: L.append(("Room / ward charges", v["room"]))
        if v["other"]: L.append(("Medicines / other charges", v["other"]))
    else: L.append((MODULES[m] + " charges" + ((" - " + v["doctor_name"]) if v["doctor_name"] else ""), v["fee"]))
    return L

@app.route("/memo/<int:vid>")
def memo(vid):
    v = q1("SELECT * FROM visits WHERE id=?", (vid,)) or abort(404)
    return render_template("memo.html", v=v, label=MODULES[v["module"]], lines=memo_lines(v), gross=v["fee"] + (v["room"] or 0) + (v["other"] or 0))

@app.route("/doctor-sheet")
def doctor_sheet():
    a, doc = request.args, request.args.get("doctor", "")
    if session["role"] == "admin": fr, to = a.get("from") or today(), a.get("to") or today()
    else: fr = to = today()
    rows = qa("SELECT * FROM visits WHERE doctor_name=? AND vdate BETWEEN ? AND ? ORDER BY vdate, module, token_no", (doc, fr, to)) if doc else []
    tot = dict(n=len(rows), net=sum(r["total"] for r in rows), disc=sum(r["discount"] for r in rows))
    return render_template("doctor_sheet.html", doctors=qa("SELECT name FROM doctors ORDER BY name"), doc=doc, rows=rows, tot=tot, fr=fr, to=to)

@app.route("/patient/<int:pid>/record")
def patient_record(pid):
    p = q1("SELECT * FROM patients WHERE id=?", (pid,)) or abort(404)
    vs = qa("SELECT * FROM visits WHERE patient_id=? ORDER BY vdate, id", (pid,))
    return render_template("record.html", p=p, vs=vs, net=sum(v["total"] for v in vs))

@app.route("/about")
def about(): return render_template("about.html")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
