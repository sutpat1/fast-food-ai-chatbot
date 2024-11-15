from flask import Flask, request, render_template_string, session, redirect, url_for
import spacy
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = 'your_secure_secret_key_here'  # Replace with a secure secret key

# Load the spaCy model for NLP processing
nlp = spacy.load('en_core_web_sm')

# Load menu data from the CSV file
menu_data = pd.read_csv('In N Out Menu.csv')

# Normalize menu items: convert to lowercase and replace hyphens with spaces
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower().str.replace('-', ' ', regex=False)

# Replace specific items for consistency
menu_data['Menu Item'] = menu_data['Menu Item'].replace({
    'cheese burger': 'cheeseburger',
    'shakes': 'shake',
    'number 1 meal': 'number one meal',
    'number 2 meal': 'number two meal',
    'number 3 meal': 'number three meal',
})

menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Create a mapping of lemmatized menu items to their original names
lemmatized_menu_items = {}
for item in menu_dict.keys():
    item_doc = nlp(item)
    lemmatized_item = ' '.join([token.lemma_ for token in item_doc])
    lemmatized_menu_items[lemmatized_item] = item

# Create a dictionary mapping menu items to their ingredients
ingredients_dict = {}
for index, row in menu_data.iterrows():
    item = row['Menu Item']
    ingredients = [ingredient.strip().lower() for ingredient in row['Ingredients'].split(',')]
    # Lemmatize each ingredient for consistency
    lemmatized_ingredients = []
    for ingredient in ingredients:
        doc = nlp(ingredient)
        lemmatized = ' '.join([token.lemma_ for token in doc])
        lemmatized_ingredients.append(lemmatized)
    ingredients_dict[item] = lemmatized_ingredients

# Dictionaries to convert written numbers and digits to words
word_to_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1  # Includes 'a' and 'an' to map to 1
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

# Function to parse orders
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
            total += float(menu_dict[item_name]) * quantity

    return order, total

# Function to parse item removals
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

# Function to parse ingredient modifications
def parse_modifications(user_input, parsed_order):
    """
    Parses user input for ingredient modifications, such as 'without onions' or 'extra cheese'.
    Returns a dictionary mapping item names to their modifications.
    """
    modifications = {}
    doc = nlp(user_input.lower())

    # Iterate through sentences
    for sent in doc.sents:
        # Look for modifiers like 'without', 'no', 'extra', 'add', 'with'
        for token in sent:
            if token.text in ['without', 'no', 'nos']:
                # Get the next token as the ingredient to remove
                try:
                    next_token = token.nbor(1)
                    if next_token.pos_ == 'NOUN':
                        ingredient = next_token.lemma_
                        # Assign to the last item in parsed_order
                        if parsed_order:
                            last_item = parsed_order[-1][0]  # item name
                            modifications.setdefault(last_item, {}).setdefault('remove', []).append(ingredient)
                except IndexError:
                    continue  # No token after modifier, skip
            elif token.text in ['extra', 'add', 'with', 'mais']:
                # Get the next token as the ingredient to add
                try:
                    next_token = token.nbor(1)
                    if next_token.pos_ == 'NOUN':
                        ingredient = next_token.lemma_
                        if token.text in ['add', 'with', 'mais']:
                            # Assign to the last item in parsed_order
                            if parsed_order:
                                last_item = parsed_order[-1][0]
                                modifications.setdefault(last_item, {}).setdefault('add', []).append(ingredient)
                        elif token.text == 'extra':
                            # Assign to the last item in parsed_order
                            if parsed_order:
                                last_item = parsed_order[-1][0]
                                modifications.setdefault(last_item, {}).setdefault('add', []).append(ingredient)
                except IndexError:
                    continue  # No token after modifier, skip

    return modifications

# Function to get the current order summary
def get_current_order_summary():
    if 'order' not in session or not session['order']:
        return "🛒 Your order is currently empty."

    summary = "<h4>Your current order:</h4><ul style='list-style-type: none;'>"
    total = 0
    for item, details in session['order'].items():
        qty = details['quantity']
        additions = details.get('add', [])
        removals = details.get('remove', [])
        item_price = float(menu_dict[item]) * qty
        total += item_price

        # Display the item with modifications
        item_display = f"{qty} x {item.title()}"
        modifications = []
        if additions:
            modifications.append("Add: " + ", ".join([add.title() for add in additions]))
        if removals:
            modifications.append("Remove: " + ", ".join([remove.title() for remove in removals]))
        if modifications:
            item_display += f" ({'; '.join(modifications)})"
        item_display += f" - ${item_price:.2f}"
        summary += f"<li>{item_display}</li>"
    summary += f"</ul><p><strong>Total: ${total:.2f}</strong></p>"
    return summary

# Function to handle adding items with modifications
def handle_addition(parsed_order, has_modifications):
    """
    Handles adding items to the order.
    If has_modifications is False, returns messages about additions and order summary.
    If has_modifications is True, skips addition messages.
    """
    response = ""
    if parsed_order:
        for item, quantity in parsed_order:
            if 'order' not in session:
                session['order'] = {}
            if item in session['order']:
                session['order'][item]['quantity'] += quantity
            else:
                session['order'][item] = {'quantity': quantity, 'add': [], 'remove': []}
            session.modified = True  # Inform Flask that the session has been modified

        if not has_modifications:
            response += "🛒 **Item(s) added to your order.**<br>"
            response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu in your order."
    return response

# Function to handle ingredient queries
def handle_ingredient_query(user_input_lower):
    """
    Handles queries related to ingredients.
    """
    # Attempt to extract the menu item from the query
    menu_item = None
    for item in menu_dict.keys():
        if item in user_input_lower:
            menu_item = item
            break

    if not menu_item:
        # If the menu item isn't found, try partial matches
        for item in menu_dict.keys():
            if item.split()[0] in user_input_lower:
                menu_item = item
                break

    if not menu_item:
        return "❓ I'm sorry, I couldn't identify which menu item you're referring to. Please specify the item."

    # Determine if the user is asking for all ingredients or a specific one
    specific_ingredient = None
    # Added 'what does' to cover more cases
    specific_patterns = ['contains', 'have', 'includes', 'include', 'has', 'what\'s in', 'what is in', 'what are in', 'contain', 'what does']

    for pattern in specific_patterns:
        if pattern in user_input_lower:
            pattern_index = user_input_lower.find(pattern)
            ingredient_part = user_input_lower[pattern_index + len(pattern):].strip()
            # Remove possible conjunctions like 'and', 'or'
            ingredient_part = re.split(r'\band\b|\bor\b', ingredient_part)[0]
            ingredient_tokens = ingredient_part.split()
            if ingredient_tokens:
                specific_ingredient = ingredient_tokens[-1]
                specific_ingredient = re.sub(r'[^\w\s]', '', specific_ingredient)
                doc = nlp(specific_ingredient)
                specific_ingredient = ' '.join([token.lemma_ for token in doc])
            break

    if specific_ingredient:
        if specific_ingredient == menu_item:
            # User is requesting the full list of ingredients
            ingredients = ingredients_dict.get(menu_item, [])
            if not ingredients:
                return f"ℹ️ The ingredients for {menu_item.title()} are currently unavailable."
            ingredients_formatted = ', '.join([ingredient.title() for ingredient in ingredients])
            return f"📝 The {menu_item.title()} contains the following ingredients: {ingredients_formatted}."
        else:
            # User is asking about a specific ingredient
            if specific_ingredient in ingredients_dict.get(menu_item, []):
                return f"✅ Yes, the {menu_item.title()} contains {specific_ingredient.title()}."
            else:
                return f"❌ No, the {menu_item.title()} does not contain {specific_ingredient.title()}."
    else:
        # User is requesting the full list of ingredients without specifying
        ingredients = ingredients_dict.get(menu_item, [])
        if not ingredients:
            return f"ℹ️ The ingredients for {menu_item.title()} are currently unavailable."
        ingredients_formatted = ', '.join([ingredient.title() for ingredient in ingredients])
        return f"📝 The {menu_item.title()} contains the following ingredients: {ingredients_formatted}."

# Function to handle modifications to items
def handle_modifications(modifications):
    response = ""
    for item, mods in modifications.items():
        if item not in session['order']:
            response += f"⚠️ You haven't ordered a {item.title()} to modify.<br>"
            continue
        # Validate and apply additions
        additions = mods.get('add', [])
        for add in additions:
            session['order'][item].setdefault('add', []).append(add)
            response += f"➕ Added {add.title()} to your {item.title()}.<br>"
        # Validate and apply removals
        removals = mods.get('remove', [])
        for remove in removals:
            if remove in ingredients_dict[item]:
                session['order'][item].setdefault('remove', []).append(remove)
                response += f"➖ Removed {remove.title()} from your {item.title()}.<br>"
            else:
                response += f"ℹ️ {item.title()} doesn't contain {remove.title()}.<br>"
        session.modified = True
    response += get_current_order_summary()
    return response

# Function to handle removal of entire items
def handle_removal(removal_items):
    response = ""
    if removal_items:
        for item, quantity in removal_items:
            if item in session['order']:
                if session['order'][item]['quantity'] > quantity:
                    session['order'][item]['quantity'] -= quantity
                    response += f"❌ Removed {quantity} x {item.title()} from your order.<br>"
                elif session['order'][item]['quantity'] == quantity:
                    session['order'].pop(item)
                    response += f"❌ Removed {quantity} x {item.title()} from your order.<br>"
                else:
                    response += f"⚠️ You have only {session['order'][item]['quantity']} x {item.title()} in your order. Removing all of them.<br>"
                    session['order'].pop(item)
                session.modified = True  # Inform Flask that the session has been modified
            else:
                response += f"⚠️ You don't have any {item.title()} in your order to remove.<br>"
        response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu to remove in your request."
    return response

# Function to handle menu display requests
def handle_menu_request():
    menu_items = get_menu_items()
    menu_html = "<h3>🍔 In-N-Out Menu:</h3><ul style='list-style-type: none;'>"
    for item in menu_items:
        menu_html += f"<li>{item['name']}: {item['price']}</li>"
    menu_html += "</ul>"
    return menu_html

# **New Function to Handle Cancellation of Entire Order**
def handle_cancel_order():
    """
    Handles the cancellation of the entire order.
    Clears the order from the session and informs the user.
    """
    if 'order' in session and session['order']:
        session.pop('order', None)
        return "🗑️ Your entire order has been canceled."
    else:
        return "⚠️ You don't have any active orders to cancel."

# Function to initialize messages in the session
def initialize_messages():
    if 'messages' not in session:
        session['messages'] = []
        # Add a welcome message from the bot
        session['messages'].append({'sender': 'bot', 'text': "👋 Welcome to In-N-Out Ordering Chatbot! How can I assist you today?"})

# Flask route for the chatbot
@app.route('/', methods=['GET', 'POST'])
def chat():
    initialize_messages()
    response = ""
    if request.method == 'POST':
        if 'complete_order' in request.form:
            if 'order' in session and session['order']:
                # Generate order summary
                order_summary = "<h3>Your final order:</h3><ul style='list-style-type: none;'>"
                total_price = 0
                for item, details in session['order'].items():
                    qty = details['quantity']
                    additions = details.get('add', [])
                    removals = details.get('remove', [])
                    item_price = float(menu_dict[item]) * qty
                    total_price += item_price

                    # Display the item with modifications
                    item_display = f"{qty} x {item.title()}"
                    modifications = []
                    if additions:
                        modifications.append("Add: " + ", ".join([add.title() for add in additions]))
                    if removals:
                        modifications.append("Remove: " + ", ".join([remove.title() for remove in removals]))
                    if modifications:
                        item_display += f" ({'; '.join(modifications)})"
                    item_display += f" - ${item_price:.2f}"
                    order_summary += f"<li>{item_display}</li>"
                order_summary += f"</ul><h3>Total: ${total_price:.2f}</h3>"

                # Add the order summary as a bot message
                response += f"{order_summary}<p>🎉 Thank you for your order!</p>"
                session['messages'].append({'sender': 'bot', 'text': response})
                # Clear the session to start a new order
                session.pop('order', None)
            else:
                response += "❓ You haven't ordered anything yet."
                session['messages'].append({'sender': 'bot', 'text': response})
        elif 'message' in request.form and request.form['message'].strip() != '':
            user_input = request.form['message']
            user_input_lower = user_input.lower()
            # Normalize user input by removing punctuation
            user_input_lower = re.sub(r'[^\w\s]', '', user_input_lower)
            # Add the user's message to the chat history
            session['messages'].append({'sender': 'user', 'text': user_input})

            # Define patterns to identify menu requests
            menu_patterns = ['menu', 'show menu', 'what do you have', 'list', 'available items']

            # Define removal intents including 'delete' and 'dont want'
            removal_intents = ['remove', 'cancel', 'delete', 'discard', 'dont want']

            # Define cancellation intents for entire order
            cancellation_intents = ['cancel my order', 'remove entire order', 'clear my order', 'discard my order', 'cancel order', 'remove all', 'clear order', 'discard order']

            # **New Condition to Handle Cancellation of Entire Order**
            if any(cancel_phrase in user_input_lower for cancel_phrase in cancellation_intents):
                # Handle cancellation of the entire order
                bot_response = handle_cancel_order()
            elif any(intent in user_input_lower for intent in removal_intents):
                # Handle item removal
                removal_items = parse_removal(user_input)
                bot_response = handle_removal(removal_items)
            elif any(word in user_input_lower for word in ['ingredient', 'ingredients', 'whats in', 'contains', 'have', 'what is in', 'what does', 'contain', 'contains']):
                # Handle ingredient queries
                ingredient_response = handle_ingredient_query(user_input_lower)
                bot_response = ingredient_response
            elif any(pattern in user_input_lower for pattern in menu_patterns):
                # Handle menu display requests
                menu_response = handle_menu_request()
                bot_response = menu_response
            else:
                # Handle orders and modifications
                # Parse the order
                parsed_order, parsed_total = parse_order(user_input)

                # Parse modifications based on user input
                modifications = parse_modifications(user_input, parsed_order)

                # Determine if there are modifications
                has_modifications = bool(modifications)

                # Handle additions
                addition_response = handle_addition(parsed_order, has_modifications)

                if has_modifications:
                    # Handle modifications
                    modification_response = handle_modifications(modifications)
                    # Combine responses without the initial addition message
                    bot_response = modification_response
                else:
                    bot_response = addition_response

            # Add the bot's response to the chat history
            session['messages'].append({'sender': 'bot', 'text': bot_response})
        else:
            # Add a prompt message if the user didn't type anything
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
                height: 500px;
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
            // Auto-scroll to the bottom of the chat when the page loads
            window.onload = function() {
                var chatBox = document.getElementById('chat-box');
                chatBox.scrollTop = chatBox.scrollHeight;
            };
        </script>
    </body>
    </html>
    '''
    return render_template_string(chat_html, messages=session['messages'], menu=menu_items)

if __name__ == '__main__':
    app.run(debug=True)
