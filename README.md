# In-N-Out Ordering Chatbot
A conversational AI chatbot built using **Flask**, **spaCy**, and **Natural Language Processing** that allows users to place and customize orders from the In-N-Out menu through a user-friendly web interface.

## 🤖 Live Demo
[Try the Chatbot](https://innoutchatbox.onrender.com/) <!-- Replace with your actual deployment link when available -->

---

## 🚀 Features
- 💬 **Natural Language Processing**: Understands conversational language for ordering food items.
- 🍔 **Menu Recognition**: Accurately identifies menu items and quantities in user messages.
- ✏️ **Order Customization**: Supports ingredient additions and removals (e.g., "no onions" or "extra cheese").
- 🛒 **Order Management**: Add, modify, or remove items from your order with simple commands.
- 🔍 **Ingredient Queries**: Ask about ingredients in any menu item.
- 📱 **Responsive Design**: Works seamlessly on desktop, tablet, and mobile devices.
- 🧠 **Contextual Understanding**: Remembers ongoing conversations for a natural ordering experience.

---

## 🛠️ Tech Stack
- **Backend**: Python, Flask
- **NLP Processing**: spaCy, en_core_web_sm model
- **Data Handling**: Pandas
- **Frontend**: HTML, CSS, JavaScript

---

## 📁 Folder Structure
<pre lang="markdown">
├── main.py                 # Main Flask application with chatbot logic
├── In N Out Menu.csv       # Menu data with prices and ingredients
├── static/                 # Static assets
│   └── InNOut_2021_logo.svg.png  # In-N-Out logo
├── README.md               # Project documentation
└── package-lock.json       # Dependency lock file
</pre>

---

## 🚀 Getting Started

**Prerequisites**

* Python 3.7 or higher
* Flask
* spaCy
* Pandas

## Installation

1. Clone the repository

   ```bash
   git clone https://github.com/yourusername/in-n-out-chatbot.git
   cd in-n-out-chatbot

2. Install dependencies
   
   ```bash
   pip install flask spacy pandas
   python -m spacy download en_core_web_sm

3. Set up the environment
   ```bash
   # Optional: Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

4. Run the application
   ```bash
   python main.py```
   
6. Open http://localhost:5000 with your browser to start using the chatbot.

---

## 🗣️ Usage Examples

**Placing an Order**
- "I'd like a cheeseburger and a medium drink"
- "Can I get two hamburgers with fries"

**Modifying Orders**
- "Add extra cheese to my hamburger"
- "No onions on my cheeseburger please"

**Removing Items**
- "Remove the fries from my order"
- "I don't want the shake anymore"

**Checking Ingredients**
- "What's in the cheeseburger?"
- "Does the hamburger have tomatoes?"

**Managing Orders**
- "Show me my order"
- "Cancel my entire order"
- "Complete my order"

---

## 💡 NLP Capabilities

The chatbot uses advanced natural language processing to:

* **Entity Recognition**: Identifies menu items and quantities in natural language
* **Intent Classification**: Understands if the user wants to add, remove, or modify items
* **Context Awareness**: Maintains order state throughout the conversation
* **Lemmatization**: Processes word variations to improve understanding (e.g., "fries" and "french fries")
* **Numerical Recognition**: Handles both written numbers ("two") and digits ("2")

---

## 🔧 Customization

To adapt this chatbot for other restaurants or use cases:

* Replace the `In N Out Menu.csv` with your own menu data
* Modify the spaCy processing logic in `main.py` for domain-specific language
* Customize the HTML template and CSS styling for your brand
* Add new intents and entity types for additional features

---

## 📄 License

This project is open source and available under the MIT License.

---

## 🤝 Acknowledgements

* spaCy team for the excellent NLP library
* Flask for the lightweight web framework
* In-N-Out Burger for menu inspiration
