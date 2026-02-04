# **📜 Legal Document Analyzer** 🚀  

An AI-powered web application that analyzes legal case documents and provides intelligent insights such as summary, case type, IPC sections, legal remedies, risk score, translation, and lawyer suggestions.

## **🔍 Features**  
-  Upload legal case files in PDF, DOCX, and TXT formats.
-  Extracts text from documents using PyMuPDF and OCR for scanned PDFs.
-  Performs AI-based summarization for large case documents.
-  Detects the nature of the case (Criminal, Family, Property, Contract, Environmental, etc.).
-  Identifies relevant IPC sections based on document content.
-  Calculates a Risk Score (Low / Medium / High) from case keywords.
-  Suggests legal remedies and recommended lawyers.
-  Supports translation of summary into multiple languages.
-  Allows users to download a detailed PDF case report.
-  Includes feedback system and admin dashboard for monitoring usage.

## **🛠️ Tech Stack**  
- **Backend:** Flask(Python Web Framework)
- **AI/NLP:** Transformers (`facebook/bart-large-cnn`, `facebook/bart-large-mnli`), PyMuPDF, Pytesseract (OCR).  
- **AI Models:** `flan-t5-large` (for chatbot & text refinement).  
- **Translation:** `deep-translator` (Google Translate API).
- **Frontend:** HTML, CSS, JavaScript(Flask Jinja Templates)
- **Storage:** Local `uploads/` history.json,lawyers.json.  

## **🚀 Installation & Setup**  

### **1️⃣ Clone the Repository**  
```bash
git clone https://github.com/santubambalwadi/A-Quick-Case-Analyser.git
cd "A Quick Case Analyser/Legal Doc"
```

### **2️⃣ Create a Virtual Environment (Optional but Recommended)**
```bash
python -m venv venv
venv\Scripts\activate
```

### **3️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
pip install PyPDF2 reportlab deep-translator
```
### **4️⃣ Run the Application
```bash
python app.py
```

The app will be available at **http://127.0.0.1:5000/**  

## **📂 Project Structure**
```
A Quick Case Analyser
 └── Legal Doc
      ├── app.py
      ├── templates/
      ├── static/
      ├── uploads/
      ├── history.json
      ├── lawyers.json
      ├── requirements.txt
      └── README.md
```
## **🛠️ How It Works**
- User uploads a legal document (PDF/DOCX/TXT).
- Text is extracted (OCR used if scanned).
- AI summarizes the document content.
- System detects the case type using keyword + AI logic.
- Risk score is calculated from sensitive terms.
- Relevant IPC sections, remedies, and lawyers are suggested.
- User can translate summary or download a full PDF report.
- Admin dashboard records user activity and feedback.

## **📜 Supported Languages for Translation**
- **English (en)**
- **Hindi (hi)**
- **Tamil (ta)**
- **Marathi (mr)**
- **Telugu (te)**

## **💡 Future Enhancements**
🚀 Integration with real legal databases and e-Courts API
🚀 Advanced AI case similarity detection
🚀 Secure cloud-based case history storage 

## **📌 Contribution**
Want to improve this project? **Fork, modify, and submit a pull request!** 🎯  

## **📜 License**
This project is licensed under the **MIT License** – free to use, modify, and distribute.  
