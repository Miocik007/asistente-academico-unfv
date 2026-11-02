"""Genera un hash para colocar en [users] dentro de secrets.toml."""
import getpass
import hashlib
import secrets

user = input('Nombre de usuario (sin espacios): ').strip()
if not user or not all(c.isalnum() or c in '._-' for c in user):
    raise SystemExit('Nombre de usuario no válido')
pwd = getpass.getpass('Contraseña nueva (no se muestra): ')
if len(pwd) < 10:
    raise SystemExit('Usa una contraseña de al menos 10 caracteres')
salt = secrets.token_hex(16)
rounds = 350_000
hash_ = hashlib.pbkdf2_hmac('sha256', pwd.encode(), bytes.fromhex(salt), rounds).hex()
print('\nColoca esta línea debajo de [users] en secrets.toml:')
print(f'{user} = "pbkdf2_sha256${rounds}${salt}${hash_}"')
