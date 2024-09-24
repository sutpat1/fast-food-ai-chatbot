import spacy
import pandas as pd

# Load the spaCy model for NLP processing
nlp = spacy.load('en_core_web_sm')

# Load the menu data from CSV file
menu_file_path = 'In N Out Menu.csv'
menu_data = pd.read_csv(menu_file_path)

# Convert the menu data into a dictionary for easy access
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
        print(f"{item}: ${price:.2f}")

# Function to parse the order using NLP
def parse_order(user_input):
    doc = nlp(user_input)
    order = []
    total = 0
    quantity = 1  # Default quantity if not specified

    # Handle numbers and written numbers
    for token in doc:
        if token.like_num:  # If token is a number (e.g., '1')
            quantity = int(token.text)
        elif token.text.lower() in word_to_num:  # If token is a written number (e.g., 'one')
            quantity = word_to_num[token.text.lower()]

    # Match multi-word menu items
    user_input_lower = user_input.lower()
    for item in menu_dict.keys():
        if item.lower() in user_input_lower:
            order.append((item, quantity))
            total += menu_dict[item] * quantity
            quantity = 1  # Reset quantity for next item

    return order, total

# Function to take the order from the user
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
            print(f"Added to your order. Total so far: ${total:.2f}")

    return order, total

# Function to display the final order and total price
def display_order(order, total):
    print("\nHere's your final order:")
    for item, quantity in order:
        print(f"- {quantity} x {item}: ${menu_dict[item]:.2f} each")
    print(f"Your total is: ${total:.2f}")
    print("Thank you for ordering at In-N-Out!")

# Main chatbot function
def chatbot():
    show_menu()
    order, total = take_order()
    display_order(order, total)

# Run the chatbot
chatbot()
