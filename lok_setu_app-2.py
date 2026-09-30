import os, sqlite3, hashlib, hmac, datetime as dt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Lok Setu", page_icon="🏛️", layout="wide")

DB = "lok_setu.db"
CATS = {"Roads & Potholes": "🛣️", "Water Supply": "💧", "Electricity": "⚡", "Garbage & Sanitation": "🗑️",
        "Street Lights": "💡", "Drainage": "🌊", "Public Safety": "🚨", "Other": "📌"}
STATUSES = ["Pending", "In Progress", "Solved"]
COLORS = {"Pending": "#F59E0B", "In Progress": "#3B82F6", "Solved": "#10B981"}


def admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return os.getenv("ADMIN_PASSWORD", "admin123")


# ------------------------------------------------------------ backend
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, description TEXT,
            location TEXT, name TEXT, contact TEXT, image BLOB, status TEXT DEFAULT 'Pending',
            created_at TEXT, updated_at TEXT, owner TEXT);
        CREATE TABLE IF NOT EXISTS updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT, report_id INTEGER, status TEXT, note TEXT, at TEXT);
        CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY, name TEXT, salt TEXT, pw TEXT);
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(reports)")]
        if "owner" not in cols:
            c.execute("ALTER TABLE reports ADD COLUMN owner TEXT")
        c.execute("UPDATE reports SET status='Solved' WHERE status='Resolved'")
        c.execute("UPDATE updates SET status='Solved' WHERE status='Resolved'")
        c.execute("UPDATE reports SET status='Pending' WHERE status='Rejected'")


def now():
    return dt.datetime.now().strftime("%d %b %Y, %H:%M")


def tid(i):
    return f"LS-{int(i):05d}"


def hp(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 100000).hex()


def register(u, name, pw):
    salt = os.urandom(8).hex()
    try:
        with conn() as c:
            c.execute("INSERT INTO users VALUES(?,?,?,?)", (u.strip().lower(), name.strip(), salt, hp(pw, salt)))
        return True
    except sqlite3.IntegrityError:
        return False


def check(u, pw):
    with conn() as c:
        r = c.execute("SELECT * FROM users WHERE username=?", (u.strip().lower(),)).fetchone()
    if r and hmac.compare_digest(r["pw"], hp(pw, r["salt"])):
        return r["name"] or r["username"]
    return None


def add_report(title, cat, desc, loc, name, contact, image, owner):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO reports(title,category,description,location,name,contact,image,created_at,updated_at,owner)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (title, cat, desc, loc, name, contact, image, now(), now(), owner))
        rid = cur.lastrowid
        c.execute("INSERT INTO updates(report_id,status,note,at) VALUES(?,?,?,?)",
                  (rid, "Pending", "Complaint received.", now()))
    return rid


def set_status(rid, status, note):
    with conn() as c:
        c.execute("UPDATE reports SET status=?, updated_at=? WHERE id=?", (status, now(), rid))
        c.execute("INSERT INTO updates(report_id,status,note,at) VALUES(?,?,?,?)",
                  (rid, status, note or "Status updated.", now()))


def delete_report(rid):
    with conn() as c:
        c.execute("DELETE FROM reports WHERE id=?", (rid,))
        c.execute("DELETE FROM updates WHERE report_id=?", (rid,))


def get_reports(status=None, cat=None, q=None, owner=None):
    sql, args = "SELECT * FROM reports WHERE 1=1", []
    if status and status != "All":
        sql += " AND status=?"; args.append(status)
    if cat and cat != "All":
        sql += " AND category=?"; args.append(cat)
    if owner:
        sql += " AND owner=?"; args.append(owner)
    if q:
        sql += " AND (title LIKE ? OR location LIKE ? OR description LIKE ?)"
        args += [f"%{q}%"] * 3
    with conn() as c:
        return c.execute(sql + " ORDER BY id DESC", args).fetchall()


def get_one(rid):
    with conn() as c:
        return c.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()


def timeline(rid):
    with conn() as c:
        return c.execute("SELECT * FROM updates WHERE report_id=? ORDER BY id", (rid,)).fetchall()


def counts(owner=None):
    r = get_reports(owner=owner)
    n = lambda s: sum(1 for x in r if x["status"] == s)
    return len(r), n("In Progress"), n("Solved")


# ------------------------------------------------------------ styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
h1,h2,h3 { font-family:'Fraunces',serif !important; color:#312E81; }
.stApp { background:linear-gradient(160deg,#EEF2FF 0%,#FDF2F8 50%,#ECFEFF 100%); }
.stApp p, .stApp label, .stApp li, .stApp span, .stCaption { color:#1F2937; }
[data-testid="stSidebar"] { background:linear-gradient(180deg,#312E81,#6D28D9); }
[data-testid="stSidebar"] * { color:#fff !important; }
.hero { background:linear-gradient(135deg,#4F46E5,#9333EA,#EC4899); padding:26px; border-radius:20px;
        box-shadow:0 10px 30px rgba(147,51,234,.25); margin-bottom:12px; }
.hero, .hero * { color:#fff !important; }
.hero h2 { margin:6px 0 0 0; font-size:1.6rem; line-height:1.3; }
.stats { display:flex; gap:10px; margin:12px 0; }
.stat { flex:1; border-radius:16px; padding:14px 6px; text-align:center; font-weight:600; font-size:.85rem; }
.stat, .stat * { color:#fff !important; }
.stat b { display:block; font-family:'Fraunces',serif; font-size:2rem; }
.s1 { background:linear-gradient(135deg,#6366F1,#8B5CF6); }
.s2 { background:linear-gradient(135deg,#F59E0B,#F97316); }
.s3 { background:linear-gradient(135deg,#10B981,#14B8A6); }
.card { background:#fff; border-radius:14px; padding:14px 16px; margin-bottom:10px; color:#1F2937;
        box-shadow:0 4px 14px rgba(49,46,129,.08); }
.badge { display:inline-block; padding:2px 10px; border-radius:99px; color:#fff !important; font-size:.75rem; font-weight:600; }
.muted { color:#6B7280 !important; font-size:.85rem; }
.stButton>button, .stFormSubmitButton>button { background:linear-gradient(90deg,#F97316,#EC4899); color:#fff;
        border:0; border-radius:99px; font-weight:600; padding:.5rem 1.2rem; }
.stButton>button:hover, .stFormSubmitButton>button:hover { filter:brightness(1.1); color:#fff; }
.done { background:#fff; border-radius:20px; padding:24px 16px; text-align:center; position:relative; overflow:hidden;
        box-shadow:0 8px 24px rgba(16,185,129,.25); animation:pop .5s ease; margin:10px 0; color:#1F2937; }
.tick { width:72px; height:72px; border-radius:50%; background:linear-gradient(135deg,#10B981,#14B8A6);
        color:#fff !important; font-size:42px; line-height:72px; margin:0 auto 10px; animation:pulse 1.4s ease-out 3; }
.conf { position:absolute; top:-30px; font-size:22px; animation:fall 2.4s linear infinite; }
.overlay { position:fixed; inset:0; display:flex; align-items:center; justify-content:center; z-index:99999;
           background:rgba(49,46,129,.35); pointer-events:none; animation:fadeout .6s ease 5s forwards; }
.overlay .done { width:min(340px,86vw); }
@keyframes fadeout { to { opacity:0; visibility:hidden; } }
@keyframes pop { 0% { transform:scale(.6); opacity:0; } 100% { transform:scale(1); opacity:1; } }
@keyframes pulse { 0% { box-shadow:0 0 0 0 rgba(16,185,129,.6); } 100% { box-shadow:0 0 0 26px rgba(16,185,129,0); } }
@keyframes fall { to { transform:translateY(260px) rotate(360deg); opacity:0; } }
</style>
""", unsafe_allow_html=True)


def badge(s):
    return f'<span class="badge" style="background:{COLORS.get(s, "#555")}">{s}</span>'


def card(r, private=False):
    col = COLORS.get(r["status"], "#888")
    extra = (f"<br><span class='muted'>👤 {r['name'] or 'Anonymous'} · 📞 {r['contact'] or '-'}</span>"
             if private else "")
    st.markdown(
        f"<div class='card' style='border-left:6px solid {col}'>"
        f"<b>{CATS.get(r['category'], '📌')} {tid(r['id'])} · {r['title']}</b> &nbsp;{badge(r['status'])}<br>"
        f"<span class='muted'>{r['category']} · 📍 {r['location']} · 🕒 {r['created_at']}</span>{extra}</div>",
        unsafe_allow_html=True)


def show_timeline(rid):
    for u in timeline(rid):
        st.markdown(f"{badge(u['status'])} &nbsp;**{u['at']}** — {u['note']}", unsafe_allow_html=True)


def catname(c):
    return f"{CATS.get(c, '')} {c}" if c != "All" else "All"


def success_anim(rid):
    conf = "".join(f"<span class='conf' style='left:{l}%;animation-delay:{d}s'>{e}</span>"
                   for l, d, e in [(8, 0, "🎉"), (25, .4, "✨"), (45, .1, "🎊"), (65, .6, "⭐"), (85, .2, "🎉")])
    st.markdown(f"<div class='overlay'><div class='done'>{conf}<div class='tick'>✓</div>"
                f"<h3 style='margin:4px 0'>Report submitted!</h3>"
                f"<div>Your tracking ID is <b>{tid(rid)}</b></div>"
                f"<div class='muted'>Use “Track Complaint” to see progress.</div></div></div>", unsafe_allow_html=True)
    st.success(f"Tracking ID: {tid(rid)}")


def go(page):
    st.session_state.nav = page


def stats_html(total, openn, done):
    return (f"<div class='stats'><div class='stat s1'><b>{total}</b>Total</div>"
            f"<div class='stat s2'><b>{openn}</b>In Progress</div>"
            f"<div class='stat s3'><b>{done}</b>Solved</div></div>")


# ------------------------------------------------------------ pages
def login_page():
    st.markdown("<div class='hero'><small>LOK SETU</small>"
                "<h2>Welcome 👋<br>Report. Track. Resolve.</h2></div>", unsafe_allow_html=True)
    t1, t2 = st.tabs(["🔑 Log in", "✨ Sign up"])
    with t1:
        with st.form("li"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log in"):
                n = check(u, p)
                if n:
                    st.session_state.auth = {"user": u.strip().lower(), "name": n}
                    st.session_state.flash = f"Welcome back, {n}!"
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
    with t2:
        with st.form("su"):
            n = st.text_input("Your name")
            u = st.text_input("Choose a username")
            p = st.text_input("Password (min 4 characters)", type="password")
            p2 = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Create account"):
                if not (n.strip() and u.strip()):
                    st.error("Enter your name and a username.")
                elif len(p) < 4 or p != p2:
                    st.error("Passwords must match and be at least 4 characters.")
                elif register(u, n, p):
                    st.session_state.auth = {"user": u.strip().lower(), "name": n.strip()}
                    st.session_state.flash = f"Account created. Welcome, {n.strip()}!"
                    st.rerun()
                else:
                    st.error("That username is taken. Try another.")
    st.button("Continue as guest →", on_click=lambda: st.session_state.update(
        auth={"user": None, "name": "User"}))


def page_dashboard():
    a = st.session_state.auth
    st.markdown(f"<div class='hero'><small>LOK SETU</small>"
                f"<h2>Hello, {a['name']} 👋<br>Let's fix the city together</h2></div>", unsafe_allow_html=True)
    st.button("📝 Report an issue", on_click=go, args=("Report an Issue",), use_container_width=True)
    st.markdown(stats_html(*counts()), unsafe_allow_html=True)
    st.markdown("### 🕘 Recent issues")
    rows = get_reports()[:5]
    if not rows:
        st.info("No reports yet. Tap “Report an issue” to file the first one.")
    for r in rows:
        card(r)


def page_report():
    a = st.session_state.auth
    st.markdown("## 📝 Report an issue")
    cat = st.selectbox("Category", list(CATS), format_func=catname, key="rep_cat")
    other = ""
    if cat == "Other":
        other = st.text_input("Describe the issue type *", placeholder="e.g. Stray animals, illegal parking", key="rep_other")
    with st.form("report", clear_on_submit=True):
        title = st.text_input("Problem title *")
        loc = st.text_input("Location / landmark *")
        desc = st.text_area("What is the problem? *", height=120)
        img = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])
        c1, c2 = st.columns(2)
        name = c1.text_input("Your name", value="" if not a["user"] else a["name"])
        contact = c2.text_input("Phone or email *")
        ok = st.form_submit_button("🚀 Submit report")
    if ok:
        if not (title.strip() and loc.strip() and desc.strip() and contact.strip()) or (cat == "Other" and not other.strip()):
            st.error("Please fill in all fields marked * (including phone or email).")
        else:
            rid = add_report(title.strip(), cat, (f"Issue type: {other.strip()}\n\n" if cat == "Other" else "") + desc.strip(), loc.strip(), name.strip(), contact.strip(),
                             img.getvalue() if img else None, a["user"])
            st.toast(f"Report submitted! Your ID is {tid(rid)}", icon="✅")
            success_anim(rid)


def page_track():
    st.markdown("## 🔎 Track a complaint")
    code = st.text_input("Tracking ID (e.g. LS-00001)")
    if code:
        try:
            r = get_one(int(code.upper().replace("LS-", "")))
        except ValueError:
            r = None
        if not r:
            st.error("No complaint found with that ID.")
        else:
            card(r)
            st.write(r["description"])
            if r["image"]:
                st.image(r["image"], width=320)
            st.markdown("#### Progress")
            show_timeline(r["id"])


def page_mine():
    u = st.session_state.auth["user"]
    st.markdown("## 📂 My reports")
    st.markdown(stats_html(*counts(u)), unsafe_allow_html=True)
    rows = get_reports(owner=u)
    if not rows:
        st.info("You haven't filed any reports yet.")
    for r in rows:
        card(r)
        with st.expander("See progress"):
            show_timeline(r["id"])


def page_public():
    st.markdown("## 🌍 Public reports")
    c1, c2, c3 = st.columns(3)
    s = c1.selectbox("Status", ["All"] + STATUSES)
    cat = c2.selectbox("Category", ["All"] + list(CATS), format_func=catname)
    q = c3.text_input("Search")
    rows = get_reports(s, cat, q)
    st.caption(f"{len(rows)} report(s)")
    for r in rows:
        card(r)


def page_admin():
    st.markdown("## 🛡️ Admin panel")
    if not st.session_state.get("is_admin"):
        with st.form("alogin"):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Log in as admin"):
                if pw == admin_password():
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Wrong password.")
        return
    if st.button("Log out of admin"):
        st.session_state.is_admin = False
        st.rerun()
    st.markdown(stats_html(*counts()), unsafe_allow_html=True)
    f1, f2, f3 = st.columns(3)
    s = f1.selectbox("Status", ["All"] + STATUSES, key="a_s")
    cat = f2.selectbox("Category", ["All"] + list(CATS), key="a_c", format_func=catname)
    q = f3.text_input("Search", key="a_q")
    rows = get_reports(s, cat, q)
    if not rows:
        st.info("No reports match these filters.")
        return
    df = pd.DataFrame([{k: r[k] for k in r.keys() if k != "image"} for r in rows])
    df["id"] = df["id"].map(tid)
    st.dataframe(df[["id", "title", "category", "location", "status", "created_at", "name", "contact"]],
                 use_container_width=True, hide_index=True)
    st.download_button("⬇️ Download CSV", df.to_csv(index=False), "reports.csv", "text/csv")
    st.markdown("### ✏️ Update a complaint")
    pick = st.selectbox("Choose report", [r["id"] for r in rows],
                        format_func=lambda i: f"{tid(i)} · {get_one(i)['title']}")
    r = get_one(pick)
    card(r, private=True)
    st.write(r["description"])
    if r["image"]:
        st.image(r["image"], width=320)
    with st.form("upd"):
        ns = st.selectbox("New status", STATUSES, index=STATUSES.index(r["status"]))
        note = st.text_area("Progress note (visible to the citizen)")
        if st.form_submit_button("💾 Save update"):
            set_status(pick, ns, note)
            st.session_state.flash = f"{tid(pick)} updated to “{ns}”"
            st.rerun()
    st.markdown("#### History")
    show_timeline(pick)
    if st.button("🗑️ Delete this report"):
        delete_report(pick)
        st.session_state.flash = f"{tid(pick)} deleted"
        st.rerun()


# ------------------------------------------------------------ router
init_db()
if "flash" in st.session_state:
    st.toast(st.session_state.pop("flash"), icon="🔔")
if not st.session_state.get("auth"):
    login_page()
    st.stop()

auth = st.session_state.auth
PAGES = {"Dashboard": page_dashboard, "Report an Issue": page_report,
         "Track Complaint": page_track, "Public Reports": page_public}
if auth["user"]:
    PAGES["My Reports"] = page_mine
PAGES["Admin"] = page_admin
if st.session_state.get("nav") not in PAGES:
    st.session_state.nav = "Dashboard"


def logout():
    st.session_state.auth = None
    st.session_state.is_admin = False
    st.session_state.nav = "Dashboard"


with st.sidebar:
    st.markdown("## 🏛️ Lok Setu")
    st.markdown(f"👋 **{auth['name']}**")
    st.radio("Go to", list(PAGES), key="nav")
    st.button("Log out", on_click=logout)
PAGES[st.session_state.nav]()
