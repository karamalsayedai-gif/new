import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:image_picker/image_picker.dart';

class ImageStorage {
  static final ImagePicker _picker = ImagePicker();

  /// يلتقط/يختار صورة وينسخها لمجلد التطبيق الدائم، ويعيد المسار.
  static Future<String?> pickAndSave(ImageSource source) async {
    final picked = await _picker.pickImage(
      source: source,
      imageQuality: 70,
      maxWidth: 1600,
    );
    if (picked == null) return null;

    final dir = await getApplicationDocumentsDirectory();
    final receiptsDir = Directory(p.join(dir.path, 'receipts'));
    if (!await receiptsDir.exists()) {
      await receiptsDir.create(recursive: true);
    }

    final ext = p.extension(picked.path);
    final fileName = 'receipt_${DateTime.now().millisecondsSinceEpoch}$ext';
    final savedPath = p.join(receiptsDir.path, fileName);
    await File(picked.path).copy(savedPath);
    return savedPath;
  }

  /// يحذف صورة من التخزين لو موجودة.
  static Future<void> delete(String? path) async {
    if (path == null || path.isEmpty) return;
    final file = File(path);
    if (await file.exists()) {
      await file.delete();
    }
  }

  static bool exists(String? path) {
    if (path == null || path.isEmpty) return false;
    return File(path).existsSync();
  }
}
