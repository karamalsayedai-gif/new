import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../utils/formatters.dart';
import '../utils/app_lock.dart';
import '../utils/backup_helper.dart';
import '../utils/notification_service.dart';
import '../utils/pdf_generator.dart';
import 'pin_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  String _currency = 'ج.م';
  bool _notifications = true;
  bool _pinEnabled = false;
  bool _biometricEnabled = false;
  bool _canBiometric = false;
  TimeOfDay _reminderTime = const TimeOfDay(hour: 9, minute: 0);
  int _reminderDays = 7;

  @override
  void initState() {
    super.initState();
    _loadPrefs();
  }

  Future<void> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final pinOn = await AppLock.isPinEnabled();
    final bioOn = await AppLock.isBiometricEnabled();
    final canBio = await AppLock.canUseBiometrics();
    setState(() {
      _currency = prefs.getString('currency') ?? 'ج.م';
      _notifications = prefs.getBool('notifications') ?? true;
      _pinEnabled = pinOn;
      _biometricEnabled = bioOn;
      _canBiometric = canBio;
      _reminderTime = TimeOfDay(
        hour: prefs.getInt('reminder_hour') ?? 9,
        minute: prefs.getInt('reminder_minute') ?? 0,
      );
      _reminderDays = prefs.getInt('reminder_days') ?? 7;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('الإعدادات')),
      body: ListView(
        children: [
          _buildAppInfo(context),
          const SizedBox(height: 8),
          _buildSection(
            context,
            title: 'عام',
            children: [
              _buildTile(
                icon: Icons.attach_money_rounded,
                iconColor: AppColors.accent,
                title: 'العملة الأساسية',
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
            title: 'الإشعارات والتذكيرات',
            children: [
              _buildSwitchTile(
                icon: Icons.notifications_rounded,
                iconColor: AppColors.credit,
                title: 'إشعارات التذكير',
                subtitle: 'تذكير بالديون المستحقة',
                value: _notifications,
                onChanged: _toggleNotifications,
              ),
              if (_notifications) ...[
                _buildTile(
                  icon: Icons.schedule_rounded,
                  iconColor: AppColors.primary,
                  title: 'وقت الإشعار',
                  subtitle: _reminderTime.format(context),
                  onTap: _pickReminderTime,
                ),
                _buildTile(
                  icon: Icons.event_repeat_rounded,
                  iconColor: AppColors.accent,
                  title: 'تذكير بعد',
                  subtitle: '$_reminderDays أيام من آخر معاملة',
                  onTap: _pickReminderDays,
                ),
              ],
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
                title: 'قفل التطبيق برمز PIN',
                subtitle: 'حماية بياناتك برمز من 4 أرقام',
                value: _pinEnabled,
                onChanged: _togglePin,
              ),
              if (_pinEnabled) ...[
                _buildTile(
                  icon: Icons.password_rounded,
                  iconColor: AppColors.primary,
                  title: 'تغيير رمز الدخول',
                  subtitle: 'تعيين رمز PIN جديد',
                  onTap: _changePin,
                ),
                if (_canBiometric)
                  _buildSwitchTile(
                    icon: Icons.fingerprint_rounded,
                    iconColor: AppColors.credit,
                    title: 'البصمة / Face ID',
                    subtitle: 'تسجيل الدخول بالبصمة',
                    value: _biometricEnabled,
                    onChanged: _toggleBiometric,
                  ),
              ],
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
                subtitle: 'حفظ نسخة من بياناتك (Drive/ملفات)',
                onTap: _exportBackup,
              ),
              _buildTile(
                icon: Icons.restore_rounded,
                iconColor: AppColors.accent,
                title: 'استعادة بيانات',
                subtitle: 'استعادة من نسخة احتياطية',
                onTap: _restoreBackup,
              ),
              _buildTile(
                icon: Icons.picture_as_pdf_rounded,
                iconColor: AppColors.debit,
                title: 'تصدير تقرير PDF',
                subtitle: 'تقرير شامل بكل العملاء',
                onTap: _exportPdf,
              ),
              _buildTile(
                icon: Icons.delete_forever_rounded,
                iconColor: Colors.red,
                title: 'مسح جميع البيانات',
                subtitle: 'حذف كل العملاء والمعاملات',
                onTap: _confirmClearAll,
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
                subtitle: '1.1.0',
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

  // ============ Notifications ============

  Future<void> _toggleNotifications(bool v) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications', v);
    setState(() => _notifications = v);
    if (v) {
      await NotificationService().requestPermissions();
      await _rescheduleReminder();
    } else {
      await NotificationService().cancelAll();
    }
  }

  Future<void> _pickReminderTime() async {
    final picked = await showTimePicker(
      context: context,
      initialTime: _reminderTime,
    );
    if (picked != null) {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt('reminder_hour', picked.hour);
      await prefs.setInt('reminder_minute', picked.minute);
      setState(() => _reminderTime = picked);
      await _rescheduleReminder();
    }
  }

  Future<void> _pickReminderDays() async {
    final options = [3, 7, 14, 30, 60];
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
            Text('تذكير بعد كم يوم من آخر معاملة؟',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            ...options.map((d) => ListTile(
                  title: Text('$d أيام'),
                  trailing: _reminderDays == d
                      ? const Icon(Icons.check, color: AppColors.primary)
                      : null,
                  onTap: () async {
                    final prefs = await SharedPreferences.getInstance();
                    await prefs.setInt('reminder_days', d);
                    setState(() => _reminderDays = d);
                    if (mounted) Navigator.pop(context);
                    await _rescheduleReminder();
                  },
                )),
          ],
        ),
      ),
    );
  }

  Future<void> _rescheduleReminder() async {
    if (!_notifications) return;
    await NotificationService().scheduleDailyReminder(
      hour: _reminderTime.hour,
      minute: _reminderTime.minute,
      daysThreshold: _reminderDays,
    );
  }

  // ============ Security ============

  Future<void> _togglePin(bool v) async {
    if (v) {
      final ok = await Navigator.push<bool>(
        context,
        MaterialPageRoute(
          builder: (_) => const PinScreen(mode: PinMode.setup),
        ),
      );
      if (ok == true) setState(() => _pinEnabled = true);
    } else {
      await AppLock.disablePin();
      setState(() {
        _pinEnabled = false;
        _biometricEnabled = false;
      });
    }
  }

  Future<void> _changePin() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const PinScreen(mode: PinMode.change)),
    );
  }

  Future<void> _toggleBiometric(bool v) async {
    if (v) {
      final ok = await AppLock.authenticateBiometric();
      if (!ok) return;
    }
    await AppLock.setBiometricEnabled(v);
    setState(() => _biometricEnabled = v);
  }

  // ============ Data ============

  Future<void> _exportBackup() async {
    final messenger = ScaffoldMessenger.of(context);
    messenger.showSnackBar(
      const SnackBar(content: Text('جاري إنشاء النسخة الاحتياطية...')),
    );
    final result = await BackupHelper.exportBackup();
    messenger.showSnackBar(SnackBar(content: Text(result.message)));
  }

  Future<void> _restoreBackup() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('استعادة البيانات'),
        content: const Text(
            'سيتم استبدال جميع البيانات الحالية بمحتوى النسخة الاحتياطية. متابعة؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('استعادة'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final messenger = ScaffoldMessenger.of(context);
    final result = await BackupHelper.restoreBackup();
    messenger.showSnackBar(SnackBar(content: Text(result.message)));
    if (result.success && mounted) {
      await context.read<CustomerProvider>().loadCustomers();
    }
  }

  Future<void> _exportPdf() async {
    final messenger = ScaffoldMessenger.of(context);
    final provider = context.read<CustomerProvider>();
    if (provider.totalCustomers == 0) {
      messenger.showSnackBar(
        const SnackBar(content: Text('لا يوجد عملاء للتصدير')),
      );
      return;
    }
    messenger.showSnackBar(
      const SnackBar(content: Text('جاري إنشاء التقرير...')),
    );
    try {
      await provider.loadCustomers();
      final totals = provider.totals;
      final bytes = await PdfGenerator.summaryReport(
        customers: provider.customers,
        balances: provider.balances,
        totalDebit: totals['totalDebit'] ?? 0,
        totalCredit: totals['totalCredit'] ?? 0,
      );
      await PdfGenerator.printDocument(bytes, 'تقرير_حساباتي');
    } catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text('تعذّر إنشاء التقرير: $e')),
      );
    }
  }

  Future<void> _confirmClearAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('مسح جميع البيانات'),
        content: const Text(
          'هذا الإجراء سيحذف جميع العملاء والمعاملات نهائياً ولا يمكن التراجع عنه.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
            child: const Text('مسح الكل'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    final messenger = ScaffoldMessenger.of(context);
    await context.read<CustomerProvider>().clearAll();
    messenger.showSnackBar(
      const SnackBar(content: Text('تم مسح جميع البيانات')),
    );
  }

  // ============ UI Builders ============

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
              Expanded(
                child: Column(
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
      subtitle: Text(subtitle, style: const TextStyle(fontSize: 12)),
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
            Text('اختر العملة الأساسية',
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

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('هذه الخاصية ستتوفر قريباً')),
    );
  }
}
