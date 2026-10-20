from routes.authors import authors_bp
from routes.books import books_bp
from routes.categories import categories_bp
from routes.reviews import reviews_bp
from routes.users import users_bp


BLUEPRINTS = [books_bp, authors_bp, categories_bp, users_bp, reviews_bp]
