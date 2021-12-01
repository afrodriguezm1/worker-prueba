## Instalar requerimientos
Se necesita instalar el engine de docker y docker compose:
* https://docs.docker.com/compose/install/
* https://docs.docker.com/engine/install/

## Build de las imagenes

```
docker-compose build
```

## Levantar contenedores

```
docker-compose up
```

## Levantamient de archivo docker-compose 

```
docker-compose -f <file_name.yml> up
```

# Levantamiento en varios servicios

## Levantamiento de autenticación, manejador de tareas, gateway y rabbitmq

```
docker-compose -f docker-compose.gestor-tareas.yml up
```

## Levantamiento de conversor de archivos

```
docker-compose -f docker-compose.file-converter.yml up
```

# Variables de entorno

Las variables de entorno que se deben usar son:

```
# Rabbitmw config
RABBITMQ_DEFAULT_USER
RABBITMQ_DEFAULT_PASS
RABBITMQ_HOSTNAME

# Jwt secret
JWT_SECRET_KEY

# Gestor de tareas config
FLASK_ENV=development
SMTP_EMAIL_SERVER
SMTP_EMAIL_PORT
SMTP_EMAIL_SENDER_EMAIL
SMTP_EMAIL_SENDER_PASSWORD
GESTOR_TAREAS_HOST

#mySQL
DB_HOST
DB_NAME_SECURITYMS
DB_USER
DB_PASSWORD
DB_NAME_GESTORTAREAS
```