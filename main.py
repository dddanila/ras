import pandas as pd
import sqlite3
from datetime import datetime
import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import re
import threading
from time import sleep
from time import time

class Schedule:
    def __init__(self, url):
        self.db = sqlite3.connect(':memory:')
        dfs = pd.read_excel(url, sheet_name=None, skiprows=6)
        for table, df in dfs.items():
            df.to_sql(table, self.db)
    
    def get_groups(self):
        cursor = self.db.cursor()
        cursor.execute("""select * from sqlite_master
                where type = 'table'""")
        tables = cursor.fetchall()
        self.groups = []
        for table in tables:
            self.groups.append(table[1]) #названия таблиц
        cursor.close()
        return self.groups
    
    def get_week_schedule(self, group=None):
        with self.db:    
            cursor = self.db.cursor()    
            cursor.execute(f"SELECT * FROM '{group}'")
            rows = cursor.fetchall()
            self.sch = []
            for row in rows:
                self.sch.append([row[1], row[2], row[3], row[4], row[5],
                            row[6], row[7], row[8], row[9], row[10]])
            
            return self.sch
        
    def get_teachers(self):
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        unique_teachers = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT DISTINCT Преподаватель FROM '{table_name}'")
            teachers = cursor.fetchall()
            for teacher in teachers:
                if teacher[0] not in unique_teachers:
                    if teacher[0] is None or teacher[0] == " ":
                        pass
                    else:
                        unique_teachers.append(teacher[0])

        return unique_teachers
    #f"SELECT * FROM '{table}' WHERE Преподаватель='{teacher}'"
    def get_teacher_schedule(self, teacher):
        cursor = self.db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        schedule = []
        for table in tables:
            table_name = table[0]
            cursor.execute("SELECT * FROM '{}' WHERE \"Преподаватель\"=?".format(table_name), (teacher,))
            for row in cursor.fetchall():
                #sorted(schedule, key=lambda x: (x[0], x[3]))
                schedule.append([row[1], row[2], row[3], row[4], row[5],
                            row[6], row[7], row[8], row[9], row[10]])
    
        return sorted(schedule, key=lambda x: (x[0], x[3]))

    #Хрен знает как я это сделал, но это работает
    def parse_schedule(self):
        try:
            while True:
                sleep(3600)
                #try:
                url = 'https://skitu.ru/schedule-of-classes-secondary-vocational-education/'
                r = requests.get(url)
                soup = BeautifulSoup(r.content, 'lxml')
                dates = []
                for link in soup.find_all('a'):
                    text = str(link)
                    pattern = r"\d{2}\.\d{2}\.\d{4}"
                    match = re.search(pattern, text)
                    if match:
                        date = match.group()
                        dates.append(str(date))

                dates = [datetime.strptime(d, "%d.%m.%Y") for d in dates]
                latest_date = max(dates)
                sch_url = ""
                for link in soup.find_all('a'):
                    text = str(link)
                    pattern = r"\d{2}\.\d{2}\.\d{4}"
                    match = re.search(pattern, text)
                    if match:
                        if match.group() == latest_date.strftime("%d.%m.%Y"):
                            sch_url = link.get('href')               
                            break
                        
                r = requests.get(sch_url)
                with open('a.xlsx', 'wb') as f:
                    f.write(r.content)
                        
                print("Парсинг завершен!")
        except Exception as e:
            print(f"ОШИБКА ПАРСИНГА 109\n{e}")

class DB:
    def __init__(self, dbname):
        self.db = sqlite3.connect(dbname)
        try:
            cursor = self.db.execute("""CREATE TABLE users (id integer PRIMARY KEY, userid text, datetime text,)""")
            cursor.close()
        except Exception as e:
            print("70: "+str(e))

    def add_newueser(self, userid):
        self.db = sqlite3.connect(dbname)
        date = datetime.now()
        cursor = self.db.cursor()
        cursor.execute(f"SELECT * FROM users WHERE userid={userid};")
        user = cursor.fetchall()
        if len(user) == 0:
            cursor.execute(f"INSERT INTO users (id, userid, datetime) VALUES (null, {userid}, '{date}');")
        cursor.close()
        self.db.commit()

    def count_users(self):
        cursor = self.db.cursor()
        cursor.execute(f"SELECT * FROM users")
        count = len(cursor.fetchall())
        return count
    
    def last_user(self):
        cursor = self.db.cursor()
        cursor.execute(f"SELECT * FROM users DESC LIMIT 1")
        row = cursor.fetchall()
        return row[0][2]

class Bot:
    def __init__(self, bot_token, admin_id):
        self.bot_token = bot_token
        self.admin_id = admin_id
        self.bot = telebot.TeleBot(self.bot_token)
    
    def send_msg(self, user, msg):
        self.bot.send_message(user, msg)

    def start(self):
        @self.bot.message_handler(commands=['start'])
        def handler_start(message):
            database.add_newueser(message.chat.id)
            keyboard1 = telebot.types.ReplyKeyboardMarkup(True,False)
            keyboard1.add('Расписание для студентов')
            keyboard1.add('Расписание для преподавателей')
            if message.chat.id == admin_id:
                count = database.count_users()
                lastuser = database.last_user()
                self.bot.send_message(message.chat.id,
                                f'Привет. Выбери нужное тебе расписание\n--\nКол-во пользователей: {count}\nПоследний: {lastuser}',
                                reply_markup=keyboard1)
            else:
                self.bot.send_message(message.chat.id,
                                    f'Привет. Выбери нужное тебе расписание',
                                reply_markup=keyboard1)

        @self.bot.message_handler(commands=['admin'])
        def handler_start(message):
            if message.chat.id == self.admin_id:
                msg = self.bot.send_message(message.chat.id,
                                'Отправь ссылку на файл с расписанием.')
                self.bot.register_next_step_handler(msg, update_schedule)
            elif message.chat.id != self.admin_id:
                pass
        
        def update_schedule(message):
            try:
                r = requests.get(message.text)
                with open('a.xlsx', 'wb') as f:
                    f.write(r.content)

                msg = self.bot.send_message(message.chat.id, message.text)
            except:
                msg = self.bot.send_message(message.chat.id, "❌Ошибка!")

        @self.bot.message_handler(commands=['global'])
        def handler_start(message):
            if message.chat.id == self.admin_id:
                msg = self.bot.send_message(message.chat.id,
                                'Отправь текст для рассылки\nОт 5 символов!')
                self.bot.register_next_step_handler(msg, sending)
            elif message.chat.id != self.admin_id:
                pass

        def sending(message):
            text = message.text
            if len(text) > 5:
                print("РАССЫЛКА")
            else:
                print("РАССЫЛКА ОТМЕНА!")

        @self.bot.message_handler(content_types=["text"])
        def send_message(message):

            #антифлуд
            if message.chat.id not in last_time:
                last_time[message.chat.id] = time()
            elif (time() - last_time[message.chat.id]) * 1000 < antiflood_timer:
                    self.bot.send_message(message.chat.id, "❌ Слишком частые сообщения!")
                    return
            last_time[message.chat.id] = time()

            schedule = Schedule(url)
            if message.text == "Расписание для студентов":
                list = types.InlineKeyboardMarkup(row_width=3)
                for group in schedule.get_groups():
                    list.add(types.InlineKeyboardButton(text=group, callback_data=group))   
                self.bot.send_message(message.chat.id, "Выберите вашу группу:", reply_markup=list)

            if message.text == "Расписание для преподавателей":
                list = types.InlineKeyboardMarkup()
                for teacher in schedule.get_teachers():
                    list.add(types.InlineKeyboardButton(text=teacher, callback_data=teacher))
                                 
                self.bot.send_message(message.chat.id, "Выберите себя:", reply_markup=list)
                
        @self.bot.callback_query_handler(func=lambda call: True)
        def handler_call(call):
            schedule = Schedule(url)
            date = datetime.now()
            if call.data == "teacher-main":
                list = types.InlineKeyboardMarkup()
                for teacher in schedule.get_teachers():
                    list.add(types.InlineKeyboardButton(text=teacher, callback_data=teacher))   
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Выберите преподавателя:",
                    reply_markup=list)
            
            if call.data == "main":
                list = types.InlineKeyboardMarkup()
                for group in schedule.get_groups():
                    list.add(types.InlineKeyboardButton(text=group, callback_data=group))   
                self.bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="Выберите вашу группу:",
                    reply_markup=list)

            for teacher in schedule.get_teachers():
                week_schedule = schedule.get_teacher_schedule(teacher)
                exit = types.InlineKeyboardMarkup()
                exit.add(types.InlineKeyboardButton(text="◀️Назад", callback_data=teacher))
                if call.data == teacher:
                    menu = types.InlineKeyboardMarkup()
                    menu.add(
                        types.InlineKeyboardButton(text="Неделя", callback_data=teacher+"-week"),
                        types.InlineKeyboardButton(text="Завтра", callback_data=teacher+"-tomorrow"),
                        types.InlineKeyboardButton(text="Сегодня", callback_data=teacher+"-today"),
                        types.InlineKeyboardButton(text="◀️Назад", callback_data="teacher-main"),
                    )
                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"Расписание для преподавателя: {teacher}",
                        reply_markup=menu
                        )
                    
                if call.data == teacher+"-week":
                    text = f"{teacher}\n"
                    last_date = 0
                    for row in week_schedule:
                        if row[0] is None:
                            break
                        row[0] = str(row[0]).replace(".0", "")
                        row[1] = str(row[1]).replace(".0", "")
                        if last_date != row[0] or last_date != row[0]:
                            text+=f"--------------------------------------\n📅{row[0]}.{row[1]} {row[2]}\n"
                            last_date = row[0]

                        text+=f"⌛️{row[4]}\n"
                        text+=f"📗{row[6]}\n👩‍🎓{row[8]}\n🏠Аудитория: {row[9]}\nГруппа: {row[5]}\n\n"

                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        reply_markup=exit
                    )

                if call.data == teacher+"-tomorrow" or call.data == teacher+"-today":
                    try:
                        text = f"{teacher}\n"
                        last_date = 0
                        for row in week_schedule:
                            if ((row[0] == date.day+1 and call.data == teacher+"-tomorrow") or (row[0] == date.day and call.data == teacher+"-today")):
                                if row[0] is None:
                                    break
                                if last_date != row[0]:
                                    text+=f"--------------------------------------\n📅{row[0]}.{row[1]} {row[2]}\n"
                                    last_date = row[0]
                
                                text+=f"⌛️{row[4]}\n"
                                text+=f"📗{row[6]}\n👩‍🎓{row[8]}\n🏠Аудитория: {row[9]}\nГруппа: {row[5]}\n\n"
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=text,
                            reply_markup=exit
                            )
                    except:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text="❌Расписания нет.",
                            reply_markup=exit)

            for group in schedule.get_groups():
                week_schedule = schedule.get_week_schedule(group)
                exit = types.InlineKeyboardMarkup()
                exit.add(types.InlineKeyboardButton(text="◀️Назад", callback_data=group))
                if call.data == group:
                    menu = types.InlineKeyboardMarkup()
                    menu.add(
                        types.InlineKeyboardButton(text="Неделя", callback_data=group+"-week"),
                        types.InlineKeyboardButton(text="Завтра", callback_data=group+"-tomorrow"),
                        types.InlineKeyboardButton(text="Сегодня", callback_data=group+"-today"),
                        types.InlineKeyboardButton(text="◀️Назад", callback_data="main"),
                    )
                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=f"Расписание для группы: {group}",
                        reply_markup=menu
                        )
                
                if call.data == group+"-week":
                    text = f"{group}\n"
                    last_date = 0
                    for row in week_schedule:
                        if row[0] is None:
                            break
                        if last_date != row[0]:
                            text+=f"--------------------------------------\n📅{row[0]}.{row[1]} {row[2]}\n"
                            last_date = row[0]
        
                        text+=f"⌛️{row[4]}\n"
                        text+=f"📗{row[6]}\n👩‍🎓{row[8]}\n🏠Аудитория: {row[9]}\n👨Группа: {row[5]}\n\n"
                    self.bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text=text,
                        reply_markup=exit
                    )

                if call.data == group+"-tomorrow" or call.data == group+"-today":
                    try:
                        text = f"{group}\n"
                        last_date = 0
                        for row in week_schedule:
                            if ((row[0] == date.day+1 and call.data == group+"-tomorrow") or (row[0] == date.day and call.data == group+"-today")):
                                if row[0] is None:
                                    break
                                if last_date != row[0]:
                                    text+=f"--------------------------------------\n📅{row[0]}.{row[1]} {row[2]}\n"
                                    last_date = row[0]
                
                                text+=f"⌛️{row[4]}\n"
                                text+=f"📗{row[6]}\n👩‍🎓{row[8]}\n🏠Аудитория: {row[9]}\n👨Группа: {row[5]}\n\n"
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text=text,
                            reply_markup=exit
                            )
                    except:
                        self.bot.edit_message_text(
                            chat_id=call.message.chat.id,
                            message_id=call.message.message_id,
                            text="❌Расписания нет.",
                            reply_markup=exit)

        while True:
            try:
                self.bot.polling(none_stop=True)
            except Exception as e:
                self.bot.send_message(error_chat, f"❌Ошибка!\n{e}")

if __name__ == "__main__":
    while True:
        try:
            url = "a.xlsx"
            bot_token = "6433740656:AAHvMbB2u3PuBHFYusYKSiB_ccNTxk78Cy4"
            admin_id = 6609625743
            last_time = {}
            antiflood_timer = 1500
            error_chat = 1969649751 # БЕЗ -100
            dbname = "dbase.sqlite"
            bot = Bot(bot_token, admin_id)
            schedule = Schedule(url)
            database = DB(dbname)
            cron = threading.Thread(target=schedule.parse_schedule)
            cron.start()
            bot.start()
        except Exception as e:
            print(f"ОШИБКА!\n{e}")
            
    
