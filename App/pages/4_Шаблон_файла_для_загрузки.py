import streamlit as st
import pandas as pd

st.set_page_config(page_title="Сервис расчета рыночной стоимости жилой недвижимости г.Москвы",
                   page_icon=":house_buildings:",
                   layout="centered")
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title(":pushpin: Шаблон файла для загрузки")

st.write('Здесь можно скачать шаблонный файл для загрузки в качестве образца.')
sample = pd.read_excel('/usr/src/app/sample_for_user.xlsx')
st.write('Важно, чтобы при загрузке файла названия полей, значения полей соответствовали шаблону.'
         'Эталон - обязательно должен быть 1, и отмечен единицей. Поле "Эталон" обязательно должно присутствовать.')
st.write(sample)
with open('/usr/src/app/sample_for_user.xlsx', "rb") as file:

    btn = st.download_button(label = 'Скачать шаблон',
                            data = file,
                            file_name='Sample.xlsx',
                            mime="application/vnd.ms-excel")