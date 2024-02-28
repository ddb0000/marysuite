from flask import Flask, render_template

app = Flask(__name__)

def get_herb_entries():
    return [
        {"name": "Basil", "quantity": "5g"},
        {"name": "Basils", "quantity": "15g"},
        {"name": "Mint", "quantity": "3g"},
        {"name": "Cilantro", "quantity": "2g"}
    ]

@app.route('/')
def index():
    herb_entries = get_herb_entries()
    return render_template('index.html', herb_entries=herb_entries)
