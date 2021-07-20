# -*- coding: utf8 -*-
import telebot
from telebot import types
import config
import psycopg2
import requests
import threading
from bs4 import BeautifulSoup
import lxml
import time
import os
import random
from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from fake_useragent import UserAgent
global db
global sql
global subjects_dict
global random_password
subjects_dict={'english':'Англійська мова', 'biology':'Біологія', 'geography':'Географія', 'ukraine-history': 'Історія України', 'mathematics':'Математика', 'ukrainian':'Українська мова та література', 'physics':'Фізика', 'chemistry':'Хімія'}
db = psycopg2.connect(database='ddk9qa7sutb4mr', user='adwzndgecbixjz', port="5432", password='bd23abc77f0204811cb49b7f97c00885ff3403ce9c4410a9b34a7daf33b51af0', host='ec2-35-171-250-21.compute-1.amazonaws.com', sslmode='require')
sql=db.cursor()
sql.execute("""CREATE TABLE IF NOT EXISTS users (chatid TEXT, cursub TEXT)""")
db.commit()
#right_answers INT, wrong_answers INT, skipped_answers INT,
sql.execute("""CREATE TABLE IF NOT EXISTS subjects (chatid TEXT, subject TEXT, right_answers INT, wrong_answers INT, skipped_answers INT, curques INT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS skipped (chatid TEXT, subject TEXT, curques INT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS helps (chatid TEXT, subject TEXT, curques INT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS helpers (chatid TEXT, subject TEXT, amount INT, status TEXT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS admins (chatid TEXT, username TEXT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS abits (chatid TEXT, fio TEXT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS abits_checks (chatid TEXT, link TEXT, name TEXT)""")
db.commit()

#sql.execute(f"DELETE FROM helpers")
#db.commit()
#sql.execute(f"DELETE FROM helps")
#db.commit()




def last_ques_check(subject):
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"}
    req = requests.get(f'https://zno.osvita.ua/{subject}/list.html', headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    amount_ques = soup.find("div", class_="task-card current").find("div").get_text(strip=True)
    amount_ques = int(amount_ques[len(amount_ques)-4:])
    return amount_ques


bot=telebot.TeleBot(config.TOKEN)

def clock_message(message, clocks_list, msg, clock_sended):
    if clocks_list==[]:
        clocks_list=list('🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛')
        clocks_list.pop(0)
    time.sleep(0.05)
    msg = f"{msg.replace(msg[len(msg)-2:], '')} {clocks_list[0]}"
    try:
        bot.edit_message_text(msg, chat_id=clock_sended.chat.id, message_id=clock_sended.message_id, parse_mode='html')
        clocks_list.pop(0)
    except:
        pass
    return clocks_list

def start_clock(message, download_thread):
    download_thread.start()
    clocks_list = list('🕛🕐🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛')
    msg = f'Зачекайте, будь ласка {clocks_list[0]}'
    clocks_list.pop(0)
    clock_sended = bot.send_message(message.chat.id, msg, parse_mode='html')
    while download_thread.is_alive()!=False:
        clocks_list=clock_message(message, clocks_list, msg, clock_sended)
    bot.delete_message(clock_sended.chat.id, clock_sended.message_id) 

@bot.message_handler(commands=['start'])
def welcome(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res is None:
        msg = 'Вітаю! Дякую, що приєдналися до проходження тестування минулих завдань із ЗНО за допомогою @znotasks_bot. Усі тести зібрані з офіційного сайту освіти України zno.osvita.ua.\n\nЯк тільки ви отримаєте нове завдання, вам буде надана можливість відповісти, натиснувши на відповідну кнопку.\n\nЯкщо ви не знаєте відповіді на запитання, можете натиснути на кнопку "Пропустити". Це завдання буде зберігатися у базі даних до того моменту, поки ви не застосуєте команду /skipped та не дасте відповідь на нього.\n\nПісля кожної неправильної відповіді ви зможете отримати пояснення, натиснувши на кнопку поряд. У свою чергу ви також можете допомагати іншим, користуючись командою /tohelp.\n\nУ випадку, коли ви хочете отримати останнє запитання, використайте команду /resetquestion.\n\nВи можете також переглянути статистику ваших відповідей за допомогою /stats та загальну статистику всіх учасників - /globalstats.\n\nУ деяких відповідей бота є кнопка з емодзі "❌". Повідомлення видаляється, якщо ви натискаєте на цей елемент.\n\n<b>Увага!</b> Ваша статистика відповідей доступна тільки вам та не надається адміністраторам боту.\n\n'
        bot.send_message(message.chat.id, msg, parse_mode='html')
        time.sleep(5)
        link_reply = types.InlineKeyboardMarkup()
        link_reply.add(types.InlineKeyboardButton('Підписатися на оновлення', url='https://t.me/znotasks'))
        bot.send_message(message.chat.id, f'Для реєстрації потрібно приєднатись до каналу з оновленнями функцій боту. Від підписників каналу залежить розвиток боту, а нам важлива думка кожного.', reply_markup=link_reply)
        time.sleep(10)
        start_reply = types.InlineKeyboardMarkup(row_width=2)
        start_reply.add(types.InlineKeyboardButton('✅ З інформацією ознайомлений(а)', callback_data=f'start-{message.from_user.id}'))
        msg = 'Якщо ви побачили помилку в певному завданні, можете написати про це розробнику/адміністратору (дивіться опис до цього акаунту).\n\nІснують різні типи завдань.\n\nЯкщо вам пропонується вибрати одну відповідь з варіантів А-Д, вам достатньо натиснути на відповідну кнопку.\n\nУ випадку, коли вам потрібно встановити відповідність між цифрами та варіантами відповідей (літерами), натискайте на кнопку "Відповісти на запитання" і напишіть літери (тільки українські) у правильній послідовності таким чином: гвба або ГВБА (бот розцінює це як 1 - Г, 2 - В, 3 - Б, 4 - А та перевіряє кожний варіант окремо).\n\nЯкщо вам потрібно вибрати лише цифри із переліку, ви можете зробити це в будь-якій послідовності.\n\nОзнайомившись з усією вище зазначеною інформацією, натисніть на кнопку нижче для початку.'
        bot.send_message(message.chat.id, msg, reply_markup=start_reply, parse_mode='html')
    else:
        checking_ques(message)

@bot.message_handler(commands=['deleteme'])
def to_delete(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res is None:
        return bot.reply_to(message, "Ви не авторизовані. Використайте команду /start для початку.")
    delete_me_reply=types.InlineKeyboardMarkup(row_width=2)
    delete_me_reply.add(types.InlineKeyboardButton('✅ Гаразд, видаліть мій акаунт', callback_data='delme'))
    delete_me_reply.add(types.InlineKeyboardButton('❌ Ні, поки що не треба', callback_data='nodelme'))
    msg=f"Якщо ви насправді хочете видалити свій акаунт (усі ваші досягнення будуть анульовані), пам'ятайте, що ви вже <b>не зможете</b> їх відновити та <b>не будете</b> отримувати повідомлення про оновлення боту."
    bot.send_message(message.chat.id, msg, parse_mode='html', reply_markup=delete_me_reply)

@bot.message_handler(commands=['tohelp'])
def helps_list(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res = sql.fetchone()
    if res is None:
        return bot.reply_to(message, "Використайте команду /start для початку.")
    sql.execute(f"SELECT * FROM helpers WHERE chatid = '{message.chat.id}' AND status = 'banned'")
    res = sql.fetchone()
    if res!=None:
        return bot.reply_to(message, "⚠️ На жаль, ваш доступ до цієї команди заблокований.")
    sql.execute(f"SELECT * FROM helps")
    rows = sql.fetchall()
    counter = 0
    helps_list_reply=types.InlineKeyboardMarkup(row_width=2)
    for row in rows:
        if int(row[0])==message.chat.id:
            continue
        counter += 1
        helps_list_reply.add(types.InlineKeyboardButton(f'{sub_to_right(row[1])} (#{row[2]})', callback_data=f'givehelp-{row[1]}-{row[2]}'))
    if counter==0:
        return bot.reply_to(message, f'⚠️ Жодних запитань з предметів не знайдено.')
    helps_list_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
    bot.send_message(message.chat.id, f'Кількість знайдених запитань з різних предметів: <b>{counter}</b>', parse_mode='html', reply_markup=helps_list_reply)

@bot.message_handler(commands=['makeadmin'])
def making_admin(message):
    global random_password
    if message.from_user.username=='jerwright':
        chars = '+-/*!&$#?=@<>abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
        random_password=''
        for i in range(4):
            random_password=random_password+random.choice(chars)
        bot.send_message(message.chat.id, f'Пароль адміністратору: {random_password}')

@bot.message_handler(commands=['alogin'])
def giving_admin(message):
    do_login = bot.send_message(message.chat.id, "Надішліть спеціальний пароль")
    bot.register_next_step_handler(do_login, doing_login)
def doing_login(message):
    global random_password
    if message.text=='/cancel':
        return bot.reply_to(message, "✅ Дія відхилена")
    if message.text==random_password:
        chars = '+-/*!&$#?=@<>abcdefghijklnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'
        random_password=''
        for i in range(4):
            random_password=random_password+random.choice(chars)
        print(random_password)
        create_username = bot.send_message(message.chat.id, "Напишіть ваш нікнейм")
        bot.register_next_step_handler(create_username, creating_username)
def creating_username(message):
    if message.text=='/cancel':
        return bot.reply_to(message, "✅ Дія відхилена")
    sql.execute(f"SELECT * FROM admins WHERE chatid = '{message.chat.id}'")
    res = sql.fetchone()
    if res != None:
        return
    sql.execute("INSERT INTO admins VALUES (%s, %s)", (message.chat.id, message.text))
    db.commit()

@bot.message_handler(commands=['admins'])
def check_admins(message):
    sql.execute(f"SELECT * FROM admins")
    rows = sql.fetchall()
    admin=False
    msg = f'Адміністратори боту:\n'
    for row in rows:
        if int(row[0]) == message.chat.id:
            admin=True
        msg = f'{msg}<b>{row[1]}</b>, '
    msg = msg[:-2]
    if admin!=True:
        return
    bot.send_message(message.chat.id, msg, parse_mode='html')

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if message.from_user.username == 'jerwright':
        do_remove = bot.send_message(message.chat.id, "Укажіть нікнейм адміністратору")
        bot.register_next_step_handler(do_remove, doing_remove)
def doing_remove(message):
    if message.text=='/cancel':
        return bot.reply_to(message, "✅ Действие отменено")
    sql.execute(f"DELETE * FROM admins WHERE username = '{message.text}'")
    db.commit()


@bot.message_handler(commands=['send'])
def login(message):
    if message.from_user.username=='jerwright':
        do_send=bot.send_message(message.from_user.id, "Что будете отправлять пользователям?")
        bot.register_next_step_handler(do_send, sending)
    else:
        return time.sleep(0.5)


def sending(message):
    if message.text=='/cancel':
        return bot.reply_to(message, "✅ Действие отменено")
    mes=message.text
    sql.execute("SELECT chatid FROM users")
    rows = sql.fetchall()
    counter = 0
    for row in rows:
        try:
            bot.send_message(row[0], mes, parse_mode='html', disable_web_page_preview=True)
            counter += 1
        except:
            pass
    bot.send_message(message.chat.id, f'Кількість користувачів, що отримали повідомлення: <b>{counter}</b>', parse_mode='html')
    time.sleep(0.5)

@bot.message_handler(commands=['abitcheck'])
def abitchecking(message):
    sql.execute(f"SELECT * FROM abits WHERE chatid = '{message.chat.id}'")
    res = sql.fetchone()
    if res is None:
        add_abit = bot.send_message(message.chat.id, 'Введіть ваші прізвище та ініціали українськими літерами (приклад: Шевченко Т.Г.). Пізніше ви зможете змінити ці дані.')
        bot.register_next_step_handler(add_abit, adding_abit)
    else:
        find_abits_checks(message)

def adding_abit(message):
    if list(message.text).count('.')<2:
        return bot.reply_to(message, f'⚠️ Ви не додали ініціали, як показано у прикладі.')
    sql.execute("INSERT INTO abits VALUES (%s, %s)", (message.chat.id, message.text))
    db.commit()
    find_abits_checks(message)

def take_abiturl(message, URL=None):
    sql.execute(f"SELECT * FROM abits WHERE chatid = '{message.chat.id}'")
    res = sql.fetchone()
    fio = res[1]
    if URL==None:
        do_takeurl = bot.send_message(message.chat.id, "Введіть посилання на сторінку зі списком заявок певної спеціальності учбового закладу (тільки на сайті vstup.osvita.ua)")
        bot.register_next_step_handler(do_takeurl, do_abitcheck, fio)
    else:
        download_thread = threading.Thread(target=do_abitcheck, args=(message, fio, URL))
        start_clock(message, download_thread)

def do_abitcheck(message, fio, URL=None):
    if URL==None:
        URL = message.text.replace('https://', '')
        URL = f'https://{URL}'
    else:
        URL = URL.replace('https://', '')
        URL = f'https://{URL}'
    if 'vstup.osvita.ua' not in URL:
        return bot.reply_to(message, "У вашому посиланні немає адреси vstup.osvita.ua. Спробуйте ще раз.")
    user_fio = fio
    user_grate = 0

    #useragent = UserAgent()
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    #chrome_options.add_argument(f"user-agent={useragent.random}")
    driver = webdriver.Chrome(executable_path=os.environ.get("CHROMEDRIVER_PATH"), options=chrome_options)

    try:
        driver.get(url=URL)
        time.sleep(2)
        driver.refresh()
        time.sleep(3)
        more_button = driver.find_element_by_xpath("//iframe[@title='iframe']")
        while more_button.is_displayed()==False:
            time.sleep(0.5)
        more_button.click()
        #more_button = driver.find_element_by_class_name('container dtlnk').find_element_by_tag_name('span').click()
        time.sleep(1)
        #Собрали все колонки таблицы
    except UnexpectedAlertPresentException as ex:
        return bot.send_message(message.chat.id, "Виникла помилка під час підключення до сайту через постійних спроб зі сторони боту. Зачекайте, будь ласка, та спробуйте ще раз.")
    except Exception as ex:
        print(ex)
        return bot.send_message(message.chat.id, 'Виникла помилка під час підключення до сайту. Можливо, сторінка не була знайдена. Спробуйте ще раз та перевірте посилання.')
    finally:
        time.sleep(4)
        needed_html_code = driver.page_source
        driver.close()
        driver.quit()
    HEADERS = {'User-Agent': useragent.random}
    soup = BeautifulSoup(needed_html_code, 'html.parser')
    
    #инфа про специальность и вуз
    univer_info = soup.find('div', class_='page-vnz-detail-header').find('h1').get_text(strip=True).replace(": ", ":").replace(":", ": ").replace('.', ". ")
    univer_info = f"{univer_info}Навчальний заклад: {soup.find('div', class_='page-vnz-detail-header').find('h2').get_text(strip=True)}."
    #print(univer_info)

    #Узнаем кол-во поданых мест
    requests_count = int(soup.find('b', class_='requests_count').get_text(strip=True))
    max_dershes = soup.find_all('div', class_='table-of-specs-item panel-mobile')

    contents = ''
    for row in max_dershes:
        if 'ліцензований обсяг прийому' in row.get_text(strip=True).lower():
            contents=row.get_text()

    full_info = ''
    symbols_check='йцукенгшщзхїфівапролджєячсмитьбю.:'
    for i in range(len(contents)):
        if contents[i].isdigit() == False and contents[i].lower() not in symbols_check:
            continue
        full_info = f"{full_info}{contents[i]}"
        if contents[i+1] not in symbols_check and contents[i+1].isdigit()!=True:
            full_info = f'{full_info} '
        if contents[i].isdigit()==True and contents[i+1].isdigit()!=True and contents[i+1] not in symbols_check:
            full_info = f'{full_info}\n'

    columns = soup.find_all('tr', {'class':['rstatus6', 'rstatus1']})
    full_list = []
    for column in columns:
        if column.find('td', {'data-th':'ПІБ'}).get_text(strip=True).lower() == user_fio.lower():
            user_grate = float(column.find('td', {'data-th':'Бал'}).get_text(strip=True).replace('розрахунок', ''))
            user_prio = column.find('td', {'data-th':'П'}).get_text(strip=True)
            continue
        full_list.append({
            'fio':column.find('td', {'data-th':'ПІБ'}).get_text(strip=True),
            'prio':column.find('td', {'data-th':'П'}).get_text(strip=True),
            'bal':float(column.find('td', {'data-th':'Бал'}).get_text(strip=True).replace('розрахунок', '')),
            })
        #print(column.find('td', {'data-th':'ПІБ'}))

    if user_grate == 0:
        return bot.send_message(message.chat.id, f"Користувача з ФІО <b>{user_fio}</b> не знайдено. Можливо сталася помилка з підключенням або ви зробили помилку у вашому запиті.", parse_mode='html')
    print(user_grate)
    prios = {'1':0, '2':0, '3':0, '4':0, '5':0, '-': 0}
    user_place = 1
    same_grate_count = 0
    prios_global_count = 0
    for item in full_list:
        if item['bal']>user_grate:
            user_place += 1
            if item['prio'].isdigit() == True:
                prios[str(item['prio'])] += 1
            else:
                prios['-'] += 1
            prios_global_count += 1
        elif item['bal']==user_grate:
            same_grate_count += 1
            full_list.remove(item)
        else:
            full_list.remove(item)

    msg = f"Ви на {user_place}/{requests_count} серед інших абітурієнтів, з таким балом, як у вас - {same_grate_count}.\n"
    msg = f'{msg}Статистика пріорітетності: '
    for key in prios.keys():
        edited_key = key.replace('-', 'без пріорітетності')
        percents = str(round(prios[key]*100/prios_global_count))
        msg = f'{msg}{edited_key} - {prios[key]} ({percents}%), '
    msg = msg[:-2]+'\n'
    if user_prio.isdigit()==True:
        msg=f"{msg}Однак, якщо врахувати, що хоча б 50% можливо подали заявки на нижчий пріорітет, ситуація може бути така: "
        for key in prios.keys():
            if key.isdigit()==True:
                if int(user_prio)<int(key):
                    user_place -= int(round(prios[key]/2, 1))
        msg = f'{univer_info}\n\nІнформація стосовно спеціальності:\n{full_info}\n\nВаші прізвище та ініціали: {user_fio}\n\n{msg}≈{user_place}/{requests_count} (заяви без пріорітетності не враховувались)'
    sql.execute(f"SELECT * FROM abits_checks WHERE chatid = '{message.chat.id}' AND link ='{URL}'")
    res = sql.fetchone()
    if res is None:
        sql.execute("INSERT INTO abits_checks VALUES (%s, %s, %s)", (message.chat.id, URL, univer_info))
        db.commit()
    return bot.send_message(message.chat.id, msg, parse_mode='html')

def find_abits_checks(message):
    sql.execute(f"SELECT * FROM abits WHERE chatid = '{message.chat.id}'")
    res = sql.fetchone()
    fio = res[1]
    sql.execute(f"SELECT * FROM abits_checks WHERE chatid = '{message.chat.id}'")
    rows = sql.fetchall()
    abits_checks_reply = types.InlineKeyboardMarkup(row_width=2)
    msg = f'Ваші прізвище та ініціали: {fio}\n'
    if rows == []:
        msg = f'{msg}Немає жодної доданої сторінки на перевірку.'
    else:
        msg = f'{msg}Ви додали {len(rows)} сторінок:\n'
        counter = 1
        for row in rows:
            msg=f'{msg}<b><u>#{counter}</u> |</b> {row[2]}'
            url = row[1].replace('https://', '')
            abits_checks_reply.add(types.InlineKeyboardButton(f'Перевірити #{counter}', callback_data=f'abitcheck-{url}'), 
                types.InlineKeyboardButton(f'❌ Видалити', callback_data=f'delabitcheck-{row[1]}'))
            counter += 1
    abits_checks_reply.add(types.InlineKeyboardButton(f'🔎 Пошук нової сторінки', callback_data=f'new_abitcheck'))
    bot.send_message(message.chat.id, msg, parse_mode='html', reply_markup=abits_checks_reply)

@bot.message_handler(commands=['checkemp'])
def checking_emp(message):
    do_give_emp=bot.send_message(message.chat.id,'Введіть слово, наголос якого шукаєте.')
    bot.register_next_step_handler(do_give_emp, giving_emp)
def giving_emp(message):
    url = 'https://ru.osvita.ua/test/advice/65116/'
    user_msg = message.text
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"}
    req = requests.get(url, headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    items = soup.find("article").find_all("ul")
    contents_list=[]
    for item in items:
        words = item.find_all("li")
        for word in words:
            if word.find_parent(class_='artbutton')!=None:
                continue
            contents_list.append(word.get_text(strip=True))
    found_items=[]
    for content in contents_list:
        if '(' in content:
            index = content.index('(')
            if user_msg.lower() in content.lower()[:index-1]:
                found_items.append(content)
        else:
            if user_msg.lower() in content.lower():
                found_items.append(content) 
    if found_items==[]:
        bot.reply_to(message, f'⚠️ Не знайдено наголосів для слова <b>"{user_msg.lower()}"</b>.', parse_mode='html')
    else:
        msg = f'Знайдено такі наголоси для слова <b>"{user_msg.lower()}"</b>:\n'
        for item in found_items:
            msg = f'{msg}• {item}\n'
        bot.send_message(message.chat.id, msg, parse_mode='html')

@bot.message_handler(commands=['changesub'])
def changing_sub(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res is None:
        return bot.reply_to(message, "Використайте команду /start для початку.")
    mes = f'Гаразд! Виберіть один із запропонованих предметів.'
    bot.send_message(message.chat.id, mes, parse_mode='html', reply_markup=subjects_reply)

@bot.message_handler(commands=['skipped'])
def skipped_questions(message):
    sql.execute(f"SELECT * FROM skipped WHERE chatid = '{message.chat.id}'")
    try:
        res = sql.fetchone()
    except:
        return bot.reply_to(message,'⚠️ У вас немає пропущених питань.')
    if res is None:
        return bot.reply_to(message, f'⚠️ У вас немає пропущених питань.')
    sql.execute(f"SELECT * FROM skipped WHERE chatid= '{message.chat.id}' ORDER by curques")
    rows = sql.fetchall()
    for row in rows:
        checking_ques(message, skipped_ques=row[2], subject=row[1])


@bot.message_handler(commands=['resetquestion'])
def reseting(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res!=None:
        checking_ques(message)
    else:
        return bot.reply_to(message, "Використайте команду /start для початку")

@bot.message_handler(commands=['stats'])
def statistics(message):
    sql.execute(f"SELECT cursub FROM users WHERE chatid = '{message.chat.id}'")
    subject = sql.fetchone()
    if subject is None:
        return bot.reply_to(message, "Використайте команду /start для початку.")
    statistics_reply=types.InlineKeyboardMarkup(row_width=2)
    for row in subjects_dict:
        statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'statistics-{row}'))
    statistics_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
    bot.send_message(message.chat.id, get_statistics(message, subject[0]), parse_mode='html', reply_markup=statistics_reply)
def get_statistics(message, subject, call=None):
    sql.execute(f"SELECT * FROM helpers WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res = sql.fetchone()
    if res is None:
        help_count=0
    else:
        help_count=str(res[2])
        if res[3]=='banned':
            help_count = f'{help_count} (доступ заблоковано)'

    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res!=None:
        msg = f'📈 Ваші результати 📈\n\n'
        try:
            msg = f'{msg}<b>{sub_to_right(res[1])}</b>\nВідповідей:\n✅ Правильних - <b>{res[2]}</b>\n❌ Неправильних - <b>{res[3]}</b>\n💨 Пропущених - <b>{res[4]}</b>\n\n🎯 Точність: <b>{round(int(res[2])*100/(int(res[2])+int(res[3])+int(res[4])), 2)}%</b>\n\n💪 Зараз на запитанні: <b>{res[5]}/{last_ques_check(res[1])}</b>\n\n🙏 Пояснень: {help_count}\n\n'
        except ZeroDivisionError:
            msg = f'{msg}<b>{sub_to_right(res[1])}</b>\nВідповідей:\n✅ Правильних - <b>{res[2]}</b>\n❌ Неправильних - <b>{res[3]}</b>\n💨 Пропущених - <b>{res[4]}</b>\n\n🎯 Точність: неможливо підрахувати на першому запитанні\n\n💪 Зараз на запитанні: <b>{res[5]}/{last_ques_check(res[1])}</b>\n\n🙏 Пояснень: {help_count}\n\n'
        sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}'")
        rows=sql.fetchall()
        if len(rows)<=1:
            return msg
        table_dict={}
        for row in rows:
            table_dict.update({row[1]:round(int(row[2])*100/(int(row[2])+int(row[3])+int(row[4])), 2)})
        worst_list={}
        worst_list.update({res[1]:table_dict[res[1]]})
        worst_list_sub=res[1]
        for sub in table_dict.keys():
            if table_dict[sub]<worst_list[worst_list_sub]:
                worst_list.clear()
                worst_list.update({sub:table_dict[sub]})
                worst_list_sub=sub
            elif table_dict[sub]==worst_list[worst_list_sub]:
                worst_list.update({sub:table_dict[sub]})
        msg = f'{msg}Результати з таких предметів (визначено за точністю), як:'
        for sub in worst_list.keys():
            msg = f'{msg} <b>{sub_to_right(sub)}</b>,'
            percents=worst_list[sub]
        msg = f'{msg[:len(msg)-1]} (<b>{percents}%</b>) є найнижчими серед інших. Однак усе ще попереду!\n\n'
        return msg
    else:
        return bot.reply_to(message, f"⚠️ Ви не проходили тести з цього предмету.")

@bot.message_handler(commands=['globalstats'])
def global_statistics(message):
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res is None:
        return bot.reply_to(message, "Використайте команду /changesub та виберіть один із запропонованих предметів.")
    sql.execute(f"SELECT cursub FROM users WHERE chatid = '{message.chat.id}'")
    subject = sql.fetchone()
    global_statistics_reply=types.InlineKeyboardMarkup(row_width=2)
    for row in subjects_dict:
        global_statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'globalstatistics-{row}'))
    global_statistics_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
    bot.send_message(message.chat.id, get_global_statistics(message, subject[0]), parse_mode='html', reply_markup=global_statistics_reply)
def get_global_statistics(message, subject, call=None):
    sql.execute(f"SELECT * FROM helpers WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res = sql.fetchone()
    if res is None:
        help_count=0
    else:
        help_count=int(res[2])
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res is None:
        return bot.reply_to(message, "⚠️ Ви не проходили тести з цього предмету.")

    #sql.execute(f"SELECT * FROM users")
    #users_number = len(sql.fetchall())
    sql.execute(f"SELECT * FROM helpers WHERE subject = '{subject}'")
    rows = sql.fetchall()
    global_help_count = 0
    for row in rows:
        global_help_count += row[2]
    sql.execute(f"SELECT * FROM users")
    rows = sql.fetchall()
    if rows==[]:
        return bot.reply_to(message, f"⚠️ Поки що неможливо отримати загальну статистику.")
    all_users_number = len(rows)
    msg=''
    sql.execute(f"SELECT right_answers, wrong_answers, skipped_answers FROM subjects WHERE subject = '{subject}'")
    rows=sql.fetchall()
    if rows == []:
        return bot.reply_to(message, f"⚠️ Поки що неможливо отримати загальну статистику.")
    users_number = len(rows)
    global_right_answers=0
    global_wrong_answers=0
    global_skipped_answers=0
    for row in rows:
        global_right_answers+=row[0]
        global_wrong_answers+=row[1]
        global_skipped_answers+=row[2]
    try:
        global_right_percents = round((int(res[2])*100)/global_right_answers, 2)
    except ZeroDivisionError: 
        global_right_percents=0.0
    try:
        global_wrong_percents = round((int(res[3])*100)/global_wrong_answers, 2)
    except ZeroDivisionError: 
        global_wrong_percents=0.0
    try:
        global_skipped_percents = round((int(res[4])*100)/global_skipped_answers, 2)
    except ZeroDivisionError: 
        global_skipped_percents=0.0
    try:
        global_help_percents = round((help_count*100)/global_help_count,2)
    except ZeroDivisionError:
        global_help_percents = 0.0
    try:
        accuracy = str(round(int(global_right_answers)*100/(int(global_right_answers)+int(global_wrong_answers)+int(global_skipped_answers)), 2))+'%'
    except ZeroDivisionError: 
        accuracy='поки що неможливо підрахувати'
    msg = f'{msg}<b>{subjects_dict[subject]}</b>\n🌐 Усього учасників: <b>{users_number}/{all_users_number}</b>\n\nЗагальних відповідей:\n✅ Правильних - <b>{global_right_answers}</b> (<b>{global_right_percents}%</b> ваших)\n❌ Неправильних - <b>{global_wrong_answers}</b> (<b>{global_wrong_percents}%</b> ваших)\n💨 Пропущених - <b>{global_skipped_answers}</b> (<b>{global_skipped_percents}%</b> ваших)\n\n🎯 Загальна точність: <b>{accuracy}</b>\n\n🙏 Загальних пояснень: <b>{global_help_count}</b> (<b>{global_help_percents}%</b> ваших)\n\n'
    msg = f'📈 Результати учасників 📈\n\n{msg}'
    sql.execute(f"SELECT chatid, right_answers FROM subjects WHERE subject = '{subject}' ORDER by right_answers DESC")
    rows=sql.fetchall()
    if len(rows)<=1:
        return msg
    counter = 0
    for row in rows:
        previous_amount=rows[counter-1][1]
        counter += 1
        if int(row[0])==message.chat.id:
            if previous_amount==row[1] and counter-2>=0:
                counter -= 1
            break
    user_rating=100-round((counter*100)/len(rows))
    if user_rating==0:
        msg=f'{msg}За кількістю правильних відповідей ви посідаєте останнє місце серед інших користувачів. Однак усе ще попереду!\n\n'
        return msg
    msg = f'{msg}За кількістю правильних відповідей ви посідаєте <b>{counter}/{len(rows)}</b> місце. Ваші результати з цього предмету краще, ніж у <b>{user_rating}%</b> користувачів.\n\n'
    return msg


#@bot.message_handler(commands=['others'])
#def otherbots(message):
#    msg = f'<b>Усі боти з тестами ЗНО:</b>\n\n• Географія - @geozno_bot\n• Українська мова та література - @ukrlzno_bot'
#    bot.send_message(message.chat.id, msg, parse_mode='html')



def checking_ques(message, skipped_ques=None, subject=None, givinghelp=None, admin=None):
    if subject is None:
        sql.execute(f"SELECT cursub FROM users WHERE chatid = '{message.chat.id}'")
        subject = sql.fetchone()
        subject=subject[0]
    sql.execute(f"SELECT curques FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res is None and givinghelp is None:
        return
    if givinghelp != None:
        user_question=givinghelp
    else:
        user_question=res[0]

    if skipped_ques!=None:
        user_question=skipped_ques
    if user_question>last_ques_check(subject):
        return bot.send_message(message.chat.id, "Ви вже виконали усі можливі тести. Як тільки їх кількість на сайті zno.osvita.ua збільшиться, вони з'являться і у вас.")
    if user_question<=15:  
        url = f"https://zno.osvita.ua/{subject}/list.html"
    elif user_question>15:
        if user_question%15!=0:
            url=f'https://zno.osvita.ua/{subject}/all/{user_question - (user_question%15)}/' 
        else:   
            if int(user_question/15)>=2:
                url=f'https://zno.osvita.ua/{subject}/all/{user_question - 15}/'
            else:
                url=f'https://zno.osvita.ua/{subject}/all/{user_question}/'
    #else:
    #    url=f'https://zno.osvita.ua/{subject}/all/{user_question}/'
    download_thread = threading.Thread(target=getting_ques, args=(message, user_question, url, subject, skipped_ques, givinghelp, admin))
    start_clock(message, download_thread)
    #getting_ques(message, user_question, url, subject, skipped_ques)

def getting_ques(message, user_question, url, subject, skipped_ques=None, givinghelp=None, admin=None):
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"}
    req = requests.get(url, headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    form = soup.find('form', {"id":f'q_form_{user_question}'})
    if form is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Повідомте, будь ласка, про це розробнику/адміністратору (контаки в інформації про бота).")
    question = f'<b>Завдання #{user_question}</b>\n'
    if form.find("iframe")!=None:
        video = form.find("iframe").get("src")
        question=f'{question}Необхідне посилання: {video}\n'
    for row in form.find("div", class_="question").find_all("p"):
        if row.get_text()=='' or row.get_text()=='\n':
            continue
        question = question + html_fix(row.contents)+'\n'
        #if html_fix(row.contents).count("\n")<2:
        #    question = question + '\n'
    if form.find("div", class_="question").p is None:
        question = question + html_fix(form.find("div", class_="question").get_text(strip=True).replace("\n", "", 1))+'\n'
    action = form.find("div", class_="q-info")
    if action==None:
        action = form.find("div", class_="select-answers-title")
    action = action.get_text(strip=True)

    right_answer=form.find("input", {"type":"hidden", "name":"result"}).get("value")
    if right_answer is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Повідомте, будь ласка, про це розробнику/адміністратору (контаки в інформації про бота).")
    else:
        right_answer = str(right_answer)
    true_answer_list = {"a": "а", "b": "б", "c": "в", "d":"г", "e":"д"}
    for row in true_answer_list:
        if row in right_answer:
            if subject.lower()!='english':
                right_answer = right_answer.replace(row, true_answer_list[row])
    right_answer=right_answer.upper()
    answers_list=[]
    answers_images=[]
    items = form.find_all("div", class_="answers")
    if items[0].find("div")!=None:
        for item in items:
            for item_answer in item.find_all("div"):
                #print(added_item)
                #print(item_answer.find("span").get_text())
                #added_item=added_item.replace(item_answer.find("span").get_text(), '', 1)
                if item_answer.get('class')[0] == 'quest-title':
                    quest_title=item_answer.contents[0]
                    question = f'{question}\n{quest_title}'
                else:
                    if item_answer.find("img")!=None:
                        answers_images.append('zno.osvita.ua'+item_answer.find("img").get('src'))
                        answers_list.append(item_answer.find("span").get_text(strip=True))
                        continue
                    added_items = item_answer.contents
                    number = item_answer.find("span").get_text(strip=True)
                    answers_list.append(number)
                    added_items.remove(item_answer.find("span"))
                    #added_item=item_answer.get_text()
                    added_item=html_fix(added_items)
                    
                    question = f'{question}\n{number}) {added_item}'
            question = question+'\n'
    else:
        items = form.find("table").find('tr')
        if items!=None:
            for item_answer in items.find_all("th"):
                answers_list.append(item_answer.get_text(strip=True))
    
    img = form.find("div", class_="question").find("img")
    if img != None:
        img_link = f"zno.osvita.ua{img.get('src')}"
    else:
        img_link=None
    
    lets_answer_markup = types.InlineKeyboardMarkup()
    lets_answer_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-one-{subject}-{right_answer.replace(";", "")}{check_skipped(skipped_ques)}'))
    lets_answer_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
    lets_answer_markup = give_help(message, user_question, subject, lets_answer_markup, givinghelp, admin)

    lets_answer_many_markup = types.InlineKeyboardMarkup()
    lets_answer_many_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-many-{subject}-{right_answer.replace(";", "")}{check_skipped(skipped_ques)}'))
    lets_answer_many_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
    lets_answer_many_markup = give_help(message, user_question, subject, lets_answer_many_markup, givinghelp, admin)
    ques_len = len(f'{question}\n{action}')
    if action == 'Впишіть відповідь:':
        if img_link==None:
            bot.send_message(message.chat.id, send_parts(message, ques_len, img_link, lets_answer_markup, question, action), parse_mode='html', reply_markup=lets_answer_markup)
        else:
            bot.send_photo(message.chat.id, img_link, caption=send_parts(message, ques_len, img_link, lets_answer_markup, question, action), parse_mode='html', reply_markup=lets_answer_markup)
    elif action == 'Позначте відповіді:':
        right_answer = right_answer.replace(";", "")
        for row in right_answer:
            if row.isdigit():
                right_answer = right_answer.replace(row, "")
        radio_answer_markup = types.InlineKeyboardMarkup(row_width=2)
        if len(right_answer)==1:
            for row in answers_list:
                if row==right_answer:
                    cbdata = f'right-{subject}-{right_answer}{check_skipped(skipped_ques)}'
                else:
                    cbdata = f'wrong-{subject}-{right_answer}{check_skipped(skipped_ques)}'
                radio_answer_markup.add(types.InlineKeyboardButton(row, callback_data=cbdata))
            if answers_list==[]:
                radio_answer_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-one-{subject}-{right_answer.replace(";", "").upper()}{check_skipped(skipped_ques)}'))
            radio_answer_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
            radio_answer_markup = give_help(message, user_question, subject, radio_answer_markup, givinghelp, admin)
            if img_link==None:
                bot.send_message(message.chat.id, send_parts(message, ques_len, img_link, radio_answer_markup, question, action), parse_mode='html', reply_markup=radio_answer_markup)
            else:
                bot.send_photo(message.chat.id, img_link, caption=send_parts(message, ques_len, img_link, radio_answer_markup, question, action), parse_mode='html', reply_markup=radio_answer_markup)
        else:
            lets_answer_markup = types.InlineKeyboardMarkup()
            lets_answer_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-one-{subject}-{right_answer.replace(";", "").upper()}{check_skipped(skipped_ques)}'))
            lets_answer_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
            radio_answer_markup = None
            lets_answer_markup = give_help(message, user_question, subject, lets_answer_markup, givinghelp, admin)
            if img_link==None:
                bot.send_message(message.chat.id, send_parts(message, ques_len, img_link, lets_answer_markup, question, action), parse_mode='html', reply_markup=lets_answer_markup)
            else:
                bot.send_photo(message.chat.id, img_link, caption=send_parts(message, ques_len, img_link, lets_answer_markup, question, action), parse_mode='html', reply_markup=lets_answer_markup)
    elif action == 'Впишіть цифри:':
        right_answer = right_answer.replace(";", "")
        if img_link==None:
            bot.send_message(message.chat.id, send_parts(message, ques_len, img_link, lets_answer_many_markup, question, action), parse_mode='html', reply_markup=lets_answer_many_markup)
        else:
            bot.send_photo(message.chat.id, img_link, caption=send_parts(message, ques_len, img_link, lets_answer_many_markup, question, action), parse_mode='html', reply_markup=lets_answer_many_markup)
    if answers_images!=[]:
        for i in range(len(answers_images)):
            try:
                bot.send_photo(message.chat.id, answers_images[i], caption=answers_list[i], parse_mode='html')
            except IndexError:
                pass
    if givinghelp != None:
        bot.send_message(message.chat.id, f'Правильна відповідь: <b>{right_answer.upper()}</b>', parse_mode='html')
def html_fix(added_items):
    added_item=''
    for row in added_items:
        added_item=added_item+str(row)
    added_item = added_item.replace("<sup>", "")
    added_item = added_item.replace("</sup>", "")
    added_item = added_item.replace("<sub>", "")
    added_item = added_item.replace("</sub>", "")
    added_item = added_item.replace("<small>", "")
    added_item = added_item.replace("</small>", "")
    added_item = added_item.replace("<ins>", "")
    added_item = added_item.replace("</ins>", "")
    added_item = added_item.replace("<br>", "\n")
    added_item = added_item.replace("</br>", "\n")
    added_item = added_item.replace("br>", "\n")
    added_item = added_item.replace("<br\>", "\n")
    added_item = added_item.replace("</br", "\n")
    added_item = added_item.replace("br", "\n")
    added_item = added_item.replace("<p>", "")
    added_item = added_item.replace("</p>", "")
    return added_item

def give_help(message, user_question, subject, reply, givinghelp=None, admin=None):
    if givinghelp is None:
        return reply
    if admin == True:
        return None
    give_help_reply=types.InlineKeyboardMarkup(row_width=2)
    give_help_reply.add(types.InlineKeyboardButton("✅ Надати пояснення відповіді", callback_data=f"returnhelp-{subject}-{user_question}"))
    give_help_reply.add(types.InlineKeyboardButton("❌ Не знаю, як допомогти", callback_data=f"canthelp"))
    return give_help_reply
def send_parts(message, ques_len, img_link, reply_markup, question, action):
    if img_link==None:
        if ques_len>=4086:
            bot.send_message(message.chat.id, html_fix(f'{question[:round((ques_len)/2)]}...'), parse_mode='html')
            return html_fix(f'...{question[ques_len-round((ques_len)/2):]}\n{action}')
        else:
            return html_fix(f'{question}\n{action}')
    else:
        if ques_len>=4086:
            bot.send_photo(message.chat.id, img_link, caption=html_fix(f'{question[:round((ques_len)/2)]}'), parse_mode='html')
            return html_fix(f'...{question[ques_len-round((ques_len)/2):]}\n{action}')
        else:
            return html_fix(f'{question}\n{action}')


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        if 'start-' in call.data:
            user_id = call.data.replace('start-', '')
            statuses = ['creator', 'administrator', 'member']
            channel_id = -1001325930135
            permit = False
            for status in statuses:
                if status.lower() == bot.get_chat_member(chat_id=channel_id, user_id=user_id).status.lower():
                    permit = True
                    break
            if permit is False:
                msg = f"❌ Вибачте, але для реєстрації потрібно підписатись на канал, посилання на який ви отримали вище. Після цього використайте /start ще раз."
                bot.send_message(call.message.chat.id, msg, parse_mode='html')
                return
            msg=f'✅ Гаразд. Час розпочинати! Виберіть предмет, тести з якого бажаєте пройти. Ви також зможете змінити предмет, скориставшись командою /changesub.'
            bot.send_message(call.message.chat.id, msg, reply_markup=subjects_reply)
            #sending_new(call.message)
        elif 'new_abitcheck' == call.data:
            take_abiturl(call.message, URL=None)
            bot.delete_message(call.message.chat.id, call.message.message_id)
        elif 'abitcheck-' in call.data:
            take_abiturl(call.message, URL = call.data.replace('abitcheck-', ''))
            bot.delete_message(call.message.chat.id, call.message.message_id)
        elif 'returnhelp-' in call.data:
            #returnhelp-{subject}-{user_question}_{message.chat.id}
            print(call.data)
            fixed_data = call.data.replace('returnhelp-', '')
            subject = fixed_data[:fixed_data.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
            ques_num = fixed_data.replace(subject, '')
            ques_num = int(ques_num[1:])
            helper_chatid = call.message.chat.id
            do_help = bot.send_message(call.message.chat.id, 'Напишіть розгорнуте пояснення нижче.')
            bot.register_next_step_handler(do_help, sending_help, subject, ques_num, helper_chatid)
        elif 'canthelp' in call.data:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        elif 'givehelp-' in call.data:
            print(call.data)
            fixed_data = call.data.replace('givehelp-', '')
            subject = fixed_data[:fixed_data.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
            ques_num = fixed_data.replace(subject, '')
            ques_num = int(ques_num[1:])
            checking_ques(call.message, skipped_ques=None, subject=subject, givinghelp=ques_num)
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        elif 'anicehelp-' in call.data or 'awarn' in call.data or 'aban' in call.data:
            print(call.data)
            action = call.data[:call.data.index('-')]
            fixed_data = call.data.replace(action+'-', '')
            subject = fixed_data[:fixed_data.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
                print(fixed_data)
            ques_num = fixed_data.replace(subject, '')
            ques_num = ques_num[1:ques_num.index('_')]
            helper_chatid = fixed_data[fixed_data.index('_')+1:fixed_data.index('#')]
            warner_chatid = fixed_data[fixed_data.index('#')+1:]
            sql.execute(f"SELECT * FROM helps WHERE chatid = '{warner_chatid}' AND subject = '{subject}' and curques = {ques_num}")
            res = sql.fetchone()
            if res is None:
                return bot.delete_message(call.message.chat.id, call.message.message_id)
            if action == 'anicehelp':
                sql.execute(f"SELECT * FROM helps WHERE subject = '{subject}' AND curques = {ques_num}")
                res=sql.fetchone()
                if res is None:
                    return bot.send_message(call.message.chat.id, f"⚠️ Відповідь на питання вже надано.")
                sql.execute(f"UPDATE helpers SET amount = amount + {1} WHERE chatid = '{helper_chatid}' AND subject = '{subject}'")
                db.commit()
                helper_msg = f"✅ Ваше пояснення до запитання: <b>{sub_to_right(subject)} #{ques_num}</b> зараховано."
                warner_msg = f"👋 Ваш запит до адміністрації стосовно питання: <b>{sub_to_right(subject)} #{ques_num}</b> розглянуто. Адміністрація вирішила зарахувати цю відповідь, як правильну. Питання більше не доступне для інших."
                sql.execute(f"DELETE FROM helps WHERE subject = '{subject}' AND curques = {ques_num}")
                db.commit()
            elif action == 'awarn':
                helper_msg = f"⚠️ Ваше пояснення до запитання: <b>{sub_to_right(subject)} #{ques_num}</b> не зараховано через невідповідність питанню або незрозумілу відповідь. Якщо ваші відповіді систематично взагалі не будуть стосуватися теми, доступ до цієї функції може бути заблокований."
                warner_msg = f"👋 Ваш запит до адміністрації стосовно питання: <b>{sub_to_right(subject)} #{ques_num}</b> розглянуто. Адміністрація вирішила попередити автора про помилку. Ваше питання залишається актуальним для інших."
            elif action == 'aban':
                helper_msg = f"🛑 Ваше пояснення до запитання: <b>{sub_to_right(subject)} #{ques_num}</b> не зараховано через невідповідність питанню або незрозумілу відповідь. Доступ до цієї функції заблокований для вас. Якщо ви побачили помилку, повідомте про це розробнику/адміністратору."
                warner_msg = f"👋 Ваш запит до адміністрації стосовно питання: <b>{sub_to_right(subject)} #{ques_num}</b> розглянуто. Адміністрація вирішила заблокувати автор відповіді. Дякуємо, що повідомили про це нам! Ваше питання залишається актуальним для інших."
                sql.execute(f"UPDATE helpers SET status = 'banned' WHERE chatid = '{helper_chatid}' AND subject = '{subject}'")
                db.commit()
            bot.send_message(helper_chatid, helper_msg, parse_mode='html')
            bot.send_message(warner_chatid, warner_msg, parse_mode='html')
            return bot.send_message(call.message.chat.id, "Дякуємо за працю! Адресати вже отримали повідомлення.")
        elif 'nicehelp-' in call.data or 'notnicehelp-' in call.data or 'badhelp' in call.data:
            #nicehelp-{subject}-{ques_num}_{helper_chatid}
            action = call.data[:call.data.index('-')]
            fixed_data = call.data.replace(action+'-', '')
            subject = fixed_data[:fixed_data.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
            ques_num = fixed_data.replace(subject, '')
            ques_num = ques_num[1:ques_num.index('_')]
            helper_chatid = fixed_data[fixed_data.index('_')+1:]
            sql.execute(f"SELECT * FROM helps WHERE subject = '{subject}' AND curques = {ques_num} AND chatid = '{call.message.chat.id}'")
            check_ques_visibility=sql.fetchone()
            if check_ques_visibility is None:
                bot.send_message(call.message.chat.id, f"⚠️ Ви вже отримали відповідь на запитання.")
            sql.execute(f"SELECT * FROM helpers WHERE chatid = '{helper_chatid}' AND subject = '{subject}'")
            res = sql.fetchone()
            if res is None:
                sql.execute("INSERT INTO helpers VALUES (%s, %s, %s, %s)", (helper_chatid, subject, 0, 'unbanned'))
                db.commit()
            if action == 'nicehelp':
                if check_ques_visibility is None:
                    return
                sql.execute(f"UPDATE helpers SET amount = amount + {1} WHERE chatid = '{helper_chatid}' AND subject = '{subject}'")
                db.commit()
                bot.send_message(helper_chatid, f"👋 Ваше пояснення: <b>{sub_to_right(subject)} - #{ques_num}</b> зараховано, як задовільне, користувачем.", parse_mode='html')
                sql.execute(f"DELETE FROM helps WHERE subject = '{subject}' AND curques = {ques_num} AND chatid = '{call.message.chat.id}'")
                db.commit()
            elif action == 'notnicehelp' or 'badhelp':
                if action == 'notnicehelp':
                    argument = '⚠️ Немає/незрозуміле пояснення до цього питання'
                elif action == 'badhelp':
                    argument = "❌ Текст взагалі не пов'язаний із завданням"
                sql.execute(f"SELECT chatid FROM admins")
                rows = sql.fetchall()
                true_msg = call.message.text[call.message.text.index(')')+1:call.message.text.index('\n\nВи')]
                msg = f'<b>Запит</b>\n<b>Ідентифікатор користувача:</b> {helper_chatid}\n\n<b>Причина:</b> {argument}\n\n<b>Текст пояснення:</b>\n{true_msg}\n\nВиберіть одну з дій для цього запиту.'
                admin_reply = types.InlineKeyboardMarkup(row_width=2)
                admin_reply.add(types.InlineKeyboardButton(f'✅ Відповідь надано вірно (зарахувати її)', callback_data=f'anicehelp-{subject}-{ques_num}_{helper_chatid}#{call.message.chat.id}'))
                admin_reply.add(types.InlineKeyboardButton(f'⚠️ Попередити автора відповіді про порушення', callback_data=f'awarn-{subject}-{ques_num}_{helper_chatid}#{call.message.chat.id}'))
                admin_reply.add(types.InlineKeyboardButton(f'🛑 Заблокувати автора відповіді', callback_data=f'aban-{subject}-{ques_num}_{helper_chatid}#{call.message.chat.id}'))
                for row in rows:
                    am = bot.send_message(row[0], msg, parse_mode='html', reply_markup=admin_reply)
                    checking_ques(am, skipped_ques=None, subject=subject, givinghelp=int(ques_num), admin=True)
            bot.send_message(call.message.chat.id, "Дякуємо за відгук 😉")
        elif 'help-' in call.data:
            print(call.data)
            fixed_data = call.data.replace('help-', '')
            subject = fixed_data[:fixed_data.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
            ques_num = fixed_data.replace(subject, '')
            ques_num = ques_num[1:]
            sql.execute("INSERT INTO helps VALUES (%s, %s, %s)", (call.message.chat.id, subject, ques_num))
            db.commit()
            bot.send_message(call.message.chat.id, "✅ Гаразд! Ваше запитання відправлено. Зачекайте на пояснення від інших користувачів.")
        elif 'globalstatistics-' in call.data:
            subject = call.data.replace('globalstatistics-', '')
            global_statistics_reply=types.InlineKeyboardMarkup(row_width=2)
            for row in subjects_dict:
                global_statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'globalstatistics-{row}'))
            global_statistics_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
            try:
                bot.edit_message_text(text=get_global_statistics(call.message, subject, call), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=global_statistics_reply, parse_mode='html')
            except:
                pass
        elif 'statistics-' in call.data:
            subject = call.data.replace('statistics-', '')
            statistics_reply=types.InlineKeyboardMarkup(row_width=2)
            for row in subjects_dict:
                statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'statistics-{row}'))
            statistics_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
            try:
                bot.edit_message_text(text=get_statistics(call.message, subject, call), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=statistics_reply, parse_mode='html')
            except:
                pass
        elif 'change-' in call.data:
            subject = call.data.replace('change-', '')
            change_sub(call.message, subject)
        elif 'answer-many-' in call.data:
            right_answer=call.data.replace('answer-many-', '', 1)
            right_answer, skipped_ques = callback_check_skipped(right_answer)
            subject = right_answer[:right_answer.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
                right_answer = right_answer.replace("ukraine-history", "")
            right_answer = right_answer[right_answer.index('-')+1:]
            get_answer = bot.send_message(call.message.chat.id, "Яка ваша відповідь? Варіанти відповідей можна надати у будь-якій послідовності.")
            bot.register_next_step_handler(get_answer, sending_many_answer, right_answer, subject, skipped_ques)
        elif 'answer-one-' in call.data:
            right_answer=call.data.replace('answer-one-', '', 1)
            right_answer, skipped_ques = callback_check_skipped(right_answer)
            subject = right_answer[:right_answer.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
                right_answer = right_answer.replace("ukraine-history", "")
            right_answer = right_answer[right_answer.index('-')+1:]
            get_answer = bot.send_message(call.message.chat.id, "Яка ваша відповідь?")
            bot.register_next_step_handler(get_answer, sending_answer, right_answer, subject, skipped_ques)
        elif 'wrong-' in call.data:
            right_answer = call.data.replace('wrong-', '', 1)
            right_answer, skipped_ques = callback_check_skipped(right_answer)
            subject = right_answer[:right_answer.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
                right_answer = right_answer.replace("ukraine-history", "")
            right_answer = right_answer[right_answer.index('-')+1:]
            sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1}, curques = curques + {1} WHERE chatid = '{call.message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(call.message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.", parse_mode='html', reply_markup=get_help_ques(call.message, skipped_ques, subject))
            upd_skipped(call.message, skipped_ques, subject)
            #download_thread = threading.Thread(target=upd_skipped, args=(call.message, skipped_ques, subject,))
            #start_clock(call.message, download_thread)
        elif 'right-' in call.data:
            right_answer = call.data.replace('right-', '', 1)
            right_answer, skipped_ques = callback_check_skipped(right_answer)
            subject = right_answer[:right_answer.index('-')]
            if 'ukraine-history' in call.data:
                subject = 'ukraine-history'
                right_answer = right_answer.replace("ukraine-history", "")
            right_answer = right_answer[right_answer.index('-')+1:]
            sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1}, curques = curques + {1} WHERE chatid = '{call.message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(call.message.chat.id, f"✅ Вітаю, ви вибрали правильну відповідь: <b>{right_answer}</b>.", parse_mode='html')
            #download_thread = threading.Thread(target=upd_skipped, args=(call.message, skipped_ques, subject,))
            #start_clock(call.message, download_thread)
            upd_skipped(call.message, skipped_ques, subject)
        elif 'skip-' in call.data:
            right_answer = call.data.replace('skip-', '', 1)
            subject = right_answer[:right_answer.index('-')]
            right_answer = right_answer[right_answer.index('-')+1:]
            if call.message.text is None:
                msg = call.message.caption
            else:
                msg = call.message.text
            ques_num=msg.replace('Завдання #', '')[:msg.replace('Завдання #', '').index('\n')]
            sql.execute(f"SELECT subject FROM skipped WHERE chatid = '{call.message.chat.id}' AND subject = '{subject}' AND curques = {ques_num}")
            res=sql.fetchone()
            if res is None:
                sql.execute("INSERT INTO skipped VALUES (%s, %s, %s)", (call.message.chat.id, subject, ques_num))
                db.commit()
                sql.execute(f"UPDATE subjects SET skipped_answers = skipped_answers + {1}, curques = curques + {1} WHERE chatid = '{call.message.chat.id}' AND subject = '{subject}'")
                db.commit()
                bot.delete_message(call.message.chat.id, call.message.message_id)
                bot.send_message(call.message.chat.id, f"Запитання пропущено.\nЯк тільки ви будете готові відповісти на нього, використайте команду /skipped.", parse_mode='html')
                sending_new(call.message)
                return
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, f"Запитання пропущено.\nЯк тільки ви будете готові відповісти на нього, використайте команду /skipped.", parse_mode='html')
        elif call.data == 'delme':
            sql.execute(f"DELETE FROM users WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM subjects WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM skipped WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM helps WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM helpers WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM abits WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            sql.execute(f"DELETE FROM abits_checks WHERE chatid = '{call.message.chat.id}'")
            db.commit()
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, f'✅ Ваш акаунт був видалений. Успіхів!')
        elif call.data == 'nodelme':
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, '✅ Добре, коли вам знадобиться це, знов використайте команду /deleteme')
        elif call.data == 'delmsg':
            bot.delete_message(call.message.chat.id, call.message.message_id)
def sending_help(message, subject, ques_num, helper_chatid):
    if message.text=='/cancel':
        return bot.send_message(message.chat.id, f'✅ Добре! Як тільки будете готові відповісти, знову використайте команду /tohelp.')
    helpmsg = message.text
    if helpmsg[-1] != '.':
        helpmsg = helpmsg+'.'
    quality_reply=types.InlineKeyboardMarkup(row_width=2)
    quality_reply.add(types.InlineKeyboardButton('✅ Пояснення повністю задовольняє мене', callback_data=f'nicehelp-{subject}-{ques_num}_{helper_chatid}'))
    quality_reply.add(types.InlineKeyboardButton('⚠️ Немає/незрозуміле пояснення до цього питання', callback_data=f'notnicehelp-{subject}-{ques_num}_{helper_chatid}'))
    quality_reply.add(types.InlineKeyboardButton("❌ Текст взагалі не пов'язаний із завданням", callback_data=f'badhelp-{subject}-{ques_num}_{helper_chatid}'))
    sql.execute(f"SELECT * FROM helps WHERE subject = '{subject}' AND curques = {ques_num}")
    rows = sql.fetchall()
    for row in rows:
        ban_counter=len(rows)
        try:
            ban_counter -= 1
        except:
            sql.execute(f"DELETE FROM helps WHERE chatid = '{row[0]}' AND subject = '{subject}' AND curques = '{ques_num}'")
            db.commit()
        if ban_counter>0:
            bot.send_message(message.chat.id, f"⚠️ На жаль, не всім користувачам надійшло пояснення ({ban_counter}/{len(rows)}), адже доступ до отримання повідомлень від бота був заблокований")
            return
        else:
            bot.send_message(row[0], f'<b>Пояснення ({sub_to_right(subject)} - завдання #{ques_num}</b>)\n<i>{helpmsg}</i>\n\nВи можете оцінити відповідь нижче. Запити розглядаються адміністраторами: ви дізнаєтесь про рішення у повідомленні.', parse_mode='html', reply_markup=quality_reply)
    bot.send_message(message.chat.id, f"✅ Пояснення надіслано! Зачекайте на відгук користувачів.")
def sending_answer(message, right_answer, subject, skipped_ques=None):
    if message.text=='/cancel':
        return bot.send_message(message.chat.id, f'✅ Добре! Як тільки будете готові відповісти, знову натисніть на відповідну кнопку.')
    if message.text.isdigit()==False:
        right_counter=0
        if fix_answer(message.text) is None:
            return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Використовуйте лише українські літери А-Д для відповідей. Спробуйте відповісти ще раз за допомогою команди /resetquestion.")
        for i in range(len(right_answer)):
            try:
                if fix_answer(message.text)[i] == right_answer[i] and subject.lower()!='english':
                    sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
                    db.commit()
                    right_counter+=1
                elif message.text[i] == right_answer[i] and subject.lower()=='english':
                    sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
                    db.commit()
                    right_counter+=1
                else:
                    sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
                    db.commit()
            except IndexError:
                pass
        reply_markup = get_help_ques(message, skipped_ques, subject)
        if right_counter==len(right_answer):
            msg = f"✅ Вітаю, ваша відповідь (<b>{right_answer}</b>) повністю правильна."
            reply_markup=None
        elif right_counter==0:
            msg = f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>."
        else:
            msg = f"✅❌ Ваша відповідь частково правильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.\nЗараховано відповідей: <b>{right_counter}</b>."
        sql.execute(f"UPDATE subjects SET curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
        db.commit()
        bot.send_message(message.chat.id, msg, parse_mode='html', reply_markup=reply_markup)
        #upd_skipped(message, skipped_ques, subject)
    elif message.text.isdigit()==True:
        if message.text.upper() == right_answer:
            sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"✅ Вітаю, ви вибрали правильну відповідь: <b>{right_answer}</b>.", parse_mode='html')
            #upd_skipped(message, skipped_ques, subject)

        else:
            sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.", parse_mode='html')
            #upd_skipped(message, skipped_ques, subject)
    download_thread = threading.Thread(target=upd_skipped, args=(message, skipped_ques, subject,))
    start_clock(message, download_thread)
    

def sending_many_answer(message, right_answer, subject, skipped_ques=None):
    if message.text=='/cancel':
        return bot.send_message(message.chat.id, f'✅ Добре! Як тільки будете готові відповісти, знову натисніть на відповідну кнопку.')
    user_answer = fix_answer(message.text)
    if user_answer is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Використовуйте лише літери А-Д для відповідей. Спробуйте відповісти ще раз за допомогою команди /resetquestion.")
    if subject.lower()=='english':
        user_answer=message.text
    msg_right_answer = ''
    for arow in right_answer:
        msg_right_answer=f'{msg_right_answer}{arow};'
    for row in right_answer:
        if row not in user_answer:
            sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{msg_right_answer}</b>.", parse_mode='html', reply_markup=get_help_ques(message, skipped_ques, subject))
            return
    sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    db.commit()
    bot.send_message(message.chat.id, f"✅ Вітаю, ви вибрали правильну відповідь: <b>{msg_right_answer}</b>.", parse_mode='html')
    #upd_skipped(message, skipped_ques, subject)
    download_thread = threading.Thread(target=upd_skipped, args=(message, skipped_ques, subject,))
    start_clock(message, download_thread)


def sending_new(message):
    time.sleep(5)
    checking_ques(message)

def change_sub(message, subject):
    msg = f'Ви вибрали предмет <b>{subjects_dict[subject]}</b> для тестування.'
    bot.edit_message_text(msg, chat_id=message.chat.id, message_id=message.message_id, parse_mode='html', reply_markup=None)
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    user=sql.fetchone()
    if user is None:
        sql.execute("INSERT INTO users VALUES (%s, %s)", (message.chat.id, subject))
        db.commit()
    else:
        sql.execute(f"UPDATE users SET cursub = '{subject}' WHERE chatid = '{message.chat.id}'")
        db.commit()
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    user_subjects=sql.fetchone()
    if user_subjects is None:
        sql.execute("INSERT INTO subjects VALUES (%s, %s, %s, %s, %s, %s)", (message.chat.id, subject, 0, 0, 0, 1))
        db.commit()
    checking_ques(message)


def subjects_keyboard():
    #subjects_dict={'geography':'Географія', 'ukrainian':'Українська мова та література', 'mathematics':'Математика'}
    global subjects_reply
    subjects_reply=types.InlineKeyboardMarkup(row_width=2)
    for row in subjects_dict:
        subjects_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'change-{row}'))
    subjects_reply.add(types.InlineKeyboardButton("❌", callback_data='delmsg'))
subjects_keyboard()


def sub_to_right(subject):
   if subject in subjects_dict:
        return subjects_dict[subject]
    
def fix_answer(answer):
    true_answer_list = {"a": "а", "b": "б", "c": "в", "d":"г", "e":"д", 'f':'f', 'g':'g', 'h':'h'}
    answer = answer.lower()
    for row in answer:
        if row not in true_answer_list and row not in true_answer_list.values():
            return None
    for row in true_answer_list:
        if row in answer.lower():
            answer = answer.replace(row, true_answer_list[row])
    answer=answer.upper()
    return answer


def check_skipped(skipped_ques):
    if skipped_ques is None:
        return ''
    else:
        return f'_{skipped_ques}'

def callback_check_skipped(right_answer):
    if '_' in right_answer:
        skipped_ques=right_answer[right_answer.index('_')+1:]
        right_answer=right_answer.replace(f'_{skipped_ques}', '')
    else:
        skipped_ques=None
    return right_answer, skipped_ques

def upd_skipped(message, skipped_ques, subject):
    if skipped_ques==None:
        return sending_new(message)
    sql.execute(f"DELETE FROM skipped WHERE chatid = '{message.chat.id}' AND curques = {skipped_ques} AND subject = '{subject}'")
    db.commit()
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}' AND curques = {int(skipped_ques)-1}")
    if sql.fetchone() is None:
        sql.execute(f"UPDATE subjects SET skipped_answers = skipped_answers - {1}, curques = curques - {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
        db.commit()
    else:
        sql.execute(f"UPDATE subjects SET skipped_answers = skipped_answers - {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
        db.commit()

def get_help_ques(message, skipped_ques, subject):
    get_help_reply = types.InlineKeyboardMarkup(row_width=2)
    if skipped_ques==None:
        sql.execute(f"SELECT curques FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
        res = sql.fetchone()
        get_help_reply.add(types.InlineKeyboardButton('⚠️ Чому саме така відповідь?', callback_data=f'help-{subject}-{int(res[0]-1)}'))
    else:
        get_help_reply.add(types.InlineKeyboardButton('⚠️ Чому саме така відповідь?', callback_data=f'help-{subject}-{skipped_ques}'))
    return get_help_reply


    

bot.polling(none_stop=True)