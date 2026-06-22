import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../database/database_helper.dart';

/// نسخ احتياطي تلقائي محلي: يعمل تلقائيًا عند فتح التطبيق (مرة كل يوم كحد
/// أقصى) ويحتفظ بآخر [_maxBackups] نسخ داخل تخزين التطبيق الدائم، بدون أي
/// تدخل من المستخدم.
class AutoBackupService {
  static const _maxBackups = 7;
  static const _prefEnabled = 'auto_backup_enabled';
  static const _prefLastRun = 'auto_backup_last_run';

  static Future<Directory> _backupDir() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/auto_backups');
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  static Future<bool> isEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_prefEnabled) ?? true;
  }

  static Future<void> setEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefEnabled, value);
  }

  static Future<DateTime?> lastRunAt() async {
    final prefs = await SharedPreferences.getInstance();
    final iso = prefs.getString(_prefLastRun);
    return iso == null ? null : DateTime.tryParse(iso);
  }

  /// ينشئ نسخة احتياطية جديدة لو النسخ التلقائي مفعّل ومرّ يوم على الأقل
  /// من آخر نسخة. آمن للاستدعاء في كل مرة يُفتح فيها التطبيق.
  static Future<void> runIfDue() async {
    if (!await isEnabled()) return;

    final last = await lastRunAt();
    if (last != null && DateTime.now().difference(last) < const Duration(hours: 24)) {
      return;
    }

    try {
      final data = await DatabaseHelper().exportData();
      // مفيش داعي لعمل نسخة من قاعدة بيانات فاضية.
      final customers = data['customers'] as List? ?? [];
      if (customers.isEmpty) return;

      final json = const JsonEncoder.withIndent('  ').convert(data);
      final dir = await _backupDir();
      final stamp = DateTime.now().toIso8601String().replaceAll(':', '-').split('.').first;
      final file = File('${dir.path}/auto_$stamp.json');
      await file.writeAsString(json);

      await _prune(dir);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(_prefLastRun, DateTime.now().toIso8601String());
    } catch (_) {
      // فشل النسخ الاحتياطي التلقائي لا يجب أن يوقف التطبيق أبداً.
    }
  }

  static Future<void> _prune(Directory dir) async {
    final files = await dir
        .list()
        .where((e) => e is File && e.path.endsWith('.json'))
        .cast<File>()
        .toList();
    files.sort((a, b) => b.path.compareTo(a.path)); // الأحدث أولاً
    for (final f in files.skip(_maxBackups)) {
      await f.delete();
    }
  }

  /// قائمة النسخ الاحتياطية التلقائية المتاحة، الأحدث أولاً.
  static Future<List<File>> listBackups() async {
    final dir = await _backupDir();
    final files = await dir
        .list()
        .where((e) => e is File && e.path.endsWith('.json'))
        .cast<File>()
        .toList();
    files.sort((a, b) => b.path.compareTo(a.path));
    return files;
  }

  static Future<void> restore(File file) async {
    final content = await file.readAsString();
    final data = jsonDecode(content) as Map<String, dynamic>;
    if (!data.containsKey('customers') || !data.containsKey('transactions')) {
      throw const FormatException('ملف النسخة الاحتياطية غير صالح');
    }
    await DatabaseHelper().importData(data);
  }
}
