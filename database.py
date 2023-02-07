from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Float
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import datetime
import os

url = f"mysql://{os.environ['DB_USERNAME']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_URL']}/{os.environ['DB_USERNAME']}']}}"
engine = create_engine(url, echo=True)

class Base(DeclarativeBase):
    pass

class UserInfo(Base):
    __tablename__ = 'UserInfo'

    uid: Mapped[str] = mapped_column(String(37), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(32))
    last_name: Mapped[str] = mapped_column(String(32))
    pref_name: Mapped[str] = mapped_column(String(32))
    first_signed_in: Mapped[datetime.datetime] = mapped_column(DateTime)
    last_signed_in: Mapped[datetime.datetime] = mapped_column(DateTime)
    total_auths: Mapped[int] = mapped_column()

    def __repr__(self):
        return f'UserInfo(uid={self.uid}, first_name={self.first_name}, last_name={self.last_name}, pref_name={self.pref_name}, first_signed_in={self.first_signed_in}, last_signed_in={self.last_signed_in}, total_auths={self.total_auths})'

class Purchases(Base):
    __tablename__ = 'Purchases'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'), primary_key=True)
    dt: Mapped[datetime.datetime] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(64))
    amount: Mapped[float] = mapped_column(Float)
    new_balance: Mapped[float] = mapped_column(Float)

    def __repr__(self):
        return f'Purchases(uid={self.uid}, dt={self.dt}, location={self.location}, amount={self.amount}, new_balance={self.new_balance})'

class SessionData(Base):
    __tablename__ = 'SessionData'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'), primary_key=True)
    theme: Mapped[int] = mapped_column()
    skey: Mapped[str] = mapped_column(String(32))
    default_plan: Mapped[int] = mapped_column()

    def __repr__(self):
        return f'SessionData(uid={self.uid}, theme={self.theme}, skey={self.skey}, default_plan={self.default_plan})'

class MealPlans(Base):
    __tablename__ = 'MealPlans'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'), primary_key=True)
    plan_id: Mapped[int] = mapped_column()
    plan_name: Mapped[str] = mapped_column(String(64))

    def __repr__(self):
        return f'MealPlans(uid={self.uid}, plan_id={self.plan_id}, plan_name={self.plan_name})'


def create_user(uid: str, first_name: str, last_name: str, pref_name: str, skey: str, default_plan: int, plans: list[tuple[int, str]]):
    with Session(engine) as session:
        user = UserInfo(
            uid=uid,
            first_name=first_name,
            last_name=last_name,
            pref_name=pref_name,
            first_signed_in=datetime.datetime.now(),
            last_signed_in=datetime.datetime.now(),
            total_auths=1
        )

        session_data = SessionData(
            uid=uid,
            theme=0,
            skey=skey,
            default_plan=default_plan
        )

        meal_plans = [MealPlans(uid=uid, plan_id=plan[0], plan_name=plan[1]) for plan in plans]

        session.add(user)
        session.add(session_data)
        session.add_all(meal_plans)
        session.commit()

def remove_user(uid: str):
    with Session(engine) as session:
        session.query(UserInfo).filter(UserInfo.uid == uid).delete()
        session.query(SessionData).filter(SessionData.uid == uid).delete()
        session.query(MealPlans).filter(MealPlans.uid == uid).delete()
        session.query(Purchases).filter(Purchases.uid == uid).delete()
        session.commit()

def get_user(uid: str):
    with Session(engine) as session:
        return session.query(UserInfo).filter(UserInfo.uid == uid).first()

def get_session_data(uid: str):
    with Session(engine) as session:
        return session.query(SessionData).filter(SessionData.uid == uid).first()

def get_meal_plans(uid: str):
    with Session(engine) as session:
        return session.query(MealPlans).filter(MealPlans.uid == uid).all()

def get_purchases(uid: str):
    with Session(engine) as session:
        return session.query(Purchases).filter(Purchases.uid == uid).all()

def add_purchase(purchase: Purchases):
    with Session(engine) as session:
        session.add(purchase)
        session.commit()

def add_purchases(purchases: list[Purchases]):
    with Session(engine) as session:
        session.add_all(purchases)
        session.commit()

def replace_meal_plans(uid: str, meal_plans: list[MealPlans]):
    with Session(engine) as session:
        session.query(MealPlans).filter(MealPlans.uid == uid).delete()
        session.add_all(meal_plans)
        session.commit()

def update_session_data(uid: str, theme: int, skey: str, default_plan: int):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.theme: theme,
            SessionData.skey: skey,
            SessionData.default_plan: default_plan
        })
        session.commit()

def update_user(uid: str, first_name: str, last_name: str, pref_name: str, account_number: int):
    with Session(engine) as session:
        session.query(UserInfo).filter(UserInfo.uid == uid).update({
            UserInfo.first_name: first_name,
            UserInfo.last_name: last_name,
            UserInfo.pref_name: pref_name,
        })
        session.commit()

def change_user_theme(uid: str, theme: int):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.theme: theme
        })
        session.commit()