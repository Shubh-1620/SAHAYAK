import os
import csv
import json
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# File paths
USERS_FILE = "real_users.csv"
LOGINS_FILE = "real_logins.csv"
COMPLAINTS_FILE = "complaints_data.csv"

def check_user_exists(email):
    """Scans real_users.csv to see if the email is already registered."""
    if not os.path.exists(USERS_FILE):
        return False
    try:
        with open(USERS_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Email", "").strip().lower() == email.strip().lower():
                    return True
    except Exception as e:
        print(f"[!] Error checking user existence: {e}")
    return False

def authenticate_user(email, password):
    """Checks credentials against real_users.csv and returns user data if valid."""
    if not os.path.exists(USERS_FILE):
        return None
    try:
        with open(USERS_FILE, mode='r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("Email", "").strip().lower() == email.strip().lower() and row.get("Password", "") == password:
                    return {
                        "name": row.get("Name", ""),
                        "email": row.get("Email", ""),
                        "district": row.get("District", ""),
                        "isAdmin": "Admin" in row.get("Name", "") or row.get("Email", "").strip().lower() == "admin@sahayak.in"
                    }
    except Exception as e:
        print(f"[!] Error authenticating user: {e}")
    return None

def save_user_to_csv(data):
    """Appends registered user data to real_users.csv."""
    file_exists = os.path.exists(USERS_FILE)
    try:
        with open(USERS_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Name", "Email", "Password", "District", "Signup_Timestamp"])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "Name": data.get("name", ""),
                "Email": data.get("email", ""),
                "Password": data.get("password", ""),
                "District": data.get("district", ""),
                "Signup_Timestamp": data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            })
        print(f"[+] Account registered: {data.get('name')} ({data.get('email')})")
    except Exception as e:
        print(f"[!] Error saving registration to CSV: {e}")

def save_login_to_csv(data):
    """Appends login log details to real_logins.csv."""
    file_exists = os.path.exists(LOGINS_FILE)
    try:
        with open(LOGINS_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Email", "Login_Timestamp", "Success", "IP_Address", "Device_Used"])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                "Email": data.get("email", ""),
                "Login_Timestamp": data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                "Success": str(data.get("success", False)),
                "IP_Address": data.get("ip", "127.0.0.1"),
                "Device_Used": data.get("device", "Unknown Browser")
            })
        print(f"[+] Login attempt logged: {data.get('email')} - Success: {data.get('success')}")
    except Exception as e:
        print(f"[!] Error saving login log to CSV: {e}")

def sync_complaints_to_csv(complaints_list):
    """Synchronizes complaints database array to complaints_data.csv."""
    if isinstance(complaints_list, dict):
        complaints_list = [complaints_list]
    try:
        with open(COMPLAINTS_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=["Complaint_ID", "Citizen_Name", "Aadhaar_No", "Category", "Details", "District", "State", "Support_Count", "Date_Filed", "Status"])
            writer.writeheader()
            for c in complaints_list:
                writer.writerow({
                    "Complaint_ID": c.get("id", ""),
                    "Citizen_Name": c.get("name", ""),
                    "Aadhaar_No": c.get("aadhaar", ""),
                    "Category": c.get("category", ""),
                    "Details": c.get("details", ""),
                    "District": c.get("district", ""),
                    "State": c.get("state", ""),
                    "Support_Count": c.get("support", 0),
                    "Date_Filed": c.get("date", ""),
                    "Status": c.get("status", "Open")
                })
        print(f"[+] Complaints synchronized ({len(complaints_list)} records)")
    except Exception as e:
        print(f"[!] Error synchronizing complaints to CSV: {e}")

class AuthHandler(BaseHTTPRequestHandler):
    """API handler with CORS headers to serve data stream from frontend browser."""
    def log_message(self, format, *args):
        return # Suppress built-in log printing to keep CLI output clean

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

        response_data = {"success": False}

        # Route matching
        if self.path == '/api/register':
            email = data.get("email", "")
            if check_user_exists(email):
                response_data = {"success": False, "error": "An account with this email already exists."}
            else:
                save_user_to_csv(data)
                response_data = {"success": True}

        elif self.path == '/api/login':
            email = data.get("email", "")
            password = data.get("password", "")
            user = authenticate_user(email, password)
            success = user is not None
            
            # Log login audit trail
            save_login_to_csv({
                "email": email,
                "success": success,
                "device": data.get("device", "Unknown Browser"),
                "ip": self.client_address[0],
                "timestamp": data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            })

            if success:
                response_data = {"success": True, "user": user}
            else:
                response_data = {"success": False, "error": "No match with this data found. Please create an account."}

        elif self.path == '/api/sync_complaints':
            sync_complaints_to_csv(data)
            response_data = {"success": True}

        self.wfile.write(json.dumps(response_data).encode('utf-8'))

def run_server():
    print("=" * 60)
    print("        SAHAYAK AUTHENTICATION & DATA COLLECTION SERVER")
    print("=" * 60)
    print("[*] Server started locally at http://localhost:8000")
    print("[*] Web app can register, login, and sync complaints data.")
    print("[*] Press Ctrl+C to stop...\n")
    try:
        HTTPServer(('', 8000), AuthHandler).serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Stopping server...")

if __name__ == '__main__':
    run_server()
