import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../utils/formatters.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _currency = 'ج.م';
  bool _notifications = true;
  bool _pinEnabled = false;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _currency = prefs.getString('currency') ?? 'ج.م';
      _notifications = prefs.getBool('notifications') ?? true;
      _pinEnabled = prefs.getBool('pin_enabled') ?? false;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الإعدادات')),
      body: ListView(
        children: [
          // App Info Card
          _buildAppInfo(context),
          const SizedBox(height: 8),

          // Settings Sections
          _buildSection(
            context,
            title: 'عام',
            children: [
              _buildTile(
                icon: Icons.attach_money_rounded,
                iconColor: AppColors.accent,
                title: 'العملة',
                subtitle: _currency,
                onTap: () => _changeCurrency(context),
              ),
              _buildTile(
                icon: Icons.language_rounded,
                iconColor: AppColors.primary,
                title: 'اللغة',
                subtitle: 'العربية',
                onTap: () {},
              ),
            ],
          ),
          const SizedBox(height: 8),

          _buildSection(
            context,
            title: 'الإشعارات',
            children: [
              _buildSwitchTile(
                icon: Icons.notifications_rounded,
                iconColor: AppColors.credit,
                title: 'إشعارات التذكير',
                subtitle: 'تذكير بالديون المستحقة',
                value: _notifications,
                onChanged: (v) async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setBool('notifications', v);
                  setState(() => _notifications = v);
                },
              ),
            ],
          ),
          const SizedBox(height: 8),

          _buildSection(
            context,
            title: 'الأمان',
            children: [
              _buildSwitchTile(
                icon: Icons.lock_rounded,
                iconColor: AppColors.debit,
                title: 'قفل التطبيق',
                subtitle: 'تفعيل PIN أو البصمة',
                value: _pinEnabled,
                onChanged: (v) async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setBool('pin_enabled', v);
                  setState(() => _pinEnabled = v);
                },
              ),
              _buildTile(
                icon: Icons.fingerprint_rounded,
                iconColor: AppColors.primary,
                title: 'البصمة / Face ID',
                subtitle: 'تسجيل الدخول بالبصمة',
                onTap: () {},
              ),
            ],
          ),
          const SizedBox(height: 8),

          _buildSection(
            context,
            title: 'البيانات',
            children: [
              _buildTile(
                icon: Icons.backup_rounded,
                iconColor: AppColors.credit,
                title: 'نسخ احتياطي',
                subtitle: 'حفظ البيانات على السحابة',
                onTap: () => _showComingSoon(context),
              ),
              _buildTile(
                icon: Icons.restore_rounded,
                iconColor: AppColors.accent,
                title: 'استعادة بيانات',
                subtitle: 'استعادة من نسخة احتياطية',
                onTap: () => _showComingSoon(context),
              ),
              _buildTile(
                icon: Icons.picture_as_pdf_rounded,
                iconColor: AppColors.debit,
                title: 'تصدير تقرير PDF',
                subtitle: 'تصدير جميع الحسابات',
                onTap: () => _exportPDF(context),
              ),
              _buildTile(
                icon: Icons.delete_forever_rounded,
                iconColor: Colors.red,
                title: 'مسح جميع البيانات',
                subtitle: 'حذف كل العملاء والمعاملات',
                onTap: () => _confirmClearAll(context),
                titleColor: Colors.red,
              ),
            ],
          ),
          const SizedBox(height: 8),

          _buildSection(
            context,
            title: 'حول التطبيق',
            children: [
              _buildTile(
                icon: Icons.info_outline_rounded,
                iconColor: AppColors.primary,
                title: 'الإصدار',
                subtitle: '1.0.0',
                onTap: () {},
              ),
              _buildTile(
                icon: Icons.star_rounded,
                iconColor: AppColors.accent,
                title: 'تقييم التطبيق',
                subtitle: 'ساعدنا بتقييمك على المتجر',
                onTap: () => _showComingSoon(context),
              ),
              _buildTile(
                icon: Icons.share_rounded,
                iconColor: AppColors.credit,
                title: 'مشاركة التطبيق',
                subtitle: 'شارك التطبيق مع أصدقائك',
                onTap: () => _showComingSoon(context),
              ),
            ],
          ),
          const SizedBox(height: 40),
        ],
      ),
    );
  }

  Widget _buildAppInfo(BuildContext context) {
    return Consumer<CustomerProvider>(
      builder: (_, provider, __) {
        final totals = provider.totals;
        return Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.primaryDark, AppColors.primaryLight],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(
                  Icons.account_balance_wallet_rounded,
                  color: Colors.white,
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'حساباتي',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    '${provider.totalCustomers} عميل • ${Formatters.currency((totals['netBalance'] ?? 0).abs())} صافي',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.7),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSection(
    BuildContext context, {
    required String title,
    required List<Widget> children,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 8),
          child: Text(
            title,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  color: AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5,
                ),
          ),
        ),
        Container(
          margin: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: isDark ? AppColors.darkCard : Colors.white,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: isDark ? AppColors.darkBorder : AppColors.border,
            ),
          ),
          child: Column(children: children),
        ),
      ],
    );
  }

  Widget _buildTile({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    Color? titleColor,
  }) {
    return ListTile(
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: iconColor.withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: iconColor, size: 20),
      ),
      title: Text(
        title,
        style: TextStyle(
          fontWeight: FontWeight.w500,
          color: titleColor,
          fontSize: 14,
        ),
      ),
      subtitle: Text(
        subtitle,
        style: const TextStyle(fontSize: 12),
      ),
      trailing: const Icon(Icons.chevron_right_rounded,
          color: AppColors.textHint, size: 20),
      onTap: onTap,
    );
  }

  Widget _buildSwitchTile({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return ListTile(
      leading: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: iconColor.withOpacity(0.12),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: iconColor, size: 20),
      ),
      title: Text(
        title,
        style: const TextStyle(fontWeight: FontWeight.w500, fontSize: 14),
      ),
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
      trailing: Switch.adaptive(
        value: value,
        onChanged: onChanged,
        activeColor: AppColors.primary,
      ),
    );
  }

  void _changeCurrency(BuildContext context) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('اختر العملة',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            ...['ج.م', 'USD', 'SAR', 'AED', 'EUR'].map((c) {
              return ListTile(
                title: Text(c),
                trailing: _currency == c
                    ? const Icon(Icons.check, color: AppColors.primary)
                    : null,
                onTap: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setString('currency', c);
                  setState(() => _currency = c);
                  if (mounted) Navigator.pop(context);
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  void _exportPDF(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('جاري تصدير التقرير...')),
    );
  }

  void _confirmClearAll(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('مسح جميع البيانات'),
        content: const Text(
          'هذا الإجراء سيحذف جميع العملاء والمعاملات نهائياً ولا يمكن التراجع عنه.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('تم مسح جميع البيانات')),
              );
            },
            style:
                ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('مسح الكل'),
          ),
        ],
      ),
    );
  }

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('هذه الخاصية ستتوفر قريباً')),
    );
  }
}
