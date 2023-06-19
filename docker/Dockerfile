FROM python:3.10-slim-buster

# Установка git
RUN apt-get update && apt-get install -y --no-install-recommends git

LABEL version=1.0.4
EXPOSE 7005
EXPOSE 1234

RUN mkdir -p /opt/pysonic_nemo
WORKDIR /opt/pysonic_nemo
RUN git clone https://github.com/anydict/pysonic_nemo.git /opt/pysonic_nemo

# Установка зависимостей и запуск приложения

RUN pip install --no-cache-dir -r requirements.txt
CMD ["python", "main.py"]