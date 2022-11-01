import streamlit as st
import pandas as pd
import numpy as np
import dill
from modules import update_notifications
from modules import find_analogs
from modules import count_analog_unitprice
import datetime
#from sklearn.pipeline import Pipeline
#from sklearn.preprocessing import FunctionTransformer
#from catboost import CatBoostClassifier
#from pyarrow import null
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim


st.set_page_config(page_title="Сервис расчета рыночной стоимости жилой недвижимости г.Москвы",
                   page_icon=":house_buildings:",
                   layout="wide")
st.title(":house_buildings: Сервис расчета рыночной стоимости жилой недвижимости г.Москвы")
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

        #st.write(geocode(addressfind.tolist())[1])
        if geocode(addressfind.tolist()) != None:
            coords = geocode(addressfind.tolist())[1]
            if len(coords) > 0:
                st.write('Координаты найдены!')
                df1.loc[df1['Эталон'] == 1, 'lat'] = coords[0]
                df1.loc[df1['Эталон'] == 1, 'lon'] = coords[1]
                st.write(df1[df1['Эталон'] == 1][['Местоположение','lat','lon']])


                st.map(df1[df1['Эталон'] == 1][['lat', 'lon']])
                df1.to_excel('C:/Users/Sasha/PycharmProjects/hackaton2/etalon.xlsx')


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
    metro_minutes = cols[3].number_input("Время до метро пешком (до N мин.)", value=30.0, min_value = 3.0)

    submitted = st.form_submit_button(label="Подобрать аналоги!")

    if submitted:

        etalon = pd.read_excel('C:/Users/Sasha/PycharmProjects/hackaton2/etalon.xlsx').drop( \
            ['short_address', 'Unnamed: 0'], axis=1)
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
        analogs.to_excel('C:/Users/Sasha/PycharmProjects/hackaton2/analogs.xlsx')


st.subheader('ШАГ 3. Расчет удельной стоимости')

#даем возможность пользователю корректировать расчет:
with st.form('count'):
    st.write('Настройте параметры расчета:')
    cols = st.columns(4)
    #выбор радиуса поиска объявлений
    analogs = pd.read_excel('C:/Users/Sasha/PycharmProjects/hackaton2/analogs.xlsx')
    etalon = pd.read_excel('C:/Users/Sasha/PycharmProjects/hackaton2/etalon.xlsx').drop('Unnamed: 0', axis = 1)
    etalon = etalon[etalon['Эталон'] == 1]
    objects = cols[0].multiselect('Укажите аналоги, которые надо убрать из расчета: ', list(analogs['Unnamed: 0']))

    #далее пользователь набирает параметры - они сохраняются списками:
    #segment = cols[1].multiselect('Сегмент:', ['новостройка', 'вторичка', 'старый жилой фонд'])
    #rooms = cols[2].multiselect('Число комнат (студия - 0.5, св.план./пентх./аппартам. - 0):', [0,0.5, 1,2,3,4,5,6,7])
    #repair = cols[3].multiselect('Состояние ремонта:', ['требует ремонта', 'косметический ремонт', 'евроремонт'])
    submitted1 = st.form_submit_button(label="Посчитать удельную стоимость и общую рыночную стоимость!")

    if submitted1:
        #удаляем из аналогов те, которые пользователь указал
        analogs_corrected = analogs[analogs['Unnamed: 0'].isin(objects) == False]
        st.write('Сокращенный список аналогов:')
        st.write(analogs_corrected) #сокращенный список аналогов для расчета

        unit_prices_list = []

        #теперь для каждого аналога корректируем по таблицам unit_price
        for i in list(analogs_corrected['Unnamed: 0']):
            count = count_analog_unitprice(etalon, analogs_corrected[analogs_corrected['Unnamed: 0'] == i])
            unit_prices_list.append(count[1])
        st.write(unit_prices_list)

        st.markdown(f"Эталон:")
        st.write(etalon, 'Средняя удельная цена:', )





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


