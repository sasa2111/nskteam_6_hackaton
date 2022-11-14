import imaplib
import email
from email.header import decode_header
import pandas as pd
import base64
import datetime
import time
import dill
import streamlit as st
import geopy
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim


###############################################################################
#Функция обработки одного письма в почте:
@st.cache
def mail_preparation(msg):
    # вытаскиваем характеристики письма
    letter_date = email.utils.parsedate_tz(msg["Date"])
    header = decode_header(msg["Subject"])[0][0].decode()
    letter_from = msg["Return-path"]
    letter_id = msg["Message-ID"]

    # вытащим тело письма, из которого будем брать информацию об объявлениях
    for part in msg.walk():
        if part.get_content_maintype() == 'text':
            s = base64.b64decode(part.get_payload()).decode()

    # переходим к расшифровке тела письма. Создаем словарь - болванку.
    dictionary = {'rooms': [], 'square': [], 'floor': [], 'floors': [], 'address': [],
                  'st_metro': [], 'metro_minutes': [], 'price': [], 'unit_price': [],
                  'balkon': [], 'segment': [], 'repair': [], 'material': [],
                  'day': [], 'month': [], 'year': []}

    # вытащим содержательные данные из тела письма в этот словарь

    # ВАЖНО! Если в письмах что-то поменяется, это работать перестанет, нужно поддерживать алгоритм.
    # надо следить, что каждый день что-то парсится. Если парсинг прекратился - значит либо беда с рассылкой,
    # либо надо проверить, что поменялось в письмах и под них подстроиться.

    dividing_list = ['color:#04b">', 'style="color:#999">', '&nbsp;</td><td valign="top" >', 'font-weight:bold">',
                     'top:6px;font-size:16px">', ':#999;font-size:13px;">']
    help_dict = {}
    for item in dividing_list:
        data = s.split(item)
        help_dict[item] = []
        for i in range(1, len(data)):
            help_dict[item].append(data[i][:data[i].find('<')])

    # вытащили данные из тела письма списками по разделителям в теле письма.
    # теперь перенесем их в словарь для формирования датафрейма и вытащим туда же данные из темы письма.

    list1 = help_dict['color:#04b">']
    for item in list1:
        # вытащим комнаты объявлений (где указано)
        if item.find('-комн') != -1:
            dictionary['rooms'].append(int(item[0:item.find('-комн')]))
        else:
            dictionary['rooms'].append(0.5)
        # вытащим площадь объявлений
        if item.find('м²') != -1:
            dictionary['square'].append(float(item[item.find(' ') + 1:item.find('м²')]))
        else:
            dictionary['square'].append(0)

        # этаж
        if item.find('этаж') != -1:
            dictionary['floor'].append(int(item[item.find("этаж") + 5:item.find(' из ')]))
        else:
            dictionary['floor'].append(0)

        # общая этажность дома
        if item.find(' из ') != -1:
            dictionary['floors'].append(int(item[item.find(" из ") + 4:]))
        else:
            dictionary['floors'].append(0)

    list1 = help_dict['style="color:#999">']

    # адрес:
    dictionary['address'] = list1
    dictionary12 = dictionary.copy()

    # метро
    list1 = help_dict['&nbsp;</td><td valign="top" >']
    # print(list1)
    for item in list1:
        dictionary['st_metro'].append(item[:item.find(',')])
        if item.find('пешком') != -1:
            dictionary['metro_minutes'].append(int(item[item.find(',') + 1:item.find('мин. ')].replace(' ', '')))
        if item.find('на трансп') != -1:
            dictionary['metro_minutes'].append(int(item[item.find(',') + 1:item.find('мин. ')].replace(' ', '')) * 6)

    #проверка что метро нашлось или заполнение чем-то
    if len(dictionary['metro_minutes']) != len(dictionary['address']):
        dictionary['metro_minutes'] = [1000 for x in range(len(dictionary['address']))]
    if len(dictionary['st_metro']) != len(dictionary['address']):
        dictionary['st_minutes'] = ['н/д' for x in range(len(dictionary['address']))]

    # цену вытащим
    list1 = help_dict['font-weight:bold">']
    for item in list1:
        dictionary['price'].append(int(item[:item.find(' ₽')].replace(' ', '')))

    # удельную цену тащим
    list1 = help_dict['top:6px;font-size:16px">']
    for item in list1:
        dictionary['unit_price'].append(int(item[:item.find(' ₽')].replace(' ', '')))

    # год, месяц, день
    dictionary['day'] = [letter_date[2] for x in range(len(dictionary['price']))]
    dictionary['month'] = [letter_date[1] for x in range(len(dictionary['price']))]
    dictionary['year'] = [letter_date[0] for x in range(len(dictionary['price']))]

    # теперь из фильтров, указанных в теме письма, дополним все остальное -
    # в рамсках одного письма эти данные в объявлениях совпадают

    header_dict = {'вторичка': 'segment', 'новостройка': 'segment', 'монолит': 'material', 'балкон': 'balkon',
                   'панель': 'material', 'кирпич': 'material', 'косметический ремонт': 'repair',
                   'евроремонт': 'repair',
                   'требует ремонта': 'repair', 'до 1989': 'segment'}

    for item in header_dict:
        if header.find(item) != -1:
            dictionary[header_dict[item]] = [item for x in range(len(dictionary['year']))]

    # и поверх на всякий случай отдельные тонкости проверяем
    if header.find('монолит') != -1:
        dictionary['material'] = ['монолит' for x in range(len(dictionary['year']))]

    if header.find('до 1989') != -1:
        dictionary['segment'] = ['старый жилой фонд' for x in range(len(dictionary['year']))]


    exception = 0 #индикатор ошибки парсинга

    # запишем вседанные из письма в датафрейм, если все хорошо спарсилось
    try:
        df = pd.DataFrame.from_dict(dictionary)
    except ValueError:
        # если где-то в письме что-то не смогло спарситься (не заполнено метро, не так что-то указано),
        #и из-за этого словарь не смог конвертироваться в датафрейм, тогда
        # сносим все письмо - то есть потеряем от 1 до 5 объявлений. Иначе будет утеря нескольких десятков объявл.
        # т.к. данный вид парсинга может выдавать огромный спектр несоответствий, все их автоматом не отследить
        # пока основная масса писем парсится - есть смысл делать так.

        exception = 1
        dictionary = {'rooms': [], 'square': [], 'floor': [], 'floors': [], 'address': [],
                      'st_metro': [], 'metro_minutes': [], 'price': [], 'unit_price': [],
                      'balkon': [], 'segment': [], 'repair': [], 'material': [],
                      'day': [], 'month': [], 'year': []}
        df = pd.DataFrame.from_dict(dictionary) #пустой датафрейм

    #если ошибок не было и датафрейм сгенерился:
    if exception ==0:

        # считаем, что кухня занимает 20% от общей площади
        df['kitchen'] = df.square*0.2

        #и координаты расположения подкачаем - если адрес распознается
        geolocator = Nominatim(user_agent="my_small_project")
        geocode = RateLimiter(geolocator.geocode)
        c = [] #списком подкачаем геолокацию по адресам (убраны мешающие слова, которые сбивают геолокатор)
        for i in df.index:
            c.append(geocode(df.loc[i, 'address'].replace('жилищный комплекс', '')\
                                .replace('ЖК', '').replace('поселок', '').replace('пос.','').replace('г.','')\
                                .replace('поселение', '').replace('жилой комплекс', '').replace('д.', '').replace('ул.','')))
        diction = {'c': c} #из списка подготовим словарь, который далее станет датафреймом
        df_help = pd.DataFrame.from_dict(diction)
        df['coord'] = df_help.c #добавим вспом. столбик в наш датафрейм
        df['lat'] = df.apply(lambda x: x.coord[1][0] if x.coord != None else 0, axis=1)
        df['long'] = df.apply(lambda x: x.coord[1][1] if x.coord != None else 0, axis=1)
        df.drop('coord', axis=1, inplace=True)
        df = df.drop_duplicates()
    else:
        #случай, когда ранее ошибка выскочила - в пустом датафрейме поля все равно должны совпадать
        df['kitchen'] = None
        df['lat'] = None
        df['long'] = None

    return df, letter_date, header, letter_from, letter_id




#################################################################################
# функция для обработки всех непрочитанных писем в почте и объединения их в одну таблицу
#@st.cache
def update_notifications():
    # заготовки будущей таблицы
    start = time.time()
    dictionary = {'rooms': [], 'square': [], 'floor': [], 'floors': [], 'address': [],
                  'st_metro': [], 'metro_minutes': [], 'price': [], 'unit_price': [],
                  'balkon': [], 'segment': [], 'repair': [], 'material': [], 'day': [], 'month': [], 'year': [],
                  'kitchen':[], 'lat':[], 'long':[]}
    df = pd.DataFrame.from_dict(dictionary)

    # зайдем в почту (реквизиты настоящей почты скрыла, т.к. публичный доступ)
    username = 'nekaya_pochta@mail.ru'
    mail_pass = 'набор_символов'
    imap_server = "imap.mail.ru"
    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(username, mail_pass)

    # зайдем в нужную папку
    imap.select("INBOX/Appartments")

    # посмотрим последние непрочитанные письма (номера)
    numbers = imap.search(None, "Unseen")[1]
    ids = numbers[0].split()

    # теперь идем по всем непрочитанным письмам, читаем их и обрабатываем
    for i in ids:
        res, msg = imap.fetch(i, '(RFC822)')
        msg = email.message_from_bytes(msg[0][1])
        df1 = mail_preparation(msg)[0]  # датафрейм из объявлений данного письма
        df = pd.concat([df, df1], ignore_index=True)

    df = df[['segment', 'address', 'repair', 'balkon', 'rooms', 'st_metro',
       'metro_minutes', 'square', 'kitchen', 'floor', 'floors', 'material',
       'price', 'unit_price', 'day', 'month', 'year', 'lat', 'long']]

    with open('./df_for_system.pkl', 'rb') as file:
        df_base = dill.load(file)

    df_base = pd.concat([df_base, df], ignore_index=True)


    with open('./df_for_system.pkl', 'wb') as file:
        dill.dump(df_base, file)
    end = time.time()

    return len(df), df_base, (end - start) / 60

#############################################################################
#Подбор аналогов для эталона
@st.cache
def find_analogs(etalon, dist = 1.0, segment = [], rooms = [], repair = [], square = 1000.0, material = [],
                     floor = [], metro_minutes = 30.0):

   # with open('./df_for_system.pkl', 'rb') as file:
    file = './df_for_system.pkl'
       # df = dill.load(file)
    df = pd.read_pickle(file)
        # строковые данные н/д в столбце придется заменить на 1000, чтобы сохранить элемент в выдаче
    df.loc[df.metro_minutes == 'н/д', 'metro_minutes'] = 1000
    etalon_coord = (etalon.loc[0, 'lat'], etalon.loc[0, 'lon'])
    df1 = df[(abs(df.lat - etalon.loc[0, 'lat']) < 0.009009009009 * dist) & (abs(df.long - etalon.loc[0, 'lon']) < 0.009009009009 * dist)]
    df1 = df1.rename(columns={'long':'lon'})

    if len(segment) > 0:
        df1 = df1[df1.segment.isin(segment)]
    if len(rooms) > 0:
        df1 = df1[df1.rooms.isin(rooms)]
    if len(repair) > 0:
        df1 = df1[df1.repair.isin(repair)]
    if len(material) > 0:
        df1 = df1[df1.material.isin(material)]

    if len(floor) > 0:
        df1['floor_type'] = df1.apply(lambda x: 'первый' if x.floor == 1
        else ('последний' if x.floor == x.floors else 'средний'), axis = 1)
        df1 = df1[df1.floor_type.isin(floor)]

    df1 = df1[(df1.square < square + etalon.loc[0,'Площадь квартиры, кв.м'])&((df1.square > -square + etalon.loc[0,'Площадь квартиры, кв.м']))]
    df1 = df1[df1.metro_minutes <= metro_minutes]


    return df1

##########################################################################################
# Функция, которая будет применяться к каждому из отобранных аналогов эталона для общего расчета уд.цены.
@st.cache
def count_analog_unitprice(etalon, analog,i):
    unit_price = list(analog['unit_price'])[0]*1

    # Матрицы корректировок:
    corr_torg = -0.045

    corr_floor = pd.DataFrame.from_dict({'etalon':['первый', 'средний', 'последний'],
                                         'первый': [0.0, 0.075, 0.032],
                                         'средний': [-0.07, 0.0, -0.04],
                                         'последний': [-0.31, 0.042, 0.0]})


    corr_square_cat = pd.DataFrame.from_dict({'etalon':['<30', '30-50', '50-65', '65-90', '90-120', '>120'],
                                              '<30':[0.0, -0.06, -0.12, -0.17, -0.22, -0.24],
                                              '30-50':[0.06, 0.0, -0.07, -0.12, -0.17, -0.19],
                                              '50-65':[0.14, 0.07, 0.0, -0.06, -0.11, -0.13],
                                              '65-90':[0.21, 0.14, 0.06, 0.0, -0.06, -0.08],
                                              '90-120':[0.28, 0.21, 0.13, 0.06, 0.0, -0.03],
                                              '>120':[0.31, 0.24, 0.16, 0.09, 0.03, 0.0]})
    corr_kitchen_cat = pd.DataFrame.from_dict({'etalon':['<7', '7-10', '>10'],
                                               '<7':[0.0, 0.03, 0.09],
                                               '7-10':[-0.029, 0.0, 0.058],
                                               '>10':[-0.083, -0.055, 0.0]})
    corr_balkon = -0.05 #в наших данных всегда либо четко указан балкон, либо мы не знаем.
    # если не знаем - считаем, что балкон есть по умолчанию. То есть среди аналогов тут всегда "да".
    # Поэтому по балкону в системе либо не будет корректировки. Либо на случай, если у эталона балкона нет.

    corr_metro = pd.DataFrame.from_dict({'etalon':['<5', '5-10', '10-15', '15-30', '30-60', '>60'],
                                         '<5':[0.0, -0.07, -0.11, -0.15, -0.19, -0.22],
                                         '5-10': [0.07, 0.0, -0.04, -0.08, -0.13, -0.17],
                                         '10-15': [0.12, 0.04, 0.0, -0.05, -0.1, -0.13],
                                         '15-30': [0.17, 0.09, 0.05, 0.0, -0.06, -0.09],
                                         '30-60': [0.24, 0.15, 0.11, 0.06, 0.0, -0.04],
                                         '>60': [0.29, 0.2, 0.15, 0.1, 0.04, 0.0]})
    corr_repair = pd.DataFrame.from_dict({'etalon':['Без отделки', 'Муниципальный ремонт', 'Современный ремонт'],
                                          'требует ремонта':[0, 13400, 20100],
                                          'косметический ремонт':[-13400, 0, 6700],
                                          'евроремонт':[-20100, -6700, 0]})

    #некоторые сокращения:
    etalon_floor_type = etalon.loc[0, 'floor_type']
    etalon_sq_cat = etalon.loc[0, 'sq_category']
    etalon_kitchen_type = etalon.loc[0, 'kitchen_category']
    etalon_balkon_type = etalon.loc[0, 'Наличие балкона/лоджии']
    etalon_metro_min = etalon.loc[0, 'metro_min_cat']
    etalon_repair = etalon.loc[0,'Состояние']

    # добавляем корректировки (проценты для конкретного аналога)
    # на торг
    analog['corr_torg'] = corr_torg
    # на этаж
    analog['corr_floor_type'] = analog.apply(lambda x: corr_floor[corr_floor.etalon == etalon_floor_type]\
                                             [x.floor_type],axis = 1)
    # на площадь
    analog['corr_square_cat'] = analog.apply(lambda x: corr_square_cat[corr_square_cat.etalon == etalon_sq_cat]\
        [x.sq_category], axis=1)

    # На кухню
    analog['corr_kitchen_cat'] = analog.apply(lambda x: corr_kitchen_cat[corr_kitchen_cat.etalon == etalon_kitchen_type] \
        [x.kitchen_category], axis=1)

    # корр. на балкон (у аналогов он всегда есть, либо н/д --> тоже есть (считаем так)
    # Поэтому тут либо 0 будет, либо по таблице -5%
    analog['corr_balkon'] = analog.apply( lambda x: corr_balkon if etalon_balkon_type.lower() == "нет"
                                          else 0, axis = 1)

    #корректировки метро (время пешком)
    analog['corr_metro_min'] = analog.apply(lambda x: corr_metro[corr_metro.etalon == etalon_metro_min]\
        [x.metro_min_cat], axis=1)

    # на ремонт.
    #если в аналоге нет данных по ремонту (н/д), то считаем, что в нем нет ремонта (требует ремонта)
    analog['corr_repair'] = analog.apply(lambda x: corr_repair[corr_repair.etalon == etalon_repair][x.repair] if x.repair!='н/д'
                                         else corr_repair[corr_repair.etalon == etalon_repair]['требует ремонта'], axis=1)

    #для каждого аналога считаем скорректированную цену
    analog['corr_unit_price'] = analog.unit_price * (1+analog.corr_torg)*(1+analog.corr_floor_type)* \
                                (1+analog.corr_square_cat)*(1+analog.corr_kitchen_cat)*(1+analog.corr_balkon)* \
                                (1+analog.corr_metro_min)+analog['corr_repair']

    return analog


############################################################################
# Функция расчета пула
@st.cache
def count_pool_unitprice(etalon, pool, i):
    # некоторые сокращения:
    etalon_floor_type = etalon.loc[0, 'floor_type']
    etalon_sq_cat = etalon.loc[0, 'sq_category']
    etalon_kitchen_type = etalon.loc[0, 'kitchen_category']
    etalon_balkon_type = etalon.loc[0, 'Наличие балкона/лоджии']
    etalon_metro_min = etalon.loc[0, 'metro_min_cat']
    etalon_repair = etalon.loc[0, 'Состояние']

    # Матрицы корректировок:
    corr_torg = -0.045

    corr_floor = pd.DataFrame.from_dict({'pool': ['первый', 'средний', 'последний'],
                                         'первый': [0.0, 0.075, 0.032],
                                         'средний': [-0.07, 0.0, -0.04],
                                         'последний': [-0.31, 0.042, 0.0]})

    corr_square_cat = pd.DataFrame.from_dict({'pool': ['<30', '30-50', '50-65', '65-90', '90-120', '>120'],
                                              '<30': [0.0, -0.06, -0.12, -0.17, -0.22, -0.24],
                                              '30-50': [0.06, 0.0, -0.07, -0.12, -0.17, -0.19],
                                              '50-65': [0.14, 0.07, 0.0, -0.06, -0.11, -0.13],
                                              '65-90': [0.21, 0.14, 0.06, 0.0, -0.06, -0.08],
                                              '90-120': [0.28, 0.21, 0.13, 0.06, 0.0, -0.03],
                                              '>120': [0.31, 0.24, 0.16, 0.09, 0.03, 0.0]})
    corr_kitchen_cat = pd.DataFrame.from_dict({'pool': ['<7', '7-10', '>10'],
                                               '<7': [0.0, 0.03, 0.09],
                                               '7-10': [-0.029, 0.0, 0.058],
                                               '>10': [-0.083, -0.055, 0.0]
                                               })
    corr_balkon = pd.DataFrame.from_dict({'pool':['Нет', 'Да'],
                                          'Нет':[0.0, 0.053],
                                          'Да':[-0.05, 0.0]
                                          })

    corr_metro = pd.DataFrame.from_dict({'pool': ['<5', '5-10', '10-15', '15-30', '30-60', '>60'],
                                         '<5': [0.0, -0.07, -0.11, -0.15, -0.19, -0.22],
                                         '5-10': [0.07, 0.0, -0.04, -0.08, -0.13, -0.17],
                                         '10-15': [0.12, 0.04, 0.0, -0.05, -0.1, -0.13],
                                         '15-30': [0.17, 0.09, 0.05, 0.0, -0.06, -0.09],
                                         '30-60': [0.24, 0.15, 0.11, 0.06, 0.0, -0.04],
                                         '>60': [0.29, 0.2, 0.15, 0.1, 0.04, 0.0]})
    corr_repair = pd.DataFrame.from_dict({'pool': ['Без отделки', 'Муниципальный ремонт', 'Современный ремонт'],
                                          'Без отделки': [0, 13400, 20100],
                                          'Муниципальный ремонт': [-13400, 0, 6700],
                                          'Современный ремонт': [-20100, -6700, 0]})
    # добавляем корректировки (проценты для конкретного аналога)
    # на торг корректировку не добавляем, т.к. в эталоне она уже применялась при расчете цены


    # на этаж
    pool['corr_floor_type'] = pool.apply(lambda x: corr_floor[corr_floor.pool == x.floor_type] \
        [etalon_floor_type], axis=1)
    # на площадь
    pool['corr_square_cat'] = pool.apply(lambda x: corr_square_cat[corr_square_cat.pool == x.sq_category] \
        [etalon_sq_cat], axis=1)

    # На кухню
    pool['corr_kitchen_cat'] = pool.apply(lambda x: corr_kitchen_cat[corr_kitchen_cat.pool == x.kitchen_category] \
        [etalon_kitchen_type], axis=1)

    # корр. на балкон
    pool['corr_balkon'] = pool.apply(lambda x: corr_balkon[corr_balkon.pool == x['Наличие балкона/лоджии']]\
        [etalon_balkon_type], axis=1)

    # корректировки метро (время пешком)
    pool['corr_metro_min'] = pool.apply(lambda x: corr_metro[corr_metro.pool == x.metro_min_cat] \
        [etalon_metro_min], axis=1)
    # на ремонт
    pool['corr_repair'] = pool.apply(lambda x: corr_repair[corr_repair.pool == x['Состояние']][etalon_repair], axis=1)

    pool['unit_price'] = etalon.loc[0, 'unit_price'] * (1 + pool.corr_floor_type) * \
                         (1 + pool.corr_square_cat) * (1 + pool.corr_kitchen_cat) * \
                         (1 + pool.corr_balkon) *(1 + pool.corr_metro_min) + \
                         pool['corr_repair']
    return pool
