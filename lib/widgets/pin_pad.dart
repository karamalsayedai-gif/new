import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';

class PinPad extends StatelessWidget {
  final ValueChanged<String> onDigit;
  final VoidCallback onBackspace;
  final VoidCallback? onBiometric;
  final bool showBiometric;

  const PinPad({
    super.key,
    required this.onDigit,
    required this.onBackspace,
    this.onBiometric,
    this.showBiometric = false,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final row in const [
          ['1', '2', '3'],
          ['4', '5', '6'],
          ['7', '8', '9'],
        ])
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (final d in row) _DigitKey(digit: d, onTap: () => onDigit(d)),
              ],
            ),
          ),
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 6),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Biometric or empty
              showBiometric
                  ? _IconKey(
                      icon: Icons.fingerprint_rounded,
                      onTap: onBiometric ?? () {},
                    )
                  : const SizedBox(width: 76, height: 76),
              _DigitKey(digit: '0', onTap: () => onDigit('0')),
              _IconKey(
                icon: Icons.backspace_outlined,
                onTap: onBackspace,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _DigitKey extends StatelessWidget {
  final String digit;
  final VoidCallback onTap;

  const _DigitKey({required this.digit, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Material(
        color: isDark
            ? Colors.white.withOpacity(0.06)
            : Colors.white.withOpacity(0.12),
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: () {
            HapticFeedback.lightImpact();
            onTap();
          },
          child: SizedBox(
            width: 76,
            height: 76,
            child: Center(
              child: Text(
                digit,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 28,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _IconKey extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;

  const _IconKey({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(8),
      child: Material(
        color: Colors.transparent,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: () {
            HapticFeedback.lightImpact();
            onTap();
          },
          child: SizedBox(
            width: 76,
            height: 76,
            child: Icon(icon, color: Colors.white.withOpacity(0.85), size: 28),
          ),
        ),
      ),
    );
  }
}

class PinDots extends StatelessWidget {
  final int length;
  final int filled;
  final bool error;

  const PinDots({
    super.key,
    this.length = 4,
    required this.filled,
    this.error = false,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: List.generate(length, (i) {
        final isFilled = i < filled;
        return AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          margin: const EdgeInsets.symmetric(horizontal: 10),
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: error
                ? AppColors.error
                : isFilled
                    ? Colors.white
                    : Colors.transparent,
            border: Border.all(
              color: error ? AppColors.error : Colors.white,
              width: 2,
            ),
          ),
        );
      }),
    );
  }
}
