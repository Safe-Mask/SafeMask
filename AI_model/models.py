import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from dotenv import load_dotenv
load_dotenv()

senha = os.getenv('DB_PASS')
usuario = os.getenv('DB_USER')
banco = os.getenv('DB_NAME')

DATABASE_URL = f"postgresql://{usuario}:{senha}@localhost:5432/{banco}"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key = True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    acess_level = Column(Integer, default=0)
    documents = relationship("Document", back_populates="owner")

class Document(Base):
    __tablename__ = 'documents'

    id= Column(Integer, primary_key=True)
    filename = Column(String(200), nullable=False)
    filepath = Column(String(500), nullable=False)
    upload_date = Column(DateTime, default=datetime.datetime.utcnow)
    file_hash = Column(String(64), nullable=True)
    owner_id = Column(Integer, ForeignKey('users.id'))
    owner = relationship("User", back_populates="documents")
    
    # Relacionamento: Um documento tem vários trechos sensíveis
    sensitive_data = relationship("SensitiveData", back_populates="document")


class SensitiveData(Base) :
    __tablename__ = 'sensitive_data_map'

    id = Column(Integer,primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))

    # Oq é ? cpf, nome, salario ...
    entity_type = Column(String(50))
    original_content_encrypted = Column(Text, nullable=False)
    page = Column(Integer, nullable=False, default=0)
    #Cordenadas onde os dados sensiveis estão no documento
    coordinates = Column(JSON, nullable=False)

    required_level = Column(Integer, default=4)

    document = relationship("Document", back_populates="sensitive_data")


################
### Execução ###
################ 
if __name__ == "__main__" :
    try :
        print("Conectando ao PostgreSQL")
        Base.metadata.create_all(engine)
        print('Tabelas Criadas com sucesso')
        print(" - Tabela 'users' criada")
        print(" - Tabela 'documents' criada")
        print(" - Tabela 'sensitive_data_map' criada")
    except Exception as e :
        print("Erro ao Criar as tabelas")
        print(e)

