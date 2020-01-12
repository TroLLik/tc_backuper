FROM python:3

COPY ./com/tc_backuper/main/app.py /opt/tc_backuper/
COPY ./requirements.txt /opt/tc_backuper/

WORKDIR /opt/tc_backuper/

RUN pip install -r requirements.txt

CMD [ "sh", "-c", "python -u ./app.py --tc_url ${TC_URL} --tc_user ${TC_USER} --tc_pwd ${TC_PASSWD} --minio_url ${MINIO_URL} --minio_acc ${MINIO_ACCESS_KEY} --minio_sec ${MINIO_SECRET_KEY} --backup_count ${BACKUP_COUNT} --backup_interval ${BACKUP_INTERVAL}"]