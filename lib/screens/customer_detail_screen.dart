import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:share_plus/share_plus.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../providers/transaction_provider.dart';
import '../models/customer.dart';
import '../models/transaction.dart';
import '../widgets/transaction_tile.dart';
import '../utils/formatters.dart';
import 'add_transaction_screen.dart';
import 'add_customer_screen.dart';

class CustomerDetailScreen extends StatefulWidget {
  final int customerId;

  const CustomerDetailScreen({super.key, required this.customerId});

  @override
  State<CustomerDetailScreen> createState() => _CustomerDetailScreenState();
}

class _CustomerDetailScreenState extends State<CustomerDetailScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<TransactionProvider>().loadTransactions(widget.customerId);
    });
  }

  Customer? _getCustomer(CustomerProvider provider) {
    try {
      return provider.customers.firstWhere((c) => c.id == widget.customerId);
    } catch (_) {
      return null;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Consumer2<CustomerProvider, TransactionProvider>(
      builder: (_, customerProvider, txProvider, __) {
        final customer = _getCustomer(customerProvider);
        if (customer == null) {
          return const Scaffold(
            body: Center(child: Text('العميل غير موجود')),
          );
        }

        final balance = customerProvider.getBalance(widget.customerId);
        final isPositive = balance > 0;

        return Scaffold(
          backgroundColor: Theme.of(context).scaffoldBackgroundColor,
          body: CustomScrollView(
            slivers: [
              _buildAppBar(context, customer, balance, isPositive),
              SliverToBoxAdapter(
                child: _buildBalanceBanner(context, balance),
              ),
              SliverToBoxAdapter(
                child: _buildActions(context, customer),
              ),
              SliverToBoxAdapter(
                child: Padding(
                  padding:
                      const EdgeInsets.fromLTRB(16, 20, 16, 8),
                  child: Row(
                    children: [
                      Text(
                        'سجل المعاملات',
                        style:
                            Theme.of(context).textTheme.titleMedium?.copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                      ),
                      const Spacer(),
                      Text(
                        '${txProvider.transactions.length} معاملة',
                        style:
                            Theme.of(context).textTheme.bodySmall?.copyWith(
                                  color: AppColors.textHint,
                                ),
                      ),
                    ],
                  ),
                ),
              ),
              if (txProvider.isLoading)
                const SliverToBoxAdapter(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Center(child: CircularProgressIndicator()),
                  ),
                )
              else if (txProvider.transactions.isEmpty)
                SliverToBoxAdapter(child: _buildEmptyTransactions(context))
              else
                SliverList(
                  delegate: SliverChildBuilderDelegate(
                    (_, i) {
                      final tx = txProvider.transactions[i];
                      return TransactionTile(
                        transaction: tx,
                        onDelete: () => _deleteTransaction(context, tx),
                        onEdit: () => _editTransaction(context, tx),
                      )
                          .animate(delay: (i * 40).ms)
                          .slideY(begin: 0.05, duration: 250.ms);
                    },
                    childCount: txProvider.transactions.length,
                  ),
                ),
              const SliverToBoxAdapter(child: SizedBox(height: 100)),
            ],
          ),
          floatingActionButton: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              FloatingActionButton(
                heroTag: 'debit',
                onPressed: () => _addTransaction(context, customer,
                    type: TransactionType.debit),
                backgroundColor: AppColors.debit,
                child: const Icon(Icons.add_rounded),
                tooltip: 'أعطيت',
              ),
              const SizedBox(height: 12),
              FloatingActionButton.extended(
                heroTag: 'credit',
                onPressed: () => _addTransaction(context, customer,
                    type: TransactionType.credit),
                backgroundColor: AppColors.credit,
                icon: const Icon(Icons.remove_rounded),
                label: const Text('أخذت'),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildAppBar(
    BuildContext context,
    Customer customer,
    double balance,
    bool isPositive,
  ) {
    return SliverAppBar(
      expandedHeight: 140,
      pinned: true,
      backgroundColor: AppColors.primary,
      actions: [
        IconButton(
          onPressed: () => _editCustomer(context, customer),
          icon: const Icon(Icons.edit_rounded),
        ),
        IconButton(
          onPressed: () => _shareStatement(context, customer),
          icon: const Icon(Icons.share_rounded),
        ),
      ],
      flexibleSpace: FlexibleSpaceBar(
        background: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [AppColors.primaryDark, AppColors.primaryLight],
            ),
          ),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(72, 8, 16, 16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.end,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    customer.name,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  if (customer.phone != null && customer.phone!.isNotEmpty)
                    Text(
                      customer.phone!,
                      style: TextStyle(
                        color: Colors.white.withOpacity(0.7),
                        fontSize: 14,
                      ),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBalanceBanner(BuildContext context, double balance) {
    final isPositive = balance > 0;
    final isZero = balance.abs() < 0.01;

    Color color;
    Color bgColor;
    String label;
    IconData icon;

    if (isZero) {
      color = AppColors.textSecondary;
      bgColor = AppColors.background;
      label = 'الحساب مسوّى - لا يوجد دين';
      icon = Icons.check_circle_outline;
    } else if (isPositive) {
      color = AppColors.debit;
      bgColor = AppColors.debitLight;
      label = 'له عليّ - يستحق مني';
      icon = Icons.arrow_upward_rounded;
    } else {
      color = AppColors.credit;
      bgColor = AppColors.creditLight;
      label = 'عليه لي - مدين لي';
      icon = Icons.arrow_downward_rounded;
    }

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 32),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: TextStyle(
                      color: color, fontSize: 13, fontWeight: FontWeight.w500)),
              Text(
                isZero ? 'صفر' : Formatters.currency(balance.abs()),
                style: TextStyle(
                    color: color, fontSize: 26, fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ],
      ),
    ).animate().scale(duration: 300.ms, curve: Curves.easeOut);
  }

  Widget _buildActions(BuildContext context, Customer customer) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: _ActionButton(
              icon: Icons.add_circle_rounded,
              label: 'أعطيت',
              color: AppColors.debit,
              bgColor: AppColors.debitLight,
              onTap: () => _addTransaction(context, customer,
                  type: TransactionType.debit),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _ActionButton(
              icon: Icons.remove_circle_rounded,
              label: 'أخذت',
              color: AppColors.credit,
              bgColor: AppColors.creditLight,
              onTap: () => _addTransaction(context, customer,
                  type: TransactionType.credit),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _ActionButton(
              icon: Icons.share_rounded,
              label: 'مشاركة',
              color: AppColors.accent,
              bgColor: AppColors.accentLight.withOpacity(0.2),
              onTap: () => _shareStatement(context, customer),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyTransactions(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        children: [
          Icon(Icons.receipt_long_outlined,
              size: 64, color: AppColors.textHint),
          const SizedBox(height: 12),
          Text(
            'لا توجد معاملات بعد',
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(color: AppColors.textSecondary),
          ),
          const SizedBox(height: 4),
          Text(
            'اضغط على "أعطيت" أو "أخذت" لتسجيل أول معاملة',
            textAlign: TextAlign.center,
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: AppColors.textHint),
          ),
        ],
      ),
    );
  }

  Future<void> _addTransaction(
    BuildContext context,
    Customer customer, {
    required TransactionType type,
  }) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AddTransactionScreen(
          customer: customer,
          initialType: type,
        ),
      ),
    );
    if (mounted) {
      await context
          .read<TransactionProvider>()
          .loadTransactions(widget.customerId);
      await context
          .read<CustomerProvider>()
          .refreshBalance(widget.customerId);
    }
  }

  Future<void> _editTransaction(
      BuildContext context, Transaction transaction) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AddTransactionScreen(
          customer: _getCustomer(context.read<CustomerProvider>())!,
          initialType: transaction.type,
          transaction: transaction,
        ),
      ),
    );
    if (mounted) {
      await context
          .read<TransactionProvider>()
          .loadTransactions(widget.customerId);
      await context
          .read<CustomerProvider>()
          .refreshBalance(widget.customerId);
    }
  }

  void _deleteTransaction(BuildContext context, Transaction transaction) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('حذف المعاملة'),
        content: const Text('هل أنت متأكد من حذف هذه المعاملة؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () async {
              Navigator.pop(context);
              await context.read<TransactionProvider>().deleteTransaction(
                    transaction.id!,
                    widget.customerId,
                  );
              await context
                  .read<CustomerProvider>()
                  .refreshBalance(widget.customerId);
            },
            style:
                ElevatedButton.styleFrom(backgroundColor: AppColors.debit),
            child: const Text('حذف'),
          ),
        ],
      ),
    );
  }

  void _editCustomer(BuildContext context, Customer customer) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => AddCustomerScreen(customer: customer),
      ),
    ).then((_) => context.read<CustomerProvider>().loadCustomers());
  }

  void _shareStatement(BuildContext context, Customer customer) {
    final txProvider = context.read<TransactionProvider>();
    final balance =
        context.read<CustomerProvider>().getBalance(widget.customerId);

    final buffer = StringBuffer();
    buffer.writeln('📊 كشف حساب - ${customer.name}');
    buffer.writeln('━━━━━━━━━━━━━━━━━━━━');
    buffer.writeln('📅 التاريخ: ${Formatters.date(DateTime.now())}');
    buffer.writeln('');

    for (final tx in txProvider.transactions) {
      final emoji = tx.isDebit ? '⬆️' : '⬇️';
      buffer.writeln(
          '$emoji ${tx.typeLabel}: ${Formatters.currency(tx.amount)}  -  ${Formatters.date(tx.date)}');
      if (tx.note != null && tx.note!.isNotEmpty) {
        buffer.writeln('   📝 ${tx.note}');
      }
    }

    buffer.writeln('━━━━━━━━━━━━━━━━━━━━');
    if (balance.abs() < 0.01) {
      buffer.writeln('✅ الحساب مسوّى');
    } else if (balance > 0) {
      buffer.writeln('💸 له عليّ: ${Formatters.currency(balance)}');
    } else {
      buffer.writeln('💰 عليه لي: ${Formatters.currency(balance.abs())}');
    }
    buffer.writeln('');
    buffer.writeln('تم الإرسال من تطبيق حساباتي');

    Share.share(buffer.toString());
  }
}

class _ActionButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final Color bgColor;
  final VoidCallback onTap;

  const _ActionButton({
    required this.icon,
    required this.label,
    required this.color,
    required this.bgColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withOpacity(0.2)),
        ),
        child: Column(
          children: [
            Icon(icon, color: color, size: 24),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                color: color,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
