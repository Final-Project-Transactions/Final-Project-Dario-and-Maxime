import bcrypt


def hash_password(password):
    """Turn a password into a hash that can be stored in the database."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    """True if the typed password matches the stored hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())
