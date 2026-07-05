# 4. تصميم قاعدة البيانات (SQLite)

## اصطلاحات عامة

- كل الجداول `STRICT`، المفتاح الأساسي `id INTEGER PRIMARY KEY` (rowid).
- **المبالغ:** `INTEGER` بالقرش (1 جنيه = 100). أعمدة المبالغ تنتهي بـ `_amount`/`_cost`/`_price`.
- **التواريخ:** `TEXT` بصيغة ISO-8601 (`2026-07-05T21:30:00`)، وأعمدة التاريخ فقط `date` بصيغة `2026-07-05`.
- **الحالات (status):** `TEXT` مقيدة بـ `CHECK (status IN (...))`.
- أعمدة التتبع القياسية في كل جدول مستندي: `created_at`, `created_by → users.id`, وعند التعديل `updated_at`, `updated_by`، وعند الإلغاء `cancelled_at`, `cancelled_by`, `cancel_reason`.
- الحذف الفعلي مسموح فقط للسجلات المرجعية غير المرتبطة بأي حركة؛ عدا ذلك تعطيل (`is_active = 0`) أو إلغاء.
- `ON DELETE RESTRICT` هو الافتراضي لكل المفاتيح الأجنبية (لا حذف متسلسل لبيانات مالية أبدًا).

## 4.1 النظام والمستخدمون

### `users`
| العمود | النوع | ملاحظات |
|---|---|---|
| id | INTEGER PK | |
| username | TEXT UNIQUE NOT NULL | |
| password_hash | TEXT NOT NULL | Argon2id أو PBKDF2 (بدون تخزين نص صريح أبدًا) |
| full_name | TEXT NOT NULL | |
| role_id | FK → roles | |
| is_active | INTEGER (0/1) | التعطيل بدل الحذف |
| must_change_password | INTEGER (0/1) | |
| created_at / created_by | | |

### `roles`
(id, name UNIQUE, description, is_system 0/1 — الأدوار الثلاثة الافتراضية system لا تُحذف)

### `permissions`
(id, code UNIQUE مثل `sales.discount.above_limit`, description, module)

### `role_permissions`
(role_id FK, permission_id FK, PRIMARY KEY(role_id, permission_id))

### `sessions`
سجل دخول/خروج: (id, user_id FK, login_at, logout_at NULL, logout_type CHECK IN ('manual','idle_lock','forced','app_close'), machine_name)

### `settings`
مفتاح/قيمة مع أنواع: (key TEXT PK, value TEXT, value_type CHECK IN ('int','text','bool','money','json'), updated_at, updated_by). أمثلة مفاتيح: `tax_rate_bp` (نقاط أساس), `cashier_max_discount_bp`, `manager_max_discount_bp`, `idle_lock_minutes`, `reservation_default_days`, `stagnant_vehicle_days`, `low_stock_default`, `doc_numbering_reset` , `shop_name`, `shop_phone`, `receipt_footer_text`, `backup_daily_keep`…

### `audit_log`
| العمود | ملاحظات |
|---|---|
| id, occurred_at, user_id FK | |
| action | CHECK IN ('create','update','cancel','approve','login','logout','denied_attempt','backup','restore','price_change','status_change','settings_change','shift_open','shift_close','manual_points') |
| entity_type, entity_id | اسم الجدول + رقم السجل |
| summary | نص مقروء («خصم 500ج على INV-2026-0041») |
| old_value_json, new_value_json | القيمة قبل/بعد للحقوق الحساسة |
- **قاعدة:** جدول append-only — لا UPDATE ولا DELETE عليه من التطبيق إطلاقًا (Trigger يمنع).

### `approvals`
(id, requested_by FK users, approved_by FK users, action_code, entity_type, entity_id, value_amount, reason, status CHECK IN ('approved','rejected'), created_at)

## 4.2 الكتالوج والمخزون

### `brands` (id, name UNIQUE, is_active)
### `models` (id, brand_id FK, name, engine_cc INTEGER NULL, is_active, UNIQUE(brand_id, name))
### `colors` (id, name UNIQUE)
### `categories` (id, name, parent_id FK NULL — لتصنيف الأصناف العامة شجريًا)

### `vehicles` — **قلب النظام: كل صف = موتوسيكل واحد بعينه**
| العمود | النوع/القيد | ملاحظات |
|---|---|---|
| id | PK | |
| stock_no | TEXT UNIQUE | كود داخلي يولَّد تلقائيًا `V-2026-0001` |
| model_id | FK models NOT NULL | يجر معه الماركة |
| color_id | FK colors | |
| manufacture_year | INTEGER | |
| chassis_no | TEXT UNIQUE NOT NULL COLLATE NOCASE | رقم الشاسيه |
| engine_no | TEXT UNIQUE NOT NULL COLLATE NOCASE | رقم الموتور |
| condition | CHECK IN ('new','used') | قابلة للتحويل مع تسجيل الحركة |
| status | CHECK IN ('in_stock','reserved','sold','returned_to_supplier','draft') | تُدار بآلة حالة فقط |
| purchase_invoice_item_id | FK NULL | مصدر الدخول (شراء) |
| tradein_sales_invoice_id | FK NULL | مصدر الدخول (استبدال من عميل) |
| base_cost | INTEGER | تكلفة الشراء/التقييم |
| extra_cost_total | INTEGER DEFAULT 0 | مجموع مصاريف الوحدة (محسوب من vehicle_costs) |
| total_cost | INTEGER (generated أو يحدَّث بمعاملة) | base + extra |
| list_price | INTEGER | سعر البيع المعلن |
| notes | TEXT | |
| entered_stock_at | TEXT | لتقرير الركود |
- CHECK: `(purchase_invoice_item_id IS NOT NULL) + (tradein_sales_invoice_id IS NOT NULL) <= 1` مع سماح كليهما NULL لرصيد افتتاحي.

### `vehicle_costs` — مصاريف إضافية على وحدة
(id, vehicle_id FK, cost_type CHECK IN ('transport','preparation','brokerage','license','other'), amount, expense_voucher_id FK NULL — لو صُرفت نقدًا من الخزنة, notes, created_at, created_by)

### `vehicle_movements` — سجل حركة الوحدة الكامل (append-only)
(id, vehicle_id FK, movement_type CHECK IN ('purchased','opening_balance','tradein_received','price_changed','cost_added','reserved','reservation_released','sold','sale_returned','returned_to_supplier','condition_changed','stocktake_adjust'), ref_table, ref_id, details_json, occurred_at, user_id FK)

### `products` — الأصناف الكمية العامة
(id, sku TEXT UNIQUE NULL, barcode TEXT UNIQUE NULL, name NOT NULL, category_id FK, unit TEXT DEFAULT 'قطعة', cost_price INTEGER — متوسط تكلفة متحرك, sale_price INTEGER, qty_on_hand INTEGER DEFAULT 0, low_stock_threshold INTEGER DEFAULT 0, is_active)

### `stock_movements` — حركات مخزون الأصناف الكمية (append-only)
(id, product_id FK, movement_type CHECK IN ('purchase','sale','purchase_return','sale_return','stocktake_adjust','opening_balance'), qty_delta INTEGER — موجب/سالب, unit_cost INTEGER NULL, ref_table, ref_id, occurred_at, user_id)
- `qty_on_hand` يُحدَّث في نفس المعاملة، وscript جرد يتحقق دوريًا أن المجموع = الرصيد.

### `stocktakes` + `stocktake_lines`
جرد: (id, stocktake_no, scope CHECK IN ('vehicles','products','both'), status CHECK IN ('draft','posted','cancelled'), started_at, posted_at, created_by, approved_by)
البنود: (id, stocktake_id FK, vehicle_id FK NULL, product_id FK NULL, expected_qty, counted_qty, note) — فروق الاعتماد تولّد stock_movements/vehicle_movements.

## 4.3 الأطراف: عملاء / ضامنون / موردون / مندوبون

### `customers`
(id, name NOT NULL, phone NOT NULL, phone2 NULL, national_id TEXT UNIQUE NULL — إلزامي عند آجل/تقسيط بقاعدة عمل, address, notes, salesperson_id FK NULL, points_balance INTEGER DEFAULT 0, is_active, created_at, created_by)

### `customer_points_log`
(id, customer_id FK, points_delta INTEGER, reason TEXT NOT NULL, user_id, created_at) — يدوي فقط في الإصدار الأول.

### `guarantors`
(id, name, phone, national_id, address, notes, created_at) — الضامن كيان مستقل قابل لإعادة الاستخدام، والربط بالعقد في `installment_plans.guarantor_id`.

### `suppliers`
(id, name, phone, address, notes, is_active, created_at)

### `salespersons`
(id, name, phone, is_active) — مندوب البيع؛ لا حساب دخول له (إلا لو أنشئ له مستخدم).

> **كشوف الحساب** لا تحتاج جداول خاصة: تُبنى من party_transactions (أدناه).

### `party_transactions` — دفتر حركة موحّد للعملاء والموردين
| العمود | ملاحظات |
|---|---|
| id, party_type CHECK IN ('customer','supplier'), party_id | |
| direction | CHECK IN ('debit','credit') — debit: زاد ما علينا/له، حسب النوع |
| amount INTEGER | |
| txn_type | CHECK IN ('sale_invoice','purchase_invoice','receipt','payment','sale_return','purchase_return','installment_due','opening_balance','manual_adjust') |
| ref_table, ref_id, occurred_at, user_id, notes | |
- رصيد العميل/المورد = مجموع الحركات، ويُخزن رصيد مشتق `balance_cache` في جدول الطرف يُحدَّث بنفس المعاملة للسرعة.

## 4.4 المشتريات

### `purchase_invoices`
(id, doc_no TEXT UNIQUE `PUR-2026-0001`, supplier_id FK, invoice_date, subtotal, expenses_total, grand_total, paid_amount, status CHECK IN ('posted','cancelled'), payment_type CHECK IN ('cash','credit','mixed'), notes, created_at/by, cancelled_at/by/reason)

### `purchase_invoice_items`
(id, purchase_invoice_id FK, line_type CHECK IN ('vehicle','product'), vehicle_id FK NULL — يُنشأ صف vehicle مع الفاتورة, product_id FK NULL, qty INTEGER DEFAULT 1 — دائمًا 1 للوحدات, unit_cost INTEGER, line_total INTEGER)
- CHECK: سطر vehicle ⇒ qty=1 وvehicle_id NOT NULL؛ سطر product ⇒ product_id NOT NULL.

### `purchase_expenses` — مصاريف على الفاتورة (نقل/سمسرة)
(id, purchase_invoice_id FK, expense_type, amount, allocation CHECK IN ('distribute_by_value','distribute_equal','no_distribute'), notes)
- التوزيع على تكلفة الوحدات يُسجل في `vehicle_costs` ضمن نفس المعاملة.

### `purchase_returns` + `purchase_return_items`
(id, doc_no `PRT-…`, purchase_invoice_id FK, supplier_id, return_date, total, refund_method_id FK payment_methods NULL — أو خصم من رصيد المورد, status, notes, created_at/by)
البنود: (id, purchase_return_id FK, purchase_invoice_item_id FK, vehicle_id NULL, product_id NULL, qty, amount)

## 4.5 المبيعات والحجز

### `sales_invoices`
| العمود | ملاحظات |
|---|---|
| id, doc_no UNIQUE `INV-2026-0001`, invoice_date | |
| customer_id FK NULL | إلزامي إن كان فيها وحدة موتوسيكل أو آجل/تقسيط؛ NULL = عميل نقدي عابر للإكسسوارات |
| salesperson_id FK NULL | |
| sale_kind | CHECK IN ('cash','credit','installment') |
| reservation_id FK NULL | لو الفاتورة تحويل من حجز |
| subtotal | مجموع البنود قبل الخصم |
| discount_type CHECK IN ('none','percent','amount'), discount_value, discount_amount | خصم مستوى الفاتورة |
| fees_total | مصاريف على الفاتورة (رخصة/توصيل…) من جدول invoice_fees |
| tax_rate_bp, tax_amount | لقطة نسبة الضريبة وقت الفاتورة |
| grand_total | subtotal − discounts + fees + tax |
| tradein_credit | قيمة المستعمل المستلم (تخفض المطلوب سداده) |
| paid_amount | المحصل حتى الآن (مشتق من التحصيلات، cache) |
| shift_id FK | الوردية التي أنشئت فيها |
| status | CHECK IN ('posted','cancelled') |
| notes, created_at/by, cancelled_* | |

### `sales_invoice_items`
(id, sales_invoice_id FK, line_type CHECK IN ('vehicle','product'), vehicle_id NULL, product_id NULL, qty DEFAULT 1, unit_price, line_discount_type/value/amount, line_total, cost_snapshot INTEGER — لقطة تكلفة وقت البيع لحساب الربح الثابت)

### `invoice_fees`
(id, sales_invoice_id FK, fee_type TEXT, amount, notes)

### `reservations` — الحجز والعربون
(id, doc_no `RSV-…`, vehicle_id FK, customer_id FK, deposit_amount, reserved_at, expires_at, status CHECK IN ('active','converted','cancelled','expired'), converted_invoice_id FK NULL, refund_receipt_id FK NULL, notes, created_at/by)
- العربون يُقبض بسند قبض مرتبط، وعند التحويل لفاتورة يُخصم من المطلوب.

### `sales_returns` + `sales_return_items`
(id, doc_no `SRT-…`, sales_invoice_id FK, customer_id, return_date, total, refund_method_id NULL — أو رصيد دائن للعميل, restocking_fee INTEGER DEFAULT 0, status, reason, created_at/by)
البنود: (id, sales_return_id FK, sales_invoice_item_id FK, vehicle_id NULL, product_id NULL, qty, amount)

### `tradeins` — استلام مستعمل ضمن بيع
(id, sales_invoice_id FK, received_vehicle_id FK vehicles — الوحدة الجديدة المنشأة كمستعمل, evaluated_value INTEGER, evaluated_by FK users, notes)

## 4.6 التقسيط

### `installment_plans`
| العمود | ملاحظات |
|---|---|
| id, plan_no UNIQUE `PLN-2026-0001` | |
| sales_invoice_id FK UNIQUE | عقد لكل فاتورة تقسيط |
| customer_id FK, guarantor_id FK NULL | الضامن إلزامي بقاعدة إعداد |
| principal | أصل المبلغ الممول = grand_total − down_payment − tradein_credit |
| interest_rate_bp | نسبة الفائدة/الربح (نقاط أساس، Flat حسب افتراض A4) |
| interest_amount | محسوبة ومجمدة عند الإنشاء |
| total_payable | principal + interest |
| down_payment | المقدم |
| months_count, installment_amount | عدد الأقساط وقيمة القسط (الأخير يمتص كسر التقريب) |
| first_due_date, due_day INTEGER 1–28 | يوم التحصيل الثابت |
| status | CHECK IN ('active','completed','early_settled','defaulted','cancelled') |
| early_settlement_discount INTEGER NULL, closed_at NULL | |
| contract_printed_at, notes, created_at/by | |

### `installments` — جدول الأقساط
(id, plan_id FK, seq_no INTEGER, due_date, amount, paid_amount INTEGER DEFAULT 0, status CHECK IN ('pending','partial','paid','waived'), paid_at NULL, UNIQUE(plan_id, seq_no))

### `installment_payments` — كل عملية تحصيل (تدعم الجزئي وتوزيع دفعة على أكثر من قسط)
(id, receipt_voucher_id FK vouchers, installment_id FK, amount, created_at, created_by)
- سند القبض الواحد قد يغطي عدة أقساط ⇒ عدة صفوف هنا بنفس receipt_voucher_id.

## 4.7 المالية والخزنة

### `payment_methods`
(id, name, kind CHECK IN ('cash','wallet','instapay','bank'), is_active, display_order)
- بذور افتراضية: كاش، إنستا باي، فودافون كاش، تحويل بنكي. الرصيد مشتق من finance_transactions (+ cache).

### `vouchers` — سندات القبض والصرف (مستند موحد)
| العمود | ملاحظات |
|---|---|
| id, doc_no UNIQUE (`RCV-…` قبض / `PAY-…` صرف), voucher_type CHECK IN ('receipt','payment') | |
| amount, payment_method_id FK | |
| party_type CHECK IN ('customer','supplier','other') , party_id NULL, other_party_name NULL | |
| purpose | CHECK IN ('invoice_payment','installment','reservation_deposit','deposit_refund','supplier_payment','expense','refund','transfer_in','transfer_out','shift_difference','other') |
| ref_table, ref_id | الفاتورة/القسط/الحجز/المصروف المرتبط |
| shift_id FK NULL | إلزامي لسندات الكاش |
| status CHECK IN ('posted','cancelled'), notes, created_at/by, cancelled_* | |

### `expenses` + `expense_categories`
الفئات: (id, name UNIQUE, parent_id NULL, is_active)
المصروف: (id, doc_no `EXP-…`, category_id FK, amount, payment_method_id FK, expense_date, payment_voucher_id FK vouchers, description, shift_id NULL, status, created_at/by)

### `finance_transactions` — دفتر حركة موحد لكل طرق الدفع (append-only)
(id, payment_method_id FK, direction CHECK IN ('in','out'), amount, txn_type CHECK IN ('sale','purchase','installment','deposit','refund','expense','transfer','shift_adjust','opening'), voucher_id FK NULL, ref_table, ref_id, occurred_at, shift_id NULL, user_id)
- كشف حساب أي طريقة دفع = تصفية هذا الجدول. التحويل بين طريقتين = صفان (out + in) بنفس المرجع.

### `shifts` — الورديات
| العمود | ملاحظات |
|---|---|
| id, shift_no UNIQUE `SH-2026-0001` | |
| opened_by FK users, opened_at, opening_cash INTEGER | جرد افتتاحي |
| closed_by FK NULL, closed_at NULL | من أغلق (قد يختلف عمن فتح) |
| expected_cash | محسوب: افتتاحي + مقبوضات كاش − مصروفات كاش |
| counted_cash INTEGER NULL | الجرد الفعلي |
| difference INTEGER NULL | counted − expected (سالب = عجز) |
| difference_approved_by FK NULL, difference_note | |
| status CHECK IN ('open','closed') | وردية مفتوحة واحدة فقط في النظام (فهرس فريد جزئي) |

## 4.8 النسخ الاحتياطي والتنبيهات

### `backups`
(id, file_name, file_path, backup_type CHECK IN ('daily','weekly','monthly','manual','pre_restore','pre_migration'), size_bytes, checksum_sha256, schema_version, integrity_ok INTEGER, created_at, created_by NULL — NULL للتلقائي)

### `notifications`
(id, notif_type CHECK IN ('installment_due','installment_overdue','low_stock','stagnant_vehicle','reservation_expiring','backup_failed','backup_missed','license'), severity CHECK IN ('info','warning','critical'), title, body, ref_table, ref_id, created_at, dismissed_at NULL, dismissed_by NULL)
- تولَّد بمهمة عند بدء التشغيل + كل ساعة، مع منع التكرار (فهرس فريد على النوع+المرجع+اليوم).

### `schema_migrations`
(version INTEGER PK, applied_at, app_version)

## 4.9 مخطط العلاقات المختصر (ERD نصي)

```
brands 1─* models 1─* vehicles *─1 colors
vehicles 1─* vehicle_costs / 1─* vehicle_movements
suppliers 1─* purchase_invoices 1─* purchase_invoice_items *─1 (vehicles | products)
purchase_invoices 1─* purchase_expenses / 1─* purchase_returns
customers 1─* sales_invoices 1─* sales_invoice_items *─1 (vehicles | products)
sales_invoices 1─0..1 installment_plans 1─* installments 1─* installment_payments *─1 vouchers
sales_invoices 1─* invoice_fees / 0..1 tradeins ─1 vehicles(المستعمل الداخل)
customers 1─* reservations *─1 vehicles ; reservations 0..1─ sales_invoices
(customers|suppliers) 1─* party_transactions
payment_methods 1─* finance_transactions *─0..1 vouchers
shifts 1─* (vouchers | sales_invoices | expenses | finance_transactions)
users 1─* كل شيء عبر created_by / audit_log / approvals / sessions
```

## 4.10 استراتيجية الفهرسة (Indexing)

فهارس فريدة: `vehicles(chassis_no)`, `vehicles(engine_no)`, `vehicles(stock_no)`, كل `doc_no`, `products(barcode)`, `customers(national_id)`, `shifts` فهرس فريد جزئي `WHERE status='open'`.

فهارس أداء أساسية:
```sql
CREATE INDEX ix_vehicles_status        ON vehicles(status, model_id);
CREATE INDEX ix_sales_date             ON sales_invoices(invoice_date, status);
CREATE INDEX ix_sales_customer         ON sales_invoices(customer_id);
CREATE INDEX ix_installments_due       ON installments(status, due_date);
CREATE INDEX ix_installments_plan      ON installments(plan_id, seq_no);
CREATE INDEX ix_fin_txn_method_date    ON finance_transactions(payment_method_id, occurred_at);
CREATE INDEX ix_party_txn              ON party_transactions(party_type, party_id, occurred_at);
CREATE INDEX ix_vouchers_shift         ON vouchers(shift_id);
CREATE INDEX ix_vmove_vehicle          ON vehicle_movements(vehicle_id, occurred_at);
CREATE INDEX ix_smove_product          ON stock_movements(product_id, occurred_at);
CREATE INDEX ix_notifications_active   ON notifications(dismissed_at) WHERE dismissed_at IS NULL;
CREATE INDEX ix_audit_entity           ON audit_log(entity_type, entity_id);
CREATE INDEX ix_audit_time             ON audit_log(occurred_at);
```
- البحث النصي السريع (اسم عميل/موديل): `LIKE 'prefix%'` مع COLLATE NOCASE يكفي للحجم المتوقع؛ لو احتجنا بحثًا داخليًا (`%وسط%`) على عشرات الآلاف نضيف FTS5 لاحقًا على (customers.name, vehicles.chassis_no/engine_no).

## 4.11 الترقيم المستندي

جدول `doc_counters` (doc_type TEXT, year INTEGER, last_no INTEGER, PRIMARY KEY(doc_type, year)). التوليد داخل نفس معاملة الحفظ: `UPDATE … SET last_no = last_no + 1 RETURNING last_no` — يضمن تسلسلًا بلا فجوات ولا تكرار. المستندات الملغاة تحتفظ برقمها (الفجوة الممنوعة هي فجوة الإصدار لا الإلغاء).
