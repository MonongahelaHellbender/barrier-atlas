FROM python:3.12-slim

WORKDIR /atlas
COPY . /atlas

CMD ["sh", "tools/reproduce.sh"]
