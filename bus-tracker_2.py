


import streamlit as st
import pandas as pd
from datetime import datetime
import hashlib
import base64
import sqlite3
from io import BytesIO


# ====================== DATABASE LAYER ======================

DB_NAME = "bus_income_tracker.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_database():
    conn = get_connection()
    c = conn.cursor()

    
    # Users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT ''
        )
    """)

    # Buses table
    c.execute("""
    CREATE TABLE IF NOT EXISTS buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plate_number TEXT UNIQUE NOT NULL,
        bus_name TEXT NOT NULL,
        driver TEXT DEFAULT '',
        route TEXT DEFAULT '',
        status TEXT DEFAULT 'Active',
        insurance_expiry TEXT DEFAULT '',
        service_date TEXT DEFAULT '',
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT DEFAULT ''
    )
""")

    # Daily financial records
    c.execute("""
        CREATE TABLE IF NOT EXISTS daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_plate TEXT NOT NULL,
            record_date TEXT NOT NULL,
            income INTEGER DEFAULT 0,
            expense INTEGER DEFAULT 0,
            category TEXT DEFAULT 'None',
            notes TEXT DEFAULT '',
            updated_by TEXT,
            updated_at TEXT,
            UNIQUE(bus_plate, record_date)
        )
    """)

    # Audit logs
    c.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            username TEXT,
            role TEXT,
            action TEXT NOT NULL
        )
    """)

    # App settings
    c.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT
        )
    """)

    # Default users
    c.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        "admin",
        hashlib.sha256("admin123".encode()).hexdigest(),
        "admin",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    c.execute("""
        INSERT OR IGNORE INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        "partner",
        hashlib.sha256("partner2026".encode()).hexdigest(),
        "user",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    # Default buses
    c.execute("""
        INSERT OR IGNORE INTO buses (plate_number, bus_name, status, created_at)
        VALUES (?, ?, ?, ?)
    """, ("DVQ", "Bus 1", "Active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    c.execute("""
        INSERT OR IGNORE INTO buses (plate_number, bus_name, status, created_at)
        VALUES (?, ?, ?, ?)
    """, ("DYJ", "Bus 2", "Active", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def migrate_buses_table():
    conn = get_connection()
    c = conn.cursor()

    c.execute("PRAGMA table_info(buses)")
    existing_columns = [col[1] for col in c.fetchall()]

    new_columns = {
        "driver": "TEXT DEFAULT ''",
        "route": "TEXT DEFAULT ''",
        "insurance_expiry": "TEXT DEFAULT ''",
        "service_date": "TEXT DEFAULT ''",
        "notes": "TEXT DEFAULT ''",
        "updated_at": "TEXT DEFAULT ''"
    }

    for column, definition in new_columns.items():
        if column not in existing_columns:
            c.execute(f"ALTER TABLE buses ADD COLUMN {column} {definition}")

    conn.commit()
    conn.close()


def migrate_users_table():
    conn = get_connection()
    c = conn.cursor()

    c.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in c.fetchall()]

    new_columns = {
        "is_active": "INTEGER DEFAULT 1",
        "updated_at": "TEXT DEFAULT ''"
    }

    for column, definition in new_columns.items():
        if column not in existing_columns:
            c.execute(
                f"ALTER TABLE users ADD COLUMN {column} {definition}"
            )

    conn.commit()
    conn.close()


def migrate_audit_logs_table():
    conn = get_connection()
    c = conn.cursor()

    c.execute("PRAGMA table_info(audit_logs)")
    existing_columns = [col[1] for col in c.fetchall()]

    if "username" not in existing_columns:
        c.execute("ALTER TABLE audit_logs ADD COLUMN username TEXT")

    conn.commit()
    conn.close()

# HELPER FUNCTION


def load_buses():
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            plate_number AS "Plate Number",
            bus_name AS "Bus Name",
            driver AS "Driver",
            route AS "Route",
            status AS "Status",
            insurance_expiry AS "Insurance Expiry",
            service_date AS "Service Date",
            notes AS "Notes"
        FROM buses
        ORDER BY plate_number
        """,
        conn
    )

    conn.close()
    return df


def get_active_buses_for_sidebar():
    """Load active buses for sidebar selection."""
    buses_df = load_buses()

    if buses_df.empty:
        return []

    buses_df = buses_df[buses_df["Status"] == "Active"]

    return [
        {
            "plate": row["Plate Number"],
            "label": f"{row['Plate Number']} - {row['Bus Name']}"
        }
        for _, row in buses_df.iterrows()
    ]




def save_bus_to_db(
    plate_number,
    bus_name,
    driver,
    route,
    status,
    insurance_expiry,
    service_date,
    notes
):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO buses (
            plate_number,
            bus_name,
            driver,
            route,
            status,
            insurance_expiry,
            service_date,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(plate_number)
        DO UPDATE SET
            bus_name = excluded.bus_name,
            driver = excluded.driver,
            route = excluded.route,
            status = excluded.status,
            insurance_expiry = excluded.insurance_expiry,
            service_date = excluded.service_date,
            notes = excluded.notes,
            updated_at = excluded.updated_at
    """, (
        plate_number,
        bus_name,
        driver,
        route,
        status,
        insurance_expiry,
        service_date,
        notes,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def delete_bus_from_db(plate_number):
    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "DELETE FROM buses WHERE plate_number = ?",
        (plate_number,)
    )

    conn.commit()
    conn.close()


def export_all_records_to_excel():
    conn = get_connection()

    records_df = pd.read_sql_query(
        "SELECT * FROM daily_records ORDER BY record_date, bus_plate",
        conn
    )

    buses_df = pd.read_sql_query(
        "SELECT * FROM buses ORDER BY plate_number",
        conn
    )

    logs_df = pd.read_sql_query(
        "SELECT * FROM audit_logs ORDER BY id DESC",
        conn
    )

    conn.close()

    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        records_df.to_excel(writer, index=False, sheet_name="Daily Records")
        buses_df.to_excel(writer, index=False, sheet_name="Buses")
        logs_df.to_excel(writer, index=False, sheet_name="Audit Logs")

    output.seek(0)
    return output


def import_records_from_excel(uploaded_excel):
    excel_file = pd.ExcelFile(uploaded_excel)

    conn = get_connection()

    if "Daily Records" in excel_file.sheet_names:
        records_df = pd.read_excel(uploaded_excel, sheet_name="Daily Records")

        records_df.to_sql(
            "daily_records",
            conn,
            if_exists="append",
            index=False
        )

    if "Buses" in excel_file.sheet_names:
        buses_df = pd.read_excel(uploaded_excel, sheet_name="Buses")

        buses_df.to_sql(
            "buses",
            conn,
            if_exists="append",
            index=False
        )

    conn.commit()
    conn.close()



def authenticate_user(username, password):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        SELECT username, password_hash, role
        FROM users
        WHERE username = ?
    """, (username,))

    user = c.fetchone()
    conn.close()

    if not user:
        return None

    db_username, password_hash, role = user

    if hashlib.sha256(password.encode()).hexdigest() == password_hash:
        return {
            "username": db_username,
            "role": role
        }

    return None


def save_record_to_db(bus_plate, record_date, income, expense, category, notes):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO daily_records (
            bus_plate, record_date, income, expense, category,
            notes, updated_by, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(bus_plate, record_date)
        DO UPDATE SET
            income = excluded.income,
            expense = excluded.expense,
            category = excluded.category,
            notes = excluded.notes,
            updated_by = excluded.updated_by,
            updated_at = excluded.updated_at
    """, (
        bus_plate,
        record_date,
        income,
        expense,
        category,
        notes,
        st.session_state.current_user,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def load_month_from_db(bus_plate, month_name, year):
    month_number = datetime.strptime(month_name, "%B").month
    start_date = f"{year}-{month_number:02d}-01"
    end_date = f"{year}-{month_number:02d}-31"

    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT record_date, income, expense, category, notes
        FROM daily_records
        WHERE bus_plate = ?
        AND record_date BETWEEN ? AND ?
        ORDER BY record_date
        """,
        conn,
        params=(bus_plate, start_date, end_date)
    )

    conn.close()
    return df


def save_log_to_db(action):
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        INSERT INTO audit_logs (timestamp, username, role, action)
        VALUES (?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        st.session_state.get("current_user"),
        st.session_state.get("current_role"),
        action
    ))

    conn.commit()
    conn.close()


def load_logs_from_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("PRAGMA table_info(audit_logs)")
    columns = [col[1] for col in c.fetchall()]

    user_column = "username" if "username" in columns else "user"

    df = pd.read_sql_query(
        f"""
        SELECT
            timestamp AS Timestamp,
            {user_column} AS User,
            role AS Role,
            action AS "Action Details"
        FROM audit_logs
        ORDER BY id DESC
        """,
        conn
    )

    conn.close()
    return df




# DASH BOARD HELPER FUNCTION

def load_all_daily_records():
    conn = get_connection()

    df = pd.read_sql_query(
        """
        SELECT
            bus_plate,
            record_date,
            income,
            expense,
            category,
            notes
        FROM daily_records
        ORDER BY record_date
        """,
        conn
    )

    conn.close()

    if not df.empty:
        df["record_date"] = pd.to_datetime(df["record_date"])
        df["Month"] = df["record_date"].dt.strftime("%B")
        df["Month No"] = df["record_date"].dt.month
        df["Day"] = df["record_date"].dt.day
        df["Net"] = df["income"] - df["expense"]

    return df


def get_dashboard_data(selected_year):
    df = load_all_daily_records()

    if df.empty:
        return df

    df = df[df["record_date"].dt.year == selected_year]

    return df    

# For PDF generation
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def set_app_theme(theme_name):
    themes = {
        "🌙 Night": {
            "image": "background_night.jpg",
            "overlay": "rgba(5,10,25,0.60)",
            "button": "#FF8C00",
            "button_hover": "#E67E00"
        },
        "🌊 Ocean": {
            "image": "background_ocean.jpg",
            "overlay": "rgba(0,40,70,0.45)",
            "button": "#0284C7",
            "button_hover": "#0369A1"
        },
        "🌲 Forest": {
            "image": "background_forest.jpg",
            "overlay": "rgba(0,45,25,0.50)",
            "button": "#16A34A",
            "button_hover": "#15803D"
        },
        "🌅 Sunset": {
            "image": "background_sunset.jpg",
            "overlay": "rgba(80,30,0,0.50)",
            "button": "#F97316",
            "button_hover": "#EA580C"
        }
    }

    theme = themes.get(theme_name, themes["🌙 Night"])

    try:
        with open(theme["image"], "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode()

        background_css = f"""
        background:
            linear-gradient({theme['overlay']}, {theme['overlay']}),
            url("data:image/jpeg;base64,{encoded}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
        """

    except FileNotFoundError:
        background_css = """
        background: linear-gradient(135deg, #020617, #0F172A, #1E293B);
        """

    st.markdown(
        f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            {background_css}
        }}

        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}

        [data-testid="stSidebar"] {{
            background: rgba(0,0,0,0.55);
            backdrop-filter: blur(10px);
        }}

        .stApp {{
            background: transparent;
        }}

        h1, h2, h3, h4, h5, h6, p, label, span {{
            color: white !important;
        }}

        div[data-testid="metric-container"] {{
            background: rgba(255,255,255,0.10);
            border-radius: 15px;
            padding: 16px;
            border: 1px solid rgba(255,255,255,0.18);
            backdrop-filter: blur(8px);
        }}

        button[kind="primary"] {{
            background: {theme["button"]} !important;
            color: white !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
        }}

        button[kind="primary"]:hover {{
            background: {theme["button_hover"]} !important;
            color: white !important;
        }}

        button[kind="primary"] * {{
            color: white !important;
        }}

        div[data-testid="stDataFrame"] {{
            background: rgba(255,255,255,0.92);
            border-radius: 12px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

        # SET CONFIGURATION


st.set_page_config(
    page_title="Bus Income Tracker",
    layout="wide",
    page_icon="🚌"
)

init_database()
migrate_buses_table()
migrate_users_table()
migrate_audit_logs_table()

if "app_theme" not in st.session_state:
    st.session_state.app_theme = "🌙 Night"

with st.sidebar:
    st.markdown("### 🎨 Theme")
    st.session_state.app_theme = st.selectbox(
        "Select appearance",
        ["🌙 Night", "🌊 Ocean", "🌲 Forest", "🌅 Sunset"],
        index=["🌙 Night", "🌊 Ocean", "🌲 Forest", "🌅 Sunset"].index(
            st.session_state.app_theme
        )
    )

set_app_theme(st.session_state.app_theme)

# ====================== USER MANAGEMENT ======================
if "users" not in st.session_state:
    st.session_state.users = {
        "admin": (hashlib.sha256("admin123".encode()).hexdigest(), "admin"),
        "partner": (hashlib.sha256("partner2026".encode()).hexdigest(), "user"),
    }

if "current_user" not in st.session_state:
    st.session_state.current_user = None
    st.session_state.current_role = None

if "logs" not in st.session_state:
    st.session_state.logs = []

def log_activity(action):
    if st.session_state.current_user:
        save_log_to_db(action)


# ====================== USER MANAGEMENT ======================

if "users" not in st.session_state:
    st.session_state.users = {
        "admin": (...),
        "partner": (...),
    }

if "current_user" not in st.session_state:
    st.session_state.current_user = None
    st.session_state.current_role = None

if "logs" not in st.session_state:
    st.session_state.logs = []


def log_activity(action):
    if st.session_state.current_user:
        save_log_to_db(action)


# ======================================================
# PERMISSION HELPERS
# ======================================================

def is_admin():
    return st.session_state.get("current_role") == "admin"


def require_admin():
    if not is_admin():
        st.error("⛔ Administrator access required.")
        st.stop()


# ======================================================
# LOGIN
# ======================================================

def login():
    ...

def login():
    if st.session_state.current_user is None:
        st.title("🔐 Bus Income Tracker Login")

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", type="primary"):
            user = authenticate_user(username, password)

            if user:
                st.session_state.current_user = user["username"]
                st.session_state.current_role = user["role"]
                log_activity("Logged into system session")
                st.rerun()
            else:
                st.error("Invalid username or password")

        st.stop()

login()

# ====================== STYLING ======================
st.markdown("""
<style>
    .main {background-color: #f8f9fa; color: #ffffff;}
    h1, h2, h3, p, label {color: #ffffff !important;}
</style>
""", unsafe_allow_html=True)


# ====================== SIDEBAR ======================
st.sidebar.success(f"👤 {st.session_state.current_user} ({st.session_state.current_role})")
st.sidebar.markdown("# 🚌 Bus Income Tracker")

# BUS CHOICES

active_buses = get_active_buses_for_sidebar()

if not active_buses:
    st.sidebar.warning("No active buses found. Add a bus in Manage Buses.")
    st.stop()

bus_labels = [bus["label"] for bus in active_buses]

bus_choice = st.sidebar.radio(
    "Select Bus",
    bus_labels,
    horizontal=False
)

current_bus = next(
    bus["plate"]
    for bus in active_buses
    if bus["label"] == bus_choice
)

months = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
selected_month = st.sidebar.selectbox("Select Current Entry Month", months, index=datetime.now().month-1)

if st.sidebar.button("🚪 Logout"):
    log_activity("Logged out of system session")
    st.session_state.current_user = None
    st.session_state.current_role = None
    st.rerun()

# ====================== HELPER FUNCTIONS ======================
def get_days_in_month(month_name):
    if month_name == "February":
        year = datetime.now().year
        return 29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28
    elif month_name in ["January", "March", "May", "July", "August", "October", "December"]:
        return 31
    return 30

def get_month_dataframe(bus, month_name):
    year = datetime.now().year
    total_days = get_days_in_month(month_name)

    db_df = load_month_from_db(bus, month_name, year)

    saved_records = {}

    if not db_df.empty:
        db_df["day"] = pd.to_datetime(db_df["record_date"]).dt.day

        saved_records = {
            int(row["day"]): row
            for _, row in db_df.iterrows()
        }

    m_records = []

    for d in range(1, total_days + 1):
        saved = saved_records.get(d)

        income = int(saved["income"]) if saved is not None else 0
        expense = int(saved["expense"]) if saved is not None else 0
        category = saved["category"] if saved is not None else "None"
        notes = saved["notes"] if saved is not None else ""

        m_records.append({
            "Day": d,
            "Date": f"{d:02d} {month_name}",
            "Month": month_name,
            "Income (TZS)": income,
            "Expense (TZS)": expense,
            "Category": category,
            "Net (TZS)": income - expense,
            "Notes": notes
        })

    return pd.DataFrame(m_records)

# ====================== MAIN APP ======================
st.title("🚌 Bus Income & Expense Tracker")
st.caption(f"**Viewing/Editing:** {current_bus} • {selected_month} 2026")

tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🏠 Dashboard",
    "📊 Daily Entry",
    "📈 Trends",
    "📋 Monthly Summary",
    "📋 Audit Trail Logs",
    "📄 Reports",
    "🚌 Fleet Management",
    "👥 User Administration"
])

# ====================== DASHBOARD ======================

with tab0:
    st.subheader("🏠 Fleet Financial Dashboard")

    selected_year_dashboard = st.selectbox(
        "Select dashboard year",
        [datetime.now().year, datetime.now().year - 1, datetime.now().year - 2],
        index=0,
        key="dashboard_year"
    )

    dashboard_df = get_dashboard_data(selected_year_dashboard)

    if dashboard_df.empty:
        st.info("No financial records available for dashboard.")
    else:
        total_income_dash = dashboard_df["income"].sum()
        total_expense_dash = dashboard_df["expense"].sum()
        total_profit_dash = dashboard_df["Net"].sum()
        profit_margin = (
            total_profit_dash / total_income_dash * 100
            if total_income_dash > 0 else 0
        )

        m1, m2, m3, m4 = st.columns(4)

        m1.metric("Total Income", f"TZS {total_income_dash:,.0f}")
        m2.metric("Total Expenses", f"TZS {total_expense_dash:,.0f}")
        m3.metric("Net Profit", f"TZS {total_profit_dash:,.0f}")
        m4.metric("Profit Margin", f"{profit_margin:.1f}%")

        st.divider()

        # Monthly profit trend
        monthly_df = (
            dashboard_df
            .groupby(["Month No", "Month"], as_index=False)
            .agg({
                "income": "sum",
                "expense": "sum",
                "Net": "sum"
            })
            .sort_values("Month No")
        )

        st.markdown("### 📈 Monthly Profit Trend")

        monthly_chart_df = monthly_df.set_index("Month")[["income", "expense", "Net"]]

        st.line_chart(monthly_chart_df)

        st.divider()

        col_a, col_b = st.columns(2)


        # fuel cost trend

        st.divider()
        st.markdown("### ⛽ Fuel and Repairs Cost Trend")

        cost_trend_df = dashboard_df[
            dashboard_df["category"].isin(["Fuel", "Repairs"])
        ]

        if cost_trend_df.empty:
            st.info("No Fuel or Repairs expenses recorded yet.")
        else:
            fuel_repairs_df = (
                cost_trend_df
                .groupby(["Month No", "Month", "category"], as_index=False)["expense"]
                .sum()
                .sort_values("Month No")
            )

            pivot_cost_df = fuel_repairs_df.pivot_table(
                index="Month",
                columns="category",
                values="expense",
                aggfunc="sum",
                fill_value=0
            )

            st.line_chart(pivot_cost_df)

        # Expense category pie chart
        with col_a:
            st.markdown("### 🧾 Expense by Category")

            expense_category_df = (
                dashboard_df[dashboard_df["expense"] > 0]
                .groupby("category", as_index=False)["expense"]
                .sum()
                .sort_values("expense", ascending=False)
            )

            if expense_category_df.empty:
                st.info("No expense categories recorded.")
            else:
                fig_expense = {
                    "data": [
                        {
                            "labels": expense_category_df["category"],
                            "values": expense_category_df["expense"],
                            "type": "pie",
                            "hole": 0.35
                        }
                    ],
                    "layout": {
                        "height": 380,
                        "paper_bgcolor": "rgba(0,0,0,0)",
                        "plot_bgcolor": "rgba(0,0,0,0)",
                        "font": {"color": "white"}
                    }
                }

                st.plotly_chart(fig_expense, use_container_width=True)

        # Bus comparison
        with col_b:
            st.markdown("### 🚌 Bus Comparison")

            bus_compare_df = (
                dashboard_df
                .groupby("bus_plate", as_index=False)
                .agg({
                    "income": "sum",
                    "expense": "sum",
                    "Net": "sum"
                })
                .sort_values("Net", ascending=False)
            )

            st.bar_chart(
                bus_compare_df.set_index("bus_plate")[["income", "expense", "Net"]]
            )

        st.divider()

        # Best and worst days
        st.markdown("### 🏆 Best and Worst Performing Days")

        daily_perf_df = (
            dashboard_df
            .groupby(["record_date", "bus_plate"], as_index=False)
            .agg({
                "income": "sum",
                "expense": "sum",
                "Net": "sum"
            })
        )

        best_days = daily_perf_df.sort_values("Net", ascending=False).head(5)
        worst_days = daily_perf_df.sort_values("Net", ascending=True).head(5)

        best_col, worst_col = st.columns(2)

        with best_col:
            st.markdown("#### 🟢 Best Days")
            st.dataframe(
                best_days.rename(columns={
                    "record_date": "Date",
                    "bus_plate": "Bus",
                    "income": "Income",
                    "expense": "Expense",
                    "Net": "Net Profit"
                }),
                use_container_width=True,
                hide_index=True
            )

        with worst_col:
            st.markdown("#### 🔴 Worst Days")
            st.dataframe(
                worst_days.rename(columns={
                    "record_date": "Date",
                    "bus_plate": "Bus",
                    "income": "Income",
                    "expense": "Expense",
                    "Net": "Net Profit"
                }),
                use_container_width=True,
                hide_index=True
            )


with tab1:
    st.subheader(f"Daily Records - {selected_month} 2026")
    
       
    df = get_month_dataframe(current_bus, selected_month)
   
    edited_df = st.data_editor(df, hide_index=True, use_container_width=True,
        column_config={
            "Day": None,
            "Month": None,
            "Date": st.column_config.TextColumn(disabled=True),
            "Income (TZS)": st.column_config.NumberColumn(format="TZS %d", min_value=0),
            "Expense (TZS)": st.column_config.NumberColumn(format="TZS %d", min_value=0),
            "Category": st.column_config.SelectboxColumn(
                options=["None", "Fuel", "Repairs", "Driver Wages", "Tolls", "Other"],
                required=True
            ),
            "Net (TZS)": st.column_config.NumberColumn(format="TZS %d", disabled=True),
            "Notes": st.column_config.TextColumn()
        })
   
    total_income = edited_df["Income (TZS)"].sum()
    total_expense = edited_df["Expense (TZS)"].sum()
    total_net = total_income - total_expense
   
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Income", f"TZS {total_income:,.0f}")
    c2.metric("Total Expense", f"TZS {total_expense:,.0f}")
    c3.metric("Net Profit", f"TZS {total_net:,.0f}")
   
    if st.button("💾 Save Entries", type="primary", use_container_width=True):
        for i, row in edited_df.iterrows():
            day_key = f"day_{row['Day']}"
            record_date = f"{datetime.now().year}-{datetime.strptime(selected_month, '%B').month:02d}-{int(row['Day']):02d}"

            save_record_to_db(
                bus_plate=current_bus,
                record_date=record_date,
                income=int(row["Income (TZS)"]),
                expense=int(row["Expense (TZS)"]),
                category=str(row["Category"]),
                notes=str(row["Notes"])
            )
            
        log_activity(f"Updated data matrix records for {current_bus} - {selected_month}")
        st.success("✅ Saved successfully!")
        st.rerun()

with tab2:
    st.subheader(f"📈 Performance Trends - {current_bus}")
    col_t1, col_t2 = st.columns([1, 4])
    with col_t1:
        select_all_trends = st.checkbox("Select All Months", value=False, key="trend_all_cb")
    with col_t2:
        trend_months = st.multiselect(
            "Choose months to visualize:",
            options=months,
            default=[selected_month]
        )
   
    active_trend_months = months if select_all_trends else trend_months
   
    if active_trend_months:
        trend_frames = [get_month_dataframe(current_bus, m) for m in active_trend_months]
        combined_trend_df = pd.concat(trend_frames, ignore_index=True)
        if not combined_trend_df.empty:
            st.line_chart(combined_trend_df.set_index("Date")[["Income (TZS)", "Expense (TZS)", "Net (TZS)"]])

with tab3:
    st.subheader(f"📋 Monthly Summary - {selected_month}")
    year = datetime.now().year

    total_income_all = 0
    total_expense_all = 0

    for bus in [bus["plate"] for bus in active_buses]:
        bus_df = get_month_dataframe(bus, selected_month)

        total_income_all += bus_df["Income (TZS)"].sum()
        total_expense_all += bus_df["Expense (TZS)"].sum()

    net_all = total_income_all - total_expense_all
   
    col1, col2, col3 = st.columns(3)
    col1.metric("Combined Fleet Income", f"TZS {total_income_all:,.0f}")
    col2.metric("Combined Fleet Expenses", f"TZS {total_expense_all:,.0f}")
    col3.metric("Combined Net Profit", f"TZS {net_all:,.0f}")

with tab4:
    st.subheader("📋 Audit Trail Logs")

    require_admin()

    logs_df = load_logs_from_db()

    if logs_df.empty:
        st.info("No system logging actions found yet.")
    else:
        st.dataframe(
            logs_df,
            use_container_width=True,
            hide_index=True
        )

with tab5:
    st.subheader("📄 Professional PDF Reports")

    require_admin()
   
    col_r1, col_r2 = st.columns([1, 4])
    with col_r1:
        select_all_reports = st.checkbox("Select All Months", value=False, key="report_all_cb")
    with col_r2:
        report_months = st.multiselect(
            "Choose months for PDF:",
            options=months,
            default=[selected_month]
        )
       
    active_report_months = months if select_all_reports else report_months
   
    if st.button("Generate & Download PDF Report", type="primary"):
        if active_report_months:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
            styles = getSampleStyleSheet()
            elements = []
           
            elements.append(Paragraph(f"FLEET PERFORMANCE REPORT - {selected_month} 2026", styles['Title']))
            elements.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 20))

            # Summary Table (You can expand this part further)
            elements.append(Paragraph("Summary Metrics", styles['Heading2']))
            data = [["Metric", "Value (TZS)"], 
                    ["Total Income", f"{total_income:,.0f}"],
                    ["Total Expense", f"{total_expense:,.0f}"],
                    ["Net Profit", f"{total_net:,.0f}"]]
            t = Table(data, colWidths=[3*inch, 3*inch])
            t.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.grey),
                                   ('BACKGROUND', (0,0), (-1,0), colors.grey),
                                   ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke)]))
            elements.append(t)

            doc.build(elements)
            buffer.seek(0)

            st.download_button(
                label="📥 Download PDF Report",
                data=buffer,
                file_name=f"Bus_Report_{current_bus}_{selected_month}.pdf",
                mime="application/pdf"

            )

# ==========================================================
# BACKUP & RESTORE CENTER
# ==========================================================

st.divider()

st.subheader("💾 Backup & Restore Center")

backup_tab1, backup_tab2, backup_tab3 = st.tabs(
    [
        "📥 Export",
        "📤 Import",
        "🗄 Database Backup"
    ]
)

# ==========================================================
# EXPORT
# ==========================================================

with backup_tab1:

    st.markdown("### Excel Export")

    st.info(
        "Export all financial records, buses and audit logs "
        "into a professional Excel workbook."
    )

    excel_buffer = export_all_records_to_excel()

    st.download_button(
        label="📥 Download Excel Workbook",
        data=excel_buffer,
        file_name=f"Fleet_Backup_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# ==========================================================
# IMPORT
# ==========================================================

with backup_tab2:

    st.markdown("### Restore From Excel")

    uploaded_excel = st.file_uploader(
        "Choose Excel backup",
        type=["xlsx"],
        key="excel_import"
    )

    if uploaded_excel is not None:

        st.success("Backup loaded successfully.")

        if st.button(
            "📤 Restore Workbook",
            type="primary",
            use_container_width=True
        ):

            try:

                import_records_from_excel(uploaded_excel)

                log_activity("Restored Excel backup")

                st.success(
                    "Database restored successfully."
                )

                st.rerun()

            except Exception as e:

                st.error(e)

# ==========================================================
# SQLITE BACKUP
# ==========================================================

with backup_tab3:

    st.markdown("### Database Backup")

    st.info(
        "Download the complete SQLite database. "
        "This preserves ALL records exactly."
    )

    with open(DB_NAME, "rb") as f:

        st.download_button(

            "🗄 Download Database",

            data=f,

            file_name="bus_income_tracker.db",

            mime="application/octet-stream",

            use_container_width=True

        )

with tab6:
    st.subheader("🚌 Manage Buses")


    require_admin()

    buses_df = load_buses()

    st.markdown("### Current Fleet")

    if buses_df.empty:
        st.info("No buses registered yet.")
    else:
        st.dataframe(
            buses_df,
            use_container_width=True,
            hide_index=True
        )

    st.divider()

    st.markdown("### Add or Edit Bus")

    edit_mode = "Add New Bus"

    if not buses_df.empty:
        edit_mode = st.radio(
            "Mode",
            ["Add New Bus", "Edit Existing Bus"],
            horizontal=True
        )

    selected_bus = None

    if edit_mode == "Edit Existing Bus" and not buses_df.empty:
        selected_plate = st.selectbox(
            "Select bus to edit",
            buses_df["Plate Number"].tolist()
        )

        selected_bus = buses_df[
            buses_df["Plate Number"] == selected_plate
        ].iloc[0]

    col1, col2 = st.columns(2)

    with col1:
        plate_number = st.text_input(
            "Plate number",
            value=selected_bus["Plate Number"] if selected_bus is not None else ""
        )

        bus_name = st.text_input(
            "Bus name",
            value=selected_bus["Bus Name"] if selected_bus is not None else ""
        )

        driver = st.text_input(
            "Driver",
            value=selected_bus["Driver"] if selected_bus is not None else ""
        )

        route = st.text_input(
            "Route",
            value=selected_bus["Route"] if selected_bus is not None else ""
        )

    with col2:
        status_options = ["Active", "Maintenance", "Inactive", "Sold"]

        selected_status = (
            selected_bus["Status"]
            if selected_bus is not None and selected_bus["Status"] in status_options
            else "Active"
        )

        status = st.selectbox(
            "Status",
            status_options,
            index=status_options.index(selected_status)
        )

        insurance_expiry = st.date_input(
            "Insurance expiry",
            value=(
                pd.to_datetime(selected_bus["Insurance Expiry"]).date()
                if selected_bus is not None and selected_bus["Insurance Expiry"]
                else datetime.now().date()
            )
        )

        service_date = st.date_input(
            "Last / next service date",
            value=(
                pd.to_datetime(selected_bus["Service Date"]).date()
                if selected_bus is not None and selected_bus["Service Date"]
                else datetime.now().date()
            )
        )

        notes = st.text_area(
            "Notes",
            value=selected_bus["Notes"] if selected_bus is not None else ""
        )

    if st.button("💾 Save Bus", type="primary", use_container_width=True):
        if st.session_state.current_role != "admin":
            st.error("Permission denied. Only admin can save bus records.")

        elif not plate_number.strip():
            st.error("Plate number is required.")

        elif not bus_name.strip():
            st.error("Bus name is required.")

        else:
            save_bus_to_db(
                plate_number=plate_number.strip().upper(),
                bus_name=bus_name.strip(),
                driver=driver.strip(),
                route=route.strip(),
                status=status,
                insurance_expiry=str(insurance_expiry),
                service_date=str(service_date),
                notes=notes.strip()
            )

            log_activity(f"Saved bus record: {plate_number.strip().upper()}")
            st.success("Bus record saved successfully.")
            st.rerun()

    if (
        edit_mode == "Edit Existing Bus"
        and selected_bus is not None
        and st.session_state.current_role == "admin"
    ):
        st.divider()
        st.markdown("### Danger Zone")

        confirm_delete = st.checkbox(
            f"I understand this will delete bus {selected_bus['Plate Number']}"
        )

        if st.button("🗑️ Delete Selected Bus", type="primary"):
            if confirm_delete:
                delete_bus_from_db(selected_bus["Plate Number"])
                log_activity(f"Deleted bus record: {selected_bus['Plate Number']}")
                st.success("Bus deleted.")
                st.rerun()
            
        else:
            st.warning("Please select at least one month.")

st.caption("✅ Multi-user • PDF Reports • Built with ❤️ using Streamlit")

