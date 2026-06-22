import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

class WhatsappHelper {
  /// يفتح محادثة واتساب مع الرقم المحدد ونص جاهز.
  /// [number] لازم يكون بصيغة دولية بدون + أو أصفار (مثال: 201001234567).
  static Future<bool> sendMessage({
    required String number,
    required String message,
    required BuildContext context,
  }) async {
    final encoded = Uri.encodeComponent(message);
    final uri = Uri.parse('https://wa.me/$number?text=$encoded');
    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok && context.mounted) {
        _showError(context, 'تعذّر فتح واتساب. تأكد من تثبيته.');
      }
      return ok;
    } catch (_) {
      if (context.mounted) {
        _showError(context, 'تعذّر فتح واتساب. تأكد من تثبيته.');
      }
      return false;
    }
  }

  /// يتصل بالعميل هاتفياً.
  static Future<void> call({
    required String number,
    required BuildContext context,
  }) async {
    final uri = Uri.parse('tel:$number');
    try {
      final ok = await launchUrl(uri);
      if (!ok && context.mounted) {
        _showError(context, 'تعذّر إجراء الاتصال.');
      }
    } catch (_) {
      if (context.mounted) {
        _showError(context, 'تعذّر إجراء الاتصال.');
      }
    }
  }

  static void _showError(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }
}
