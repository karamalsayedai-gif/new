import 'dart:io';
import 'package:flutter/material.dart';
import '../models/transaction.dart';
import '../theme/app_theme.dart';
import '../utils/formatters.dart';

class TransactionTile extends StatelessWidget {
  final Transaction transaction;
  final VoidCallback? onDelete;
  final VoidCallback? onEdit;
  final ValueChanged<String>? onViewImage;

  const TransactionTile({
    super.key,
    required this.transaction,
    this.onDelete,
    this.onEdit,
    this.onViewImage,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isDebit = transaction.isDebit;
    final color = isDebit ? AppColors.debit : AppColors.credit;
    final bgColor = isDebit ? AppColors.debitLight : AppColors.creditLight;
    final icon = isDebit
        ? Icons.arrow_upward_rounded
        : Icons.arrow_downward_rounded;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark
              ? AppColors.darkBorder
              : AppColors.border.withOpacity(0.5),
        ),
      ),
      child: Row(
        children: [
          GestureDetector(
            onTap: transaction.hasImage &&
                    File(transaction.imagePath!).existsSync()
                ? () => onViewImage?.call(transaction.imagePath!)
                : null,
            child: Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: bgColor,
                borderRadius: BorderRadius.circular(12),
              ),
              clipBehavior: Clip.antiAlias,
              child: transaction.hasImage &&
                      File(transaction.imagePath!).existsSync()
                  ? Stack(
                      fit: StackFit.expand,
                      children: [
                        Image.file(File(transaction.imagePath!),
                            fit: BoxFit.cover),
                        Align(
                          alignment: Alignment.bottomLeft,
                          child: Container(
                            padding: const EdgeInsets.all(1),
                            color: Colors.black45,
                            child: const Icon(Icons.photo_camera_rounded,
                                color: Colors.white, size: 10),
                          ),
                        ),
                      ],
                    )
                  : Icon(icon, color: color, size: 20),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                        color: bgColor,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        transaction.typeLabel,
                        style: TextStyle(
                          color: color,
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ),
                if (transaction.note != null &&
                    transaction.note!.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Text(
                    transaction.note!,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: AppColors.textSecondary,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
                const SizedBox(height: 2),
                Text(
                  Formatters.relativeDate(transaction.date),
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                        color: AppColors.textHint,
                        fontSize: 11,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${isDebit ? '+' : '-'} ${Formatters.currency(transaction.amount, symbol: transaction.currency)}',
                style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
              if (transaction.currency != 'ج.م' &&
                  transaction.exchangeRate != null)
                Text(
                  '≈ ${Formatters.currency(transaction.baseAmount)}',
                  style: const TextStyle(
                    color: AppColors.textHint,
                    fontSize: 10,
                  ),
                ),
            ],
          ),
          if (onDelete != null || onEdit != null) ...[
            const SizedBox(width: 4),
            PopupMenuButton<String>(
              icon: Icon(Icons.more_vert, size: 18, color: AppColors.textHint),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12)),
              itemBuilder: (_) => [
                if (onEdit != null)
                  const PopupMenuItem(
                    value: 'edit',
                    child: Row(
                      children: [
                        Icon(Icons.edit_outlined, size: 18),
                        SizedBox(width: 8),
                        Text('تعديل'),
                      ],
                    ),
                  ),
                if (onDelete != null)
                  const PopupMenuItem(
                    value: 'delete',
                    child: Row(
                      children: [
                        Icon(Icons.delete_outline,
                            size: 18, color: AppColors.debit),
                        SizedBox(width: 8),
                        Text('حذف', style: TextStyle(color: AppColors.debit)),
                      ],
                    ),
                  ),
              ],
              onSelected: (value) {
                if (value == 'delete') onDelete?.call();
                if (value == 'edit') onEdit?.call();
              },
            ),
          ],
        ],
      ),
    );
  }
}
