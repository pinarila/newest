from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import mysql.connector
import random
import string
from math import ceil
from datetime import datetime, timedelta
from flask import send_file
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from sklearn.neighbors import KNeighborsRegressor
import numpy as np


app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Generate random ID (4 letters + 3 digits)
def generate_id():
    letters = ''.join(random.choices(string.ascii_uppercase, k=4))
    digits = ''.join(random.choices(string.digits, k=3))
    return letters + digits

# Connect to MySQL
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="predict_penjualan"
    )

# Dashboard route
@app.route('/')
def dashboard():
    return render_template('index.html')

# Category CRUD
@app.route('/category', methods=['GET', 'POST'])
def category():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        category_id = request.form.get('catID')
        category_name = request.form.get('catName')

        if not category_id or category_id.strip() == "":
            category_id = generate_id()

        cursor.execute('SELECT * FROM category WHERE id = %s OR name = %s', (category_id, category_name))
        existing_category = cursor.fetchone()

        if existing_category:
            flash('Kategori sudah ada dengan ID atau Nama tersebut.', 'error')
        else:
            cursor.execute('INSERT INTO category (id, name) VALUES (%s, %s)', (category_id, category_name))
            conn.commit()
            flash('Kategori berhasil ditambahkan!', 'success')

        conn.close()
        return redirect(url_for('category'))

    search_query = request.args.get('search')
    if search_query:
        cursor.execute("SELECT * FROM category WHERE name LIKE %s", ('%' + search_query + '%',))
    else:
        cursor.execute('SELECT * FROM category')

    categories = cursor.fetchall()
    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_pages = ceil(len(categories) / per_page)
    start = (page - 1) * per_page
    categories = categories[start:start + per_page]

    conn.close()
    return render_template('category.html', categories=categories, page=page, total_pages=total_pages)

@app.route('/update/<category_id>', methods=['POST'])
def update_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    new_name = request.form['catName']
    cursor.execute('UPDATE category SET name = %s WHERE id = %s', (new_name, category_id))
    conn.commit()
    conn.close()

    flash('Kategori berhasil diperbarui!', 'success')
    return redirect(url_for('category'))

@app.route('/delete/<category_id>')
def delete_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM category WHERE id = %s', (category_id,))
    conn.commit()
    conn.close()

    flash('Kategori berhasil dihapus!', 'success')
    return redirect(url_for('category'))

@app.route('/product', methods=['GET', 'POST'])
def list_product():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil semua kategori
    cursor.execute('SELECT id, name FROM category')
    categories = cursor.fetchall()

    # Handle POST untuk tambah produk
    if request.method == 'POST':
        product_id = request.form.get('productID')
        product_name = request.form['productName']
        product_category = request.form['productCategory']
        product_unit = request.form['productUnit']
        product_price = request.form['productPrice']
        product_initial_price = request.form['productInitialPrice']

        if not product_id or product_id.strip() == "":
            product_id = generate_id()

        try:
            cursor.execute(
                '''
                INSERT INTO product (id, name, category, unit, price, initial_price)
                VALUES (%s, %s, %s, %s, %s, %s)
                ''',
                (product_id, product_name, product_category, product_unit, product_price, product_initial_price)
            )
            conn.commit()
            flash('Produk berhasil ditambahkan!', 'success')
        except mysql.connector.Error as e:
            flash(f'Gagal menambahkan produk: {str(e)}', 'danger')
        finally:
            conn.close()
            return redirect(url_for('list_product'))

    # GET: Search dan Pagination
    search_query = request.args.get('search')
    sql = '''
        SELECT p.id, p.name, c.name AS category_name, p.unit, p.price, p.initial_price
        FROM product p
        JOIN category c ON p.category = c.id
    '''
    params = []

    if search_query:
        sql += " WHERE p.name LIKE %s OR c.name LIKE %s"
        params.extend(['%' + search_query + '%'] * 2)

    cursor.execute(sql, params)
    products = cursor.fetchall()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_pages = ceil(len(products) / per_page)
    start = (page - 1) * per_page
    products = products[start:start + per_page]

    conn.close()
    return render_template(
        'product.html',
        categories=categories,
        products=products,
        page=page,
        total_pages=total_pages
    )

@app.route('/update_product/<product_id>', methods=['POST'])
def update_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    new_name = request.form['productName']
    new_category = request.form['productCategory']
    new_unit = request.form['productUnit']
    new_price = request.form['productPrice']
    new_initial_price = request.form['productInitialPrice']

    try:
        cursor.execute(
            '''
            UPDATE product
            SET name=%s, category=%s, unit=%s, price=%s, initial_price=%s
            WHERE id=%s
            ''',
            (new_name, new_category, new_unit, new_price, new_initial_price, product_id)
        )
        conn.commit()
        flash('Produk berhasil diperbarui!', 'success')
    except mysql.connector.Error as e:
        flash(f'Gagal memperbarui produk: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('list_product'))

@app.route('/delete_product/<product_id>', methods=['GET'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM product WHERE id=%s', (product_id,))
        conn.commit()
        flash('Produk berhasil dihapus!', 'success')
    except mysql.connector.Error as e:
        flash(f'Gagal menghapus produk: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('list_product'))

@app.route('/stock', methods=['GET', 'POST'])
def list_stock():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil data produk & kategori untuk dropdown
    cursor.execute('SELECT id, name FROM product')
    products = cursor.fetchall()

    cursor.execute('SELECT id, name FROM category')
    categories = cursor.fetchall()

    if request.method == 'POST':
        stock_id = request.form.get('stockID')
        product_id = request.form.get('productID')
        manual_product_id = request.form.get('manualProductID')
        product_id = manual_product_id.strip() if manual_product_id and manual_product_id.strip() else product_id
        tanggal = request.form['tanggal']
        jumlah = request.form['jumlahStok']

        if not stock_id or stock_id.strip() == "":
            stock_id = generate_id()

        try:
            cursor.execute(
                'INSERT INTO stock (id_stok, id_produk, tanggal, jumlah_stok) VALUES (%s, %s, %s, %s)',
                (stock_id, product_id, tanggal, jumlah)
            )
            conn.commit()
            flash('Stok berhasil ditambahkan!', 'success')
        except mysql.connector.Error as e:
            flash(f'Gagal menambahkan stok: {str(e)}', 'danger')
        finally:
            conn.close()
            return redirect(url_for('list_stock'))

    # Handle GET: Search & Pagination
    search_query = request.args.get('search')
    sql = """
        SELECT s.id_stok, p.name, s.tanggal, s.jumlah_stok
        FROM stock s
        JOIN product p ON s.id_produk = p.id
    """
    params = []

    if search_query:
        sql += " WHERE p.name LIKE %s"
        params.append('%' + search_query + '%')

    cursor.execute(sql, params)
    stocks = cursor.fetchall()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_pages = ceil(len(stocks) / per_page)
    start = (page - 1) * per_page
    stocks = stocks[start:start + per_page]

    conn.close()

    return render_template(
        'stock.html',
        products=products,
        categories=categories,
        stocks=stocks,
        page=page,
        total_pages=total_pages
    )

@app.route('/update_stock/<stock_id>', methods=['POST'])
def update_stock(stock_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    product_id = request.form['productID']
    manual_product_id = request.form.get('manualProductID')
    product_id = manual_product_id.strip() if manual_product_id and manual_product_id.strip() else product_id
    tanggal = request.form['tanggal']
    jumlah = request.form['jumlahStok']

    cursor.execute(
        'UPDATE stock SET id_produk=%s, tanggal=%s, jumlah_stok=%s WHERE id_stok=%s',
        (product_id, tanggal, jumlah, stock_id)
    )
    conn.commit()
    conn.close()

    flash('Stok berhasil diperbarui!', 'success')
    return redirect(url_for('list_stock'))

@app.route('/delete_stock/<stock_id>')
def delete_stock(stock_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM stock WHERE id_stok=%s', (stock_id,))
        conn.commit()
        flash('Stok berhasil dihapus!', 'success')
    except mysql.connector.Error as e:
        flash(f'Gagal menghapus stok: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('list_stock'))

@app.route('/get_products_by_category/<category_id>')
def get_products_by_category(category_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT id, name FROM product WHERE category = %s', (category_id,))
    products = cursor.fetchall()

    conn.close()
    return jsonify(products)

@app.route('/sales', methods=['GET', 'POST'])
def list_sales():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # <-- PENTING!

    cursor.execute('SELECT id, name FROM category')
    categories = cursor.fetchall()

    cursor.execute('SELECT id, name FROM product')
    products = cursor.fetchall()

    if request.method == 'POST':
        sales_id = request.form.get('salesID')
        product_id = request.form.get('productID')
        tanggal = request.form['tanggal']
        jumlah = request.form['jumlahPenjualan']

        if not sales_id or sales_id.strip() == "":
            sales_id = generate_id()

        try:
            cursor.execute(
                'INSERT INTO sales (id_penjualan, id_produk, tanggal, jumlah) VALUES (%s, %s, %s, %s)',
                (sales_id, product_id, tanggal, jumlah)
            )
            conn.commit()
            flash('Penjualan berhasil ditambahkan!', 'success')
        except mysql.connector.Error as e:
            flash(f'Gagal menambahkan penjualan: {str(e)}', 'danger')
        finally:
            conn.close()
            return redirect(url_for('list_sales'))

    # Handle GET: Search & Pagination
    search_query = request.args.get('search')
    sql = """
    SELECT s.id_penjualan, s.id_produk, p.name AS product_name, s.tanggal, s.jumlah
    FROM sales s
    JOIN product p ON s.id_produk = p.id
    """

    params = []

    if search_query:
        sql += " WHERE p.name LIKE %s"
        params.append('%' + search_query + '%')

    cursor.execute(sql, params)
    sales = cursor.fetchall()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_pages = ceil(len(sales) / per_page)
    start = (page - 1) * per_page
    sales = sales[start:start + per_page]

    conn.close()

    return render_template(
        'sales.html',
        sales=sales,
        categories=categories,
        products=products,
        page=page,
        total_pages=total_pages
    )

@app.route('/update_sale/<sales_id>', methods=['POST'])
def update_sale(sales_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    product_id = request.form['productID']
    tanggal = request.form['tanggal']
    jumlah = request.form['jumlahPenjualan']

    cursor.execute(
        'UPDATE sales SET id_produk=%s, tanggal=%s, jumlah=%s WHERE id_penjualan=%s',
        (product_id, tanggal, jumlah, sales_id)
    )
    conn.commit()
    conn.close()

    flash('Penjualan berhasil diperbarui!', 'success')
    return redirect(url_for('list_sales'))

@app.route('/delete_sale/<sales_id>')
def delete_sale(sales_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('DELETE FROM sales WHERE id_penjualan=%s', (sales_id,))
        conn.commit()
        flash('Penjualan berhasil dihapus!', 'success')
    except mysql.connector.Error as e:
        flash(f'Gagal menghapus penjualan: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('list_sales'))

@app.route('/predictions', methods=['GET', 'POST'])
def list_predictions():
    conn = get_db_connection()
    cursor = conn.cursor()  # rekomendasi dict cursor

    cursor.execute('SELECT id, name FROM category')
    categories = cursor.fetchall()

    cursor.execute('SELECT id, name FROM product')
    products = cursor.fetchall()

    # ✅ Tambahkan logika POST
    if request.method == 'POST':
        product_id = request.form['productID']
        jumlah_prediksi = request.form['jumlahPrediksi']
        pred_id = generate_id()

        try:
            cursor.execute(
                'INSERT INTO prediction (id_prediksi, id_produk, jumlah_prediksi) VALUES (%s, %s, %s)',
                (pred_id, product_id, jumlah_prediksi)
            )
            conn.commit()
            flash('Prediksi berhasil ditambahkan!', 'success')
        except Exception as e:
            flash(f'Gagal menambahkan prediksi: {str(e)}', 'danger')
        finally:
            return redirect(url_for('list_predictions'))

    # ✅ Search + pagination logic tetap
    search_query = request.args.get('search')
    sql = """
        SELECT pr.id_prediksi, p.name, pr.jumlah_prediksi, p.id
        FROM prediction pr
        JOIN product p ON pr.id_produk = p.id
    """
    params = []
    if search_query:
        sql += " WHERE p.name LIKE %s"
        params.append('%' + search_query + '%')

    cursor.execute(sql, params)
    predictions = cursor.fetchall()

    page = request.args.get('page', 1, type=int)
    per_page = 5
    total_pages = ceil(len(predictions) / per_page)
    start = (page - 1) * per_page
    predictions = predictions[start:start + per_page]

    conn.close()

    return render_template(
        'predictions.html',
        predictions=predictions,
        categories=categories,
        products=products,
        page=page,
        total_pages=total_pages
    )

@app.route('/update_prediction/<pred_id>', methods=['POST'])
def update_prediction(pred_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    product_id = request.form['productID']
    jumlah_prediksi = request.form['jumlahPrediksi']

    try:
        cursor.execute(
            'UPDATE prediction SET id_produk=%s, jumlah_prediksi=%s WHERE id_prediksi=%s',
            (product_id, jumlah_prediksi, pred_id)
        )
        conn.commit()
        flash('Prediksi berhasil diperbarui!', 'success')
    except Exception as e:
        flash(f'Gagal memperbarui prediksi: {str(e)}', 'danger')
    finally:
        conn.close()

    return redirect(url_for('list_predictions'))

@app.route('/delete_prediction/<pred_id>')
def delete_prediction(pred_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM prediction WHERE id_prediksi=%s', (pred_id,))
        conn.commit()
        flash('Prediksi berhasil dihapus!', 'success')
    except Exception as e:
        flash(f'Gagal menghapus prediksi: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('list_predictions'))

@app.route('/predict_sales', methods=['GET'])
def predict_sales():
    k = int(request.args.get('k', 3))
    range_value = request.args.get('range', 'day')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ambil data historis penjualan
    cursor.execute("""
        SELECT id_produk, tanggal, jumlah
        FROM sales
        ORDER BY tanggal
    """)
    raw_sales = cursor.fetchall()

    # Mapping ID produk string → angka
    product_id_map = {}
    id_counter = 1

    X, y = [], []


    for sale in raw_sales:
        product_id, tanggal, jumlah = sale

        # Pastikan semua ID produk dikonversi ke angka
        if product_id not in product_id_map:
            product_id_map[product_id] = id_counter
            id_counter += 1
        product_num_id = product_id_map[product_id]

        # Ubah tanggal ke angka
        if not isinstance(tanggal, datetime):
            tanggal = datetime.strptime(str(tanggal), "%Y-%m-%d")
        days_since = (tanggal - datetime(2000, 1, 1)).days

        X.append([product_num_id, days_since])
        y.append(jumlah)

    if not X:
        flash("Data penjualan tidak cukup untuk prediksi.", "warning")
        return redirect(url_for('list_predictions'))

    # Fit model
    knn = KNeighborsRegressor(n_neighbors=k)
    knn.fit(X, y)

    # Ambil semua produk
    cursor.execute("SELECT id, name FROM product")
    products = cursor.fetchall()

    now = datetime.now()
    if range_value == 'week':
        predict_days = 7
    elif range_value == 'month':
        predict_days = 30
    else:
        predict_days = 1

    future_days = (now - datetime(2000, 1, 1)).days + predict_days

    predictions_result = []

    for product_id, product_name in products:
        if product_id not in product_id_map:
            continue  # skip produk tanpa data historis

        product_num_id = product_id_map[product_id]
        prediction = knn.predict([[product_num_id, future_days]])
        predicted_amount = max(int(prediction[0]), 0)  # hindari negatif

        predictions_result.append((product_id, product_name, predicted_amount))

    conn.close()

    return render_template(
        'predictions.html',
        predictions=predictions_result,  # hasil prediksi
        categories=[],
        products=[],
        page=1,
        total_pages=1
    )

if __name__ == '__main__':
    app.run(debug=True)
