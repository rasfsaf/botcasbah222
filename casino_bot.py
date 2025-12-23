# Telegram Casino Bot - Рулетка и Black Jack
# Версия: 5 - Казино Щедрый Еврей (ИСПРАВЛЕННЫЙ BLACK JACK в группе, ДОБАВЛЕНЫ СЛОТЫ!!!)
# Валюта: Шекели

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage

# =============== КОНФИГУРАЦИЯ ===============
TOKEN = "8544075261:AAGetzEOJwrIiJn4bYF9CT1fvmt_iJXLuJQ"
USERS_DATA_FILE = "users_data.json"

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# =============== СКЛОНЕНИЯ ===============
def declension(num: int, word1: str, word2: str, word5: str) -> str:
    """Правильное склонение слова по числу"""
    if num % 10 == 1 and num % 100 != 11:
        return word1
    elif num % 10 in [2, 3, 4] and num % 100 not in [12, 13, 14]:
        return word2
    else:
        return word5

def format_currency(num: int) -> str:
    """Форматировать число с правильным названием валюты"""
    word = declension(num, "Шекель", "Шекеля", "Шекелей")
    return f"**{num}** 🪙 {word}"

# =============== СОСТОЯНИЯ ===============
class GameStates(StatesGroup):
    main_menu = State()
    roulette_betting = State()
    roulette_spinning = State()
    blackjack_betting = State()
    blackjack_playing = State()
    group_roulette_waiting = State()
    group_blackjack_betting = State()
    group_blackjack_playing = State()
    slots_betting = State()
    slots_spinning = State()


# =============== БАЗА ДАННЫХ ===============
users_data: Dict[int, dict] = {}
group_roulette_games: Dict[int, dict] = {}
group_blackjack_games: Dict[int, dict] = {}

# =============== ФУНКЦИИ СОХРАНЕНИЯ/ЗАГРУЗКИ ===============
def load_users_data():
    """Загрузить данные пользователей из файла"""
    global users_data
    if os.path.exists(USERS_DATA_FILE):
        try:
            with open(USERS_DATA_FILE, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
                print(f"✅ Загружено {len(users_data)} пользователей из файла")
        except Exception as e:
            print(f"❌ Ошибка при загрузке данных: {e}")
            users_data = {}
    else:
        print("📝 Файл данных не найден, создаём новый")
        users_data = {}

def save_users_data():
    """Сохранить данные пользователей в файл"""
    try:
        with open(USERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Ошибка при сохранении данных: {e}")

def get_user(user_id: int) -> dict:
    """Получить данные пользователя или создать новые"""
    user_id_str = str(user_id)
    if user_id_str not in users_data:
        users_data[user_id_str] = {
            'shekels': 1000,
            'total_won': 0,
            'total_lost': 0,
            'games_played': 0,
            'username': 'Unknown',
            'transfers_sent': 0,
            'transfers_received': 0,
        }
        save_users_data()
    else:
        user = users_data[user_id_str]
        if 'transfers_sent' not in user:
            user['transfers_sent'] = 0
        if 'transfers_received' not in user:
            user['transfers_received'] = 0
        users_data[user_id_str] = user
        save_users_data()
    return users_data[user_id_str]


def get_user_by_username(username: str) -> dict | None:
    """
    Найти пользователя по username (без @).
    Возвращает словарь данных или None.
    """
    for u_id, data in users_data.items():
        if data.get("username") == username:
            return data
    return None

def get_user_name(user: types.User) -> str:
    # ОСТАВЬ как отображаемое имя
    return user.first_name or user.username or "Игрок"

def save_user(user_id: int, data: dict):
    """Сохранить данные пользователя"""
    user_id_str = str(user_id)
    users_data[user_id_str] = data
    save_users_data()

def create_main_menu(user: dict, player_name: str) -> str:
    """Создать текст главного меню"""
    welcome_text = f"""
🎰 **ДОБРО ПОЖАЛОВАТЬ В КАЗИНО ЩЕДРЫЙ ЕВРЕЙ!** 🎰

Привет, {player_name}! 👋

Ваш баланс: {format_currency(user['shekels'])}

**Доступные игры:**
1️⃣ **Рулетка** - классическая игра везения
2️⃣ **Black Jack** - игра против дилера
3️⃣ **Рулетка в группе** - играй с друзьями
4️⃣ **Black Jack в группе** - групповая игра
5️⃣ **Слоты - проверь свою удачу

Выберите игру или посмотрите статистику!
    """
    return welcome_text

# =============== ГЛАВНОЕ МЕНЮ ===============
@dp.message(Command("start", "casino"))
async def start_command(message: types.Message, state: FSMContext):
    """Начало работы бота"""
    user_id = message.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(message.from_user)
    user['username'] = message.from_user.username or player_name
    save_user(user_id, user)

    await state.set_state(GameStates.main_menu)

    welcome_text = create_main_menu(user, player_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
                InlineKeyboardButton(text="♠️ Black Jack", callback_data="game_blackjack"),
            ],
            [
                InlineKeyboardButton(text="🎡 Рулетка в группе", callback_data="group_roulette_menu"),
                InlineKeyboardButton(text="♠️ Black Jack в группе", callback_data="group_blackjack_menu"),
            ],
            [InlineKeyboardButton(text="🎰 СЛОТЫ(НОВОЕ!)", callback_data="slots_menu")],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            ],
            [
            InlineKeyboardButton(text="💸 Перевод шекелей", callback_data="transfer_menu"),
        ],
            

        ]
    )

    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "transfer_menu")
async def transfer_menu(callback: types.CallbackQuery):
    text = (
        "💸 **ПЕРЕВОД ШЕКЕЛЕЙ** 💸\n\n"
        "Чтобы перевести валюту другому игроку, используй команду:\n"
        "`/pay @username сумма`\n\n"
        "Пример: `/pay @user 150`"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.message(Command("pay"))
async def pay_command(message: types.Message):
    """
    /pay @username amount
    """
    user_id = message.from_user.id
    sender = get_user(user_id)

    parts = message.text.split()
    if len(parts) != 3:
        await message.reply("❌ Использование: /pay @username сумма")
        return

    raw_username = parts[1]
    amount_str = parts[2]

    if not raw_username.startswith("@"):
        await message.reply("❌ Укажи получателя как @username")
        return

    try:
        amount = int(amount_str)
    except ValueError:
        await message.reply("❌ Сумма должна быть целым числом")
        return

    if amount <= 0:
        await message.reply("❌ Сумма должна быть больше нуля")
        return

    if sender["shekels"] < amount:
        await message.reply(
            f"❌ Недостаточно средств! У тебя {format_currency(sender['shekels'])}, нужно {format_currency(amount)}",
            parse_mode="Markdown",
        )
        return

    username = raw_username[1:]
    receiver = get_user_by_username(username)
    if receiver is None:
        await message.reply("❌ Игрок с таким @username ещё не заходил в бота.")
        return

    sender["shekels"] -= amount
    sender["total_lost"] += amount
    sender["transfers_sent"] = sender.get("transfers_sent", 0) + amount

    receiver["shekels"] += amount
    receiver["total_won"] += amount
    receiver["transfers_received"] = receiver.get("transfers_received", 0) + amount
    
    save_user(user_id, sender)

    receiver_id = None
    for u_id, data in users_data.items():
        if data is receiver:
            receiver_id = int(u_id)
            break
    if receiver_id is not None:
        save_user(receiver_id, receiver)

    await message.reply(
        f"✅ Перевод выполнен!\n"
        f"Ты отправил {format_currency(amount)} игроку @{username}.\n"
        f"Твой новый баланс: {format_currency(sender['shekels'])}",
        parse_mode="Markdown",
    )

    if receiver_id is not None:
        try:
            await bot.send_message(
                receiver_id,
                f"💰 Ты получил {format_currency(amount)} от @{message.from_user.username or 'игрока'}!",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        
    if receiver_id is not None:
        try:
            await bot.send_message(
                receiver_id,
                f"💰 Ты получил {format_currency(amount)} от @{message.from_user.username or 'игрока'}!",
                parse_mode="Markdown",
            )
        except Exception:
            pass


    # =============== СЛОТЫ - ФУНКЦИИ ПОМОЩИ ===============
def check_win(symbols: List[str], bet: int) -> tuple:
    """Проверить выигрышную комбинацию"""
    s1, s2, s3 = symbols[0], symbols[1], symbols[2]
    
    # ДЖЕКПОТ - все три одинаковы
    if s1 == s2 == s3:
        if s1 == '🎰':
            return (bet * 100, "СУПЕР ДЖЕКПОТ! 🎰🎰🎰")
        elif s1 == '👑':
            return (bet * 50, "ТРИ КОРОНЫ! 👑👑👑")
        elif s1 == '💎':
            return (bet * 30, "ТРИ АЛМАЗА! 💎💎💎")
        elif s1 == '⭐':
            return (bet * 20, "ТРИ ЗВЕЗДЫ! ⭐⭐⭐")
        elif s1 == '🔔':
            return (bet * 15, "ТРИ КОЛОКОЛА! 🔔🔔🔔")
        elif s1 == '💰':
            return (bet * 25, "ТРИ ЗОЛОТЫХ! 💰💰💰")
        else:
            return (bet * 5, f"ТРИ {s1}! {s1}{s1}{s1}")
    
    # Две идентичные (рядом)
    if s1 == s2 or s2 == s3:
        symbol = s1 if s1 == s2 else s3
        if symbol == '💎':
            return (bet * 10, f"ДВА АЛМАЗА! {symbol}{symbol}")
        elif symbol == '⭐':
            return (bet * 8, f"ДВЕ ЗВЕЗДЫ! {symbol}{symbol}")
        else:
            return (bet * 3, f"ДВА {symbol}! {symbol}{symbol}")
    
    # Две одинаковые (не рядом)
    if s1 == s3:
        return (bet * 2, f"ПОЧТИ! {s1}__{s1}")
    
    return (0, "Нет выигрыша ❌")

def spin_slot() -> List[str]:
    """Вращение одного барабана слота"""
    symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '👑', '⭐', '🔔', '🎰', '💰']
    return [random.choice(symbols) for _ in range(3)]

def spin_gold_slot() -> List[str]:
    """Вращение с смещением к редким символам"""
    rare_symbols = ['💎', '💰', '👑']
    common_symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '🔔', '🎰']
    all_symbols = rare_symbols + common_symbols * 5
    return [random.choice(all_symbols) for _ in range(3)]


# =============== СЛОТЫ МЕНЮ ===============

@dp.callback_query(lambda c: c.data == "slots_menu")
async def slots_main_menu(callback: types.CallbackQuery):
    """Главное меню слотов"""
    text = """
🎰 **ВЫБЕРИТЕ ТИП СЛОТОВ** 🎰

**Доступные слоты:**

1️⃣ **Классические слоты** - стандартные правила
2️⃣ **Слоты с мультипликатором** - случайный множитель выигрыша
3️⃣ **Удача или смерть** - все или ничего, 100x выигрыш
4️⃣ **Золотая лихорадка** - редкие золотые символы, до 200x
5️⃣ **Бесплатные вращения** - получайте фриспины

"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Классические", callback_data="game_slots")],
            [InlineKeyboardButton(text="✨ С мультипликатором", callback_data="game_slots_multiplier")],
            [InlineKeyboardButton(text="💀 Удача или смерть", callback_data="game_slots_risk")],
            [InlineKeyboardButton(text="💰 Золотая лихорадка", callback_data="game_slots_gold")],
            [InlineKeyboardButton(text="🎁 Бесплатные вращения", callback_data="game_slots_free")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== КЛАССИЧЕСКИЕ СЛОТЫ ===============

@dp.callback_query(lambda c: c.data == "game_slots")
async def slots_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню слотов"""
    await state.set_state(GameStates.slots_betting)
    
    text = """
🎰 **КЛАССИЧЕСКИЕ СЛОТЫ** 🎰

**Правила:**
- Выберите ставку
- Три одинаковых символа = ВЫИГРЫШ!
- 🎰 ДЖЕКПОТ = 100x выигрыш!
- 👑 Три короны = 50x выигрыш
- 💎 Три алмаза = 30x выигрыш
- Две одинаковые рядом = 3-10x выигрыш
- Две одинаковые (не рядом) = 2x выигрыш

Сколько ставите?
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="slots_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="slots_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="slots_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="slots_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="slots_bet_500"),
                InlineKeyboardButton(text="1000 🪙", callback_data="slots_bet_1000"),
            ],
            [
                InlineKeyboardButton(text="5000 🪙", callback_data="slots_bet_5000"),
                InlineKeyboardButton(text="10000 🪙", callback_data="slots_bet_10000"),
                InlineKeyboardButton(text="20000 🪙", callback_data="slots_bet_20000"),
            ],
            [
            InlineKeyboardButton(text="50000 🪙", callback_data="slots_bet_50000"),
            InlineKeyboardButton(text="100000 🪙", callback_data="slots_bet_100000"),
        ],
        [
            InlineKeyboardButton(text="200000 🪙", callback_data="slots_bet_200000"),
            InlineKeyboardButton(text="500000 🪙", callback_data="slots_bet_500000"),
            InlineKeyboardButton(text="1 000 000 🪙", callback_data="slots_bet_1000000"),
        ],
        [   InlineKeyboardButton(text="2 000 000 🪙", callback_data="slots_bet_2000000"),
          InlineKeyboardButton(text="5 000 000 🪙", callback_data="slots_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="slots_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="slots_bet_all"),
         
         ]
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("slots_bet_"))
async def slots_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение слотов"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['shekels'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    reel1 = spin_slot()
    reel2 = spin_slot()
    reel3 = spin_slot()
    result_symbols = [reel1[1], reel2[1], reel3[1]]
    
    winnings, description = check_win(result_symbols, bet)
    
    if winnings > 0:
        user['shekels'] += winnings
        user['total_won'] += winnings
        status = "✅ ВЫИГРЫШ!"
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        status = "❌ ПРОИГРЫШ"
        winnings = -bet
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    reel_display = f"""
{reel1[0]} {reel2[0]} {reel3[0]}
**{reel1[1]} {reel2[1]} {reel3[1]}** ← РЕЗУЛЬТАТ
{reel1[2]} {reel2[2]} {reel3[2]}
"""
    
    text = f"""
🎰 **КЛАССИЧЕСКИЕ СЛОТЫ** 🎰

{reel_display}

**{description}**

**Ставка:** {format_currency(bet)}
**{status}**
**{'+' if winnings >= 0 else ''}{winnings}** 🪙

**Новый баланс:** {format_currency(user['shekels'])}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎰 Ещё раз", callback_data="game_slots"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СЛОТЫ С МУЛЬТИПЛИКАТОРОМ ===============

@dp.callback_query(lambda c: c.data == "game_slots_multiplier")
async def slots_multiplier_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню слотов с мультипликатором"""
    await state.set_state(GameStates.slots_betting)
    
    text = """
✨ **СЛОТЫ С МУЛЬТИПЛИКАТОРОМ** ✨

**Правила:**
- При выигрыше выпадает рандомный мультипликатор
- 🔥 5x, 10x, 20x или даже 50x!
- Джекпот гарантирует минимум 50x

Удача на вашей стороне?
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
            InlineKeyboardButton(text="10 🪙", callback_data="slots_mult_bet_10"),
            InlineKeyboardButton(text="50 🪙", callback_data="slots_mult_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="slots_mult_bet_100"),
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="slots_mult_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="slots_mult_bet_500"),
            InlineKeyboardButton(text="1000 🪙", callback_data="slots_mult_bet_1000"),
        ],
        [
            InlineKeyboardButton(text="5000 🪙", callback_data="slots_mult_bet_5000"),
            InlineKeyboardButton(text="10000 🪙", callback_data="slots_mult_bet_10000"),
            InlineKeyboardButton(text="20000 🪙", callback_data="slots_mult_bet_20000"),
        ],
        [
            InlineKeyboardButton(text="50000 🪙", callback_data="slots_mult_bet_50000"),
            InlineKeyboardButton(text="100000 🪙", callback_data="slots_mult_bet_100000"),
        ],
        [
            InlineKeyboardButton(text="200000 🪙", callback_data="slots_mult_bet_200000"),
            InlineKeyboardButton(text="500000 🪙", callback_data="slots_mult_bet_500000"),
        ],
        [InlineKeyboardButton(text="1 000 000 🪙", callback_data="slots_mult_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="slots_mult_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="slots_mult_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="slots_mult_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="slots_mult_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("slots_mult_bet_"))
async def slots_multiplier_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение слотов с мультипликатором"""
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    reel1 = spin_slot()
    reel2 = spin_slot()
    reel3 = spin_slot()
    result_symbols = [reel1[1], reel2[1], reel3[1]]
    
    base_win, description = check_win(result_symbols, 1)
    
    if base_win > 0:
        multipliers = [5, 10, 15, 20, 50]
        multiplier = random.choice(multipliers)
        
        if "ДЖЕКПОТ" in description:
            multiplier = random.choice([50, 75, 100, 150])
        
        actual_winnings = int(bet * base_win * multiplier)
        user['shekels'] += actual_winnings
        user['total_won'] += actual_winnings
        
        mult_text = f"🔥 x{multiplier} МУЛЬТИПЛИКАТОР!"
        status = "✅ ЭКСТРА ВЫИГРЫШ!"
        result_amount = actual_winnings
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        mult_text = "Нет мультипликатора"
        status = "❌ ПРОИГРЫШ"
        result_amount = -bet
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    reel_display = f"""
{reel1[0]} {reel2[0]} {reel3[0]}
**{reel1[1]} {reel2[1]} {reel3[1]}** ← РЕЗУЛЬТАТ
{reel1[2]} {reel2[2]} {reel3[2]}
"""
    
    text = f"""
✨ **СЛОТЫ С МУЛЬТИПЛИКАТОРОМ** ✨

{reel_display}

**{description}**
**{mult_text}**

**Ставка:** {format_currency(bet)}
**{status}**
**+{result_amount}** 🪙

**Новый баланс:** {format_currency(user['shekels'])}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✨ Ещё раз", callback_data="game_slots_multiplier"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СЛОТЫ "УДАЧА ИЛИ СМЕРТЬ" ===============

@dp.callback_query(lambda c: c.data == "game_slots_risk")
async def slots_risk_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню рискованных слотов"""
    await state.set_state(GameStates.slots_betting)
    
    text = """
💀 **СЛОТЫ "УДАЧА ИЛИ СМЕРТЬ"** 💀

**Экстремальные слоты!**

**Правила:**
- ВСЕ ИЛИ НИЧЕГО!
- Три одинаковых = выигрыш в 100x!
- Другое = ПРОИГРЫШ 💀

Рискни для БОЛЬШОГО выигрыша!
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
            InlineKeyboardButton(text="10 🪙", callback_data="slots_risk_bet_10"),
            InlineKeyboardButton(text="50 🪙", callback_data="slots_risk_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="slots_risk_bet_100"),
        ],
        [
            InlineKeyboardButton(text="500 🪙", callback_data="slots_risk_bet_500"),
            InlineKeyboardButton(text="1000 🪙", callback_data="slots_risk_bet_1000"),
            InlineKeyboardButton(text="5000 🪙", callback_data="slots_risk_bet_5000"),
        ],
        [
            InlineKeyboardButton(text="10000 🪙", callback_data="slots_risk_bet_10000"),
            InlineKeyboardButton(text="20000 🪙", callback_data="slots_risk_bet_20000"),
        ],
        [
            InlineKeyboardButton(text="50000 🪙", callback_data="slots_risk_bet_50000"),
            InlineKeyboardButton(text="100000 🪙", callback_data="slots_risk_bet_100000"),
        ],
        [
            InlineKeyboardButton(text="200000 🪙", callback_data="slots_risk_bet_200000"),
            InlineKeyboardButton(text="500000 🪙", callback_data="slots_risk_bet_500000"),
        ],
        [
        InlineKeyboardButton(text="1 000 000 🪙", callback_data="slots_risk_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="slots_risk_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="slots_risk_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="slots_risk_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="slots_risk_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("slots_risk_bet_"))
async def slots_risk_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение рискованных слотов"""
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    reel1 = spin_slot()
    reel2 = spin_slot()
    reel3 = spin_slot()
    result_symbols = [reel1[1], reel2[1], reel3[1]]
    
    is_jackpot = result_symbols[0] == result_symbols[1] == result_symbols[2]
    
    if is_jackpot:
        winnings = bet * 100
        user['shekels'] += winnings
        user['total_won'] += winnings
        emoji = "🎊🎊🎊"
        status = "🎉 ВЫИГРЫШ!"
        message = f"ВСЕ ТРИ {result_symbols[0]}! x100 ВЫИГРЫШ!"
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        emoji = "💀💀💀"
        status = "💀 СМЕРТЬ!"
        winnings = -bet
        message = "НЕ ВСЕ ТРИ! ВЫ ПОТЕРЯЛИ ВСЁ!"
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    reel_display = f"""
{reel1[0]} {reel2[0]} {reel3[0]}
**{reel1[1]} {reel2[1]} {reel3[1]}**
{reel1[2]} {reel2[2]} {reel3[2]}

{emoji}
"""
    
    text = f"""
💀 **СЛОТЫ "УДАЧА ИЛИ СМЕРТЬ"** 💀

{reel_display}

**{message}**

**Ставка:** {format_currency(bet)}
**{status}**
**{'+' if winnings > 0 else ''}{winnings}** 🪙

**Баланс:** {format_currency(user['shekels'])}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💀 Ещё раз", callback_data="game_slots_risk"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СЛОТЫ "ЗОЛОТАЯ ЛИХОРАДКА" ===============

@dp.callback_query(lambda c: c.data == "game_slots_gold")
async def slots_gold_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню слотов Золотая лихорадка"""
    await state.set_state(GameStates.slots_betting)
    
    text = """
💰 **СЛОТЫ "ЗОЛОТАЯ ЛИХОРАДКА"** 💰

**Правила:**
- Ищите редкие золотые символы: 💎 💰 👑
- 💰💰💰 Три золота = 200x выигрыш!
- 💎💎💎 Три алмаза = 150x выигрыш!
- 👑👑👑 Три короны = 100x выигрыш!

Вероятность редких: 15%
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
            InlineKeyboardButton(text="25 🪙", callback_data="slots_gold_bet_25"),
            InlineKeyboardButton(text="50 🪙", callback_data="slots_gold_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="slots_gold_bet_100"),
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="slots_gold_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="slots_gold_bet_500"),
            InlineKeyboardButton(text="1000 🪙", callback_data="slots_gold_bet_1000"),
        ],
        [
            InlineKeyboardButton(text="5000 🪙", callback_data="slots_gold_bet_5000"),
            InlineKeyboardButton(text="10000 🪙", callback_data="slots_gold_bet_10000"),
            InlineKeyboardButton(text="20000 🪙", callback_data="slots_gold_bet_20000"),
        ],
        [
            InlineKeyboardButton(text="50000 🪙", callback_data="slots_gold_bet_50000"),
            InlineKeyboardButton(text="100000 🪙", callback_data="slots_gold_bet_100000"),
        ],
        [
            InlineKeyboardButton(text="200000 🪙", callback_data="slots_gold_bet_200000"),
            InlineKeyboardButton(text="500000 🪙", callback_data="slots_gold_bet_500000"),
        ],
        [
        InlineKeyboardButton(text="1 000 000 🪙", callback_data="slots_gold_bet_1000000"),
    ],
    [
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="slots_gold_bet_2000000"),
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="slots_gold_bet_5000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="slots_gold_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("slots_gold_bet_"))
async def slots_gold_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение слотов Золотая лихорадка"""
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    reel1 = spin_gold_slot()
    reel2 = spin_gold_slot()
    reel3 = spin_gold_slot()
    result_symbols = [reel1[1], reel2[1], reel3[1]]
    
    s1, s2, s3 = result_symbols
    winnings = 0
    description = ""
    
    if s1 == s2 == s3:
        if s1 == '💰':
            winnings = bet * 200
            description = "💰💰💰 СУПЕР ЗОЛОТО! 200x!"
        elif s1 == '💎':
            winnings = bet * 150
            description = "💎💎💎 АЛМАЗНЫЕ СОКРОВИЩА! 150x!"
        elif s1 == '👑':
            winnings = bet * 100
            description = "👑👑👑 КОРОЛЕВСКИЙ КЛАД! 100x!"
        else:
            winnings = bet * 5
            description = f"{s1}{s1}{s1} Выигрыш! 5x"
    elif (s1 == s2 or s2 == s3):
        symbol = s1 if s1 == s2 else s3
        if symbol in ['💎', '💰', '👑']:
            winnings = bet * 20
            description = f"Два редких {symbol}! 20x"
        else:
            winnings = bet * 3
            description = f"Два {symbol}! 3x"
    elif s1 == s3:
        winnings = bet * 2
        description = f"Две крайние {s1}! 2x"
    else:
        description = "Нет выигрыша"
    
    if winnings > 0:
        user['shekels'] += winnings
        user['total_won'] += winnings
        status = "✅ ВЫИГРЫШ!"
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        status = "❌ НИЧЕГО"
        winnings = -bet
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    reel_display = f"""
{reel1[0]} {reel2[0]} {reel3[0]}
**{reel1[1]} {reel2[1]} {reel3[1]}** ← РЕЗУЛЬТАТ
{reel1[2]} {reel2[2]} {reel3[2]}
"""
    
    text = f"""
💰 **СЛОТЫ "ЗОЛОТАЯ ЛИХОРАДКА"** 💰

{reel_display}

**{description}**

**Ставка:** {format_currency(bet)}
**{status}**
**{'+' if winnings > 0 else ''}{winnings}** 🪙

**Баланс:** {format_currency(user['shekels'])}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💰 Ещё раз", callback_data="game_slots_gold"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== СЛОТЫ С БЕСПЛАТНЫМИ ВРАЩЕНИЯМИ ===============

@dp.callback_query(lambda c: c.data == "game_slots_free")
async def slots_free_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню слотов с бесплатными вращениями"""
    await state.set_state(GameStates.slots_betting)
    
    text = """
🎁 **СЛОТЫ "БЕСПЛАТНЫЕ ВРАЩЕНИЯ"** 🎁

**Уникальный механизм:**
- Получите от 3 до 10 бесплатных вращений!
- Две и более одинаковых = БЕСПЛАТНЫЕ ВРАЩЕНИЯ!
- Все выигрыши в бесплатных вращениях x2 мультипликатор

Бонусная механика!
"""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
             [
            InlineKeyboardButton(text="20 🪙", callback_data="slots_free_bet_20"),
            InlineKeyboardButton(text="50 🪙", callback_data="slots_free_bet_50"),
            InlineKeyboardButton(text="100 🪙", callback_data="slots_free_bet_100"),
        ],
        [
            InlineKeyboardButton(text="250 🪙", callback_data="slots_free_bet_250"),
            InlineKeyboardButton(text="500 🪙", callback_data="slots_free_bet_500"),
            InlineKeyboardButton(text="1000 🪙", callback_data="slots_free_bet_1000"),
        ],
        [
            InlineKeyboardButton(text="5000 🪙", callback_data="slots_free_bet_5000"),
            InlineKeyboardButton(text="10000 🪙", callback_data="slots_free_bet_10000"),
            InlineKeyboardButton(text="20000 🪙", callback_data="slots_free_bet_20000"),
        ],
        [
            InlineKeyboardButton(text="50000 🪙", callback_data="slots_free_bet_50000"),
            InlineKeyboardButton(text="100000 🪙", callback_data="slots_free_bet_100000"),
        ],
        [
            InlineKeyboardButton(text="200000 🪙", callback_data="slots_free_bet_200000"),
            InlineKeyboardButton(text="500000 🪙", callback_data="slots_free_bet_500000"),
        ],
        [InlineKeyboardButton(text="1 000 000 🪙", callback_data="slots_free_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="slots_free_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="slots_free_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="slots_free_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="slots_free_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("slots_free_bet_"))
async def slots_free_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение слотов с бесплатными вращениями"""
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно!", show_alert=True)
        return
    
    reel1 = spin_slot()
    reel2 = spin_slot()
    reel3 = spin_slot()
    result_symbols = [reel1[1], reel2[1], reel3[1]]
    
    s1, s2, s3 = result_symbols
    free_spins = 0
    
    if s1 == s2 == s3:
        free_spins = random.randint(5, 10)
    elif (s1 == s2 or s2 == s3 or s1 == s3):
        free_spins = random.randint(3, 5)
    
    reel_display = f"""
{reel1[0]} {reel2[0]} {reel3[0]}
**{reel1[1]} {reel2[1]} {reel3[1]}** ← РЕЗУЛЬТАТ
{reel1[2]} {reel2[2]} {reel3[2]}
"""
    
    base_winnings, first_description = check_win(result_symbols, bet)
    
    total_winnings = base_winnings
    free_info = ""
    
    if free_spins > 0:
        free_info = f"\n\n🎁 **{free_spins} БЕСПЛАТНЫХ ВРАЩЕНИЙ!** 🎁"
        
        for i in range(free_spins):
            free_reel1 = spin_slot()
            free_reel2 = spin_slot()
            free_reel3 = spin_slot()
            free_symbols = [free_reel1[1], free_reel2[1], free_reel3[1]]
            
            free_win, _ = check_win(free_symbols, bet)
            total_winnings += free_win * 2
        
        free_info += f"\n📊 Сумма всех выигрышей с 2x мультипликатором"
    
    if total_winnings > 0:
        user['shekels'] += total_winnings - bet
        user['total_won'] += total_winnings
        status = "✅ ВЫИГРЫШ!"
        final_amount = total_winnings
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        status = "❌ БЕЗ ВЫИГРЫША"
        final_amount = -bet
        free_info = ""
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    text = f"""
🎁 **СЛОТЫ "БЕСПЛАТНЫЕ ВРАЩЕНИЯ"** 🎁

{reel_display}

**{first_description}**

{free_info}

**Ставка:** {format_currency(bet)}
**{status}**
**{'+' if final_amount > 0 else ''}{final_amount}** 🪙

**Баланс:** {format_currency(user['shekels'])}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎁 Ещё раз", callback_data="game_slots_free"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer() 

# =============== РУЛЕТКА (личная) ===============
@dp.callback_query(lambda c: c.data == "game_roulette")
async def roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню рулетки"""
    await state.set_state(GameStates.roulette_betting)

    text = """
🎡 **РУЛЕТКА** 🎡

**Правила:**
- Выберите ставку (от 10 до 500 Шекелей)
- Угадайте: Красное или Чёрное
- Вероятность выигрыша: 48.6%
- При выигрыше удвоите ставку

Сколько ставите?
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="roulette_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="roulette_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="roulette_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="roulette_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="roulette_bet_500"),
                InlineKeyboardButton(text="1000 🪙", callback_data="roulette_bet_1000"),
            ],
            [
                InlineKeyboardButton(text="5000 🪙", callback_data="roulette_bet_5000"),
                InlineKeyboardButton(text="10000 🪙", callback_data="roulette_bet_10000"),
                InlineKeyboardButton(text="20000 🪙", callback_data="roulette_bet_20000"),
            ],
            [
    InlineKeyboardButton(text="50000 🪙", callback_data="roulette_bet_50000"),
    InlineKeyboardButton(text="100000 🪙", callback_data="roulette_bet_100000"),
],
[
    InlineKeyboardButton(text="200000 🪙", callback_data="roulette_bet_200000"),
    InlineKeyboardButton(text="500000 🪙", callback_data="roulette_bet_500000"),
],
[ InlineKeyboardButton(text="1 000 000 🪙", callback_data="roulette_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="roulette_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="roulette_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="roulette_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="roulette_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("roulette_bet_"))
async def roulette_choose_color(callback: types.CallbackQuery, state: FSMContext):
    """Выбор цвета в рулетке"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['shekels'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    await state.update_data(roulette_bet=bet)
    
    text = f"""
🎡 **ВЫБЕРИТЕ ЦВЕТ** 🎡

Ставка: {format_currency(bet)}

Выберите:
🔴 **Красное** - удвоите ставку
⬛ **Чёрное** - удвоите ставку
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Красное", callback_data="roulette_red"),
            InlineKeyboardButton(text="⬛ Чёрное", callback_data="roulette_black")
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    
@dp.callback_query(lambda c: c.data in ["roulette_red", "roulette_black"])
async def roulette_spin(callback: types.CallbackQuery, state: FSMContext):
    """Вращение рулетки"""
    data = await state.get_data()
    bet = data.get('roulette_bet', 10)
    chosen_color = "Красное" if callback.data == "roulette_red" else "Чёрное"
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    is_win = result_color == chosen_color
    
    if is_win:
        user['shekels'] += bet
        user['total_won'] += bet
        result_text = f"""
🎉 **ВЫИГРЫШ!** 🎉

Результат рулетки: **{result_color}** ✅
Ваш выбор: **{chosen_color}** ✅
Выигрыш: **+{bet}** 🪙

Новый баланс: {format_currency(user['shekels'])}
        """
    else:
        user['shekels'] -= bet
        user['total_lost'] += bet
        result_text = f"""
😢 **ПРОИГРЫШ** 😢

Результат рулетки: **{result_color}** ❌
Ваш выбор: **{chosen_color}** ❌
Потеря: **-{bet}** 🪙

Новый баланс: {format_currency(user['shekels'])}
        """
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎡 Ещё раз", callback_data="game_roulette"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    
# =============== BLACK JACK (личная) ===============
def calculate_hand(cards: List[str]) -> tuple:
    """Рассчитать значение руки"""
    total = 0
    aces = 0
    for card in cards:
        if card == 'A':
            aces += 1
            total += 11
        elif card in ['J', 'Q', 'K']:
            total += 10
        else:
            total += int(card)
    
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total, aces

def is_blackjack(cards: List[str]) -> bool:
    """Проверить, есть ли Black Jack (21 с двумя картами)"""
    if len(cards) != 2:
        return False
    value, _ = calculate_hand(cards)
    return value == 21

def get_deck() -> List[str]:
    """Создать колоду карт"""
    deck = []
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    for _ in range(4):
        deck.extend(cards)
    random.shuffle(deck)
    return deck

@dp.callback_query(lambda c: c.data == "game_blackjack")
async def blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню Black Jack"""
    await state.set_state(GameStates.blackjack_betting)

    text = """
♠️ **BLACK JACK** ♠️

**Правила:**
- Цель: набрать 21 очко или близко к нему
- Дилер играет против вас
- Если перебрали (>21) - ПЕРЕБОР, игра заканчивается
- **BLACK JACK!** (21 с первых двух карт) = **5x выигрыш от ставки!** 🎉
- При обычном выигрыше - получаете 2x от ставки

Сколько ставите?
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="bj_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="bj_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="bj_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="bj_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="bj_bet_500"),
                InlineKeyboardButton(text="1000 🪙", callback_data="bj_bet_1000"),
            ],
            [
                InlineKeyboardButton(text="5000 🪙", callback_data="bj_bet_5000"),
                InlineKeyboardButton(text="10000 🪙", callback_data="bj_bet_10000"),
                InlineKeyboardButton(text="20000 🪙", callback_data="bj_bet_20000"),
            ],
            
            [
    InlineKeyboardButton(text="10 🪙", callback_data="bj_bet_10"),
    InlineKeyboardButton(text="50 🪙", callback_data="bj_bet_50"),
    InlineKeyboardButton(text="100 🪙", callback_data="bj_bet_100"),
],
[
    InlineKeyboardButton(text="250 🪙", callback_data="bj_bet_250"),
    InlineKeyboardButton(text="500 🪙", callback_data="bj_bet_500"),
    InlineKeyboardButton(text="1000 🪙", callback_data="bj_bet_1000"),
],
[
    InlineKeyboardButton(text="5000 🪙", callback_data="bj_bet_5000"),
    InlineKeyboardButton(text="10000 🪙", callback_data="bj_bet_10000"),
    InlineKeyboardButton(text="20000 🪙", callback_data="bj_bet_20000"),
],
[
    InlineKeyboardButton(text="50000 🪙", callback_data="bj_bet_50000"),
    InlineKeyboardButton(text="100000 🪙", callback_data="bj_bet_100000"),
],
[
    InlineKeyboardButton(text="200000 🪙", callback_data="bj_bet_200000"),
    InlineKeyboardButton(text="500000 🪙", callback_data="bj_bet_500000"),
],
[InlineKeyboardButton(text="1 000 000 🪙", callback_data="bj_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="bj_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="bj_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="bj_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="bj_bet_all"),
    ],
[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("bj_bet_"))
async def blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало игры Black Jack"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['shekels'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    deck = get_deck()
    player_cards = [deck.pop(), deck.pop()]
    dealer_cards = [deck.pop(), deck.pop()]
    
    player_value, _ = calculate_hand(player_cards)
    dealer_value, _ = calculate_hand(dealer_cards)
    
    # ✅ ИСПРАВЛЕННАЯ ПРОВЕРКА BLACK JACK
    if is_blackjack(player_cards):
        # Проверяем BLACK JACK у дилера
        if is_blackjack(dealer_cards):
            # Оба имеют BLACK JACK - ничья, возвращаем ставку
            user['shekels'] += bet
            user['total_won'] += bet
            winnings = bet
            result_text = f"""
🤝 **ОБА ИМЕЮТ BLACK JACK!** 🤝

**Ваши карты:** {' '.join(player_cards)} = **21** 🎯
**Карты дилера:** {' '.join(dealer_cards)} = **21** 🎯

Ставка возвращена: **+{bet}** 🪙
Новый баланс: {format_currency(user['shekels'])}
            """
        else:
            # Только игрок имеет BLACK JACK - выигрыш 5x
            winnings = bet * 5
            user['shekels'] += winnings
            user['total_won'] += winnings
            result_text = f"""
🌟 **BLACK JACK!!!** 🌟

**Ваши карты:** {' '.join(player_cards)} = **21** 🎯
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

✨ ВЫИГРЫШ В 5 РАЗ! ✨
Выигрыш: **+{winnings}** 🪙

Новый баланс: {format_currency(user['shekels'])}
            """
        
        user['games_played'] += 1
        save_user(user_id, user)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="♠️ Ещё партию", callback_data="game_blackjack"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
            ]
        ])
        
        await callback.message.edit_text(result_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        
        return
    
    # Нет BLACK JACK - игра продолжается
    await state.update_data(
        bj_bet=bet,
        bj_deck=deck,
        bj_player_cards=player_cards,
        bj_dealer_cards=dealer_cards,
        bj_player_id=user_id
    )
    await state.set_state(GameStates.blackjack_playing)
    
    text = f"""
♠️ **BLACK JACK - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?

**Ставка:** {format_currency(bet)}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
    

@dp.callback_query(lambda c: c.data == "bj_hit")
async def blackjack_hit(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("bj_player_id")
    if owner_id is not None and owner_id != callback.from_user.id:
        await callback.answer("❌ Это не ваша игра.", show_alert=True)
        return
    """Взять ещё карту"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    dealer_cards = data['bj_dealer_cards']
    bet = data['bj_bet']
    
    if not deck:
        deck = get_deck()
    
    player_cards.append(deck.pop())
    player_value, _ = calculate_hand(player_cards)
    
    # ПЕРЕБОР - игра заканчивается сразу
    if player_value > 21:
        user_id = callback.from_user.id
        user = get_user(user_id)
        user['shekels'] -= bet
        user['total_lost'] += bet
        user['games_played'] += 1
        save_user(user_id, user)
        
        text = f"""
💥 **ПЕРЕБОР!** 💥

**Ваши карты:** {' '.join(player_cards)}
**Сумма:** {player_value} ❌

Игра закончена! Вы перебрали.

Проигрыш: **-{bet}** 🪙
Новый баланс: {format_currency(user['shekels'])}
        """
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="♠️ Ещё партию", callback_data="game_blackjack"),
                InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
            ]
        ])
        
        await state.clear()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        
        return
    
    await state.update_data(bj_deck=deck, bj_player_cards=player_cards)
    
    text = f"""
♠️ **BLACK JACK - ИГРА** ♠️

**Ваши карты:** {' '.join(player_cards)}
Сумма: **{player_value}**

**Карта дилера:** {dealer_cards[0]} ?

**Ставка:** {format_currency(bet)}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎴 Ещё карту", callback_data="bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="bj_stand")
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "bj_stand")
async def blackjack_stand(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    owner_id = data.get("bj_player_id")
    if owner_id is not None and owner_id != callback.from_user.id:
        await callback.answer("❌ Это не ваша игра.", show_alert=True)
        return
    """Остановиться и завершить игру"""
    data = await state.get_data()
    deck = data['bj_deck']
    player_cards = data['bj_player_cards']
    dealer_cards = data['bj_dealer_cards']
    bet = data['bj_bet']
    
    # Дилер играет
    while True:
        dealer_value, _ = calculate_hand(dealer_cards)
        if dealer_value >= 17:
            break
        if not deck:
            deck = get_deck()
        dealer_cards.append(deck.pop())
    
    player_value, _ = calculate_hand(player_cards)
    dealer_value, _ = calculate_hand(dealer_cards)
    
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    # Проверяем BLACK JACK у дилера
    if is_blackjack(dealer_cards):
        # Дилер имеет BLACK JACK - просто забирает ставку
        user['shekels'] -= bet
        user['total_lost'] += bet
        result = f"""
🌟 **ДИЛЕР ИМЕЕТ BLACK JACK!** 🌟

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **21** 🎯

Дилер выигрывает! Ставка забрана.

Проигрыш: **-{bet}** 🪙
Новый баланс: {format_currency(user['shekels'])}
        """
    elif dealer_value > 21:
        # Дилер перебрал
        winnings = int(bet * 2)
        user['shekels'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** 💥

Дилер перебрал!
Выигрыш: **+{winnings}** 🪙
Новый баланс: {format_currency(user['shekels'])}
        """
    elif player_value > dealer_value:
        # Игрок выигрывает
        winnings = int(bet * 2)
        user['shekels'] += winnings
        user['total_won'] += winnings
        result = f"""
🎉 **ВЫИГРЫШ!** 🎉

**Ваши карты:** {' '.join(player_cards)} = **{player_value}** ✅
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Выигрыш: **+{winnings}** 🪙
Новый баланс: {format_currency(user['shekels'])}
        """
    elif player_value == dealer_value:
        # Ничья
        user['shekels'] += bet
        result = f"""
🤝 **НИЧЬЯ** 🤝

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

Ставка возвращена: **+{bet}** 🪙
Баланс: {format_currency(user['shekels'])}
        """
    else:
        # Проигрыш
        user['shekels'] -= bet
        user['total_lost'] += bet
        result = f"""
😢 **ПРОИГРЫШ** 😢

**Ваши карты:** {' '.join(player_cards)} = **{player_value}**
**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}** ✅

Проигрыш: **-{bet}** 🪙
Новый баланс: {format_currency(user['shekels'])}
        """
    
    user['games_played'] += 1
    save_user(user_id, user)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="♠️ Ещё партию", callback_data="game_blackjack"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="back_to_menu")
        ]
    ])
    
    await state.clear()
    await callback.message.edit_text(result, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

# =============== ГРУППОВАЯ РУЛЕТКА ===============
@dp.callback_query(lambda c: c.data == "group_roulette_menu")
async def group_roulette_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню групповой рулетки"""
    text = """
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

**Как это работает:**
- Любой может присоединиться к игре
- Все ставят одновременно
- Один результат рулетки для всех
- У каждого свой баланс и счет

Выберите ставку:
"""

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="group_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="group_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="group_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="group_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="group_bet_500"),
                InlineKeyboardButton(text="1000 🪙", callback_data="group_bet_1000"),
            ],
            [
                InlineKeyboardButton(text="5000 🪙", callback_data="group_bet_5000"),
                InlineKeyboardButton(text="10000 🪙", callback_data="group_bet_10000"),
                InlineKeyboardButton(text="20000 🪙", callback_data="group_bet_20000"),
            ],
            [
    InlineKeyboardButton(text="50000 🪙", callback_data="group_bet_50000"),
    InlineKeyboardButton(text="100000 🪙", callback_data="group_bet_100000"),
],
[
    InlineKeyboardButton(text="200000 🪙", callback_data="group_bet_200000"),
    InlineKeyboardButton(text="500000 🪙", callback_data="group_bet_500000"),
],
[InlineKeyboardButton(text="1 000 000 🪙", callback_data="group_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="group_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="group_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="group_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="group_bet_all"),
    ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
            ],
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("group_bet_"))
async def group_roulette_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало групповой рулетки"""
    bet = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    player_name = get_user_name(callback.from_user)
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['shekels'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    chat_id = callback.message.chat.id
    
    if chat_id not in group_roulette_games:
        group_roulette_games[chat_id] = {
            'players': {},
            'bet': bet,
            'message_id': callback.message.message_id
        }
    
    game = group_roulette_games[chat_id]
    game['players'][user_id] = {
        'name': player_name,
        'bet': bet,
        'color': None
    }
    
    players_text = "\n".join([f"👤 {p['name']} - {format_currency(p['bet'])}" 
                              for p in game['players'].values()])
    
    text = f"""
🎡 **ГРУППОВАЯ РУЛЕТКА** 🎡

**Ставка:** {format_currency(bet)}
**Игроков:** {len(game['players'])}

**Участники:**
{players_text}

Выберите цвет:
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔴 Красное", callback_data="group_color_red"),
            InlineKeyboardButton(text="⬛ Чёрное", callback_data="group_color_black"),
        ],
        [
            InlineKeyboardButton(text="🎡 Запустить рулетку!", callback_data="group_roulette_spin"),
        ],
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Вы присоединились к игре!")

@dp.callback_query(lambda c: c.data.startswith("group_color_"))
async def group_roulette_color(callback: types.CallbackQuery):
    color = callback.data.split("_")[2]   # red / black
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in group_roulette_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_roulette_games[chat_id]

    if user_id not in game['players']:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    color_name = "Красное" if color == "red" else "Чёрное"
    game['players'][user_id]['color'] = color

    await callback.answer(f"✅ Вы выбрали: {color_name}")

@dp.callback_query(lambda c: c.data == "group_roulette_spin")
async def group_roulette_spin(callback: types.CallbackQuery):
    """Вращение групповой рулетки"""
    chat_id = callback.message.chat.id
    
    if chat_id not in group_roulette_games:
        await callback.answer("❌ Нет активной игры", show_alert=True)
        return
    
    game = group_roulette_games[chat_id]
    
    players_without_color = [p for p in game['players'].values() if p['color'] is None]
    if players_without_color:
        await callback.answer(f"❌ Не все выбрали цвет! {len(players_without_color)} игроков ждут...", show_alert=True)
        return
    
    result_color = random.choices(["Красное", "Чёрное"], weights=[48.6, 51.4])[0]
    
    results = []
    for user_id, player in game['players'].items():
        user = get_user(user_id)
        player_color = "Красное" if player['color'] == "red" else "Чёрное"
        is_win = result_color == player_color
        
        if is_win:
            user['shekels'] += player['bet']
            user['total_won'] += player['bet']
            results.append(f"✅ {player['name']} выиграл {format_currency(player['bet'])}")
        else:
            user['shekels'] -= player['bet']
            user['total_lost'] += player['bet']
            results.append(f"❌ {player['name']} проиграл {format_currency(player['bet'])}")
        
        user['games_played'] += 1
        save_user(user_id, user)
    
    results_text = "\n".join(results)
    
    text = f"""
🎰 **РЕЗУЛЬТАТ РУЛЕТКИ** 🎰

**Выпало:** {result_color}

**Результаты:**
{results_text}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎡 Новая игра", callback_data="group_roulette_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    if chat_id in group_roulette_games:
        del group_roulette_games[chat_id]
    
    await callback.answer("🎉 Игра завершена!")

# =============== ГРУППОВОЙ BLACK JACK ===============
def calculate_hand(cards: List[str]) -> tuple:
    """Рассчитать значение руки"""
    total = 0
    aces = 0
    for card in cards:
        if card == 'A':
            aces += 1
            total += 11
        elif card in ['J', 'Q', 'K']:
            total += 10
        else:
            total += int(card)
    
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total, aces

def is_blackjack(cards: List[str]) -> bool:
    """Проверить, есть ли Black Jack (21 с двумя картами)"""
    if len(cards) != 2:
        return False
    value, _ = calculate_hand(cards)
    return value == 21

def get_deck() -> List[str]:
    """Создать колоду карт"""
    deck = []
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    for _ in range(4):
        deck.extend(cards)
    random.shuffle(deck)
    return deck

@dp.callback_query(lambda c: c.data == "group_blackjack_menu")
async def group_blackjack_menu(callback: types.CallbackQuery, state: FSMContext):
    """Меню группового Black Jack"""
    text = """
♠️ **ГРУППОВОЙ BLACK JACK** ♠️
  !!!ПРОЕКТ ГРУППОВОГО БЛЕК ДЖЕКА В БЕТА ТЕСТЕ, РАБОТАЕТ НЕ СТАБИЛЬНО!!!!
**Как это работает:**
- Все игроки играют против одного дилера
- Каждый ставит свою сумму
- У каждого свои карты и решения
- Один результат дилера для всех
- **BLACK JACK** (21 с первых двух карт) = **5x выигрыш**!
- **ПЕРЕБОР** - игра заканчивается сразу

Выберите ставку:
"""

    keyboard = InlineKeyboardMarkup( inline_keyboard=[
            [
                InlineKeyboardButton(text="10 🪙", callback_data="group_bj_bet_10"),
                InlineKeyboardButton(text="50 🪙", callback_data="group_bj_bet_50"),
                InlineKeyboardButton(text="100 🪙", callback_data="group_bj_bet_100"),
            ],
            [
                InlineKeyboardButton(text="250 🪙", callback_data="group_bj_bet_250"),
                InlineKeyboardButton(text="500 🪙", callback_data="group_bj_bet_500"),
            ],
            [
                InlineKeyboardButton(text="1000 🪙", callback_data="group_bj_bet_1000"),
                InlineKeyboardButton(text="5000 🪙", callback_data="group_bj_bet_5000"),
            ],
            [
                InlineKeyboardButton(text="10000 🪙", callback_data="group_bj_bet_10000"),
                InlineKeyboardButton(text="20000 🪙", callback_data="group_bj_bet_20000"),
            ],
            [
    InlineKeyboardButton(text="50000 🪙", callback_data="group_bj_bet_50000"),
    InlineKeyboardButton(text="100000 🪙", callback_data="group_bj_bet_100000"),
],
[
    InlineKeyboardButton(text="200000 🪙", callback_data="group_bj_bet_200000"),
    InlineKeyboardButton(text="500000 🪙", callback_data="group_bj_bet_500000"),
],
[InlineKeyboardButton(text="1 000 000 🪙", callback_data="group_bj_bet_1000000"),
        InlineKeyboardButton(text="2 000 000 🪙", callback_data="group_bj_bet_2000000"),
    ],
    [
        InlineKeyboardButton(text="5 000 000 🪙", callback_data="group_bj_bet_5000000"),
        InlineKeyboardButton(text="10 000 000 🪙", callback_data="group_bj_bet_10000000"),
        InlineKeyboardButton(text="ВСЁ ИМУЩЕСТВО 🪙", callback_data="group_bj_bet_all"),
    ],
[
    InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu"),
]

        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("group_bj_bet_"))
async def group_blackjack_start(callback: types.CallbackQuery, state: FSMContext):
    """Присоединение к групповой игре Black Jack"""
    bet = int(callback.data.split("_")[3])
    user_id = callback.from_user.id
    player_name = get_user_name(callback.from_user)
    user = get_user(user_id)
    
    if user['shekels'] < bet:
        await callback.answer(f"❌ Недостаточно! У вас {format_currency(user['shekels'])}, нужно {format_currency(bet)}", show_alert=True)
        return
    
    chat_id = callback.message.chat.id
    
    if chat_id not in group_blackjack_games:
        deck = get_deck()
        group_blackjack_games[chat_id] = {
            'players': {},
            'dealer_cards': [deck.pop(), deck.pop()],
            'deck': deck,
            'status': 'betting',
            'message_id': callback.message.message_id
        }
    
    game = group_blackjack_games[chat_id]
    deck = game['deck']
    
    game['players'][user_id] = {
        'name': player_name,
        'bet': bet,
        'cards': [deck.pop(), deck.pop()],
        'status': 'playing',
        'finished': False
    }
    
    players_display = []
    for uid, player in game['players'].items():
        value, _ = calculate_hand(player['cards'])
        cards_str = ' '.join(player['cards'])
        players_display.append(f"👤 {player['name']}: {cards_str} = **{value}**")
    
    players_text = "\n".join(players_display)
    
    text = f"""
♠️ **ГРУППОВОЙ BLACK JACK** ♠️

**Карта дилера:** {game['dealer_cards'][0]} ?

**Игроки ({len(game['players'])}):**
{players_text}

Делайте ходы:
    """
    
    keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
         [
            InlineKeyboardButton(text="🎴 Ещё карту", callback_data="group_bj_hit"),
            InlineKeyboardButton(text="⏹️ Стоп", callback_data="group_bj_stand"),
        ],
        [InlineKeyboardButton(text="✅ Начать игру дилера", callback_data="group_bj_dealer")],
    
    ],
)

    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer("✅ Вы присоединились!")
    
@dp.callback_query(lambda c: c.data == "group_bj_hit")
async def group_blackjack_hit(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_blackjack_games[chat_id]

    if user_id not in game['players']:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    player = game['players'][user_id]

    if player['finished']:
        await callback.answer("❌ Ваша игра уже завершена", show_alert=True)
        return

    deck = game['deck']
    if not deck:
        deck = get_deck()
        game['deck'] = deck

    player['cards'].append(deck.pop())
    value, _ = calculate_hand(player['cards'])

    if value > 21:
        player['status'] = 'bust'
        player['finished'] = True
        await callback.answer(f"💥 ПЕРЕБОР! {value} очков - ваша игра закончена", show_alert=True)
    else:
        await callback.answer(f"🎴 Вы взяли карту. Сумма: {value}")

@dp.callback_query(lambda c: c.data == "group_bj_stand")
async def group_blackjack_stand(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Игра не начиналась", show_alert=True)
        return

    game = group_blackjack_games[chat_id]

    if user_id not in game['players']:
        await callback.answer("❌ Вы не в этой игре", show_alert=True)
        return

    player = game['players'][user_id]
    if player['finished']:
        await callback.answer("❌ Ваша игра уже завершена", show_alert=True)
        return

    value, _ = calculate_hand(player['cards'])
    player['status'] = 'stand'
    player['finished'] = True
    await callback.answer(f"⏹️ Вы остановились с {value} очками")

@dp.callback_query(lambda c: c.data == "group_bj_dealer")
async def group_blackjack_dealer(callback: types.CallbackQuery):
    """Игра дилера и результаты"""
    chat_id = callback.message.chat.id
    
    if chat_id not in group_blackjack_games:
        await callback.answer("❌ Нет активной игры", show_alert=True)
        return
    
    game = group_blackjack_games[chat_id]
    deck = game['deck']
    dealer_cards = game['dealer_cards']
    
    while True:
        dealer_value, _ = calculate_hand(dealer_cards)
        if dealer_value >= 17:
            break
        if not deck:
            deck = get_deck()
            game['deck'] = deck
        dealer_cards.append(deck.pop())
    
    dealer_value, _ = calculate_hand(dealer_cards)
    dealer_has_blackjack = is_blackjack(dealer_cards)
    
    results = []
    for user_id, player in game['players'].items():
        user = get_user(user_id)
        player_value, _ = calculate_hand(player['cards'])
        player_has_blackjack = is_blackjack(player['cards'])
        
        if player['status'] == 'bust':
            user['shekels'] -= player['bet']
            user['total_lost'] += player['bet']
            results.append(f"💥 {player['name']} - ПЕРЕБОР ({player_value})")
        elif player_has_blackjack and dealer_has_blackjack:
            user['shekels'] += player['bet']
            results.append(f"🤝 {player['name']} - BLACK JACK НИЧЬЯ!")
        elif player_has_blackjack:
            winnings = player['bet'] * 5
            user['shekels'] += winnings
            user['total_won'] += winnings
            results.append(f"🌟 {player['name']} - BLACK JACK! +{winnings}!")
        elif dealer_has_blackjack:
            user['shekels'] -= player['bet']
            user['total_lost'] += player['bet']
            results.append(f"🌟 {player['name']} - Дилер BLACK JACK, -{player['bet']}")
        elif dealer_value > 21:
            user['shekels'] += int(player['bet'] * 2)
            user['total_won'] += int(player['bet'] * 2)
            results.append(f"✅ {player['name']} - ВЫИГРЫШ! Дилер перебрал")
        elif player_value > dealer_value:
            user['shekels'] += int(player['bet'] * 2)
            user['total_won'] += int(player['bet'] * 2)
            results.append(f"✅ {player['name']} - ВЫИГРЫШ! ({player_value} vs {dealer_value})")
        elif player_value == dealer_value:
            user['shekels'] += player['bet']
            results.append(f"🤝 {player['name']} - НИЧЬЯ ({player_value})")   
        else:
            user['shekels'] -= player['bet']
            user['total_lost'] += player['bet']
            results.append(f"❌ {player['name']} - ПРОИГРЫШ ({player_value} vs {dealer_value})")
        
        user['games_played'] += 1
        users_data[str(user_id)] = user
    
    results_text = "\n".join(results)
    save_users_data()
    
    text = f"""
🎰 **РЕЗУЛЬТАТЫ BLACK JACK** 🎰

**Карты дилера:** {' '.join(dealer_cards)} = **{dealer_value}**

**Результаты:**
{results_text}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="♠️ Новая игра", callback_data="group_blackjack_menu")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    if chat_id in group_blackjack_games:
        del group_blackjack_games[chat_id]
    
    await callback.answer("🎉 Игра завершена!")
# =============== СТАТИСТИКА ===============
@dp.callback_query(lambda c: c.data == "stats")
async def show_stats(callback: types.CallbackQuery):
    """Показать статистику"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    profit = user['total_won'] - user['total_lost']
    profit_emoji = "📈" if profit >= 0 else "📉"
    profit_word = declension(abs(profit), "Шекель", "Шекеля", "Шекелей")
    
    text = f"""
📊 **ВАША СТАТИСТИКА** 📊

**Баланс:** {format_currency(user['shekels'])}

**Всего игр:** {user['games_played']}
**Выигрыш:** +{user['total_won']} 🪙
**Проигрыш:** -{user['total_lost']} 🪙
**Прибыль/Убыток:** {profit_emoji} {profit:+d} {profit_word}
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    """Показать баланс"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    text = f"""
💰 **ВАШ БАЛАНС** 💰

{format_currency(user['shekels'])}

Начинайте игру и выигрывайте! 🎰
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
# =============== НАВИГАЦИЯ ===============
@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    """Вернуться в главное меню"""
    user_id = callback.from_user.id
    user = get_user(user_id)
    player_name = get_user_name(callback.from_user)

    await state.set_state(GameStates.main_menu)

    welcome_text = create_main_menu(user, player_name)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎡 Рулетка", callback_data="game_roulette"),
                InlineKeyboardButton(text="♠️ Black Jack", callback_data="game_blackjack"),
            ],
            [
                InlineKeyboardButton(text="🎡 Рулетка в группе", callback_data="group_roulette_menu"),
                InlineKeyboardButton(text="♠️ Black Jack в группе", callback_data="group_blackjack_menu"),
            ],
            [
            InlineKeyboardButton(text="🎰 СЛОТЫ(НОВОЕ!)", callback_data="slots_menu"),
        ],
            [
                InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
                InlineKeyboardButton(text="💰 Баланс", callback_data="balance"),
            ],
            [
            InlineKeyboardButton(text="💸 Перевод шекелей", callback_data="transfer_menu"),
        ],
            
        ]
    )

    await callback.message.edit_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()
# =============== ЗАПУСК БОТА ===============
async def main():
    """Запуск бота"""
    print("🎰 Казино Щедрый Еврей запущено! (Версия 3.1 - ИСПРАВЛЕННЫЙ BLACK JACK 21 + ГРУППОВЫЕ ИГРЫ)")
    load_users_data()
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
