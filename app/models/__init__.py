# SQLAlchemy ORM models will be imported here for Alembic autogeneration.

from app.database import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.expense import Expense  # noqa: F401
from app.models.budget import Budget  # noqa: F401
from app.models.currency_rate import CurrencyRate  # noqa: F401 