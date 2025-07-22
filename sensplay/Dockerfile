FROM python:3.11-slim-buster

WORKDIR /python-docker

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

# =========================================================================
# NUEVO: Copiar la carpeta 'my-app/secrets' a /python-docker/my-app/secrets/
# La ruta de origen es relativa a la ubicación del Dockerfile (proyecto-complexivo)
# La ruta de destino es relativa al WORKDIR (/python-docker)
COPY my-app/secrets/ my-app/secrets/
# =========================================================================

COPY . .

EXPOSE 8080

CMD [ "python", "-m", "flask", "--app", "my-app/run", "run", "--host=0.0.0.0", "--port=8080"]
