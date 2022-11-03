FROM python:3.8
#FROM python:3.7.4-alpine3.10
#FROM pypy:3

#WORKDIR /app
WORKDIR /usr/src/app

COPY ./App/requirements.txt requirements.txt
#COPY ./App/pipe.pkl pipe.pkl
COPY ./App/df_for_system.pkl df_for_system.pkl
COPY ./App/modules.py modules.py
COPY ./App/main.py main.py
COPY ./App/sample_for_user.xlsx sample_for_user.xlsx
COPY ./App/update.txt update.txt
RUN mkdir /usr/src/app/userdata
COPY ./App/userdata/analogs.xlsx /usr/src/app/userdata/analogs.xlsx
COPY ./App/userdata/etalon.xlsx /usr/src/app/userdata/etalon.xlsx
COPY ./App/userdata/Оценка_пула_данных.xlsx /usr/src/app/userdata/Оценка_пула_данных.xlsx

RUN python -m pip install -q --upgrade pip
RUN pip install pandas
RUN pip install cmake==3.22.1
#RUN pip install pyarrow==10.0.0
#RUN pip uninstall cmake
RUN pip install pyarrow==10.0.*
#RUN ARROW_HOME=/usr/local/bin
#RUN PATH=$PATH:/opt/cmake/bin
#RUN PATH=$PATH:/usr/local/bin/cmake
#RUN PATH=$PATH:/usr/local/cmake/bin
#установим библиотеки:
RUN pip install --no-cache-dir -r requirements.txt


#Внешний вид приложения зададим:
RUN mkdir -p /root/.streamlit
COPY ./App/config.toml /root/.streamlit/config.toml

RUN pip install --upgrade pandas
RUN pip install --upgrade streamlit
# Открываем порт 8501 чтобы он был доступен снаружи контейнера
EXPOSE 8501

#запуск приложения.
#ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.enableXsrfProtection=false"]
#ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]
ENTRYPOINT streamlit run /usr/src/app/main.py --server.enableXsrfProtection=false --server.port=8501 --server.address=0.0.0.0
