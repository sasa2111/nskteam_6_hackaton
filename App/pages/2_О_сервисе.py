import streamlit as st


st.set_page_config(page_title="Сервис расчета рыночной стоимости жилой недвижимости г.Москвы",
                   page_icon=":house_buildings:",
                   layout="centered")
hide_menu_style = """
        <style>
        #MainMenu {visibility: hidden;}
        </style>
        """
st.markdown(hide_menu_style, unsafe_allow_html=True)

st.title(":crown: О сервисе")

st.write('Данный сервис разработан для автоматизации процесса расчета рыночной оценки жилой недвижимости в г.Москве.'
         ' '
         'Сервис на основе загруженных данных, ищет координаты эталона, подбирает по координатам и указанным фильтрам'
         ' квартиры-аналоги, рассчитывает корректировки на основе параметров квартир, и стоимость квартир из загруженного'
         ' пула. '
         '','\n',
         'Также сервис рассчитывает рыночную стоимость квартир загруженного пула альтернативным способом:'
         ' искусственный интеллект на основе алгоритма Catboost, обученный на базе 2352 объявлений '
         'о продаже квартир стоимостью до 300 млн.руб., '
         'используемых для поиска аналогов, '
         ' дает свою оценку стоимости квартир, эту оценку можно увидеть в той же таблице на Шаге 3 основного'
         ' алгоритма, рядом с оценками, сделанными по алгоритму из ТЗ. Пользователь получает сразу две оценки: '
         'одна - согласно ТЗ на основе данных о квартирах-аналогах, вторая - оценка ИИ, которая может отличаться'
         ' от оценки основного алгоритма. Эта оценка может быть полезной пользователю, т.к. если варьировать в подборе аналогов'
         ' параметры фильтров, оценки основного алгоритма также могут заметно меняться, исходя из разных наборов аналогов, '
         ' и если оценки заметно различаются, то возможно стоит проверить другие варианты настроек в фильтрах на шаге 2, 3.')

st.write('В текущей версии сервис (MVP) рассчитан на одного пользователя. Параллельное использование несколькими '
         'пользователями не рекомендуется - это может повлечь ошибки и путаницу в данных пользователей.'
         'Для мультипользовательского применения необходимы доработки. ')

st.write('Для корректной работы сервиса, пожалуйста, загружайте файл, соответствующий шаблону, который можно скачать'
         'на в разделе  "Шаблон файла для загрузки". ')
st.write('В загруженном файле обязательно должен быть указан 1 эталон (обозначений - 1 в соответствующем поле, '
         'все не эталонные объекты обозначаются нулем.')

st.write('Также для корректного использования ИИ, необходимо его регулярно переобучать или настроить этот процесс'
         ' автоматически. В текущей версии, ИИ обучен на более 2 тыс объявлений, собранных за период с 24.10-4.11.22г.'
         ' Автопереобучение можно настроить, добавив в сервис раздел (по примеру автоподгрузки), где можно будет'
         ' запускать по нажатию кнопки или с определенной периодичностью переобучение алгоритма ИИ.')

st.write('Сервис создан командой NskTeam в рамках хакатона Лидеры Цифровой Трансформации 2022, '
         'в период 24.10.2022-06.11.2022г. (задача №6).')