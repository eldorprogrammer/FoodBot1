from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_address = State()


class CheckoutStates(StatesGroup):
    waiting_address = State()
    waiting_phone = State()
    waiting_comment = State()
    waiting_payment_method = State()


class AdminAuthStates(StatesGroup):
    waiting_login = State()
    waiting_password = State()


class AdminCategoryStates(StatesGroup):
    waiting_name = State()
    waiting_rename = State()


class AdminItemStates(StatesGroup):
    waiting_category = State()
    waiting_name = State()
    waiting_description = State()
    waiting_price = State()
    waiting_photo = State()
    waiting_edit_field = State()
    waiting_edit_value = State()
