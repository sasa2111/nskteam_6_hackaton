FROM python:3.8


#WORKDIR /app
WORKDIR /usr/src/app

COPY ./App/requirements.txt requirements.txt
COPY ./App/df_for_system.pkl df_for_system.pkl
COPY ./App/df_for_system.xlsx df_for_system.xlsx
COPY ./App/modules.py modules.py
COPY App/Home.py Home.py
COPY ./App/sample_for_user.xlsx sample_for_user.xlsx
COPY ./App/update.txt update.txt
RUN mkdir /usr/src/app/userdata
RUN mkdir /usr/src/app/pages
COPY ./App/userdata/analogs.xlsx /usr/src/app/userdata/analogs.xlsx
COPY ./App/userdata/etalon.xlsx /usr/src/app/userdata/etalon.xlsx
COPY ./App/userdata/Оценка_пула_данных.xlsx /usr/src/app/userdata/Оценка_пула_данных.xlsx
COPY ./App/pages/1_Автоподгрузка_объявлений.py /usr/src/app/pages/1_Автоподгрузка_объявлений.py
COPY ./App/pages/2_О_сервисе.py /usr/src/app/pages/2_O_сервисе.py
COPY ./App/pages/3_Архив.py /usr/src/app/pages/3_Архив.py
COPY ./App/pages/4_Шаблон_файла_для_загрузки.py /usr/src/app/pages/4_Шаблон_файла_для_загрузки.py
COPY ./App/Archive.xlsx Archive.xlsx
COPY ./App/catboost.pkl catboost.pkl

RUN python -m pip install -q --upgrade pip
RUN pip install pandas
RUN pip install cmake==3.22.1

RUN pip install pyarrow==10.0.*

#установим библиотеки:
RUN pip install --no-cache-dir -r requirements.txt

#Внешний вид приложения зададим:
RUN mkdir -p /root/.streamlit
COPY ./App/config.toml /root/.streamlit/config.toml

#Во избежание конфликтов при установке
# сначала ставим то, что ставится, а потом уже апгрейдим.
RUN pip install --upgrade pandas
RUN pip install --upgrade streamlit

# Открываем порт 8501 чтобы он был доступен снаружи контейнера
EXPOSE 8501

#запуск приложения.
#ENTRYPOINT ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableXsrfProtection=false"]
ENTRYPOINT streamlit run /usr/src/app/Home.py --server.enableXsrfProtection=false --server.port=8501 --server.address=0.0.0.0
