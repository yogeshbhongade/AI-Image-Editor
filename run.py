import sys
import os

print(sys.path)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print(sys.path)

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
