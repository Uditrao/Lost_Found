from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.utils import secure_filename
import os
import mysql.connector
import random
from flask_mail import Mail, Message
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")   # <-- replace with your Gmail
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")     # <-- use App Password from Google
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']
mail = Mail(app)

client = MongoClient(os.getenv("MONGO_URI")) 
db = client["lost_found"]

users = db.users
lost_items = db.lost_items
found_items = db.found_items
claims = db.claims
admins = db.admins




# Route: Home
@app.route('/')
def home():
    return render_template('register.html')

# Route: Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if users.find_one({"email": email}):
            flash("User already exists!", "error")
            return redirect('/register')

        otp = str(random.randint(100000, 999999))
        session['pending_user'] = {"name": name, "email": email, "password": password}
        session['otp'] = otp

        msg = Message('Your OTP for Lost & Found Registration', recipients=[email])
        msg.body = f"Your OTP is {otp}"
        mail.send(msg)

        flash("OTP sent to email!", "success")
        return redirect('/verify_otp')

    return render_template('register.html')


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    if request.method == 'POST':
        if request.form['otp'] == session.get('otp'):
            u = session['pending_user']
            users.insert_one(u)

            session.pop('otp', None)
            session.pop('pending_user', None)

            flash("Registration successful!", "success")
            return redirect('/login')
        else:
            flash("Invalid OTP", "error")

    return render_template('verify_otp.html')


# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.find_one({"email": email, "password": password})

        if user:
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['email'] = user['email']

            # Check admin
            admin = admins.find_one({"user_id": str(user['_id'])})
            session['is_admin'] = bool(admin)

            return redirect('/admin/claims' if session['is_admin'] else '/dashboard')

        flash("Invalid credentials", "error")

    return render_template('login.html')

# ---------------- Forgot Password (Email OTP) ----------------
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']

        user = users.find_one({"email": email})
        if not user:
            flash("Email not found.", "error")
            return redirect('/forgot_password')

        otp = str(random.randint(100000, 999999))
        session['reset_email'] = email
        session['reset_otp'] = otp

        msg = Message("Reset Password OTP", recipients=[email])
        msg.body = f"Your OTP is {otp}"
        mail.send(msg)

        flash("OTP sent to your email.", "success")
        return redirect('/verify_reset_otp')

    return render_template('forgot_password.html')

@app.route('/verify_reset_otp', methods=['GET', 'POST'])
def verify_reset_otp():
    if request.method == 'POST':
        if request.form['otp'] == session.get('reset_otp'):
            session['reset_verified'] = True
            return redirect('/reset_password')
        flash("Invalid OTP", "error")

    return render_template('verify_reset_otp.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        if not session.get('reset_verified'):
            return redirect('/verify_reset_otp')

        newpass = request.form['new_password']

        users.update_one(
            {"email": session['reset_email']},
            {"$set": {"password": newpass}}
        )

        session.clear()
        flash("Password updated. Login now.", "success")
        return redirect('/login')

    return render_template('reset_password.html')
 
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('dashboard.html')



# Route: Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Route: Report Lost Item
@app.route('/report_lost', methods=['GET', 'POST'])
def report_lost():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_lost = request.form['date_lost']

        image = request.files['image']
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        lost_items.insert_one({
            "title": title,
            "description": description,
            "location": location,
            "date_lost": date_lost,
            "image": filepath,
            "user_id": session['user_id'],
            "collected": False
        })

        return redirect('/view_items')

    return render_template('report_lost.html')


# Route: Report Found Item
@app.route('/report_found', methods=['GET', 'POST'])
def report_found():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        location = request.form['location']
        date_found = request.form['date_found']

        # image upload
        image = request.files['image']
        filename = secure_filename(image.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        found_items.insert_one({
            "title": title,
            "description": description,
            "location": location,
            "date_found": date_found,
            "image": filepath,
            "user_id": session['user_id']
        })

        return redirect('/view_items')

    return render_template('report_found.html')

# Route: View Items
@app.route('/view_items')
def view_items():
    uid = session['user_id']

    lost = list(lost_items.find({"user_id": {"$ne": uid}}))
    found = list(found_items.find({"user_id": {"$ne": uid}}))

    for x in lost:
        claim = claims.find_one({"item_id": str(x['_id']), "item_type": "lost", "user_id": uid})
        x['claimed_by_user'] = bool(claim)
        x['claim_status'] = claim['status'] if claim else ""

    for x in found:
        claim = claims.find_one({"item_id": str(x['_id']), "item_type": "found", "user_id": uid})
        x['claimed_by_user'] = bool(claim)
        x['claim_status'] = claim['status'] if claim else ""

    return render_template('view_items.html', lost_items=lost, found_items=found)


# Route: Claim Item
@app.route('/claim_item', methods=['POST'])
def claim_item():
    claims.insert_one({
        "user_id": session['user_id'],
        "item_id": request.form['item_id'],
        "item_type": request.form['item_type'],
        "status": "pending",
        "collected": False
    })
    return redirect('/view_items')

# Route: My Claims
@app.route('/my_claims')
def my_claims():
    if 'user_id' not in session:
        return redirect('/login')

    user_claims = list(claims.find({"user_id": session['user_id']}))

    # convert ObjectId to string for HTML safety
    for c in user_claims:
        c['_id'] = str(c['_id'])

    return render_template('my_claims.html', claims=user_claims)

# Admin Panel: View Claims
@app.route('/admin/claims')
def admin_claims():
    cl = list(claims.aggregate([
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
                "as": "user"
            }
        },
        {"$unwind": "$user"}
    ]))

    return render_template('admin_claims.html', claims=cl)


 
@app.route('/admin/mark_collected/<claim_id>')
def mark_collected(claim_id):
    if not session.get('is_admin'):
        return redirect('/')

    claims.update_one(
        {"_id": ObjectId(claim_id)},
        {"$set": {"collected": True}}
    )

    flash("Item marked as collected!", "success")
    return redirect('/admin/claims')

#---------------------------------------
@app.route('/update_profile', methods=['POST'])
def update_profile():
    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$set": {"name": request.form['name']}}
    )
    session['user_name'] = request.form['name']
    return redirect('/dashboard')



@app.route('/change_password', methods=['POST'])
def change_password():
    user = users.find_one({"_id": ObjectId(session['user_id'])})

    if user['password'] != request.form['current_password']:
        flash("Wrong current password", "error")
        return redirect('/dashboard')

    users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$set": {"password": request.form['new_password']}}
    )
    
    flash("Password changed!", "success")
    return redirect('/dashboard')



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

# Admin Action: Approve/Reject Claim
@app.route('/admin/claim_action/<claim_id>/<action>')
def claim_action(claim_id, action):
    c = claims.find_one({"_id": ObjectId(claim_id)})
    if not c:
        flash("Claim not found", "error")
        return redirect('/admin/claims')

    user = users.find_one({"_id": ObjectId(c['user_id'])})

    if action == "approved":
        send_approval_email(user['email'], c['item_type'])
    else:
        send_rejection_email(user['email'], c['item_type'])

    claims.update_one({"_id": ObjectId(claim_id)}, {"$set": {"status": action}})
    return redirect('/admin/claims')


@app.route('/make_admin/<user_id>')
def make_admin(user_id):
    admins.insert_one({"user_id": user_id})
    return f"User {user_id} is now an admin!"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
