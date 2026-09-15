
import streamlit as st
import pandas as pd
import sqlite3
import json
import os
from datetime import date
from io import StringIO

st.set_page_config(
    page_title="Fire/EMS Grant Command Center",
    page_icon="🚒",
    layout="wide",
)

DB_PATH = os.getenv("GRANT_DB_PATH", "fire_ems_grants.db")

# =========================================================
# DATABASE
# =========================================================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS department_profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        department_name TEXT,
        department_type TEXT,
        ein_tax_id TEXT,
        uei TEXT,
        address TEXT,
        municipality TEXT,
        county TEXT,
        state TEXT,
        zip_code TEXT,
        website TEXT,
        chief_contact TEXT,
        grant_contact TEXT,
        phone TEXT,
        email TEXT,
        mission TEXT,
        service_area_sq_miles REAL,
        population_served INTEGER,
        stations INTEGER,
        career_staff INTEGER,
        part_time_staff INTEGER,
        volunteer_members INTEGER,
        active_operational_members INTEGER,
        annual_budget REAL,
        founded_year INTEGER,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS department_statistics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        metric TEXT NOT NULL,
        value TEXT NOT NULL,
        period TEXT,
        source TEXT,
        verified INTEGER DEFAULT 1,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS call_volume (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER,
        fire_calls INTEGER DEFAULT 0,
        ems_calls INTEGER DEFAULT 0,
        rescue_calls INTEGER DEFAULT 0,
        hazmat_calls INTEGER DEFAULT 0,
        service_calls INTEGER DEFAULT 0,
        false_alarms INTEGER DEFAULT 0,
        other_calls INTEGER DEFAULT 0,
        mutual_aid_given INTEGER DEFAULT 0,
        mutual_aid_received INTEGER DEFAULT 0,
        total_calls INTEGER DEFAULT 0,
        avg_response_minutes REAL,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inventory_needs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        item TEXT NOT NULL,
        current_qty INTEGER DEFAULT 0,
        needed_qty INTEGER DEFAULT 0,
        condition TEXT,
        age_years REAL,
        replacement_cycle_years REAL,
        unit_cost REAL DEFAULT 0,
        priority TEXT,
        standard_reference TEXT,
        justification TEXT,
        vendor_quote TEXT,
        status TEXT DEFAULT 'Needed'
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS compliance_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        framework TEXT,
        standard_reference TEXT,
        topic TEXT,
        requirement_summary TEXT,
        current_status TEXT,
        gap TEXT,
        evidence_source TEXT,
        last_reviewed TEXT,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS demographics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric TEXT NOT NULL,
        value TEXT NOT NULL,
        geography TEXT,
        year TEXT,
        source TEXT,
        verified INTEGER DEFAULT 1,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS grant_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grant_name TEXT,
        funder TEXT,
        project TEXT,
        year INTEGER,
        amount_requested REAL DEFAULT 0,
        amount_awarded REAL DEFAULT 0,
        result TEXT,
        match_amount REAL DEFAULT 0,
        purpose TEXT,
        feedback TEXT,
        closeout_complete TEXT,
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grant_key TEXT,
        category TEXT,
        line_item TEXT,
        qty REAL DEFAULT 1,
        unit_cost REAL DEFAULT 0,
        requested_amount REAL DEFAULT 0,
        match_amount REAL DEFAULT 0,
        other_funding REAL DEFAULT 0,
        justification TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS grants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grant_name TEXT,
        funder TEXT,
        deadline TEXT,
        project_name TEXT,
        amount_requested REAL DEFAULT 0,
        match_amount REAL DEFAULT 0,
        project_summary TEXT,
        statement_of_need TEXT,
        goals TEXT,
        methods TEXT,
        evaluation TEXT,
        sustainability TEXT,
        status TEXT DEFAULT 'Planning',
        notes TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS rubrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grant_id INTEGER,
        criterion TEXT,
        weight REAL DEFAULT 0,
        max_score REAL DEFAULT 10,
        funder_guidance TEXT,
        character_limit INTEGER DEFAULT 0,
        required_elements TEXT,
        FOREIGN KEY(grant_id) REFERENCES grants(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS ai_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        grant_id INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        model TEXT,
        content TEXT,
        FOREIGN KEY(grant_id) REFERENCES grants(id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

def execute(query, params=()):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    conn.close()

def query_df(query, params=()):
    conn = get_conn()
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def query_one(query, params=()):
    conn = get_conn()
    row = conn.execute(query, params).fetchone()
    conn.close()
    return dict(row) if row else None

def money(x):
    try:
        return f"${float(x):,.2f}"
    except:
        return "$0.00"

def safe(v):
    return "" if v is None else str(v)

def build_context(grant_id):
    profile = query_one("SELECT * FROM department_profile WHERE id=1") or {}
    stats = query_df("SELECT * FROM department_statistics ORDER BY category, metric").to_dict("records")
    calls = query_df("SELECT * FROM call_volume ORDER BY year DESC").to_dict("records")
    inv = query_df("SELECT * FROM inventory_needs ORDER BY CASE priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 ELSE 4 END, item").to_dict("records")
    compliance = query_df("SELECT * FROM compliance_data ORDER BY framework, standard_reference").to_dict("records")
    demographics = query_df("SELECT * FROM demographics ORDER BY metric").to_dict("records")
    history = query_df("SELECT * FROM grant_history ORDER BY year DESC").to_dict("records")
    grant = query_one("SELECT * FROM grants WHERE id=?", (grant_id,)) or {}
    rubric = query_df("SELECT * FROM rubrics WHERE grant_id=? ORDER BY id", (grant_id,)).to_dict("records")
    budget = query_df("SELECT * FROM budgets WHERE grant_key=? ORDER BY category, line_item", (str(grant_id),)).to_dict("records")

    return {
        "department_profile": profile,
        "department_statistics": stats,
        "call_volume_history": calls,
        "inventory_and_equipment_needs": inv,
        "nfpa_iso_and_compliance_records": compliance,
        "community_demographics": demographics,
        "grant_history": history,
        "current_grant": grant,
        "rubric": rubric,
        "budget": budget,
    }

def build_ai_prompt(context):
    return f"""
You are a professional Fire/EMS grant writer.

Write a complete grant application working draft that is optimized to address every scoring criterion in the funder's rubric while remaining truthful, specific, and evidence-based.

CRITICAL RULES:
1. Use ONLY facts contained in the provided department dataset or clearly label missing information as [DATA NEEDED: ...].
2. Never invent call volume, response times, staffing, demographics, equipment condition, NFPA requirements, ISO classifications, quotes, costs, grant history, dates, certifications, or outcomes.
3. NFPA/ISO information in the dataset may be department-entered notes. Do not independently claim a specific standard mandates something unless the dataset explicitly says so.
4. Tie statistics directly to the statement of need.
5. Explain why the requested equipment/program changes operational capability, responder safety, patient/community outcomes, reliability, readiness, interoperability, or service continuity when supported by the data.
6. Address every rubric criterion explicitly.
7. Use measurable objectives. If a baseline or target is missing, insert [DATA NEEDED] rather than inventing it.
8. Explain budget reasonableness using entered costs and quantities only.
9. Where relevant, distinguish existing resources from gaps and requested resources.
10. Mention prior grants only when present in grant history.
11. Do not promise compliance, performance improvements, or outcomes that cannot be supported.
12. Write in polished professional grant language suitable for a fire department, EMS agency, rescue squad, or combination public-safety organization.

OUTPUT FORMAT:
# Executive Summary

# Organizational Background

# Statement of Need

# Project Description

# Goals and Measurable Objectives

# Implementation Plan

# Community Impact

# Fire/EMS Operational Impact

# Standards / ISO / Compliance Alignment
Only discuss records actually supplied.

# Evaluation Plan

# Sustainability

# Budget Narrative

# Prior Grant Performance
Only include if supported by the dataset.

# Rubric-by-Rubric Response
For EACH rubric criterion:
## [Criterion Name]
- Weight / Max Points
- What the funder is asking for
- Draft response
- Evidence used
- Missing evidence or improvements needed

# Final Application Readiness Review
Provide:
- Strengths
- Missing data
- High-priority improvements before submission
- Claims that should be verified
- Rubric areas at risk of losing points

DATASET:
{json.dumps(context, indent=2, default=str)}
"""

# =========================================================
# UI
# =========================================================
st.title("🚒 Fire/EMS Grant Command Center")
st.caption("Department database • Equipment needs • NFPA/ISO tracking • Call history • Demographics • Budgets • Rubric-driven AI grant writing")

with st.sidebar:
    st.header("Navigation")
    page = st.radio(
        "Section",
        [
            "Dashboard",
            "Department Profile",
            "Department Statistics",
            "Call Volume History",
            "Equipment & Inventory Needs",
            "NFPA / ISO / Compliance",
            "Community Demographics",
            "Grant History",
            "Grant Projects",
            "Budget Builder",
            "Rubric Builder",
            "AI Grant Writer",
            "Data Export",
        ]
    )
    st.divider()
    st.caption(f"Database: {DB_PATH}")

# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    profile = query_one("SELECT * FROM department_profile WHERE id=1") or {}
    calls = query_df("SELECT * FROM call_volume ORDER BY year")
    inventory = query_df("SELECT * FROM inventory_needs")
    grants = query_df("SELECT * FROM grants ORDER BY deadline")
    history = query_df("SELECT * FROM grant_history")

    st.subheader(profile.get("department_name") or "Fire/EMS Department Grant Dashboard")

    c1, c2, c3, c4 = st.columns(4)
    if not calls.empty:
        latest = calls.iloc[-1]
        c1.metric("Latest Annual Calls", f"{int(latest.get('total_calls',0) or 0):,}")
    else:
        c1.metric("Latest Annual Calls", "No data")

    critical = 0 if inventory.empty else len(inventory[inventory["priority"].isin(["Critical", "High"])])
    c2.metric("Critical / High Needs", critical)

    outstanding = 0
    if not inventory.empty:
        outstanding = ((inventory["needed_qty"].fillna(0) * inventory["unit_cost"].fillna(0))).sum()
    c3.metric("Estimated Equipment Need", money(outstanding))

    awarded = 0 if history.empty else history["amount_awarded"].fillna(0).sum()
    c4.metric("Historical Grant Awards", money(awarded))

    st.divider()
    if not calls.empty:
        chart = calls[["year", "fire_calls", "ems_calls", "rescue_calls", "total_calls"]].copy()
        chart = chart.set_index("year")
        st.subheader("Call Volume Trend")
        st.line_chart(chart)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top Equipment Needs")
        if inventory.empty:
            st.info("No equipment needs entered.")
        else:
            show = inventory[["item","needed_qty","unit_cost","priority","condition","status"]].copy()
            show["estimated_cost"] = show["needed_qty"].fillna(0) * show["unit_cost"].fillna(0)
            st.dataframe(show.sort_values(["priority","estimated_cost"], ascending=[True,False]).head(10), use_container_width=True, hide_index=True)

    with col2:
        st.subheader("Active Grant Projects")
        if grants.empty:
            st.info("No grant projects entered.")
        else:
            st.dataframe(grants[["grant_name","funder","deadline","project_name","amount_requested","status"]], use_container_width=True, hide_index=True)

# =========================================================
# DEPARTMENT PROFILE
# =========================================================
elif page == "Department Profile":
    st.subheader("Permanent Department Profile")
    existing = query_one("SELECT * FROM department_profile WHERE id=1") or {}

    with st.form("profile"):
        a,b = st.columns(2)
        with a:
            department_name = st.text_input("Department / Agency Name", value=safe(existing.get("department_name")))
            department_type = st.selectbox(
                "Department Type",
                ["", "Volunteer Fire", "Career Fire", "Combination Fire", "EMS", "Fire/EMS", "Rescue", "Municipal Public Safety", "Other"],
                index=0
            )
            if existing.get("department_type") in ["Volunteer Fire", "Career Fire", "Combination Fire", "EMS", "Fire/EMS", "Rescue", "Municipal Public Safety", "Other"]:
                department_type = existing.get("department_type")
            ein = st.text_input("EIN / Tax ID", value=safe(existing.get("ein_tax_id")))
            uei = st.text_input("UEI", value=safe(existing.get("uei")))
            address = st.text_input("Address", value=safe(existing.get("address")))
            municipality = st.text_input("Municipality", value=safe(existing.get("municipality")))
            county = st.text_input("County", value=safe(existing.get("county")))
            state = st.text_input("State", value=safe(existing.get("state")))
            zip_code = st.text_input("ZIP Code", value=safe(existing.get("zip_code")))
        with b:
            website = st.text_input("Website", value=safe(existing.get("website")))
            chief_contact = st.text_input("Chief / Executive Contact", value=safe(existing.get("chief_contact")))
            grant_contact = st.text_input("Grant Contact", value=safe(existing.get("grant_contact")))
            phone = st.text_input("Phone", value=safe(existing.get("phone")))
            email = st.text_input("Email", value=safe(existing.get("email")))
            service_area = st.number_input("Service Area (sq mi)", min_value=0.0, value=float(existing.get("service_area_sq_miles") or 0))
            pop = st.number_input("Population Served", min_value=0, value=int(existing.get("population_served") or 0))
            stations = st.number_input("Stations", min_value=0, value=int(existing.get("stations") or 0))
            founded = st.number_input("Founded Year", min_value=0, max_value=2100, value=int(existing.get("founded_year") or 0))
        c,d,e,f = st.columns(4)
        career = c.number_input("Career Staff", min_value=0, value=int(existing.get("career_staff") or 0))
        part = d.number_input("Part-Time Staff", min_value=0, value=int(existing.get("part_time_staff") or 0))
        volunteers = e.number_input("Volunteer Members", min_value=0, value=int(existing.get("volunteer_members") or 0))
        active = f.number_input("Active Operational Members", min_value=0, value=int(existing.get("active_operational_members") or 0))
        annual_budget = st.number_input("Annual Department Budget ($)", min_value=0.0, value=float(existing.get("annual_budget") or 0))
        mission = st.text_area("Mission", value=safe(existing.get("mission")), height=120)
        notes = st.text_area("Department Background / Notes", value=safe(existing.get("notes")), height=140)

        if st.form_submit_button("Save Department Profile", type="primary"):
            execute("DELETE FROM department_profile WHERE id=1")
            execute("""
            INSERT INTO department_profile
            (id,department_name,department_type,ein_tax_id,uei,address,municipality,county,state,zip_code,website,
             chief_contact,grant_contact,phone,email,mission,service_area_sq_miles,population_served,stations,
             career_staff,part_time_staff,volunteer_members,active_operational_members,annual_budget,founded_year,notes)
            VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                department_name,department_type,ein,uei,address,municipality,county,state,zip_code,website,
                chief_contact,grant_contact,phone,email,mission,service_area,pop,stations,career,part,
                volunteers,active,annual_budget,founded,notes
            ))
            st.success("Department profile saved.")

# =========================================================
# GENERIC TABLE PAGES
# =========================================================
elif page == "Department Statistics":
    st.subheader("Permanent Department Statistics Database")
    with st.form("stats_add", clear_on_submit=True):
        c1,c2,c3 = st.columns(3)
        category = c1.selectbox("Category", ["Operations","Staffing","Training","Response","Finance","Community","Prevention","EMS","Fire","Rescue","Other"])
        metric = c2.text_input("Metric")
        value = c3.text_input("Value")
        c4,c5 = st.columns(2)
        period = c4.text_input("Period / Year")
        source = c5.text_input("Source")
        verified = st.checkbox("Verified", value=True)
        notes = st.text_input("Notes / Grant Relevance")
        if st.form_submit_button("Add Statistic"):
            if metric and value:
                execute("INSERT INTO department_statistics(category,metric,value,period,source,verified,notes) VALUES(?,?,?,?,?,?,?)",
                        (category,metric,value,period,source,int(verified),notes))
                st.success("Statistic added.")
    df = query_df("SELECT * FROM department_statistics ORDER BY category, metric")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Call Volume History":
    st.subheader("Fire/EMS Call-Volume History")
    with st.form("calls_add", clear_on_submit=True):
        year = st.number_input("Year", min_value=1900, max_value=2100, value=date.today().year)
        cols = st.columns(4)
        fire = cols[0].number_input("Fire Calls", min_value=0)
        ems = cols[1].number_input("EMS Calls", min_value=0)
        rescue = cols[2].number_input("Rescue Calls", min_value=0)
        hazmat = cols[3].number_input("HazMat Calls", min_value=0)
        cols2 = st.columns(4)
        service = cols2[0].number_input("Service Calls", min_value=0)
        false = cols2[1].number_input("False Alarms", min_value=0)
        other = cols2[2].number_input("Other Calls", min_value=0)
        avg_resp = cols2[3].number_input("Avg Response Time (min)", min_value=0.0)
        m1,m2 = st.columns(2)
        mag = m1.number_input("Mutual Aid Given", min_value=0)
        mar = m2.number_input("Mutual Aid Received", min_value=0)
        notes = st.text_input("Notes")
        if st.form_submit_button("Add Year"):
            total = int(fire+ems+rescue+hazmat+service+false+other)
            execute("""
            INSERT INTO call_volume(year,fire_calls,ems_calls,rescue_calls,hazmat_calls,service_calls,false_alarms,other_calls,
            mutual_aid_given,mutual_aid_received,total_calls,avg_response_minutes,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(year,fire,ems,rescue,hazmat,service,false,other,mag,mar,total,avg_resp,notes))
            st.success("Call-volume year added.")
    df = query_df("SELECT * FROM call_volume ORDER BY year DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        chart = df.sort_values("year").set_index("year")[["fire_calls","ems_calls","rescue_calls","total_calls"]]
        st.line_chart(chart)

elif page == "Equipment & Inventory Needs":
    st.subheader("Equipment / Inventory Needs Database")
    with st.form("inventory_add", clear_on_submit=True):
        a,b,c = st.columns(3)
        category = a.selectbox("Category", ["PPE","SCBA","Fire Suppression","EMS","Rescue","Communications","Apparatus","Training","Station","Prevention","IT","Other"])
        item = b.text_input("Item")
        condition = c.selectbox("Condition", ["","New Need","Good","Fair","Poor","Out of Service","Obsolete","Expired/Near Expiration"])
        a,b,c,d = st.columns(4)
        current_qty = a.number_input("Current Qty", min_value=0)
        needed_qty = b.number_input("Qty Requested", min_value=0)
        age_years = c.number_input("Average Age (years)", min_value=0.0)
        replacement = d.number_input("Target Replacement Cycle (years)", min_value=0.0)
        e,f,g = st.columns(3)
        unit_cost = e.number_input("Estimated Unit Cost ($)", min_value=0.0)
        priority = f.selectbox("Priority", ["Critical","High","Medium","Low"])
        status = g.selectbox("Status", ["Needed","Quoted","Budgeted","Applied For","Ordered","Received","Closed"])
        standard = st.text_input("NFPA / ISO / State / Local Reference (optional)")
        quote = st.text_input("Vendor Quote / Quote Date / Reference")
        justification = st.text_area("Operational Need / Justification")
        if st.form_submit_button("Add Equipment Need"):
            if item:
                execute("""
                INSERT INTO inventory_needs(category,item,current_qty,needed_qty,condition,age_years,replacement_cycle_years,
                unit_cost,priority,standard_reference,justification,vendor_quote,status)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,(category,item,current_qty,needed_qty,condition,age_years,replacement,unit_cost,priority,standard,justification,quote,status))
                st.success("Equipment need added.")
    df = query_df("SELECT *, needed_qty*unit_cost AS estimated_request FROM inventory_needs ORDER BY id DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)
    if not df.empty:
        st.metric("Total Estimated Equipment Need", money(df["estimated_request"].fillna(0).sum()))

elif page == "NFPA / ISO / Compliance":
    st.subheader("NFPA / ISO / Compliance Reference Tracker")
    st.warning("Enter standards and requirements from authoritative sources or your agency records. The AI writer will not invent compliance requirements.")
    with st.form("comp_add", clear_on_submit=True):
        a,b,c = st.columns(3)
        framework = a.selectbox("Framework", ["NFPA","ISO","OSHA","State","County","Municipal","Medical Protocol","Other"])
        ref = b.text_input("Standard / Section / Classification")
        topic = c.text_input("Topic")
        requirement = st.text_area("Requirement / Relevance Summary")
        current = st.text_input("Current Department Status")
        gap = st.text_input("Identified Gap")
        source = st.text_input("Evidence / Source")
        reviewed = st.date_input("Last Reviewed", value=date.today())
        notes = st.text_area("Notes")
        if st.form_submit_button("Add Compliance Record"):
            execute("""
            INSERT INTO compliance_data(framework,standard_reference,topic,requirement_summary,current_status,gap,evidence_source,last_reviewed,notes)
            VALUES(?,?,?,?,?,?,?,?,?)
            """,(framework,ref,topic,requirement,current,gap,source,str(reviewed),notes))
            st.success("Compliance record added.")
    df = query_df("SELECT * FROM compliance_data ORDER BY framework, standard_reference")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Community Demographics":
    st.subheader("Community Demographics")
    st.caption("Use authoritative sources such as Census, municipal planning data, county records, or other documented sources.")
    with st.form("demo_add", clear_on_submit=True):
        a,b,c = st.columns(3)
        metric = a.text_input("Metric", placeholder="Population, age 65+, poverty rate, households, etc.")
        value = b.text_input("Value")
        geography = c.text_input("Geography")
        d,e = st.columns(2)
        year = d.text_input("Data Year")
        source = e.text_input("Source")
        verified = st.checkbox("Verified", value=True)
        notes = st.text_input("Why this matters to the grant")
        if st.form_submit_button("Add Demographic"):
            if metric and value:
                execute("INSERT INTO demographics(metric,value,geography,year,source,verified,notes) VALUES(?,?,?,?,?,?,?)",
                        (metric,value,geography,year,source,int(verified),notes))
                st.success("Demographic added.")
    df = query_df("SELECT * FROM demographics ORDER BY metric")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Grant History":
    st.subheader("Prior Grant History")
    with st.form("history_add", clear_on_submit=True):
        a,b,c = st.columns(3)
        grant_name = a.text_input("Grant Name")
        funder = b.text_input("Funder")
        year = c.number_input("Year", min_value=1900, max_value=2100, value=date.today().year)
        project = st.text_input("Project")
        a,b,c = st.columns(3)
        req = a.number_input("Amount Requested", min_value=0.0)
        award = b.number_input("Amount Awarded", min_value=0.0)
        match = c.number_input("Match", min_value=0.0)
        result = st.selectbox("Result", ["Awarded","Partially Awarded","Denied","Withdrawn","Pending","Other"])
        purpose = st.text_area("Purpose")
        feedback = st.text_area("Funder Feedback / Lessons Learned")
        closeout = st.selectbox("Closeout Complete?", ["","Yes","No","Not Applicable"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Add Grant History"):
            execute("""
            INSERT INTO grant_history(grant_name,funder,project,year,amount_requested,amount_awarded,result,match_amount,purpose,feedback,closeout_complete,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,(grant_name,funder,project,year,req,award,result,match,purpose,feedback,closeout,notes))
            st.success("Grant history added.")
    df = query_df("SELECT * FROM grant_history ORDER BY year DESC")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Grant Projects":
    st.subheader("Current Grant Projects")
    with st.form("grant_add", clear_on_submit=True):
        a,b = st.columns(2)
        grant_name = a.text_input("Grant / Program Name")
        funder = b.text_input("Funder")
        a,b,c = st.columns(3)
        deadline = a.date_input("Deadline", value=date.today())
        amount = b.number_input("Amount Requested", min_value=0.0)
        match = c.number_input("Match Amount", min_value=0.0)
        project = st.text_input("Project Name")
        summary = st.text_area("Project Summary")
        need = st.text_area("Statement of Need")
        goals = st.text_area("Goals / Objectives")
        methods = st.text_area("Implementation / Methods")
        evaluation = st.text_area("Evaluation Plan")
        sustain = st.text_area("Sustainability")
        status = st.selectbox("Status", ["Planning","Drafting","Internal Review","Submitted","Awarded","Denied","Closed"])
        notes = st.text_area("Notes")
        if st.form_submit_button("Create Grant Project", type="primary"):
            execute("""
            INSERT INTO grants(grant_name,funder,deadline,project_name,amount_requested,match_amount,project_summary,
            statement_of_need,goals,methods,evaluation,sustainability,status,notes)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,(grant_name,funder,str(deadline),project,amount,match,summary,need,goals,methods,evaluation,sustain,status,notes))
            st.success("Grant project created.")
    df = query_df("SELECT * FROM grants ORDER BY deadline")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif page == "Budget Builder":
    st.subheader("Grant Budget Builder")
    grants = query_df("SELECT id, grant_name, project_name FROM grants ORDER BY id DESC")
    if grants.empty:
        st.info("Create a grant project first.")
    else:
        options = {f"{r.id} — {r.grant_name} — {r.project_name}": str(r.id) for _,r in grants.iterrows()}
        label = st.selectbox("Grant Project", list(options.keys()))
        grant_key = options[label]
        with st.form("budget_add", clear_on_submit=True):
            a,b = st.columns(2)
            category = a.selectbox("Budget Category", ["Equipment","PPE","Apparatus","Training","Personnel","Contractual","Supplies","Technology","Construction","Travel","Other"])
            line = b.text_input("Line Item")
            a,b,c,d = st.columns(4)
            qty = a.number_input("Quantity", min_value=0.0, value=1.0)
            unit = b.number_input("Unit Cost", min_value=0.0)
            requested = c.number_input("Grant Requested", min_value=0.0)
            match = d.number_input("Local Match", min_value=0.0)
            other = st.number_input("Other Funding", min_value=0.0)
            justification = st.text_area("Budget Justification")
            if st.form_submit_button("Add Budget Line"):
                if requested == 0 and qty and unit:
                    requested = qty * unit
                execute("""
                INSERT INTO budgets(grant_key,category,line_item,qty,unit_cost,requested_amount,match_amount,other_funding,justification)
                VALUES(?,?,?,?,?,?,?,?,?)
                """,(grant_key,category,line,qty,unit,requested,match,other,justification))
                st.success("Budget line added.")
        df = query_df("SELECT * FROM budgets WHERE grant_key=? ORDER BY category,line_item",(grant_key,))
        st.dataframe(df, use_container_width=True, hide_index=True)
        if not df.empty:
            a,b,c = st.columns(3)
            a.metric("Grant Request", money(df["requested_amount"].sum()))
            b.metric("Local Match", money(df["match_amount"].sum()))
            c.metric("Other Funding", money(df["other_funding"].sum()))

elif page == "Rubric Builder":
    st.subheader("Grant Rubric Builder")
    grants = query_df("SELECT id, grant_name, project_name FROM grants ORDER BY id DESC")
    if grants.empty:
        st.info("Create a grant project first.")
    else:
        options = {f"{r.id} — {r.grant_name} — {r.project_name}": int(r.id) for _,r in grants.iterrows()}
        label = st.selectbox("Grant Project", list(options.keys()))
        gid = options[label]

        with st.form("rubric_add", clear_on_submit=True):
            a,b,c = st.columns([2,1,1])
            criterion = a.text_input("Scoring Criterion")
            weight = b.number_input("Weight %", min_value=0.0, max_value=100.0)
            max_score = c.number_input("Max Points", min_value=1.0, value=10.0)
            guidance = st.text_area("Exact Funder Guidance / Scoring Language")
            chars = st.number_input("Character Limit (0 = none)", min_value=0)
            required = st.text_area("Required Elements / Questions That Must Be Answered")
            if st.form_submit_button("Add Rubric Criterion"):
                execute("""
                INSERT INTO rubrics(grant_id,criterion,weight,max_score,funder_guidance,character_limit,required_elements)
                VALUES(?,?,?,?,?,?,?)
                """,(gid,criterion,weight,max_score,guidance,chars,required))
                st.success("Rubric criterion added.")

        df = query_df("SELECT * FROM rubrics WHERE grant_id=? ORDER BY id",(gid,))
        st.dataframe(df, use_container_width=True, hide_index=True)
        if not df.empty:
            st.metric("Total Rubric Weight", f"{df['weight'].sum():.1f}%")
            if abs(df["weight"].sum()-100) > .01:
                st.warning("Rubric weights do not total 100%.")

elif page == "AI Grant Writer":
    st.subheader("AI Grant Writer")
    st.write("Creates a complete Fire/EMS grant working draft using the selected grant rubric and your stored department data.")

    grants = query_df("SELECT id, grant_name, project_name, funder FROM grants ORDER BY id DESC")
    if grants.empty:
        st.info("Create a grant project first.")
    else:
        options = {f"{r.id} — {r.grant_name} — {r.project_name}": int(r.id) for _,r in grants.iterrows()}
        label = st.selectbox("Grant Project", list(options.keys()))
        gid = options[label]

        context = build_context(gid)
        rubric = context["rubric"]

        if not rubric:
            st.warning("This grant does not have a rubric yet. Add the funder's scoring rubric before generating the draft.")

        st.markdown("### AI Configuration")
        st.caption("Your API key is used only for this running app session unless you configure it as a deployment secret.")
        api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY",""))
        model = st.selectbox("Model", ["gpt-5.6", "gpt-5.6-terra", "gpt-5.6-luna"], index=1)

        with st.expander("Review the data that will be provided to the AI"):
            st.json(context)

        if st.button("Generate Complete Grant Draft", type="primary", disabled=not bool(rubric)):
            if not api_key:
                st.error("Enter an OpenAI API key or configure OPENAI_API_KEY.")
            else:
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key)
                    prompt = build_ai_prompt(context)
                    with st.spinner("Generating rubric-driven grant draft..."):
                        response = client.responses.create(
                            model=model,
                            input=prompt,
                        )
                    draft = response.output_text
                    execute("INSERT INTO ai_drafts(grant_id,model,content) VALUES(?,?,?)",(gid,model,draft))
                    st.session_state["latest_draft"] = draft
                    st.success("Draft generated and saved.")
                except Exception as e:
                    st.error(f"AI generation failed: {e}")

        drafts = query_df("SELECT id, created_at, model, content FROM ai_drafts WHERE grant_id=? ORDER BY id DESC",(gid,))
        if "latest_draft" in st.session_state:
            st.markdown("### Latest Draft")
            st.markdown(st.session_state["latest_draft"])
            st.download_button(
                "Download Latest Draft (.md)",
                st.session_state["latest_draft"],
                file_name="fire_ems_grant_draft.md",
                mime="text/markdown"
            )
        elif not drafts.empty:
            st.markdown("### Most Recent Saved Draft")
            st.markdown(drafts.iloc[0]["content"])
            st.download_button(
                "Download Most Recent Draft (.md)",
                drafts.iloc[0]["content"],
                file_name="fire_ems_grant_draft.md",
                mime="text/markdown"
            )

elif page == "Data Export":
    st.subheader("Export / Backup")
    st.write("Download department data as CSV files or back up the SQLite database.")

    tables = [
        "department_profile","department_statistics","call_volume","inventory_needs",
        "compliance_data","demographics","grant_history","budgets","grants","rubrics","ai_drafts"
    ]
    selected = st.selectbox("Table", tables)
    df = query_df(f"SELECT * FROM {selected}")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        f"Download {selected}.csv",
        df.to_csv(index=False).encode("utf-8"),
        file_name=f"{selected}.csv",
        mime="text/csv"
    )

    if os.path.exists(DB_PATH):
        with open(DB_PATH, "rb") as f:
            st.download_button(
                "Download Complete Database Backup",
                f.read(),
                file_name="fire_ems_grants_backup.db",
                mime="application/octet-stream"
            )

st.divider()
st.caption(
    "Fire/EMS Grant Command Center — Always verify grant requirements, standards, costs, statistics, and final claims before submission."
)
