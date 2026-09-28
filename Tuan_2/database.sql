BEGIN TRANSACTION;
CREATE TABLE books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT,
            price REAL
        );
INSERT INTO "books" VALUES(1,'Clean Code','Robert C. Martin','9780132350884',30.0);
INSERT INTO "books" VALUES(2,'The Pragmatic Programmer','Andrew Hunt','9780135957059',42.5);
CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            status TEXT NOT NULL
        );
INSERT INTO "orders" VALUES(1,'Clean Code',1,30.0,'PENDING');
INSERT INTO "orders" VALUES(2,'The Pragmatic Programmer',2,85.0,'COMPLETED');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('books',2);
INSERT INTO "sqlite_sequence" VALUES('orders',2);
COMMIT;
