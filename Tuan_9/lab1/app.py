from flask import Flask
from blueprints.v1 import bp as v1_bp
from blueprints.v2 import bp as v2_bp

app = Flask(__name__)
app.json.ensure_ascii = False
app.register_blueprint(v1_bp, url_prefix="/api/v1/users")
app.register_blueprint(v2_bp, url_prefix="/api/v2/users")

if __name__ == "__main__":
    app.run(port=5055)
