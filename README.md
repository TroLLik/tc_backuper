# TimeCity Backuper

[![Build Status](https://travis-ci.com/TroLLik/tc_backuper.svg?branch=master)](https://travis-ci.com/TroLLik/tc_backuper)

### Запуск тестов
* В корне проекта выполнить:
    $ python ./com/tc_backuper/tests/unit.py
* Coverage=57%

### Документация по сервису
* Поднимаем сервисы из корня проекта коммандой:
	$ docker-compose up
* Получаем:
    * TeamCity на http://localhost:8112
    * Minio на http://localhost:9000
    * Prometheus на http://localhost:9090
    * Grafana на http://localhost:3000
    * tc_backuper без внешнего ip/порта

* Сервис tc_backuper принимает следующие параметры (при необходимости их можно корректировать через docker-compose.yml):

    | Compose переменная    | Bash переменная | Значение по умолчанию | Комментарий                                             |
    | --------------------- | --------------- | --------------------- | ------------------------------------------------------- |
    | TC_URL                | tc_url          | tc-server:8111        | url целевого TimeCity                                   |
    | TC_USER               | tc_user         | theuser               | Логин для API TimeCity                                  |
    | TC_PASSWD             | tc_pwd          | thepasswd             | Проль для API TimeCity                                  |
    | MINIO_URL             | minio_url       | minio:9000            | url целевого minio                                      |
    | MINIO_ACCESS_KEY      | minio_acc       | oi4ieGh9              | Aсс ключь для API minio                                 |
    | MINIO_SECRET_KEY      | minio_sec       | quohp9Ohfe0eiNov      | Sec ключь для API minio                                 |
    | BACKUP_COUNT          | backup_count    | 5                     | Кол-во последних бакапов хранимых в minio               |
    | BACKUP_INTERVAL       | backup_interval | 30                    | Интервал между запусками создания\развёртывания бакапов |

* Логика работы:
Каждый интервал времени сервис проверяет готов ли TimeCity к созданию резервной копии. Если он готов, с сервера снимается бакап в общий с tc_backuper'ом каталог, об успехе бакапа отправляется метрика. Из общего каталога полученный бакап отправляется в minio с последующей проверкой на разрешённое кол-во копий хранимых в minio, если резервных копий больше положенного, все лишние удаляются. Затем, последняя резервная копия скачивается из minio и из этой копии разворачивается тестовый инстанс TimeCity, об успехе развёртывания отправляется соответствующая метрика.

* Замечание:
Алертинг настроен прямо в графане.

### Как донастроить
* Выполнить начальную инициализацию TeamCity http://localhost:8112
* В логах TeamCity server'а найти authentication token
* Зайти под этим токином в веб интерфейс сервера
* Завести пользователя с админскими привилегиями, и креденшелами из docker-compose.yml переменные TC_USER\TC_PASSWD (по умолчанию: theuser\thepasswd)
* После того как API TeamCity server'а станет доступнен по этим креденшелам, создание\развёртывание резервных копий + сбор метрик начнётся автоматически.