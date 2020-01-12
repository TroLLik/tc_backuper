# TimeCity Backuper
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

    | Compose переменная    | Bash переменная | Значение по умолчанию | Комментарий                                 |
    | --------------------- | --------------- | --------------------- | ------------------------------------------- |
    | TC_URL                | tc_url          | tc-server:8111        | url целевого TimeCity                       |
    | TC_USER               | tc_user         | theuser               | Логин для API TimeCity                      |
    | TC_PASSWD             | tc_pwd          | thepasswd             | Проль для API TimeCity                      |
    | MINIO_URL             | minio_url       | minio:9000            | url целевого minio                          |
    | MINIO_ACCESS_KEY      | minio_acc       | oi4ieGh9              | Aсс ключь для API minio                     |
    | MINIO_SECRET_KEY      | minio_sec       | quohp9Ohfe0eiNov      | Sec ключь для API minio                     |
    | BACKUP_COUNT          | backup_count    | 5                     | Кол-во последних бакапов хранимых в minio   |
    | BACKUP_INTERVAL       | backup_interval | 30                    | Интервал между запусками создания\развёртывания бакапов |

* Логика работы:
Каждый интервал времени сервис проверяет готов ли TimeCity к созданию резервной копии. Если он готов, с сервера снимается бакап в общий с tc_backup'ером каталог, об успехе бакапа отправляется метрика. Из общего каталога полученный бакап отправляется в minio с последуюшей проверкой на разрешённое кол-во копий хранимых в minio, если резервных копий больше положенного, все лишние удалаются. Затем последняя резервная копия скачивается из minio и тз этой копии разворачивается тестовый инстанс TimeCity, об успехе развёртывания отправляется соответствйющая метрика.

* Замечание:
Алертинг настроен в прямо в графане.

### Как донастроить
* В логах TeamCity server'а найти authentication token
* Зати под этим токином на http://localhost:8112
* Завести пользователя с креденшелами из docker-compose.yml переменные TC_USER\TC_PASSWD (по умолчанию: theuser\thepasswd)
* После того как API TeamCity server'а станет доступно по этим креденшелам создание\развёртывание резервных копий + сбор метрик начнётся автоматически.