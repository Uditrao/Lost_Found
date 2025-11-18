from flask import Flask, render_template, request, redirect, session, flash
from werkzeug.utils import secure_filename
import os
import random
from flask_mail import Mail, Message
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load .env
load_dotenv()

# ----------------- APP & CONFIG -----------------
app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Email config
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = app.config["MAIL_USERNAME"]
mail = Mail(app)

# MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["lost_found"]

users = db.users
lost_items = db.lost_items
found_items = db.found_items
claims = db.claims
admins = db.admins


# ----------------- ROUTES -----------------

@app.route("/")
def home():
    return render_template("register.html")


# ---------- REGISTER + OTP ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if users.find_one({"email": email}):
            flash("User already exists!", "error")
            return redirect("/register")

        otp = str(random.randint(100000, 999999))
        session["pending_user"] = {"name": name, "email": email, "password": password}
        session["otp"] = otp

        msg = Message("Your OTP for Lost & Found Registration", recipients=[email])
        msg.body = f"Your OTP is {otp}"
        mail.send(msg)

        flash("OTP sent to email!", "success")
        return redirect("/verify_otp")

    return render_template("register.html")


@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if request.method == "POST":
        if request.form["otp"] == session.get("otp"):
            u = session["pending_user"]
            users.insert_one(u)

            session.pop("otp", None)
            session.pop("pending_user", None)

            flash("Registration successful!", "success")
            return redirect("/login")
        else:
            flash("Invalid OTP", "error")

    return render_template("verify_otp.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Find user by email only
        user = users.find_one({"email": email})

        if not user:
            flash("Email not found!", "error")
            return redirect("/login")

        if user["password"] != password:
            flash("Incorrect password!", "error")
            return redirect("/login")

        # Save user in session
        session["user_id"] = str(user["_id"])
        session["user_name"] = user["name"]
        session["email"] = user["email"]

        # Check admin based on string user_id
        admin = admins.find_one({"user_id": session["user_id"]})
        session["is_admin"] = bool(admin)

        return redirect("/admin/claims" if session["is_admin"] else "/dashboard")

    return render_template("login.html")


# ---------- FORGOT PASSWORD (OTP) ----------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]

        user = users.find_one({"email": email})
        if not user:
            flash("Email not found.", "error")
            return redirect("/forgot_password")

        otp = str(random.randint(100000, 999999))
        session["reset_email"] = email
        session["reset_otp"] = otp

        msg = Message("Reset Password OTP", recipients=[email])
        msg.body = f"Your OTP is {otp}"
        mail.send(msg)

        flash("OTP sent to your email.", "success")
        return redirect("/verify_reset_otp")

    return render_template("forgot_password.html")


@app.route("/verify_reset_otp", methods=["GET", "POST"])
def verify_reset_otp():
    if request.method == "POST":
        if request.form["otp"] == session.get("reset_otp"):
            session["reset_verified"] = True
            return redirect("/reset_password")
        flash("Invalid OTP", "error")

    return render_template("verify_reset_otp.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    if request.method == "POST":
        if not session.get("reset_verified"):
            return redirect("/verify_reset_otp")

        newpass = request.form["new_password"]

        users.update_one(
            {"email": session["reset_email"]},
            {"$set": {"password": newpass}},
        )

        session.clear()
        flash("Password updated. Login now.", "success")
        return redirect("/login")

    return render_template("reset_password.html")


# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html")


# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------- REPORT LOST ----------
@app.route("/report_lost", methods=["GET", "POST"])
def report_lost():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        date_lost = request.form["date_lost"]

        image = request.files["image"]
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(filepath)

        lost_items.insert_one(
            {
                "title": title,
                "description": description,
                "location": location,
                "date_lost": date_lost,
                "image": filepath,
                "user_id": session["user_id"],  # string
                "collected": False,
            }
        )

        return redirect("/view_items")

    return render_template("report_lost.html")


# ---------- REPORT FOUND ----------
@app.route("/report_found", methods=["GET", "POST"])
def report_found():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        location = request.form["location"]
        date_found = request.form["date_found"]

        image = request.files["image"]
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(filepath)

        found_items.insert_one(
            {
                "title": title,
                "description": description,
                "location": location,
                "date_found": date_found,
                "image": filepath,
                "user_id": session["user_id"],  # string
                "collected": False,
            }
        )

        return redirect("/view_items")

    return render_template("report_found.html")


# ---------- VIEW ITEMS ----------
@app.route("/view_items")
def view_items():
    if "user_id" not in session:
        return redirect("/login")

    uid = session["user_id"]

    # Skip items from current user and items already collected
    lost = list(
        lost_items.find(
            {"user_id": {"$ne": uid}, "collected": {"$ne": True}}
        )
    )
    found = list(
        found_items.find(
            {"user_id": {"$ne": uid}, "collected": {"$ne": True}}
        )
    )

    for x in lost:
        claim = claims.find_one(
            {"item_id": str(x["_id"]), "item_type": "lost", "user_id": uid}
        )
        x["claimed_by_user"] = bool(claim)
        x["claim_status"] = claim["status"] if claim else ""

    for x in found:
        claim = claims.find_one(
            {"item_id": str(x["_id"]), "item_type": "found", "user_id": uid}
        )
        x["claimed_by_user"] = bool(claim)
        x["claim_status"] = claim["status"] if claim else ""

    return render_template("view_items.html", lost_items=lost, found_items=found)


# ---------- CLAIM ITEM ----------
@app.route("/claim_item", methods=["POST"])
def claim_item():
    if "user_id" not in session:
        return redirect("/login")

    claims.insert_one(
        {
            "user_id": session["user_id"],  # string
            "item_id": request.form["item_id"],
            "item_type": request.form["item_type"],
            "status": "pending",
            "collected": False,
        }
    )
    return redirect("/view_items")


# ---------- MY CLAIMS ----------
@app.route("/my_claims")
def my_claims():
    if "user_id" not in session:
        return redirect("/login")

    user_claims = list(claims.find({"user_id": session["user_id"]}))

    for c in user_claims:
        c["_id"] = str(c["_id"])

    return render_template("my_claims.html", claims=user_claims)


# ---------- ADMIN: VIEW CLAIMS ----------
@app.route("/admin/claims")
def admin_claims():
    if not session.get("is_admin"):
        return redirect("/")

    cl = list(
        claims.aggregate(
            [
                {
                    "$lookup": {
                        "from": "users",
                        "let": {"uid": "$user_id"},
                        "pipeline": [
                            {
                                "$match": {
                                    "$expr": {
                                        "$eq": [{"$toString": "$_id"}, "$$uid"]
                                    }
                                }
                            }
                        ],
                        "as": "user",
                    }
                },
                {"$unwind": "$user"},
            ]
        )
    )

    return render_template("admin_claims.html", claims=cl)


# ---------- ADMIN: MARK COLLECTED ----------
@app.route("/admin/mark_collected/<claim_id>")
def mark_collected(claim_id):
    if not session.get("is_admin"):
        return redirect("/")

    claims.update_one(
        {"_id": ObjectId(claim_id)},
        {"$set": {"collected": True}},
    )

    flash("Item marked as collected!", "success")
    return redirect("/admin/claims")


# ---------- PROFILE: UPDATE NAME ----------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect("/login")

    users.update_one(
        {"_id": ObjectId(session["user_id"])},
        {"$set": {"name": request.form["name"]}},
    )
    session["user_name"] = request.form["name"]
    flash("Profile updated!", "success")
    return redirect("/dashboard")


# ---------- PROFILE: CHANGE PASSWORD ----------
@app.route("/change_password", methods=["POST"])
def change_password():
    if "user_id" not in session:
        return redirect("/login")

    user = users.find_one({"_id": ObjectId(session["user_id"])})

    if user["password"] != request.form["current_password"]:
        flash("Wrong current password", "error")
        return redirect("/dashboard")

    users.update_one(
        {"_id": ObjectId(session["user_id"])},
        {"$set": {"password": request.form["new_password"]}},
    )

    flash("Password changed!", "success")
    return redirect("/dashboard")


# ---------- EMAIL HELPERS ----------
def send_approval_email(user_email, item_name):
    subject = "✅ Your Lost & Found Request Has Been Approved!"
    body = f"""
    Hello,

    Great news! Your request for the item "{item_name}" has been approved by the admin.

    Please log in to your Lost & Found account to view details or collect your item.

    - Lost & Found Team
    """
    msg = Message(subject, recipients=[user_email], body=body)
    mail.send(msg)


def send_rejection_email(user_email, item_name):
    subject = "❌ Your Lost & Found Request Has Been Rejected"
    body = f"""
    Hello,

    We’re sorry to inform you that your request for the item "{item_name}" has been rejected by the admin.

    For more details, please log in to your Lost & Found account.

    - Lost & Found Team
    """
    msg = Message(subject, recipients=[user_email], body=body)
    mail.send(msg)


# ---------- ADMIN: APPROVE / REJECT ----------
@app.route("/admin/claim_action/<claim_id>/<action>")
def claim_action(claim_id, action):
    if not session.get("is_admin"):
        return redirect("/")

    c = claims.find_one({"_id": ObjectId(claim_id)})
    if not c:
        flash("Claim not found", "error")
        return redirect("/admin/claims")

    # c['user_id'] is a string of the user's ObjectId
    user = users.find_one({"_id": ObjectId(c["user_id"])})

    if action == "approved":
        send_approval_email(user["email"], c["item_type"])
    elif action == "rejected":
        send_rejection_email(user["email"], c["item_type"])

    claims.update_one({"_id": ObjectId(claim_id)}, {"$set": {"status": action}})
    return redirect("/admin/claims")


# ---------- TEMP: MAKE ADMIN ----------
@app.route("/make_admin/<user_id>")
def make_admin(user_id):
    admins.insert_one({"user_id": user_id})
    return f"User {user_id} is now an admin!"


# ---------- MAIN ----------
if __name__ == "__main__":
    # For local development. On Render/Railway, gunicorn will run app:app
    app.run(debug=True)
