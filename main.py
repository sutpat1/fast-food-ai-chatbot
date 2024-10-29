from flask import Flask, request, render_template_string, session, redirect, url_for
import spacy
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key'  # Replace with a secure secret key

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
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1  # Include 'a' and 'an' to map to 1
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

        tokens = [token for token in chunk]
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

        tokens = [token for token in chunk]
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

# Function to get current order summary
def get_current_order_summary():
    if 'order' not in session or not session['order']:
        return "Your order is currently empty."

    summary = "<h4>Your current order:</h4><ul style='list-style-type: none;'>"
    total = 0
    for item, qty in session['order'].items():
        item_price = menu_dict[item] * qty
        total += item_price
        summary += f"<li>{qty} x {item.title()} - ${item_price:.2f}</li>"
    summary += f"</ul><p><strong>Total: ${total:.2f}</strong></p>"
    return summary

# Function to handle addition of items
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
            session.modified = True  # Inform Flask that the session has been modified
        response += "🛒 **Item(s) added to your order.**"
        response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu in your order."
    return response

# Function to handle removal of items
def handle_removal(removal_items):
    response = ""
    if removal_items:
        for item, quantity in removal_items:
            if item in session['order']:
                if session['order'][item] > quantity:
                    session['order'][item] -= quantity
                    response += f"❌ Removed {quantity} x {item.title()} from your order.<br>"
                elif session['order'][item] == quantity:
                    session['order'].pop(item)
                    response += f"❌ Removed {quantity} x {item.title()} from your order.<br>"
                else:
                    response += f"⚠️ You have only {session['order'][item]} x {item.title()} in your order. Removing all of them.<br>"
                    session['order'].pop(item)
                session.modified = True  # Inform Flask that the session has been modified
            else:
                response += f"⚠️ You don't have any {item.title()} in your order to remove.<br>"
        response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu to remove in your request."
    return response

# Function to initialize messages in session
def initialize_messages():
    if 'messages' not in session:
        session['messages'] = []
        # Add a welcome message from the bot
        session['messages'].append({'sender': 'bot', 'text': "👋 Welcome to In-N-Out Ordering Chatbot! How can I assist you today?"})

# Flask routes
@app.route('/')
def index():
    session.clear()
    session['order'] = {}
    initialize_messages()
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
    initialize_messages()
    response = ""
    if request.method == 'POST':
        if 'complete_order' in request.form:
            return redirect(url_for('summary'))
        elif 'message' in request.form and request.form['message'].strip() != '':
            user_input = request.form['message']
            user_input_lower = user_input.lower()
            # Add user's message to the chat history
            session['messages'].append({'sender': 'user', 'text': user_input})
            if 'remove' in user_input_lower or 'cancel' in user_input_lower:
                removal_items = parse_removal(user_input)
                bot_response = handle_removal(removal_items)
            else:
                parsed_order, parsed_total = parse_order(user_input)
                bot_response = handle_addition(parsed_order)
            # Add bot's response to the chat history
            session['messages'].append({'sender': 'bot', 'text': bot_response})
        else:
            # Add a prompt message if the user didn't enter anything
            session['messages'].append({'sender': 'bot', 'text': "❓ Please enter a message."})

    menu_items = get_menu_items()
    chat_html = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>In-N-Out Chatbot</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f2f2f2; }
            .container { max-width: 800px; margin: auto; padding: 20px; }
            .chat-box {
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 10px;
                height: 400px;
                overflow-y: scroll;
                background-color: #fff;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
            .message {
                margin: 10px 0;
                padding: 10px 15px;
                border-radius: 20px;
                max-width: 70%;
                word-wrap: break-word;
                position: relative;
                clear: both;
            }
            .user-message {
                background-color: #dcf8c6;
                float: right;
                text-align: right;
            }
            .bot-message {
                background-color: #ececec;
                float: left;
                text-align: left;
            }
            .input-area {
                margin-top: 20px;
                display: flex;
                justify-content: center;
                align-items: center;
            }
            input[type="text"] {
                width: 70%;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 20px;
                outline: none;
                transition: border 0.3s;
            }
            input[type="text"]:focus {
                border: 1px solid #66afe9;
            }
            input[type="submit"], input[type="button"] {
                padding: 10px 20px;
                margin-left: 10px;
                border: none;
                border-radius: 20px;
                background-color: #28a745;
                color: white;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            input[type="submit"]:hover, input[type="button"]:hover {
                background-color: #218838;
            }
            .menu {
                margin-top: 20px;
                text-align: left;
            }
            .menu ul {
                list-style-type: none;
                padding: 0;
            }
            .menu li {
                padding: 5px 0;
            }
        </style>
    </head>
    <body>
        <div class="container" style="text-align: center;">
            <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
            <h1>In-N-Out Ordering Chatbot</h1>
            <div class="chat-box" id="chat-box">
                {% for message in messages %}
                    {% if message.sender == 'user' %}
                        <div class="message user-message">
                            {{ message.text }}
                        </div>
                    {% elif message.sender == 'bot' %}
                        <div class="message bot-message">
                            {{ message.text|safe }}
                        </div>
                    {% endif %}
                {% endfor %}
            </div>
            <div class="input-area">
                <form method="post" style="width: 100%; display: flex; justify-content: center;">
                    <input type="text" name="message" placeholder="Type your message here..." autocomplete="off">
                    <input type="submit" value="Send">
                    <input type="submit" name="complete_order" value="Complete Order">
                </form>
            </div>
            <div class="menu">
                <h2>Menu:</h2>
                <ul>
                    {% for item in menu %}
                        <li>{{ item.name }}: {{ item.price }}</li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        <script>
            // Auto-scroll to the bottom of the chat box
            var chatBox = document.getElementById('chat-box');
            chatBox.scrollTop = chatBox.scrollHeight;
        </script>
    </body>
    </html>
    '''
    return render_template_string(chat_html, messages=session['messages'], menu=menu_items)


@app.route('/summary')
def summary():
    if 'order' not in session or not session['order']:
        menu_items = get_menu_items()
        # Add a message indicating no order has been made
        session['messages'].append({'sender': 'bot', 'text': "❓ You haven't ordered anything yet."})
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Order Summary</title>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f2f2f2; }
                    .container { max-width: 800px; margin: auto; padding: 20px; text-align: center; }
                    .menu ul { list-style-type: none; padding: 0; }
                    .menu li { padding: 5px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
                    <h1>You haven't ordered anything yet.</h1>
                    <a href="{{ url_for('chat') }}">Go back to order</a>
                    <div class="menu">
                        <h2>Menu:</h2>
                        <ul>
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
        # Add a thank you message to the chat history
        session['messages'].append({'sender': 'bot', 'text': "🎉 Thank you for your order!"})
        session.clear()
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Order Summary</title>
                <style>
                    body { font-family: Arial, sans-serif; background-color: #f2f2f2; }
                    .container { max-width: 800px; margin: auto; padding: 20px; text-align: center; }
                    .menu ul { list-style-type: none; padding: 0; }
                    .menu li { padding: 5px 0; }
                </style>
            </head>
            <body>
                <div class="container">
                    <img src="{{ url_for('static', filename='InNOut_2021_logo.svg.png') }}" alt="In-N-Out Logo" width="200">
                    {{ order_summary|safe }}
                    <p>🎉 Thank you for your order!</p>
                    <a href="{{ url_for('index') }}">Start a new order</a>
                    <div class="menu">
                        <h2>Menu:</h2>
                        <ul>
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
