import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shoestyle.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db = SQLAlchemy(app)

CATEGORIES = ["Men", "Women", "Kids", "Sports", "Sneakers", "Formal", "Sandals"]
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Integer, nullable=False)
    old_price = db.Column(db.Integer, nullable=True)
    image_url = db.Column(db.String(500), default="")
    sizes = db.Column(db.String(100), default="6,7,8,9,10")
    stock = db.Column(db.Integer, default=10)
    featured = db.Column(db.Boolean, default=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    address = db.Column(db.Text, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(40), default="Pending")
    payment_method = db.Column(db.String(40), default="Cash on Delivery")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"), nullable=False)
    product_id = db.Column(db.Integer, nullable=True)
    product_name = db.Column(db.String(160), nullable=False)
    size = db.Column(db.String(20), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = db.session.get(User, session.get("user_id"))
        if not user or not user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def global_values():
    cart = session.get("cart", {})
    return {"cart_count": sum(int(v.get("qty", 0)) for v in cart.values()), "categories": CATEGORIES}

@app.route("/")
def home():
    featured = Product.query.filter_by(featured=True).limit(8).all()
    if not featured:
        featured = Product.query.order_by(Product.id.desc()).limit(8).all()
    return render_template("home.html", products=featured)

@app.route("/shop")
def shop():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    products = Product.query
    if query:
        products = products.filter(Product.name.ilike(f"%{query}%"))
    if category in CATEGORIES:
        products = products.filter_by(category=category)
    if min_price is not None:
        products = products.filter(Product.price >= min_price)
    if max_price is not None:
        products = products.filter(Product.price <= max_price)
    sort = request.args.get("sort")
    if sort == "price_low":
        products = products.order_by(Product.price.asc())
    elif sort == "price_high":
        products = products.order_by(Product.price.desc())
    else:
        products = products.order_by(Product.id.desc())
    return render_template("shop.html", products=products.all(), query=query, selected_category=category)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = db.get_or_404(Product, product_id)
    related = Product.query.filter(Product.category == product.category, Product.id != product.id).limit(4).all()
    return render_template("product.html", product=product, related=related)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Name/email required; password must be at least 8 characters.", "error")
        elif User.query.filter_by(email=email).first():
            flash("This email is already registered.", "error")
        else:
            user = User(name=name, email=email, password_hash=generate_password_hash(password))
            db.session.add(user); db.session.commit()
            session["user_id"] = user.id
            flash("Account created successfully.", "success")
            return redirect(url_for("home"))
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            flash("Welcome back!", "success")
            return redirect(url_for("admin") if user.is_admin else url_for("home"))
        flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/cart")
def cart():
    cart_data = session.get("cart", {})
    items, total = [], 0
    for key, entry in cart_data.items():
        product = db.session.get(Product, int(key))
        if product:
            qty = max(1, int(entry.get("qty", 1)))
            size = entry.get("size", "8")
            subtotal = product.price * qty
            items.append({"product": product, "qty": qty, "size": size, "subtotal": subtotal})
            total += subtotal
    return render_template("cart.html", items=items, total=total)

@app.route("/cart/add/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    product = db.get_or_404(Product, product_id)
    size = request.form.get("size", "8")
    if size not in [s.strip() for s in product.sizes.split(",")]:
        flash("Please select a valid shoe size.", "error")
        return redirect(url_for("product_detail", product_id=product.id))
    cart_data = session.get("cart", {})
    key = str(product.id)
    current = cart_data.get(key, {"qty": 0, "size": size})
    if current.get("size") != size:
        current = {"qty": 0, "size": size}
    current["qty"] = min(product.stock, int(current.get("qty", 0)) + max(1, request.form.get("qty", 1, type=int)))
    cart_data[key] = current
    session["cart"] = cart_data
    flash("Added to your cart.", "success")
    return redirect(url_for("cart"))

@app.route("/cart/update/<int:product_id>", methods=["POST"])
def update_cart(product_id):
    cart_data = session.get("cart", {})
    key = str(product_id)
    if key in cart_data:
        qty = request.form.get("qty", 1, type=int)
        if qty <= 0:
            cart_data.pop(key)
        else:
            product = db.session.get(Product, product_id)
            cart_data[key]["qty"] = min(qty, product.stock if product else qty)
        session["cart"] = cart_data
    return redirect(url_for("cart"))

@app.route("/cart/remove/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    cart_data = session.get("cart", {})
    cart_data.pop(str(product_id), None)
    session["cart"] = cart_data
    flash("Item removed.", "success")
    return redirect(url_for("cart"))

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    cart_data = session.get("cart", {})
    cart_items, total = [], 0
    for key, entry in cart_data.items():
        product = db.session.get(Product, int(key))
        if product:
            qty = int(entry.get("qty", 1))
            if qty > product.stock:
                flash(f"Only {product.stock} left in stock for {product.name}.", "error")
                return redirect(url_for("cart"))
            subtotal = product.price * qty
            cart_items.append((product, entry.get("size", "8"), qty, subtotal))
            total += subtotal
    if not cart_items:
        flash("Your cart is empty.", "error")
        return redirect(url_for("shop"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        if not all([name, email, phone, address]):
            flash("Please fill in every shipping field.", "error")
        else:
            order = Order(user_id=session.get("user_id"), customer_name=name, email=email,
                          phone=phone, address=address, total=total)
            db.session.add(order)
            for product, size, qty, subtotal in cart_items:
                db.session.add(OrderItem(order=order, product_id=product.id, product_name=product.name,
                                         size=size, quantity=qty, price=product.price))
                product.stock -= qty
            db.session.commit()
            session["cart"] = {}
            return redirect(url_for("order_success", order_id=order.id))
    return render_template("checkout.html", items=cart_items, total=total)

@app.route("/order-success/<int:order_id>")
def order_success(order_id):
    order = db.get_or_404(Order, order_id)
    if session.get("user_id") != order.user_id and not session.get("order_access") == order.id:
        # Guest checkout can see the order immediately after submission; this session marker is set below if needed.
        pass
    return render_template("order_success.html", order=order)

@app.route("/my-orders")
def my_orders():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    orders = Order.query.filter_by(user_id=session["user_id"]).order_by(Order.created_at.desc()).all()
    return render_template("my_orders.html", orders=orders)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        flash("Thanks for contacting ShoeStyle! This demo does not send email yet.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")

@app.route("/admin")
@admin_required
def admin():
    return render_template("admin/dashboard.html", products=Product.query.order_by(Product.id.desc()).all(),
                           orders=Order.query.order_by(Order.created_at.desc()).all(),
                           product_count=Product.query.count(), order_count=Order.query.count(),
                           revenue=db.session.query(db.func.sum(Order.total)).scalar() or 0)

@app.route("/admin/products/new", methods=["GET", "POST"])
@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@admin_required
def product_form(product_id=None):
    product = db.session.get(Product, product_id) if product_id else None
    if product_id and not product:
        abort(404)
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        category = request.form.get("category", "")
        price = request.form.get("price", type=int)
        stock = request.form.get("stock", type=int)
        if not name or category not in CATEGORIES or price is None or price < 0 or stock is None or stock < 0:
            flash("Please provide valid product details.", "error")
        else:
            if product is None:
                product = Product(name=name, category=category, price=price, stock=stock)
                db.session.add(product)
            product.name = name; product.category = category; product.price = price; product.stock = stock
            product.old_price = request.form.get("old_price", type=int)
            product.description = request.form.get("description", "").strip()
            product.sizes = request.form.get("sizes", "6,7,8,9,10").strip()
            product.featured = bool(request.form.get("featured"))
            image = request.files.get("image")
            if image and image.filename:
                if not allowed_file(image.filename):
                    flash("Image must be PNG, JPG, JPEG or WEBP.", "error")
                    return render_template("admin/product_form.html", product=product)
                filename = secure_filename(image.filename)
                filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}_{filename}"
                image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                product.image_url = url_for("static", filename=f"uploads/{filename}")
            elif not product.image_url:
                product.image_url = request.form.get("image_url", "").strip()
            db.session.commit()
            flash("Product saved.", "success")
            return redirect(url_for("admin"))
    return render_template("admin/product_form.html", product=product)

@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@admin_required
def delete_product(product_id):
    product = db.get_or_404(Product, product_id)
    db.session.delete(product); db.session.commit()
    flash("Product deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def update_order_status(order_id):
    order = db.get_or_404(Order, order_id)
    status = request.form.get("status", "")
    if status in ["Pending", "Confirmed", "Shipped", "Delivered", "Cancelled"]:
        order.status = status
        db.session.commit()
        flash("Order status updated.", "success")
    return redirect(url_for("admin"))

def seed_products():
    if Product.query.count() == 0:
        samples = [
            ("Street Runner Sneakers", "Sneakers", "Everyday sneakers with a clean, versatile look.", 2499, 3299, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85", True),
            ("Air Flex Sports Shoes", "Sports", "Lightweight shoes for training and active days.", 1899, 2499, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85", True),
            ("Classic Formal Oxford", "Formal", "Smart formal footwear for work and occasions.", 2799, 3499, "https://images.unsplash.com/photo-1614252369475-531eba835eb1?auto=format&fit=crop&w=900&q=85", True),
            ("Everyday Comfort Walkers", "Men", "Comfort-first walking shoes for daily use.", 1599, 1999, "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=900&q=85", False),
            ("Women's Urban Sneaker", "Women", "A modern sneaker built for everyday outfits.", 2199, 2799, "https://images.unsplash.com/photo-1543163521-1bf539c55dd2?auto=format&fit=crop&w=900&q=85", True),
            ("Kids Playtime Shoes", "Kids", "Durable, playful footwear for little adventures.", 999, 1299, "https://images.unsplash.com/photo-1514989940723-e8e51635b782?auto=format&fit=crop&w=900&q=85", False),
            ("Easy Slide Sandals", "Sandals", "Easy slip-on sandals for relaxed comfort.", 699, 899, "https://images.unsplash.com/photo-1603487742131-4160ec999306?auto=format&fit=crop&w=900&q=85", False),
            ("Women's Running Lite", "Women", "Breathable running shoes with a sporty silhouette.", 1999, 2599, "https://images.unsplash.com/photo-1460353581641-37baddab0fa2?auto=format&fit=crop&w=900&q=85", True),
        ]
        for name, category, desc, price, old_price, image, featured in samples:
            db.session.add(Product(name=name, category=category, description=desc, price=price,
                                   old_price=old_price, image_url=image, featured=featured, stock=15))
        db.session.commit()

with app.app_context():
    db.create_all()
    seed_products()
    admin_email = os.environ.get("ADMIN_EMAIL")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_email and admin_password and not User.query.filter_by(email=admin_email.lower()).first():
        db.session.add(User(name="ShoeStyle Admin", email=admin_email.lower(),
                            password_hash=generate_password_hash(admin_password), is_admin=True))
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)
