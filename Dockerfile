FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY streamlit-geovista /app/streamlit-geovista/

WORKDIR /app

RUN pip3 install -r streamlit-geovista/requirements.txt

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "streamlit-prettymapp/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
