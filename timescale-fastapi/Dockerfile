FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9
WORKDIR /usr/app
COPY /src/requirements.txt ./
RUN pip install -r requirements.txt
COPY . .
WORKDIR /usr/app/src
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


