import imaplib
import email
from email.header import decode_header
import pandas as pd
import base64
import datetime
import time
import dill
import geopy
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from geopy import distance

###############################################################################
#Функция обработки одного письма в почте:

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

    # переходим к расшифровке тела письма
    dictionary = {'rooms': [], 'square': [], 'floor': [], 'floors': [], 'address': [],
                  'st_metro': [], 'metro_minutes': [], 'price': [], 'unit_price': [],
                  'balkon': [], 'segment': [], 'repair': [], 'material': [],
                  'day': [], 'month': [], 'year': []}

    # вытащим содержательные данные из тела письма в словарь

    # ВАЖНО! Если в письмах что-то поменяется, это работать перестанет, нужно поддерживать алгоритм,
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


    exception = 0

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

def update_notifications():
    # заготовки будущей таблицы
    start = time.time()
    dictionary = {'rooms': [], 'square': [], 'floor': [], 'floors': [], 'address': [],
                  'st_metro': [], 'metro_minutes': [], 'price': [], 'unit_price': [],
                  'balkon': [], 'segment': [], 'repair': [], 'material': [], 'day': [], 'month': [], 'year': [],
                  'kitchen':[], 'lat':[], 'long':[]}
    df = pd.DataFrame.from_dict(dictionary)

    # зайдем в почту
    username = 'sbor_dannyh_msk@mail.ru'
    mail_pass = 'XZWfpTus7EvTPFhwdAqD'
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

    with open('C:/Users/Sasha/PycharmProjects/hackaton2/df_for_system.pkl', 'rb') as file:
        df_base = dill.load(file)

    df_base = pd.concat([df_base, df], ignore_index=True)

    with open('C:/Users/Sasha/PycharmProjects/hackaton2/df_for_system.pkl', 'wb') as file:
        dill.dump(df_base, file)
    end = time.time()

    return len(df), df_base,(end - start) / 60

#############################################################################
#Подбор аналогов для эталона
def find_analogs(etalon, dist = 1.0, segment = [], rooms = [], repair = [], square = 1000.0, material = [],
                     floor = [], metro_minutes = 30.0):

    with open('C:/Users/Sasha/PycharmProjects/hackaton2/df_for_system.pkl', 'rb') as file:
        df = dill.load(file)
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
       # df1 = df1[df1.metro_minutes <= metro_minutes]

    return df1

##########################################################################################
# Функция, которая будет применяться к каждому из отобранных аналогов эталона для общего расчета уд.цены.
def count_analog_unitprice(etalon, analog):
    unit_price = list(analog['unit_price'])[0]*1

    return analog, unit_price