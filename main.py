import spacy
import pandas as pd

# Load the spaCy model for NLP processing
nlp = spacy.load('en_core_web_sm')

# Load the menu data from CSV file
menu_file_path = 'In N Out Menu.csv'
menu_data = pd.read_csv(menu_file_path)

# Normalize menu items: Convert to lowercase, replace dashes with spaces, and merge specific items
menu_data['Menu Item'] = menu_data['Menu Item'].str.lower().str.replace('-', ' ')
menu_data['Menu Item'] = menu_data['Menu Item'].replace({
    'cheese burger': 'cheeseburger',  # Merge 'Cheese Burger'
    'shakes': 'shake'                 # Change 'Shakes' to 'Shake'
})
menu_dict = dict(zip(menu_data['Menu Item'], menu_data['Price']))

# Dictionary for converting written numbers to integers
word_to_num = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10
}

# Function to display the menu
def show_menu():
    print("Welcome to In-N-Out! Here's our menu:")
    for item, price in menu_dict.items():
        print(f"{item.title()}: ${price:.2f}")  # Display with title-case

# Corrected parse_order function
def parse_order(user_input):
    doc = nlp(user_input)
    order = []
    total = 0
    quantity = 1  # Default quantity if not specified

    # Normalize user input: Convert to lowercase and replace dashes with spaces
    user_input_lower = user_input.lower().replace('-', ' ')

    # Handle plural forms in user input
    user_input_lower = user_input_lower.replace('shakes', 'shake')

    # Handle numbers and written numbers
    for token in doc:
        token_lower = token.text.lower()
        if token_lower in word_to_num:
            quantity = word_to_num[token_lower]
        elif token.like_num:
            try:
                quantity = int(token.text)
            except ValueError:
                # Handle number words that are recognized as numbers but can't be converted directly
                if token_lower in word_to_num:
                    quantity = word_to_num[token_lower]
                else:
                    print(f"Cannot interpret quantity '{token.text}'. Using default quantity of 1.")
                    quantity = 1

    # Match menu items (ignoring case and dashes)
    for item in menu_dict.keys():
        if item in user_input_lower:
            order.append((item.title(), quantity))  # Store with title-case for display
            total += menu_dict[item] * quantity
            quantity = 1  # Reset quantity for next item

    return order, total

# Modified take_order function to repeat back the order
def take_order():
    order = []
    total = 0
    while True:
        user_input = input("What would you like to order? (type 'done' to finish): ")
        if user_input.lower() == 'done':
            break
        else:
            parsed_order, parsed_total = parse_order(user_input)
            order.extend(parsed_order)
            total += parsed_total
            # Repeat back the items just added
            if parsed_order:
                print("Added to your order:")
                for item, quantity in parsed_order:
                    print(f"- {quantity} x {item}")
            else:
                print("Sorry, we couldn't find any items from the menu in your order.")
            print(f"Total so far: ${total:.2f}")

    return order, total

# Function to display the final order and total price
def display_order(order, total):
    print("\nHere's your final order:")
    for item, quantity in order:
        print(f"- {quantity} x {item}: ${menu_dict[item.lower()]:.2f} each")
    print(f"Your total is: ${total:.2f}")
    print("Thank you for ordering at In-N-Out!")

# Main chatbot function
def chatbot():
    show_menu()
    order, total = take_order()
    display_order(order, total)

# Run the chatbot
chatbot()
