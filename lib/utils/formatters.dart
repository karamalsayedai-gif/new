import 'package:intl/intl.dart';

class Formatters {
  static String currency(double amount, {String symbol = 'ج.م'}) {
    final formatter = NumberFormat('#,##0.##', 'ar');
    return '${formatter.format(amount.abs())} $symbol';
  }

  static String date(DateTime date) {
    return DateFormat('dd/MM/yyyy', 'ar').format(date);
  }

  static String dateTime(DateTime date) {
    return DateFormat('dd/MM/yyyy  hh:mm a', 'ar').format(date);
  }

  static String relativeDate(DateTime date) {
    final now = DateTime.now();
    final diff = now.difference(date);

    if (diff.inDays == 0) return 'اليوم';
    if (diff.inDays == 1) return 'أمس';
    if (diff.inDays < 7) return 'منذ ${diff.inDays} أيام';
    if (diff.inDays < 30) return 'منذ ${(diff.inDays / 7).floor()} أسابيع';
    if (diff.inDays < 365) return 'منذ ${(diff.inDays / 30).floor()} أشهر';
    return DateFormat('dd/MM/yyyy', 'ar').format(date);
  }

  static String monthYear(String monthStr) {
    try {
      final date = DateFormat('yyyy-MM').parse(monthStr);
      return DateFormat('MMMM yyyy', 'ar').format(date);
    } catch (_) {
      return monthStr;
    }
  }
}
