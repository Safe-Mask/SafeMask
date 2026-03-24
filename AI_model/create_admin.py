import bcrypt
import os
from sqlalchemy.orm import sessionmaker
from models import engine, User
from dotenv import load_dotenv
load_dotenv()


Session = sessionmaker(bind=engine)
session = Session()

def create_super_user() :
    print('Criando usuário admin')

    username = os.getenv('ADMIN_USER')
    email = os.getenv('ADMIN_MAIL')
    senha_plana = os.getenv('ADMIN_PASS')

    salt = bcrypt.gensalt()
    senha_hash = bcrypt.hashpw(senha_plana.encode('utf-8'), salt)
    senha_hash_str = senha_hash.decode('utf-8')


    usuario_existente = session.query(User).filter_by(username=username).first()

    if usuario_existente :
        print(f"O usuário {username} já existe")
        return
    
    novo_admin = User(
        username=username,
        email=email,
        password_hash = senha_hash_str,
        acess_level = 4
    )

    try :
        session.add(novo_admin)
        session.commit()
        print("Usuário criado")
        print(f"Login : {username}")
        print(f"Senha : {senha_plana}")
        print(f"Hash no banco : {senha_hash_str}")
    except Exception as e :
        session.rollback()
        print(f"Erro ao criar usuário {e}")
    finally:
        session.close()

if __name__ == "__main__" :
    create_super_user()