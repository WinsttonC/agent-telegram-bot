from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship, declarative_base, sessionmaker

# SQLite Database URL
db_url = "sqlite:///main_database.db"

# Create an engine
engine = create_engine(db_url, connect_args={"check_same_thread": False})

# Create a declarative base
Base = declarative_base()

# Define a sample table - History
class History(Base):
    __tablename__ = "chat_history"
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, index=True)
    history = Column(String, index=True)

# Define another table - Tool
class Tools(Base):
    __tablename__ = "agents_tools"
    id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

# Create the tables in the database
Base.metadata.create_all(bind=engine)

# Create a session to interact with the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Example usage for History table:
history_entry = History(telegram_id=123456789, history="Some historical data")
db.add(history_entry)
db.commit()

# Example usage for Tool table:
tool_entry = Tools(tool_name="Some Tool", is_active=True)
db.add(tool_entry)
db.commit()

# history_entries = db.query(History).all()
# tool_entries = db.query(Tools).filter(Tools.is_active == True).all()

# Remember to commit changes and close the session after use:
db.commit()
db.close()
