import sqlalchemy.orm as orm
from datetime import datetime

class Base(orm.DeclarativeBase):
  pass

class Wallet(Base):
  __tablename__ = "wallets"

  adress: orm.Mapped[str] = orm.mapped_column(primary_key=True)
  earliest_tsx: orm.Mapped[None | datetime] = orm.mapped_column(default=None)
  good: orm.Mapped[bool] = orm.mapped_column(default=False)