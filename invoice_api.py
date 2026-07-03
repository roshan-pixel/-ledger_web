from flask import Blueprint, request, jsonify
import sqlite3
import datetime

invoice_api = Blueprint('invoice_api', __name__)

DB_PATH = 'invoices.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            amount REAL NOT NULL,
            date_created TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize the database table if it doesn't exist
init_db()

@invoice_api.route('/api/invoice/create', methods=['POST'])
def create_invoice():
    data = request.get_json()
    if not data or 'customer_name' not in data or 'amount' not in data:
        return jsonify({'error': 'Missing customer_name or amount'}), 400
    
    customer_name = data['customer_name']
    amount = data['amount']
    date_created = datetime.datetime.now().isoformat()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            'INSERT INTO invoices (customer_name, amount, date_created) VALUES (?, ?, ?)',
            (customer_name, amount, date_created)
        )
        invoice_id = c.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Invoice created successfully',
            'invoice_id': invoice_id,
            'customer_name': customer_name,
            'amount': amount,
            'date_created': date_created
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoice_api.route('/api/invoice/list', methods=['GET'])
def list_invoices():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, customer_name, amount, date_created FROM invoices')
        rows = c.fetchall()
        conn.close()
        
        invoices = [
            {
                'id': row[0],
                'customer_name': row[1],
                'amount': row[2],
                'date_created': row[3]
            }
            for row in rows
        ]
        return jsonify({'invoices': invoices}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
