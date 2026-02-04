from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session, flash
from PyPDF2 import PdfReader
import re, os, io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from deep_translator import GoogleTranslator
import json   # <<< added >>>
from datetime import datetime   # <<< added >>>
from transformers import pipeline
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch


import requests
from bs4 import BeautifulSoup

app = Flask(__name__)
app.secret_key = "12345"

# ----------------- History Storage -----------------  <<< added >>>
HISTORY_FILE = "history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(data):
    with open(HISTORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def add_history(entry):
    history = load_history()
    history.append(entry)
    save_history(history)



# ----------------- Helper: Summarization -----------------
summarizer = pipeline("summarization", model="t5-small", tokenizer="t5-small")
# ----------------- QA Model -----------------
qa_pipeline = pipeline("question-answering", model="deepset/roberta-base-squad2")

# ===============================
# Extract text from uploaded PDF
# ===============================
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

# ===============================
# AI-based Summarization
# ===============================
def summarize_text(text, max_len=150, min_len=50):
    # Break text into chunks (T5 works best on <= 1000 tokens)
    chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
    result = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=max_len, min_length=min_len, do_sample=False)
        result.append(summary[0]['summary_text'])
    return " ".join(result)

# ----------------- Helper: Case Nature -----------------
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

# ----------------- Improved Case Nature -----------------
def detect_case_nature(text):
    text_lower = text.lower()

    keyword_sets = {
        "Criminal Case": ["murder","homicide","theft","robbery","assault","fraud","kidnapping","violence","police","crime","rape","cybercrime","section 302","section 420"],
        "Family Case": ["divorce","marriage","custody","alimony","dowry","domestic","family dispute"],
        "Property Case": ["land","property","ownership","lease","possession","eviction","real estate","tenant","encroachment"],
        "Contract Case": ["contract","agreement","breach","business","partnership","liability","obligation"],
        "Environmental Case": ["environment","pollution","forest","waste","ecology","climate","emission","sustainability"]
    }

    scores = {case:0 for case in keyword_sets}
    for case, keywords in keyword_sets.items():
        for word in keywords:
            scores[case] += text_lower.count(word)

    # if any keyword found, pick the highest
    best_match = max(scores, key=scores.get)
    if scores[best_match] > 0:
        return best_match

    # else fall back to AI
    labels = list(keyword_sets.keys()) + ["Civil Case"]
    result = classifier(text, candidate_labels=labels)
    return result["labels"][0]

# ----------------- Helper: Risk Score -----------------
def calculate_risk_score(text):
    score = 0
    text_lower = text.lower()
    if any(word in text_lower for word in ["murder", "theft", "fraud", "assault"]):
        score += 70
    if any(word in text_lower for word in ["divorce", "custody", "dowry"]):
        score += 40
    if any(word in text_lower for word in ["land", "property", "possession"]):
        score += 30
    if any(word in text_lower for word in ["contract", "agreement", "breach"]):
        score += 20
    if "pollution" in text_lower or "environment" in text_lower:
        score += 25
    return min(score, 100)

# ----------------- Login -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name")
        gmail = request.form.get("gmail")
        password = request.form.get("password")
        session["user"] = name or gmail

        # <<< added >>> Save login event
        add_history({
            "name": name,
            "email": gmail,
            "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "logout_time": None,
            "feedback": None,
            "rating": None
        })

        return redirect(url_for("home"))
    return render_template("login.html")

# ----------------- Logout with Rating -----------------
@app.route("/logout")
def logout():
    if "user" in session:
        history = load_history()
        if history:
            history[-1]["logout_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")   # <<< added >>>
            save_history(history)   # <<< added >>>
    session.pop("user", None)
    return redirect(url_for("rating"))

@app.route("/rating", methods=["GET", "POST"])
def rating():
    if request.method == "POST":
        stars = request.form.get("stars")

        # <<< added >>> Save rating
        history = load_history()
        if history:
            history[-1]["rating"] = stars
            save_history(history)

        flash(f"Thanks for rating us {stars} ⭐")
        return redirect(url_for("welcome"))
    return render_template("rating.html", datetime=datetime)

# ----------------- Basic Pages -----------------
@app.route("/home")
def home():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("home.html")

@app.route("/find_lawyer", methods=["GET", "POST"])
def find_lawyer():
    lawyers = []
    if request.method == "POST":
        city = request.form.get("city", "").strip().lower()
        specialization = request.form.get("specialization", "").strip().lower()

        with open("data/lawyer.json", "r") as f:
            all_lawyers = json.load(f)

        lawyers = [
            l for l in all_lawyers
            if l["city"].lower() == city and l["specialization"].lower() == specialization
        ]

    return render_template("find_lawyer.html", lawyers=lawyers)

@app.route("/about")
def about():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("about.html")

@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if "user" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        fb = request.form.get("feedback")

        # <<< added >>> Save feedback
        history = load_history()
        if history:
            history[-1]["feedback"] = fb
            save_history(history)

        return render_template("feedback.html", success=True, name=name)
    return render_template("feedback.html", success=False)

# ----------------- Analyzer -----------------
@app.route("/analyze", methods=["GET"])
def analyze_page():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("index.html")

# ----------------- Legal Insights Helper -----------------
def get_legal_insights(text, case_nature):
    data = {
        "Criminal Case": {
            "ipc_sections": [
                "IPC 302 – Murder",
                "IPC 376 – Sexual Offences",
                "IPC 420 – Cheating"
            ],
            "remedies": [
                "File FIR at nearest police station",
                "Apply for anticipatory bail",
                "Consult a criminal defense lawyer"
            ],
            "lawyers": [
                "Rajesh Kumar – Criminal Lawyer, Delhi (📞 +91-9876543210)",
                "Anita Sharma – High Court Criminal Lawyer, Mumbai (📞 +91-9123456780)"
            ]
        },
        "Family Case": {
            "ipc_sections": [
                "HMA 13 – Divorce Grounds",
                "DV Act 2005 – Domestic Violence"
            ],
            "remedies": [
                "File for divorce or maintenance",
                "Seek protection order under DV Act"
            ],
            "lawyers": [
                "Ritu Mehra – Family Law Expert, Pune (📞 +91-9090909090)",
                "Sameer Patel – Family Court Lawyer, Ahmedabad (📞 +91-8787878787)"
            ]
        },
        "Property Case": {
            "ipc_sections": [
                "Transfer of Property Act 1882",
                "Registration Act 1908"
            ],
            "remedies": [
                "Verify title deed and ownership",
                "File a civil property suit in court"
            ],
            "lawyers": [
                "Nisha Singh – Property Lawyer, Chennai (📞 +91-9345678901)",
                "Arun Kumar – Real Estate Legal Advisor, Delhi (📞 +91-9812345678)"
            ]
        },
        "Contract Case": {
            "ipc_sections": [
                "Indian Contract Act 1872",
                "Specific Relief Act 1963"
            ],
            "remedies": [
                "Send a legal notice to the other party",
                "File a breach of contract suit"
            ],
            "lawyers": [
                "Manish Rao – Business Lawyer, Hyderabad (📞 +91-9999988888)"
            ]
        },
        "Environmental Case": {
            "ipc_sections": [
                "Environment Protection Act 1986",
                "Water (Prevention and Control of Pollution) Act 1974"
            ],
            "remedies": [
                "File complaint to Pollution Control Board",
                "Approach National Green Tribunal (NGT)"
            ],
            "lawyers": [
                "Neha Gupta – Environmental Lawyer, Bengaluru (📞 +91-9012345678)"
            ]
        }
    }

    default = {
        "ipc_sections": ["No specific IPC sections found."],
        "remedies": ["No direct remedies detected."],
        "lawyers": ["No lawyer recommendation available."]
    }

    return data.get(case_nature, default)


@app.route("/analyze", methods=["POST"])
def analyze_file():
    if "user" not in session:
        return redirect(url_for("login"))

    uploaded_file = request.files.get("file")
    if not uploaded_file:
        return "No file uploaded", 400

    text = ""
    try:
        reader = PdfReader(uploaded_file)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception:
        try:
            text = uploaded_file.read().decode("utf-8")
        except Exception:
            return jsonify({"error": "Could not read file"}), 500

    if not text.strip():
        return jsonify({"error": "No text extracted"}), 400

    summary = summarize_text(text)
    case_nature = detect_case_nature(text)
    risk_score = calculate_risk_score(text)

    if "Criminal" in case_nature:
        punishments = "Possible punishments: Fine, Imprisonment"
    elif "Family" in case_nature:
        punishments = "Possible punishments: Custody changes, Divorce settlement"
    elif "Property" in case_nature:
        punishments = "Possible punishments: Property seizure, Compensation"
    elif "Contract" in case_nature:
        punishments = "Possible punishments: Monetary damages, Contract termination"
    elif "Environmental" in case_nature:
        punishments = "Possible punishments: Fines, License cancellation"
    else:
        punishments = "Not determined"

   


    insights = get_legal_insights(text, case_nature)

    return jsonify({
    "summary": summary,
    "case_nature": case_nature,
    "risk_score": risk_score,
    "punishments": punishments,
    "ipc_sections": insights["ipc_sections"],
    "remedies": insights["remedies"],
    "lawyers": insights["lawyers"],
    
})

# ----------------- Helper: Find Similar Judgements -----------------

# ----------------- Translation -----------------
# ----------------- Translation -----------------
@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    target = data.get("target_lang") or data.get("language") or "en"
    
    # Map full language names to ISO codes
    lang_map = {
        "Hindi": "hi",
        "Kannada": "kn",
        "Telugu": "te",
        "Tamil": "ta",
        "Marathi": "mr",
        "Gujarati": "gu",
        "Bengali": "bn",
        "English": "en"
    }
    
    # Fix the target if user sent a name instead of code
    target = lang_map.get(target, target)
    
    if not text:
        return jsonify({"error": "No text provided for translation"}), 400
    
    try:
        translated = GoogleTranslator(source="auto", target=target).translate(text)
        return jsonify({"translated_text": translated})
    except Exception as e:
        return jsonify({"error": f"Translation failed: {str(e)}"}), 500

# ----------------- Chatbot -----------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json(force=True, silent=True) or {}
    question = data.get("question", "").strip()
    text = data.get("text", "")

    if not question or not text:
        return jsonify({"answer": "Please provide both a question and document text."})

    # Rule-based quick answers (fast)
    q_lower = question.lower()
    if "summary" in q_lower:
        return jsonify({"answer": summarize_text(text)})
    elif "case" in q_lower:
        return jsonify({"answer": f"Case nature: {detect_case_nature(text)}"})
    elif "risk" in q_lower:
        return jsonify({"answer": f"Estimated risk score: {calculate_risk_score(text)}"})
    elif "punishment" in q_lower:
        return jsonify({"answer": "Punishments are based on case type. Try asking about the case nature first."})

    # Otherwise → use QA model
    try:
        result = qa_pipeline(question=question, context=text)
        answer = result.get("answer", "Sorry, I couldn’t find an answer in the document.")
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"answer": f"Error during Q&A: {str(e)}"})


# ----------------- Download PDF -----------------

@app.route("/download-pdf", methods=["POST"])
def download_pdf():
    data = request.json

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=60,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom heading style
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#2a5298"),
        fontSize=15,
        spaceAfter=10
    )

    # Normal text style
    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["BodyText"],
        fontSize=11,
        leading=14,
    )

    # Title style
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Title"],
        textColor=colors.HexColor("#0d47a1"),
        fontSize=22,
        alignment=1
    )

    # List of content
    content = []

    # Title
    content.append(Paragraph("⚖ Legal Document Analysis Report", title_style))
    content.append(Spacer(1, 0.3 * inch))

    # Helper to add section blocks
    def add_section(title, text):
        content.append(Paragraph(title, heading_style))
        safe_text = text.replace("\n", "<br/>")
        content.append(Paragraph(safe_text, body_style))
        content.append(Spacer(1, 0.2 * inch))

    # Add all sections
    add_section("📄 Summary", data.get("summary", ""))
    add_section("📌 Case Nature", data.get("case_nature", ""))
    add_section("⚠ Risk Score", data.get("risk_score", ""))
    add_section("🔒 Possible Punishments", data.get("punishments", ""))
    add_section("⚖ Relevant IPC Sections", data.get("ipc_sections", ""))
    add_section("🩺 Legal Remedies", data.get("remedies", ""))
    add_section("👩‍⚖ Recommended Lawyers", data.get("lawyers", ""))
    

    # Build PDF
    doc.build(content)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="Legal_Report.pdf",
        mimetype="application/pdf"
    )
# ----------------- Welcome Page -----------------
@app.route('/')
def welcome():
    return render_template("welcome.html", datetime=datetime)

# ----------------- Admin Login -----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        if name == "santosh" and email == "santubambalwadi@gmail.com" and password == "359364":
            data = load_history()[::-1]   # <<< added >>>
            return render_template("admin_dashboard.html", data=data)   # <<< added >>>
        else:
            return render_template("admin_login.html", error="Invalid credentials!")
    return render_template("admin_login.html")

@app.route('/logout_admin')
def logout_admin():
    # Just clear session (if you’re using session)
    session.clear()
    return redirect(url_for('welcome'))

# ----------------- Main -----------------
if __name__ == "__main__":
    app.run(debug=True)
