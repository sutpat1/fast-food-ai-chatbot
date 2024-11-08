from flask import Flask, request, render_template_string, session, redirect, url_for
import spacy
import pandas as pd
import re

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_segura_aqui'  # Substitua por uma chave secreta segura

# Carrega o modelo spaCy para processamento de NLP
nlp = spacy.load('en_core_web_sm')

# Carrega os dados do menu a partir do arquivo CSV
menu_data = pd.read_csv('In N Out Menu.csv')

# Normaliza os itens do menu: converte para minúsculas e substitui hífens por espaços
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower().str.replace('-', ' ')

# Substitui itens específicos para consistência
menu_data['Menu Item'] = menu_data['Menu Item'].replace({
    'cheese burger': 'cheeseburger',
    'shakes': 'shake',
    'number 1 meal': 'number one meal',
    'number 2 meal': 'number two meal',
    'number 3 meal': 'number three meal',
})

menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Cria um mapeamento de itens do menu lematizados para os nomes originais
lemmatized_menu_items = {}
for item in menu_dict.keys():
    item_doc = nlp(item)
    lemmatized_item = ' '.join([token.lemma_ for token in item_doc])
    lemmatized_menu_items[lemmatized_item] = item

# Cria um dicionário mapeando itens do menu para seus ingredientes
ingredients_dict = {}
for index, row in menu_data.iterrows():
    item = row['Menu Item']
    ingredients = [ingredient.strip().lower() for ingredient in row['Ingredients'].split(',')]
    # Lematiza cada ingrediente para garantir consistência
    lemmatized_ingredients = []
    for ingredient in ingredients:
        doc = nlp(ingredient)
        lemmatized = ' '.join([token.lemma_ for token in doc])
        lemmatized_ingredients.append(lemmatized)
    ingredients_dict[item] = lemmatized_ingredients

# Dicionários para converter números escritos em inteiros e dígitos em palavras
word_to_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "a": 1, "an": 1  # Inclui 'a' e 'an' para mapear para 1
}

num_to_word = {str(value): key for key, value in word_to_num.items()}

# Função para substituir numerais por palavras
def replace_numerals_with_words(text):
    def replace_match(match):
        return num_to_word.get(match.group(0), match.group(0))

    return re.sub(r'\b\d+\b', replace_match, text)

# Função para obter itens do menu
def get_menu_items():
    menu_items = []
    for item, price in menu_dict.items():
        menu_items.append({'name': item.title(), 'price': f"${price:.2f}"})
    return menu_items

# Função para parsear pedidos
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

# Função para parsear remoções de itens
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

# Função para parsear modificações nos ingredientes
def parse_modifications(user_input, parsed_order):
    """
    Parseia a entrada do usuário para modificações nos ingredientes, como 'sem cebolas' ou 'extra queijo'.
    Retorna um dicionário mapeando os nomes dos itens para suas modificações.
    """
    modifications = {}
    doc = nlp(user_input.lower())

    # Itera pelas sentenças
    for sent in doc.sents:
        # Procura por modificadores como 'sem' e 'extra'
        for token in sent:
            if token.text == 'without':
                # Pega o próximo token como ingrediente a remover
                try:
                    next_token = token.nbor(1)
                    if next_token.pos_ == 'NOUN':
                        ingredient = next_token.lemma_
                        # Atribui ao último item em parsed_order
                        if parsed_order:
                            last_item = parsed_order[-1][0]  # nome do item
                            modifications.setdefault(last_item, {}).setdefault('remove', []).append(ingredient)
                except IndexError:
                    continue  # Nenhum token após 'without', pula
            elif token.text in ['extra', 'add', 'with']:
                # Pega o próximo token como ingrediente a adicionar
                try:
                    next_token = token.nbor(1)
                    if next_token.pos_ == 'NOUN':
                        ingredient = next_token.lemma_
                        if token.text in ['add', 'with']:
                            # Atribui ao último item em parsed_order
                            if parsed_order:
                                last_item = parsed_order[-1][0]
                                modifications.setdefault(last_item, {}).setdefault('add', []).append(ingredient)
                        elif token.text == 'extra':
                            # Atribui ao último item em parsed_order
                            if parsed_order:
                                last_item = parsed_order[-1][0]
                                modifications.setdefault(last_item, {}).setdefault('add', []).append(ingredient)
                except IndexError:
                    continue  # Nenhum token após o modificador, pula

    return modifications

# Função para obter o resumo atual do pedido
def get_current_order_summary():
    if 'order' not in session or not session['order']:
        return "🛒 Your order is currently empty."

    summary = "<h4>Your current order:</h4><ul style='list-style-type: none;'>"
    total = 0
    for item, details in session['order'].items():
        qty = details['quantity']
        additions = details.get('add', [])
        removals = details.get('remove', [])
        item_price = menu_dict[item] * qty
        total += item_price

        # Exibe o item com modificações
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

# Função para lidar com adições de itens com modificações
def handle_addition(parsed_order, has_modifications):
    """
    Lida com a adição de itens ao pedido.
    Se has_modifications for False, retorna mensagens de adição e resumo do pedido.
    Se has_modifications for True, pula as mensagens de adição.
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
            session.modified = True  # Informa ao Flask que a sessão foi modificada

        if not has_modifications:
            response += "🛒 **Item(s) added to your order.**<br>"
            response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu in your order."
    return response

# Função para lidar com consultas sobre ingredientes
def handle_ingredient_query(user_input_lower):
    """
    Lida com consultas relacionadas a ingredientes.
    """
    # Tenta extrair o item do menu da consulta
    menu_item = None
    for item in menu_dict.keys():
        if item in user_input_lower:
            menu_item = item
            break

    if not menu_item:
        # Se o item do menu não for encontrado, tenta correspondências parciais
        for item in menu_dict.keys():
            if item.split()[0] in user_input_lower:
                menu_item = item
                break

    if not menu_item:
        return "❓ I'm sorry, I couldn't identify which menu item you're referring to. Please specify the item."

    # Determina se o usuário está perguntando sobre todos os ingredientes ou um ingrediente específico
    specific_ingredient = None
    specific_patterns = ['contains', 'have', 'include', 'has']
    for pattern in specific_patterns:
        if pattern in user_input_lower:
            pattern_index = user_input_lower.find(pattern)
            ingredient_part = user_input_lower[pattern_index + len(pattern):].strip()
            ingredient_tokens = ingredient_part.split()
            if ingredient_tokens:
                specific_ingredient = ingredient_tokens[-1]
                specific_ingredient = re.sub(r'[^\w\s]', '', specific_ingredient)
                doc = nlp(specific_ingredient)
                specific_ingredient = ' '.join([token.lemma_ for token in doc])
            break

    if specific_ingredient:
        # Verifica se o ingrediente específico está nos ingredientes do item
        if specific_ingredient in ingredients_dict.get(menu_item, []):
            return f"✅ Yes, the {menu_item.title()} contains {specific_ingredient.title()}."
        else:
            return f"❌ No, the {menu_item.title()} does not contain {specific_ingredient.title()}."
    else:
        # Fornece a lista completa de ingredientes
        ingredients = ingredients_dict.get(menu_item, [])
        if not ingredients:
            return f"ℹ️ The ingredients for {menu_item.title()} are currently unavailable."
        ingredients_formatted = ', '.join([ingredient.title() for ingredient in ingredients])
        return f"📝 The {menu_item.title()} contains the following ingredients: {ingredients_formatted}."

# Função para lidar com modificações nos itens
def handle_modifications(modifications):
    response = ""
    for item, mods in modifications.items():
        if item not in session['order']:
            response += f"⚠️ You haven't ordered a {item.title()} to modify.<br>"
            continue
        # Valida e aplica adições
        additions = mods.get('add', [])
        for add in additions:
            session['order'][item].setdefault('add', []).append(add)
            response += f"➕ Added {add.title()} to your {item.title()}.<br>"
        # Valida e aplica remoções
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

# Função para lidar com remoções de itens inteiros
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
                session.modified = True  # Informa ao Flask que a sessão foi modificada
            else:
                response += f"⚠️ You don't have any {item.title()} in your order to remove.<br>"
        response += get_current_order_summary()
    else:
        response += "❓ Sorry, we couldn't find any items from the menu to remove in your request."
    return response

# Função para inicializar mensagens na sessão
def initialize_messages():
    if 'messages' not in session:
        session['messages'] = []
        # Adiciona uma mensagem de boas-vindas do bot
        session['messages'].append({'sender': 'bot', 'text': "👋 Welcome to In-N-Out Ordering Chatbot! How can I assist you today?"})

# Rota Flask para o chatbot
@app.route('/', methods=['GET', 'POST'])
def chat():
    initialize_messages()
    response = ""
    if request.method == 'POST':
        if 'complete_order' in request.form:
            if 'order' in session and session['order']:
                # Gera o resumo do pedido
                order_summary = "<h3>Your final order:</h3><ul style='list-style-type: none;'>"
                total_price = 0
                for item, details in session['order'].items():
                    qty = details['quantity']
                    additions = details.get('add', [])
                    removals = details.get('remove', [])
                    item_price = menu_dict[item] * qty
                    total_price += item_price

                    # Exibe o item com modificações
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

                # Adiciona o resumo do pedido como uma mensagem do bot
                response += f"{order_summary}<p>🎉 Thank you for your order!</p>"
                session['messages'].append({'sender': 'bot', 'text': response})
                # Limpa a sessão para reiniciar para um novo pedido
                session.pop('order', None)
            else:
                response += "❓ You haven't ordered anything yet."
                session['messages'].append({'sender': 'bot', 'text': response})
        elif 'message' in request.form and request.form['message'].strip() != '':
            user_input = request.form['message']
            user_input_lower = user_input.lower()
            # Adiciona a mensagem do usuário ao histórico de chat
            session['messages'].append({'sender': 'user', 'text': user_input})

            # Determina o tipo de solicitação
            if any(word in user_input_lower for word in ['remove', 'cancel']):
                # Lida com a remoção de itens
                removal_items = parse_removal(user_input)
                bot_response = handle_removal(removal_items)
            elif any(word in user_input_lower for word in ['ingredient', 'ingredients', 'what\'s in', 'contains', 'have']):
                # Lida com consultas sobre ingredientes
                ingredient_response = handle_ingredient_query(user_input_lower)
                bot_response = ingredient_response
            else:
                # Lida com pedidos e modificações
                # Parseia o pedido
                parsed_order, parsed_total = parse_order(user_input)

                # Parseia modificações com base na entrada do usuário
                modifications = parse_modifications(user_input, parsed_order)

                # Determina se há modificações
                has_modifications = bool(modifications)

                # Lida com adições
                addition_response = handle_addition(parsed_order, has_modifications)

                if has_modifications:
                    # Lida com modificações
                    modification_response = handle_modifications(modifications)
                    # Combina respostas sem a mensagem inicial de adição
                    bot_response = modification_response
                else:
                    bot_response = addition_response

            # Adiciona a resposta do bot ao histórico de chat
            session['messages'].append({'sender': 'bot', 'text': bot_response})
        else:
            # Adiciona uma mensagem de prompt se o usuário não digitou nada
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
            // Auto-scroll para o fundo do chat sempre que a página for carregada
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
