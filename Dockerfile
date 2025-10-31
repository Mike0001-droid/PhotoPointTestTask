FROM python:3.11-slim

WORKDIR /test_task

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY test_task/ .

RUN python manage.py makemigrations && python manage.py migrate

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]