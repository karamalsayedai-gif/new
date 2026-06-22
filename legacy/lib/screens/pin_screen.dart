import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../utils/app_lock.dart';
import '../widgets/pin_pad.dart';

enum PinMode { unlock, setup, change }

class PinScreen extends StatefulWidget {
  final PinMode mode;
  final VoidCallback? onSuccess;

  const PinScreen({
    super.key,
    this.mode = PinMode.unlock,
    this.onSuccess,
  });

  @override
  State<PinScreen> createState() => _PinScreenState();
}

class _PinScreenState extends State<PinScreen> {
  String _entered = '';
  String? _firstPin; // أثناء إنشاء/تغيير الرمز
  bool _error = false;
  bool _confirming = false;
  bool _canBiometric = false;

  @override
  void initState() {
    super.initState();
    _setup();
  }

  Future<void> _setup() async {
    if (widget.mode == PinMode.unlock) {
      final bio = await AppLock.isBiometricEnabled();
      final can = await AppLock.canUseBiometrics();
      if (mounted) setState(() => _canBiometric = bio && can);
      if (_canBiometric) _tryBiometric();
    }
  }

  String get _title {
    switch (widget.mode) {
      case PinMode.unlock:
        return 'أدخل رمز الدخول';
      case PinMode.setup:
      case PinMode.change:
        return _confirming ? 'أعد إدخال الرمز للتأكيد' : 'أنشئ رمز دخول';
    }
  }

  Future<void> _onDigit(String d) async {
    if (_entered.length >= 4) return;
    setState(() {
      _entered += d;
      _error = false;
    });
    if (_entered.length == 4) {
      await Future.delayed(const Duration(milliseconds: 120));
      _onComplete();
    }
  }

  void _onBackspace() {
    if (_entered.isEmpty) return;
    setState(() => _entered = _entered.substring(0, _entered.length - 1));
  }

  Future<void> _onComplete() async {
    if (widget.mode == PinMode.unlock) {
      final ok = await AppLock.verifyPin(_entered);
      if (ok) {
        _success();
      } else {
        _showError();
      }
      return;
    }

    // setup / change
    if (!_confirming) {
      setState(() {
        _firstPin = _entered;
        _confirming = true;
        _entered = '';
      });
    } else {
      if (_entered == _firstPin) {
        await AppLock.setPin(_entered);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('تم تعيين رمز الدخول')),
          );
        }
        _success();
      } else {
        setState(() {
          _confirming = false;
          _firstPin = null;
        });
        _showError(message: 'الرمزان غير متطابقين، حاول مجدداً');
      }
    }
  }

  void _showError({String? message}) {
    setState(() {
      _error = true;
      _entered = '';
    });
    if (message != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(message)),
      );
    }
  }

  Future<void> _tryBiometric() async {
    final ok = await AppLock.authenticateBiometric();
    if (ok) _success();
  }

  void _success() {
    if (widget.onSuccess != null) {
      widget.onSuccess!();
    } else {
      Navigator.of(context).pop(true);
    }
  }

  @override
  Widget build(BuildContext context) {
    // في وضع فتح القفل نمنع زر الرجوع حتى لا يتجاوز المستخدم الحماية.
    return PopScope(
      canPop: widget.mode != PinMode.unlock,
      child: _buildScaffold(context),
    );
  }

  Widget _buildScaffold(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [AppColors.primaryDark, AppColors.primary, AppColors.primaryLight],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              const Spacer(flex: 2),
              Container(
                width: 84,
                height: 84,
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.12),
                  borderRadius: BorderRadius.circular(24),
                ),
                child: const Icon(Icons.lock_rounded,
                    color: Colors.white, size: 40),
              ).animate().scale(duration: 400.ms, curve: Curves.easeOut),
              const SizedBox(height: 20),
              const Text(
                'حساباتي',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _title,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.75),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 32),
              PinDots(filled: _entered.length, error: _error)
                  .animate(target: _error ? 1 : 0)
                  .shakeX(hz: 4, amount: 6),
              const Spacer(flex: 1),
              PinPad(
                onDigit: _onDigit,
                onBackspace: _onBackspace,
                showBiometric: _canBiometric,
                onBiometric: _tryBiometric,
              ),
              const Spacer(flex: 1),
              if (widget.mode != PinMode.unlock)
                TextButton(
                  onPressed: () => Navigator.of(context).pop(false),
                  child: Text(
                    'إلغاء',
                    style: TextStyle(color: Colors.white.withOpacity(0.7)),
                  ),
                ),
              const SizedBox(height: 12),
            ],
          ),
        ),
      ),
    );
  }
}
