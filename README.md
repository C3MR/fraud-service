# Fraud Scoring Service

خدمة تقييم احتيال المعاملات المالية. نقل نموذج تعلُّم آلي مُدرَّب من دفتر Jupyter
إلى خدمة نظيفة: معمارية طبقية، واجهة REST مُتحقَّق منها، حاوية Docker،
ومجموعة اختبارات.

## البرنامج التدريبي

- المتدرّب: عمر حيدر
- البرنامج: ممارسات هندسة البرمجيات لأنظمة الذكاء الاصطناعي (الفوج الأول)
- رمز المقرّر: SDA-AIE-113
- الجهة: SDAIA Academy — https://github.com/SDAIAAcademy
- المدرّب: MohammadYusif

## الفكرة

نموذج `fraud_xgb_v3` (الإصدار `v3.2.0`) يعطي لكل معاملة احتمال كونها احتيالية،
والخدمة تحوّل الاحتمال إلى قرار وفق حدود مُعتمَدة:

- `>= 0.85` → BLOCK (حظر)
- `0.70 – 0.85` → REVIEW (مراجعة بشرية)
- `< 0.70` → ALLOW (سماح)

تُقدَّم بطريقتين: معالجة دفعية لملف CSV، وواجهة REST لتقييم معاملة واحدة آنيًّا.

## المعمارية

مبنية على العمارة النظيفة؛ الاعتماد يتّجه للداخل، وطبقة `domain` لا تعتمد على أي
إطار خارجي. `sklearn`/`joblib` تُستورَد فقط في `adapters`.

```
src/fraud_service/
  domain/         entities.py, policies.py   (المنطق الأساسي، بلا أطر)
  service/        scorer.py, interfaces.py    (تنسيق التقييم عبر Model Protocol)
  adapters/       sklearn_model.py            (الوحيد الذي يستورد joblib/sklearn)
  api/            app.py, routes.py, schemas.py
  config.py       إعدادات مُتحقَّقة (pydantic-settings)
  logging_setup.py  لوقات JSON (structlog)
  batch.py        المعالجة الدفعية (نقطة التجميع)
tests/            unit, integration, behavioural
data/, models/    البيانات والنموذج
payloads/         عيّنات صحيحة/مشوّهة لاختبار العقد
Dockerfile, docker-compose.yml, Makefile, pyproject.toml
```

## المتطلّبات

- Python 3.12+
- Docker Desktop (اختياري، لتشغيل الحاوية)
- Git

## متغيّرات البيئة

كل الإعدادات عبر كائن `Settings` واحد (بادئة `FRAUD_`). لا يوجد مفتاح API خارجي؛
النموذج محلّي ضمن `models/`.

| المتغيّر | الافتراضي | الوصف |
|---|---|---|
| `FRAUD_MODEL_PATH` | `models/fraud_xgb_v3.joblib` | مسار النموذج (يفشل الإقلاع إن لم يوجد) |
| `FRAUD_BLOCK_THRESHOLD` | `0.85` | حدّ الحظر (بين 0.5 و0.99) |
| `FRAUD_LOG_LEVEL` | `INFO` | DEBUG / INFO / WARNING / ERROR |
| `FRAUD_REGISTRY_TOKEN` | — | سرّي واختياري (يُخفى في اللوقات) |

## التثبيت

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows
# source .venv/bin/activate       # macOS/Linux
pip install -e ".[dev]"
```

## التشغيل

### معالجة دفعية

```bash
python -m fraud_service.batch
```

المخرجات المتوقّعة:

```
Loaded model fraud_xgb v3.2.0
Scored 5,000 transactions -> scored.csv (block: 311, review: 320, allow: 4369)
```

### واجهة REST

```bash
fastapi dev src/fraud_service/api/app.py
curl -s http://localhost:8000/v1/predict -d @payloads/sample.json -H "content-type: application/json"
```

المخرجات المتوقّعة:

```json
{
  "transaction_id": "TXN-2026-00042",
  "fraud_probability": 0.557066,
  "decision": "allow",
  "model_version": "v3.2.0",
  "trace_id": "27025dec6ec14649"
}
```

النقاط: `POST /v1/predict`، و`GET /v1/health` (نبض)، و`GET /v1/ready` (جهوزية،
تُرجع 503 قبل تحميل النموذج).

### Docker

```bash
docker compose up --build -d
docker compose ps
```

الصورة متعدّدة المراحل، تعمل بمستخدم غير جذر، وبها فحص صحّة على `/v1/ready`.
أرقام الأحجام وزمن الاستجابة في `BENCHMARKS.md`.

## الاختبارات

```bash
pytest              # الكل + تقرير التغطية
pytest -m unit      # وحدة فقط (< ثانية)
```

المستويات: unit (المنطق)، integration (العقد عبر TestClient وكل الحمولات
المشوّهة → 4xx)، behavioural (النموذج الحقيقي + الملف الذهبي لكشف الانحراف).
النتيجة الحالية: 57 اختبارًا ناجحًا، تغطية 94%.

## CI/CD

ملف `.github/workflows/ci.yml` يُشغّل الفحص (ruff، import-linter، mypy)
والاختبارات بالتوازي، ثم يبني الصورة ويختبر دخانها، وينشرها إلى GHCR
(موسومة بـ Git SHA) عند الدفع إلى `main` فقط.

## الأسرار وممارسات Git

- `.gitignore` يستبعد البيئات الافتراضية والملفات المولّدة والأسرار.
- لا تُخزَّن أسرار في المستودع؛ الحقول السرّية `SecretStr` وتُخفى في اللوقات.
- سجلّ التزامات تدريجي برسائل ذات معنى (لابًا بلاب)، لا رفعة واحدة ضخمة.
- إجراء تسريب الأسرار في `INCIDENT.md`.
