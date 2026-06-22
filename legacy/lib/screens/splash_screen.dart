import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:provider/provider.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../utils/app_lock.dart';
import '../utils/auto_backup_service.dart';
import 'home_screen.dart';
import 'pin_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    await context.read<CustomerProvider>().loadCustomers();
    unawaited(AutoBackupService.runIfDue());
    final pinEnabled = await AppLock.isPinEnabled();
    await Future.delayed(const Duration(milliseconds: 2200));
    if (!mounted) return;

    if (pinEnabled) {
      // قفل كامل الشاشة فوق الـ Splash، لا يمكن تجاوزه إلا بالرمز الصحيح.
      final unlocked = await Navigator.of(context).push<bool>(
        MaterialPageRoute(
          builder: (_) => const PinScreen(mode: PinMode.unlock),
        ),
      );
      if (unlocked == true && mounted) _goHome();
    } else {
      _goHome();
    }
  }

  void _goHome() {
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => const HomeScreen(),
        transitionsBuilder: (_, animation, __, child) {
          return FadeTransition(opacity: animation, child: child);
        },
        transitionDuration: const Duration(milliseconds: 600),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.primary,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              width: 100,
              height: 100,
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.15),
                borderRadius: BorderRadius.circular(28),
              ),
              child: const Icon(
                Icons.account_balance_wallet_rounded,
                size: 56,
                color: Colors.white,
              ),
            )
                .animate()
                .scale(duration: 600.ms, curve: Curves.elasticOut)
                .fade(duration: 400.ms),
            const SizedBox(height: 28),
            Text(
              'حساباتي',
              style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 1,
                  ),
            )
                .animate()
                .slideY(begin: 0.3, duration: 500.ms, curve: Curves.easeOut)
                .fade(delay: 200.ms, duration: 400.ms),
            const SizedBox(height: 8),
            Text(
              'إدارة حسابات عملائك بكل سهولة',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.white.withOpacity(0.7),
                  ),
            )
                .animate()
                .fade(delay: 400.ms, duration: 400.ms),
            const SizedBox(height: 60),
            SizedBox(
              width: 40,
              height: 40,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                valueColor: AlwaysStoppedAnimation<Color>(
                  Colors.white.withOpacity(0.6),
                ),
              ),
            ).animate().fade(delay: 800.ms, duration: 400.ms),
          ],
        ),
      ),
    );
  }
}
