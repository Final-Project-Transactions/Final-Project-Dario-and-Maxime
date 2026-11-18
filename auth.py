import bcrypt


def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password, password_hash):
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Funktion wird definiert und in der Klammer gibt man das Passwort ein
# -> encode wandelt word in bytes, salt gibt zusätzlicher wert, damit wenn 2x gleiches Wort trotzdem unterschiedlicher wert, bcryp.haspw nimmt beides zusammen heisst salt und wort und dadurch ein prüfwert, decode wandelt byte wieder in text um.
# -> password ist das wort was eingegeben wird, password_hash
# Beide werden bei encode in bytes umgewandelt und bcrypt.checkpw nimmt den ursprünglichen salt vom gespeicherten Wert und dann sagt das return wenn stimmt ob True oder False
