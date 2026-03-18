FROM python:3.12-slim-bullseye

RUN groupadd -g 1000 appgroup && \
    useradd -r -u 1000 -g appgroup appuser

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt update -y && \
    apt install -y python3-dev \
    gcc \
    libffi-dev \
    musl-dev \
    wget

ENV TZ=Asia/Qyzylorda
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app/
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY src src
COPY static static
COPY tests tests
COPY entrypoint.sh .
COPY alembic.ini .

RUN sed -i 's/\r$//' ./entrypoint.sh && \
    chmod +x ./entrypoint.sh && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD wget --quiet --tries=1 -O /dev/null http://localhost:8000/health || exit 1

ENTRYPOINT ["sh", "./entrypoint.sh"]

