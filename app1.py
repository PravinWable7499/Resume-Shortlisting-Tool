# ---------------- Import Libraries ----------------
import streamlit as st
import os
import re
import pandas as pd
from io import BytesIO
import hashlib
import fitz  # PyMuPDF
from docx import Document
from base64 import b64encode
import matplotlib.pyplot as plt

# ---------------- Session Initialization ----------------
USERNAME = "Pravin"
PASSWORD = "123"

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "resumes" not in st.session_state:
    st.session_state.resumes = []
if "resume_hashes" not in st.session_state:
    st.session_state.resume_hashes = set()
if "page" not in st.session_state:
    st.session_state.page = "Overview"
if "skills_input" not in st.session_state:
    st.session_state.skills_input = "Python, Power BI"
if "min_exp" not in st.session_state:
    st.session_state.min_exp = 0
if "min_score" not in st.session_state:
    st.session_state.min_score = 50
if "city_filter" not in st.session_state:
    st.session_state.city_filter = "All"

# ---------------- Background Image ----------------
def add_background(image_path):
    with open(image_path, "rb") as image_file:
        encoded = b64encode(image_file.read()).decode()
    page_bg_img = f"""
    <style>
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        color: white;
    }}
    .stTextInput > div > label, .stSelectbox > div > label {{
        color: #ffffff !important;  
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

# ---------------- Sidebar Navigation ----------------
# ---------------- Sidebar Navigation with Visuals Page ----------------
def sidebar_navigation():
    st.sidebar.markdown("""
        <style>
        .menu-header {
            color: white;
            font-size: 22px;
            margin-bottom: 20px;
        }

        .sidebar-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .sidebar-button {
            display: flex;
            align-items: center;
            padding: 12px 18px;
            border: none;
            border-radius: 10px;
            background: linear-gradient(145deg, #3a3f47, #2c313a);
            box-shadow: 2px 2px 5px #1e2228, -2px -2px 5px #3c424c;
            color: white;
            font-size: 16px;
            transition: all 0.2s ease-in-out;
        }

        .sidebar-button:hover {
            background: #57606f;
            transform: scale(1.02);
            box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
        }

        .sidebar-button img {
            width: 22px;
            margin-right: 12px;
        }
        </style>
    """, unsafe_allow_html=True)



    st.sidebar.markdown("<div class='menu-header'>📋 Menu</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-container'>", unsafe_allow_html=True)

    if st.sidebar.button("📁 Overview", key="overview"):
        st.session_state.page = "Overview"

    if st.sidebar.button("📊 Dashboard", key="dashboard"):
        st.session_state.page = "Dashboard"

    if st.sidebar.button("🧮 Visuals", key="visuals"):
        st.session_state.page = "Visuals"

    st.sidebar.markdown("</div>", unsafe_allow_html=True)

# ---------------- Resume Extraction Functions ----------------
def read_resume(file_bytes, extension):
    try:
        if extension == "pdf":
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            return " ".join([page.get_text() for page in doc])
        elif extension == "docx":
            doc = Document(BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs])
        elif extension == "txt":
            return file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        return ""
    return ""

def extract_name(text):
    email_match = re.search(r"([a-zA-Z0-9._%+-]+)@[^\s]+", text)
    if email_match:
        raw = email_match.group(1)
        parts = [p.capitalize() for p in re.split(r"[._\-]", raw) if p.isalpha()]
        if 1 <= len(parts) <= 3:
            return " ".join(parts)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:30]:
        if (2 <= len(line.split()) <= 4 and not any(char in line for char in "@0123456789") and
            not re.search(r'(developer|engineer|resume|experience|skills|certifications|project|manager|profile|summary)', line, re.IGNORECASE)):
            return line.strip()
    return "N/A"

def extract_email(text):
    match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
    return match.group(0) if match else "N/A"

def extract_phone(text):
    pattern = r"(?:\+91[\s-]*)?(?:\(?[6-9]\d{2}\)?[-\s]?\d{3}[-\s]?\d{4})"
    matches = re.findall(pattern, text)
    for match in matches:
        clean = re.sub(r"[^0-9]", "", match)
        if len(clean) >= 10:
            return clean[-10:]
    return "N/A"

def extract_education(text):
    degree_map = {
        "SSC": ["ssc", "secondary school certificate", "10th", "matric"],
        "HSC": ["hsc", "higher secondary certificate", "12th", "intermediate"],
        "B.E": ["bachelor of engineering", "b.e", "be"],
        "B.Tech": ["bachelor of technology", "b.tech", "btech"],
        "M.Tech": ["master of technology", "m.tech", "mtech"],
        "MBA": ["master of business administration", "mba"],
        "B.Sc": ["bachelor of science", "b.sc", "bsc"],
        "M.Sc": ["master of science", "m.sc", "msc"],
        "BA": ["bachelor of arts", "ba"],
        "MA": ["master of arts", "ma"],
        "MCA": ["master of computer applications", "mca"],
        "BCA": ["bachelor of computer applications", "bca"],
        "Ph.D": ["doctor of philosophy", "ph.d", "phd"],
        "Diploma": ["diploma", "polytechnic"],
        "PGDM": ["pgdm", "post graduate diploma in management"]
    }
    text_lower = text.lower()
    found = []
    for short, keywords in degree_map.items():
        for keyword in keywords:
            if re.search(rf"\b{re.escape(keyword)}\b", text_lower):
                found.append(f"{short} ({keyword.title()})")
                break
    return ", ".join(sorted(set(found))) if found else "N/A"

def extract_skills(text, required_skills):
    text = re.sub(r"[^a-zA-Z0-9\s,]", " ", text.lower())
    return ", ".join([skill for skill in required_skills if re.search(rf'\b{skill.lower()}\b', text)]) or "N/A"

def extract_experience(text):
    patterns = [r'(\d+)\+?\s*years? of experience', r'(\d+)\s*years? experience', r'experience of (\d+)', r'(\d+)\s*yrs']
    for p in patterns:
        match = re.search(p, text.lower())
        if match:
            return f"{match.group(1)} years"
    return "N/A"

def extract_certifications(text):
    lines = [line.strip() for line in text.split('\n') if 'certificat' in line.lower()]
    cleaned = [re.sub(r"[^a-zA-Z0-9., ]", "", line) for line in lines]
    return ", ".join(cleaned) if cleaned else "N/A"

def extract_city(text):
    cities = [
        "Pune", "Mumbai", "Delhi", "Nashik", "Sambhaji Nagar", "Jalgaon",
        "Hyderabad", "Bangalore", "Chennai", "Kolkata", "Ahmedabad", "Nagpur",
        "Thane", "Indore", "Bhopal", "Surat", "Vadodara", "Rajkot", "Lucknow",
        "Noida", "Gurgaon", "Faridabad", "Chandigarh", "Patna", "Jaipur", "Kanpur",
        "Coimbatore", "Vijayawada", "Visakhapatnam", "Amritsar", "Ludhiana", "Ranchi",
        "Agra", "Varanasi", "Mysore", "Hubli", "Mangalore", "Nanded", "Aurangabad",
        "Akola", "Solapur", "Kolhapur", "Satara", "Sangli", "Navi Mumbai", "Panvel"
    ]
    
    text_clean = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    for city in cities:
        if re.search(r"\b" + re.escape(city.lower()) + r"\b", text_clean):
            return city
    return "N/A"


def calculate_match_score(skills, exp_text, required_skills, min_exp):
    matched = set(s.lower() for s in skills.split(", ")) & set(r.lower() for r in required_skills)
    skill_score = (len(matched) / len(required_skills)) * 100 if required_skills else 0
    exp_years = int(re.search(r"(\d+)", exp_text).group(1)) if re.search(r"(\d+)", exp_text) else 0
    exp_score = 100 if exp_years >= min_exp else (exp_years / min_exp) * 100 if min_exp > 0 else 0
    return round(0.7 * skill_score + 0.3 * exp_score, 2)

def process_resume(file_name, file_bytes, required_skills, min_exp):
    ext = file_name.split('.')[-1].lower()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    if file_hash in st.session_state.resume_hashes:
        return None
    st.session_state.resume_hashes.add(file_hash)
    text = read_resume(file_bytes, ext)
    return {
        "Name": extract_name(text),
        "Email": extract_email(text),
        "Phone": extract_phone(text),
        "Education": extract_education(text),
        "Skills": extract_skills(text, required_skills),
        "Experience": extract_experience(text),
        "Certifications": extract_certifications(text),
        "City": extract_city(text),
        "Match Score": calculate_match_score(
            extract_skills(text, required_skills),
            extract_experience(text),
            required_skills,
            min_exp
        )
    }

def exp_to_int(exp_str):
    match = re.search(r"(\d+)", exp_str)
    return int(match.group(1)) if match else 0

def overview_page():
    add_background("D:/Resume Shorrtlisted Project/Images/background2.avif")
    st.markdown("""<h1 style='text-align: center; color: black;'>Upload Resumes</h1>""", unsafe_allow_html=True)
    uploaded_files = st.file_uploader("Upload Resumes", type=["pdf", "docx", "txt"], accept_multiple_files=True)

    required_skills = [s.strip().lower() for s in st.session_state.skills_input.split(",")]
    min_exp = st.session_state.min_exp

    if uploaded_files:
        for file in uploaded_files:
            file_bytes = file.read()
            result = process_resume(file.name, file_bytes, required_skills, min_exp)
            if result:
                st.session_state.resumes.append(result)
                st.success(f"{file.name} processed.")

    
    # ---------- Title ----------
    st.markdown("<h3 style='margin-bottom: 0; color: Black;'>Upload Resumes from Folder</h3>", unsafe_allow_html=True)

    # ---------- Input ----------
    folder_path = st.text_input("Folder Path", "D:/Resumes/")


    # ---------------- Global Button Styling ----------------
    st.markdown("""
        <style>
        div.stButton > button:first-child {
            background-color: #A0522D !important;
            color: white !important;
            height: 3em;
            width: 10em;
            border-radius: 7px;
            margin-top: 10px;
            border: none;
            font-weight: bold;
        }

        div.stButton > button:hover {
            background-color: #8B4513 !important;
            transform: scale(1.02);
            cursor: pointer;
        }
        </style>
    """, unsafe_allow_html=True)


    # ---------- Button Logic ----------
    if st.button("Process Folder"):
        if os.path.isdir(folder_path):
            files = [(f, open(os.path.join(folder_path, f), 'rb').read())
                    for f in os.listdir(folder_path) if f.lower().endswith(('pdf', 'docx', 'txt'))]
            with st.spinner("Processing folder..."):
                new = 0
                for name, content in files:
                    result = process_resume(name, content, required_skills, min_exp)
                    if result:
                        st.session_state.resumes.append(result)
                        new += 1
                st.success(f"{new} resumes processed from folder.")
        else:
            st.error("Invalid folder path. Please check the path and try again.")


def dashboard_page():
    add_background("D:/Resume Shorrtlisted Project/Images/background2.avif")
    st.markdown("""<h1 style='text-align: center; color: black;'>Resume Shortlisting Dashboard</h1>""", unsafe_allow_html=True)

    if not st.session_state.resumes:
        st.warning("No resumes uploaded yet. Please upload resumes from Overview page.")
        return

    df = pd.DataFrame(st.session_state.resumes)
    df["Experience (Years)"] = df["Experience"].apply(exp_to_int)

    required_skills = [s.strip().lower() for s in st.session_state.skills_input.split(",")]

    filtered = df[
        (df["Match Score"] >= st.session_state.min_score) &
        (df["Skills"] != "N/A") &
        (df["Experience (Years)"] >= st.session_state.min_exp)
    ]
    if st.session_state.city_filter != "All":
        filtered = filtered[filtered["City"] == st.session_state.city_filter]

    left_col, right_col = st.columns([1, 3], gap="large")

    with left_col:
        st.markdown("<h4 style='color: Black;'>🎯 Candidate Filters</h4>", unsafe_allow_html=True)
        st.session_state.skills_input = st.text_input("Required Skills", st.session_state.skills_input)
        st.session_state.min_exp = st.number_input("Min Experience", 0, 20, st.session_state.min_exp)
        st.session_state.min_score = st.slider("Min Match Score", 0, 100, st.session_state.min_score)
        st.session_state.city_filter = st.selectbox("City", ["All", "Pune", "Mumbai", "Delhi", "Nashik", "Sambhaji Nagar", "Jalgaon"],
                                                    index=["All", "Pune", "Mumbai", "Delhi", "Nashik", "Sambhaji Nagar", "Jalgaon"].index(st.session_state.city_filter))

    with right_col:
        if not filtered.empty:
            filtered.insert(0, "S.No", range(1, len(filtered) + 1))
            st.markdown("#### ✅ Shortlisted Candidates")
            st.dataframe(filtered, use_container_width=True)
            st.download_button("📥 Download CSV", filtered.to_csv(index=False), "shortlisted_candidates.csv")
        else:
            st.info("No candidates matched the filters.")

def visuals_page():
    add_background("D:/Resume Shorrtlisted Project/Images/background2.avif")

    if not st.session_state.resumes:
        st.warning("No resumes uploaded yet. Please upload resumes from Overview page.")
        return

    df = pd.DataFrame(st.session_state.resumes)
    df["Experience (Years)"] = df["Experience"].apply(exp_to_int)

    filtered = df[
        (df["Match Score"] >= st.session_state.min_score) &
        (df["Skills"] != "N/A") &
        (df["Experience (Years)"] >= st.session_state.min_exp)
    ]
    if st.session_state.city_filter != "All":
        filtered = filtered[filtered["City"] == st.session_state.city_filter]

    if filtered.empty:
        st.info("No data to visualize. Try changing filters on Dashboard.")
        return
    # ---------------- Charts Section ----------------
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("##### City-wise Count")
        city_counts = filtered["City"].value_counts()
        fig1, ax1 = plt.subplots(figsize=(5, 2))
        ax1.bar(city_counts.index, city_counts.values, color='Coral')
        ax1.set_ylabel("Count", fontsize=7)
        ax1.set_xlabel("City", fontsize=7)
        ax1.set_title("Candidates per City", fontsize=6)
        ax1.set_facecolor("none")
        fig1.patch.set_facecolor('none')
        ax1.tick_params(colors='black', labelsize=7)
        ax1.xaxis.label.set_color('black')
        ax1.yaxis.label.set_color('black')
        ax1.title.set_color('black')
        st.pyplot(fig1)

    with chart_col2:
        st.markdown("##### Top Skills")
        all_skills = [skill.strip().title() for sublist in filtered["Skills"].dropna().str.split(",") for skill in sublist if skill.strip()]
        skill_series = pd.Series(all_skills).value_counts().head(8)
        fig2, ax2 = plt.subplots(figsize=(6, 2))
        wedges, texts, autotexts = ax2.pie(skill_series, labels=skill_series.index, autopct='%1.1f%%', startangle=140)
        ax2.axis('equal')
        fig2.patch.set_facecolor('none')
        for text in texts:
            text.set_color('black')
            text.set_fontsize(6)
        for autotext in autotexts:
            autotext.set_color('black')
            autotext.set_fontsize(6)
        st.pyplot(fig2)

    chart_col3, chart_col4 = st.columns(2)

    with chart_col3:
        st.markdown("##### Match Score Distribution")
        fig3, ax3 = plt.subplots(figsize=(5, 2))
        counts, bins, patches = ax3.hist(filtered["Match Score"], bins=10, color='LightCoral')

        ax3.set_xlabel("Match Score", fontsize=6)
        ax3.set_ylabel("Candidates", fontsize=6)
        ax3.set_title("Score Distribution", fontsize=6)
        ax3.set_facecolor("none")
        fig3.patch.set_facecolor('none')

        ax3.tick_params(colors='black', labelsize=6)  # Smaller tick labels
        ax3.xaxis.label.set_color('black')
        ax3.yaxis.label.set_color('black')
        ax3.title.set_color('black')

        # Add smaller value labels on top of each bar
        for rect, count in zip(patches, counts):
            height = rect.get_height()
            if height > 0:
                ax3.text(rect.get_x() + rect.get_width() / 2, height + 0.5, int(count),
                        ha='center', va='bottom', fontsize=6, color='white')  # Smaller fontsize

        st.pyplot(fig3)


    with chart_col4:
        st.markdown("##### Education Levels")
        edu_counts = filtered["Education"].value_counts().head(8)
        fig4, ax4 = plt.subplots(figsize=(4, 3))
        ax4.barh(edu_counts.index, edu_counts.values, color='Crimson')
        ax4.set_xlabel("Count")
        ax4.set_title("Top Education", fontsize=8)
        ax4.set_facecolor("none")
        fig4.patch.set_facecolor('none')
        ax4.tick_params(colors='black')
        ax4.xaxis.label.set_color('black')
        ax4.yaxis.label.set_color('black')
        ax4.title.set_color('black')
        st.pyplot(fig4)

if not st.session_state.logged_in:
    add_background("D:/Resume Shorrtlisted Project/Images/background4.jpg")
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{b64encode(open("D:/Resume Shorrtlisted Project/Images/logo.png", "rb").read()).decode()}' width='100'/>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white;'>HR Login</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
            else:
                st.error("Invalid credentials")
else:
    sidebar_navigation()
    if st.session_state.page == "Overview":
        overview_page()
    elif st.session_state.page == "Dashboard":
        dashboard_page()
    elif st.session_state.page == "Visuals":
        visuals_page()

 