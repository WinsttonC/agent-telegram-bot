import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters.command import Command
from aiogram.fsm.storage.memory import MemoryStorage 
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup

from dotenv import load_dotenv

from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker

from database_module import Tools, UserInformation, MainInfo
from model import *

load_dotenv()
TOKEN = os.getenv('TGTOKEN')
storage = MemoryStorage()
router = Router()

class FSMAdmin(StatesGroup):
    open_ai = State()
    admin_start = State()
    user_start = State()
    add_inf = State()
    add_doc = State()
    added_doc = State()
    add_tool = State()
    model_choose = State()
    f_search = State()
    g_search = State()
    poll = State()
    start = State()
    auth = State()
    setup = State()
    add_admin = State()
    add_user = State()

async def main():
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    bot = Bot(TOKEN)
    await dp.start_polling(bot)

@router.message(FSMAdmin.start)
async def start(message: types.Message):
    await message.answer("На этом момент бот умер, но мы с этим обязательно что нибудь сделаем")

def check_info_user_from_db(username):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    user_info = db.query(UserInformation).filter_by(username=username).first()
    db.close()
    return user_info

def get_info_user_from_db(username):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    user_info = db.query(UserInformation).filter_by(username=username, is_root=False).first()
    db.close()
    return user_info

def get_info_admin_from_db(username):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    user_info = db.query(UserInformation).filter_by(username=username, is_root=True).first()
    db.close()
    return user_info

def update_open_ai_key(open_ai_key):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    main_info = db.query(MainInfo).filter_by(id=1).first()

    if main_info:
        db.execute(update(MainInfo).where(MainInfo.id == 1).values(open_ai_key=open_ai_key))
    else:
        value_open_ai = MainInfo(id=1, open_ai_key=open_ai_key)
        db.add(value_open_ai)

    db.commit()
    db.close()

    return main_info

def add_user_to_db(username):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    user_info = UserInformation(username=username, is_root=False) 
    new_tools_info = Tools(username=username, doc_retriever=True, docs_template=False, google_calendar=False)
    db.add(user_info)
    db.add(new_tools_info)
    db.commit()
    db.close()    

def update_user_root_status(username, status=True):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    db.execute(update(UserInformation).where(UserInformation.username == username).values(is_root=status))
    db.commit()
    db.close() 

def update_model_type(model):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    main_info = db.query(MainInfo).filter_by(id=1).first()

    if main_info:
        db.execute(update(MainInfo).where(MainInfo.id == 1).values(model=model))
    else:
        model_open_ai = MainInfo(id=1, model=model)
        db.add(model_open_ai)

    db.commit()
    db.close()

    return main_info
    
username = ''
@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    global username
    username = message.from_user.username
    
    if not check_info_user_from_db(username): # если юзера нет в нашей таблице UserInformation, отказываем в доступе 
        await message.answer('У вас нет доступа к этому боту. Пожалуйста, обратитесь к администратору.')
    
    if get_info_user_from_db(username): # получить информацию о пользователях без root-доступа
        await state.set_state(FSMAdmin.user_start)
        await message.answer('Вы вошли как пользователь. Для выхода напишите /stop')
    
    if get_info_admin_from_db(username): # получить информацию о админах с root-доступом
        await state.set_state(FSMAdmin.user_start)
        await message.answer('Вы авторизованы как администратор. Для настройки нажмите /setup')

kb_remove = types.ReplyKeyboardRemove()
@router.message(Command('setup'))
async def cmd_start(message: types.Message):
    username = message.from_user.username
    if not get_info_admin_from_db(username):
        await message.answer('У вас нет доступа к настройке.')
    else:
        kb = [
            [   
                types.KeyboardButton(text="Open AI Key"),
                types.KeyboardButton(text="Выбрать модель")
            ],
            [   
                types.KeyboardButton(text="Добавить пользователя"),
                types.KeyboardButton(text="Добавить администратора")
            ],

            [types.KeyboardButton(text="Добавить информацию")],
            [types.KeyboardButton(text="Добавить документ")],
            [types.KeyboardButton(text="Добавить инструмент")],
        ]
        keyboard = types.ReplyKeyboardMarkup(
            keyboard=kb,
            resize_keyboard=True,
            input_field_placeholder="Выберите один из вариантов",
            one_time_keyboard=True
        )
        
        await message.answer("Выберите один из вариантов ниже:", reply_markup=keyboard)

@router.message(lambda message: message.text == "Open AI")
async def review_state12(message: types.Message, state: FSMContext):
    await state.set_state(FSMAdmin.open_ai)
    await message.answer('Введите ваш ключ', reply_markup=kb_remove)
    
@router.message(FSMAdmin.open_ai)
async def update_key(message: types.Message, state: FSMContext):
    open_ai_key = message.text
    update_open_ai_key(open_ai_key)
    await message.answer('Ключ обновлен', reply_markup=kb_remove)
    await state.set_state(FSMAdmin.setup)
    
@router.message(lambda message: message.text == "Добавить пользователя")
async def add_user(message: types.Message, state: FSMContext):
    await state.set_state(FSMAdmin.add_user)
    await message.answer(f'Введите username без "@"', reply_markup=kb_remove)

@router.message(FSMAdmin.add_user)
async def add_user(message: types.Message, state: FSMContext):
    
    if '@' not in message.text:
        username = message.text
    if 'https' in message.text:
        username = message.text.replace("https://t.me/", "")
    else:
        username = message.text.split('@')[0]
    if check_info_user_from_db(username):
        await message.answer(f'Пользователь {username} уже добавлен')
    if not check_info_user_from_db(username):
        add_user_to_db(username)
        await message.answer(f'Пользователь {username} добавлен', reply_markup=kb_remove)
    await state.set_state(FSMAdmin.setup)

@router.message(lambda message: message.text == "Добавить администратора")
async def add_user(message: types.Message, state: FSMContext):
    await state.set_state(FSMAdmin.add_admin)
    await message.answer(f'Введите username без "@"', reply_markup=kb_remove)
    
    
@router.message(FSMAdmin.add_admin)
async def add_user(message: types.Message, state: FSMContext):
    
    if '@' not in message.text:
        username = message.text
    if 'https' in message.text:
        username = message.text.replace("https://t.me/", "")       
    else:
        username = message.text.split('@')[0]
    
    if get_info_admin_from_db(username): # проверяем, есть ли статус root у пользователя 
        await message.answer(f'Администратор {username} уже добавлен')
    if not get_info_admin_from_db(username):
        update_user_root_status(username, True)
        await message.answer(f'Администратор {username} добавлен', reply_markup=kb_remove)
    await state.set_state(FSMAdmin.setup)


@router.message(lambda message: message.text == "Выбрать модель")
async def review_state1(message: types.Message, state: FSMContext):
    kb = [
        [
            types.KeyboardButton(text="GPT4-16k"),
            types.KeyboardButton(text="GPT4-32k"),
        ],    
        [    
            types.KeyboardButton(text="GPT3.5 Turbo 4k"),
            types.KeyboardButton(text="GPT3.5 Turbo 16k"),
        ],
    ]
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
    )
    
    await message.answer("Выберите один из вариантов ниже:", reply_markup=keyboard)
    await state.set_state(FSMAdmin.model_choose)

@router.message(FSMAdmin.model_choose)
async def model_choose(message: types.Message, state: FSMContext):
    if message.text == "GPT4-16k":
        update_model_type('GPT4-16k')
        await message.answer('GPT4-16k выбран')
    if message.text == "GPT4-32k":
        update_model_type('GPT4-32k')
        await message.answer('GPT4-32k выбран')
    if message.text == "GPT3.5 Turbo 4k":
        update_model_type('GPT3.5 Turbo 4k')
        await message.answer('GPT3.5 Turbo 4k выбран')
    if message.text == "GPT3.5 Turbo 16k":
        update_model_type('GPT3.5 Turbo 16k')
        await message.answer('GPT3.5 Turbo 16k выбран')
    await state.set_state(FSMAdmin.setup)  


@router.message(lambda message: message.text == "Добавить информацию")
async def review_state(message: types.Message, state: FSMContext):
    await state.set_state(FSMAdmin.add_inf)
    await message.answer('Напишитие, что нужно добавить или прикрепите документ', reply_markup=kb_remove)

@router.message(lambda message: message.text == "Добавить документ")
async def review_state2(message: types.Message, state: FSMContext):
    await state.set_state(FSMAdmin.add_doc)
    await message.answer('Прикрепите документ', reply_markup=kb_remove)
    
@router.message(FSMAdmin.add_doc)
async def document_handler(message: types.Message, state: FSMContext, bot):
    doc = message.document
    
    if doc.mime_type == 'application/msword' or doc.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        file_id = doc.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, 'docs_templates/'+doc.file_name)
        await message.reply("Документ сохранен")
        await message.answer("Добавьте название")
        await state.set_state(FSMAdmin.added_doc)
    else:
        await message.answer("Формат файла не поддерживается. Прикрепите, пожалуйста, документ в формате .doc или .docx")
        await state.set_state(FSMAdmin.add_doc)
   
@router.message(FSMAdmin.added_doc)
async def s_state(message: types.Message, state: FSMContext):
    await message.answer('Название сохранено')    

@router.message(FSMAdmin.add_inf)
async def document_handler(message: types.Message, state: FSMContext, bot):
    doc = message.document
    print(message.document, message.text)
    if doc is not None:
        if (doc.mime_type == 'application/msword' 
            or doc.mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            or doc.mime_type == 'text/markdown'
            or doc.mime_type == 'text/plain'
            or doc.mime_type == 'application/pdf'):
            
            file_id = doc.file_id
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, 'doc_retriever/'+doc.file_name)
            await message.answer("Информация добавлена")
            await state.set_state(FSMAdmin.start)
        else:
            await message.answer("Формат файла не поддерживается. Прикрепите, пожалуйста, документ в формате .doc/.docx/.md/.pdf")
            await state.set_state(FSMAdmin.add_inf)
    else:
        text_to_add = message.text
        with open('doc_retriever/general.txt', 'w', encoding='utf-8') as file:
            file.write(text_to_add)
        
        await message.answer("Информация добавлена")
        await state.set_state(FSMAdmin.start)

def update_user_tools(username, tool, value=True):
    db_url = "sqlite:///main_database.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    tools_info = db.query(Tools).filter_by(username=username).first()

    if tools_info:
        update_values = {tool: value}
        db.execute(update(Tools).where(Tools.username == username).values(**update_values))
    else:
        new_tools_info = Tools(username=username, **{tool: value})
        db.add(new_tools_info)

    db.commit()
    db.close()
    
poll_var = ['docs_template', 'google_calendar', 'doc_retriever']
@router.message(lambda message: message.text == "Добавить инструмент")
async def poll_handler(message: types.Message, state: FSMContext, bot, poll_var=poll_var):
    q = 'Какие варианты вам интересны?'
    
    await bot.send_poll(
        chat_id=message.chat.id, 
        question=q,
        options=poll_var, 
        allows_multiple_answers=True, 
        is_anonymous=False
        ) 

@router.message(FSMAdmin.user_start)
async def model_conversation(message: types.Message, state: FSMContext):
    config = generate_config(username)
    model = ModelGPT(config)   
    
    if message.text == "Остановить модель":
        await state.set_state(FSMAdmin.start)
    if message.text == "/setup":
        await state.set_state(FSMAdmin.start)
    if message.text == "/help":
        await state.set_state(FSMAdmin.start)
    if message.text == "/start":
        await state.set_state(FSMAdmin.start)
    
    user_answer = model.run(message.text)
    await message.answer(user_answer)
    await state.set_state(FSMAdmin.user_start)

tools_dict = {
    'Шаблоны документов': 'docs_template',
    'Google календарь': 'google_calendar',
    'Документы': 'doc_retriever'
}
@router.poll_answer() 
async def poll_answer_handler(poll_answer: types.PollAnswer, state: FSMContext, poll_var=poll_var):
    selected_options = poll_answer.option_ids
    username = poll_answer.user.username
    for i in selected_options:
        tool_name = tools_dict[poll_var[i]]
        update_user_tools(username, tool_name)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")