/// قائمة العملات المدعومة وأسعار الصرف الافتراضية مقابل الجنيه المصري.
/// المستخدم يقدر يعدّل سعر الصرف وقت تسجيل المعاملة.
class CurrencyInfo {
  final String code; // الرمز المعروض (ج.م, USD...)
  final String name; // الاسم بالعربي
  final double defaultRate; // سعر الصرف الافتراضي مقابل العملة الأساسية (ج.م)

  const CurrencyInfo({
    required this.code,
    required this.name,
    required this.defaultRate,
  });
}

class Currencies {
  /// العملة الأساسية للتطبيق - كل الأرصدة تُحسب بها.
  static const String base = 'ج.م';

  static const List<CurrencyInfo> all = [
    CurrencyInfo(code: 'ج.م', name: 'جنيه مصري', defaultRate: 1.0),
    CurrencyInfo(code: 'USD', name: 'دولار أمريكي', defaultRate: 48.0),
    CurrencyInfo(code: 'SAR', name: 'ريال سعودي', defaultRate: 12.8),
    CurrencyInfo(code: 'AED', name: 'درهم إماراتي', defaultRate: 13.1),
    CurrencyInfo(code: 'EUR', name: 'يورو', defaultRate: 52.0),
    CurrencyInfo(code: 'KWD', name: 'دينار كويتي', defaultRate: 156.0),
  ];

  static CurrencyInfo byCode(String code) {
    return all.firstWhere(
      (c) => c.code == code,
      orElse: () => all.first,
    );
  }

  static bool isBase(String code) => code == base;
}
