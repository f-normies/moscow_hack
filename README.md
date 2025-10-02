# Хакатон ЛЦТ

## Описание

Данный проект является MVP платформы для анализа и предсказания наличия и местоположении патологии в КТ исследованиях. С технической точки зрения проект представляет из себя микросервисную архитектуру:
1. Backend - ответственный за предобработку DICOM файлов, их отправку в S3-compatable хранилище, отправку запросов на инференс модели и взаимодействию с PostgreSQL БД
2. MinIO - self-host решение S3 хранилища, масштабируемо и поддерживаемо
3. Inference-worker - ONNX runtime, поддерживается как CPU инференс, так и GPU
4. Celery+redis - организуют поток обработки и очередь КТ исследований для inference-worker
4. PostgreSQL - база данных, хранит метаданные файлов и прочую информацию
5. Frontend - базовый, лишь концепт как оно должно было бы выглядеть, реализована аутентификация и отправка на предобработку DICOM файлов, планируется расширение на просмотривальщик КТ исследований после инференса моделей с высокой производительностьей и полный функционал для анализа КТ исследований с инструментами "Линейка", "Зум" и пр.

## Основные возможности и ограничения

Основные возможности описаны в описании и системных требованиях. Ограничения - статус MVP платформы, относительно сырое состояние frontend'а и ограниченная производительность обученной модели (датасеты собирать было очень сложно, из-за этого у нас было мало времени на обучение). 

## Системные требования для запуска

Проект был запущен на конфигурации средней мощности и успешно работал, поэтому, данную конфигурацию можно называть "рекомендуемой" (или "минимальной", вопрос семантики):

1. CPU: Ryzen 5 5600x (6c/12t)
2. GPU: RTX 2070 (8Gb VRAM)
3. RAM: 32Gb DDR4

## Quick Start

1. Сборка и запуск контейнеров (ПРИ НАЛИЧИИ ТОЛЬКО CPU МЕНЯЕМ `docker-compose.gpu.yml` на `docker-compose.cpu.yml`)

```
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.gpu.yml build
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose.gpu.yml up -d
```

2. Проверка конфигурации

```
Frontend: http://localhost:5173
Backend: http://localhost:8000
Automatic Interactive Docs (Swagger UI): http://localhost:8000/docs
Automatic Alternative Docs (ReDoc): http://localhost:8000/redoc
Adminer: http://localhost:8080
Traefik UI: http://localhost:8090
MailCatcher: http://localhost:1080
MinIO: http://localhost:9001
```

Для аутентификации используйте данные из .env:

```
FIRST_SUPERUSER=admin@webapp.com
FIRST_SUPERUSER_PASSWORD=GYSgmXnhFR3p7-4x-2D21A

MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=KaAsm5IXs--CrKeEFILGkA
```

3. Загрузка моделей:

```
По данной ссылке доступны тестовая модель (nnunet_test) и рабочая модель (multitalent_production): 

https://drive.google.com/drive/folders/1SZrMc-2sJCuOprVL_7XcJhZn20O0MaqU?usp=sharing

Загрузите их и распакуйте в `data/models`. Итоговая файловая структура должна выглядеть следующим образом:
data/models
├── nnunet_test
│   └── 3d_fullres
│       └── fold_0
│           ├── checkpoint_final.onnx
│           └── config.json
├── multitalent_production
│   └── 3d_fullres
│       └── fold_0
│           ├── checkpoint_final.onnx
│           └── config.json
```

4. Добавление доступных моделей для инференса в PostgreSQL:

```
docker compose exec backend python scripts/seed_inference_models.py
```

5. Загрузка данных для bulk inference в `data/studies` (ДАННЫЕ ДОЛЖНЫ БЫТЬ В ФОРМАТЕ .zip)

6. Создание виртуального окружения и установка зависимостей для bulk inference (тестировалось на Python 3.10):

```
cd scripts
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

7. Запуск bulk inference:

```
cd ..
python scripts/bulk_inference.py \
    --email admin@webapp.com \
    --password GYSgmXnhFR3p7-4x-2D21A \
    --studies-dir data/studies \
    --output-dir data/results
```

Скрипт будет обрабатывать файл-за-файлом. КТ исследования после обработки и соответствующие сегментации будут находиться в `data/results`. Таблица с результатами обработки будет находиться в `data/reports`.

## Использование production модели

Мы не успели доделать инференс модели `multitalent_production`, поэтому в качестве Proof-Of-Concept описание, как инференсить с помощью неё:

1. Установка MultiTalent и настройка окружения:

```
# Создание окружения
python -m venv venv
source venv/bin/activate

# Установка зависимостей
git clone https://github.com/MIC-DKFZ/MultiTalent.git
cd multitalent
pip install .
pip install dicom2nifti

# Настройка окружения
mkdir data/studies_nifti
```

2. Загрузка модели как описано в Quick Start пн. 3

3. Предобработка данных:

```
python convert_zip_dicom_to_nifti.py -i data/studies -o data/studies_nifti
```

4. Инференс модели:

```
multitalent_predict_from_modelfolder -i data/studies_nifti/ -o data/results/ -m models/MultiTalent_trainer__nnUNetResEncUNetLPlansIso1x1x1__3d_fullres/ -f 0
```

На выходе вы получите бинарные маски для всех датасетов, которые мы использовали при обучении.

## Структура проекта

```
.
├── backend
│   ├── alembic.ini
│   ├── app
│   ├── Dockerfile
│   ├── htmlcov
│   ├── pyproject.toml
│   ├── README.md
│   ├── scripts
│   └── uv.lock
├── data
│   ├── models
│   ├── reports
│   ├── results
│   └── studies
├── deployment.md
├── development.md
├── docker-compose.cpu.yml
├── docker-compose.gpu.yml
├── docker-compose.override.yml
├── docker-compose.traefik.yml
├── docker-compose.yml
├── frontend
│   ├── biome.json
│   ├── blob-report
│   ├── Dockerfile
│   ├── Dockerfile.playwright
│   ├── index.html
│   ├── nginx-backend-not-found.conf
│   ├── nginx.conf
│   ├── node_modules
│   ├── openapi.json
│   ├── openapi-ts.config.ts
│   ├── openapi-ts-error-1758492555431.log
│   ├── package.json
│   ├── package-lock.json
│   ├── playwright.config.ts
│   ├── public
│   ├── README.md
│   ├── src
│   ├── test-results
│   ├── tests
│   ├── tsconfig.build.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── inference-service
│   ├── app
│   ├── Dockerfile.cpu
│   ├── Dockerfile.gpu
│   ├── pyproject.cpu.toml
│   ├── pyproject.toml
│   ├── README.md
│   ├── uv.cpu.lock
│   └── uv.lock
├── old_readme.md
├── README.md
├── scripts
│   ├── build-push.sh
│   ├── build.sh
│   ├── bulk_inference.py
│   ├── cleanup_incomplete_studies.py
│   ├── deploy.sh
│   ├── generate-client.sh
│   ├── __pycache__
│   ├── README_BULK_INFERENCE.md
│   ├── report_generator.py
│   ├── requirements.txt
│   ├── test-local.sh
│   └── test.sh
├── temp
│   ├── entry_points.py
│   ├── inference
│   ├── onnx_export.py
│   ├── postprocessing
│   ├── preprocessing
│   └── venv
└── tooling.md

26 directories, 54 files
```