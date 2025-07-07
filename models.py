import sqlalchemy.orm as orm

class Base(orm.DeclarativeBase):
  pass

class Wallet(Base):
  __tablename__ = "wallets"

  adress: orm.Mapped[str] = orm.mapped_column(primary_key=True)