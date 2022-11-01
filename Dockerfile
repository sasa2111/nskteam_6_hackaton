FROM python:3

WORKDIR /app

COPY ./App/requirements.txt requirements.txt

COPY ./App/pipe.pkl pipe.pkl

COPY ./App/main.py main.py

#установим библиотеки:
RUN pip install --no-cache-dir -r requirements.txt

#Внешний вид приложения зададим:
RUN mkdir -p /root/.streamlit
COPY ./App/config.toml /root/.streamlit/config.toml

# Открываем порт 8501 чтобы он был доступен снаружи контейнера
EXPOSE 8501


ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.address=0.0.0.0"]

