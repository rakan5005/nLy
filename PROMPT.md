# nLy — Username Availability Checker CLI

## دورك
انت تكمل تطوير أداة nLy. هذه الأداة تفحص توفر اليوزرات على ٦ منصات تواصل اجتماعي. اسم المشروع nLy، مكتوب بـ Python 3.11، يستخدم curl_cffi لتجاوز Cloudflare مع Safari impersonation.

## هيكل المشروع
```
nLy/
  by_nly/
    checker/        # 6 فاحصين - كل منصة لها ملف
    cli/            # واجهة الأوامر + القائمة التفاعلية
    generator/      # مولد يوزرات عشوائية من قوالب
    models/         # enums + نتائج
    http_client.py  # curl_cffi adapter (impersonate=chrome131)
    proxy/          # مدير البروكسي
  tests/            # 50 اختبار وحدة
  pyproject.toml    # pip install -e .
```

## الاوامر
```bash
pip install -e .        # تثبيت
python -m by_nly        # تشغيل القائمة التفاعلية
python -m by_nly generate -p discord -t quad -l 100 --fast -w 20
python -m by_nly update # تحديث من Git
```

## ماذا سوينا (الترتيب الزمني)

### الاصلاحات الحرجة
1. **Telegram**: كان يرجع TAKEN لكل شي لان t.me دايم يرجع 200. صلحناه: يفحص `tgme_page_title`، اذا موجود = TAKEN، اذا لا = AVAILABLE.

2. **Twitter**: كان يستخدم Chrome UA وX.com يرجع SPA shell بدون بيانات. صلحناه: نستخدم `Twitterbot/1.0` UA فيرجع 404 للمستخدمين الغير موجودين و200 للموجودين. Nitter كـ fallback مع 6 instances متوازية بـ asyncio.wait مع FIRST_COMPLETED.

3. **Discord**: اكبر تحدي. عدنا عليه ٦ مرات:
   - endpoint الاساسي: `POST /api/v9/auth/register` مع `check.example.com` كإيميل وهمي
   - validation order في ديسكورد: username check -> captcha
   - اذا رجع `USERNAME_ALREADY_TAKEN` = TAKEN
   - اذا رجع `captcha-required` (بدون username error) = AVAILABLE (لان اليوزر اجتاز فحص التوفر)
   - المشكلة: race conditions مع الجلسات المتزامنة. الحل النهائي: جلسة Safari جديدة لكل فحص مع auto-retry اذا فشل
   - WITHOUT proxy: 8 concurrent (safe), WITH proxy: 40 concurrent

4. **TikTok**: ماكان يشتغل بدون بروكسي. صلحناه: `tiktok.com/oembed?url=...` endpoint رسمي - 200=TAKEN, 400=AVAILABLE. مع urlebird.com و web scraping كـ fallbacks، كلهم بالتوازي via asyncio.gather.

5. **Tellonym**: كان يرجع UNKNOWN بسبب race conditions مع CurlAsyncSession المتزامنة. صلحناه بنفس نهج Discord: جلسة جديدة لكل فحص، semaphore 20، auto-retry.

### تحسينات الاداء
- كل المنصات صار عندها parallel fallbacks (TikTok 3 طرق متوازية، Twitter 6 Nitter instances متوازية)
- قللنا timeouts 30-50% (Telegram 4s, Discord 3s, Tellonym 4s)
- ازلنا double-retry loops (كانت تسبب 9 محاولات بدل 3)
- Session sharing بين workers (بس للـ SessionAdapter مو Safari - هذا يسبب race condition)

### الـ Dashboard
- يعرض كل النتائج: AVAILABLE اخضر، TAKEN احمر، UNKNOWN اصفر، BLOCKED بنفسجي
- احصائية كل ثانية
- `\a` beep عند اكتشاف يوزر متاح

### القوالب (Patterns)
- 2letters, semi2, triple, triple_mixed, semi3, quad, quad_repeat, full, custom
- القائمة التفاعلية مقسمة حسب الفئات

### Git + GitHub
- المستودع: `github.com/rakan5005/nLy` (عام)
- فيه setup.bat و nLy.bat للتشغيل بنقرة وحدة
- `nLy update` = git pull + pip install -e .

## الحالة الحالية لكل منصة

| منصة | TAKEN | AVAILABLE | الطريقة | التزامن | ملاحظات |
|------|:-----:|:---------:|---------|:------:|--------|
| Telegram | ✅ | ✅ | `t.me/{user}` web | 50 safe | اسرع منصة |
| Tellonym | ✅ | ✅ | `tellonym.me/api/accounts/check` + Safari | 20 | fresh session per check |
| Twitter | ✅ | ✅ | `Twitterbot/1.0` UA + Nitter parallel | 50 via session | x.com يحد احياناً |
| Snapchat | ✅ | ✅ | `snapchat.com/add/` + Bitmoji API parallel | 50 via session | Cloudflare ممكن يحظر |
| TikTok | ✅ | ✅ | `oembed` + `urlebird` + `web` parallel | 50 via session | يشتغل بدون بروكسي |
| Discord | ✅ | ✅ | `auth/register` + fresh Safari | 8 بدون / 40 مع بروكسي | يحتاج بروكسي دوار للسرعة العالية |

## الملفات الرئيسية (اقرأها قبل التعديل)

### checker/discord.py
- MAX_CONCURRENT: 8 بدون بروكسي، 40 مع بروكسي
- email: `{username}@check.example.com`
- timeout: 3s
- كل فحص: CurlAsyncSession(impersonate="safari17_0") جديد
- auto-retry مرة وحدة اذا UNKNOWN/RATE_LIMITED
- `proxy_manager` يمرر من `get_checker()` لتدوير البروكسيات

### checker/tellonym.py
- MAX_CONCURRENT: 20
- timeout: 5s
- نفس نهج Discord: جلسة جديدة لكل فحص + retry

### checker/tiktok.py
- 3 طرق متوازية: oembed, urlebird, web
- asyncio.gather مع return_exceptions=True
- max_retries: 1

### checker/twitter.py
- Primary: x.com مع Twitterbot UA
- Fallback: 6 Nitter instances متوازية بـ asyncio.wait(FIRST_COMPLETED)
- timeout: 5s X.com, 4s Nitter

### checker/telegram.py
- t.me/{user} — 200 مع tgme_page_title = TAKEN، بدونها = AVAILABLE
- max_retries: 1, timeout: 4s

### checker/snapchat.py
- web + Bitmoji API بالتوازي
- timeout: 5s web, 4s Bitmoji

### cli/interactive.py
- `_run_check()`: ينشئ shared_session + checker
- يمرر `proxy_manager` للـ checker
- Dashboard يعرض النتائج مباشرة

### cli/main.py
- اوامر Click: generate, check, validate, test-proxy, export, update, patterns

### http_client.py
- SessionAdapter: يغلف CurlAsyncSession(impersonate="chrome131") بواجهة aiohttp-like
- create_session(): ينشئ session مع proxy اختياري

## المشاكل المعروفة

1. **Discord بدون بروكسي**: أقصى سرعة 4-8 فحوصات/ثانية. هذا حد Discord نفسه مو حد الأداة.
2. **nLy.exe ينكسر احياناً**: استخدم `python -m by_nly` بداله. السبب: editable install يفقد الرابط بعد update.
3. **الـ Worker count**: احياناً العمال مايتوزعون صح بسبب الـ semaphore الداخلي لكل checker.
4. **Snapchat مع Cloudflare**: بعد 100-200 فحص ممكن يحظر الـ IP. استخدم بروكسي.
5. **TikTok اذا الـ oembed endpoint تغير**: راح يرجع للـ fallbacks (urlebird, web).

## حدودك

- **لا تغير هيكل المشروع** الا للضرورة
- **لا تستخدم DISCORD_TOKEN كشرط اساسي** — الديسكورد يشتغل بدونه
- **لا تضيف تعقيد بدون فايدة** — الكود الحالي بسيط
- **اي منصة جديدة**: اضف checker + validator + charset + enum
- **قبل اي تغيير**: شغل `python -m pytest tests/` وتأكد 50 passed
- **الـ curl_cffi Safari impersonation**: `safari17_0` يتجاوز Cloudflare بس مايتحمل اكثر من 20-30 جلسة متزامنة
- **CurlAsyncSession لازم ينقفل** بعد الاستخدام: `await saf.close()` في finally
- **الـ Semaphore**: استخدمه للتحكم بالتزامن، لا تستخدم global locks

## اللي مطلوب (منك انت)

1. **ميزة الحجز التلقائي (Auto-Claim)** — اول مايطلع AVAILABLE يحطه فحساب المستخدم. يحتاج توكنات. او عالاقل clipboard copy + beep.

2. **تحسين سرعة Discord اكثر** — مع البروكسي الدوار، ممكن نوصل لسرعات اعلى.

3. **اضافة منصات جديدة** اذا ممكن — Instagram, YouTube, Twitch, Reddit.

4. **تصدير النتائج Live** — حفظ اليوزرات المتاحة في ملف مباشرة اثناء الفحص.

5. **Fix nLy.exe breaking** — المشكلة في editable install مع pip.

6. **Web dashboard** — لوحة تحكم ويب بدل الـ Terminal.

## اختبار
```bash
python -m pytest tests/ -v  # 50 tests must pass
python -m by_nly            # interactive mode must work
```