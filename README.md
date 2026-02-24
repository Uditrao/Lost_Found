# 🔍 Lost & Found – Item Recovery Platform

A robust, full-stack web application designed to help people recover lost items and report found belongings. Built with **Python (Flask)** and **MongoDB**, this platform features a seamless reporting flow, OTP-based security, and an administrative oversight system.

---

## 🚀 Key Features

### 👤 User Features
- **Secure Authentication**: OTP-based registration and password reset via email.
- **Item Reporting**: Detailed forms for reporting "Lost" or "Found" items, including location and date.
- **Image Management**: High-quality image uploads powered by **Cloudinary**.
- **Claim System**: Users can claim items they recognize and track the status of their requests.
- **Personal Dashboard**: Manage reported items and track claim history.

### 🛠️ Admin Features
- **Claim Management**: Review, approve, or reject user claims.
- **Collection Tracking**: Mark items as "Collected" once returned to the rightful owner.
- **Administrative Control**: Secure access for authorized personnel.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | HTML5, CSS3, JavaScript, Jinja2 Templates |
| **Backend** | Python (Flask) |
| **Database** | MongoDB (NoSQL) |
| **Image Hosting** | Cloudinary |
| **Communication** | Flask-Mail (SMTP Integration) |
| **Deployment** | Vercel / Heroku Ready |

---

## 🛠️ Installation & Setup

Follow these steps to get the project running on your local machine:

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/Lost_Found_git.git
cd Lost_Found_git
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r api/requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and add the following:

```env
SECRET_KEY=your_secret_key
MONGO_URI=your_mongodb_connection_string
MAIL_USERNAME=your_gmail@gmail.com
MAIL_PASSWORD=your_google_app_password
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
UPLOAD_FOLDER=static/uploads
```

### 5. Run the Application
```bash
python api/index.py
```
Open `http://localhost:5000` in your browser.

---

## 📁 Project Structure

```bash
├── api/                   # Backend logic (Flask routes)
│   ├── index.py           # Main application entry point
│   └── requirements.txt   # Python dependencies
├── static/                # Styles and assets
│   ├── auth.css           # Authentication specific styles
│   ├── dashboard.css      # User dashboard styles
│   └── styles.css         # Global styles
├── templates/             # HTML Jinja2 templates
├── vercel.json            # Vercel deployment configuration
└── README.md              # Project documentation
```

---

## 🛡️ Security
- **OTP Verification**: Ensures valid email addresses for all users.
- **Environment Safety**: Sensitive credentials are managed via `.env`.
- **Admin Roles**: Restricted access to sensitive administrative actions.

---

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License
This project is licensed under the MIT License.

---
*Created by [Udit Yadav](https://github.com/Uditrao)*
