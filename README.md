# ShoeStyle — Flask Shoes Store

## Features
- Responsive product catalogue, category filters and search
- Product detail and shoe-size selection
- Session-based cart and checkout (Cash on Delivery demo)
- User registration/login and order history
- Admin dashboard, product CRUD, image upload and order status updates
- SQLite database auto-created on first run with sample products

## Run on Windows (PowerShell)
```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:SECRET_KEY="replace-with-a-long-random-secret"
$env:ADMIN_EMAIL="admin@example.com"
$env:ADMIN_PASSWORD="Use-A-Strong-Password-Here"
python app.py
```
Open http://127.0.0.1:5000

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

## Important
- The admin account is created only when `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set before the first app run. If the database already exists, create an admin using the SQLAlchemy shell or a one-off script; do not use a public registration form to grant admin rights.
- Product demo photos use remote Unsplash URLs. Replace them with photos you own or have permission to use.
- Checkout currently supports Cash on Delivery as a demo. It does not charge online payments, send email, or arrange shipping.
- Before production deployment: set a strong SECRET_KEY, turn off debug mode, add CSRF protection and rate limiting, configure HTTPS, validate image uploads more strictly, add privacy/returns pages, secure order access, and use a real payment provider if required.
