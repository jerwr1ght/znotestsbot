# -*- coding: utf8 -*-
import telebot
from telebot import types
import config
import psycopg2
import requests
from bs4 import BeautifulSoup
import lxml
import time
global db
global sql
global subjects_dict
subjects_dict={'biology':'Біологія','geography':'Географія', 'ukrainian':'Українська мова та література', 'mathematics':'Математика', 'ukraine-history': 'Історія України'}
db = psycopg2.connect(database='d7vu070ofr61cg', user='ekelorsfyfauek', port="5432", password='f99c8f6fd63dec2d3913c7daef4095819205f44c0d4e19c1ecb63ad495e9b960', host='ec2-54-243-92-68.compute-1.amazonaws.com', sslmode='require')
sql=db.cursor()
sql.execute("""CREATE TABLE IF NOT EXISTS users (chatid TEXT, cursub TEXT)""")
db.commit()
#right_answers INT, wrong_answers INT, skipped_answers INT,
sql.execute("""CREATE TABLE IF NOT EXISTS subjects (chatid TEXT, subject TEXT, right_answers INT, wrong_answers INT, skipped_answers INT, curques INT)""")
db.commit()
sql.execute("""CREATE TABLE IF NOT EXISTS skipped (chatid TEXT, subject TEXT, curques INT)""")
db.commit()
#sql.execute(f"DELETE FROM subjects WHERE subject = 'biology'")
#db.commit()




def last_ques_check(subject):
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"}
    req = requests.get(f'https://zno.osvita.ua/{subject}/list.html', headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    amount_ques = soup.find("div", class_="task-card current").find("div").get_text(strip=True)
    amount_ques = int(amount_ques[len(amount_ques)-4:])
    return amount_ques


bot=telebot.TeleBot(config.TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    sql.execute(f"SELECT * FROM users WHERE chatid = '{message.chat.id}'")
    res=sql.fetchone()
    if res is None:
        msg = 'Вітаю! Дякую, що приєдналися до проходження тестування минулих завдань із ЗНО за допомогою @znotasks_bot. Усі тести зібрані з офіційного сайту освіти України zno.osvita.ua.\n\nЯк тільки ви отримаєте нове завдання, вам буде надана можливість відповісти, натиснувши на відповідну кнопку.\n\nЯкщо ви не знаєте відповіді на запитання, можете натиснути на кнопку "Пропустити". Це завдання буде зберігатися у базі даних до того моменту, поки ви не застосуєте команду /skipped та не дасте відповідь на нього.\n\nУ випадку, коли ви хочете отримати останнє запитання, використайте команду /resetquestion.\n\nВи можете також переглянути статистику ваших відповідей за допомогою /stats та загальну статистику всіх учасників - /globalstats.\n\n<b>Увага!</b> Ваша статистика відповідей доступна тільки вам та не надається адміністраторам боту.\n\n'
        bot.send_message(message.chat.id, msg, parse_mode='html')
        time.sleep(5)
        start_reply = types.InlineKeyboardMarkup(row_width=2)
        start_reply.add(types.InlineKeyboardButton('✅ З інформацією ознайомлений(а)', callback_data='start'))
        msg = 'Якщо ви побачили помилку в певному завданні, можете написати про це розробнику (дивіться опис до цього акаунту).\n\nІснують різні типи завдань.\n\nЯкщо вам пропонується вибрати одну відповідь з варіантів А-Д, вам достатньо натиснути на відповідну кнопку.\n\nУ випадку, коли вам потрібно встановити відповідність між цифрами та варіантами відповідей (літерами), натискайте на кнопку "Відповісти на запитання" і напишіть літери (тільки українські) у правильній послідовності таким чином: гвба або ГВБА (бот розцінює це як 1 - Г, 2 - В, 3 - Б, 4 - А та перевіряє кожний варіант окремо).\n\nЯкщо вам потрібно вибрати лише цифри із переліку, ви можете зробити це в будь-якій послідовності.\n\nОзнайомившись з усією вище зазначеною інформацією, натисніть на кнопку нижче для початку.'
        bot.send_message(message.chat.id, msg, reply_markup=start_reply, parse_mode='html')
    else:
        checking_ques(message)

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
    for row in rows:
        try:
            bot.send_message(row[0], mes, parse_mode='html')
        except:
            pass
    time.sleep(0.5)

@bot.message_handler(commands=['changesub'])
def changing_sub(message):
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
    bot.send_message(message.chat.id, get_statistics(message, subject[0]), parse_mode='html', reply_markup=statistics_reply)

def get_statistics(message, subject, call=None):
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res!=None:
        msg = f'📈 Ваші результати 📈\n\n'
        try:
            msg = f'{msg}<b>{sub_to_right(res[1])}</b>\nВідповідей:\n✅ Правильних - <b>{res[2]}</b>\n❌ Неправильних - <b>{res[3]}</b>\n💨 Пропущених - <b>{res[4]}</b>\n\n🎯 Точність: <b>{round(int(res[2])*100/(int(res[2])+int(res[3])+int(res[4])), 2)}%</b>\n\nЗараз на запитанні: <b>{res[5]}/{last_ques_check(res[1])}</b>\n\n'
        except ZeroDivisionError:
            msg = f'{msg}<b>{sub_to_right(res[1])}</b>\nВідповідей:\n✅ Правильних - <b>{res[2]}</b>\n❌ Неправильних - <b>{res[3]}</b>\n💨 Пропущених - <b>{res[4]}</b>\n\n🎯 Точність: неможливо підрахувати на першому запитанні\n\nЗараз на запитанні: <b>{res[5]}/{last_ques_check(res[1])}</b>\n\n'
        return msg
    else:
        return bot.reply_to(message, f"⚠️ Поки що неможливо отримати загальну статистику.")

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
    bot.send_message(message.chat.id, get_global_statistics(message, subject[0]), parse_mode='html', reply_markup=global_statistics_reply)

def get_global_statistics(message, subject, call=None):
    sql.execute(f"SELECT * FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res is None:
        return bot.reply_to(message, "⚠️ Ви не проходили тести з цього предмету.")

    #sql.execute(f"SELECT * FROM users")
    #users_number = len(sql.fetchall())

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
        accuracy = str(round(int(global_right_answers)*100/(int(global_right_answers)+int(global_wrong_answers)+int(global_skipped_answers)), 2))+'%'
    except ZeroDivisionError: 
        accuracy='поки що неможливо підрахувати'
    msg = f'{msg}<b>{subjects_dict[subject]}</b>\n🌐 Усього учасників: <b>{users_number}</b>\n\nЗагальних відповідей:\n✅ Правильних - <b>{global_right_answers}</b> (<b>{global_right_percents}%</b> ваших)\n❌ Неправильних - <b>{global_wrong_answers}</b> (<b>{global_wrong_percents}%</b> ваших)\n💨 Пропущених - <b>{global_skipped_answers}</b> (<b>{global_skipped_percents}%</b> ваших)\n\n🎯 Загальна точність: <b>{accuracy}</b>\n\n'
    msg = f'📈 Результати учасників 📈\n\n{msg}'
    return msg


#@bot.message_handler(commands=['others'])
#def otherbots(message):
#    msg = f'<b>Усі боти з тестами ЗНО:</b>\n\n• Географія - @geozno_bot\n• Українська мова та література - @ukrlzno_bot'
#    bot.send_message(message.chat.id, msg, parse_mode='html')



def checking_ques(message, skipped_ques=None, subject=None):
    if subject is None:
        sql.execute(f"SELECT cursub FROM users WHERE chatid = '{message.chat.id}'")
        subject = sql.fetchone()
        subject=subject[0]
    sql.execute(f"SELECT curques FROM subjects WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    res=sql.fetchone()
    if res is None:
        return
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
    getting_ques(message, user_question, url, subject, skipped_ques)

def getting_ques(message, user_question, url, subject, skipped_ques=None):
    headers = {"user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"}
    req = requests.get(url, headers=headers)
    soup = BeautifulSoup(req.content, "html.parser")
    form = soup.find('form', {"id":f'q_form_{user_question}'})
    if form is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Повідомте, будь ласка, про це розробнику (контаки в інформації про бота).")
    question = f'<b>Завдання #{user_question}</b>\n'
    for row in form.find("div", class_="question").find_all("p"):
        if row.get_text()=='' or row.get_text()=='\n':
            continue
        question = question + html_fix(row.contents)+'\n'
    action = form.find("div", class_="q-info")
    if action==None:
        action = form.find("div", class_="select-answers-title")
    action = action.get_text(strip=True)

    right_answer=form.find("input", {"type":"hidden", "name":"result"}).get("value")
    if right_answer is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Повідомте, будь ласка, про це розробнику (контаки в інформації про бота).")
    else:
        right_answer = str(right_answer)
    true_answer_list = {"a": "а", "b": "б", "c": "в", "d":"г", "e":"д"}
    for row in true_answer_list:
        if row in right_answer:
            right_answer = right_answer.replace(row, true_answer_list[row])
    right_answer=right_answer.upper()
    answers_list=[]
    items = form.find_all("div", class_="answers")
    if items!=None:
        for item in items:
            for item_answer in item.find_all("div"):
                #print(added_item)
                #print(item_answer.find("span").get_text())
                #added_item=added_item.replace(item_answer.find("span").get_text(), '', 1)
                if item_answer.get('class')[0] == 'quest-title':
                    quest_title=item_answer.contents[0]
                    question = f'{question}\n{quest_title}'
                else:
                    added_items = item_answer.contents
                    number = item_answer.find("span").get_text(strip=True)
                    answers_list.append(number)
                    added_items.remove(item_answer.find("span"))
                    #added_item=item_answer.get_text()
                    added_item=html_fix(added_items)
                    
                    question = f'{question}\n{number}) {added_item}'
            question = question+'\n'
    
    img = form.find("img")
    if img != None:
        img_link = f"zno.osvita.ua{img.get('src')}"
    else:
        img_link=None
    
    lets_answer_markup = types.InlineKeyboardMarkup()
    lets_answer_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-one-{subject}-{right_answer.replace(";", "")}{check_skipped(skipped_ques)}'))
    lets_answer_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
    
    lets_answer_many_markup = types.InlineKeyboardMarkup()
    lets_answer_many_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-many-{subject}-{right_answer.replace(";", "")}{check_skipped(skipped_ques)}'))
    lets_answer_many_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
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
            if img_link==None:
                bot.send_message(message.chat.id, send_parts(message, ques_len, img_link, radio_answer_markup, question, action), parse_mode='html', reply_markup=radio_answer_markup)
            else:
                bot.send_photo(message.chat.id, img_link, caption=send_parts(message, ques_len, img_link, radio_answer_markup, question, action), parse_mode='html', reply_markup=radio_answer_markup)
        else:
            lets_answer_markup = types.InlineKeyboardMarkup()
            lets_answer_markup.add(types.InlineKeyboardButton("Відповісти на запитання", callback_data=f'answer-one-{subject}-{right_answer.replace(";", "").upper()}{check_skipped(skipped_ques)}'))
            lets_answer_markup.add(types.InlineKeyboardButton("Пропустити запитання", callback_data=f'skip-{subject}-{right_answer.replace(";", "")}'))
            radio_answer_markup = None
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
    return added_item

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
        if call.data == 'start':
            msg=f'✅ Гаразд. Час розпочинати! Виберіть предмет, тести з якого бажаєте пройти. Ви також зможете змінити предмет, скориставшись командою /changesub.'
            bot.send_message(call.message.chat.id, msg, reply_markup=subjects_reply)
            #sending_new(call.message)
        elif 'globalstatistics-' in call.data:
            subject = call.data.replace('globalstatistics-', '')
            global_statistics_reply=types.InlineKeyboardMarkup(row_width=2)
            for row in subjects_dict:
                global_statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'globalstatistics-{row}'))
            bot.edit_message_text(text=get_global_statistics(call.message, subject, call), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=global_statistics_reply, parse_mode='html')
        elif 'statistics-' in call.data:
            subject = call.data.replace('statistics-', '')
            statistics_reply=types.InlineKeyboardMarkup(row_width=2)
            for row in subjects_dict:
                statistics_reply.add(types.InlineKeyboardButton(subjects_dict[row], callback_data=f'statistics-{row}'))
            bot.edit_message_text(text=get_statistics(call.message, subject, call), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=statistics_reply, parse_mode='html')
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
            bot.send_message(call.message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.", parse_mode='html')
            upd_skipped(call.message, skipped_ques, subject)
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
        

def sending_answer(message, right_answer, subject, skipped_ques=None):
    if message.text=='/cancel':
        return bot.send_message(message.chat.id, f'✅ Добре! Як тільки будете готові відповісти, знову натисніть на відповідну кнопку.')
    if message.text.isdigit()==False:
        right_counter=0
        if fix_answer(message.text) is None:
            return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Використовуйте лише українські літери А-Д для відповідей. Спробуйте відповісти ще раз за допомогою команди /resetquestion.")
        for i in range(len(right_answer)):
            try:
                if fix_answer(message.text)[i] == right_answer[i]:
                    sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
                    db.commit()
                    right_counter+=1
                else:
                    sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
                    db.commit()
            except IndexError:
                pass
        if right_counter==len(right_answer):
            msg = f"✅ Вітаю, ваша відповідь (<b>{right_answer}</b>) повністю правильна."
        elif right_counter==0:
            msg = f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>."
        else:
            msg = f"✅❌ Ваша відповідь частково правильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.\nЗараховано відповідей: <b>{right_counter}</b>."
        sql.execute(f"UPDATE subjects SET curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
        db.commit()
        bot.send_message(message.chat.id, msg, parse_mode='html')
        upd_skipped(message, skipped_ques, subject)
    elif message.text.isdigit()==True:
        if message.text.upper() == right_answer:
            sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"✅ Вітаю, ви вибрали правильну відповідь: <b>{right_answer}</b>.", parse_mode='html')
            upd_skipped(message, skipped_ques, subject)
        else:
            sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{right_answer}</b>.", parse_mode='html')
            upd_skipped(message, skipped_ques, subject)
    

def sending_many_answer(message, right_answer, subject, skipped_ques=None):
    if message.text=='/cancel':
        return bot.send_message(message.chat.id, f'✅ Добре! Як тільки будете готові відповісти, знову натисніть на відповідну кнопку.')
    user_answer = fix_answer(message.text)
    if user_answer is None:
        return bot.send_message(message.chat.id, "⚠️ З'явилась помилка. Використовуйте лише літери А-Д для відповідей. Спробуйте відповісти ще раз за допомогою команди /resetquestion.")
    msg_right_answer = ''
    for arow in right_answer:
        msg_right_answer=f'{msg_right_answer}{arow};'
    for row in right_answer:
        if row not in user_answer:
            sql.execute(f"UPDATE subjects SET wrong_answers = wrong_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
            db.commit()
            bot.send_message(message.chat.id, f"❌ На жаль, ваша відповідь неправильна.\n✅ Правильна відповідь: <b>{msg_right_answer}</b>.", parse_mode='html')
            return
    sql.execute(f"UPDATE subjects SET right_answers = right_answers + {1}, curques = curques + {1} WHERE chatid = '{message.chat.id}' AND subject = '{subject}'")
    db.commit()
    bot.send_message(message.chat.id, f"✅ Вітаю, ви вибрали правильну відповідь: <b>{msg_right_answer}</b>.", parse_mode='html')
    upd_skipped(message, skipped_ques, subject)


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

subjects_keyboard()


def sub_to_right(subject):
   if subject in subjects_dict:
        return subjects_dict[subject]
    
def fix_answer(answer):
    true_answer_list = {"a": "а", "b": "б", "c": "в", "d":"г", "e":"д"}
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




    

bot.polling(none_stop=True)