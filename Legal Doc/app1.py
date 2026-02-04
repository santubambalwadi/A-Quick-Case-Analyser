from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session, flash
from PyPDF2 import PdfReader
import re, os, io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from deep_translator import GoogleTranslator
import json   # <<< added >>>
from datetime import datetime   # <<< added >>>


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
def summarize_text(text, sentence_count=3):
    sentences = re.split(r'(?<=[.!?]) +', text)
    if len(sentences) <= sentence_count:
        return text
    return " ".join(sentences[:sentence_count])

# ----------------- Helper: Case Nature -----------------
def detect_case_nature(text):
    text_lower = text.lower()
    if any(word in text_lower for word in ["murder", "theft", "assault", "crime", "police"]):
        return "Criminal Case"
    elif any(word in text_lower for word in ["divorce", "marriage", "custody", "dowry"]):
        return "Family Case"
    elif any(word in text_lower for word in ["land", "property", "ownership", "possession"]):
        return "Property Case"
    elif any(word in text_lower for word in ["contract", "agreement", "breach", "business"]):
        return "Contract Case"
    elif any(word in text_lower for word in ["environment", "pollution", "forest"]):
        return "Environmental Case"
    else:
        return "General / Civil Case"

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

    return jsonify({
        "summary": summary,
        "case_nature": case_nature,
        "risk_score": risk_score,
        "punishments": punishments
    })

# ----------------- Translation -----------------
@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text", "").strip()
    target = data.get("target_lang") or data.get("language") or "en"
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
    question = data.get("question", "").lower()
    text = data.get("text", "")

    answer = "Sorry, I don’t have an answer for that."
    if "summary" in question:
        answer = summarize_text(text)
    elif "case" in question:
        answer = detect_case_nature(text)
    elif "risk" in question:
        answer = f"Estimated risk score: {calculate_risk_score(text)}"
    elif "keywords" in question:
        words = set(re.findall(r"\b\w+\b", text.lower()))
        answer = f"Keywords in document: {', '.join(list(words)[:20])}..."

    return jsonify({"answer": answer})

# ----------------- Download PDF -----------------
@app.route('/download-pdf', methods=['POST'])
def download_pdf():
    data = request.json
    summary = data.get("summary", "")
    case_nature = data.get("case_nature", "")
    risk_score = data.get("risk_score", "")
    punishments = data.get("punishments", "")
    translation = data.get("translation", "")

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 60
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width / 2, y, "⚖️ Legal Document Analysis Report")
    y -= 40

    def draw_section(title, content, start_y, space=20):
        nonlocal p
        y = start_y
        if not content:
            return y
        p.setFont("Helvetica-Bold", 13)
        p.drawString(50, y, title)
        y -= space
        p.setFont("Helvetica", 11)
        for line in content.splitlines():
            for chunk in [line[i:i+95] for i in range(0, len(line), 95)]:
                p.drawString(60, y, chunk)
                y -= 15
                if y < 50:
                    p.showPage()
                    y = height - 60
                    p.setFont("Helvetica", 11)
        y -= 15
        return y

    y = draw_section("📌 Case Nature:", case_nature, y)
    y = draw_section("⚠️ Risk Score:", str(risk_score), y)
    y = draw_section("📑 Summary:", summary, y)
    y = draw_section("🔒 Possible Punishments:", punishments, y)
    y = draw_section("🌍 Translation:", translation, y)

    p.setFont("Helvetica-Oblique", 9)
    p.drawString(50, 30, "Generated by Legal Document Analyzer")
    p.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name="Legal_Report.pdf",
                     mimetype="application/pdf")

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
            data = load_history()   # <<< added >>>
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
