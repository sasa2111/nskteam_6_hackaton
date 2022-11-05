import datetime
import streamlit as st
from modules import update_notifications

#Настроим конфигурацию страницы
st.set_page_config(page_title="Сервис расчета рыночной стоимости жилой недвижимости г.Москвы",
                   page_icon=":house_buildings:",
                   layout="centered")

hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title(":truck: Автоподгрузка объявлений для подбора аналогов")

st.write('Здесь можно запустить работу модуля автоподгрузки последних объявлений о продаже квартир в систему.')
st.write('Во время работы данного модуля не рекомендуется что-то еще делать в системе.','\n','\n',
         'Если запускать автоподгрузку ежедневно, то она будет занимать не более нескольких минут. ', '\n',
         'За одни сутки в обычно собирается несколько десятков объявлений.')

with open("/usr/src/app/update.txt", "r") as file:

    text = file.read()

st.write(f'Последнее обновление данных об объявлениях в системе: {text}')
if st.button('Подгрузить новые объявления в систему'):
    st.write('Процесс загрузки данных... может занять несколько минут.')
    with open("/usr/src/app/update.txt", "w") as file:
        file.write(f"{datetime.datetime.now()}")
    leng, df_upd, minutes = update_notifications()


    df_upd.to_excel('df_for_system.xlsx')
    st.write(f'Подгрузка новых данных заняла {minutes} мин.')
    if leng >0:
        st.write(f'Загружено {leng} новых объявлений. Всего объявлений в базе: {len(df_upd)}. ')
    else:
        st.write('Новых объявлений нет. Рекомендуем обновить данные через несколько часов.')

st.write('Вы можете выкачать текущую базу объявлений в виде xlsx-файла')

with open('/usr/src/app/df_for_system.xlsx', "rb") as file:
    btn = st.download_button(label='Скачать архив объявлений',
                             data=file,
                             file_name='df_for_system.xlsx',
                             mime="application/vnd.ms-excel")