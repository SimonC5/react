from sqlalchemy import create_engine

try:
    from .models import Base
except ImportError:
    from models import Base


def initialize_models(database_path):
    engine = create_engine(f'sqlite:///{database_path}', future=True)
    Base.metadata.create_all(engine)
    return engine
