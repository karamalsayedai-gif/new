import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_animate/flutter_animate.dart';
import '../theme/app_theme.dart';
import '../providers/customer_provider.dart';
import '../widgets/customer_card.dart';
import 'customer_detail_screen.dart';
import 'add_customer_screen.dart';

class CustomersScreen extends StatefulWidget {
  const CustomersScreen({super.key});

  @override
  State<CustomersScreen> createState() => _CustomersScreenState();
}

class _CustomersScreenState extends State<CustomersScreen> {
  final _searchController = TextEditingController();
  bool _isSearching = false;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: _isSearching
            ? TextField(
                controller: _searchController,
                autofocus: true,
                style: const TextStyle(color: Colors.white),
                decoration: InputDecoration(
                  hintText: 'ابحث عن عميل...',
                  hintStyle: TextStyle(color: Colors.white.withOpacity(0.6)),
                  border: InputBorder.none,
                  filled: false,
                ),
                onChanged: (q) =>
                    context.read<CustomerProvider>().search(q),
              )
            : const Text('العملاء'),
        actions: [
          IconButton(
            onPressed: () {
              setState(() {
                _isSearching = !_isSearching;
                if (!_isSearching) {
                  _searchController.clear();
                  context.read<CustomerProvider>().search('');
                }
              });
            },
            icon: Icon(
              _isSearching ? Icons.close : Icons.search_rounded,
            ),
          ),
          IconButton(
            onPressed: () => _sortCustomers(context),
            icon: const Icon(Icons.sort_rounded),
          ),
        ],
      ),
      body: Consumer<CustomerProvider>(
        builder: (_, provider, __) {
          if (provider.isLoading) {
            return const Center(child: CircularProgressIndicator());
          }

          if (provider.customers.isEmpty) {
            return _buildEmptyState(context, provider.searchQuery.isNotEmpty);
          }

          return RefreshIndicator(
            onRefresh: provider.loadCustomers,
            child: ListView.builder(
              padding: const EdgeInsets.only(top: 8, bottom: 100),
              itemCount: provider.customers.length,
              itemBuilder: (_, i) {
                final customer = provider.customers[i];
                return CustomerCard(
                  customer: customer,
                  balance: provider.getBalance(customer.id!),
                  onTap: () => _openCustomer(context, customer.id!),
                  onLongPress: () => _showOptions(context, customer.id!),
                )
                    .animate(delay: (i * 50).ms)
                    .slideX(
                      begin: -0.05,
                      duration: 300.ms,
                      curve: Curves.easeOut,
                    )
                    .fade(duration: 300.ms);
              },
            ),
          );
        },
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => _addCustomer(context),
        child: const Icon(Icons.person_add_rounded),
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, bool isSearching) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            isSearching ? Icons.search_off_rounded : Icons.people_outline,
            size: 80,
            color: AppColors.textHint,
          ),
          const SizedBox(height: 16),
          Text(
            isSearching ? 'لا توجد نتائج' : 'لا يوجد عملاء بعد',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: AppColors.textSecondary,
                ),
          ),
          const SizedBox(height: 8),
          Text(
            isSearching
                ? 'جرب كلمة بحث مختلفة'
                : 'اضغط على + لإضافة أول عميل',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: AppColors.textHint,
                ),
          ),
          if (!isSearching) ...[
            const SizedBox(height: 24),
            ElevatedButton.icon(
              onPressed: () => _addCustomer(context),
              icon: const Icon(Icons.person_add_rounded),
              label: const Text('إضافة عميل'),
            ),
          ],
        ],
      ),
    );
  }

  void _openCustomer(BuildContext context, int customerId) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CustomerDetailScreen(customerId: customerId),
      ),
    ).then((_) => context.read<CustomerProvider>().loadCustomers());
  }

  void _addCustomer(BuildContext context) {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const AddCustomerScreen()),
    ).then((_) => context.read<CustomerProvider>().loadCustomers());
  }

  void _showOptions(BuildContext context, int customerId) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(height: 20),
            ListTile(
              leading: const Icon(Icons.open_in_new_rounded),
              title: const Text('فتح الحساب'),
              onTap: () {
                Navigator.pop(context);
                _openCustomer(context, customerId);
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete_outline, color: AppColors.debit),
              title: const Text('حذف العميل',
                  style: TextStyle(color: AppColors.debit)),
              onTap: () {
                Navigator.pop(context);
                _confirmDelete(context, customerId);
              },
            ),
          ],
        ),
      ),
    );
  }

  void _confirmDelete(BuildContext context, int customerId) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('حذف العميل'),
        content: const Text(
            'سيتم حذف العميل وجميع معاملاته. هل أنت متأكد؟'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(context);
              context.read<CustomerProvider>().deleteCustomer(customerId);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('تم حذف العميل')),
              );
            },
            style: ElevatedButton.styleFrom(backgroundColor: AppColors.debit),
            child: const Text('حذف'),
          ),
        ],
      ),
    );
  }

  void _sortCustomers(BuildContext context) {
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
            Text('ترتيب حسب',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            ListTile(
              leading: const Icon(Icons.sort_by_alpha_rounded),
              title: const Text('الاسم'),
              onTap: () => Navigator.pop(context),
            ),
            ListTile(
              leading: const Icon(Icons.schedule_rounded),
              title: const Text('آخر تعامل'),
              onTap: () => Navigator.pop(context),
            ),
            ListTile(
              leading: const Icon(Icons.attach_money_rounded),
              title: const Text('الرصيد'),
              onTap: () => Navigator.pop(context),
            ),
          ],
        ),
      ),
    );
  }
}
