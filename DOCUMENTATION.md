# SUZL (Ledorub) — Система управления заказами льда
## Полная техническая документация для разработчиков

> **Версия документации:** 2.0  
> **Дата:** 2026-02-18  

---

## Оглавление

- [1. Обзор системы](#1-обзор-системы)
- [2. Архитектура](#2-архитектура)
- [3. Запуск проекта](#3-запуск-проекта)
- [4. Структура проекта](#4-структура-проекта)
- [5. Backend](#5-backend)
  - [5.1 Entity (JPA-сущности)](#51-entity-jpa-сущности)
  - [5.2 Enums (перечисления)](#52-enums-перечисления)
  - [5.3 DTO (Data Transfer Objects)](#53-dto-data-transfer-objects)
  - [5.4 Controllers (REST API)](#54-controllers-rest-api)
  - [5.5 Services (бизнес-логика)](#55-services-бизнес-логика)
  - [5.6 Repositories](#56-repositories)
  - [5.7 Config](#57-config)
  - [5.8 Exceptions](#58-exceptions)
- [6. Frontend Customer (Клиентское приложение)](#6-frontend-customer)
  - [6.1 Точка входа и роутинг](#61-точка-входа-и-роутинг)
  - [6.2 Глобальное состояние (AppContext)](#62-глобальное-состояние-appcontext)
  - [6.3 API-клиент (api.ts)](#63-api-клиент-apits)
  - [6.4 Утилиты (telegram.ts)](#64-утилиты-telegramts)
  - [6.5 Панели — подробное описание](#65-панели--подробное-описание)
- [7. Frontend Courier (Приложение курьера)](#7-frontend-courier)
  - [7.1 Точка входа и роутинг](#71-точка-входа-и-роутинг)
  - [7.2 API-клиент (api.ts)](#72-api-клиент-apits)
  - [7.3 Панели — подробное описание](#73-панели--подробное-описание)
- [8. Пользовательские потоки (User Flows)](#8-пользовательские-потоки)
- [9. Инфраструктура (Docker / Nginx)](#9-инфраструктура)
- [10. Бизнес-правила и ограничения](#10-бизнес-правила-и-ограничения)
- [11. Внешние интеграции](#11-внешние-интеграции)
- [12. Известные особенности и TODO](#12-известные-особенности-и-todo)

---

## 1. Обзор системы

**SUZL (Ledorub)** — комплекс ПО для автоматизации продажи и доставки льда. Три приложения:

| Компонент | Назначение | Технология | Порт |
|---|---|---|---|
| **Backend API** | REST API, бизнес-логика, БД | Java 17, Spring Boot 3, JPA, PostgreSQL | `8080` |
| **Customer App** | Telegram Mini App для клиентов (владельцы заведений) | React 18, TypeScript, Vite, VKUI | `5173` |
| **Courier App** | Telegram Mini App для курьеров | React 18, TypeScript, Vite, VKUI | `5174` |

### Ключевые бизнес-сущности

- **Organization** — клиент (бар, ресторан, кафе); оформляет заказы на лёд
- **User** — пользователь системы; привязан к роли и организации
- **Order** — заказ на лёд; содержит позиции (OrderItem), информацию о доставке (Delivery), оплате (OrderManyInfo), контейнерах (OrderContainerInfo)
- **IceType** — тип льда (Хошизаки, Кубик, Фраппе); имеет цену за кг
- **Container** — физический контейнер для хранения льда (Арктика, Пенополи); арендуется организацией
- **Courier** — курьер; принимает и доставляет заказы
- **Address** — адрес доставки; привязан к организации

---

## 2. Архитектура

```
┌──────────────────────────────────────────────────────────────────┐
│                      КЛИЕНТЫ (Браузер / Telegram)                │
│  Customer App (localhost:5173)    Courier App (localhost:5174)    │
└──────────────────────┬──────────────────────────┬────────────────┘
                       │                          │
                       ▼                          ▼
         ┌──────────────────────────────────────────┐
         │              NGINX (порт 80)              │
         │  /api/* → backend:8080                    │
         │  /     → frontend:80 или courier:80       │
         └──────────────────┬───────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────────┐
         │         SPRING BOOT (порт 8080)          │
         │                                           │
         │  Controller → Service → Repository → DB  │
         │                                           │
         │  Swagger: /swagger-ui/index.html          │
         └──────────────────┬───────────────────────┘
                            │
                            ▼
         ┌──────────────────────────────────────────┐
         │            PostgreSQL (suzl)              │
         └──────────────────────────────────────────┘
```

### Технологический стек

| Слой | Технологии |
|---|---|
| Backend | Java 17, Spring Boot 3, Spring Data JPA, Hibernate, Lombok, Swagger/OpenAPI |
| Frontend | React 18, TypeScript 5, Vite 5, VKUI 7 (VK Design System), @vkontakte/icons |
| Карты | Yandex Maps API 2.1 (Geocoder + Suggest) |
| Платформа | Telegram WebApp (Mini Apps) |
| Инфраструктура | Docker, Docker Compose, Nginx |
| БД | PostgreSQL |
| CI/CD | Yandex Container Registry (cr.yandex) |

---

## 3. Запуск проекта

### 3.1 Docker (рекомендуемый)

**Требования:** Docker Desktop (запущен)

```bash
# Авторизация в Yandex Container Registry
docker login -u oauth -p <OAUTH_TOKEN> cr.yandex

# Запуск всех сервисов
cd docker
docker-compose pull
docker-compose up -d

# Проверка
docker-compose ps
```

**Доступные адреса:**

| Сервис | URL |
|---|---|
| Customer App | http://localhost:5173 |
| Courier App | http://localhost:5174 |
| Swagger UI | http://localhost:8080/swagger-ui/index.html |
| API | http://localhost:8080/api/v1/ |
| Nginx (прокси) | http://localhost/ |

### 3.2 Локальная разработка фронтенда

```bash
# Customer
cd frontend/customer && npm install && npm run dev

# Courier (отдельный терминал)
cd frontend/courier && npm install && npm run dev
```

Vite проксирует `/api` → `http://localhost:8080` (см. `vite.config.ts`).

### 3.3 Остановка

```bash
cd docker && docker-compose down
```

### 3.4 Переменные окружения (`docker/.env`)

```env
POSTGRES_USER=test
POSTGRES_PASSWORD=test1234
POSTGRES_DB=suzl
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin123
```

---

## 4. Структура проекта

```
SUZL/
├── backend/
│   └── src/main/java/ru/ledorub/backend/
│       ├── config/                    # Конфигурация (Swagger, Jackson, Security)
│       ├── controller/                # REST-контроллеры (11 шт.)
│       │   └── exception/             # RoleNotFoundException
│       ├── dto/                       # Data Transfer Objects (37 файлов)
│       │   ├── address/               # AddressDto, AddressDetails, AddressFullDto, ...
│       │   ├── order/                 # OrderCreateDto, OrderItemAddDto, ContainerDto, ...
│       │   ├── organization/          # OrganizationDto, OrganizationRootDto, ...
│       │   └── user/                  # UserDto, UserSimpleDto, UserFullDto, ...
│       ├── entity/                    # JPA-сущности
│       │   ├── User, UserRole, Organization, Address, AddressType
│       │   ├── order/                 # Order, OrderItem, IceType, Container, ...
│       │   └── enums/                 # OrderStatus, PaymentMethod, DeliveryType, ...
│       ├── repository/                # Spring Data JPA репозитории (10 шт.)
│       ├── service/                   # Бизнес-логика (интерфейсы + реализации)
│       │   ├── address/
│       │   ├── order/
│       │   ├── organization/
│       │   ├── user/
│       │   └── exception/             # Кастомные исключения + GlobalExceptionHandler
│       └── specifications/            # JPA Specifications для фильтрации
│
├── frontend/
│   ├── customer/                      # Клиентское приложение (23 панели)
│   │   ├── src/
│   │   │   ├── App.tsx                # Роутинг между панелями
│   │   │   ├── main.tsx               # Точка входа React
│   │   │   ├── context/AppContext.tsx  # Глобальное состояние
│   │   │   ├── services/api.ts        # HTTP-клиент
│   │   │   ├── utils/telegram.ts      # Утилиты Telegram WebApp
│   │   │   ├── types/index.ts         # TypeScript-типы
│   │   │   └── panels/               # Экраны приложения
│   │   ├── vite.config.ts
│   │   └── package.json
│   │
│   └── courier/                       # Приложение курьера (14 панелей)
│       ├── src/
│       │   ├── App.tsx
│       │   ├── main.tsx
│       │   ├── services/api.ts
│       │   ├── utils/telegram.ts
│       │   ├── types/index.ts
│       │   └── panels/
│       ├── vite.config.ts
│       └── package.json
│
├── docker/
│   ├── docker-compose.yaml
│   ├── .env
│   ├── nginx.conf
│   ├── NginxDockerFile
│   ├── BackendDockerFile
│   ├── FrontendDockerFile
│   └── CourierDockerFile
│
├── Makefile                           # Make-команды для Linux/Mac
├── DOCUMENTATION.md                   # Этот файл
└── README.md
```

---

## 5. Backend

### 5.1 Entity (JPA-сущности)

#### `User` (таблица `users`)

Пользователь системы. Может быть владельцем организации, курьером, администратором.

| Поле | Тип | БД-ограничения | Описание |
|---|---|---|---|
| `id` | Long | PK, auto-increment | Идентификатор |
| `userRole` | UserRole | FK `user_role_id`, NOT NULL | Роль пользователя |
| `firstName` | String | NOT NULL, max 100 | Имя |
| `lastName` | String | NOT NULL, max 100 | Фамилия |
| `login` | String | UNIQUE, NOT NULL, max 100 | Логин |
| `passwordHash` | String | NOT NULL, max 255 | Хеш пароля |
| `number` | String | UNIQUE, NOT NULL, max 32 | Телефон |
| `email` | String | UNIQUE, NOT NULL, max 255 | Email |
| `organization` | Organization | FK `organization_id` (nullable) | Организация |
| `active` | boolean | NOT NULL, default true | Признак активности (soft delete) |

#### `UserRole` (таблица `user_roles`)

Роль пользователя в системе.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `name` | String | Название роли (UNIQUE) |
| `description` | String | Описание |

**Предопределённые роли:** `admin`, `administrator`, `courier`, `worker`, `analyst`, `user`, `test`

**Группы ролей:**
- `customersDependencies` — роли клиентов: admin, administrator, worker, user
- `companyDependencies` — корпоративные роли: admin, courier, user
- `analystDependencies` — аналитические роли: admin, analyst, user

#### `Organization` (таблица `organizations`)

Организация-клиент (бар, ресторан).

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `name` | String | Название (NOT NULL) |
| `inn` | String | ИНН (UNIQUE, NOT NULL, max 12) |
| `rootUser` | User | FK — основной пользователь (nullable) |
| `rootAddress` | Address | FK — основной адрес (nullable) |
| `addressList` | List\<Address\> | ManyToMany через `organization_addresses` |
| `active` | boolean | Soft delete |

> **Важно:** `addressList` — это ManyToMany связь. Один адрес может принадлежать нескольким организациям.

#### `Address` (таблица `addresses`)

Физический адрес.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `addressType` | AddressType | FK, NOT NULL — тип адреса |
| `countryCode` | String | Код страны (max 2) |
| `postalCode` | String | Почтовый индекс (max 20) |
| `region` | String | Регион |
| `city` | String | Город |
| `street` | String | Улица |
| `houseNumber` | String | Номер дома |
| `apartment` | String | Квартира/офис |
| `fullAddress` | String | Полный адрес строкой |
| `description` | String | Комментарий |
| `latitude` | BigDecimal(9,6) | Широта |
| `longitude` | BigDecimal(9,6) | Долгота |
| `active` | boolean | Soft delete |

#### `AddressType` (таблица `address_types`)

Тип адреса.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `name` | String | Название (UNIQUE, max 100) |
| `description` | String | Описание (max 200) |

**Предопределённые типы:** `bar`, `warehouse`, `office`, `customer`, `test`

#### `Order` (таблица `orders`)

Заказ на лёд.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `customer` | User | FK `customer_id`, NOT NULL — кто заказал |
| `organization` | Organization | FK, NOT NULL — от какой организации |
| `createdAt` | LocalDateTime | Автоматическая дата создания (CreationTimestamp) |
| `status` | OrderStatus | ENUM, NOT NULL |
| `delivery` | Delivery | OneToOne — информация о доставке |
| `orderContainerInfo` | OrderContainerInfo | OneToOne — информация о контейнерах |
| `orderManyInfo` | OrderManyInfo | OneToOne — финансовая информация |
| `orderItemsList` | List\<OrderItem\> | OneToMany — позиции заказа |

> **Примечание:** Поле `customer` в коде имеет комментарий «Исправлено с user» — раньше называлось `user`, переименовано в `customer`.

#### `OrderItem` (таблица `order_items`)

Позиция заказа (один вид льда в заказе).

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `order` | Order | FK, NOT NULL |
| `iceType` | IceType | FK, NOT NULL — тип льда |
| `weight` | Integer | Вес (кг) |
| `packaging` | Packaging | ENUM — размер фасовки |
| `unitPrice` | BigDecimal(12,2) | Цена за единицу |
| `active` | boolean | Soft delete |

#### `Delivery` (таблица `delivery`)

Информация о доставке заказа.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `order` | Order | OneToOne (mappedBy) |
| `deliveryType` | DeliveryType | ENUM — тип доставки |
| `preferredDeliveryDatetime` | LocalDateTime | Желаемое время, NOT NULL |
| `address` | Address | FK — адрес доставки (nullable для самовывоза) |
| `comment` | String | Комментарий к доставке |
| `courier` | User | FK — назначенный курьер |

#### `OrderManyInfo` (таблица `order_many_info`)

Финансовая информация заказа.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `order` | Order | OneToOne (mappedBy) |
| `paymentMethod` | PaymentMethod | ENUM, NOT NULL — способ оплаты |
| `priceIce` | BigDecimal(12,2) | Стоимость льда, NOT NULL |
| `priceDrive` | BigDecimal(12,2) | Стоимость доставки |
| `priceContainer` | BigDecimal(12,2) | Стоимость контейнеров |

**Метод:** `totalPrice()` — возвращает сумму `priceIce + priceDrive + priceContainer`.

#### `OrderContainerInfo` (таблица `order_container_info`)

Информация о контейнерах в заказе.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `order` | Order | OneToOne (mappedBy) |
| `needContainer` | boolean | Нужен ли контейнер, NOT NULL |
| `iceInContainer` | boolean | Лёд внутри контейнера |
| `rentContainerDay` | int | Дней аренды |
| `containers` | List\<Container\> | OneToMany — привязанные контейнеры |

#### `IceType` (таблица `ice_types`)

Тип льда.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `name` | String | Название (UNIQUE, max 100) |
| `description` | String | Описание (max 500) |
| `pricePerKg` | BigDecimal(12,2) | Цена за кг, NOT NULL |
| `imageUrl` | String | URL изображения, NOT NULL, max 255 |
| `active` | boolean | Soft delete |

#### `Container` (таблица `containers`)

Физический контейнер для хранения льда.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `containerType` | ContainerType | FK, NOT NULL — тип контейнера |
| `free` | boolean | Свободен ли контейнер, NOT NULL |
| `atOrganization` | Organization | FK — у какой организации находится (nullable) |
| `containerInfo` | OrderContainerInfo | FK — связь с заказом (nullable) |
| `active` | boolean | Soft delete |

#### `ContainerType` (таблица `container_types`)

Тип контейнера.

| Поле | Тип | Описание |
|---|---|---|
| `id` | Long | PK |
| `name` | String | Название (NOT NULL, max 100) |
| `rentalPrice` | Integer | Стоимость аренды за день, NOT NULL |
| `volume` | Integer | Объём, NOT NULL |
| `capacity` | Integer | Вместимость, NOT NULL |
| `imageUrl` | String | URL изображения (max 255) |

---

### 5.2 Enums (перечисления)

#### `OrderStatus`
| Значение | Описание |
|---|---|
| `New` | Новый заказ |
| `Approved` | Подтверждён |
| `InWay` | В пути |
| `Delivered` | Доставлен |
| `Cancelled` | Отменён |

#### `PaymentMethod`
| Значение | Описание |
|---|---|
| `Account` | Расчётный счёт (безнал) |
| `Cash` | Наличные |
| `Card` | Банковская карта |

#### `DeliveryType`
| Значение | Описание |
|---|---|
| `SELFCALL` | Самовывоз |
| `DELIVERY` | Обычная доставка |
| `EXPRESS` | Экспресс-доставка |

#### `Packaging`
Размер фасовки (вес одной упаковки).
| Значение | Вес (кг) |
|---|---|
| `KG_10` | 10 |
| `KG_5` | 5 |
| `KG_2` | 2 |

#### `ContainerStatus`
| Значение | Описание |
|---|---|
| `FREE` | Свободен |
| `BUSY` | Занят |
| `ACTIVATED` | Активирован |
| `DEACTIVATED` | Деактивирован |

---

### 5.3 DTO (Data Transfer Objects)

#### Address DTO

| DTO | Назначение | Ключевые поля |
|---|---|---|
| `AddressDto` | Создание/обновление адреса | `addressTypeId`, `details: AddressDetails`, `fullAddress`, `description` |
| `AddressDetails` | Вложенный объект с полями адреса | `countryCode`, `postalCode`, `region`, `city`, `street`, `houseNumber`, `apartment`, `latitude`, `longitude` |
| `AddressSimpleDto` | Краткий вид для списков | `id`, `fullAddress`, `typeName` |
| `AddressFullDto` | Полный вид для чтения | Все поля Address + AddressType |
| `AddressTypeDto` | Обновление типа адреса | `description` (required, max 200) |
| `AddressFilterRequest` | Фильтр адресов | `addressTypeId`, `addressType` (имя) |

#### Organization DTO

| DTO | Назначение | Ключевые поля |
|---|---|---|
| `OrganizationDto` | Создание + полное чтение | `name`, `inn`, `rootUserId?`, `rootAddressId?` |
| `OrganizationSimpleDto` | Обновление name/inn | `id`, `name`, `inn` |
| `OrganizationRootDto` | Установка root user/address | `rootUserId?`, `rootAddressId?` |
| `OrganizationIdDto` | Передача ID организации | `organizationId` |
| `AddressInfo` | Привязка адреса к организации | `addressId?`, `fullAddress?` |

#### Order DTO

| DTO | Назначение | Ключевые поля |
|---|---|---|
| `OrderCreateDto` | Создание заказа | `customerId`, `organizationId`, `deliveryAddDto`, `orderManyInfoAddDto`, `containerInfoAddDto?`, `items[]` |
| `OrderGetDto` | Полное чтение заказа | `id`, `customer`, `organization`, `delivery`, `manyInfo`, `containerInfo`, `items[]`, `status`, `createdAt` |
| `OrderListDto` | Краткий вид для списков | `id`, `organizationName`, `status`, `createdAt`, `totalPrice` |
| `OrderDto` | Упрощённое DTO (курьерский API) | `id`, `customer`, `deliveryDateTime`, `address`, `comment`, `paymentMethod`, `totalAmount`, `status`, `items[]` |
| `OrderItemAddDto` | Создание позиции | `orderId`, `iceTypeId`, `weight`, `packaging`, `unitPrice` |
| `OrderItemUpdateDto` | Обновление позиции | `iceTypeId?`, `weight?`, `packaging?`, `unitPrice?` |
| `OrderItemSimpleDto` | Краткий вид позиции | `id`, `iceTypeName`, `weight`, `packaging`, `unitPrice` |
| `OrderItemFullDto` | Полный вид позиции | Все поля + orderId + iceType |
| `DeliveryAddDto` | Информация о доставке при создании | `deliveryType`, `preferredDeliveryDatetime`, `addressId?`, `comment?` |
| `ContainerInfoAddDto` | Информация о контейнерах | `needContainer`, `iceInContainer`, `rentContainerDay`, `containerIds[]` |
| `ContainerDto` | Полный контейнер | `id`, `containerType`, `free`, `organizationName`, `active` |
| `ContainerSimpleDto` | Создание/обновление контейнера | `containerTypeId` |
| `ContainerTypeStatisticDto` | Статистика по типу контейнера | `containerTypeName`, `total`, `free`, `busy` |
| `ContainerFilterRequest` | Фильтр контейнеров | `containerTypeId?`, `containerStatus?`, `organizationId?` |
| `IceTypeDto` | Создание/обновление типа льда | `name`, `description`, `pricePerKg`, `imageUrl` |

#### User DTO

| DTO | Назначение | Ключевые поля |
|---|---|---|
| `UserDto` | Создание пользователя | `firstName`, `lastName`, `login`, `number`, `email`, `password`, `organizationId?` |
| `UserSimpleDto` | Краткий вид / обновление | `id`, `firstName`, `lastName`, `login`, `number`, `email` |
| `UserFullDto` | Полный вид (с ролью и организацией) | Все поля + `roleName`, `organizationId`, `organizationName` |
| `UserOrganizationDto` | Обновление организации пользователя | `organizationId` (nullable — сбросить) |
| `UserRoleDto` | Обновление описания роли | `description` |
| `UserFilterRequest` | Фильтр пользователей | `roleId?`, `roleName?`, `organizationId?` |
| `UserAssignRole` | Назначение роли | `userId?`, `login?`, `roleId?`, `roleName?` |

---

### 5.4 Controllers (REST API)

Базовый URL: `/api/v1`

#### `UserController` — `/api/v1/user`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все активные пользователи | — |
| GET | `/` | Пагинация (page, size, sort) | — |
| GET | `/{id}` | Пользователь по ID | — |
| POST | `/` | Создать пользователя | `UserDto` |
| PUT | `/{id}` | Обновить данные | `UserSimpleDto` |
| PUT | `/{id}/organization` | Обновить организацию пользователя | `UserOrganizationDto` |
| POST | `/filter` | Фильтр по роли/организации | `UserFilterRequest` |
| PUT | `/assign-role` | Назначить роль | `UserAssignRole` |
| DELETE | `/{id}` | Деактивировать (soft delete) | — |
| PUT | `/{id}/activate` | Активировать | — |

#### `UserRoleController` — `/api/v1/user-role`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все роли | — |
| GET | `/{id}` | Роль по ID | — |
| PUT | `/{id}` | Обновить роль | `UserRoleDto` |

#### `OrganizationController` — `/api/v1/organization`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все активные организации | — |
| GET | `/` | Пагинация | — |
| GET | `/{id}` | Организация по ID | — |
| POST | `/` | Создать организацию | `OrganizationDto` |
| PUT | `/{id}` | Обновить name/inn | `OrganizationSimpleDto` |
| PUT | `/{id}/root` | Установить rootUser/rootAddress | `OrganizationRootDto` |
| DELETE | `/{id}` | Деактивировать | — |
| PUT | `/{id}/activate` | Активировать | — |
| GET | `/{id}/addresses` | Адреса организации | — |
| POST | `/{id}/addresses` | Привязать адреса | `List<AddressInfo>` |

#### `AddressController` — `/api/v1/address`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все активные адреса | — |
| GET | `/` | Пагинация | — |
| GET | `/{id}` | Адрес по ID | — |
| POST | `/` | Создать адрес | `AddressDto` |
| PUT | `/{id}` | Обновить | `AddressDto` |
| DELETE | `/{id}` | Деактивировать | — |
| PUT | `/{id}/activate` | Активировать | — |
| POST | `/allFilter` | Фильтр по типу | `AddressFilterRequest` |

#### `AddressTypeController` — `/api/v1/address-type`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все типы адресов | — |
| GET | `/{id}` | Тип по ID | — |
| PUT | `/{id}` | Обновить | `AddressTypeDto` |

> **Примечание:** POST-метод для создания типа адреса **отсутствует**. Типы создаются через миграции/прямое добавление в БД.

#### `OrderController` — `/api/v1/order`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all-status` | Все статусы заказов | — |
| GET | `/all` | Все заказы | — |
| GET | `/` | Пагинация | — |
| GET | `/{id}` | Заказ по ID | — |
| POST | `/` | Создать заказ | `OrderCreateDto` |
| DELETE | `/{id}` | Удалить заказ | — |
| GET | `/organizations/{id}` | Заказы организации | — |

> **TODO в коде:** PUT-метод `update` закомментирован; DELETE по факту удаляет, а не деактивирует.

#### `OrderItemController` — `/api/v1/order-item`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все позиции | — |
| GET | `/` | Пагинация | — |
| GET | `/{id}` | Позиция по ID | — |
| POST | `/` | Создать позицию | `OrderItemAddDto` |
| PUT | `/{id}` | Обновить | `OrderItemUpdateDto` |
| DELETE | `/{id}` | Деактивировать | — |
| PUT | `/{id}/activate` | Активировать | — |
| GET | `/packaging` | Все типы упаковки | — |

#### `IceTypeController` — `/api/v1/ice-type`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все типы льда | — |
| GET | `/{id}` | Тип по ID | — |
| POST | `/` | Создать тип | `IceTypeDto` |
| PUT | `/{id}` | Обновить | `IceTypeDto` |
| DELETE | `/{id}` | Деактивировать | — |
| PUT | `/{id}/activate` | Активировать | — |

#### `ContainerController` — `/api/v1/container`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все контейнеры | — |
| GET | `/{id}` | Контейнер по ID | — |
| POST | `/` | Создать | `ContainerSimpleDto` |
| PUT | `/{id}` | Обновить | `ContainerSimpleDto` |
| DELETE | `/{id}` | Деактивировать | — |
| PUT | `/{id}/activate` | Активировать | — |
| POST | `/{id}/take` | Взять контейнер (привязать к организации) | `OrganizationIdDto` |
| POST | `/{id}/free` | Освободить контейнер | — |
| GET | `/status-container` | Все статусы | — |
| POST | `/filter` | Фильтр | `ContainerFilterRequest` |
| GET | `/statistics` | Статистика | — |

#### `ContainerTypeController` — `/api/v1/container-type`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все типы контейнеров | — |
| GET | `/{id}` | Тип по ID | — |
| POST | `/` | Создать | `ContainerType` (entity напрямую) |
| PUT | `/{id}` | Обновить | `ContainerType` |

#### `CourierController` — `/api/v1/courier`

| Метод | Путь | Описание | Body |
|---|---|---|---|
| GET | `/all` | Все курьеры | — |
| GET | `/{id}` | Курьер по ID | — |
| POST | `/` | Создать | `UserDto` |
| PUT | `/{id}` | Обновить | `UserDto` |
| DELETE | `/{id}` | Удалить | — |
| POST | `/{id}/order` | Назначить заказы курьеру | `List<Order>` |
| GET | `/{id}/order` | Заказы курьера | — |

---

### 5.5 Services (бизнес-логика)

Каждый сервис имеет интерфейс и реализацию (`*ServiceImpl`). Ключевые особенности:

#### `AddressServiceImpl`
- `create(AddressDto)` — создаёт адрес; валидирует координаты (latitude: -90..90, longitude: -180..180); оба поля координат обязательны, если хоть одно задано
- `update(id, AddressDto)` — обновляет только переданные поля; проверяет `isActive`
- `deactivate(id)` / `activate(id)` — soft delete
- `filter(AddressFilterRequest)` — фильтрация через JPA Specifications по типу адреса

#### `OrganizationServiceImpl`
- `create(OrganizationDto)` — создаёт организацию; валидирует ИНН (10 или 12 цифр); опционально привязывает rootUser и rootAddress
- `update(id, OrganizationSimpleDto)` — обновляет name и inn; валидирует ИНН
- `updateRoot(id, OrganizationRootDto)` — устанавливает rootUser и rootAddress; привязывает адрес к addressList
- `allAddress(id)` — возвращает все адреса организации
- `addAddresses(id, List<AddressInfo>)` — привязывает адреса к организации по ID или fullAddress

#### `OrderServiceImpl`
- `create(OrderCreateDto)` — создаёт заказ с Delivery, OrderManyInfo, OrderContainerInfo и OrderItems в одной транзакции; привязывает контейнеры к заказу
- `listOrderOrganizations(orgId)` — заказы конкретной организации
- `delete(id)` — физическое удаление

#### `UserServiceImpl`
- `create(UserDto)` — создаёт пользователя с ролью `user` по умолчанию; шифрует пароль через BCrypt; может привязать к организации
- `update(id, UserSimpleDto)` — обновляет только переданные поля
- `updateOrganization(id, UserOrganizationDto)` — меняет/сбрасывает организацию
- `assignRole(UserAssignRole)` — назначает роль по userId/login и roleId/roleName
- `filter(UserFilterRequest)` — фильтрация через JPA Specifications

#### `CourierServiceImpl`
- `create(UserDto)` — создаёт курьера (роль `courier`)
- `setOrder(id, List<Order>)` — назначает заказы курьеру (обновляет `delivery.courier`)
- `getOrder(id)` — возвращает заказы курьера

---

### 5.6 Repositories

Все репозитории наследуют `JpaRepository` или `JpaSpecificationRepository`:

| Репозиторий | Основная entity | Кастомные методы |
|---|---|---|
| `UserRepository` | User | `findByLoginAndActiveTrue`, `findByActiveTrue(Pageable)` |
| `UserRoleRepository` | UserRole | `findByName` |
| `OrganizationRepository` | Organization | `findByIdWithAddressList`, `findByActiveTrue(Pageable)` |
| `AddressRepository` | Address | `findByActiveTrue(Pageable)` |
| `AddressTypeRepository` | AddressType | — |
| `OrderRepository` | Order | `findByOrganizationId` |
| `OrderItemRepository` | OrderItem | — |
| `IceTypeRepository` | IceType | `findByActiveTrue` |
| `ContainerRepository` | Container | `findByActiveTrue` |
| `ContainerTypeRepository` | ContainerType | — |

---

### 5.7 Config

| Файл | Назначение |
|---|---|
| `SwaggerConfig.java` | Настройка OpenAPI/Swagger UI; заголовок «SUZL API» |
| `JacksonConfig.java` | Настройка Jackson: формат дат `yyyy-MM-dd'T'HH:mm:ss`, LazyInitializationException → не падать |
| `SecurityCryptoConfig.java` | Бин `BCryptPasswordEncoder` для хеширования паролей |

### 5.8 Exceptions

| Класс | HTTP Status | Когда бросается |
|---|---|---|
| `ResourceNotFoundException` | 404 | Entity не найдена по ID |
| `BadRequestException` | 400 | Невалидные данные, неактивная entity |
| `ConflictException` | 409 | Нарушение уникальности (DataIntegrityViolation) |
| `RoleNotFoundException` | 404 | Роль не найдена (контроллер-специфичное) |

`GlobalExceptionHandler` — `@ControllerAdvice`, обрабатывает все исключения и возвращает единообразный формат ошибки.

---

## 6. Frontend Customer

### 6.1 Точка входа и роутинг

**`main.tsx`** — рендерит `<App />` в корень DOM.

**`App.tsx`** — корневой компонент:

| Переменная/функция | Тип | Описание |
|---|---|---|
| `activePanel` | `string` (state) | Текущая активная панель |
| `panelHistory` | `string[]` (state) | Стек навигации (для кнопки «Назад») |
| `panelData` | `Record<string, any>` (state) | Данные, передаваемые между панелями |
| `goForward(panel, data?)` | функция | Переход к новой панели; добавляет текущую в историю |
| `goBack()` | функция | Возврат к предыдущей панели из стека |
| `goReplace(panel)` | функция | Замена текущей панели (без добавления в стек) |

Все панели рендерятся через `<View activePanel={activePanel}>` с компонентами `<Panel id="...">`.

### 6.2 Глобальное состояние (AppContext)

**`context/AppContext.tsx`** — React Context + Provider.

#### Хранимые данные

| Поле | Тип | Описание |
|---|---|---|
| `currentUser` | `User \| null` | Авторизованный пользователь |
| `currentOrganization` | `Organization \| null` | Организация пользователя |
| `addresses` | `Address[]` | Адреса организации |
| `orders` | `Order[]` | Заказы |
| `iceTypes` | `IceType[]` | Типы льда |
| `currentOrder` | `Partial<OrderDto> \| null` | Заказ в процессе оформления |

#### `OrderDto` (формируется по шагам создания заказа)

| Поле | Тип | Описание |
|---|---|---|
| `orderMethod` | `'pickup' \| 'delivery' \| 'urgent'` | Способ получения |
| `iceTypeId` | number | Тип льда |
| `weight` | number | Вес |
| `quantity` | number | Количество |
| `unitPrice` | number | Цена за единицу |
| `addressId` | number | ID адреса |
| `paymentMethod` | string | Способ оплаты |
| `totalAmount` | number | Итоговая сумма |
| `comment` | string | Комментарий |
| `deliveryDay` | `'today' \| 'other'` | День доставки |
| `customDate` | string | Конкретная дата |
| `time` | string | Время доставки |
| `packSize` | number | Размер фасовки (кг) |
| `containers` | `ContainerItem[]` | Контейнеры |
| `containerDays` | number | Дней аренды |
| `containerDeliveryMethod` | `'bags' \| 'bulk'` | Фасовка |

#### `ContainerItem`

| Поле | Тип | Описание |
|---|---|---|
| `id` | string | Уникальный ID |
| `name` | string | Название контейнера |
| `count` | number | Количество |
| `pricePerDay` | number | Цена за день |

### 6.3 API-клиент (`api.ts`)

**Базовый URL:** `/api/v1` (проксируется Vite на `http://localhost:8080`).

**Вспомогательная функция `request<T>(endpoint, options)`:**
- Добавляет заголовок `Content-Type: application/json`
- Логирует метод, URL, тело запроса и ответ в `console.log`
- При ошибке (`!response.ok`) логирует ошибку и бросает `Error`
- Обрабатывает пустые ответы (DELETE)
- Использует `safeStringify` для защиты от циклических ссылок

**API-объекты:**

| Объект | Методы | Endpoint |
|---|---|---|
| `userApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/user` |
| `userRoleApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/user-role` |
| `organizationApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete`, `getAddresses` | `/organization` |
| `addressApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/address` |
| `addressTypeApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/address-type` |
| `iceTypeApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/ice-type` |
| `orderApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete`, `getByOrganizationId` | `/order` |
| `orderItemApi` | `getAll`, `getPage`, `getById`, `create`, `update`, `delete` | `/order-item` |

### 6.4 Утилиты (`telegram.ts`)

Обёртка над `window.Telegram.WebApp`:
- `getTelegramWebApp()` — возвращает объект Telegram WebApp
- `getUserData()` — данные текущего пользователя Telegram
- `getInitData()` — init data для авторизации
- `closeMiniApp()` — закрытие Mini App

### 6.5 Панели — подробное описание

#### `SplashPanel`
Стартовый экран с логотипом. Через 2 секунды автоматически переходит на `registration`.

#### `RegistrationPanel`
Регистрация организации. Поля: **название организации**, **ИНН**. При сабмите:
1. `POST /organization` — создание организации
2. `POST /user` — создание пользователя
3. `PUT /organization/{id}/root` — установка rootUser
4. Переход на `selectAddressMethod`

#### `HomePanel`
Главный экран. Три кнопки: **Новый заказ** → `createOrder`, **Профиль** → `profileOwner`, **История заказов** → `orderHistory`.

#### `CreateOrderPanel`
Выбор способа получения: **Самовывоз** → `createOrderPickup`, **Доставка** → `createOrderDelivery`, **Срочный заказ** → `createOrderDelivery` (с пометкой urgent). Сохраняет `orderMethod` в `currentOrder`.

#### `CreateOrderPickupPanel`
Оформление самовывоза. Выбор: тип льда (из `iceTypes`), вес (кг), фасовка, дата/время. Сохраняет данные в `currentOrder`, переход → `needContainer`.

#### `CreateOrderDeliveryPanel`
Оформление доставки. Выбор адреса из `addresses`, тип льда, вес, фасовка, дата/время. Можно добавить новый адрес → `addAddress`. Переход → `needContainer`.

#### `NeedContainerPanel`
Вопрос: «Нужен контейнер?» **Да** → `selectContainer`, **Нет** → `orderComment`.

#### `SelectContainerPanel`
Выбор контейнеров: типы (Арктика, Пенополи), количество, дней аренды, способ фасовки (в пакеты / навалом). Сохраняет в `currentOrder.containers`.

#### `OrderCommentPanel`
Поле для комментария к заказу. Сохраняет в `currentOrder.comment`. Переход → `review`.

#### `ReviewPanel`
Итоговый просмотр заказа. Показывает: тип льда, вес, количество, адрес, контейнеры, комментарий, **итоговую сумму**. Переход → `payment`.

#### `PaymentPanel`
Выбор способа оплаты: **Наличные**, **Перевод**, **Безнал**, **Карта**. При подтверждении:
1. `POST /order` — создание заказа (OrderCreateDto)
2. `POST /order-item` — создание позиций
3. При успехе → `paymentSuccess`, при ошибке → `paymentError`

#### `PaymentSuccessPanel`
Экран успешного создания заказа. Кнопка «На главную» → `home`.

#### `PaymentErrorPanel`
Экран ошибки. Кнопки: «Повторить» → `payment`, «На главную» → `home`.

#### `SelectAddressMethodPanel`
Выбор способа добавления адреса: **Ввести вручную** → `enterAddressManually`, **Выбрать на карте** → `selectAddressOnMap`.

#### `EnterAddressManuallyPanel`
Ручной ввод адреса с **Yandex Suggest API**.

**Состояние:**
| Переменная | Тип | Описание |
|---|---|---|
| `activeModal` | `string \| null` | Текущая активная модалка |
| `searchQuery` | string | Текст в строке поиска |
| `selectedAddress` | string | Выбранный адрес |
| `suggestions` | `string[]` | Подсказки от Яндекса |

**Ключевые эффекты:**
- `useEffect` #1 — загрузка скрипта Yandex Maps API (`apikey` + `suggest_apikey`), инициализация `SuggestView` на внутреннем `<input>` компонента VKUI Search
- `useEffect` #2 — при каждом изменении `searchQuery` вызывает `ymaps.suggest(query)` для 3 городов (Нижний Новгород, Бор, Кстово), фильтрует и обновляет `suggestions`

**Ключевые функции:**
- `handleSelectAddress(address)` — устанавливает адрес, закрывает модалку, вызывает `goForward('saveAddress', { address })`
- `handleConfirmAddress(source?)` — при Enter/клике по подсказке: геокодирует адрес, проверяет город (только Нижний Новгород, Бор, Кстово), проверяет наличие номера дома через `GeocoderMetaData.Address.Components`, при успехе → `handleSelectAddress`
- `handleSearchKeyDown(e)` — обработчик Enter → `handleConfirmAddress()`

#### `SelectAddressOnMapPanel`
Выбор адреса на интерактивной карте Яндекса.

**Состояние:**
| Переменная | Тип | Описание |
|---|---|---|
| `comment` | string | Комментарий к адресу |
| `selectedCoords` | `[number, number] \| null` | Координаты метки |
| `selectedAddress` | string | Адрес, определённый по координатам |
| `mapRef` | Ref | Ссылка на экземпляр ymaps.Map |
| `placemarkRef` | Ref | Ссылка на экземпляр ymaps.Placemark |
| `updatingFromMapRef` | Ref\<boolean\> | Флаг для предотвращения бесконечного цикла |

**Поведение:**
- Центр карты: Нижний Новгород `[56.326797, 44.005986]`, zoom 12
- Перетаскиваемая метка (Placemark, `draggable: true`)
- При перетаскивании метки → `ymaps.geocode(coords)` → обновляет `selectedAddress` + `selectedCoords`
- При вводе адреса вручную → `ymaps.geocode(text)` → двигает метку и центрирует карту
- Флаг `updatingFromMapRef` предотвращает бесконечный цикл (карта обновляет адрес → адрес обновляет карту → ...)
- Кнопка «Сохранить» → `goForward('home')` (логирует координаты и адрес в консоль)

#### `SaveAddressPanel`
Сохранение адреса. Получает `addressData.address` из предыдущей панели.

**Состояние:** `address`, `comment`, `loading`, `error`

**Функция `handleSave`:**
1. Получает адреса организации (`organizationApi.getAddresses`) для определения, откуда пришли (регистрация или профиль)
2. Получает тип адреса (`addressTypeApi.getAll`); если нет — fallback на ID=1
3. Создаёт адрес (`addressApi.create`)
4. Если у организации нет `rootAddress` — обновляет (`organizationApi.update`)
5. Переход: если первый адрес → `home`, иначе → `profileOwner`

#### `AddAddressPanel`
Экран выбора способа добавления адреса (аналогичен `SelectAddressMethodPanel`).

#### `AddressListPanel`
Список всех адресов организации. Для каждого адреса: полный адрес, город, возможность перехода в детали.

#### `OrderHistoryPanel`
История заказов организации. Загружает заказы через `orderApi.getByOrganizationId`. Фильтрация по статусам. Для каждого заказа: номер, дата, статус, сумма, адрес, тип льда.

#### `OrderDetailsPanel`
Детальная информация о заказе: все позиции, адрес, способ оплаты, статус. Кнопка «Отменить заказ» (только для статусов New/Approved).

#### `ProfileOwnerPanel`
Профиль владельца. Информация об организации (название, ИНН), список адресов (до 4 шт.), кнопки: «Все адреса», «Добавить адрес», «Настройки».

#### `SettingsOwnerPanel`
Настройки: изменение **имени организации**, **ИНН**, **телефона**, **email**. Сохранение через `organizationApi.update` и `userApi.update`.

---

## 7. Frontend Courier

### 7.1 Точка входа и роутинг

**`App.tsx`** — аналогичная структура: `activePanel`, `panelHistory`, `goForward()`, `goBack()`.

### 7.2 API-клиент (`api.ts`)

Аналогичный API-клиент с теми же функциями `request<T>` и API-объектами. Дополнительно:
- `courierApi` — методы для работы с курьерскими эндпоинтами (`/courier`)

### 7.3 Панели — подробное описание

#### `SplashPanel`
Стартовый экран, 2 секунды → `registration`.

#### `RegistrationPanel`
Ввод номера телефона курьера. При сабмите ищет пользователя по номеру (`userApi.filter` по номеру). Если найден → `password`, если нет → создаёт нового.

#### `PasswordPanel`
Ввод пароля для входа. Проверяет через бэкенд (сравнение хешей).

#### `HomePanel`
Главный экран курьера. Кнопки: **Заказы** → `orders`, **Склад** → `warehouse`, **Финансы** → `finance`, **Завершённые** → `completedOrders`, **Профиль** → `profile`.

#### `OrdersPanel`
Список заказов, назначенных курьеру. Фильтрация по дате. Мультивыбор заказов для формирования маршрута. Кнопка «Сформировать маршрут» → `route`.

#### `RoutePanel`
Обзор выбранных заказов (маршрут). Для каждого заказа: адрес, комментарий, позиции. Кнопка «Начать доставку» → `deliveryRoute`.

#### `DeliveryRoutePanel`
Активная доставка. Для каждого заказа: детали, кнопки **«Доставлен»** (статус → `Delivered`) и **«Проблема»**. Обновляет статус через API. После завершения всех → возврат на `home`.

#### `CompletedOrdersPanel`
Завершённые заказы. Фильтрация по датам. Для каждого заказа: номер, дата, адрес, сумма, статус (`Delivered`/`Cancelled`). Разворачиваемые детали с позициями.

#### `WarehousePanel`
Склад курьера. Отображает типы льда (Хошизаки, Кубик, Фраппе) с текущим количеством. Кнопки: **Изменить один вид** → `warehouseChangeOne`, **Изменить все** → `warehouseChangeAll`.

#### `WarehouseChangeOnePanel`
Изменение количества одного типа льда. Поле ввода нового значения, кнопка «Сохранить».

#### `WarehouseChangeAllPanel`
Изменение всех типов льда одновременно. Поля ввода для каждого типа.

#### `FinancePanel`
Финансовая статистика. Фильтрация по периоду (сегодня, неделя, месяц, произвольный). Показывает: количество доставленных заказов, сумму заработка.

#### `ProfilePanel`
Профиль курьера. Имя, фамилия, телефон, email. Переключатель уведомлений. Кнопка **Настройки** → `settings`.

#### `SettingsPanel`
Настройки курьера. Поля: имя, фамилия, телефон. Кнопка «Сохранить» → `userApi.update`.

---

## 8. Пользовательские потоки (User Flows)

### 8.1 Регистрация клиента

```
SplashPanel (2 сек)
  └→ RegistrationPanel
       │  Ввод: название организации, ИНН
       │  POST /organization → POST /user → PUT /organization/{id}/root
       └→ SelectAddressMethodPanel
            ├→ EnterAddressManuallyPanel → SaveAddressPanel → HomePanel
            └→ SelectAddressOnMapPanel → HomePanel
```

### 8.2 Создание заказа (доставка)

```
HomePanel → CreateOrderPanel (выбор: доставка)
  └→ CreateOrderDeliveryPanel
       │  Выбор адреса, типа льда, веса, даты/времени
       └→ NeedContainerPanel
            ├→ [Да] SelectContainerPanel → OrderCommentPanel
            └→ [Нет] OrderCommentPanel
                       └→ ReviewPanel (итог)
                            └→ PaymentPanel (выбор оплаты, POST /order)
                                 ├→ PaymentSuccessPanel → HomePanel
                                 └→ PaymentErrorPanel
```

### 8.3 Работа курьера

```
SplashPanel → RegistrationPanel (телефон)
  └→ PasswordPanel → HomePanel
       ├→ OrdersPanel (выбор заказов)
       │     └→ RoutePanel (маршрут)
       │           └→ DeliveryRoutePanel (доставка, смена статусов)
       ├→ WarehousePanel (склад льда)
       ├→ FinancePanel (доходы)
       ├→ CompletedOrdersPanel (история)
       └→ ProfilePanel → SettingsPanel
```

---

## 9. Инфраструктура

### docker-compose.yaml

| Сервис | Образ | Порты | Зависимости |
|---|---|---|---|
| `app` | `cr.yandex/.../backend:latest` | 8080:8080 | — |
| `frontend` | `cr.yandex/.../frontend:latest` | 5173:80 | app |
| `courier-frontend` | `cr.yandex/.../courier:latest` | 5174:80 | app |
| `nginx` | Локальный build (NginxDockerFile) | 80:80 | — |

**Сеть:** `test_network` (bridge)

### Vite Proxy

Оба фронтенда проксируют `/api/*` → `http://localhost:8080`:

```typescript
proxy: {
  '/api': {
    target: 'http://localhost:8080',
    changeOrigin: true,
    secure: false,
  },
}
```

---

## 10. Бизнес-правила и ограничения

### Адреса (Customer App)
- Разрешены только 3 города: **Нижний Новгород**, **Бор**, **Кстово**
- Адрес обязан содержать **номер дома** (проверяется через `ymaps.geocode` → `GeocoderMetaData.Address.Components` → `kind === 'house'`)
- Подсказки фильтруются через 3 параллельных запроса к `ymaps.suggest`: `"Нижний Новгород, {query}"`, `"Бор, {query}"`, `"Кстово, {query}"`

### Организации
- ИНН должен быть 10 или 12 цифр (regex `^(\d{10}|\d{12})$`)
- Порядок создания: организация → пользователь → адрес → обновление rootUser/rootAddress

### Заказы
- Статусный переход: `New → Approved → InWay → Delivered` (или `Cancelled` из любого)
- При создании заказа: `Order` + `Delivery` + `OrderManyInfo` + `OrderContainerInfo` + `OrderItem[]` создаются в одной транзакции
- Контейнеры при привязке к заказу помечаются как `free = false`

### Soft Delete
Все основные entity используют поле `active` (boolean). DELETE-запросы устанавливают `active = false`, а не удаляют запись физически. Исключение: `Order.delete` — физическое удаление.

### Пароли
- Хешируются через `BCryptPasswordEncoder` (бин в `SecurityCryptoConfig`)
- При создании пользователя: `passwordHash = encoder.encode(password)`

---

## 11. Внешние интеграции

### Yandex Maps API 2.1

| Ключ | Значение | Назначение |
|---|---|---|
| `apikey` | `a4e01f48-a28c-4121-9a37-0bb7c1b667d5` | Геокодер, карты |
| `suggest_apikey` | `2d001efd-43af-433e-9e52-8b4b77964f71` | Подсказки адресов (Suggest) |

Используется в:
- `EnterAddressManuallyPanel` — подсказки адресов + геокодирование для валидации
- `SelectAddressOnMapPanel` — интерактивная карта + обратное геокодирование

### Telegram WebApp

Оба приложения (customer, courier) предназначены для запуска как **Telegram Mini Apps**.  
Утилиты в `utils/telegram.ts` обёрнуты в safe-обращения к `window.Telegram.WebApp`.

### Yandex Container Registry

Образы хранятся в `cr.yandex/crp2o4k8oqd3qpbo6vbn/`:
- `backend:latest`
- `frontend:latest`
- `courier:latest`

---

## 12. Известные особенности и TODO

1. **OrderController.update** — закомментирован (`// TODO Дописать Update`), нет метода обновления заказа
2. **OrderController.delete** — физическое удаление вместо soft delete (`// TODO Изменить на Deactivate и Activate`)
3. **Delivery.deliveryType** — поле nullable, хотя логически обязательно (`// TODO вернуть nullable = false`)
4. **CourierServiceImpl** — часть методов закомментирована / заглушена
5. **AddressTypeController** — нет POST-метода; типы адресов нужно заводить в БД напрямую
6. **ContainerTypeController** — принимает entity `ContainerType` вместо DTO
7. **CourierController** — принимает `List<Order>` (entity) вместо DTO для назначения заказов
8. **Фронтенд `api.ts`** — URL `organizationApi.getAddresses` изначально содержал опечатку `/adress` (исправлено на `/addresses`)
9. **SaveAddressPanel** — при отсутствии типов адресов в БД (`addressTypeApi.getAll` → пустой массив) — fallback на `addressTypeId = 1`, что может привести к ошибке если ID=1 не существует

---

*Документация составлена на основе полного анализа исходного кода проекта SUZL (Ledorub).*
