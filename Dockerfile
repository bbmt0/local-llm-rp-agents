FROM python:3.13.5-alpine3.22 AS builder

WORKDIR /code 

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir -r /code/requirements.txt

COPY app /code/app 

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
