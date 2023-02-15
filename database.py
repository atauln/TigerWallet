from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime, Float
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import datetime
from time import time
import os

url = f"mysql://{os.environ['DB_USERNAME']}:{os.environ['DB_PASSWORD']}@{os.environ['DB_URL']}/{os.environ['DB_USERNAME']}"
engine = create_engine(url)

class Base(DeclarativeBase):
    pass

class UserInfo(Base):
    __tablename__ = 'UserInfo'

    uid: Mapped[str] = mapped_column(String(37), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(32))
    last_name: Mapped[str] = mapped_column(String(32))
    pref_name: Mapped[str] = mapped_column(String(32))
    first_sign_in: Mapped[datetime.datetime] = mapped_column(DateTime)
    last_sign_in: Mapped[datetime.datetime] = mapped_column(DateTime)
    total_auths: Mapped[int] = mapped_column()

    def __repr__(self):
        return f'UserInfo(uid={self.uid}, first_name={self.first_name}, last_name={self.last_name}, pref_name={self.pref_name}, first_sign_in={self.first_sign_in}, last_sign_in={self.last_sign_in}, total_auths={self.total_auths})'

class UserSettings(Base):
    __tablename__ = 'UserSettings'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'), primary_key=True)
    credential_sync: Mapped[bool] = mapped_column()
    receipt_notifications: Mapped[bool] = mapped_column()
    balance_notifications: Mapped[bool] = mapped_column()
    email_address: Mapped[str] = mapped_column(String(64))
    phone_number: Mapped[str] = mapped_column(String(16))

    def __repr__(self):
        return f'UserSettings(uid={self.uid}, credential_sync={self.credential_sync}, receipt_notifications={self.receipt_notifications}, balance_notifications={self.balance_notifications}, email_address={self.email_address}, phone_number={self.phone_number})'

    def toJson(self):
        return {
            'uid': self.uid,
            'credential_sync': self.credential_sync,
            'receipt_notifications': self.receipt_notifications,
            'balance_notifications': self.balance_notifications,
            'email_address': self.email_address,
            'phone_number': self.phone_number
        }

class Purchases(Base):
    __tablename__ = 'Purchases'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'))
    dt: Mapped[datetime.datetime] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(64))
    amount: Mapped[float] = mapped_column(Float)
    new_balance: Mapped[float] = mapped_column(Float)
    plan_id: Mapped[int] = mapped_column()
    pid: Mapped[str] = mapped_column(String(32), primary_key=True)

    def __repr__(self):
        return f'Purchases(uid={self.uid}, dt={self.dt}, location={self.location}, amount={self.amount}, new_balance={self.new_balance}, pid={self.pid}, plan_id={self.plan_id})'

class SessionData(Base):
    __tablename__ = 'SessionData'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'), primary_key=True)
    theme: Mapped[str] = mapped_column()
    skey: Mapped[str] = mapped_column(String(32))
    default_plan: Mapped[int] = mapped_column()

    def __repr__(self):
        return f'SessionData(uid={self.uid}, theme={self.theme}, skey={self.skey}, default_plan={self.default_plan})'

class MealPlans(Base):
    __tablename__ = 'MealPlans'

    uid: Mapped[str] = mapped_column(String(37), ForeignKey('UserInfo.uid'))
    plan_id: Mapped[int] = mapped_column()
    plan_name: Mapped[str] = mapped_column(String(64))
    pid: Mapped[str] = mapped_column(String(32), primary_key=True)

    def __repr__(self):
        return f'MealPlans(uid={self.uid}, plan_id={self.plan_id}, plan_name={self.plan_name}, pid={self.pid})'


def create_user(uid: str, first_name: str, last_name: str, pref_name: str, skey: str, default_plan: int, plans):
    """Creates User, session data, and fills in meal plans"""
    with Session(engine) as session:
        user = UserInfo(
            uid=uid,
            first_name=first_name,
            last_name=last_name,
            pref_name=pref_name,
            first_sign_in=datetime.datetime.now(),
            last_sign_in=datetime.datetime.now(),
            total_auths=1
        )

        user_settings = UserSettings(uid=uid, credential_sync=True, receipt_notifications=False, balance_notifications=False);

        session.add(user)
        session.add(user_settings)
        session.commit()
    create_session_data(uid, skey, default_plan)
    replace_meal_plans(uid, [MealPlans(uid=uid, plan_id=plan[0], plan_name=plan[1], pid=time()) for plan in plans])

def create_session_data(uid: str, skey: str, default_plan: int):
    with Session(engine) as session:
        session_data = SessionData(
            uid=uid,
            theme='dark',
            skey=skey,
            default_plan=default_plan
        )

        session.add(session_data)
        session.commit()

def update_user(uid: str, first_name: str, last_name: str, pref_name: str, skey: str):
    with Session(engine) as session:
        session.query(UserInfo).filter(UserInfo.uid == uid).update({
            UserInfo.first_name: first_name,
            UserInfo.last_name: last_name,
            UserInfo.pref_name: pref_name,
            UserInfo.last_sign_in: datetime.datetime.now()
        })

        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.theme: 'dark',
            SessionData.skey: skey,
        })

        session.commit()

def remove_user(uid: str):
    with Session(engine) as session:
        session.query(MealPlans).filter(MealPlans.uid == uid).delete()
        session.query(SessionData).filter(SessionData.uid == uid).delete()
        session.query(Purchases).filter(Purchases.uid == uid).delete()
        session.query(UserSettings).filter(UserSettings.uid == uid).delete()
        session.query(UserInfo).filter(UserInfo.uid == uid).delete()
        session.commit()

def get_user(uid: str):
    with Session(engine) as session:
        return session.query(UserInfo).filter(UserInfo.uid == uid).first()

def get_user_with_skey(skey: str):
    with Session(engine) as session:
        return session.query(UserInfo).join(SessionData).filter(SessionData.skey == skey).first()

def get_session_data(uid: str):
    with Session(engine) as session:
        return session.query(SessionData).filter(SessionData.uid == uid).first()

def get_meal_plans(uid: str):
    with Session(engine) as session:
        return session.query(MealPlans).filter(MealPlans.uid == uid).all()

def get_purchases(uid: str, plan_id: int):
    with Session(engine) as session:
        result = session.query(Purchases).filter(Purchases.uid == uid).filter(Purchases.plan_id == plan_id).all()
        return result if result != [] else None

def add_purchase(purchase: Purchases):
    with Session(engine) as session:
        session.add(purchase)
        session.commit()

def safely_add_purchases(uid: str, purchases):
    with Session(engine) as session:
        session.query(Purchases).filter(Purchases.uid == uid).filter(Purchases.plan_id == purchases[0].plan_id).delete()
        #print (f"DELETED {uid} {purchases[0].plan_id}")
        session.add_all(purchases)
        session.commit()

def add_meal_plans(meal_plans):
    with Session(engine) as session:
        session.add_all(meal_plans)
        session.commit()

def replace_meal_plans(uid: str, meal_plans):
    with Session(engine) as session:
        session.query(MealPlans).filter(MealPlans.uid == uid).delete()
        session.add_all(meal_plans)
        session.commit()

def update_session_data(uid: str, theme: str, skey: str, default_plan: int):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.theme: theme,
            SessionData.skey: skey,
            SessionData.default_plan: default_plan
        })
        session.commit()

def log_user_auth(uid: str):
    with Session(engine) as session:
        session.query(UserInfo).filter(UserInfo.uid == uid).update({
            UserInfo.last_sign_in: datetime.datetime.now(),
            UserInfo.total_auths: UserInfo.total_auths + 1
        })
        session.commit()

def update_skey(uid: str, skey: str):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.skey: skey
        })
        session.commit()

def user_exists(uid: str):
    with Session(engine) as session:
        return session.query(UserInfo).filter(UserInfo.uid == uid).first() is not None

def change_user_theme(uid: str, theme: str):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.theme: theme
        })
        session.commit()

def change_default_plan(uid: str, plan_id: int):
    with Session(engine) as session:
        session.query(SessionData).filter(SessionData.uid == uid).update({
            SessionData.default_plan: plan_id
        })
        session.commit()

def get_number_of_users():
    with Session(engine) as session:
        return session.query(UserInfo).count()

def get_number_of_purchases():
    with Session(engine) as session:
        return session.query(Purchases).count()

def get_all_sessions():
    with Session(engine) as session:
        return session.query(SessionData).all()

def change_email(uid: str, email_address: str):
    with Session(engine) as session:
        session.query(UserSettings).filter(UserSettings.uid == uid).update({
            UserSettings.email_address: email_address
        })
        session.commit()

def update_user_settings(settings: UserSettings):
    with Session(engine) as session:
        session.query(UserSettings).filter(UserSettings.uid == settings.uid).delete()
        session.add(settings)
        session.commit()

def get_user_settings(uid: str):
    with Session(engine) as session:
        return session.query(UserSettings).filter(UserSettings.uid == uid).first()
