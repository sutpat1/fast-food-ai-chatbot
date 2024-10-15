from flask import Flask, request, render_template_string, session, redirect, url_for
import spacy
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Load the spaCy model for NLP processing
nlp = spacy.load('en_core_web_sm')

# Load the menu data from CSV file
menu_data = pd.read_csv('In N Out Menu.csv')

# Normalize menu items: Convert to lowercase
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower()
menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Word to number mapping
word_to_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

# Function to replace numerals with words
def replace_numerals_with_words(text):
    num_to_word = {str(value): key for key, value in word_to_num.items()}
    def replace(match):
        return num_to_word.get(match.group(0), match.group(0))
    return re.sub(r'\b\d+\b', replace, text)

# Function to get menu items
def get_menu_items():
    menu_items = []
    for item, price in menu_dict.items():
        menu_items.append({'name': item.title(), 'price': f"${price:.2f}"})
    return menu_items

# Function to parse and process the order
def parse_order(user_input):
    user_input = user_input.lower()
    user_input = replace_numerals_with_words(user_input)
    doc = nlp(user_input)
    found_items = []
    quantity = 1

    # Extract quantities and items
    for token in doc:
        if token.like_num:
            try:
                quantity = int(token.text)
            except ValueError:
                quantity = word_to_num.get(token.text.lower(), 1)
        elif token.text in word_to_num:
            quantity = word_to_num[token.text]
        elif token.text in menu_dict:
            found_items.append((token.text, quantity))
            quantity = 1  # Reset quantity after finding an item

    if found_items:
        for item, qty in found_items:
            # Update session data
            if 'order' not in session:
                session['order'] = {}
            if item in session['order']:
                session['order'][item] += qty
            else:
                session['order'][item] = qty
    else:
        return "Sorry, I didn't understand your order."

    return ""

# Flask routes
@app.route('/')
def index():
    session.clear()
    session['order'] = {}
    session['total'] = 0.0
    menu_items = get_menu_items()
    # HTML template as a string
    index_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>In-N-Out Chatbot</title>
    </head>
    <body>
        <div style="text-align: center;">
            <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
            <h1>Welcome to In-N-Out!</h1>
            <h2>Here's our menu:</h2>
            <ul style="list-style-type: none;">
                {% for item in menu %}
                    <li>{{ item.name }}: {{ item.price }}</li>
                {% endfor %}
            </ul>
            <a href="{{ url_for('chat') }}">Start Ordering</a>
        </div>
    </body>
    </html>
    '''
    return render_template_string(index_html, menu=menu_items)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'order' not in session:
        session['order'] = {}
    response = ""
    if request.method == 'POST':
        if 'complete_order' in request.form:
            return redirect(url_for('summary'))
        user_input = request.form['message']
        response = parse_order(user_input)
        if response == "":
            response = "Item(s) added to your order."
    # Generate the current order summary
    order_summary = ""
    total_price = 0
    if 'order' in session and session['order']:
        order_summary += "<h3>Your current order:</h3><ul style='list-style-type: none;'>"
        for item, qty in session['order'].items():
            item_price = menu_dict[item] * qty
            total_price += item_price
            order_summary += f"<li>{qty} x {item.title()} - ${item_price:.2f}</li>"
        order_summary += f"</ul><p>Total: ${total_price:.2f}</p>"
    else:
        order_summary = "<p>Your order is currently empty.</p>"
    # HTML template as a string
    chat_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>In-N-Out Chatbot</title>
    </head>
    <body>
        <div style="text-align: center;">
            <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
            <h1>In-N-Out Ordering Chatbot</h1>
            <div>
                {% if response %}
                    <p>{{ response|safe }}</p>
                {% endif %}
            </div>
            <div>
                {{ order_summary|safe }}
            </div>
            <form method="post">
                <input type="text" name="message" placeholder="Type your message here..." required size="50">
                <input type="submit" value="Send">
                <input type="submit" name="complete_order" value="Complete Order">
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(chat_html, response=response, order_summary=order_summary)

@app.route('/summary')
def summary():
    # Generate the final order summary
    if 'order' not in session or not session['order']:
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Order Summary</title>
            </head>
            <body>
                <div style="text-align: center;">
                    <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
                    <h1>You haven't ordered anything yet.</h1>
                    <a href="{{ url_for('chat') }}">Go back to order</a>
                </div>
            </body>
            </html>
        ''')
    else:
        order_summary = "<h3>Your final order:</h3><ul style='list-style-type: none;'>"
        total_price = 0
        for item, qty in session['order'].items():
            item_price = menu_dict[item] * qty
            total_price += item_price
            order_summary += f"<li>{qty} x {item.title()} - ${item_price:.2f}</li>"
        order_summary += f"</ul><h3>Total: ${total_price:.2f}</h3>"
        # Clear the session after showing the summary
        session.clear()
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Order Summary</title>
            </head>
            <body>
                <div style="text-align: center;">
                    <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
                    {{ order_summary|safe }}
                    <p>Thank you for your order!</p>
                    <a href="{{ url_for('index') }}">Start a new order</a>
                </div>
            </body>
            </html>
        ''', order_summary=order_summary)

if __name__ == '__main__':
    app.run(debug=True)
