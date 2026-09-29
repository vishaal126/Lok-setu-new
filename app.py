import os
import sqlite3
import datetime as dt

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Lok Setu", page_icon="🏛️", layout="wide")

DB = "lok_setu.db"
CATS = ["Roads & Potholes", "Water Supply", "Electricity", "Garbage & Sanitation",
        "Street Lights", "Drainage", "Public Safety", "Other"]
STATUSES = ["Pending", "In Progress", "Resolved", "Rejected"]
COLORS = {"Pending": "#B7791F", "In Progress": "#0B3FA8", "Resolved": "#2F855A", "Rejected": "#9B2C2C"}


def admin_password():
    try:
        return st.secrets["ADMIN_PASSWORD"]
    except Exception:
        return os.getenv("ADMIN_PASSWORD", "admin123")


# ---------------------------------------------------------------- backend
def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS reports(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, category TEXT, description TEXT, location TEXT,
            name TEXT, contact TEXT, image BLOB,
            status TEXT DEFAULT 'Pending', created_at TEXT, updated_at TEXT);
        CREATE TABLE IF NOT EXISTS updates(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER, status TEXT, note TEXT, at TEXT);
        """)


def now():
    return dt.datetime.now().strftime("%d %b %Y, %H:%M")


def tid(i):
    return f"LS-{int(i):05d}"


def add_report(title, cat, desc, loc, name, contact, image):
    with conn() as c:
        cur = c.execute(
            "INSERT INTO reports(title,category,description,location,name,contact,image,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (title, cat, desc, loc, name, contact, image, now(), now()))
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


def get_reports(status=None, cat=None, q=None):
    sql, args = "SELECT * FROM reports WHERE 1=1", []
    if status and status != "All":
        sql += " AND status=?"; args.append(status)
    if cat and cat != "All":
        sql += " AND category=?"; args.append(cat)
    if q:
        sql += " AND (title LIKE ? OR location LIKE ? OR description LIKE ?)"
        args += [f"%{q}%"] * 3
    sql += " ORDER BY id DESC"
    with conn() as c:
        return c.execute(sql, args).fetchall()


def get_one(rid):
    with conn() as c:
        return c.execute("SELECT * FROM reports WHERE id=?", (rid,)).fetchone()


def timeline(rid):
    with conn() as c:
        return c.execute("SELECT * FROM updates WHERE report_id=? ORDER BY id", (rid,)).fetchall()


def counts():
    r = get_reports()
    n = lambda s: sum(1 for x in r if x["status"] == s)
    return len(r), n("Pending") + n("In Progress"), n("Resolved")


# --------------------------------------------------------------- styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:wght@600;700&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
h1,h2,h3,.serif { font-family:'Fraunces',serif !important; color:#14213D; }
.stApp { background:#F1F4F9; }
.hero { background:linear-gradient(135deg,#0B3FA8,#082B75); color:#fff; padding:28px; border-radius:18px; }
.hero h2 { color:#fff !important; margin:6px 0 0 0; font-size:1.7rem; }
.hero small { opacity:.8; }
.stat { background:#fff; border-radius:14px; padding:16px; text-align:center; border:1px solid #E2E8F0; }
.stat b { font-family:'Fraunces',serif; font-size:2rem; display:block; }
.card { background:#fff; border:1px solid #E2E8F0; border-radius:14px; padding:14px 16px; margin-bottom:10px; }
.badge { display:inline-block; padding:2px 10px; border-radius:99px; color:#fff; font-size:.75rem; font-weight:600; }
.muted { color:#64748B; font-size:.85rem; }
.stButton>button, .stFormSubmitButton>button { background:#D69E2E; color:#fff; border:0; border-radius:99px; font-weight:600; }
.stButton>button:hover, .stFormSubmitButton>button:hover { background:#B7791F; color:#fff; }
</style>
""", unsafe_allow_html=True)


def badge(s):
    return f'<span class="badge" style="background:{COLORS.get(s, "#555")}">{s}</span>'


def report_card(r, show_private=False):
    extra = f"<br><span class='muted'>By {r['name'] or 'Anonymous'} · {r['contact'] or '-'}</span>" if show_private else ""
    st.markdown(
        f"<div class='card'><b>{tid(r['id'])} · {r['title']}</b> &nbsp;{badge(r['status'])}<br>"
        f"<span class='muted'>{r['category']} · {r['location']} · {r['created_at']}</span>{extra}</div>",
        unsafe_allow_html=True)


def show_timeline(rid):
    for u in timeline(rid):
        st.markdown(f"{badge(u['status'])} &nbsp;**{u['at']}** — {u['note']}", unsafe_allow_html=True)


# ----------------------------------------------------------------- pages
def go(page):
    st.session_state.page = page


def page_dashboard():
    total, pending, resolved = counts()
    left, right = st.columns([1, 2], gap="large")
    with left:
        st.markdown("<div class='hero'><small>LOK SETU</small><h2>Let's fix the city together</h2></div>",
                    unsafe_allow_html=True)
        st.button("Report an issue", on_click=go, args=("Report an Issue",), use_container_width=True)
    with right:
        st.markdown("### Hello, Guest User")
        a, b, c = st.columns(3)
        a.markdown(f"<div class='stat'><b>{total}</b>Total reports</div>", unsafe_allow_html=True)
        b.markdown(f"<div class='stat'><b style='color:#B7791F'>{pending}</b>Open</div>", unsafe_allow_html=True)
        c.markdown(f"<div class='stat'><b style='color:#2F855A'>{resolved}</b>Resolved</div>", unsafe_allow_html=True)
    st.markdown("### Recent issues")
    rows = get_reports()[:5]
    if not rows:
        st.info("No reports yet. Use “Report an issue” to file the first one.")
    for r in rows:
        report_card(r)


def page_report():
    st.markdown("## Report an issue")
    with st.form("report", clear_on_submit=True):
        title = st.text_input("Issue title *")
        cat = st.selectbox("Category", CATS)
        loc = st.text_input("Location / landmark *")
        desc = st.text_area("What is the problem? *", height=120)
        img = st.file_uploader("Photo (optional)", type=["jpg", "jpeg", "png"])
        c1, c2 = st.columns(2)
        name = c1.text_input("Your name (optional)")
        contact = c2.text_input("Phone or email (optional)")
        ok = st.form_submit_button("Submit report")
    if ok:
        if not (title.strip() and loc.strip() and desc.strip()):
            st.error("Fill in the title, location and description.")
        else:
            rid = add_report(title.strip(), cat, desc.strip(), loc.strip(), name.strip(),
                             contact.strip(), img.getvalue() if img else None)
            st.success(f"Report submitted. Your tracking ID is **{tid(rid)}**. Save it to check progress.")


def page_track():
    st.markdown("## Track a complaint")
    code = st.text_input("Tracking ID (e.g. LS-00001)")
    if code:
        try:
            r = get_one(int(code.upper().replace("LS-", "")))
        except ValueError:
            r = None
        if not r:
            st.error("No complaint found with that ID. Check it and try again.")
        else:
            report_card(r)
            st.write(r["description"])
            if r["image"]:
                st.image(r["image"], width=320)
            st.markdown("#### Progress")
            show_timeline(r["id"])


def page_public():
    st.markdown("## Public reports")
    c1, c2, c3 = st.columns(3)
    s = c1.selectbox("Status", ["All"] + STATUSES)
    cat = c2.selectbox("Category", ["All"] + CATS)
    q = c3.text_input("Search")
    rows = get_reports(s, cat, q)
    st.caption(f"{len(rows)} report(s)")
    for r in rows:
        report_card(r)


def page_admin():
    st.markdown("## Admin panel")
    if not st.session_state.get("is_admin"):
        with st.form("login"):
            pw = st.text_input("Admin password", type="password")
            if st.form_submit_button("Log in"):
                if pw == admin_password():
                    st.session_state.is_admin = True
                    st.rerun()
                else:
                    st.error("Wrong password.")
        return
    if st.button("Log out"):
        st.session_state.is_admin = False
        st.rerun()

    total, pending, resolved = counts()
    a, b, c = st.columns(3)
    a.metric("Total", total); b.metric("Open", pending); c.metric("Resolved", resolved)

    f1, f2, f3 = st.columns(3)
    s = f1.selectbox("Status", ["All"] + STATUSES, key="a_s")
    cat = f2.selectbox("Category", ["All"] + CATS, key="a_c")
    q = f3.text_input("Search", key="a_q")
    rows = get_reports(s, cat, q)
    if not rows:
        st.info("No reports match these filters.")
        return

    df = pd.DataFrame([{k: r[k] for k in r.keys() if k != "image"} for r in rows])
    df["id"] = df["id"].map(tid)
    st.dataframe(df[["id", "title", "category", "location", "status", "created_at", "name", "contact"]],
                 use_container_width=True, hide_index=True)
    st.download_button("Download CSV", df.to_csv(index=False), "reports.csv", "text/csv")

    st.markdown("### Update a complaint")
    pick = st.selectbox("Choose report", [r["id"] for r in rows],
                        format_func=lambda i: f"{tid(i)} · {get_one(i)['title']}")
    r = get_one(pick)
    report_card(r, show_private=True)
    st.write(r["description"])
    if r["image"]:
        st.image(r["image"], width=320)
    with st.form("upd"):
        ns = st.selectbox("New status", STATUSES, index=STATUSES.index(r["status"]))
        note = st.text_area("Progress note (visible to the citizen)")
        if st.form_submit_button("Save update"):
            set_status(pick, ns, note)
            st.success("Complaint updated.")
            st.rerun()
    st.markdown("#### History")
    show_timeline(pick)
    if st.button("Delete this report"):
        delete_report(pick)
        st.rerun()


# ---------------------------------------------------------------- router
init_db()
PAGES = {"Dashboard": page_dashboard, "Report an Issue": page_report, "Track Complaint": page_track,
         "Public Reports": page_public, "Admin": page_admin}
st.session_state.setdefault("page", "Dashboard")

with st.sidebar:
    st.markdown("<h2 class='serif'>🏛️ Lok Setu</h2>", unsafe_allow_html=True)
    st.radio("Go to", list(PAGES), key="page")
PAGES[st.session_state.page]()
