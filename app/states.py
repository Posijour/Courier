from aiogram.fsm.state import State, StatesGroup


class StartShiftStates(StatesGroup):
    waiting_for_mode = State()


class CloseShiftStates(StatesGroup):
    waiting_for_total = State()


class AdvancedOrderStates(StatesGroup):
    waiting_for_district = State()
    waiting_for_platform = State()
    waiting_for_earnings = State()


class ResearchOrderStates(StatesGroup):
    waiting_for_platform = State()
    waiting_for_position_district = State()
    waiting_for_pickup_district = State()
    waiting_for_dropoff_district = State()
    waiting_for_earnings = State()
