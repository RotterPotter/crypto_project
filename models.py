import sqlalchemy.orm as orm
from datetime import datetime
from sqlalchemy import ForeignKey

class Base(orm.DeclarativeBase):
  pass

class Wallet(Base):
  __tablename__ = "wallets"

  adress: orm.Mapped[str] = orm.mapped_column(primary_key=True)
  earliest_tsx: orm.Mapped[None | datetime] = orm.mapped_column(default=None)
  average_total_return_per_month: orm.Mapped[float] = orm.mapped_column(default=0)
  traded_tokens: orm.Mapped[int] = orm.mapped_column(default=0)
  good: orm.Mapped[bool] = orm.mapped_column(default=False)