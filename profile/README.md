<div align="center">

<h1>Mirea&nbsp;CRM</h1>

<p>
<b>Микросервисная CRM для сети салонов красоты.</b><br>
Записи к специалистам, каталог услуг, складской учёт расходников, филиальная структура.
</p>

<p>
<img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&style=for-the-badge&logoColor=white">
<img alt="Go 1.26" src="https://img.shields.io/badge/Go-1.26-00ADD8?logo=go&style=for-the-badge&logoColor=white">
<img alt="gRPC" src="https://img.shields.io/badge/gRPC-protobuf-2E86AB?style=for-the-badge&logoColor=white">
<img alt="RabbitMQ 3.13" src="https://img.shields.io/badge/RabbitMQ-3.13-FF6600?logo=rabbitmq&style=for-the-badge&logoColor=white">
<img alt="NATS 2.10" src="https://img.shields.io/badge/NATS-2.10-27AAE1?logo=natsdotio&style=for-the-badge&logoColor=white">
</p>

<p>
<img alt="PostgreSQL 16" src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&style=flat-square&logoColor=white">
<img alt="Keycloak 26" src="https://img.shields.io/badge/Keycloak-26-008AAA?logo=keycloak&style=flat-square&logoColor=white">
<img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&style=flat-square&logoColor=white">
<img alt="Docker Compose" src="https://img.shields.io/badge/Docker%20Compose-2496ED?logo=docker&style=flat-square&logoColor=white">
<img alt="OpenTelemetry" src="https://img.shields.io/badge/OpenTelemetry-425CC7?logo=opentelemetry&style=flat-square&logoColor=white">
<img alt="Prometheus" src="https://img.shields.io/badge/Prometheus-E6522C?logo=prometheus&style=flat-square&logoColor=white">
<img alt="Grafana" src="https://img.shields.io/badge/Grafana-F46800?logo=grafana&style=flat-square&logoColor=white">
<img alt="Jaeger" src="https://img.shields.io/badge/Jaeger-66CFE3?logo=jaeger&style=flat-square&logoColor=white">
</p>

<p>
<img alt="9 сервисов" src="https://img.shields.io/badge/%D1%81%D0%B5%D1%80%D0%B2%D0%B8%D1%81%D0%BE%D0%B2-9-1F6FEB?style=flat-square&labelColor=24292F">
<img alt="15 репозиториев" src="https://img.shields.io/badge/%D1%80%D0%B5%D0%BF%D0%BE%D0%B7%D0%B8%D1%82%D0%BE%D1%80%D0%B8%D0%B5%D0%B2-15-1F6FEB?style=flat-square&labelColor=24292F">
<img alt="7 баз" src="https://img.shields.io/badge/%D0%B1%D0%B0%D0%B7-7-1F6FEB?style=flat-square&labelColor=24292F">
<img alt="4 транспорта" src="https://img.shields.io/badge/%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%B0-4-1F6FEB?style=flat-square&labelColor=24292F">
<img alt="МИРЭА" src="https://img.shields.io/badge/%D0%BA%D1%83%D1%80%D1%81%D0%BE%D0%B2%D0%BE%D0%B9%20%D0%BF%D1%80%D0%BE%D0%B5%D0%BA%D1%82-%D0%9C%D0%98%D0%A0%D0%AD%D0%90-1F6FEB?style=flat-square&labelColor=24292F">
</p>

<p>
<a href="#архитектура">Архитектура</a> ·
<a href="#сводная-схема">Сводная схема</a> ·
<a href="#репозитории">Репозитории</a> ·
<a href="#запуск">Запуск</a> ·
<a href="#контракты-прежде-реализации">Контракты</a> ·
<a href="#устройство-сервиса">Устройство сервиса</a>
</p>

</div>

---

Учебный проект по курсу «Микросервисная архитектура» (МИРЭА). Система
поднимается одной командой и работает целиком: девять сервисов на Python и Go,
четыре транспорта, пятнадцать репозиториев.

## Архитектура

Наружу открыт один порт. Сервисы за шлюзом публичных портов не имеют.
Шлюз проверяет токен Keycloak, извлекает роли и маршрутизирует запрос;
предметной логики в нём нет: иначе он оказался бы связан с каждым сервисом
сразу.

### Синхронный контур: gRPC

Внутренние вызовы идут по gRPC. Граф вызовов ацикличен: ни один сервис
не вызывает того, кто вызывает его, поэтому взаимная блокировка невозможна
по построению.

```mermaid
flowchart TD
    U([Браузер]) -->|REST| GW[gateway]
    GW -->|REST| SVC

    subgraph SVC [Девять сервисов, между собой по gRPC]
        direction TB
        BOOK[booking-service] -->|слоты и цены| CAT[catalog-service]
        BOOK -->|филиал и мастер| CORE[core-service]
        INV[inventory-service] -->|нормативы расхода| CAT
        NOTIF[notification-service] -->|контакты| CLI[client-service]
        BILL[billing-service] -->|что за визит| BOOK
        BILL -->|кто клиент| CLI
        ANA[analytics-service] -->|оргструктура| CORE
    end
```

### Асинхронный контур: RabbitMQ

Изменения состояния, потеря которых недопустима, расходятся доменными
событиями через topic-обменник RabbitMQ. События содержат идентификаторы,
а не снимки данных: детали потребитель дозапрашивает по gRPC.

```mermaid
flowchart TB
    subgraph pub [Публикуют]
        BOOK[booking-service]
        INV[inventory-service]
        BILL[billing-service]
    end

    pub --> EX{{"mirea.events · topic"}}

    EX -->|appointment.completed| QI[["inventory-service.events"]]
    EX -->|appointment.completed| QB[["billing-service.events"]]
    EX -->|"appointment.created · appointment.cancelled<br/>stock.low · invoice.issued"| QN[["notification-service.events"]]
    EX -->|"# — весь поток"| QA[["analytics-service.events"]]

    QI -.-> DLX
    QB -.-> DLX
    QN -.-> DLX
    QA -.->|"после 10 неудачных попыток"| DLX{{"mirea.events.dlx · fanout"}}
    DLX --> DEAD[["mirea.events.dead"]]
```

Каждую очередь читает одноимённый с ней сервис. Очереди quorum-типа
с ограничением в десять доставок: сообщение, которое не удалось обработать,
не повторяется бесконечно, а уходит через fanout-обменник в очередь разбора.

Событие `appointment.completed` обрабатывают три потребителя: списание
расходников, выставление счёта и аналитика. Уведомления подписаны на другие
ключи — создание и отмена записи, выставленный счёт, низкий остаток.

### Живые обновления: NATS

По NATS идут широковещательные обновления, которые устаревают за секунды.
Используется core pub/sub без JetStream: очередей и гарантий доставки нет,
подписчик ресинхронизируется самостоятельно.

```mermaid
flowchart LR
    BOOK[booking-service] -->|mirea.branch.ID.schedule| N((NATS))
    INV[inventory-service] -->|mirea.branch.ID.alerts| N

    N -->|mirea.branch.*.alerts| NOTIF[notification-service]
    N -.->|подписчика пока нет| BOARD([Табло на ресепшене])
```

| Тема | Публикует | Слушает |
|---|---|---|
| `mirea.branch.{id}.schedule` | booking-service | никто: тема предназначена живому табло, веб-клиента у системы нет |
| `mirea.branch.{id}.alerts` | inventory-service | notification-service, по шаблону `mirea.branch.*.alerts` |

**Разделение брокеров.** RabbitMQ отвечает за сообщения, потеря которых
недопустима: списание материалов, выставленный счёт. Для них нужны
durable-очереди и подтверждения. NATS отвечает за широковещательную рассылку
без гарантий. Это разные классы доставки; объединение их в одной шине
означало бы либо избыточную надёжность там, где она не требуется, либо
её нехватку там, где требуется.

Проекту такого масштаба хватило бы и одного брокера. Второй введён, чтобы
развести оба класса задач явно, и снимается без изменений доменной логики.

## Сводная схема

```mermaid
flowchart TB
    U([Браузер]) --> GW
    GW <-.-> KC[(Keycloak)]

    GW[gateway] --> CORE[core-service]
    GW --> CAT[catalog-service]
    GW --> CLI[client-service]
    GW --> BOOK[booking-service]
    GW --> INV[inventory-service]
    GW --> BILL[billing-service]
    GW --> NOTIF[notification-service]
    GW --> ANA[analytics-service]

    BOOK -.-> CAT
    BOOK -.-> CORE
    INV -.-> CAT
    NOTIF -.-> CLI
    BILL -.-> BOOK
    BILL -.-> CLI
    ANA -.-> CORE

    BOOK ==> EX{{mirea.events}}
    INV ==> EX
    BILL ==> EX
    EX ==> QI[[inventory-service.events]] ==> INV
    EX ==> QB[[billing-service.events]] ==> BILL
    EX ==> QN[[notification-service.events]] ==> NOTIF
    EX ==> QA[[analytics-service.events]] ==> ANA
    QI -.-> DLX{{mirea.events.dlx}}
    QB -.-> DLX
    QN -.-> DLX
    QA -.-> DLX
    DLX ==> DEAD[[mirea.events.dead]]

    BOOK --> NATS(((NATS)))
    INV --> NATS
    NATS --> NOTIF

    CORE --- DB1[(core_db)]
    CAT --- DB2[(catalog_db)]
    CLI --- DB3[(client_db)]
    BOOK --- DB4[(booking_db)]
    INV --- DB5[(inventory_db)]
    BILL --- DB6[(billing_db)]
    ANA --- DB7[(analytics_db)]
```

Сплошная стрелка — REST, пунктир — gRPC и отбраковка сообщений, жирная —
события RabbitMQ, линия без стрелки — собственная база. У `gateway`
и `notification-service` базы нет: первый не хранит состояние, второй держит
его в очередях.

## Репозитории

### Сервисы

| Сервис | Стек | База | Ответственность | Конвейер |
|---|:---:|---|---|:---:|
| **[`gateway`](https://github.com/mireacrm/gateway)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | — | Проверка JWT, роли, маршрутизация | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/gateway/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/gateway/actions/workflows/ci.yml) |
| **[`core-service`](https://github.com/mireacrm/core-service)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | `core_db` | Компании, филиалы, сотрудники, графики | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/core-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/core-service/actions/workflows/ci.yml) |
| **[`client-service`](https://github.com/mireacrm/client-service)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | `client_db` | Клиентская база, контакты, лояльность | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/client-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/client-service/actions/workflows/ci.yml) |
| **[`booking-service`](https://github.com/mireacrm/booking-service)** | <img alt="Go" src="https://img.shields.io/badge/Go-00ADD8?logo=go&style=flat-square&logoColor=white"> | `booking_db` | Записи, расписание специалистов, слоты | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/booking-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/booking-service/actions/workflows/ci.yml) |
| **[`catalog-service`](https://github.com/mireacrm/catalog-service)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | `catalog_db` | Услуги, прайс, нормативы расхода | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/catalog-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/catalog-service/actions/workflows/ci.yml) |
| **[`inventory-service`](https://github.com/mireacrm/inventory-service)** | <img alt="Go" src="https://img.shields.io/badge/Go-00ADD8?logo=go&style=flat-square&logoColor=white"> | `inventory_db` | Склад расходников, списание, остатки | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/inventory-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/inventory-service/actions/workflows/ci.yml) |
| **[`billing-service`](https://github.com/mireacrm/billing-service)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | `billing_db` | Счета, оплаты, комиссия специалиста | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/billing-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/billing-service/actions/workflows/ci.yml) |
| **[`notification-service`](https://github.com/mireacrm/notification-service)** | <img alt="Go" src="https://img.shields.io/badge/Go-00ADD8?logo=go&style=flat-square&logoColor=white"> | — | Напоминания клиентам и администраторам | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/notification-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/notification-service/actions/workflows/ci.yml) |
| **[`analytics-service`](https://github.com/mireacrm/analytics-service)** | <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?logo=python&style=flat-square&logoColor=white"> | `analytics_db` | Выручка, загрузка, расход материалов | [![CI](https://img.shields.io/github/actions/workflow/status/mireacrm/analytics-service/ci.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=CI&branch=main)](https://github.com/mireacrm/analytics-service/actions/workflows/ci.yml) |

Go используется там, где существенна конкурентность: захват слотов, счётчики
остатков, рассыльщик, работающий с двумя брокерами. Python — там, где важнее
скорость разработки и работа с данными.

Каждый сервис собирает свой образ и публикует его
в [`ghcr.io/mireacrm/*`](https://github.com/orgs/mireacrm/packages) —
отдельной сборки при развёртывании не требуется.

### Общее хозяйство

| Репозиторий | Что внутри | Состояние |
|---|---|:---:|
| **[`deploy`](https://github.com/mireacrm/deploy)** | **Точка входа.** Compose, настройки инфраструктуры, описание архитектуры | |
| **[`proto`](https://github.com/mireacrm/proto)** | Контракты gRPC и событий — источник правды | [![версия](https://img.shields.io/github/v/tag/mireacrm/proto?style=flat-square&label=%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%8F&color=1F6FEB&labelColor=24292F)](https://github.com/mireacrm/proto/tags)<br>[![выпуск](https://img.shields.io/github/actions/workflow/status/mireacrm/proto/release.yml?style=flat-square&logo=githubactions&logoColor=white&labelColor=24292F&label=%D0%B2%D1%8B%D0%BF%D1%83%D1%81%D0%BA)](https://github.com/mireacrm/proto/actions/workflows/release.yml) |
| **[`contracts-go`](https://github.com/mireacrm/contracts-go)** | Сгенерированный код для Go. Правится только перегенерацией | [![версия](https://img.shields.io/github/v/tag/mireacrm/contracts-go?style=flat-square&label=%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%8F&color=1F6FEB&labelColor=24292F)](https://github.com/mireacrm/contracts-go/tags) |
| **[`contracts-py`](https://github.com/mireacrm/contracts-py)** | Сгенерированный код для Python. Правится только перегенерацией | [![версия](https://img.shields.io/github/v/tag/mireacrm/contracts-py?style=flat-square&label=%D0%B2%D0%B5%D1%80%D1%81%D0%B8%D1%8F&color=1F6FEB&labelColor=24292F)](https://github.com/mireacrm/contracts-py/tags) |
| **[`go-common`](https://github.com/mireacrm/go-common)** · **[`py-common`](https://github.com/mireacrm/py-common)** | Общий обвяз: транспорт, трассировка, метрики, каркас процесса | |

## Запуск

```bash
git clone https://github.com/mireacrm/deploy.git && cd deploy
cp .env.example .env
docker compose up -d
```

Образы берутся готовыми из `ghcr.io/mireacrm/*`, собирать ничего не нужно.
Когда стенд поднялся, доступны:

| Адрес | Что это |
|---|---|
| <http://localhost:8000> | **API шлюза** — единственный вход в систему |
| <http://localhost:8080> | Keycloak: пользователи, роли, выдача токенов |
| <http://localhost:15672> | RabbitMQ: обменники, очереди, очередь разбора |
| <http://localhost:8222> | NATS: страница мониторинга |
| <http://localhost:16686> | Jaeger: сквозные трассировки запросов |
| <http://localhost:9090> | Prometheus: метрики сервисов и инфраструктуры |
| <http://localhost:3000> | Grafana: дашборды по сервисам и очередям |

## Контракты прежде реализации

Файлы `.proto` — единственный источник правды. Тег на
[`proto`](https://github.com/mireacrm/proto) перегенерирует код и раскладывает
его по языковым репозиториям под той же версией, поэтому описание и стабы
разойтись не могут:

```
proto v0.1.1  ─┬─→  contracts-go v0.1.1  ─→  go-common  ─→  сервисы на Go
               └─→  contracts-py v0.1.1  ─→  py-common  ─→  сервисы на Python
```

Версию поднимает потребитель. Это цена разъезда по репозиториям:
несовместимая правка контракта обнаруживается не в одном общем прогоне,
а в каждом сервисе в момент повышения версии.

## Устройство сервиса

Одинаково независимо от языка: REST наружу, gRPC внутрь, собственная база,
миграции при старте, раздельные `/healthz` и `/readyz`, метрики Prometheus,
сквозная трассировка, модульные и интеграционные тесты в конвейере.

Интеграционные тесты выполняются против Postgres, RabbitMQ, NATS и Keycloak,
поднятых в прогоне, а не против заглушек.
