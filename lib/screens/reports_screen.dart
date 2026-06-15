import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../providers/transaction_provider.dart';
import '../database/database_helper.dart';
import '../utils/formatters.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  List<Map<String, dynamic>> _monthlyStats = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadStats();
  }

  Future<void> _loadStats() async {
    final stats = await DatabaseHelper().getMonthlyStats();
    if (mounted) {
      setState(() {
        _monthlyStats = stats.reversed.toList();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('التقارير والإحصائيات'),
        actions: [
          IconButton(
            onPressed: _loadStats,
            icon: const Icon(Icons.refresh_rounded),
          ),
        ],
      ),
      body: Consumer<CustomerProvider>(
        builder: (_, provider, __) {
          final totals = provider.totals;
          final net = totals['netBalance'] ?? 0;
          final totalDebit = totals['totalDebit'] ?? 0;
          final totalCredit = totals['totalCredit'] ?? 0;

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Summary Cards
              _buildSummarySection(
                  context, totalDebit, totalCredit, net, provider),
              const SizedBox(height: 24),

              // Pie Chart
              if (totalDebit > 0 || totalCredit > 0) ...[
                _buildSectionTitle(context, 'توزيع الحسابات',
                    Icons.pie_chart_rounded),
                const SizedBox(height: 12),
                _buildPieChart(context, totalDebit, totalCredit),
                const SizedBox(height: 24),
              ],

              // Monthly Bar Chart
              if (_monthlyStats.isNotEmpty) ...[
                _buildSectionTitle(context, 'الحركة الشهرية',
                    Icons.bar_chart_rounded),
                const SizedBox(height: 12),
                _buildBarChart(context),
                const SizedBox(height: 24),
              ],

              // Top Customers
              _buildSectionTitle(
                  context, 'أكبر العملاء ديناً', Icons.people_rounded),
              const SizedBox(height: 12),
              _buildTopCustomers(context, provider),
              const SizedBox(height: 24),
            ],
          );
        },
      ),
    );
  }

  Widget _buildSummarySection(
    BuildContext context,
    double totalDebit,
    double totalCredit,
    double net,
    CustomerProvider provider,
  ) {
    return Column(
      children: [
        // Net Balance Hero
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [AppColors.primaryDark, AppColors.primaryLight],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            children: [
              const Icon(Icons.account_balance_rounded,
                  color: Colors.white54, size: 32),
              const SizedBox(height: 8),
              Text(
                'الرصيد الصافي',
                style: TextStyle(color: Colors.white70, fontSize: 13),
              ),
              Text(
                Formatters.currency(net.abs()),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Text(
                net > 0
                    ? 'لك عند العملاء'
                    : net < 0
                        ? 'عليك للعملاء'
                        : 'جميع الحسابات مسواة',
                style: TextStyle(
                  color: net > 0
                      ? Colors.greenAccent.shade100
                      : net < 0
                          ? Colors.redAccent.shade100
                          : Colors.white70,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ).animate().scale(duration: 400.ms, curve: Curves.easeOut),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                title: 'إجمالي أعطيت',
                value: Formatters.currency(totalDebit),
                color: AppColors.debit,
                bgColor: AppColors.debitLight,
                icon: Icons.arrow_upward_rounded,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                title: 'إجمالي أخذت',
                value: Formatters.currency(totalCredit),
                color: AppColors.credit,
                bgColor: AppColors.creditLight,
                icon: Icons.arrow_downward_rounded,
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _StatCard(
                title: 'إجمالي العملاء',
                value: '${provider.totalCustomers}',
                color: AppColors.primary,
                bgColor: AppColors.primaryLight.withOpacity(0.1),
                icon: Icons.people_rounded,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: _StatCard(
                title: 'عملاء مدينون',
                value: '${provider.customersWithDebt.length}',
                color: AppColors.accent,
                bgColor: AppColors.accentLight.withOpacity(0.2),
                icon: Icons.warning_amber_rounded,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildPieChart(
      BuildContext context, double totalDebit, double totalCredit) {
    final total = totalDebit + totalCredit;
    if (total == 0) return const SizedBox.shrink();

    return Container(
      height: 220,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.darkCard
            : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Theme.of(context).brightness == Brightness.dark
              ? AppColors.darkBorder
              : AppColors.border,
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: PieChart(
              PieChartData(
                sections: [
                  PieChartSectionData(
                    value: totalDebit,
                    color: AppColors.debit,
                    title:
                        '${(totalDebit / total * 100).toStringAsFixed(0)}%',
                    titleStyle: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                    radius: 70,
                  ),
                  PieChartSectionData(
                    value: totalCredit,
                    color: AppColors.credit,
                    title:
                        '${(totalCredit / total * 100).toStringAsFixed(0)}%',
                    titleStyle: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                    radius: 70,
                  ),
                ],
                sectionsSpace: 3,
                centerSpaceRadius: 0,
              ),
            ),
          ),
          const SizedBox(width: 16),
          Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _LegendItem(color: AppColors.debit, label: 'أعطيت'),
              const SizedBox(height: 12),
              _LegendItem(color: AppColors.credit, label: 'أخذت'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBarChart(BuildContext context) {
    if (_monthlyStats.isEmpty) return const SizedBox.shrink();

    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      height: 220,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? AppColors.darkCard : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDark ? AppColors.darkBorder : AppColors.border,
        ),
      ),
      child: BarChart(
        BarChartData(
          alignment: BarChartAlignment.spaceAround,
          maxY: _monthlyStats
              .map((s) => [
                    (s['debit'] as num?)?.toDouble() ?? 0,
                    (s['credit'] as num?)?.toDouble() ?? 0,
                  ])
              .expand((e) => e)
              .fold<double>(0, (a, b) => a > b ? a : b) *
          1.2,
          barGroups: _monthlyStats.asMap().entries.map((entry) {
            final i = entry.key;
            final s = entry.value;
            final debit = (s['debit'] as num?)?.toDouble() ?? 0;
            final credit = (s['credit'] as num?)?.toDouble() ?? 0;
            return BarChartGroupData(
              x: i,
              barRods: [
                BarChartRodData(
                    toY: debit,
                    color: AppColors.debit,
                    width: 10,
                    borderRadius: BorderRadius.circular(4)),
                BarChartRodData(
                    toY: credit,
                    color: AppColors.credit,
                    width: 10,
                    borderRadius: BorderRadius.circular(4)),
              ],
              barsSpace: 4,
            );
          }).toList(),
          titlesData: FlTitlesData(
            bottomTitles: AxisTitles(
              sideTitles: SideTitles(
                showTitles: true,
                getTitlesWidget: (value, meta) {
                  final i = value.toInt();
                  if (i >= 0 && i < _monthlyStats.length) {
                    final month = _monthlyStats[i]['month'] as String;
                    return Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: Text(
                        month.substring(5), // Show MM
                        style: TextStyle(
                          fontSize: 10,
                          color: AppColors.textHint,
                        ),
                      ),
                    );
                  }
                  return const SizedBox.shrink();
                },
              ),
            ),
            leftTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
            topTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
            rightTitles: const AxisTitles(
                sideTitles: SideTitles(showTitles: false)),
          ),
          gridData: FlGridData(
            show: true,
            drawVerticalLine: false,
            getDrawingHorizontalLine: (_) =>
                FlLine(color: AppColors.border, strokeWidth: 1),
          ),
          borderData: FlBorderData(show: false),
        ),
      ),
    );
  }

  Widget _buildTopCustomers(
      BuildContext context, CustomerProvider provider) {
    final sorted = provider.customers
        .where((c) => (provider.getBalance(c.id!) ).abs() > 0)
        .toList()
      ..sort((a, b) => provider
          .getBalance(b.id!)
          .abs()
          .compareTo(provider.getBalance(a.id!).abs()));

    if (sorted.isEmpty) {
      return Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: Theme.of(context).brightness == Brightness.dark
              ? AppColors.darkCard
              : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppColors.border),
        ),
        child: const Center(
          child: Text('لا توجد بيانات بعد'),
        ),
      );
    }

    return Container(
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.darkCard
            : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: Theme.of(context).brightness == Brightness.dark
              ? AppColors.darkBorder
              : AppColors.border,
        ),
      ),
      child: ListView.separated(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: sorted.take(5).length,
        separatorBuilder: (_, __) =>
            const Divider(height: 1, indent: 16),
        itemBuilder: (_, i) {
          final customer = sorted[i];
          final balance = provider.getBalance(customer.id!);
          final isPositive = balance > 0;
          return ListTile(
            leading: CircleAvatar(
              backgroundColor:
                  AppColors.primary.withOpacity(0.1),
              child: Text(
                '${i + 1}',
                style: const TextStyle(
                  color: AppColors.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            title: Text(customer.name),
            subtitle: Text(
              isPositive ? 'له عليّ' : 'عليه لي',
              style: TextStyle(
                color: isPositive ? AppColors.debit : AppColors.credit,
                fontSize: 12,
              ),
            ),
            trailing: Text(
              Formatters.currency(balance.abs()),
              style: TextStyle(
                color: isPositive ? AppColors.debit : AppColors.credit,
                fontWeight: FontWeight.w700,
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildSectionTitle(
      BuildContext context, String title, IconData icon) {
    return Row(
      children: [
        Icon(icon, color: AppColors.primary, size: 20),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.w600,
              ),
        ),
      ],
    );
  }
}

class _StatCard extends StatelessWidget {
  final String title;
  final String value;
  final Color color;
  final Color bgColor;
  final IconData icon;

  const _StatCard({
    required this.title,
    required this.value,
    required this.color,
    required this.bgColor,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).brightness == Brightness.dark
            ? AppColors.darkCard
            : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: color.withOpacity(0.2)),
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, color: color, size: 18),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: AppColors.textHint,
                    fontSize: 10,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  value,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.w700,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LegendItem extends StatelessWidget {
  final Color color;
  final String label;

  const _LegendItem({required this.color, required this.label});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 14,
          height: 14,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(width: 6),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
