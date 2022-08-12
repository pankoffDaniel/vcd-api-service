# Руководство

## Введение

Данный проект является сервисом, предоставляющий Application Programming Interface (API) на архитектуре Representational State Transfer (REST), который по API связывается с vCloud Director (vCD), который в свою очередь выполняет различные действия непосредственно над самими Виртуальными Машинами (ВМ).
Бизнес-задача этого сервиса - совершать действия над ВМ. 

API предоставляется клиенту/пользователю интерфейса.
Клиентом может являться как человек, так и программа, отправляющая HTTP-запросы.

## Развертывание сервиса

### Описание

Развертывание сервиса может выполняться несколькими способами.
Основные два способа:

1. Автоматическим способом поднять Docker-контейнеры
2. Ручным способом устанавливать зависимости и настраивать их

В данной инструкции будем рассматривать первый вариант, так как он самый простой, однако, требует заранее написанных Docker-файлов.

### Инструкция

#### Конфигурационные файлы

Сервис имеет две конфигурационные зависимости - это файл переменных окружения `.env` и файл конфигурации `config.toml`.

Файл `.env` отвечает за хранение чувствительных данных, таких как логины, пароли, IP-адреса и т. п., поэтому он отсутствует в репозитории и его нужно создать.

Файл `config.toml` отвечает за хранение данных, которые настраивают сервис для развертывания, например, режим дебага, версия API, настройки логгера и т. п.
Если присутствует файл `config.dev.toml`, то данные будут браться из него - это полезно для режима разработки, поэтому он не входит в репозиторий.

Пример `.env` файла:

```ini
# Postgres
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=vcd
POSTGRES_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# Celery
CELERY_BROKER_URL=amqp://rabbitmq:5672

# vCD
VCD_HOSTNAME=https://vcd.hostname.ru
VCD_API_VERSION=35.2
VCD_ORGANIZATION=vcd_organization
VCD_USERNAME=vcd_username
VCD_PASSWORD=vcd_password
```

Здесь следует уточнить, что *postgres* и *rabbitmq* - это названия Docker-сервисов.

#### Запуск контейнеров

После окончания конфигурирования в терминале вводится следующая команда:

```sh
docker-compose up --build -d
```
- `docker-compose up` поднимает контейнеры
- `--build` запускает сборку проекта
- `-d` запускает контейнеры в фоне

Проверить состояние контейнеров можно посмотрев через команду:

```sh
docker-compose ps
```

Если контейнеры успешно запущены, то напротив названия каждого контейнера будет написано **Up**.

## Сервисы

Docker Compose поднимает несколько контейнеров с сервисами:
- *nginx* - обратный прокси-сервер
- *postgres* - СУБД PostgreSQL
- *adminer* - позволяет через веб-интерфейс управлять БД
- *app* - VCD API Service
- *rabbitmq* - брокер сообщений RabbitMQ
- *celery* - исполнитель задач из брокера сообщений
- *celery-beat* - запускает задачи по крону
- *flower* - позволяет через веб-интерфейс отслеживать выполнение Сelery задач

## База данных

### Описание

Используется СУБД PostgreSQL в сочетании с асинхронным драйвером *asyncpg*.
При запуске контейнеров автоматически применяется последняя миграция, используя *alembic*.

Для создания ВМ необходимо предварительно заполнить, как минимум, таблицу *template_catalog* и его связные таблицы шаблонов.
Если в таблице *settings* не указаны поля *default_vdc* и/или *default_vdc* (будут *null*), то при запросе на создание ВМ необходимо будет указать дополнительные параметры. Об этом подробнее написано в следующем [разделе](#Создать-ВМ).

### Таблицы и столбцы

Жирным шрифтом выделены те таблицы и параметры, которые являются обязательными.

- ***alembic_version*** - таблица для работы *alembic* и миграций
    - ***version_num*** - номер примененной миграции
- ***settings*** - таблица динамических настроек
    - ***id*** - идентификатор
    - *vcd_api_jwt* - клиентский токен от vCD (можно установить вручную, либо сервис сам это сделает, но используется пока срок токена не закончится, и тогда сервис автоматически сменит его на новый)
    - *default_vdc* - vDC по-умолчанию
    - *default_vapp* - vApp по-умолчанию
- ***vm*** - таблица ВМ
    - ***id*** - идентификатор
    - ***vm_id*** - идентификатор ВМ из vCD
    - ***title*** - название
- ***vm_statistics*** - таблица статистики потребляемых ресурсов ВМ
    - ***id*** - идентификатор
    - ***vm_id*** - внешний ключ на *vm.id*
    - ***statistics*** - собираемая статистика в формате JSON
    - ***created_at*** - дата создания
- ***vm_template*** - таблица ВМ шаблона
    - ***id*** - идентификатор
    - ***title*** - название
- ***vapp_template*** - таблица vApp шаблона
    - ***id*** - идентификатор
    - ***title***- название
- ***catalog_template*** - таблица каталога шаблонов
    - ***id*** - идентификатор
    - ***title*** - название
- ***template_catalog*** - таблица шаблона, состоящая из каталога, vApp и ВМ
    - ***id*** - идентификатор
    - ***catalog_template_id*** - внешний ключ на *catalog_template.id*
    - ***vapp_template_id*** - внешний ключ на *vapp_template.id*
    - ***vm_template_id*** - внешний ключ на *vm_template.id*

## Инструкция пользования API

### Описание

API поддерживает версионирование, поэтому доступ к нему осуществляется по URL: **/api/v1/**, где *v1* - версия API, однако, последняя актуальная версия доступна и по-корневому URL: **/**.

Аутентификация отсутствует, то есть сервис принимает любой HTTP-запрос извне.

Обращения к API совершаются через GET-запрос, начиная с параметра *JOB_TYPE* - это работа, которая должна выполниться.

### Схемы параметров

По URL: **/docs/** находится веб-интерфейс, где можно посмотреть схему эндпоинтов и их параметров, а также позволяет из интерфейса совершать HTTP-запросы и тут же получать ответы.
По URL: **/redoc/** находится веб-интерфейс, где можно посмотреть схему эндпоинтов и их параметров.

Жирным шрифтом выделены те параметры, которые являются обязательными.

#### Создать ВМ

- ***JOB_TYPE=NEW_VM***
- ***TEMPLATE_ID*** - идентификатор шаблона создания ВМ из *template_catalog.id*
- ***VM_TITLE*** - название создаваемой ВМ
- ***OS_PASS*** - пароль, который установится для root-пользователя ОС
- *VDC_TITLE* - название vDC (по-умолчанию берется из *settings.default_vdc*)
- *VAPP_TITLE* - название vApp (по-умолчанию берется из *settings.default_app*)

#### Установить значение vCPU ВМ

- ***JOB_TYPE=SET_VM_CPU***
- ***VM_ID*** - идентификатор ВМ из vCD
- ***CPU*** - устанавливаемое количество vCPU

#### Установить значение vRAM ВМ

- ***JOB_TYPE=SET_VM_RAM***
- ***VM_ID*** - идентификатор ВМ из vCD
- ***RAM*** - устанавливаемое количество vRAM в МБ

#### Установить значение vHDD ВМ

- ***JOB_TYPE=SET_VM_HDD***
- ***VM_ID*** - идентификатор ВМ из vCD
- ***HDD*** - устанавливаемое количество vHDD в МБ
- *DISK_NUMBER* - номер изменяемого диска (по-умолчанию №1)

#### Запустить ВМ

- ***JOB_TYPE=START_VM***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Остановить ВМ

- ***JOB_TYPE=STOP_VM***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Cбросить ВМ по питанию

- ***JOB_TYPE=RESET_VM***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Создать снэпшот ВМ

- ***JOB_TYPE=СREATE_SNAP***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Получить статус ВМ

- ***JOB_TYPE=GET_VM_STATUS***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Получить текущее использование ресурсов ВМ

- ***JOB_TYPE=GET_VM_USAGE***
- ***VM_ID*** - идентификатор ВМ из vCD

#### Получить ссылку на консоль ВМ

- ***JOB_TYPE=GET_CONSOLE_URL***
- ***VM_ID*** - идентификатор ВМ из vCD