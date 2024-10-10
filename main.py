import spacy
import pandas as pd
import re

# Load the spaCy model for NLP processing
nlp = spacy.load('en_core_web_sm')

# Load the menu data from CSV file
menu_file_path = 'In N Out Menu.csv'
menu_data = pd.read_csv(menu_file_path)

# Normalize menu items: Convert to lowercase, replace dashes with spaces
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower().str.replace('-', ' ')

# Replace specific items for consistency
menu_data['Menu Item'] = menu_data['Menu Item'].replace({
    'cheese burger': 'cheeseburger',      # Merge 'Cheese Burger'
    'shakes': 'shake',                    # Change 'Shakes' to 'Shake'
    'number 1 meal': 'number one meal',   # Change 'Number 1 Meal' to 'Number one meal'
    'number 2 meal': 'number two meal',
    'number 3 meal': 'number three meal',
})

menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Dictionaries for converting written numbers to integers and digits to words
word_to_num = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

num_to_word = {str(value): key for key, value in word_to_num.items()}

# Function to display the menu
def show_menu():
    print("Welcome to In-N-Out! Here's our menu:")
    for item, price in menu_dict.items():
        print(f"{item.title()}: ${price:.2f}")  # Display with title-case

# Function to replace numerals in text with words
def replace_numerals_with_words(text):
    # Replace digits with words using regex
    def replace_match(match):
        return num_to_word.get(match.group(0), match.group(0))
    return re.sub(r'\b\d+\b', replace_match, text)

# Corrected parse_order function
def parse_order(user_input):
    # Normalize user input: Convert to lowercase and replace dashes with spaces
    user_input_lower = user_input.lower().replace('-', ' ')

    # Replace numerals with words in user input
    user_input_lower = replace_numerals_with_words(user_input_lower)

    # Handle plural forms in user input
    user_input_lower = user_input_lower.replace('shakes', 'shake')

    # Process with spaCy NLP
    doc = nlp(user_input_lower)
    order = []
    total = 0
    quantity = 1  # Default quantity if not specified

    # Handle numbers and written numbers
    for token in doc:
        token_lower = token.text.lower()
        if token_lower in word_to_num:
            quantity = word_to_num[token_lower]
        elif token.like_num:
            try:
                quantity = int(token.text)
            except ValueError:
                quantity = 1

    # Match menu items (ignoring case)
    for item in menu_dict.keys():
        if item in user_input_lower:
            order.append((item.title(), quantity))  # Store with title-case for display
            total += menu_dict[item] * quantity
            quantity = 1  # Reset quantity for next item

    return order, total

# Function to parse removal requests
def parse_removal(user_input):
    # Similar to parse_order, but for removal
    user_input_lower = user_input.lower().replace('-', ' ')
    user_input_lower = replace_numerals_with_words(user_input_lower)
    user_input_lower = user_input_lower.replace('shakes', 'shake')

    doc = nlp(user_input_lower)
    removal_items = []
    quantity = 1

    for token in doc:
        token_lower = token.text.lower()
        if token_lower in word_to_num:
            quantity = word_to_num[token_lower]
        elif token.like_num:
            try:
                quantity = int(token.text)
            except ValueError:
                quantity = 1

    for item in menu_dict.keys():
        if item in user_input_lower:
            removal_items.append((item.title(), quantity))
            quantity = 1

    return removal_items

# Modified take_order function to handle removal requests
def take_order():
    order = {}  # Use a dictionary to accumulate item quantities
    total = 0
    while True:
        user_input = input("What would you like to order? (type 'done' to finish): ")
        user_input_lower = user_input.lower()
        if user_input_lower == 'done':
            break
        elif 'remove' in user_input_lower or 'cancel' in user_input_lower:
            # Handle removal
            removal_items = parse_removal(user_input)
            if removal_items:
                for item, quantity in removal_items:
                    if item in order:
                        if order[item] > quantity:
                            order[item] -= quantity
                            total -= menu_dict[item.lower()] * quantity
                            print(f"Removed {quantity} x {item} from your order.")
                        elif order[item] == quantity:
                            order.pop(item)
                            total -= menu_dict[item.lower()] * quantity
                            print(f"Removed {quantity} x {item} from your order.")
                        else:
                            print(f"You have only {order[item]} x {item} in your order. Removing all of them.")
                            total -= menu_dict[item.lower()] * order[item]
                            order.pop(item)
                    else:
                        print(f"You don't have any {item} in your order to remove.")
            else:
                print("Sorry, we couldn't find any items from the menu to remove in your request.")
        else:
            # Handle adding items
            parsed_order, parsed_total = parse_order(user_input)
            # Update the order dictionary
            for item, quantity in parsed_order:
                if item in order:
                    order[item] += quantity
                else:
                    order[item] = quantity
            total += parsed_total
        # Display the current order
        if order:
            print("Your current order:")
            for item, quantity in order.items():
                print(f"- {quantity} x {item}")
        else:
            print("Your order is currently empty.")
        print(f"Total so far: ${total:.2f}")

    return order, total

# Function to display the final order and total price
def display_order(order, total):
    print("\nHere's your final order:")
    if order:
        for item, quantity in order.items():
            print(f"- {quantity} x {item}: ${menu_dict[item.lower()]:.2f} each")
        print(f"Your total is: ${total:.2f}")
        print("Thank you for ordering at In-N-Out!")
    else:
        print("You didn't order anything. Thank you for visiting In-N-Out!")

# Main chatbot function
def chatbot():
    show_menu()
    order, total = take_order()
    display_order(order, total)

# Run the chatbot
chatbot()
