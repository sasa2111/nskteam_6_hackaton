#import openpyxl
import streamlit as st
import pandas as pd

from modules import update_notifications
from modules import find_analogs
from modules import count_analog_unitprice
from modules import count_pool_unitprice
import datetime

from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim


st.set_page_config(page_title="Сервис расчета рыночной стоимости жилой недвижимости г.Москвы",
                   page_icon=":house_buildings:",
                   layout="wide")
st.title(":house_buildings: Сервис расчета рыночной стоимости жилой недвижимости г.Москвы")

#name_indicator =True
#name = st.text_input('Укажите свое ФИО для сохранения полученной оценки в файл')
#dfh = pd.read_excel('C:/Users/Sasha/PycharmProjects/hackaton2/sample_for_user.xlsx') #вспомогательный датафрейм
# заготовка для будущих оценок, позже он перезапишется.
#dfh.to_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/etalon_{name}.xlsx')
st.subheader("ШАГ 1. Загрузить пул объектов и найти координаты эталона:")


file = st.file_uploader('Загрузите таблицу для оценки xlsx: ', key = 'file')

if file is None:
    st.write('Ниже пример файла для загрузки. ','\n',
             'Для студии - число комнат указать 0.5, '
             'для свободной планировки/пентхауса/аппартаментов (где не указано) - 0.','\n',
             'В поле Эталон - указать один эталонный объект - 1, остальные - 0.')
    sample = pd.read_excel('C:/Users/Sasha/PycharmProjects/hackaton2/sample_for_user.xlsx')
    sample.loc[sample['Количество комнат'] == 'Студия', 'Количество комнат'] = 0.5
    st.write(sample)
if file is not None:
    st.write(file)
    df1 = pd.read_excel(file)
    st.write('Вы загрузили:')
    st.dataframe(df1)
    st.subheader("Найти координаты эталона")
    find_etalon = st.button('Найти координаты эталона:')


    if find_etalon:

        st.write('Ищем координаты местоположения эталона...')
        geolocator = Nominatim(user_agent="my_small_project")
        geocode = RateLimiter(geolocator.geocode)

    #Если координаты подкачиваются, то запишем их в таблицу и выведем на экран
        addressfind = (df1.loc[df1['Эталон'] == 1, 'Местоположение']).str.replace('жилищный комплекс', '') \
                              .str.replace('ЖК', '').str.replace('поселок', '').str.replace('пос.', '').str.replace('г.','')\
                              .str.replace('поселение', '').str.replace('жилой комплекс', '').str.replace('д.','').str.replace('ул.','')

        df1['short_address'] = None
        df1['lat'] = None
        df1['lon'] = None
        df1.loc[df1['Эталон'] == 1, 'short_address'] = addressfind
        #df1 = df1.copy()
        #st.write(geocode(addressfind.tolist())[1])
        if geocode(addressfind.tolist()) != None:
            coords = geocode(addressfind.tolist())[1]
            if len(coords) > 0:
                st.write('Координаты найдены!')
                df1.loc[df1['Эталон'] == 1, 'lat'] = coords[0]
                df1.loc[df1['Эталон'] == 1, 'lon'] = coords[1]
                st.write(df1[df1['Эталон'] == 1][['Местоположение','lat','lon','short_address']])
                df1.to_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/etalon.xlsx')
                st.map(df1[df1['Эталон'] == 1][['lat', 'lon']])



        else:
            st.write('Не удалось подкачать координаты эталона.')
            st.write('Вы можете перезагрузить файл с эталоном, изменив написание адреса эталона или изменив эталон.')

st.subheader('ШАГ 2. Поиск аналогов для эталона в указанном радиусе')
with st.form('data'):
    st.write('Укажите фильтры для поиска аналогов.')
    cols = st.columns(4)
    #выбор радиуса поиска объявлений
    dist = cols[0].number_input('Выберите радиус поиска, км: ', min_value = 1.0)

    #далее пользователь набирает параметры - они сохраняются списками:
    segment = cols[1].multiselect('Сегмент:', ['новостройка', 'вторичка', 'старый жилой фонд'])
    rooms = cols[2].multiselect('Число комнат (студия - 0.5, св.план./пентх./аппартам. - 0):', [0,0.5, 1,2,3,4,5,6,7])
    repair = cols[3].multiselect('Состояние ремонта:', ['требует ремонта', 'косметический ремонт', 'евроремонт'])

    square = cols[0].number_input("Допустимое отличие по площади, м2", min_value=0.0, value = 40.0)
    material = cols[1].multiselect('Материал:', ['кирпич', 'монолит', 'панель'])
    floor =  cols[2].multiselect('Тип этажа', ['первый', 'последний', 'средний'])
    metro_minutes = cols[3].number_input("Время до метро пешком (до N мин.)", value=1000.0, min_value = 3.0)

    submitted = st.form_submit_button(label="Подобрать аналоги")

    if submitted:

        #etalon = pd.read_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/etalon_{name}.xlsx').drop(
            #['short_address', 'Unnamed: 0'], axis=1)
        etalon = pd.read_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/etalon.xlsx')
        etalon = etalon[etalon['Эталон'] == 1]
        st.write('Данные эталона:', etalon)

       #запускаем функцию поиска аналогов для эталона по выбранным фильтрам
        analogs = find_analogs(etalon, dist=dist, segment=segment, rooms=rooms, repair=repair,
                     square=square, material=material, floor=floor, metro_minutes=metro_minutes)

        st.write(f'Найдено {len(analogs)} аналогов:')
        st.dataframe(analogs)
        coordinates = pd.concat([analogs[['lat', 'lon']],etalon[['lat', 'lon']]])
        st.write('На карте изображены аналоги и эталон. Более яркий цвет означает, что в этой точке больше объектов.')
        st.map(coordinates)
        analogs.to_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/analogs.xlsx')


st.subheader('ШАГ 3. Расчет удельной стоимости')

#даем возможность пользователю корректировать подбор расчет:
with st.form('count'):
    st.write('Настройте параметры расчета:')
    cols = st.columns(4)
    #выбор радиуса поиска объявлений
    analogs = pd.read_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/analogs.xlsx')
    etalon = pd.read_excel(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/etalon.xlsx')

    etalon['floor_type'] = etalon.apply(lambda x: 'первый' if x['Этаж расположения'] == 1
    else ('последний' if x['Этаж расположения'] == x['Этажность дома'] else 'средний'), axis=1)

    etalon['sq_category'] = etalon.apply(lambda x: '<30' if x['Площадь квартиры, кв.м'] < 30
    else ('30-50' if x['Площадь квартиры, кв.м'] < 50 else ('50-65' if x['Площадь квартиры, кв.м'] < 65 else (
        '65-90' if x['Площадь квартиры, кв.м'] < 90 else ('90-120' if x['Площадь квартиры, кв.м'] < 120 else
                                                          '>120')))), axis=1)

    etalon['kitchen_category'] = etalon.apply(lambda x: '<7' if (
            ((x['Площадь кухни, кв.м'] < 7) & (x['Площадь кухни, кв.м'] != 0)) |
            ((x['Площадь кухни, кв.м'] == 0) & (x['Площадь квартиры, кв.м'] * 0.2 < 7))) \
        else ('7-10' if (((x['Площадь кухни, кв.м'] < 10) & (x['Площадь кухни, кв.м'] != 0)) |
                         ((x['Площадь кухни, кв.м'] == 0) & (x['Площадь квартиры, кв.м'] * 0.2 < 10)))
              else '>10'), axis=1)

    etalon['metro_min_cat'] = etalon.apply(lambda x: '<5' if x['Удаленность от станции метро, мин. пешком'] < 5
    else ('5-10' if x['Удаленность от станции метро, мин. пешком'] < 10
          else ('10-15' if x['Удаленность от станции метро, мин. пешком'] < 15
                else ('15-30' if x['Удаленность от станции метро, мин. пешком'] < 30
                      else ('30-60' if
                            x['Удаленность от станции метро, мин. пешком'] < 60
                            else '>60')))), axis=1)


    pool = etalon.copy() #Общий пул объектов всё вместе с эталоном
    etalon = etalon[etalon['Эталон'] == 1].drop('Unnamed: 0', axis=1)  # выделяем эталон
    del_objects = cols[0].multiselect('Укажите аналоги, которые надо убрать из расчета: ', list(analogs['Unnamed: 0']))
    name = cols[1].text_input('Укажите свое ФИО для сохранения расчетов')
    #далее пользователь набирает параметры - они сохраняются списками:
    #segment = cols[1].multiselect('Сегмент:', ['новостройка', 'вторичка', 'старый жилой фонд'])
    #rooms = cols[2].multiselect('Число комнат (студия - 0.5, св.план./пентх./аппартам. - 0):', [0,0.5, 1,2,3,4,5,6,7])
    #repair = cols[3].multiselect('Состояние ремонта:', ['требует ремонта', 'косметический ремонт', 'евроремонт'])

    submitted1 = st.form_submit_button(label="Посчитать удельную стоимость и общую рыночную стоимость")

    if submitted1:
        #удаляем из аналогов те, которые пользователь указал
        analogs_corrected = analogs[analogs['Unnamed: 0'].isin(del_objects) == False]

        #добавляем к аналогам параметры, которые важны для подбора корректировок
        analogs_corrected['floor_type'] = analogs_corrected.apply(lambda x: 'первый' if x.floor == 1
        else ('последний' if x.floor == x.floors else 'средний'), axis=1)

        analogs_corrected['sq_category'] = analogs_corrected.apply(lambda x: '<30' if x['square'] < 30
        else ('30-50' if x['square'] < 50 else ('50-65' if x['square'] < 65 else (
            '65-90' if x['square'] < 90 else ('90-120' if x['square'] < 120 else '>120')))), axis=1)

        # не все данные содержат инфо о кухне. Есть много квартир, у которых не указана площадь кухни.
        # для таких квартир считаем, что кухня 20% от общей площади и категорию кухни для коэффициента берем
        # из такого расчета. Пользователь может эти квартиры вручную из расчета убрать по номерам (где метры 0)

        analogs_corrected['kitchen_category'] = analogs_corrected.apply(lambda x: '<7' if (
                    ((x['kitchen'] < 7)&(x['kitchen']!=0))|((x['kitchen'] == 0) & (x['square'] * 0.2 < 7)))\
            else ('7-10' if (((x['kitchen'] < 10)&(x['kitchen'] != 10) )|
                             ((x['kitchen'] == 0) & (x['square'] * 0.2 < 10)))
                      else '>10'), axis = 1)

        analogs_corrected['metro_min_cat'] = analogs_corrected.apply(lambda x: '<5' if x['metro_minutes'] < 5
        else ('5-10' if x['metro_minutes'] < 10
              else ('10-15' if x['metro_minutes'] < 15
                    else ('15-30' if x['metro_minutes'] < 30
                          else ('30-60' if
                                x['metro_minutes'] < 60
                                else '>60')))), axis = 1)

        #st.write('Сокращенный список аналогов:')
        #st.write(analogs_corrected) #сокращенный список аналогов для расчета

        #теперь для каждого аналога корректируем по таблицам unit_price
        analogs_new = pd.DataFrame()
        for i in list(analogs_corrected['Unnamed: 0']):
            analog = count_analog_unitprice(etalon, analogs_corrected[analogs_corrected['Unnamed: 0'] == i],i)
            analogs_new = pd.concat([analogs_new, analog])

        corr_unit_price_mean = analogs_new['corr_unit_price'].mean()

        st.write('Аналоги с процентами корректировок:')
        st.write(analogs_new)
        etalon['unit_price'] = corr_unit_price_mean
        etalon['price'] = etalon.unit_price*etalon['Площадь квартиры, кв.м']
        st.markdown(f"Эталон:")
        st.write(etalon, 'Стоимость эталона и удельная цена:',
                 etalon[['Местоположение', 'Площадь квартиры, кв.м', 'unit_price', 'price']])


        pool_new = pd.DataFrame()
        for i in list(pool['Unnamed: 0']):
            pool_item = count_pool_unitprice(etalon, pool[pool['Unnamed: 0'] == i], i)
            pool_new = pd.concat([pool_new, pool_item])
        pool_new['price'] = pool_new.unit_price*pool_new['Площадь квартиры, кв.м']


        pool_new['сотрудник'] = name
        date_time = datetime.datetime.now()
        pool_new['дата оценки'] = date_time
        st.write(pool_new)
        analogs_new['сотрудник'] = name
        analogs_new['дата оценки'] = date_time

        with pd.ExcelWriter(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/Оценка_пула_данных.xlsx') as writer:
            pool_new.to_excel(writer, sheet_name='pool')
            analogs_new.to_excel(writer, sheet_name='analogs_for_etalon')




with open(f'C:/Users/Sasha/PycharmProjects/hackaton2/userdata/Оценка_пула_данных.xlsx', "rb") as file:
    btn = st.download_button(label = 'Скачать данные об оценке',
                            data = file,
                            file_name=f'Оценка_пула_данных_{name}.xlsx',
                            mime="application/vnd.ms-excel")


with open("C:/Users/Sasha/PycharmProjects/hackaton2/update.txt", "r") as file:

    text = file.read()

st.write(f'Последнее обновление данных об объявлениях в системе: {text}')
if st.button('Подгрузить новые объявления в систему'):
    st.write('Процесс загрузки данных... может занять несколько минут.')
    with open("C:/Users/Sasha/PycharmProjects/hackaton2/update.txt", "w") as file:
        file.write(f"{datetime.datetime.now()}")
    leng, df_upd, minutes = update_notifications()


    df_upd.to_excel('df_for_system.xlsx')
    st.write(f'Подгрузка новых данных заняла {minutes} мин.')
    if leng >0:
        st.write(f'Загружено {leng} новых объявлений. Всего объявлений в базе: {len(df_upd)}. ')
    else:
        st.write('Новых объявлений нет. Рекомендуем обновить данные через несколько часов.')


