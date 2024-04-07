from flask import Flask, jsonify, render_template, Response, abort, make_response #jsonify will create python dictionaries into jsonify responses
import sqlite3    # this is another module being imported, it will help when interacting with SQLite databases
import pathlib    #this is a module that will help us handle file systems
import logging
import requests  # Importing the requests library
 
# Setup logging
logging.basicConfig(filename="app.log", level=logging.DEBUG)
 
working_directory = pathlib.Path(__file__).parent.absolute()
DATABASE = working_directory / "CCL_ecommerce.db"
 
 
def query_db(query: str, args=()) -> list:     #this is a function that connects this project to the SQLite database. this functions executes a given query and the returns the result
    try:                                          #this functions prevents repetition in code
        with sqlite3.connect(DATABASE) as conn:  #the sqlite3.connect database connects to the SQL datbase 
            cursor = conn.cursor()
            result = cursor.execute(query, args).fetchall()
        return result
    except sqlite3.Error as e:
        logging.error("Database error: %s", e)
        abort(500, description="Database error occurred.")
 
 
app = Flask(__name__) # sets a prescence for Flask that allows us to define route and handle requests
 
 
@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({"error": "Not found"}), 404)
 
 
@app.errorhandler(500)
def internal_error(error):
    return make_response(jsonify({"error": "Internal server error"}), 500)
 
 
@app.route("/")   #routes in flask are defined using '@app.route'
def index() -> str:
    return render_template("dashboard.html")  #shows how our flask application recognises different routes and will deliver the corresponding data 
 
 
@app.route("/api/temperature_over_time", methods=["GET"]) #app route is defined and will return a json response, containing temperature_over_time from our SQLite database
def temperature_over_time():
    # Fetching the date range from orders_over_time
    query = """
SELECT MIN(order_date), MAX(order_date)
FROM orders;
"""
    try:
        result = query_db(query)
        start_date, end_date = result[0]
 
        # Making an API call to fetch temperature data
        API_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": 50.6053,  # London UK
            "longitude": -3.5952,
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max",
            "timezone": "GMT",
        }
        response = requests.get(API_ENDPOINT, params=params)
        response.raise_for_status()
 
        return jsonify(response.json())
    except Exception as e:
        logging.error("Error in /api/temperature_over_time: %s", e)
        abort(500, description="Error fetching temperature data.")
 
 
@app.route("/api/orders_over_time")   #this is the code for our first API 
def orders_over_time() -> Response:        #the API function connects to the SQLite database, executes a SQL query. 
    query = """
    SELECT order_date, COUNT(order_id) AS num_orders
    FROM orders
    GROUP BY order_date
    ORDER BY order_date;
    """
    try:
        result = query_db(query)
        dates = [row[0] for row in result]
        counts = [row[1] for row in result]
        return jsonify({"dates": dates, "counts": counts})  #returns JSON data
    except Exception as e:
        logging.error("Error in /api/orders_over_time: %s", e)
        abort(500, description="Error processing data.")
 
 
@app.route("/api/low_stock_levels")   #second API endpoint
def low_stock_levels() -> Response:
    query = """
    SELECT p.product_name, s.quantity
    FROM stock_level s
    JOIN products p ON s.product_id = p.product_id
    ORDER BY s.quantity ASC;
    """
    result = query_db(query)
 
    products = [row[0] for row in result]
    quantities = [row[1] for row in result]
    return jsonify({"products": products, "quantities": quantities}) #returns JSON data
 
 
@app.route("/api/most_popular_products")
def most_popular_products_new() -> Response:
    query = """
    SELECT p.product_id, p.product_name, SUM(od.quantity_ordered) AS total_quantity
    FROM order_details od
    JOIN products p ON od.product_id = p.product_id
    GROUP BY p.product_id, p.product_name
    ORDER BY total_quantity DESC
    LIMIT 10;
    """
    result = query_db(query)
 
    products = [
        {"product_id": row[0], "product_name": row[1], "total_quantity": row[2]}
        for row in result
    ]
    return jsonify(products)
 
 
@app.route("/api/revenue_generation")
def revenue_generation() -> Response:
    query = """
    SELECT o.order_date, SUM(od.price_at_time * od.quantity_ordered) AS total_revenue
    FROM order_details od
    JOIN orders o ON od.order_id = o.order_id
    GROUP BY o.order_date
    ORDER BY o.order_date;
    """
    result = query_db(query)
 
    dates = [row[0] for row in result]
    revenues = [row[1] for row in result]
    return jsonify({"dates": dates, "revenues": revenues})
 
 
@app.route("/api/product_category_popularity")
def product_category_popularity() -> Response:
    query = """
    SELECT pc.category_name, SUM(od.price_at_time * od.quantity_ordered) AS total_sales
    FROM products p
    JOIN product_categories pc ON p.category_id = pc.category_id
    JOIN order_details od ON p.product_id = od.product_id
    GROUP BY pc.category_name
    ORDER BY total_sales DESC;
    """
    result = query_db(query)
 
    categories = [row[0] for row in result]
    sales = [row[1] for row in result]
    return jsonify({"categories": categories, "sales": sales})
 
 
@app.route("/api/payment_method_popularity")
def payment_method_popularity() -> Response:
    query = """
    SELECT pm.method_name, COUNT(p.payment_id) AS transaction_count
    FROM payments p
    JOIN payment_methods pm ON p.method_id = pm.method_id
    GROUP BY pm.method_name
    ORDER BY transaction_count DESC;
    """
    result = query_db(query)
 
    methods = [row[0] for row in result]
    counts = [row[1] for row in result]
    return jsonify({"methods": methods, "counts": counts})
 
 
if __name__ == "__main__":
    app.run(debug=True)  #this debugger activates the flask server
                        #debug equals true argument allows for real time code changes to reflect without restarting our server