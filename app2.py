# Import Libraries 
import streamlit as st
import os
import re
import pandas as pd
from io import BytesIO
import hashlib
import fitz  # PyMuPDF
from docx import Document
from base64 import b64encode

# Set usename and password 
USERNAME = "Pravin"
PASSWORD = "123"

# Session State Initialization 
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "resumes" not in st.session_state:
    st.session_state.resumes = []
if "resume_hashes" not in st.session_state:
    st.session_state.resume_hashes = set()

# Background Image Function
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
    h1, h2, h3, h4, h5, h6 {{
        color: #ffffff;
    }}
    </style>
    """
    st.markdown(page_bg_img, unsafe_allow_html=True)

# Resume Parsing Utilities
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
    email_match = re.search(r"([a-zA-Z0-9._%+-]+)@[\x01-\x7f]+", text)
    if email_match:
        raw = email_match.group(1)
        parts = [p.capitalize() for p in re.split(r"[._\-]", raw) if p.isalpha()]
        if 1 <= len(parts) <= 3:
            return " ".join(parts)
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    for line in lines[:30]:
        if (2 <= len(line.split()) <= 4 and not any(char in line for char in "@0123456789") and
            not re.search(r'(developer|engineer|resume|experience|skills|certifications|project|manager|profile|summary)', line, re.IGNORECASE) and
            not re.fullmatch(r"[-_=]{4,}", line)):
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
        "Diploma": ["diploma", "polytechnic", "pg diploma", "post graduate diploma"],
        "PGDM": ["pgdm", "post graduate diploma in management"],
        "PGDE": ["pgde", "post graduate diploma in engineering"]
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
    patterns = [
        r'(\d+)\+?\s*years? of experience',
        r'(\d+)\s*years? experience',
        r'experience of (\d+)',
        r'(\d+)\s*yrs',
        r'total experience\s*[:-]?\s*(\d+)'
    ]
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
    cities = ["Pune", "Mumbai", "Delhi", "Nashik", "Sambhaji Nagar", "Jalgaon"]
    text_clean = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    for city in cities:
        if re.search(r"\b" + re.escape(city.lower()) + r"\b", text_clean):
            return city
    return "N/A"

def calculate_match_score(skills, exp_text, required_skills, min_exp):
    if skills == "N/A":
        skill_score = 0
    else:
        matched = set(s.lower() for s in skills.split(", ")) & set(r.lower() for r in required_skills)
        skill_score = (len(matched) / len(required_skills)) * 100 if required_skills else 0

    exp_years = int(re.search(r"(\d+)", exp_text).group(1)) if re.search(r"(\d+)", exp_text) else -1
    if exp_years == -1:
        exp_score = 0
    elif exp_years >= min_exp:
        exp_score = 100
    else:
        exp_score = (exp_years / min_exp) * 100 if min_exp > 0 else 0

    if skill_score == 0 and exp_score == 0:
        return 0.0

    final_score = round(0.7 * skill_score + 0.3 * exp_score, 2)
    return final_score

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

# Login Page 
def login():
    add_background(r"D:/Resume Shorrtlisted Project/Images/background4.jpg") 
    
    logo_path = "D:/Resume Shorrtlisted Project/Images/logo.png"

    st.markdown(
    f"""
    <div style='text-align: center;'>
        <img src='data:image/png;base64,{b64encode(open("D:/Resume Shorrtlisted Project/Images/logo.png", "rb").read()).decode()}' width='100'/>
    </div>
    """,
    unsafe_allow_html=True
)

    st.markdown("""
    <h1 style='text-align: center; color: white;'>HR Login</h1>
    <style>
    .custom-input-box input {
        width: 250px !important;
        font-size: 18px !important;
        padding: 6px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<div class='custom-input-box'>", unsafe_allow_html=True)
        username = st.text_input("Username", key="username_input")
        password = st.text_input("Password", type="password", key="password_input")
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Login"):
            if username == USERNAME and password == PASSWORD:
                st.session_state.logged_in = True
            else:
                st.error("Invalid credentials")

# Dashboard Page 
def dashboard():
    add_background("D:/Resume Shorrtlisted Project/Images/background2.avif")
    st.title("Resume Shortlisting Tool")

    with st.sidebar:
        st.header("Candidate Filters")
        skills_input = st.text_input("Required Skills", "Python, Power BI")
        required_skills = [s.strip() for s in skills_input.split(",") if s.strip()]
        min_exp = st.number_input("Minimum Experience (Years)", min_value=0, max_value=20, value=0, step=1)
        min_score_ui = st.slider("Minimum Match Score", 0, 100, 50)
        city_filter_placeholder = st.empty()
    
    #File uploader
    st.subheader("Upload Files (PDF, DOCX, TXT, CSV)")
    uploaded_files = st.file_uploader("Upload files", type=["pdf", "docx", "txt", "csv"], accept_multiple_files=True)

    if uploaded_files:
        for single_file in uploaded_files:
            file_bytes = single_file.read()
            ext = single_file.name.split('.')[-1].lower()
            if ext in ["pdf", "docx", "txt"]:
                result = process_resume(single_file.name, file_bytes, required_skills, min_exp)
                if result:
                    st.session_state.resumes.append(result)
                    st.success(f"Resume '{single_file.name}' uploaded and processed.")
            elif ext == "csv":
                st.subheader(f"CSV Preview: {single_file.name}")
                st.dataframe(pd.read_csv(BytesIO(file_bytes)))

    #Path uploader
    st.markdown("### Upload Resumes from Folder Path")
    folder_path = st.text_input("Resume Folder Path", "D:/Resumes/")
    if st.button("Process Resumes") and os.path.isdir(folder_path):
        files = [(f, open(os.path.join(folder_path, f), 'rb').read())
                 for f in os.listdir(folder_path)
                 if f.lower().endswith(('pdf', 'docx', 'txt'))]
        with st.spinner(f"Processing {len(files)} resumes..."):
            new = 0
            for name, content in files:
                result = process_resume(name, content, required_skills, min_exp)
                if result:
                    st.session_state.resumes.append(result)
                    new += 1
        st.success(f"{new} resumes processed from folder.")

    if st.session_state.resumes:
        df = pd.DataFrame(st.session_state.resumes)
        df["Experience (Years)"] = df["Experience"].apply(exp_to_int)
        cities = ["All"] + sorted(df["City"].dropna().unique().tolist())
        selected_city = city_filter_placeholder.selectbox("Filter by City", cities)

        filtered = df[
            (df["Match Score"] >= min_score_ui) &
            (df["Skills"] != "N/A") &
            (df["Experience (Years)"] >= min_exp)
        ]
        if selected_city != "All":
            filtered = filtered[filtered["City"] == selected_city]

        if not filtered.empty:
            filtered.insert(0, "S.No", range(1, len(filtered) + 1))

        st.markdown("### Shortlisted Candidates")
        st.dataframe(filtered)
        st.download_button("Download CSV", filtered.to_csv(index=False), "shortlisted_candidates.csv")

    if st.button("Clear All"):
        st.session_state.resumes.clear()
        st.session_state.resume_hashes.clear()
        st.success("All uploaded and processed data cleared.")

#  Main
if not st.session_state.logged_in:
    login()
else:
    dashboard()
