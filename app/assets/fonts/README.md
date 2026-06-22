# خطوط التطبيق — Cairo

ضع ملفات خط **Cairo** هنا حتى تُحمَّل تلقائيًا وتُستخدم في كل الواجهة:

```
app/assets/fonts/Cairo-Regular.ttf
app/assets/fonts/Cairo-Bold.ttf
```

- المصدر: Google Fonts — Cairo (رخصة OFL، مجانية للاستخدام والتوزيع):
  https://fonts.google.com/specimen/Cairo
- يكفي وجود `Cairo-Regular.ttf`؛ أضف `Cairo-Bold.ttf` لتحسين العناوين.
- التحميل يتم في `app/ui/branding.py: install_fonts` عبر `QFontDatabase`،
  والقوالب تضع `Cairo` أولًا في عائلة الخط، فإن لم تتوفر الملفات يسقط النظام
  تلقائيًا إلى `Segoe UI / Tahoma` دون أي خطأ.
- ملفات الخط مُدرجة في حزمة PyInstaller عبر `datas` في
  `packaging/showroom_erp.spec`، فتعمل بعد التغليف على ويندوز.

> لم تُرفق ملفات الخط الثنائية في المستودع لأسباب ترخيص/حجم؛ نزّلها مرة واحدة
> وضعها هنا قبل البناء.
