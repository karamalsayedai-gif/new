import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/timezone.dart' as tz;
import 'package:timezone/data/latest_all.dart' as tzdata;
import '../database/database_helper.dart';
import 'formatters.dart';

class NotificationService {
  static final NotificationService _instance =
      NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    tzdata.initializeTimeZones();

    const androidSettings =
        AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: iosSettings,
    );

    await _plugin.initialize(settings);
    _initialized = true;
  }

  Future<void> requestPermissions() async {
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
    await _plugin
        .resolvePlatformSpecificImplementation<
            IOSFlutterLocalNotificationsPlugin>()
        ?.requestPermissions(alert: true, badge: true, sound: true);
  }

  static const _details = NotificationDetails(
    android: AndroidNotificationDetails(
      'debt_reminders',
      'تذكيرات الديون',
      channelDescription: 'تنبيهات بالديون المستحقة على العملاء',
      importance: Importance.high,
      priority: Priority.high,
    ),
    iOS: DarwinNotificationDetails(),
  );

  /// يجدول تذكيراً يومياً في الساعة المحددة، يفحص الديون القديمة.
  Future<void> scheduleDailyReminder({
    required int hour,
    required int minute,
    required int daysThreshold,
  }) async {
    await init();
    await cancelAll();

    final overdue = await DatabaseHelper().getOverdueDebtors(daysThreshold);
    if (overdue.isEmpty) return;

    final total = overdue.fold<double>(
        0, (s, row) => s + ((row['balance'] as num?)?.toDouble() ?? 0));

    final body = overdue.length == 1
        ? '${overdue.first['name']} مدين لك بمبلغ ${Formatters.currency((overdue.first['balance'] as num).toDouble())}'
        : 'لديك ${overdue.length} عملاء بديون قديمة بإجمالي ${Formatters.currency(total)}';

    await _plugin.zonedSchedule(
      1001,
      '🔔 تذكير بالديون المستحقة',
      body,
      _nextInstanceOf(hour, minute),
      _details,
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      matchDateTimeComponents: DateTimeComponents.time,
    );
  }

  /// إشعار فوري (للاختبار أو التنبيه اللحظي).
  Future<void> showNow(String title, String body) async {
    await init();
    await _plugin.show(
      DateTime.now().millisecondsSinceEpoch ~/ 1000,
      title,
      body,
      _details,
    );
  }

  Future<void> cancelAll() async {
    await _plugin.cancelAll();
  }

  tz.TZDateTime _nextInstanceOf(int hour, int minute) {
    final now = tz.TZDateTime.now(tz.local);
    var scheduled =
        tz.TZDateTime(tz.local, now.year, now.month, now.day, hour, minute);
    if (scheduled.isBefore(now)) {
      scheduled = scheduled.add(const Duration(days: 1));
    }
    return scheduled;
  }
}
