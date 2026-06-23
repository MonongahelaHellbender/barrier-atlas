FROM python:3.12-slim

WORKDIR /atlas
COPY requirements-signing.txt /atlas/
RUN pip install --no-cache-dir -r requirements-signing.txt
COPY . /atlas

CMD ["sh", "tools/reproduce.sh"]
