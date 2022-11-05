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

st.title(":memo: Архив")

st.write('Здесь можно скачать информацию о расчетах')
arch = pd.read_excel('/usr/src/app/Archive.xlsx', sheet_name='pool').drop('Unnamed: 0', axis = 1)
st.write('Последние оценки')
st.write(arch.tail(20))
with open('/usr/src/app/Archive.xlsx', "rb") as file:

    btn = st.download_button(label = 'Скачать архив оценок',
                            data = file,
                            file_name='Archive.xlsx',
                            mime="application/vnd.ms-excel")

