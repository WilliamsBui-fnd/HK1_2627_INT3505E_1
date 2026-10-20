from datetime import date, datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def datetime_text(value):
    return value.isoformat(timespec="seconds") + "Z"


class Category(db.Model):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    books: Mapped[list["Book"]] = relationship(back_populates="category")

    def to_dict(self, include_book_count=False):
        data = {
            "id": f"category_{self.id}",
            "name": self.name,
            "slug": self.slug,
        }
        if include_book_count:
            data["bookCount"] = len(self.books)
        return data


class Author(db.Model):
    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    book_links: Mapped[list["BookAuthor"]] = relationship(
        back_populates="author", cascade="all, delete-orphan"
    )

    def to_dict(self, include_books=False):
        data = {
            "id": f"author_{self.id}",
            "name": self.name,
            "bio": self.bio,
        }
        if include_books:
            data["books"] = [
                {
                    "id": f"book_{link.book.id}",
                    "title": link.book.title,
                    "role": link.role,
                }
                for link in sorted(self.book_links, key=lambda item: item.book.id)
            ]
        return data


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    reviews: Mapped[list["Review"]] = relationship(back_populates="user")

    def to_dict(self):
        return {
            "id": f"user_{self.id}",
            "email": self.email,
            "displayName": self.display_name,
            "status": self.status,
            "createdAt": datetime_text(self.created_at),
        }


class Book(db.Model):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    isbn: Mapped[str] = mapped_column(String(13), nullable=False, unique=True)
    price_vnd: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now, index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    category: Mapped[Category] = relationship(back_populates="books")
    author_links: Mapped[list["BookAuthor"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": f"book_{self.id}",
            "title": self.title,
            "isbn": self.isbn,
            "genre": {
                "id": f"genre_{self.category.id}",
                "name": self.category.name,
                "slug": self.category.slug,
            },
            "authors": [
                {
                    "id": f"author_{link.author.id}",
                    "name": link.author.name,
                    "role": link.role,
                }
                for link in sorted(self.author_links, key=lambda item: item.author.id)
            ],
            "price": {"amount": self.price_vnd, "currency": "VND"},
            "stock": self.stock,
            "inStock": self.stock > 0,
            "publishedAt": self.published_at.isoformat(),
            "createdAt": datetime_text(self.created_at),
        }


class BookAuthor(db.Model):
    __tablename__ = "book_authors"
    __table_args__ = (UniqueConstraint("book_id", "author_id"),)

    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="lead")
    book: Mapped[Book] = relationship(back_populates="author_links")
    author: Mapped[Author] = relationship(back_populates="book_links")


class Review(db.Model):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("book_id", "user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    book: Mapped[Book] = relationship(back_populates="reviews")
    user: Mapped[User] = relationship(back_populates="reviews")

    def to_dict(self):
        return {
            "id": f"review_{self.id}",
            "book": {"id": f"book_{self.book.id}", "title": self.book.title},
            "user": {
                "id": f"user_{self.user.id}",
                "displayName": self.user.display_name,
            },
            "rating": self.rating,
            "content": self.content,
            "createdAt": datetime_text(self.created_at),
        }


def seed_database():
    if db.session.scalar(db.select(db.func.count(Book.id))):
        return

    categories = {
        "tech": Category(name="Công nghệ", slug="tech"),
        "fiction": Category(name="Văn học", slug="fiction"),
        "business": Category(name="Kinh doanh", slug="business"),
        "science": Category(name="Khoa học", slug="science"),
    }
    authors = {
        "martin": Author(name="Robert C. Martin"),
        "hunt": Author(name="Andrew Hunt"),
        "thomas": Author(name="David Thomas"),
        "kleppmann": Author(name="Martin Kleppmann"),
        "ramalho": Author(name="Luciano Ramalho"),
        "geewax": Author(name="JJ Geewax"),
        "evans": Author(name="Eric Evans"),
        "fowler": Author(name="Martin Fowler"),
        "herbert": Author(name="Frank Herbert"),
        "orwell": Author(name="George Orwell"),
        "murakami": Author(name="Haruki Murakami"),
        "clear": Author(name="James Clear"),
        "thiel": Author(name="Peter Thiel"),
        "ries": Author(name="Eric Ries"),
        "hawking": Author(name="Stephen Hawking"),
        "sagan": Author(name="Carl Sagan"),
    }
    users = [
        User(email="an.nguyen@example.com", display_name="An Nguyễn"),
        User(email="minh.tran@example.com", display_name="Minh Trần"),
    ]
    db.session.add_all([*categories.values(), *authors.values(), *users])
    db.session.flush()

    rows = [
        ("Clean Code", "9780132350884", 450000, 8, "tech", date(2008, 8, 1), "martin"),
        ("The Pragmatic Programmer", "9780135957059", 520000, 6, "tech", date(2019, 9, 13), "hunt"),
        ("Designing Data-Intensive Applications", "9781449373320", 650000, 4, "tech", date(2017, 3, 16), "kleppmann"),
        ("Fluent Python", "9781492056355", 650000, 5, "tech", date(2022, 4, 26), "ramalho"),
        ("API Design Patterns", "9781617295850", 480000, 7, "tech", date(2021, 8, 24), "geewax"),
        ("Domain-Driven Design", "9780321125217", 590000, 3, "tech", date(2003, 8, 30), "evans"),
        ("Refactoring", "9780134757599", 520000, 9, "tech", date(2018, 11, 20), "fowler"),
        ("Dune", "9780441172719", 320000, 11, "fiction", date(1965, 8, 1), "herbert"),
        ("1984", "9780451524935", 210000, 10, "fiction", date(1949, 6, 8), "orwell"),
        ("Norwegian Wood", "9780375704024", 260000, 2, "fiction", date(1987, 9, 4), "murakami"),
        ("Atomic Habits", "9780735211292", 280000, 13, "business", date(2018, 10, 16), "clear"),
        ("Zero to One", "9780804139298", 240000, 4, "business", date(2014, 9, 16), "thiel"),
        ("The Lean Startup", "9780307887894", 310000, 6, "business", date(2011, 9, 13), "ries"),
        ("A Brief History of Time", "9780553380163", 330000, 5, "science", date(1988, 4, 1), "hawking"),
        ("Cosmos", "9780345539434", 350000, 7, "science", date(1980, 9, 28), "sagan"),
    ]

    created_base = datetime(2026, 1, 1, 8, 0, 0)
    books = []
    for index, row in enumerate(rows, 1):
        title, isbn, price, stock, category_slug, published_at, author_key = row
        book = Book(
            title=title,
            isbn=isbn,
            price_vnd=price,
            stock=stock,
            category=categories[category_slug],
            published_at=published_at,
            created_at=created_base.replace(day=index),
        )
        book.author_links.append(BookAuthor(author=authors[author_key], role="lead"))
        books.append(book)

    books[1].author_links.append(BookAuthor(author=authors["thomas"], role="co"))
    db.session.add_all(books)
    db.session.flush()
    db.session.add_all(
        [
            Review(book=books[0], user=users[0], rating=5, content="Rõ ràng và thực tế."),
            Review(book=books[7], user=users[1], rating=4, content="Thế giới xây dựng rất cuốn hút."),
        ]
    )
    db.session.commit()
