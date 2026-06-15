import 'package:flutter/material.dart';
import '../models/customer.dart';
import '../theme/app_theme.dart';
import '../utils/formatters.dart';

class CustomerCard extends StatelessWidget {
  final Customer customer;
  final double balance;
  final VoidCallback onTap;
  final VoidCallback? onLongPress;

  const CustomerCard({
    super.key,
    required this.customer,
    required this.balance,
    required this.onTap,
    this.onLongPress,
  });

  Color _avatarColor(BuildContext context) {
    if (customer.avatarColor != null) {
      try {
        return Color(int.parse(customer.avatarColor!, radix: 16));
      } catch (_) {}
    }
    final colors = [
      AppColors.primary,
      AppColors.credit,
      const Color(0xFF7B3FA0),
      const Color(0xFFD4682E),
      const Color(0xFF2E7D9A),
    ];
    return colors[customer.name.codeUnitAt(0) % colors.length];
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isPositive = balance > 0;
    final isNegative = balance < 0;
    final color = _avatarColor(context);

    return InkWell(
      onTap: onTap,
      onLongPress: onLongPress,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 5),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: isDark ? AppColors.darkCard : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isDark
                ? AppColors.darkBorder
                : AppColors.border.withOpacity(0.6),
          ),
          boxShadow: isDark
              ? []
              : [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.04),
                    blurRadius: 8,
                    offset: const Offset(0, 2),
                  ),
                ],
        ),
        child: Row(
          children: [
            // Avatar
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                color: color.withOpacity(0.12),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Center(
                child: Text(
                  customer.initials,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w700,
                    fontSize: 18,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 14),
            // Info
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    customer.name,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (customer.phone != null &&
                      customer.phone!.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Row(
                      children: [
                        Icon(
                          Icons.phone_outlined,
                          size: 12,
                          color: AppColors.textHint,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          customer.phone!,
                          style:
                              Theme.of(context).textTheme.bodySmall?.copyWith(
                                    color: AppColors.textHint,
                                  ),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: 12),
            // Balance
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                if (balance.abs() < 0.01)
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.grey.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      'مسوّى',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  )
                else ...[
                  Text(
                    Formatters.currency(balance),
                    style: TextStyle(
                      color: isPositive ? AppColors.debit : AppColors.credit,
                      fontWeight: FontWeight.w700,
                      fontSize: 15,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: isPositive
                          ? AppColors.debitLight
                          : AppColors.creditLight,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      isPositive ? 'له عليّ' : 'عليه لي',
                      style: TextStyle(
                        color: isPositive ? AppColors.debit : AppColors.credit,
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(width: 4),
            Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textHint,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}
