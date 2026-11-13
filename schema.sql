/*The database is built around a central users table. Every other table 
points to it: each transaction, friendship and group membership links back 
to a user ID. Rules inside the database (foreign keys and CHECK constraints) 
make sure only valid data can be stored, for example 
no transaction without an existing user and no friendship with yourself. */

CREATE TABLE users (
    id             SERIAL PRIMARY KEY,
    username       TEXT UNIQUE NOT NULL,
    password_hash  TEXT NOT NULL,
    household_type TEXT,
    created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE categories (
    name TEXT PRIMARY KEY
);

CREATE TABLE transactions (
    id        SERIAL PRIMARY KEY,
    user_id   INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date      DATE NOT NULL,
    merchant  TEXT,
    amount    NUMERIC(10,2) NOT NULL,
    category  TEXT REFERENCES categories(name),
    source    TEXT NOT NULL CHECK (source IN ('bank', 'cash'))
);
CREATE INDEX idx_tx_user_date ON transactions (user_id, date);

CREATE TABLE friendships (
    user_id   INT REFERENCES users(id) ON DELETE CASCADE,
    friend_id INT REFERENCES users(id) ON DELETE CASCADE,
    status    TEXT NOT NULL DEFAULT 'pending'
              CHECK (status IN ('pending', 'accepted')),
    PRIMARY KEY (user_id, friend_id),
    CHECK (user_id <> friend_id)
);

CREATE TABLE user_groups (
    id         SERIAL PRIMARY KEY,
    name       TEXT NOT NULL,
    created_by INT REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE group_members (
    group_id INT REFERENCES user_groups(id) ON DELETE CASCADE,
    user_id  INT REFERENCES users(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, user_id)
);

INSERT INTO categories (name) VALUES
  ('Groceries'), ('Restaurants'), ('Transport'), ('Housing'),
  ('Health'), ('Leisure'), ('Clothing'), ('Communication'), ('Other');