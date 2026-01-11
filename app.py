from flask import Flask, render_template, request, redirect, url_for, flash
import os
import csv

from services.rename_service import rename_certificates
from services.email_service import send_certificates

app = Flask(__name__)
app.secret_key = "9fb28e216def0dfbb430f1bcb12c30e1caa20e2d12cee3a3e490aab30a4a3d6a"

UPLOAD_CSV = "uploads/csv"
UPLOAD_CERTS = "uploads/certificates"
RENAMED_FOLDER = "certificates_renamed"
LOG_FILE = "logs.txt"

os.makedirs(UPLOAD_CSV, exist_ok=True)
os.makedirs(UPLOAD_CERTS, exist_ok=True)
os.makedirs(RENAMED_FOLDER, exist_ok=True)


# ================= INDEX =================
@app.route("/")
def index():
    return render_template("index.html")


# ================= PREVIEW =================
@app.route("/preview", methods=["POST"])
def preview():
    if "csv_file" not in request.files:
        flash("CSV file missing", "danger")
        return redirect(url_for("index"))

    csv_file = request.files["csv_file"]
    cert_files = request.files.getlist("cert_files")

    if csv_file.filename == "" or not cert_files:
        flash("CSV or certificates missing", "danger")
        return redirect(url_for("index"))

    csv_path = os.path.join(UPLOAD_CSV, csv_file.filename)
    csv_file.save(csv_path)

    for f in cert_files:
        f.save(os.path.join(UPLOAD_CERTS, f.filename))

    preview_data = []

    with open(csv_path, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for idx, row in enumerate(reader, start=1):
            name = row["name"]
            email = row["email"]

            cert_found = False
            cert_name = "Missing"

            for ext in [".jpg", ".jpeg", ".png", ".pdf"]:
                path = os.path.join(UPLOAD_CERTS, f"{idx}{ext}")
                if os.path.exists(path):
                    cert_found = True
                    cert_name = f"{idx}{ext}"
                    break

            preview_data.append({
                "name": name,
                "email": email,
                "certificate": cert_name,
                "status": "Ready" if cert_found else "Missing"
            })

    return render_template(
        "preview.html",
        preview_data=preview_data,
        csv_filename=csv_file.filename
    )


# ================= RESULT PAGE =================
@app.route("/preview-result")
def preview_result():
    return render_template("preview_result.html")


# ================= SEND =================
@app.route("/process", methods=["POST"])
def process():
    try:
        if "csv_filename" not in request.form:
            flash("Please preview certificates before sending.", "danger")
            return redirect(url_for("index"))

        sender_email = request.form["sender_email"]
        app_password = request.form["app_password"]
        subject = request.form["subject"]
        csv_filename = request.form["csv_filename"]

        csv_path = os.path.join(UPLOAD_CSV, csv_filename)

        rename_certificates(csv_path, UPLOAD_CERTS, RENAMED_FOLDER)

        sent_count, failed_count = send_certificates(
            csv_path,
            RENAMED_FOLDER,
            sender_email,
            app_password,
            subject,
            LOG_FILE
        )

        if sent_count > 0 and failed_count == 0:
            flash(f"✅ All certificates sent successfully ({sent_count})", "success")
        elif sent_count > 0:
            flash(f"⚠️ {sent_count} sent, {failed_count} failed", "warning")
        else:
            flash("❌ No emails were sent", "danger")

    except Exception as e:
        flash(f"❌ Error: {str(e)}", "danger")

    # ✅ REDIRECT TO RESULT PAGE (KEY FIX)
    return redirect(url_for("preview_result"))


if __name__ == "__main__":
    app.run()
