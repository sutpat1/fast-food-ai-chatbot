# In-N-Out Ordering Chatbot
A conversational AI chatbot built using **Flask**, **spaCy**, and **Natural Language Processing** that allows users to place and customize orders from the In-N-Out menu through a user-friendly web interface.

## 🤖 Live Demo
[Try the Chatbot](https://in-n-out-chatbot.example.com/) <!-- Replace with your actual deployment link when available -->

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
   cd in-n-out-chatbot```

2. Install dependencies
   ```bash
   pip install flask spacy pandas
   python -m spacy download en_core_web_sm```
   

Set up the environment
bash# Optional: Create and activate a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Run the application
bashpython main.py

Open http://localhost:5000 with your browser to start using the chatbot.

