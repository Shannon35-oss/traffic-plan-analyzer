from flask import Flask, request, render_template, send_file
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
REPORT_FOLDER = 'reports'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['REPORT_FOLDER'] = REPORT_FOLDER

TMP_KEYWORDS = [
    "Traffic Management Plan", "TMP", "traffic control", "road closure", "detour",
    "pedestrian control", "signage", "bollard", "barrier"
]
TCAWS_KEYWORDS = [
    "AS 1742.3", "Austroads", "TTM Part 1", "TTM Part 2", "TTM Part 3", "TTM Part 4",
    "TTM Part 5", "TTM Part 6", "TTM Part 7", "TTM Part 8", "TTM Part 9", "TTM Part 10",
    "high-visibility", "speed signage", "variable message sign", "MMS", "VSLS"
]

@app.route('/', methods=['GET', 'POST'])
def index():
    result = None
    report_path = None
    if request.method == 'POST':
        file = request.files['pdf']
        if file:
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)

            doc = fitz.open(filepath)
            full_text = ""
            for page in doc:
                pix = page.get_pixmap(dpi=300)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(img)
                full_text += text + "\n"
            doc.close()

            is_tmp = any(k.lower() in full_text.lower() for k in TMP_KEYWORDS)
            compliance_hits = [k for k in TCAWS_KEYWORDS if k.lower() in full_text.lower()]
            compliance_score = int((len(compliance_hits) / len(TCAWS_KEYWORDS)) * 100)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            report_text = f"Traffic Management Plan Analysis Report\n"
            report_text += f"Timestamp: {timestamp}\n"
            report_text += f"Filename: {filename}\n\n"
            report_text += "Summary:\n"
            report_text += "- This report analyzes the uploaded PDF to determine if it is a Traffic Management Plan (TMP).\n"
            report_text += "- It checks for compliance with TCAWS standards by identifying key indicators.\n\n"
            report_text += f"Is this a Traffic Management Plan? {'Yes' if is_tmp else 'No'}\n\n"
            report_text += "TCAWS Compliance Indicators Found:\n"
            if compliance_hits:
                for hit in compliance_hits:
                    report_text += f"- {hit}\n"
            else:
                report_text += "- None found\n"
            report_text += f"\nCompliance Score: {compliance_score}%\n"

            os.makedirs(app.config['REPORT_FOLDER'], exist_ok=True)
            report_path = os.path.join(app.config['REPORT_FOLDER'], 'compliance_report.pdf')
            pdf_doc = fitz.open()
            page = pdf_doc.new_page()
            text_rect = fitz.Rect(50, 50, 550, 800)
            page.insert_textbox(text_rect, report_text, fontsize=12, fontname="helv")
            pdf_doc.save(report_path)
            pdf_doc.close()

            result = {
                "is_tmp": is_tmp,
                "compliance_hits": compliance_hits,
                "compliance_score": compliance_score
            }
            return render_template('index.html', result=result, report_path='compliance_report.pdf')

    return render_template('index.html', result=None, report_path=None)

@app.route('/download_report')
def download_report():
    filename = request.args.get('file')
    filepath = os.path.join(app.config['REPORT_FOLDER'], filename)
    return send_file(filepath, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
