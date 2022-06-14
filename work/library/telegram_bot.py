__all__ = ['get_telegram_graphs', 'create_telegram_bot', 'set_telegram_params_work', 'work_telegram_bot']

import os
import time
import shutil
import traceback

import pandas as pd

import telebot
from telebot import types
from selenium import webdriver
from selenium.webdriver.common.by import By

SNILS = None
autoupdate_interval = None

flag_autoupdate = False
flag_update_interval = False
flag_SNILS = False
# is_SNILS_exist парсит только по первой странице. Можно доработать


def get_telegram_graphs(final_scores, agreements, BVI_number, all_places):
    '''
    Выводит диаграмму с соотношением ЕГЭшников, олимпиадников, льготников.
    Также выводит график зависимости кол-ва поданных заявлений от кол-ва дней
    :param final_scores: список из суммы баллов по ЕГЭ для каждого абитуриента
    :param agreements: список, содержащий информацию о том, подал ли заявление каждый абитуриент
    :param BVI_number: кол-во олимпиадников
    :param all_places: общее кол-во конкурсных мест
    :return: Функция возвращает None
    '''
    pass


def create_telegram_bot():
    '''
    Создает телеграмм-бота
    :return: обьект, с помощью которого происходит управление ботом
    '''
    bot_token = '5484337995:AAESpTcLKz_vT4-1eHQWaBmlUeYskAr3vSY'
    bot = telebot.TeleBot(bot_token)

    @bot.message_handler(commands=['start'])
    def get_link(message):
        bot.send_message(message.from_user.id, 'Вставьте ссылку на гугл таблицу:')
        bot.register_next_step_handler(message, get_google_sheets)

    def get_google_sheets(message):
        flag_google_sheets = False
        while not os.path.exists('students.xlsx'):
            try:
                website_link = message.text
                parse_website_link(website_link)
            except:
                bot.reply_to(message, "Неправильная ссылка на гугл таблицу.")
                bot.send_message(message.from_user.id, 'Вставьте ссылку на гугл таблицу:')
                bot.register_next_step_handler(message, get_google_sheets)
                break
        if os.path.exists('students.xlsx') and not flag_google_sheets:
            flag_google_sheets = True
            bot.send_message(message.from_user.id, "Введите свой СНИЛС")
            bot.register_next_step_handler(message, get_SNILS)

    def get_SNILS(message):
        global SNILS, flag_SNILS
        SNILS = message.text
        while not is_SNILS_exist():
            bot.reply_to(message, "Ваш СНИЛС отсутствует в списке поступающих")
            get_google_sheets(message)
            break
        if is_SNILS_exist() and not flag_SNILS:
            flag_SNILS = True
            bot.send_message(message.from_user.id, "Хотите добавить автопроверку на изменение вас в списке поступающих?")
            bot.register_next_step_handler(message, set_autoupdate)

    def set_autoupdate(message):
        global autoupdate_interval, flag_autoupdate
        while message.text.strip().lower() not in ['да', 'нет']:
            bot.reply_to(message, "Ответ должен быть 'Да' или 'Нет'")
            bot.register_next_step_handler(message, set_autoupdate)
            break

        if message.text.strip().lower() == 'да' and not flag_autoupdate:
            flag_autoupdate = True
            bot.send_message(message.from_user.id,
                             "Укажите интервал обновления информации в часах/минутах(пример: 1.5ч; 10мин): ")
            bot.register_next_step_handler(message, set_update_interval)
        elif message.text.strip().lower() == 'нет' and not flag_autoupdate:
            flag_autoupdate = True
            autoupdate_interval = 0
            print("ОК")

    def set_update_interval(message):
        global flag_update_interval
        global autoupdate_interval
        while autoupdate_interval is None:
            try:
                bot.reply_to(message, '1')
                bot.register_next_step_handler(message, get_update_interval)
                bot.reply_to(message, '2')
            except:
                bot.reply_to(message, "Неправильный формат данных.")
                bot.register_next_step_handler(message, set_update_interval)
                break

        if (autoupdate_interval is not None) and (not flag_update_interval):
            flag_update_interval = True
            bot.send_message(message.from_user.id,
                "Бот заработал. Чтобы получить актуальную информацию о вашем месте в списке поступающих, напишите комманду /update")

    def get_update_interval(message):
        print("get_update_interval")
        global autoupdate_interval
        interval = message.text
        if interval[-1] == 'ч':
            autoupdate_interval = interval[:-1]
            if autoupdate_interval.find('.') != -1:
                autoupdate_interval = str(float(autoupdate_interval))
                if set(autoupdate_interval.split('.')) == {'0'}:
                    autoupdate_interval = 0
                else:
                    autoupdate_interval = float(autoupdate_interval) * 60
            else:
                autoupdate_interval = int(autoupdate_interval) * 60
        if interval[-3:] == 'мин':
            autoupdate_interval = interval[:-3]
            if autoupdate_interval.find('.') != -1:
                autoupdate_interval = str(float(autoupdate_interval))
                if set(autoupdate_interval.split('.')) == {'0'}:
                    autoupdate_interval = 0
                else:
                    autoupdate_interval = float(autoupdate_interval)
            else:
                autoupdate_interval = int(autoupdate_interval)
        autoupdate_interval = round(autoupdate_interval * 60)
        if autoupdate_interval < 1:
            autoupdate_interval = None
            print(autoupdate_interval)

    @bot.message_handler(commands=['update'])
    def get_update(message):
        bot.send_message(message.from_user.id, "Бот работает")

    @bot.message_handler(func=lambda x: True)
    def welcome_message(message):
        bot.reply_to(message, 'Привет! Это парсер списка поступающих в ВШЭ. Чтобы начать, введите команду /start')

    bot.polling()


def parse_website_link(website_link):
    # website_link = 'https://docs.google.com/spreadsheets/d/11Wci2MHaXvGuokesyxOOcIh_JBT6wH78Zu64pxaPZp8/edit#gid=1109409760'
    path_downloads = fr"{os.path.expanduser('~')}\Downloads\students.xlsx"
    xpath_input_button = "/html/body/div[2]/div[4]/div[1]/div[1]/div[1]"
    xpath_download_button = "//*[@aria-label = 'Скачать d']"
    xpath_download_format_type = "//*[@aria-label='Microsoft Excel (XLSX) x']"

    browser = webdriver.Chrome()
    browser.get(website_link)
    browser.find_element(by=By.XPATH, value=xpath_input_button).click()
    browser.find_element(by=By.XPATH, value=xpath_download_button).click()
    browser.find_element(by=By.XPATH, value=xpath_download_format_type).click()
    while not os.path.exists(path_downloads):
        time.sleep(0.1)
    shutil.move(path_downloads, os.getcwd())


def is_SNILS_exist():
    #удалить след строчку
    return True
    df = pd.read_excel('students.xlsx', sheet_name='Sheet1')
    if SNILS in set(df['СНИЛС'].to_list()):
        return True
    return False


def set_telegram_params_work(auto_update=False):
    '''
    Настраивает работу telegram-бота.
    :param auto_update: параметр равен True, если требуется автообновление данных.
    Для единичного показа статистики параметр должен равняться False.
    P.s. По умолчанию параметр равен False.
    :return: None
    '''
    if auto_update:
        time = get_update_interval()


def work_telegram_bot():
    '''
    Функция, через которую осуществяется управление телеграмм ботом
    :return: None
    '''
    # bot = create_telegram_bot()
    # bot.polling()
create_telegram_bot()
