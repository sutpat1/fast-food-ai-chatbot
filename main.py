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

# Normalize menu items: Convert to lowercase, replace dashes with spaces
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower().str.replace('-', ' ')

# Replace specific items for consistency
menu_data['Menu Item'] = menu_data['Menu Item'].replace({
    'cheese burger': 'cheeseburger',
    'shakes': 'shake',
    'number 1 meal': 'number one meal',
    'number 2 meal': 'number two meal',
    'number 3 meal': 'number three meal',
})

menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Create a mapping from lemmatized menu items to canonical menu item names
lemmatized_menu_items = {}
for item in menu_dict.keys():
    item_doc = nlp(item)
    lemmatized_item = ' '.join([token.lemma_ for token in item_doc])
    lemmatized_menu_items[lemmatized_item] = item

# Dictionaries for converting written numbers to integers and digits to words
word_to_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

num_to_word = {str(value): key for key, value in word_to_num.items()}


# Function to replace numerals with words
def replace_numerals_with_words(text):
    def replace_match(match):
        return num_to_word.get(match.group(0), match.group(0))

    return re.sub(r'\b\d+\b', replace_match, text)


# Function to get menu items
def get_menu_items():
    menu_items = []
    for item, price in menu_dict.items():
        menu_items.append({'name': item.title(), 'price': f"${price:.2f}"})
    return menu_items


# Function to parse order
def parse_order(user_input):
    user_input_lower = user_input.lower().replace('-', ' ')
    user_input_lower = replace_numerals_with_words(user_input_lower)
    user_input_lower = user_input_lower.replace('shakes', 'shake')

    doc = nlp(user_input_lower)
    order = []
    total = 0

    for chunk in doc.noun_chunks:
        quantity = 1
        item_name = None

        tokens = [token for token in chunk if not token.is_stop]
        if len(tokens) == 0:
            continue

        if tokens[0].lemma_ in word_to_num:
            quantity = word_to_num[tokens[0].lemma_]
            item_tokens = tokens[1:]
        elif tokens[0].like_num:
            try:
                quantity = int(tokens[0].text)
            except ValueError:
                quantity = 1
            item_tokens = tokens[1:]
        else:
            item_tokens = tokens

        item_candidate = ' '.join([token.lemma_ for token in item_tokens])
        item_name = lemmatized_menu_items.get(item_candidate)
        if not item_name:
            for lemmatized_item, original_item in lemmatized_menu_items.items():
                if item_candidate in lemmatized_item:
                    item_name = original_item
                    break

        if item_name:
            order.append((item_name, quantity))
            total += menu_dict[item_name] * quantity

    return order, total


# Function to parse removal
def parse_removal(user_input):
    user_input_lower = user_input.lower().replace('-', ' ')
    user_input_lower = replace_numerals_with_words(user_input_lower)
    user_input_lower = user_input_lower.replace('shakes', 'shake')

    doc = nlp(user_input_lower)
    removal_items = []

    for chunk in doc.noun_chunks:
        quantity = 1
        item_name = None

        tokens = [token for token in chunk if not token.is_stop]
        if len(tokens) == 0:
            continue

        if tokens[0].lemma_ in word_to_num:
            quantity = word_to_num[tokens[0].lemma_]
            item_tokens = tokens[1:]
        elif tokens[0].like_num:
            try:
                quantity = int(tokens[0].text)
            except ValueError:
                quantity = 1
            item_tokens = tokens[1:]
        else:
            item_tokens = tokens

        item_candidate = ' '.join([token.lemma_ for token in item_tokens])
        item_name = lemmatized_menu_items.get(item_candidate)
        if not item_name:
            for lemmatized_item, original_item in lemmatized_menu_items.items():
                if item_candidate in lemmatized_item:
                    item_name = original_item
                    break

        if item_name:
            removal_items.append((item_name, quantity))

    return removal_items


# Helper functions to handle additions and removals
def handle_addition(parsed_order):
    response = ""
    if parsed_order:
        for item, quantity in parsed_order:
            if 'order' not in session:
                session['order'] = {}
            if item in session['order']:
                session['order'][item] += quantity
            else:
                session['order'][item] = quantity
        response += "Item(s) added to your order."
    else:
        response += "Sorry, we couldn't find any items from the menu in your order."
    return response


def handle_removal(removal_items):
    response = ""
    if removal_items:
        for item, quantity in removal_items:
            if item in session['order']:
                if session['order'][item] > quantity:
                    session['order'][item] -= quantity
                    response += f"Removed {quantity} x {item.title()} from your order.<br>"
                elif session['order'][item] == quantity:
                    session['order'].pop(item)
                    response += f"Removed {quantity} x {item.title()} from your order.<br>"
                else:
                    response += f"You have only {session['order'][item]} x {item.title()} in your order. Removing all of them.<br>"
                    session['order'].pop(item)
            else:
                response += f"You don't have any {item.title()} in your order to remove.<br>"
    else:
        response += "Sorry, we couldn't find any items from the menu to remove in your request."
    return response


# Flask routes
@app.route('/')
def index():
    session.clear()
    session['order'] = {}
    menu_items = get_menu_items()
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
        elif 'message' in request.form and request.form['message'].strip() != '':
            user_input = request.form['message']
            user_input_lower = user_input.lower()
            if 'remove' in user_input_lower or 'cancel' in user_input_lower:
                removal_items = parse_removal(user_input)
                response = handle_removal(removal_items)
            else:
                parsed_order, parsed_total = parse_order(user_input)
                response = handle_addition(parsed_order)
        else:
            response = "Please enter a message."

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

    menu_items = get_menu_items()
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
            <div>
                <h2>Menu:</h2>
                <ul style="list-style-type: none;">
                    {% for item in menu %}
                        <li>{{ item.name }}: {{ item.price }}</li>
                    {% endfor %}
                </ul>
            </div>
            <form method="post">
                <input type="text" name="message" placeholder="Type your message here..." size="50">
                <input type="submit" value="Send">
                <input type="submit" name="complete_order" value="Complete Order">
            </form>
        </div>
    </body>
    </html>
    '''
    return render_template_string(chat_html, response=response, order_summary=order_summary, menu=menu_items)


@app.route('/summary')
def summary():
    if 'order' not in session or not session['order']:
        menu_items = get_menu_items()
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
                    <div>
                        <h2>Menu:</h2>
                        <ul style="list-style-type: none;">
                            {% for item in menu %}
                                <li>{{ item.name }}: {{ item.price }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </body>
            </html>
        ''', menu=menu_items)
    else:
        order_summary = "<h3>Your final order:</h3><ul style='list-style-type: none;'>"
        total_price = 0
        for item, qty in session['order'].items():
            item_price = menu_dict[item] * qty
            total_price += item_price
            order_summary += f"<li>{qty} x {item.title()} - ${item_price:.2f}</li>"
        order_summary += f"</ul><h3>Total: ${total_price:.2f}</h3>"

        menu_items = get_menu_items()
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
                    <div>
                        <h2>Menu:</h2>
                        <ul style="list-style-type: none;">
                            {% for item in menu %}
                                <li>{{ item.name }}: {{ item.price }}</li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </body>
            </html>
        ''', order_summary=order_summary, menu=menu_items)


if __name__ == '__main__':
    app.run(debug=True)
