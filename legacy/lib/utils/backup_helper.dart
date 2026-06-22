import 'dart:convert';
import 'dart:io';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import '../database/database_helper.dart';

class BackupResult {
  final bool success;
  final String message;
  const BackupResult(this.success, this.message);
}

class BackupHelper {
  static final _db = DatabaseHelper();

  /// يصدّر كل البيانات كملف JSON ويفتح نافذة المشاركة لحفظه
  /// (على Google Drive أو أي مكان يختاره المستخدم).
  static Future<BackupResult> exportBackup() async {
    try {
      final data = await _db.exportData();
      final json = const JsonEncoder.withIndent('  ').convert(data);

      final dir = await getTemporaryDirectory();
      final stamp = DateTime.now()
          .toIso8601String()
          .replaceAll(':', '-')
          .split('.')
          .first;
      final file = File('${dir.path}/hesabati_backup_$stamp.json');
      await file.writeAsString(json);

      await Share.shareXFiles(
        [XFile(file.path)],
        subject: 'نسخة احتياطية - حساباتي',
        text: 'نسخة احتياطية من بيانات تطبيق حساباتي',
      );

      return const BackupResult(true, 'تم إنشاء النسخة الاحتياطية');
    } catch (e) {
      return BackupResult(false, 'فشل إنشاء النسخة: $e');
    }
  }

  /// يستعيد البيانات من ملف JSON يختاره المستخدم.
  static Future<BackupResult> restoreBackup() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
      );
      if (result == null || result.files.single.path == null) {
        return const BackupResult(false, 'لم يتم اختيار ملف');
      }

      final file = File(result.files.single.path!);
      final content = await file.readAsString();
      final data = jsonDecode(content) as Map<String, dynamic>;

      if (!data.containsKey('customers') ||
          !data.containsKey('transactions')) {
        return const BackupResult(false, 'الملف غير صالح');
      }

      await _db.importData(data);
      return const BackupResult(true, 'تمت استعادة البيانات بنجاح');
    } catch (e) {
      return BackupResult(false, 'فشل الاستعادة: $e');
    }
  }
}
